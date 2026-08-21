from __future__ import annotations

import os
import threading
from typing import Sequence

import numpy as np

from .exceptions import SearchServiceUnavailable


DEFAULT_MODEL_NAME = "ViT-B-32"
DEFAULT_PRETRAINED = "openai"
_encoder = None
_encoder_lock = threading.Lock()


class ClipTextEncoder:
    """Lazy OpenCLIP text encoder compatible with clip-features-32."""

    def __init__(self, device: str | None = None):
        try:
            import open_clip
            import torch
        except ImportError as exc:
            raise SearchServiceUnavailable(
                "Thiếu torch/open_clip_torch. Cài BE/requirements.txt trước khi search."
            ) from exc

        self.torch = torch
        self.device = device or os.getenv("KIS_DEVICE") or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model_name = os.getenv("KIS_CLIP_MODEL", DEFAULT_MODEL_NAME)
        self.pretrained = os.getenv("KIS_CLIP_PRETRAINED", DEFAULT_PRETRAINED)
        try:
            self.model, _, _ = open_clip.create_model_and_transforms(
                self.model_name,
                pretrained=self.pretrained,
            )
            self.tokenizer = open_clip.get_tokenizer(self.model_name)
        except Exception as exc:
            raise SearchServiceUnavailable(
                "Không tải được CLIP text encoder. Kiểm tra model cache/kết nối mạng "
                f"({self.model_name}, {self.pretrained})."
            ) from exc
        self.model.to(self.device).eval()

    def encode_text(self, text: str) -> np.ndarray:
        return self.encode_texts([text])[0]

    def encode_texts(self, texts: Sequence[str], batch_size: int = 64) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        output = []
        with self.torch.inference_mode():
            for start in range(0, len(texts), batch_size):
                tokens = self.tokenizer(list(texts[start : start + batch_size])).to(self.device)
                features = self.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True).clamp_min(1e-12)
                output.append(features.cpu().numpy().astype(np.float32))
        return np.concatenate(output, axis=0)


def get_encoder() -> ClipTextEncoder:
    global _encoder
    if _encoder is None:
        with _encoder_lock:
            if _encoder is None:
                _encoder = ClipTextEncoder()
    return _encoder


def reset_encoder_cache() -> None:
    global _encoder
    with _encoder_lock:
        _encoder = None
