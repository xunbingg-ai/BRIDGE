import asyncio
from types import SimpleNamespace

import pytest

from app.services.scoring.scorer import (
    InvalidScoreOutputError,
    NoRubricError,
    Scorer,
)


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeClient:
    def __init__(self, content: str) -> None:
        self.completions = FakeCompletions(content)

    @property
    def chat(self):
        return self


def test_score_parses_valid_json():
    client = FakeClient(
        '{"score": 72, "feedback": "Good history", "reference_answer": "Stress-related chest pain."}'
    )
    scorer = Scorer(client)  # type: ignore[arg-type]
    result = asyncio.run(
        scorer.score(
            {"case_summary": "x", "working_diagnosis": "y",
             "structured_questions": [], "suggested_answers": []},
            [{"question_id": 1, "answer": "z"}],
            {"max_score": 100, "criteria": []},
        )
    )
    assert result.score == 72
    assert result.feedback == "Good history"
    assert client.completions.kwargs["response_format"] == {"type": "json_object"}


def test_score_refuses_without_rubric():
    scorer = Scorer(FakeClient("{}"))  # type: ignore[arg-type]
    with pytest.raises(NoRubricError):
        asyncio.run(
            scorer.score(
                {"case_summary": "x"}, [{"question_id": 1, "answer": "z"}], None
            )
        )


def test_score_rejects_invalid_json():
    scorer = Scorer(FakeClient("not json"))  # type: ignore[arg-type]
    with pytest.raises(InvalidScoreOutputError):
        asyncio.run(
            scorer.score(
                {"case_summary": "x"},
                [{"question_id": 1, "answer": "z"}],
                {"max_score": 100, "criteria": []},
            )
        )
