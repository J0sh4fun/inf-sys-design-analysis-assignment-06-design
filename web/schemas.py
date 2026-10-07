"""Strict request structure; query normalization stays in application services."""

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    top_k: int = Field(default=5, gt=0)


class TextRequest(SearchRequest):
    text: str


class VoiceRequest(SearchRequest):
    transcript: str


class ImageRequest(SearchRequest):
    sample_id: str
