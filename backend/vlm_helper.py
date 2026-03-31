"""
vlm_helper.py — nanoVLM semantic scene description wrapper.

Uses the local VLMnano/nanoVLM codebase already present in the project.
Downloads weights from HuggingFace Hub on first run (cached after that).
Falls back gracefully to a placeholder if loading fails.
"""

import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Path setup ──────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_NANOVLM_DIR = _PROJECT_ROOT / "VLMnano" / "nanoVLM"

if str(_NANOVLM_DIR) not in sys.path:
    sys.path.insert(0, str(_NANOVLM_DIR))


# ── Lazy model globals ───────────────────────────────────────────────────────
_vlm_model = None
_vlm_tokenizer = None
_vlm_image_processor = None
_vlm_device = None
_vlm_available = False
_vlm_load_attempted = False


def _load_vlm():
    """Load nanoVLM model (once). Sets _vlm_available flag."""
    global _vlm_model, _vlm_tokenizer, _vlm_image_processor
    global _vlm_device, _vlm_available, _vlm_load_attempted

    if _vlm_load_attempted:
        return _vlm_available

    _vlm_load_attempted = True

    try:
        import torch
        from models.vision_language_model import VisionLanguageModel
        from data.processors import get_tokenizer, get_image_processor

        if torch.cuda.is_available():
            _vlm_device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _vlm_device = torch.device("mps")
        else:
            _vlm_device = torch.device("cpu")

        logger.info(f"[VLM] Loading nanoVLM on device: {_vlm_device}")

        HF_MODEL = "lusxvr/nanoVLM-230M-8k"
        _vlm_model = VisionLanguageModel.from_pretrained(HF_MODEL).to(_vlm_device)
        _vlm_model.eval()

        cfg = _vlm_model.cfg
        _vlm_tokenizer = get_tokenizer(
            cfg.lm_tokenizer, cfg.vlm_extra_tokens, cfg.lm_chat_template
        )

        resize_to_max = getattr(cfg, "resize_to_max_side_len", False)
        _vlm_image_processor = get_image_processor(
            cfg.max_img_size, cfg.vit_img_size, resize_to_max
        )

        _vlm_available = True
        logger.info("[VLM] nanoVLM loaded successfully.")

    except Exception as e:
        logger.warning(f"[VLM] Failed to load nanoVLM: {e}. Descriptions will be skipped.")
        _vlm_available = False

    return _vlm_available


def describe_frame(pil_image, prompt: str = "Describe what is happening in this scene. Focus on any person throwing or littering trash.") -> str:
    """
    Generate a natural-language description for a PIL image frame.

    Args:
        pil_image: PIL.Image.Image (RGB)
        prompt: text prompt for the VLM

    Returns:
        str description, or a fallback string if VLM is unavailable.
    """
    if not _load_vlm():
        return "[VLM unavailable — install dependencies or check HuggingFace connectivity]"

    try:
        import torch
        from data.processors import get_image_string

        img = pil_image.convert("RGB")
        processed_image, splitted_image_ratio = _vlm_image_processor(img)

        # If no global_image_token, strip the global patch
        if (
            not hasattr(_vlm_tokenizer, "global_image_token")
            and splitted_image_ratio[0] * splitted_image_ratio[1] == len(processed_image) - 1
        ):
            processed_image = processed_image[1:]

        image_string = get_image_string(
            _vlm_tokenizer, [splitted_image_ratio], _vlm_model.cfg.mp_image_token_length
        )

        messages = [{"role": "user", "content": image_string + prompt}]
        encoded = _vlm_tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        )
        
        if isinstance(encoded, dict) and "input_ids" in encoded:
            tokens = encoded["input_ids"].to(_vlm_device)
        else:
            tokens = encoded.to(_vlm_device)
            
        if len(tokens.shape) == 1:
            tokens = tokens.unsqueeze(0)
            
        img_t = processed_image.to(_vlm_device)

        with torch.inference_mode():
            gen = _vlm_model.generate(tokens, img_t, max_new_tokens=200)

        text = _vlm_tokenizer.batch_decode(gen, skip_special_tokens=True)[0]
        return text.strip()

    except Exception as e:
        logger.error(f"[VLM] describe_frame failed: {e}")
        return f"[VLM error: {e}]"


def is_available() -> bool:
    """Return True if VLM can be used (triggers lazy load)."""
    return _load_vlm()
