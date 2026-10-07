"""Construct the common baseline query schema."""

from data.vector_index import validate_vector
from application.text_normalization import normalize_search_text


class QueryService:
    @staticmethod
    def _text_query(text: str, mode: str) -> dict:
        if not isinstance(text, str):
            raise ValueError("Search text must be a string.")
        normalized = normalize_search_text(text)
        if not normalized:
            raise ValueError("Search text must not be empty.")
        return {"type": mode, "text": normalized, "embedding": None, "filters": {}}

    def text_query(self, text: str) -> dict:
        return self._text_query(text, "text")

    def voice_query(self, transcript: str) -> dict:
        return self._text_query(transcript, "voice")

    def image_query(self, embedding: list[float]) -> dict:
        return {"type": "image", "text": "", "embedding": validate_vector(embedding), "filters": {}}
