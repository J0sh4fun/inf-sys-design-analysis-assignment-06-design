"""Encode catalog, sample, and uploaded images with a pretrained model."""

from pathlib import Path

from data.image_encoder import CLIPImageEncoder


class ImageService:
    def __init__(self, root: Path, encoder: CLIPImageEncoder, samples: list[str]):
        self.root, self.encoder, self.samples = root.resolve(), encoder, samples

    def encode(self, image_path: str) -> list[float]:
        if not isinstance(image_path, str) or not image_path.strip():
            raise ValueError("Image path must not be empty.")
        path = Path(image_path.strip())
        path = (path if path.is_absolute() else self.root / path).resolve()
        return self.encoder.encode_paths([path])[0]

    def encode_upload(self, content: bytes) -> list[float]:
        return self.encoder.encode_bytes(content)

    def supported_images(self) -> list[str]:
        return self.samples.copy()

    @property
    def model_name(self) -> str:
        return self.encoder.model_name
