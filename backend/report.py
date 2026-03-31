"""
report.py — Generate CSV and JSON reports from AnalysisResult.
"""

import csv
import io
import json
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analyzer import AnalysisResult


def _fmt_ts(sec: float) -> str:
    """Format seconds as MM:SS.mmm"""
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def generate_csv(result: "AnalysisResult") -> bytes:
    """
    Generate a CSV report of all detections and events.

    Returns bytes (UTF-8 encoded CSV).
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # ── Header block ──────────────────────────────────────────────────────
    writer.writerow(["# Trash Detection Report"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Video", result.video_path])
    writer.writerow(["Duration (s)", f"{result.duration_sec:.2f}"])
    writer.writerow(["FPS", f"{result.fps:.2f}"])
    writer.writerow(["Resolution", f"{result.width}x{result.height}"])
    writer.writerow([])

    # ── Summary ───────────────────────────────────────────────────────────
    writer.writerow(["=== SUMMARY ==="])
    writer.writerow(["Unique Persons Detected", result.unique_persons])
    writer.writerow(["Unique Vehicles Detected", result.unique_cars])
    writer.writerow(["Unique Trash Items Detected", result.unique_trash])
    writer.writerow(["Littering/Throwing Events", result.total_events])
    writer.writerow([])

    # ── Throwing Events ───────────────────────────────────────────────────
    writer.writerow(["=== LITTERING / THROWING EVENTS ==="])
    writer.writerow(["Event #", "Timestamp", "Time (MM:SS.mmm)", "Person Track ID", "Trash Track ID", "Description"])
    for i, evt in enumerate(result.throwing_events, 1):
        writer.writerow([
            i,
            f"{evt.timestamp:.3f}",
            _fmt_ts(evt.timestamp),
            evt.person_track_id,
            evt.trash_track_id,
            evt.description,
        ])
    writer.writerow([])

    # ── VLM Scene Descriptions ────────────────────────────────────────────
    if result.vlm_descriptions:
        writer.writerow(["=== VLM SCENE DESCRIPTIONS ==="])
        writer.writerow(["Frame", "Timestamp (s)", "Time (MM:SS.mmm)", "Description"])
        for vd in result.vlm_descriptions:
            writer.writerow([vd.frame_idx, f"{vd.timestamp:.3f}", _fmt_ts(vd.timestamp), vd.description])
        writer.writerow([])

    # ── All Detections ────────────────────────────────────────────────────
    writer.writerow(["=== ALL DETECTIONS ==="])
    writer.writerow([
        "Frame", "Timestamp (s)", "Time (MM:SS.mmm)",
        "Track ID", "Class", "Model", "Confidence",
        "X1 (norm)", "Y1 (norm)", "X2 (norm)", "Y2 (norm)"
    ])
    for det in result.detections:
        writer.writerow([
            det.frame_idx,
            f"{det.timestamp:.3f}",
            _fmt_ts(det.timestamp),
            det.track_id,
            det.class_name,
            det.source_model,
            f"{det.confidence:.3f}",
            f"{det.bbox[0]:.4f}",
            f"{det.bbox[1]:.4f}",
            f"{det.bbox[2]:.4f}",
            f"{det.bbox[3]:.4f}",
        ])

    return output.getvalue().encode("utf-8")


def generate_report_json(result: "AnalysisResult") -> dict:
    """
    Generate a full structured JSON report for frontend rendering.

    Returns a plain dict (JSON-serialisable).
    """
    data = result.to_json_safe()

    # Add formatted timestamps to events for display
    for evt in data["throwing_events"]:
        evt["time_formatted"] = _fmt_ts(evt["timestamp"])

    for vd in data["vlm_descriptions"]:
        vd["time_formatted"] = _fmt_ts(vd["timestamp"])

    # Per-class detection summary
    class_counts: dict = {}
    for det in data["detections"]:
        cn = det["class_name"]
        class_counts[cn] = class_counts.get(cn, 0) + 1

    # Per-track timeline (unique track appearances)
    track_timeline: dict = {}
    for det in data["detections"]:
        tid = f"{det['source_model']}_{det['class_name']}_{det['track_id']}"
        if tid not in track_timeline:
            track_timeline[tid] = {
                "track_id": det["track_id"],
                "class_name": det["class_name"],
                "source_model": det["source_model"],
                "first_seen": det["timestamp"],
                "first_seen_fmt": _fmt_ts(det["timestamp"]),
                "last_seen": det["timestamp"],
                "last_seen_fmt": _fmt_ts(det["timestamp"]),
                "detections": 0,
            }
        entry = track_timeline[tid]
        entry["last_seen"] = det["timestamp"]
        entry["last_seen_fmt"] = _fmt_ts(det["timestamp"])
        entry["detections"] += 1

    data["class_counts"] = class_counts
    data["track_timeline"] = list(track_timeline.values())
    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return data
