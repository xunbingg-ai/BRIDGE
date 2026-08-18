import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Case, CaseStatus, CaseType, ExaminerPack, PatientInformation


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_case():
    return Case(
        id="GP-ChestPain-0001",
        title="Stress-related chest pain",
        type=CaseType.initial_visit,
        system_tags=["primary-care", "cardiology"],
        difficulty="medium",
        language_availability=["en"],
        sections_language={
            "student_instruction": "en",
            "history_taking": "en",
            "case_presentation": "en",
            "structured_questions": "en",
            "scoring": "en",
        },
        learning_objectives=["approach to chest pain in primary care"],
        student_instructions="Take a focused history.",
        status=CaseStatus.published,
        patient_information=PatientInformation(
            name="Ms. Chen",
            age=32,
            gender="female",
            chief_complaint="Recurrent chest pain for 4 weeks.",
            history_of_present_illness="Intermittent sharp pain.",
            opening_statement="I have had chest pain on and off for 4 weeks.",
        ),
        examiner_pack=ExaminerPack(
            case_summary="32yo woman with recurrent chest pain.",
            working_diagnosis="Stress/anxiety-related chest pain",
            differentials=["Angina", "Costochondritis"],
            structured_questions=[
                {
                    "id": "sq-1",
                    "order": 1,
                    "question": "State the most likely diagnosis.",
                    "language": "en",
                }
            ],
            suggested_answers=[{"question_id": "sq-1", "answer": "Stress-related chest pain."}],
            physical_exam_release=[],
            investigation_release=[],
            scoring_rubric={"max_score": 100, "criteria": []},
        ),
    )


def test_case_persists_with_related_objects(session):
    session.add(_make_case())
    session.commit()

    case = session.scalars(select(Case)).one()
    assert case.patient_information.name == "Ms. Chen"
    assert case.examiner_pack.working_diagnosis == "Stress/anxiety-related chest pain"
    assert case.status == CaseStatus.published
    assert len(case.examiner_pack.structured_questions) == 1


def test_patient_information_is_one_to_one(session):
    session.add(_make_case())
    session.commit()

    case = session.scalars(select(Case)).one()
    session.add(
        PatientInformation(
            case_id=case.id,
            name="Duplicate",
            age=30,
            gender="female",
            chief_complaint="x",
            history_of_present_illness="y",
            opening_statement="z",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_case_cascades_to_children(session):
    session.add(_make_case())
    session.commit()
    case = session.scalars(select(Case)).one()
    session.delete(case)
    session.commit()
    assert session.scalars(select(PatientInformation)).all() == []
    assert session.scalars(select(ExaminerPack)).all() == []
