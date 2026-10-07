"""Map supported sample paths to fixed embeddings; no image inference."""

import json
from pathlib import Path

from data.vector_index import validate_vector


class ImageStorage:
    def __init__(self, root: Path, mapping_path: Path, dimension: int):
        self.root = root.resolve()
        raw = json.loads(mapping_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not raw:
            raise ValueError("Query embedding mapping must be nonempty.")
        self._embeddings = {key: validate_vector(value, dimension) for key, value in raw.items()}
        self._paths = {self._resolve(key): key for key in self._embeddings}
        for path in self._paths:
            if not path.is_file():
                raise FileNotFoundError(f"Missing sample image: {path}")

    def _resolve(self, path: str) -> Path:
        candidate = Path(path)
        return (candidate if candidate.is_absolute() else self.root / candidate).resolve()

    def supported_paths(self) -> list[str]:
        return list(self._embeddings)

    def get_embedding(self, image_path: str) -> list[float]:
        if not isinstance(image_path, str) or not image_path.strip():
            raise ValueError("Image path must not be empty.")
        path = self._resolve(image_path.strip())
        if path not in self._paths:
            raise ValueError("Unsupported image path. List the supported query images.")
        if not path.is_file():
            raise FileNotFoundError(f"Missing sample image: {path}")
        return self._embeddings[self._paths[path]].copy()
