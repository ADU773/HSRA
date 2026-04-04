"""
vlm_helper.py — CLIP zero-shot semantic verification + optional Gemini scene description.

CLIP (openai/clip-vit-base-patch32) runs **fully locally** on GPU with no API key required.
It verifies whether a frame contains a littering/throwing event via zero-shot classification.

Gemini Vision (gemini-1.5-flash) provides rich natural-language descriptions when a
GEMINI_API_KEY is available in backend/.env or the environment.

Get a free Gemini key at: https://aistudio.google.com/app/apikey
"""

import os
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional

import torch
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"

# Zero-shot labels used for littering verification
CLIP_LABELS: List[str] = [
    "a person throwing or littering trash in public",
    "a person dropping garbage or waste on the ground",
    "a person walking normally without any littering",
    "an empty street or road with no people",
    "garbage or trash lying on the ground",
]

# Labels considered as "littering confirmed"
LITTERING_LABELS = {
    "a person throwing or littering trash in public",
    "a person dropping garbage or waste on the ground",
}

CLIP_CONFIDENCE_THRESHOLD = 0.30   # minimum confidence to report a CLIP verdict


# ── Device selection ──────────────────────────────────────────────────────────

def _get_device() -> str:
    if torch.cuda.is_available():
        logger.info("[CLIP] CUDA GPU detected — running CLIP on GPU.")
        return "cuda"
    logger.info("[CLIP] No GPU detected — running CLIP on CPU.")
    return "cpu"


# ── CLIP Verifier ─────────────────────────────────────────────────────────────

class _CLIPVerifier:
    """Singleton wrapper around CLIP for zero-shot frame verification."""

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

    def verify(
        self,
        pil_image: PILImage.Image,
        labels: Optional[List[str]] = None,
    ) -> Dict:
        """
        Run zero-shot CLIP classification on a PIL image.

        Args:
            pil_image: RGB PIL image (single frame).
            labels:    Optional list of text labels. Defaults to CLIP_LABELS.

        Returns:
            dict with keys:
              - label: str   — most probable label
              - confidence: float — probability [0, 1]
              - is_littering: bool
              - all_scores: dict[label → probability]
        """
        if not self._ensure_loaded():
            return _clip_error_result(self._load_error or "CLIP not available")

        if labels is None:
            labels = CLIP_LABELS

        try:
            image = pil_image.convert("RGB")

            # Tokenise text + preprocess image
            inputs = self._processor(
                text=labels,
                images=image,
                return_tensors="pt",
                padding=True,
            )
            # Move all tensors to device
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.inference_mode():
                outputs = self._model(**inputs)

            logits = outputs.logits_per_image   # (1, num_labels)
            probs = logits.softmax(dim=1)[0].float().cpu().tolist()

            all_scores = {label: round(prob, 4) for label, prob in zip(labels, probs)}
            best_idx = max(range(len(probs)), key=lambda i: probs[i])
            best_label = labels[best_idx]
            best_conf = probs[best_idx]

            is_littering = (
                best_label in LITTERING_LABELS
                and best_conf >= CLIP_CONFIDENCE_THRESHOLD
            )

            logger.debug(
                f"[CLIP] Best: '{best_label[:60]}' @ {best_conf:.2%} "
                f"(littering={is_littering})"
            )

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
            return _clip_error_result(str(e))

    def is_available(self) -> bool:
        return self._ensure_loaded()


def _clip_error_result(error_msg: str) -> Dict:
    return {
        "label": "unknown",
        "confidence": 0.0,
        "is_littering": False,
        "all_scores": {},
        "device": "none",
        "error": error_msg,
    }


# ── Public CLIP API ───────────────────────────────────────────────────────────

def clip_verify_frame(
    pil_image: PILImage.Image,
    labels: Optional[List[str]] = None,
) -> Dict:
    """
    Verify whether a frame contains a littering event using CLIP zero-shot classification.

    Args:
        pil_image: PIL RGB image.
        labels:    Optional custom label list (defaults to CLIP_LABELS).

    Returns:
        dict {label, confidence, is_littering, all_scores, device, error}
    """
    return _CLIPVerifier.get().verify(pil_image, labels)


def is_clip_available() -> bool:
    """Return True if CLIP model is loaded and ready."""
    return _CLIPVerifier.get().is_available()


def get_clip_labels() -> List[str]:
    """Return the default zero-shot label set."""
    return list(CLIP_LABELS)


# ── Gemini Vision (optional rich description) ─────────────────────────────────

_BACKEND_DIR = Path(__file__).resolve().parent


def _get_api_key() -> Optional[str]:
    """Return Gemini API key from env var or .env file next to this file."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    env_file = _BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["GEMINI_API_KEY"] = key
                    return key
    return None


_gemini_client = None
_gemini_available = False
_gemini_load_attempted = False
_GEMINI_MODEL = "gemini-1.5-flash"


def _load_gemini() -> bool:
    global _gemini_client, _gemini_available, _gemini_load_attempted

    if _gemini_load_attempted:
        return _gemini_available

    _gemini_load_attempted = True

    api_key = _get_api_key()
    if not api_key:
        logger.warning(
            "[VLM] GEMINI_API_KEY not set. "
            "Add it to backend/.env to enable rich scene descriptions. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
        _gemini_available = False
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _gemini_client = genai.GenerativeModel(_GEMINI_MODEL)
        _gemini_available = True
        logger.info(f"[VLM] Gemini Vision ready (model: {_GEMINI_MODEL})")
    except Exception as e:
        logger.warning(f"[VLM] Failed to initialise Gemini: {e}")
        _gemini_available = False

    return _gemini_available


DEFAULT_PROMPT = (
    "You are an urban security AI assistant. Analyse this video frame and provide "
    "a concise, factual description of the scene. Focus on: "
    "1) Any person who appears to be throwing, dropping, or littering trash. "
    "2) Any visible waste, garbage, or foreign objects on the ground or in the air. "
    "3) General scene context (location type, number of people, vehicles). "
    "Keep the description under 3 sentences and be specific."
)


def describe_frame(
    pil_image: PILImage.Image,
    prompt: str = DEFAULT_PROMPT,
) -> str:
    """
    Generate a natural-language description using Gemini Vision (optional).
    Falls back to a CLIP-derived summary if Gemini is unavailable.
    """
    if _load_gemini():
        try:
            import google.generativeai as genai

            img = pil_image.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)

            image_part = {"mime_type": "image/jpeg", "data": buf.read()}

            response = _gemini_client.generate_content(
                [prompt, image_part],
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=256,
                    temperature=0.3,
                ),
            )

            text = response.text.strip() if response.text else ""
            if text:
                logger.debug(f"[VLM] Gemini description: {text[:80]}…")
                return text

        except Exception as e:
            logger.error(f"[VLM] describe_frame failed: {e}")

    # Fallback: use CLIP for a short structured summary
    result = clip_verify_frame(pil_image)
    if result.get("error"):
        return (
            "[VLM unavailable] Set GEMINI_API_KEY in backend/.env for rich descriptions. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    conf_pct = round(result["confidence"] * 100, 1)
    return (
        f"[CLIP analysis] Most likely scene: \"{result['label']}\" "
        f"(confidence {conf_pct}%). "
        f"{'Littering behaviour detected.' if result['is_littering'] else 'No confirmed littering detected.'}"
    )


def is_available() -> bool:
    """Return True if Gemini VLM is configured and reachable."""
    return _load_gemini()
