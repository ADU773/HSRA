"""
vlm_helper.py — 100% local CLIP-based scene verification and description.

No API keys. No tuples. No external services.

How it works:
  • CLIP (openai/clip-vit-base-patch32) encodes the video frame and a set of
    plain-English candidate sentences per semantic axis.
  • The highest-scoring sentence for each axis is selected by cosine similarity.
  • The selected sentences are assembled into a coherent scene description.

Axes queried:
  scene_type · human_activity · waste_visibility ·
  vehicle_presence · incident_severity · time_of_day · crowd_density
"""

import logging
from typing import Dict, List, Optional

import torch
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ── Model config ───────────────────────────────────────────────────────────────

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"


# ── Littering verification labels ─────────────────────────────────────────────

CLIP_LABELS: List[str] = [
    "a person throwing or littering trash in public",
    "a person dropping garbage or waste on the ground",
    "a person walking normally without any littering",
    "an empty street or road with no people",
    "garbage or trash lying on the ground",
]

LITTERING_LABELS = {
    "a person throwing or littering trash in public",
    "a person dropping garbage or waste on the ground",
}

CLIP_CONFIDENCE_THRESHOLD = 0.30


# ── Semantic axes — plain flat lists, no tuples ────────────────────────────────

SCENE_TYPE = [
    "a busy urban street with heavy foot traffic",
    "a quiet residential road with few people",
    "a public park or green area",
    "a commercial shopping area or marketplace",
    "a highway or fast-moving road with vehicles",
    "an alley or narrow side street",
    "a parking lot or vehicle loading area",
    "an outdoor public space with benches or seating",
]

HUMAN_ACTIVITY = [
    "a person actively throwing garbage out of a vehicle",
    "a person bending down to drop trash on the ground",
    "a person holding a bag and discarding waste",
    "a person walking or running along the road",
    "a group of people standing and talking",
    "a person entering or exiting a vehicle",
    "no people visible in the scene",
    "a person on a bicycle or motorcycle",
]

WASTE_VISIBILITY = [
    "large amounts of trash and garbage clearly visible on the ground",
    "a single piece of litter or small garbage item on the ground",
    "garbage bags or waste containers spilling onto the street",
    "a plastic bag or food wrapper visible in the scene",
    "no visible garbage or litter anywhere in the scene",
    "scattered small debris across the road surface",
    "a pile of waste or discarded objects near the roadside",
]

VEHICLE_PRESENCE = [
    "multiple cars and trucks visible on the road",
    "a single parked car on the side of the road",
    "a moving vehicle passing through the scene",
    "a motorcycle or scooter visible in the scene",
    "a large truck or lorry present in the scene",
    "no vehicles visible anywhere in the frame",
    "a bus or public transit vehicle visible",
]

INCIDENT_SEVERITY = [
    "a confirmed littering incident with a person and trash both clearly visible",
    "a suspected littering event that requires further review",
    "a minor waste disposal event with a small item dropped",
    "a major illegal dumping incident with bulk waste left in public",
    "no littering or waste-related activity apparent in this scene",
]

TIME_OF_DAY = [
    "a bright sunny daytime outdoor scene",
    "an overcast or cloudy daytime outdoor scene",
    "an evening or dusk outdoor scene with fading light",
    "a dark nighttime scene with artificial street lighting",
    "a night scene lit primarily by vehicle headlights",
]

CROWD_DENSITY = [
    "a very crowded area with many pedestrians",
    "a moderately populated area with several people",
    "a sparse area with only one or two people visible",
    "a completely empty street with no people at all",
]


# ── Device selection ───────────────────────────────────────────────────────────

def _get_device() -> str:
    if torch.cuda.is_available():
        logger.info("[CLIP] CUDA GPU detected — running on GPU.")
        return "cuda"
    logger.info("[CLIP] No GPU detected — running on CPU.")
    return "cpu"


# ── Singleton CLIP wrapper ─────────────────────────────────────────────────────

class _CLIPVerifier:
    _instance: Optional["_CLIPVerifier"] = None

    def __init__(self):
        self._model = None
        self._processor = None
        self._device = _get_device()
        self._loaded = False
        self._load_error: Optional[str] = None

    @classmethod
    def get(cls) -> "_CLIPVerifier":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if self._load_error:
            return False
        try:
            from transformers import CLIPProcessor, CLIPModel

            logger.info(f"[CLIP] Loading {CLIP_MODEL_ID} on {self._device}…")
            self._model = CLIPModel.from_pretrained(
                CLIP_MODEL_ID,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
            ).to(self._device)
            self._model.eval()
            self._processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID)
            self._loaded = True
            logger.info(f"[CLIP] Ready on {self._device.upper()}.")
            return True
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"[CLIP] Failed to load: {e}")
            return False

    def _best_label(self, image: PILImage.Image, candidates: List[str]) -> tuple:
        """
        Score every candidate string against the image with CLIP.
        Returns (best_label: str, best_prob: float).
        """
        inputs = self._processor(
            text=candidates,
            images=image,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.inference_mode():
            outputs = self._model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0].float().cpu().tolist()
        best_idx = max(range(len(probs)), key=lambda i: probs[i])
        return candidates[best_idx], probs[best_idx]

    # ── Littering verification ─────────────────────────────────────────────

    def verify(
        self,
        pil_image: PILImage.Image,
        labels: Optional[List[str]] = None,
    ) -> Dict:
        if not self._ensure_loaded():
            return _error_result(self._load_error or "CLIP not available")

        candidates = labels if labels else CLIP_LABELS

        try:
            image = pil_image.convert("RGB")
            inputs = self._processor(
                text=candidates,
                images=image,
                return_tensors="pt",
                padding=True,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.inference_mode():
                outputs = self._model(**inputs)

            probs = outputs.logits_per_image.softmax(dim=1)[0].float().cpu().tolist()
            all_scores = {lbl: round(p, 4) for lbl, p in zip(candidates, probs)}
            best_idx = max(range(len(probs)), key=lambda i: probs[i])
            best_label = candidates[best_idx]
            best_conf = probs[best_idx]
            is_littering = best_label in LITTERING_LABELS and best_conf >= CLIP_CONFIDENCE_THRESHOLD

            logger.debug(f"[CLIP] '{best_label[:60]}' @ {best_conf:.2%} littering={is_littering}")

            return {
                "label": best_label,
                "confidence": round(best_conf, 4),
                "is_littering": is_littering,
                "all_scores": all_scores,
                "device": self._device,
                "error": None,
            }
        except Exception as e:
            logger.error(f"[CLIP] verify() failed: {e}")
            return _error_result(str(e))

    # ── Rich scene description ─────────────────────────────────────────────

    def describe(self, pil_image: PILImage.Image) -> str:
        """
        Generate a detailed, natural-language scene description using CLIP only.

        Queries 7 semantic axes with plain string lists, picks the best-matching
        label for each, and assembles them into a readable paragraph.
        No API, no tuples, no external dependencies.
        """
        if not self._ensure_loaded():
            return "[CLIP unavailable] Could not load the CLIP model for scene description."

        try:
            image = pil_image.convert("RGB")

            scene,    scene_conf    = self._best_label(image, SCENE_TYPE)
            activity, activity_conf = self._best_label(image, HUMAN_ACTIVITY)
            waste,    waste_conf    = self._best_label(image, WASTE_VISIBILITY)
            vehicle,  vehicle_conf  = self._best_label(image, VEHICLE_PRESENCE)
            severity, severity_conf = self._best_label(image, INCIDENT_SEVERITY)
            time_,    time_conf     = self._best_label(image, TIME_OF_DAY)
            crowd,    crowd_conf    = self._best_label(image, CROWD_DENSITY)

            # Build natural sentences from the winning labels
            description = (
                f"Scene: {scene}, {time_}, with {crowd}. "
                f"Activity observed: {activity}. "
                f"Waste status: {waste}. "
                f"Vehicles: {vehicle}. "
                f"Incident assessment: {severity}. "
                f"[CLIP confidence — scene:{scene_conf:.0%} "
                f"activity:{activity_conf:.0%} waste:{waste_conf:.0%} "
                f"severity:{severity_conf:.0%}]"
            )

            logger.debug(f"[CLIP-describe] {description[:120]}…")
            return description

        except Exception as e:
            logger.error(f"[CLIP] describe() failed: {e}")
            return f"[CLIP description error: {e}]"

    def is_available(self) -> bool:
        return self._ensure_loaded()


def _error_result(msg: str) -> Dict:
    return {"label": "unknown", "confidence": 0.0, "is_littering": False,
            "all_scores": {}, "device": "none", "error": msg}


# ── Public functions ───────────────────────────────────────────────────────────

def clip_verify_frame(
    pil_image: PILImage.Image,
    labels: Optional[List[str]] = None,
) -> Dict:
    """Zero-shot CLIP littering verification. Returns {label, confidence, is_littering, …}"""
    return _CLIPVerifier.get().verify(pil_image, labels)


def describe_frame(
    pil_image: PILImage.Image,
    prompt: str = "",          # kept for API compatibility; not used by CLIP
) -> str:
    """
    Generate a rich scene description using CLIP across 7 semantic axes.
    Fully local — no API keys, no external services.
    """
    return _CLIPVerifier.get().describe(pil_image)


def is_clip_available() -> bool:
    """Return True if the CLIP model is loaded and ready."""
    return _CLIPVerifier.get().is_available()


def is_available() -> bool:
    """Backward-compatible alias — returns CLIP availability (Gemini removed)."""
    return _CLIPVerifier.get().is_available()


def get_clip_labels() -> List[str]:
    """Return the default zero-shot littering label set."""
    return list(CLIP_LABELS)
