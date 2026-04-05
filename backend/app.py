"""
app.py — Flask API for Trash Detection Video Analytics.

Endpoints:
  POST /api/upload          — Upload video, start analysis job
  GET  /api/status/<job_id> — Server-Sent Events progress stream
  GET  /api/report/<job_id> — Full JSON report
  GET  /api/download/csv/<job_id> — Download CSV report
  GET  /api/frames/<job_id> — List of available annotated frame indices
  GET  /api/frame/<job_id>/<frame_idx> — Single annotated frame as JPEG
  GET  /api/vlmcheck        — Check if VLM is available
"""

import os
import sys
import uuid
import json
import time
import logging
import threading
import cv2
import numpy as np
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import io

# ── Path setup (so we can import local modules) ───────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))

from analyzer import analyze_video, AnalysisResult
from report import generate_csv, generate_report_json
from pdf_report import generate_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Storage ───────────────────────────────────────────────────────────────
_UPLOAD_DIR = _BACKEND_DIR / "uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory job store: job_id -> dict
_JOBS: dict = {}
_JOBS_LOCK = threading.RLock()

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2 GB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def _new_job(video_path: str, use_vlm: bool) -> str:
    job_id = str(uuid.uuid4())
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "id": job_id,
            "status": "queued",       # queued | running | done | error
            "progress": 0,
            "total": 1,
            "message": "Queued…",
            "video_path": video_path,
            "use_vlm": use_vlm,
            "result": None,
            "error": None,
            "events": [],             # SSE event queue for streaming
        }
    return job_id


def _push_event(job_id: str, msg: str, progress: int, total: int):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job:
            job["progress"] = progress
            job["total"] = total
            job["message"] = msg
            job["events"].append({
                "progress": progress,
                "total": total,
                "message": msg,
                "percent": round(progress / max(total, 1) * 100, 1),
            })


def _run_analysis(job_id: str):
    """Run in a background thread."""
    with _JOBS_LOCK:
        job = _JOBS[job_id]
        job["status"] = "running"

    video_path = job["video_path"]
    use_vlm = job["use_vlm"]

    def _progress(current, total, msg):
        _push_event(job_id, msg, current, total)

    try:
        result: AnalysisResult = analyze_video(
            video_path=video_path,
            use_vlm=use_vlm,
            progress_callback=_progress,
            annotated_frame_interval=30,
        )
        report = generate_report_json(result)

        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "done"
            _JOBS[job_id]["result"] = report
            # Store annotated frames separately (numpy arrays)
            _JOBS[job_id]["annotated_frames"] = result.annotated_frames
            _JOBS[job_id]["csv_bytes"] = generate_csv(result)
            _push_event(job_id, "Analysis complete!", result.total_frames, result.total_frames)

    except Exception as e:
        logger.exception(f"[Job {job_id}] Analysis failed: {e}")
        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "error"
            _JOBS[job_id]["error"] = str(e)
            _push_event(job_id, f"Error: {e}", 0, 1)


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_video():
    """Accept video file upload, start background analysis."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    f = request.files["video"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    use_vlm = request.form.get("use_vlm", "true").lower() == "true"

    # Save file
    job_id = str(uuid.uuid4())
    save_path = _UPLOAD_DIR / f"{job_id}{ext}"
    f.save(str(save_path))
    logger.info(f"[Upload] Saved to {save_path} (use_vlm={use_vlm})")

    # Create job and start thread
    jid = _new_job(str(save_path), use_vlm)
    t = threading.Thread(target=_run_analysis, args=(jid,), daemon=True)
    t.start()

    return jsonify({"job_id": jid}), 202


@app.route("/api/status/<job_id>")
def stream_status(job_id: str):
    """Server-Sent Events stream for real-time progress."""
    def event_stream():
        sent_idx = 0
        while True:
            with _JOBS_LOCK:
                job = _JOBS.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            with _JOBS_LOCK:
                events = job["events"][sent_idx:]
                status = job["status"]

            for evt in events:
                evt["status"] = status
                yield f"data: {json.dumps(evt)}\n\n"
                sent_idx += 1

            if status in ("done", "error"):
                final = {"status": status, "message": job.get("message", ""), "percent": 100}
                if status == "error":
                    final["error"] = job.get("error", "Unknown error")
                yield f"data: {json.dumps(final)}\n\n"
                return

            time.sleep(0.5)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/report/<job_id>")
def get_report(job_id: str):
    """Return full JSON analysis report."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "Analysis not complete", "status": job["status"]}), 202
    return jsonify(job["result"])


@app.route("/api/download/csv/<job_id>")
def download_csv(job_id: str):
    """Download CSV report file."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "Analysis not complete"}), 202

    csv_bytes = job.get("csv_bytes", b"")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trash_report_{job_id[:8]}.csv"},
    )

@app.route("/api/download/pdf/<job_id>")
def download_pdf(job_id: str):
    """Generate and stream a structured PDF report."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Job not ready or not found"}), 404

    # job["result"] is already the fully enriched JSON dict from generate_report_json()
    report_data = job.get("result")
    if report_data is None:
        return jsonify({"error": "No result data"}), 404

    try:
        pdf_bytes = generate_pdf(report_data)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="trashguard_report_{job_id[:8]}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.error(f"[pdf] Generation failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500



@app.route("/api/frames/<job_id>")
def list_frames(job_id: str):
    """List available annotated frame indices."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"frames": []})
    frames = sorted(job.get("annotated_frames", {}).keys())
    return jsonify({"frames": frames})


@app.route("/api/frame/<job_id>/<int:frame_idx>")
def get_frame(job_id: str, frame_idx: int):
    """Return annotated frame as JPEG."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Not ready"}), 404

    frames = job.get("annotated_frames", {})
    # Find closest frame
    if frame_idx not in frames:
        if not frames:
            return jsonify({"error": "No frames"}), 404
        frame_idx = min(frames.keys(), key=lambda k: abs(k - frame_idx))

    img_array = frames[frame_idx]
    _, buf = cv2.imencode(".jpg", img_array, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(buf.tobytes(), mimetype="image/jpeg")


@app.route("/api/vlmcheck")
def vlm_check():
    """Health-check: returns availability of Gemini VLM and local CLIP model."""
    try:
        from vlm_helper import is_available, is_clip_available, CLIP_MODEL_ID
        gemini_ok = is_available()
        clip_ok = is_clip_available()
        return jsonify({
            "vlm_available": gemini_ok,
            "clip_available": clip_ok,
            "clip_model": CLIP_MODEL_ID,
            "clip_device": "cuda" if __import__('torch').cuda.is_available() else "cpu",
        })
    except Exception as e:
        return jsonify({"vlm_available": False, "clip_available": False, "error": str(e)})


@app.route("/api/clip-verify", methods=["POST"])
def clip_verify():
    """
    On-demand CLIP zero-shot verification.
    Accepts JSON: { "image_b64": "<base64 JPEG>", "labels": ["..."] (optional) }
    Returns CLIP scores for the provided labels.
    """
    import base64
    try:
        data = request.get_json(force=True)
        if not data or "image_b64" not in data:
            return jsonify({"error": "Missing image_b64 field"}), 400

        raw = base64.b64decode(data["image_b64"])
        from PIL import Image
        pil_img = Image.open(io.BytesIO(raw)).convert("RGB")

        labels = data.get("labels", None)

        from vlm_helper import clip_verify_frame
        result = clip_verify_frame(pil_img, labels)
        return jsonify(result)

    except Exception as e:
        logger.error(f"[clip-verify] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs")
def list_jobs():
    """List all job IDs and statuses (for debugging)."""
    with _JOBS_LOCK:
        summary = [
            {"id": jid, "status": j["status"], "message": j.get("message", "")}
            for jid, j in _JOBS.items()
        ]
    return jsonify(summary)


@app.route("/")
def index():
    """Serve the frontend."""
    frontend_path = _BACKEND_DIR.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return send_file(str(frontend_path))
    return "<h1>Trash Detection API</h1><p>Frontend not found. Open frontend/index.html directly.</p>"


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static frontend files."""
    frontend_dir = _BACKEND_DIR.parent / "frontend"
    target = frontend_dir / filename
    if target.exists() and target.is_file():
        return send_file(str(target))
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    print("=" * 60)
    print("  Trash Detection Video Analytics — Backend")
    print(f"  Upload dir: {_UPLOAD_DIR}")
    print(f"  API:  http://localhost:5000/api/")
    print(f"  App:  http://localhost:5000/")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
