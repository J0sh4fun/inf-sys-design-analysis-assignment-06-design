"""Retrieve and score candidates, then delegate their ranking."""

import math
import re

from application.ranking_service import RankingService
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex, validate_vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left = validate_vector(left)
    right = validate_vector(right, len(left))
    # Scale first to avoid overflow with very large finite inputs.
    left_scale, right_scale = max(map(abs, left)), max(map(abs, right))
    left = [x / left_scale for x in left]
    right = [x / right_scale for x in right]
    denominator = math.sqrt(sum(x*x for x in left)) * math.sqrt(sum(x*x for x in right))
    return max(-1.0, min(1.0, sum(a*b for a, b in zip(left, right)) / denominator))


class SearchService:
    def __init__(self, products: ProductRepository, vectors: VectorIndex, ranking: RankingService):
        self.products, self.vectors, self.ranking = products, vectors, ranking
        if {p["product_id"] for p in products.all_products()} != set(vectors.all_embeddings()):
            raise ValueError("Product and vector IDs must match exactly.")

    def search(self, query: dict, top_k: int = 5) -> list[dict]:
        self.ranking.validate_top_k(top_k)
        if query.get("filters") != {}:
            raise ValueError("Filters are not supported in this baseline.")
        mode = query.get("type")
        if mode in ("text", "voice"):
            if not isinstance(query.get("text"), str) or not query["text"].strip():
                raise ValueError("Search text must not be empty.")
            candidates = self.retrieve_text_candidates(query, self.products.all_products())
        elif mode == "image":
            candidates = self.retrieve_image_candidates(query.get("embedding"))
        else:
            raise ValueError("Search type must be text, voice, or image.")
        return self.ranking.rank(candidates, top_k)

    def retrieve_text_candidates(self, query: dict, products: list[dict]) -> list[dict]:
        tokens = set(re.findall(r"\w+", query["text"].lower()))
        candidates = []
        for product in products:
            text = " ".join(product[field] for field in ("name", "category", "color", "description"))
            score = len(tokens & set(re.findall(r"\w+", text.lower())))
            if score > 0:
                candidates.append({"product": product, "score": float(score)})
        return candidates

    def retrieve_image_candidates(self, embedding: list[float]) -> list[dict]:
        embedding = validate_vector(embedding, self.vectors.dimension)
        candidates = []
        for product_id, vector in self.vectors.all_embeddings().items():
            product = self.products.get_by_id(product_id)
            if product is None:
                raise ValueError(f"Indexed product {product_id} does not exist.")
            candidates.append({"product": product, "score": cosine_similarity(embedding, vector)})
        return candidates

    def get_product(self, product_id: int) -> dict | None:
        return self.products.get_by_id(product_id)

    def list_products(self) -> list[dict]:
        return self.products.all_products()
