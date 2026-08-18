"""Idempotent case importer for developer-authored JSON files.

Usage (WSL, from backend/):
    uv run python scripts/seed_cases.py                 # default: ./cases + settings.database_url
    uv run python scripts/seed_cases.py ./cases sqlite:///./bridge.db

Loading is atomic per run: if any file fails validation, nothing is committed.
"""
import json
import sys
from pathlib import Path

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    Case,
    CaseReviewRecord,
    ExaminerPack,
    PatientInformation,
)
from cases.schema import CaseFile  # noqa: E402


def _build_orm(case_file: CaseFile) -> Case:
    case = Case(
        id=case_file.case_id,
        title=case_file.title,
        type=case_file.type,
        system_tags=case_file.system_tags,
        difficulty=case_file.difficulty,
        language_availability=[lang.value for lang in case_file.language_availability],
        sections_language={
            key: lang.value for key, lang in case_file.sections_language.items()
        },
        learning_objectives=case_file.learning_objectives,
        student_instructions=case_file.student_instructions,
        status=case_file.status,
    )
    p = case_file.patient_information
    case.patient_information = PatientInformation(
        name=p.name,
        age=p.age,
        gender=p.gender,
        occupation=p.occupation,
        ethnicity=p.ethnicity,
        patient_language=p.patient_language,
        chief_complaint=p.chief_complaint,
        history_of_present_illness=p.history_of_present_illness,
        review_of_systems=p.review_of_systems,
        past_medical_history=p.past_medical_history,
        past_surgical_history=p.past_surgical_history,
        medications=p.medications,
        allergies=p.allergies,
        family_history=p.family_history,
        personal_social_history=p.personal_social_history,
        sexual_history=p.sexual_history,
        obgyn_history=p.obgyn_history,
        opening_statement=p.opening_statement,
        affect_style=p.affect_style,
        ice=p.ice,
        disclosure_rules=p.disclosure_rules,
        qa_triggers=p.qa_triggers,
        default_negative_response=p.default_negative_response,
    )
    e = case_file.examiner_pack
    case.examiner_pack = ExaminerPack(
        case_summary=e.case_summary,
        working_diagnosis=e.working_diagnosis,
        differentials=e.differentials,
        structured_questions=[q.model_dump() for q in e.structured_questions],
        suggested_answers=[a.model_dump() for a in e.suggested_answers],
        physical_exam_release=[r.model_dump() for r in e.physical_exam_release],
        investigation_release=[r.model_dump() for r in e.investigation_release],
        scoring_rubric=(
            e.scoring_rubric.model_dump() if e.scoring_rubric is not None else None
        ),
    )
    if case_file.review_record is not None:
        r = case_file.review_record
        case.review_record = CaseReviewRecord(
            review_status=r.review_status,
            reviewer_name=r.reviewer_name,
            review_comment=r.review_comment,
            reviewed_at=r.reviewed_at,
            published_at=r.published_at,
        )
    return case


def _upsert(session: Session, case_file: CaseFile) -> None:
    existing = session.get(Case, case_file.case_id)
    if existing is not None:
        session.delete(existing)
        session.flush()
    session.add(_build_orm(case_file))


def seed_cases(cases_dir: Path, engine: Engine) -> list[str]:
    Base.metadata.create_all(engine)
    imported: list[str] = []
    with Session(engine) as session:
        for path in sorted(cases_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_file = CaseFile.model_validate(payload)
            _upsert(session, case_file)
            imported.append(case_file.case_id)
        session.commit()
    return imported


def main() -> int:
    cases_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "cases"
    database_url = sys.argv[2] if len(sys.argv) > 2 else settings.database_url
    engine = create_engine(database_url)
    imported = seed_cases(cases_dir, engine)
    print(f"Imported {len(imported)} case(s): {', '.join(imported)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
