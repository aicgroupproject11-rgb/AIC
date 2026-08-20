import torch
import open_clip
from PIL import Image
import numpy as np

_MODEL_NAME = "ViT-B-32"
_PRETRAINED = "openai"

_encoder = None


class ClipEncoder:
    def __init__(self, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            _MODEL_NAME, pretrained=_PRETRAINED
        )
        self.tokenizer = open_clip.get_tokenizer(_MODEL_NAME)
        self.model.to(self.device).eval()

    @torch.no_grad()
    def encode_image(self, image_path: str) -> np.ndarray:
        img = self.preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(self.device)
        feat = self.model.encode_image(img)
        feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().numpy()[0].astype("float32")

    @torch.no_grad()
    def encode_text(self, text: str) -> np.ndarray:
        tokens = self.tokenizer([text]).to(self.device)
        feat = self.model.encode_text(tokens)
        feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().numpy()[0].astype("float32")


def get_encoder() -> ClipEncoder:
    global _encoder
    if _encoder is None:
        _encoder = ClipEncoder()
    return _encoder