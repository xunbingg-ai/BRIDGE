"""AI scoring module — practice reference score from the rubric.

Refuses to score cases without a rubric (requirements section 9; CONTEXT.md
Rubric definition). Output is validated as ScoreResult.
"""
from __future__ import annotations

import json
from pathlib import Path

from openai import AsyncOpenAI

from app.services.llm.client import model_name
from app.services.scoring.schemas import ScoreResult

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


class NoRubricError(RuntimeError):
    """Raised when a case has no rubric and a score is requested."""


class InvalidScoreOutputError(RuntimeError):
    """Raised when the LLM output is not valid ScoreResult JSON."""


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def build_scoring_messages(
    case: dict, student_answers: list[dict], rubric: dict
) -> list[dict]:
    qa = "\n".join(
        f"Q{idx + 1}: {q.get('question', '')}\nSuggested: {a.get('answer', '')}"
        for idx, (q, a) in enumerate(
            zip(case.get("structured_questions", []), case.get("suggested_answers", []))
        )
    )
    answers = "\n".join(
        f"Q{item.get('question_id', idx + 1)}: {item.get('answer', '')}"
        for idx, item in enumerate(student_answers)
    )
    user = (
        load_prompt("scoring_user.txt")
        .replace("{{SUMMARY}}", case.get("case_summary", ""))
        .replace("{{WORKING_DIAGNOSIS}}", case.get("working_diagnosis", ""))
        .replace("{{QUESTIONS_AND_ANSWERS}}", qa)
        .replace("{{RUBRIC}}", json.dumps(rubric, ensure_ascii=False))
        .replace("{{STUDENT_ANSWERS}}", answers)
    )
    return [
        {"role": "system", "content": load_prompt("scoring_system.txt")},
        {"role": "user", "content": user},
    ]


class Scorer:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def score(
        self, case: dict, student_answers: list[dict], rubric: dict | None
    ) -> ScoreResult:
        if not rubric:
            raise NoRubricError("this case has no rubric; scoring refused")
        messages = build_scoring_messages(case, student_answers, rubric)
        resp = await self._client.chat.completions.create(
            model=model_name(), messages=messages, response_format={"type": "json_object"}
        )
        try:
            data = json.loads(resp.choices[0].message.content or "{}")
            return ScoreResult.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidScoreOutputError(str(exc)) from exc
