"""
analyzer.py — Core video analysis pipeline.

Steps:
  1. Run yolo11n.pt on every frame → detect persons & cars (with BoT-SORT tracking)
  2. Run best.pt on every frame → detect trash (with BoT-SORT tracking)
  3. Merge detections: flag frames where persons & trash co-appear (throwing events)
  4. Sample key frames every VLM_INTERVAL seconds → generate VLM scene descriptions
  5. Return AnalysisResult dataclass consumed by report.py and app.py
"""

import cv2
import time
import logging
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

import numpy as np
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BEST_PT = str(_PROJECT_ROOT / "best.pt")
_YOLO11N_PT = str(_PROJECT_ROOT / "yolo11n.pt")

# Classes we want from the base yolo11n model
BASE_CLASSES_OF_INTEREST = {"person", "car", "truck", "bus", "bicycle", "motorcycle"}

# Minimum IoU for "person overlaps trash" → throwing event
THROW_IOU_THRESHOLD = 0.05  # low: person near trash counts
# Minimum new-detection age — trash tracks younger than this are "new"
NEW_TRASH_MAX_AGE = 30  # frames
# VLM sampling interval in seconds
VLM_INTERVAL_SEC = 2.0
# How many frames to skip between full detections (for speed; set 1 = every frame)
FRAME_SKIP = 1


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Detection:
    frame_idx: int
    timestamp: float           # seconds
    track_id: int
    class_name: str
    source_model: str          # "base" | "custom"
    bbox: List[float]          # [x1, y1, x2, y2] normalised [0,1]
    confidence: float


@dataclass
class ThrowingEvent:
    frame_idx: int
    timestamp: float
    person_track_id: int
    trash_track_id: int
    description: str           # VLM or computed label


@dataclass
class VLMDescription:
    frame_idx: int
    timestamp: float
    description: str


@dataclass
class AnalysisResult:
    video_path: str
    duration_sec: float
    fps: float
    total_frames: int
    width: int
    height: int
    custom_classes: List[str]  # classes from best.pt
    detections: List[Detection] = field(default_factory=list)
    throwing_events: List[ThrowingEvent] = field(default_factory=list)
    vlm_descriptions: List[VLMDescription] = field(default_factory=list)
    annotated_frames: Dict[int, np.ndarray] = field(default_factory=dict)
    # Summary stats (filled after processing)
    unique_persons: int = 0
    unique_cars: int = 0
    unique_trash: int = 0
    total_events: int = 0

    def to_json_safe(self) -> dict:
        """Return a JSON-serialisable dict (excludes numpy arrays)."""
        return {
            "video_path": self.video_path,
            "duration_sec": round(self.duration_sec, 2),
            "fps": round(self.fps, 2),
            "total_frames": self.total_frames,
            "width": self.width,
            "height": self.height,
            "custom_classes": self.custom_classes,
            "unique_persons": self.unique_persons,
            "unique_cars": self.unique_cars,
            "unique_trash": self.unique_trash,
            "total_events": self.total_events,
            "detections": [
                {
                    "frame_idx": d.frame_idx,
                    "timestamp": round(d.timestamp, 3),
                    "track_id": d.track_id,
                    "class_name": d.class_name,
                    "source_model": d.source_model,
                    "bbox": [round(v, 4) for v in d.bbox],
                    "confidence": round(d.confidence, 3),
                }
                for d in self.detections
            ],
            "throwing_events": [
                {
                    "frame_idx": e.frame_idx,
                    "timestamp": round(e.timestamp, 3),
                    "person_track_id": e.person_track_id,
                    "trash_track_id": e.trash_track_id,
                    "description": e.description,
                }
                for e in self.throwing_events
            ],
            "vlm_descriptions": [
                {
                    "frame_idx": v.frame_idx,
                    "timestamp": round(v.timestamp, 3),
                    "description": v.description,
                }
                for v in self.vlm_descriptions
            ],
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _iou(a: List[float], b: List[float]) -> float:
    """Compute IoU of two [x1,y1,x2,y2] normalised boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter + 1e-9)


def _expand_box(bbox, factor=1.5, w=1.0, h=1.0):
    """Expand bbox by factor (for proximity check instead of strict overlap)."""
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    bw = (bbox[2] - bbox[0]) * factor / 2
    bh = (bbox[3] - bbox[1]) * factor / 2
    return [
        max(0, cx - bw), max(0, cy - bh),
        min(w, cx + bw), min(h, cy + bh)
    ]


def _draw_boxes(frame: np.ndarray, detections: List[Detection], events_this_frame: bool) -> np.ndarray:
    """Draw bounding boxes and labels on a copy of frame."""
    annotated = frame.copy()
    H, W = frame.shape[:2]

    COLOR_MAP = {
        "person": (34, 139, 34),    # green
        "car": (70, 130, 180),       # steel blue
        "truck": (70, 130, 180),
        "bus": (70, 130, 180),
        "bicycle": (100, 149, 237),
        "motorcycle": (100, 149, 237),
    }
    TRASH_COLOR = (0, 0, 220)       # red for trash
    EVENT_COLOR = (0, 165, 255)     # orange for event highlight

    for det in detections:
        x1 = int(det.bbox[0] * W)
        y1 = int(det.bbox[1] * H)
        x2 = int(det.bbox[2] * W)
        y2 = int(det.bbox[3] * H)

        if det.source_model == "custom":
            color = TRASH_COLOR
        else:
            color = COLOR_MAP.get(det.class_name, (180, 180, 180))

        if events_this_frame and det.class_name == "person":
            color = EVENT_COLOR

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{det.class_name} #{det.track_id} {det.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    if events_this_frame:
        cv2.putText(annotated, "⚠ LITTERING EVENT", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, EVENT_COLOR, 2, cv2.LINE_AA)

    return annotated


# ── Main analysis function ────────────────────────────────────────────────────

def analyze_video(
    video_path: str,
    use_vlm: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    annotated_frame_interval: int = 30,
) -> AnalysisResult:
    """
    Analyse a video file for trash-throwing incidents.

    Args:
        video_path: Path to the input video.
        use_vlm: Whether to run VLM scene descriptions.
        progress_callback: Called as callback(current_frame, total_frames, status_msg).
        annotated_frame_interval: Save 1 annotated frame every N frames (for gallery).

    Returns:
        AnalysisResult with all detection data and events.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps

    logger.info(f"[Analyzer] Video: {video_path} | {total_frames} frames @ {fps:.1f} fps | {duration_sec:.1f}s")

    # Load models
    if progress_callback:
        progress_callback(0, total_frames, "Loading YOLO models…")

    base_model = YOLO(_YOLO11N_PT)
    custom_model = YOLO(_BEST_PT)

    # Print custom model classes for debugging
    custom_classes = list(custom_model.names.values())
    logger.info(f"[Analyzer] Custom model classes: {custom_classes}")

    result = AnalysisResult(
        video_path=video_path,
        duration_sec=duration_sec,
        fps=fps,
        total_frames=total_frames,
        width=width,
        height=height,
        custom_classes=custom_classes,
    )

    # Track: dict[track_id] -> first_seen_frame
    trash_first_seen: Dict[int, int] = {}
    # Events: set of (person_id, trash_id) already recorded
    recorded_events = set()
    # VLM timing
    last_vlm_time = -VLM_INTERVAL_SEC

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        if frame_idx % max(1, FRAME_SKIP) != 0:
            frame_idx += 1
            continue

        if progress_callback and frame_idx % 10 == 0:
            progress_callback(frame_idx, total_frames, f"Processing frame {frame_idx}/{total_frames}…")

        frame_detections: List[Detection] = []

        # ── 1. Base model: persons & cars ─────────────────────────────────
        try:
            base_results = base_model.track(
                frame, persist=True, tracker="botsort.yaml",
                classes=[0, 1, 2, 3, 5, 7],  # person, bicycle, car, motorcycle, bus, truck
                verbose=False, stream=False, conf=0.35
            )
            if base_results and base_results[0].boxes is not None:
                boxes = base_results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = base_model.names[cls_id]
                    if cls_name not in BASE_CLASSES_OF_INTEREST:
                        continue
                    track_id = int(box.id[0]) if box.id is not None else -1
                    xyxyn = box.xyxyn[0].tolist()
                    conf = float(box.conf[0])
                    frame_detections.append(Detection(
                        frame_idx=frame_idx,
                        timestamp=timestamp,
                        track_id=track_id,
                        class_name=cls_name,
                        source_model="base",
                        bbox=xyxyn,
                        confidence=conf,
                    ))
        except Exception as e:
            logger.debug(f"[Analyzer] Base model frame {frame_idx}: {e}")

        # ── 2. Custom model: trash ─────────────────────────────────────────
        try:
            custom_results = custom_model.track(
                frame, persist=True, tracker="botsort.yaml",
                verbose=False, stream=False, conf=0.3
            )
            if custom_results and custom_results[0].boxes is not None:
                boxes = custom_results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = custom_model.names[cls_id]
                    track_id = int(box.id[0]) if box.id is not None else -1
                    xyxyn = box.xyxyn[0].tolist()
                    conf = float(box.conf[0])

                    # Record first sighting of this trash track
                    if track_id not in trash_first_seen:
                        trash_first_seen[track_id] = frame_idx

                    frame_detections.append(Detection(
                        frame_idx=frame_idx,
                        timestamp=timestamp,
                        track_id=track_id,
                        class_name=cls_name,
                        source_model="custom",
                        bbox=xyxyn,
                        confidence=conf,
                    ))
        except Exception as e:
            logger.debug(f"[Analyzer] Custom model frame {frame_idx}: {e}")

        result.detections.extend(frame_detections)

        # ── 3. Throwing event detection ────────────────────────────────────
        persons = [d for d in frame_detections if d.class_name == "person"]
        trash_items = [d for d in frame_detections if d.source_model == "custom"]

        events_this_frame = False
        for person in persons:
            expanded_person = _expand_box(person.bbox, factor=2.0)
            for trash in trash_items:
                # Only flag if this trash track is "new" (recently appeared)
                age = frame_idx - trash_first_seen.get(trash.track_id, frame_idx)
                key = (person.track_id, trash.track_id)
                if key not in recorded_events:
                    iou = _iou(expanded_person, trash.bbox)
                    if iou > THROW_IOU_THRESHOLD or age <= NEW_TRASH_MAX_AGE:
                        event = ThrowingEvent(
                            frame_idx=frame_idx,
                            timestamp=timestamp,
                            person_track_id=person.track_id,
                            trash_track_id=trash.track_id,
                            description=f"Person #{person.track_id} appears to discard {trash.class_name} "
                                        f"(track #{trash.track_id}) at {timestamp:.2f}s",
                        )
                        result.throwing_events.append(event)
                        recorded_events.add(key)
                        events_this_frame = True
                        logger.info(f"[Analyzer] Throwing event at {timestamp:.2f}s — {event.description}")

        # ── 4. VLM description ─────────────────────────────────────────────
        if use_vlm and (timestamp - last_vlm_time) >= VLM_INTERVAL_SEC:
            last_vlm_time = timestamp
            if progress_callback:
                progress_callback(frame_idx, total_frames, f"Running VLM at {timestamp:.1f}s…")
            try:
                from vlm_helper import describe_frame
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                desc = describe_frame(pil_img)
                result.vlm_descriptions.append(VLMDescription(
                    frame_idx=frame_idx,
                    timestamp=timestamp,
                    description=desc,
                ))
            except Exception as e:
                logger.warning(f"[Analyzer] VLM failed at frame {frame_idx}: {e}")

        # ── 5. Save annotated frame for gallery ────────────────────────────
        if frame_idx % annotated_frame_interval == 0 or events_this_frame:
            annotated = _draw_boxes(frame, frame_detections, events_this_frame)
            result.annotated_frames[frame_idx] = annotated

        frame_idx += 1

    cap.release()

    # ── Compute summary stats ──────────────────────────────────────────────
    person_ids = {d.track_id for d in result.detections if d.class_name == "person"}
    car_ids = {d.track_id for d in result.detections
               if d.class_name in {"car", "truck", "bus", "bicycle", "motorcycle"}}
    trash_ids = {d.track_id for d in result.detections if d.source_model == "custom"}

    result.unique_persons = len(person_ids)
    result.unique_cars = len(car_ids)
    result.unique_trash = len(trash_ids)
    result.total_events = len(result.throwing_events)

    if progress_callback:
        progress_callback(total_frames, total_frames, "Analysis complete.")

    logger.info(
        f"[Analyzer] Done. Persons={result.unique_persons}, Cars={result.unique_cars}, "
        f"Trash={result.unique_trash}, Events={result.total_events}"
    )

    return result
