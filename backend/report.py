"""
report.py — Generate CSV and JSON reports from AnalysisResult.

Report includes:
  - Summary statistics
  - Littering/throwing events with CLIP verification scores
  - Full VLM scene descriptions with timestamps
  - Per-object track timelines with first/last seen & duration on screen
  - Detection-VLM correlation: each VLM entry cross-referenced with
    active detections at that timestamp
"""

import csv
import io
import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from analyzer import AnalysisResult


def _fmt_ts(sec: float) -> str:
    """Format seconds as MM:SS.mmm"""
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def _duration_str(sec: float) -> str:
    """e.g. 4.52s  or  1m 12.3s"""
    if sec < 60:
        return f"{sec:.2f}s"
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}m {s:.1f}s"


# ─────────────────────────────────────────────────────────────────────────────
#  CSV Report
# ─────────────────────────────────────────────────────────────────────────────

def generate_csv(result: "AnalysisResult") -> bytes:
    """
    Generate a detailed CSV report.

    Sections:
      1. Video metadata
      2. Summary statistics
      3. Littering/throwing events (+ CLIP verification)
      4. VLM scene descriptions (with active detections at that timestamp)
      5. Object track timelines (first seen, last seen, duration)
      6. Full detection log
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # ── 1. Metadata ──────────────────────────────────────────────────────────
    writer.writerow(["# TrashGuard Incident Report"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Video", result.video_path])
    writer.writerow(["Duration (s)", f"{result.duration_sec:.2f}"])
    writer.writerow(["Duration (MM:SS)", _fmt_ts(result.duration_sec)])
    writer.writerow(["FPS", f"{result.fps:.2f}"])
    writer.writerow(["Resolution", f"{result.width}x{result.height}"])
    writer.writerow(["Total Frames", result.total_frames])
    writer.writerow([])

    # ── 2. Summary ───────────────────────────────────────────────────────────
    writer.writerow(["=== SUMMARY ==="])
    writer.writerow(["Unique Persons Detected", result.unique_persons])
    writer.writerow(["Unique Vehicles Detected", result.unique_cars])
    writer.writerow(["Unique Trash Items Detected", result.unique_trash])
    writer.writerow(["Littering / Throwing Events", result.total_events])
    clip_confirmed = sum(
        1 for e in result.throwing_events if getattr(e, "clip_is_littering", False)
    )
    writer.writerow(["CLIP-Confirmed Littering Events", clip_confirmed])
    writer.writerow(["VLM Scene Descriptions Generated", len(result.vlm_descriptions)])
    writer.writerow([])

    # ── 3. Throwing Events (with CLIP) ───────────────────────────────────────
    writer.writerow(["=== LITTERING / THROWING EVENTS ==="])
    writer.writerow([
        "Event #", "Timestamp (s)", "Time (MM:SS.mmm)",
        "Frame #", "Person Track ID", "Trash Track ID",
        "Description",
        "CLIP Label", "CLIP Confidence (%)", "CLIP Littering Confirmed",
    ])
    for i, evt in enumerate(result.throwing_events, 1):
        clip_label = getattr(evt, "clip_label", "")
        clip_conf  = getattr(evt, "clip_confidence", 0.0)
        clip_lit   = getattr(evt, "clip_is_littering", False)
        writer.writerow([
            i,
            f"{evt.timestamp:.3f}",
            _fmt_ts(evt.timestamp),
            evt.frame_idx,
            evt.person_track_id,
            evt.trash_track_id,
            evt.description,
            clip_label,
            f"{clip_conf * 100:.1f}" if clip_label else "",
            "YES" if clip_lit else ("NO" if clip_label else ""),
        ])
    writer.writerow([])

    # ── 4. VLM Scene Descriptions (with active objects) ──────────────────────
    if result.vlm_descriptions:
        # Build a quick lookup: timestamp → set of active track summaries
        def _active_at(ts: float, window: float = 1.0) -> str:
            active = [
                d for d in result.detections
                if abs(d.timestamp - ts) <= window
            ]
            if not active:
                return "—"
            # Summarise unique classes active in window
            seen: Dict[str, int] = {}
            for d in active:
                seen[d.class_name] = seen.get(d.class_name, 0) + 1
            return "; ".join(f"{cnt}× {cls}" for cls, cnt in sorted(seen.items()))

        writer.writerow(["=== VLM SCENE DESCRIPTIONS ==="])
        writer.writerow([
            "Frame #", "Timestamp (s)", "Time (MM:SS.mmm)",
            "Active Objects (±1s window)", "VLM Description",
        ])
        for vd in result.vlm_descriptions:
            writer.writerow([
                vd.frame_idx,
                f"{vd.timestamp:.3f}",
                _fmt_ts(vd.timestamp),
                _active_at(vd.timestamp),
                vd.description,
            ])
        writer.writerow([])

    # ── 5. Object Track Timelines ─────────────────────────────────────────────
    writer.writerow(["=== OBJECT TRACK TIMELINES ==="])
    writer.writerow([
        "Track ID", "Class", "Model",
        "First Seen (s)", "First Seen (MM:SS)",
        "Last Seen (s)", "Last Seen (MM:SS)",
        "Duration on Screen",
        "Total Detections",
    ])
    # Build timeline from detections
    track_map: Dict[str, dict] = {}
    for det in result.detections:
        key = f"{det.source_model}_{det.class_name}_{det.track_id}"
        if key not in track_map:
            track_map[key] = {
                "track_id": det.track_id,
                "class_name": det.class_name,
                "source_model": det.source_model,
                "first_seen": det.timestamp,
                "last_seen": det.timestamp,
                "count": 0,
            }
        entry = track_map[key]
        entry["last_seen"] = max(entry["last_seen"], det.timestamp)
        entry["first_seen"] = min(entry["first_seen"], det.timestamp)
        entry["count"] += 1

    for entry in sorted(track_map.values(), key=lambda x: x["first_seen"]):
        duration = entry["last_seen"] - entry["first_seen"]
        writer.writerow([
            entry["track_id"],
            entry["class_name"],
            entry["source_model"],
            f"{entry['first_seen']:.3f}",
            _fmt_ts(entry["first_seen"]),
            f"{entry['last_seen']:.3f}",
            _fmt_ts(entry["last_seen"]),
            _duration_str(duration),
            entry["count"],
        ])
    writer.writerow([])

    # ── 6. Full Detection Log ─────────────────────────────────────────────────
    writer.writerow(["=== ALL DETECTIONS ==="])
    writer.writerow([
        "Frame #", "Timestamp (s)", "Time (MM:SS.mmm)",
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


# ─────────────────────────────────────────────────────────────────────────────
#  JSON Report
# ─────────────────────────────────────────────────────────────────────────────

def generate_report_json(result: "AnalysisResult") -> dict:
    """
    Generate a full structured JSON report for frontend rendering.

    Additions over raw to_json_safe():
      - time_formatted on all events & descriptions
      - class_counts: { class_name: detection_count }
      - track_timeline: per-track first/last/duration/detections
      - vlm_timeline: each VLM entry enriched with active_objects & nearest_event
      - clip_confirmed_count
      - generated_at
    """
    data = result.to_json_safe()

    # ── Formatted timestamps ──────────────────────────────────────────────────
    for evt in data["throwing_events"]:
        evt["time_formatted"] = _fmt_ts(evt["timestamp"])

    for vd in data["vlm_descriptions"]:
        vd["time_formatted"] = _fmt_ts(vd["timestamp"])

    for det in data["detections"]:
        det["time_formatted"] = _fmt_ts(det["timestamp"])

    # ── Per-class detection counts ────────────────────────────────────────────
    class_counts: Dict[str, int] = {}
    for det in data["detections"]:
        cn = det["class_name"]
        class_counts[cn] = class_counts.get(cn, 0) + 1
    data["class_counts"] = class_counts

    # ── Per-track timeline with duration ──────────────────────────────────────
    track_map: Dict[str, dict] = {}
    for det in data["detections"]:
        key = f"{det['source_model']}_{det['class_name']}_{det['track_id']}"
        if key not in track_map:
            track_map[key] = {
                "track_id":       det["track_id"],
                "class_name":     det["class_name"],
                "source_model":   det["source_model"],
                "first_seen":     det["timestamp"],
                "first_seen_fmt": _fmt_ts(det["timestamp"]),
                "last_seen":      det["timestamp"],
                "last_seen_fmt":  _fmt_ts(det["timestamp"]),
                "duration_sec":   0.0,
                "duration_str":   "0.00s",
                "detections":     0,
            }
        entry = track_map[key]
        if det["timestamp"] < entry["first_seen"]:
            entry["first_seen"]     = det["timestamp"]
            entry["first_seen_fmt"] = _fmt_ts(det["timestamp"])
        if det["timestamp"] > entry["last_seen"]:
            entry["last_seen"]     = det["timestamp"]
            entry["last_seen_fmt"] = _fmt_ts(det["timestamp"])
        entry["detections"] += 1

    # Compute durations
    for entry in track_map.values():
        d = entry["last_seen"] - entry["first_seen"]
        entry["duration_sec"] = round(d, 3)
        entry["duration_str"] = _duration_str(d)

    data["track_timeline"] = sorted(
        track_map.values(), key=lambda x: x["first_seen"]
    )

    # ── VLM timeline: enrich each description ─────────────────────────────────
    # Build sorted detections list for fast window queries
    all_dets = data["detections"]

    def _active_objects_at(ts: float, window: float = 1.5) -> List[dict]:
        """Return unique active objects within ±window seconds of ts."""
        seen_keys = set()
        active = []
        for d in all_dets:
            if abs(d["timestamp"] - ts) <= window:
                key = f"{d['class_name']}_{d['track_id']}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    active.append({
                        "track_id":    d["track_id"],
                        "class_name":  d["class_name"],
                        "source_model": d["source_model"],
                        "timestamp":   d["timestamp"],
                        "time_formatted": d["time_formatted"],
                    })
        return active

    def _nearest_event(ts: float) -> dict | None:
        """Return the nearest throwing event to ts, or None if >10s away."""
        if not data["throwing_events"]:
            return None
        nearest = min(data["throwing_events"], key=lambda e: abs(e["timestamp"] - ts))
        if abs(nearest["timestamp"] - ts) > 10:
            return None
        return nearest

    vlm_timeline = []
    for vd in data["vlm_descriptions"]:
        entry = dict(vd)   # copy
        entry["active_objects"]  = _active_objects_at(vd["timestamp"])
        entry["nearest_event"]   = _nearest_event(vd["timestamp"])
        vlm_timeline.append(entry)

    data["vlm_timeline"] = vlm_timeline

    # ── Summary extras ────────────────────────────────────────────────────────
    data["clip_confirmed_count"] = sum(
        1 for e in data["throwing_events"] if e.get("clip_is_littering", False)
    )
    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return data
