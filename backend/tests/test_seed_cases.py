import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Case
from scripts.seed_cases import seed_cases


@pytest.fixture()
def cases_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'seed_test.db'}")
    yield engine
    engine.dispose()


def _write_case_file(cases_dir: Path, payload: dict, filename: str = "case.json") -> Path:
    path = cases_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _minimal_payload() -> dict:
    return {
        "case_id": "GP-ChestPain-0001",
        "title": "Stress-related chest pain",
        "type": "initial_visit",
        "system_tags": ["primary-care"],
        "difficulty": "medium",
        "language_availability": ["en"],
        "sections_language": {
            "student_instruction": "en",
            "history_taking": "en",
            "case_presentation": "en",
            "structured_questions": "en",
            "scoring": "en",
        },
        "learning_objectives": ["approach to chest pain"],
        "student_instructions": "Take a focused history.",
        "status": "published",
        "patient_information": {
            "name": "Ms. Chen",
            "age": 32,
            "gender": "female",
            "chief_complaint": "Recurrent chest pain.",
            "history_of_present_illness": "Intermittent pain.",
            "opening_statement": "I have chest pain.",
        },
        "examiner_pack": {
            "case_summary": "Chest pain.",
            "working_diagnosis": "Stress-related chest pain",
            "differentials": ["Angina"],
            "structured_questions": [
                {
                    "id": "sq-1",
                    "order": 1,
                    "question": "Diagnosis?",
                    "language": "en",
                    "reveal_items": [],
                }
            ],
            "suggested_answers": [{"question_id": "sq-1", "answer": "Stress-related."}],
            "physical_exam_release": [],
            "investigation_release": [],
            "scoring_rubric": {"max_score": 100, "criteria": []},
        },
    }


def test_seed_creates_published_case(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload())
    imported = seed_cases(cases_dir, engine)
    assert imported == ["GP-ChestPain-0001"]
    with Session(engine) as s:
        case = s.scalars(select(Case)).one()
        assert case.status.value == "published"
        assert len(case.examiner_pack.structured_questions) == 1


def test_seed_is_idempotent(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload())
    seed_cases(cases_dir, engine)
    seed_cases(cases_dir, engine)
    with Session(engine) as s:
        assert len(s.scalars(select(Case)).all()) == 1


def test_seed_imports_multiple_files(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload(), "a.json")
    second = _minimal_payload()
    second["case_id"] = "GP-HTN-0001"
    second["title"] = "Hypertension"
    _write_case_file(cases_dir, second, "b.json")
    imported = seed_cases(cases_dir, engine)
    assert sorted(imported) == ["GP-ChestPain-0001", "GP-HTN-0001"]


def test_invalid_file_rejected_without_db_pollution(cases_dir, engine):
    payload = _minimal_payload()
    del payload["title"]
    _write_case_file(cases_dir, payload, "bad.json")
    with pytest.raises(ValidationError):
        seed_cases(cases_dir, engine)
    with Session(engine) as s:
        assert s.scalars(select(Case)).all() == []


def test_reseed_reflects_file_changes(cases_dir, engine):
    _write_case_file(cases_dir, _minimal_payload())
    seed_cases(cases_dir, engine)
    updated = _minimal_payload()
    updated["title"] = "Updated title"
    _write_case_file(cases_dir, updated)
    seed_cases(cases_dir, engine)
    with Session(engine) as s:
        case = s.scalars(select(Case)).one()
        assert case.title == "Updated title"
