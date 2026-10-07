"""Shared composition root for CLI and web presentation adapters."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from application.query_service import QueryService
from application.speech_service import SpeechService
from application.image_service import ImageService
from application.search_service import SearchService
from application.ranking_service import RankingService
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from data.image_encoder import CLIPImageEncoder

ROOT = Path(__file__).resolve().parent


@dataclass
class Services:
    query: QueryService
    speech: SpeechService
    image: ImageService
    search: SearchService


@lru_cache(maxsize=1)
def _build_image_resources() -> tuple[CLIPImageEncoder, VectorIndex]:
    """Load the model and infer catalog features once per Python process."""
    products = ProductRepository(ROOT / "datasets/products.json").all_products()
    encoder = CLIPImageEncoder(ROOT / "models/clip-vit-base-patch32-vision-int8.onnx")
    vectors = encoder.encode_paths([ROOT / product["image"] for product in products])
    return encoder, VectorIndex.from_embeddings({
        product["product_id"]: vector for product, vector in zip(products, vectors)
    })


def build_services() -> Services:
    """Load and validate datasets once per adapter instance."""
    products = ProductRepository(ROOT / "datasets/products.json")
    encoder, vectors = _build_image_resources()
    samples = [f"datasets/images/query_{letter}.png" for letter in "abc"]
    image = ImageService(ROOT, encoder, samples)
    return Services(QueryService(), SpeechService(), image,
                    SearchService(products, vectors, RankingService()))
