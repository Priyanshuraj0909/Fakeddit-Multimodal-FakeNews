"""Shared local-only CLIP preprocessing and inference; optional heavy dependencies."""
from pathlib import Path
from importlib.metadata import version
import numpy as np
from ml.utils.contracts import encoder_fingerprint, PREPROCESSING


class ClipEncoder:
    def __init__(self, directory, expected_fingerprint=None, expected_packages=None):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.packages = {name: version(name) for name in ("torch", "transformers")}
        if expected_packages and self.packages != expected_packages:
            raise ValueError("Encoder dependency versions differ from the training environment")
        directory = Path(directory)
        self.fingerprint = encoder_fingerprint(directory)
        if expected_fingerprint and self.fingerprint != expected_fingerprint:
            raise ValueError("Encoder snapshot differs from the training checkpoint")
        # CPU is portable; no network requests or automatic weight downloads.
        self.torch = torch
        self.processor = CLIPProcessor.from_pretrained(str(directory), local_files_only=True)
        self.model = CLIPModel.from_pretrained(str(directory), local_files_only=True, use_safetensors=True).to("cpu").eval()

    def _normalize(self, tensor):
        array = tensor.detach().cpu().numpy().astype(np.float32)
        norm = np.linalg.norm(array, axis=1, keepdims=True)
        if not np.isfinite(array).all() or (norm <= 0).any():
            raise ValueError("Encoder produced invalid features")
        return array / norm

    def encode_image(self, image):
        inputs = self.processor(images=image, return_tensors="pt")
        with self.torch.inference_mode():
            return self._normalize(self.model.get_image_features(**inputs))

    def encode_text(self, text):
        inputs = self.processor(text=[text.strip()], return_tensors="pt", padding=True,
                                truncation=True, max_length=self.model.config.text_config.max_position_embeddings)
        with self.torch.inference_mode():
            return self._normalize(self.model.get_text_features(**inputs))

    def encode(self, text, image):
        return self.encode_image(image), self.encode_text(text)
