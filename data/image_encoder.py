"""Local image feature extraction with a pretrained CLIP vision encoder."""

from io import BytesIO
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps, UnidentifiedImageError


class CLIPImageEncoder:
    """Encode images as normalized CLIP ViT-B/32 semantic vectors."""

    model_name = "CLIP ViT-B/32 (OpenAI, ONNX INT8)"
    dimension = 512

    def __init__(self, model_path: Path):
        if not model_path.is_file():
            raise FileNotFoundError(f"Missing pretrained model: {model_path}")
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    @staticmethod
    def _prepare(image: Image.Image) -> np.ndarray:
        image = ImageOps.fit(image.convert("RGB"), (224, 224), method=Image.Resampling.BICUBIC)
        array = np.asarray(image, dtype=np.float32) / 255.0
        mean = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
        std = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
        return ((array - mean) / std).transpose(2, 0, 1)

    def _infer(self, batch: np.ndarray) -> list[list[float]]:
        vectors = self.session.run(None, {self.input_name: batch})[0].astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError("The pretrained model returned an empty image feature.")
        return (vectors / norms).tolist()

    def encode_paths(self, paths: list[Path]) -> list[list[float]]:
        prepared = []
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(f"Missing image: {path}")
            with Image.open(path) as image:
                prepared.append(self._prepare(image))
        # The INT8 graph uses dynamic quantization. Keep batch size identical to
        # uploaded-query inference so catalog and query vectors are comparable.
        return [self._infer(np.expand_dims(item, axis=0))[0] for item in prepared]

    def encode_bytes(self, content: bytes) -> list[float]:
        try:
            with Image.open(BytesIO(content)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Unsupported image format.")
                if image.width * image.height > 40_000_000:
                    raise ValueError("Image dimensions are too large.")
                image.verify()
            with Image.open(BytesIO(content)) as image:
                prepared = self._prepare(image)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("The uploaded file is not a valid supported image.") from exc
        return self._infer(np.expand_dims(prepared, axis=0))[0]
