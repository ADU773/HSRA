"""
vlm_helper.py — Local generative VLM using Qwen2-VL-2B-Instruct.

Replaces the old CLIP discriminative approach with a real vision-language model
that reads the scene and generates natural language descriptions.

Model: Qwen/Qwen2-VL-2B-Instruct
  • ~2B parameters, fits in 4 GB VRAM with 4-bit quantization (bitsandbytes)
  • Fully local — no API keys, no external services after first download
  • Downloads once to ~/.cache/huggingface on first run

Public API (unchanged — analyzer.py needs no edits):
  describe_frame(pil_image, prompt="")  → str
  clip_verify_frame(pil_image, labels)  → dict
  is_available()                        → bool
  is_clip_available()                   → bool
  get_clip_labels()                     → list[str]
"""

import logging
from typing import Dict, List, Optional

import torch
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ── Model config ───────────────────────────────────────────────────────────────

VLM_MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"

# Prompt sent for every scene description
DESCRIBE_PROMPT = (
    "You are an AI assistant analyzing a CCTV or dashcam video frame for a waste "
    "management monitoring system. Describe what is happening in this image in 2-3 "
    "concise sentences. Focus on:\n"
    "1. Whether any person is throwing, dropping, or littering trash/garbage.\n"
    "2. The type of waste or objects visible.\n"
    "3. The location, time of day, and number of people/vehicles present.\n"
    "Be factual and specific. If no littering is visible, say so clearly."
)

# Prompt for binary littering verification
VERIFY_PROMPT = (
    "Look at this image carefully. Is a person actively throwing, dropping, or "
    "littering any garbage or trash? Reply with ONLY one of these exact phrases:\n"
    "- YES, littering is occurring\n"
    "- NO, no littering visible\n"
    "Then in one sentence explain what you see."
)

# Kept for backward compatibility with analyzer.py fields
CLIP_LABELS: List[str] = [
    "a person throwing or littering trash in public",
    "a person dropping garbage or waste on the ground",
    "a person walking normally without any littering",
    "an empty street or road with no people",
    "garbage or trash lying on the ground",
]

LITTERING_KEYWORDS = {
    "throwing", "littering", "dropping", "discarding", "dumping",
    "tossing", "yes, littering"
}

CONFIDENCE_IF_YES = 0.92
CONFIDENCE_IF_NO  = 0.08


# ── Device selection ───────────────────────────────────────────────────────────

def _get_device() -> str:
    if torch.cuda.is_available():
        logger.info("[VLM] CUDA GPU detected — running on GPU.")
        return "cuda"
    logger.info("[VLM] No GPU found — falling back to CPU (will be slow).")
    return "cpu"


# ── Singleton VLM wrapper ──────────────────────────────────────────────────────

class _VLMEngine:
    _instance: Optional["_VLMEngine"] = None

    def __init__(self):
        self._model = None
        self._processor = None
        self._device = _get_device()
        self._loaded = False
        self._load_error: Optional[str] = None

    @classmethod
    def get(cls) -> "_VLMEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if self._load_error:
            return False
        try:
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

            logger.info(f"[VLM] Loading {VLM_MODEL_ID} …")
            logger.info(f"[VLM] Device: {self._device.upper()}")

            # Build quantization config only on GPU (bitsandbytes not needed on CPU)
            model_kwargs: dict = {
                "torch_dtype": torch.float16 if self._device == "cuda" else torch.float32,
                "device_map": "auto" if self._device == "cuda" else None,
            }

            if self._device == "cuda":
                try:
                    from transformers import BitsAndBytesConfig
                    bnb_cfg = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                    model_kwargs["quantization_config"] = bnb_cfg
                    logger.info("[VLM] 4-bit NF4 quantization enabled (bitsandbytes).")
                except ImportError:
                    logger.warning("[VLM] bitsandbytes not found — loading in fp16 without 4-bit quant.")

            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                VLM_MODEL_ID, **model_kwargs
            )

            if self._device == "cpu":
                self._model = self._model.to("cpu")

            self._model.eval()

            # min_pixels / max_pixels control image patch count → VRAM usage
            self._processor = AutoProcessor.from_pretrained(
                VLM_MODEL_ID,
                min_pixels=256 * 28 * 28,
                max_pixels=512 * 28 * 28,
            )

            self._loaded = True
            logger.info(f"[VLM] {VLM_MODEL_ID} ready on {self._device.upper()}.")
            return True

        except Exception as e:
            self._load_error = str(e)
            logger.error(f"[VLM] Failed to load: {e}", exc_info=True)
            return False

    # ── Core inference ─────────────────────────────────────────────────────

    def _run(self, pil_image: PILImage.Image, prompt_text: str, max_new_tokens: int = 200) -> str:
        """Run a single image+text prompt through Qwen2-VL. Returns generated text."""
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {"type": "text",  "text": prompt_text},
                    ],
                }
            ]

            # Build chat template
            text_input = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # Process inputs — handles both image patches and text tokens
            inputs = self._processor(
                text=[text_input],
                images=[pil_image],
                padding=True,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

            with torch.inference_mode():
                output_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,          # greedy — deterministic & faster
                    temperature=None,
                    top_p=None,
                )

            # Trim the input tokens from output
            input_len = inputs["input_ids"].shape[1]
            generated_ids = output_ids[0][input_len:]
            generated_text = self._processor.decode(
                generated_ids, skip_special_tokens=True
            ).strip()

            return generated_text

        except Exception as e:
            logger.error(f"[VLM] _run() error: {e}", exc_info=True)
            return f"[VLM error: {e}]"

    # ── Public methods ─────────────────────────────────────────────────────

    def describe(self, pil_image: PILImage.Image) -> str:
        """
        Generate a natural-language scene description using Qwen2-VL.
        Returns a 2-3 sentence paragraph about what is happening in the frame.
        """
        if not self._ensure_loaded():
            return f"[VLM unavailable] {self._load_error}"

        image = pil_image.convert("RGB")
        description = self._run(image, DESCRIBE_PROMPT, max_new_tokens=220)
        logger.debug(f"[VLM-describe] {description[:100]}…")
        return description

    def verify(
        self,
        pil_image: PILImage.Image,
        labels: Optional[List[str]] = None,   # kept for API compat; not used
    ) -> Dict:
        """
        Ask Qwen2-VL: 'Is a person littering in this frame?'
        Returns a dict compatible with the old clip_verify_frame() format:
          { label, confidence, is_littering, all_scores, device, error }
        """
        if not self._ensure_loaded():
            return _error_result(self._load_error or "VLM not available")

        try:
            image = pil_image.convert("RGB")
            answer = self._run(image, VERIFY_PROMPT, max_new_tokens=80)
            answer_lower = answer.lower()

            is_littering = any(kw in answer_lower for kw in LITTERING_KEYWORDS)
            confidence   = CONFIDENCE_IF_YES if is_littering else CONFIDENCE_IF_NO

            logger.info(f"[VLM-verify] '{answer[:80]}' → littering={is_littering} conf={confidence:.0%}")

            return {
                "label":        answer,
                "confidence":   confidence,
                "is_littering": is_littering,
                "all_scores":   {"vlm_answer": answer},
                "device":       str(self._model.device) if self._model else self._device,
                "error":        None,
            }

        except Exception as e:
            logger.error(f"[VLM] verify() failed: {e}", exc_info=True)
            return _error_result(str(e))

    def is_available(self) -> bool:
        return self._ensure_loaded()


# ── Helper ─────────────────────────────────────────────────────────────────────

def _error_result(msg: str) -> Dict:
    return {
        "label": "unknown",
        "confidence": 0.0,
        "is_littering": False,
        "all_scores": {},
        "device": "none",
        "error": msg,
    }


# ── Public functions (same API as before — analyzer.py unchanged) ──────────────

def describe_frame(
    pil_image: PILImage.Image,
    prompt: str = "",   # kept for compatibility; the built-in prompt is used
) -> str:
    """
    Generate a real, generative scene description using Qwen2-VL-2B-Instruct.
    Fully local — GPU-accelerated, no API keys required.
    """
    return _VLMEngine.get().describe(pil_image)


def clip_verify_frame(
    pil_image: PILImage.Image,
    labels: Optional[List[str]] = None,
) -> Dict:
    """
    Verify whether littering is occurring using Qwen2-VL (replaces CLIP).
    Returns the same dict schema so analyzer.py needs no changes.
    """
    return _VLMEngine.get().verify(pil_image, labels)


def is_clip_available() -> bool:
    """Backward-compatible alias."""
    return _VLMEngine.get().is_available()


def is_available() -> bool:
    """Return True if the VLM is loaded and ready."""
    return _VLMEngine.get().is_available()


def get_clip_labels() -> List[str]:
    """Return the legacy label list (kept for compatibility)."""
    return list(CLIP_LABELS)
