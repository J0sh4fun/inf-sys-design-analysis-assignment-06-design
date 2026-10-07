"""Load and validate artificial product vectors."""

import json
import math
from pathlib import Path


def validate_vector(vector: object, dimension: int | None = None) -> list[float]:
    """Reject empty, nonnumeric, nonfinite, zero, or mismatched vectors."""
    if not isinstance(vector, (list, tuple)) or not vector:
        raise ValueError("Embedding must be a nonempty list of numbers.")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in vector):
        raise ValueError("Embedding values must be numbers.")
    values = [float(x) for x in vector]
    if not all(math.isfinite(x) for x in values):
        raise ValueError("Embedding values must be finite.")
    if dimension is not None and len(values) != dimension:
        raise ValueError(f"Embedding must have {dimension} dimensions.")
    if not any(values):
        raise ValueError("Embedding must have nonzero norm.")
    return values


class VectorIndex:
    def __init__(self, path: Path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not raw:
            raise ValueError("Product embedding mapping must be nonempty.")
        self._vectors: dict[int, list[float]] = {}
        self.dimension = len(validate_vector(next(iter(raw.values()))))
        for key, value in raw.items():
            product_id = int(key)  # JSON object keys are strings.
            if product_id in self._vectors:
                raise ValueError("Duplicate vector product ID.")
            self._vectors[product_id] = validate_vector(value, self.dimension)

    def all_embeddings(self) -> dict[int, list[float]]:
        return {key: value.copy() for key, value in self._vectors.items()}

    @classmethod
    def from_embeddings(cls, embeddings: dict[int, list[float]]) -> "VectorIndex":
        if not embeddings:
            raise ValueError("Product embedding mapping must be nonempty.")
        instance = cls.__new__(cls)
        instance.dimension = len(validate_vector(next(iter(embeddings.values()))))
        instance._vectors = {
            int(product_id): validate_vector(vector, instance.dimension)
            for product_id, vector in embeddings.items()
        }
        return instance
