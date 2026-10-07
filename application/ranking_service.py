"""Deterministic ranking, separate from candidate retrieval."""


class RankingService:
    @staticmethod
    def validate_top_k(top_k: int) -> None:
        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

    def rank(self, candidates: list[dict], top_k: int = 5) -> list[dict]:
        self.validate_top_k(top_k)
        return sorted(candidates, key=lambda item: (-item["score"], item["product"]["product_id"]))[:top_k]
