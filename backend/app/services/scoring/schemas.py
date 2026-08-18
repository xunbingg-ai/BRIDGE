"""Output schema for AI scoring."""
from pydantic import BaseModel, Field


class ScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    feedback: str
    reference_answer: str
