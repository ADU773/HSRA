"""
vlm_helper.py — Google Gemini Vision semantic scene description.

Uses the Gemini API (gemini-1.5-flash, free tier) for scene analysis.

Set the API key via environment variable:
    GEMINI_API_KEY=<your_key>

Or place it in a file called `.env` next to this file.

Get a free API key at: https://aistudio.google.com/app/apikey
"""

import os
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── API Key resolution ────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent

def _get_api_key() -> str | None:
    """Return Gemini API key from env var or .env file next to this file."""
    # 1. Check environment variable (set externally or via the .env loader below)
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    # 2. Try reading from a .env file in the backend directory
    env_file = _BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["GEMINI_API_KEY"] = key  # cache in env
                    return key
    return None


# ── Lazy client globals ───────────────────────────────────────────────────────
_gemini_client = None
_gemini_available = False
_gemini_load_attempted = False
_GEMINI_MODEL = "gemini-1.5-flash"   # free-tier quota model


def _load_gemini():
    """Initialise the Gemini client (once). Sets _gemini_available flag."""
    global _gemini_client, _gemini_available, _gemini_load_attempted

    if _gemini_load_attempted:
        return _gemini_available

    _gemini_load_attempted = True

    api_key = _get_api_key()
    if not api_key:
        logger.warning(
            "[VLM] GEMINI_API_KEY not set. "
            "Add it to backend/.env or set the environment variable. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
        _gemini_available = False
        return False

    try:
        import google.generativeai as genai   # noqa
        genai.configure(api_key=api_key)
        _gemini_client = genai.GenerativeModel(_GEMINI_MODEL)
        # Quick connectivity test (list models doesn't cost quota)
        _gemini_available = True
        logger.info(f"[VLM] Gemini Vision ready (model: {_GEMINI_MODEL})")
    except Exception as e:
        logger.warning(f"[VLM] Failed to initialise Gemini: {e}")
        _gemini_available = False

    return _gemini_available


# ── Public API ────────────────────────────────────────────────────────────────

DEFAULT_PROMPT = (
    "You are an urban security AI assistant. Analyse this video frame and provide "
    "a concise, factual description of the scene. Focus on: "
    "1) Any person who appears to be throwing, dropping, or littering trash. "
    "2) Any visible waste, garbage, or foreign objects on the ground or in the air. "
    "3) General scene context (location type, number of people, vehicles). "
    "Keep the description under 3 sentences and be specific."
)


def describe_frame(
    pil_image,
    prompt: str = DEFAULT_PROMPT,
) -> str:
    """
    Generate a natural-language description for a PIL image frame using Gemini Vision.

    Args:
        pil_image: PIL.Image.Image (RGB)
        prompt: Instruction for the VLM

    Returns:
        str description, or informative fallback if Gemini is unavailable.
    """
    if not _load_gemini():
        return (
            "[VLM unavailable] Set GEMINI_API_KEY in backend/.env "
            "to enable scene descriptions. Get a free key at: "
            "https://aistudio.google.com/app/apikey"
        )

    try:
        import google.generativeai as genai
        from PIL import Image as PILImage

        img = pil_image.convert("RGB")

        # Convert PIL image to bytes for the API
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)

        image_part = {
            "mime_type": "image/jpeg",
            "data": buf.read(),
        }

        response = _gemini_client.generate_content(
            [prompt, image_part],
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=256,
                temperature=0.3,
            ),
        )

        text = response.text.strip() if response.text else ""
        if not text:
            return "[VLM returned empty response]"

        logger.debug(f"[VLM] Gemini description: {text[:80]}…")
        return text

    except Exception as e:
        logger.error(f"[VLM] describe_frame failed: {e}")
        return f"[VLM error: {e}]"


def is_available() -> bool:
    """Return True if Gemini VLM is configured and reachable."""
    return _load_gemini()
