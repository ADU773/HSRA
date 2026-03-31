import sys
import os
from pathlib import Path
import torch

_BACKEND_DIR = Path("c:/Users/aadva/OneDrive/Documents/Model - Copy/backend")
_PROJECT_ROOT = _BACKEND_DIR.parent
_NANOVLM_DIR = _PROJECT_ROOT / "VLMnano" / "nanoVLM"

if str(_NANOVLM_DIR) not in sys.path:
    sys.path.insert(0, str(_NANOVLM_DIR))

from models.vision_language_model import VisionLanguageModel
from data.processors import get_tokenizer

HF_MODEL = "lusxvr/nanoVLM-230M-8k"
cfg = VisionLanguageModel.from_pretrained(HF_MODEL).cfg
tokenizer = get_tokenizer(cfg.lm_tokenizer, cfg.vlm_extra_tokens, cfg.lm_chat_template)

messages = [{"role": "user", "content": "<image>Describe this"}]
try:
    encoded1 = tokenizer.apply_chat_template([messages], tokenize=True, add_generation_prompt=True)
    print("Type of encoded1:", type(encoded1))
    if isinstance(encoded1, list) and len(encoded1) > 0:
        print("Type of encoded1[0]:", type(encoded1[0]))
except Exception as e:
    print("Error 1:", e)

try:
    encoded2 = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
    print("Type of encoded2:", type(encoded2))
    if isinstance(encoded2, dict):
        print("Keys:", encoded2.keys())
except Exception as e:
    print("Error 2:", e)
