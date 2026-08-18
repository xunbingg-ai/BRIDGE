import pytest
from pydantic import ValidationError

from cases.schema import CaseFile


def _valid_payload() -> dict:
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
            "chief_complaint": "Recurrent chest pain for 4 weeks.",
            "history_of_present_illness": "Intermittent sharp pain.",
            "opening_statement": "I have had chest pain for 4 weeks.",
        },
        "examiner_pack": {
            "case_summary": "32yo woman with chest pain.",
            "working_diagnosis": "Stress-related chest pain",
            "differentials": ["Angina"],
            "structured_questions": [
                {
                    "id": "sq-1",
                    "order": 1,
                    "question": "State the most likely diagnosis.",
                    "language": "en",
                    "reveal_items": [],
                }
            ],
            "suggested_answers": [
                {"question_id": "sq-1", "answer": "Stress-related chest pain."}
            ],
            "physical_exam_release": [],
            "investigation_release": [],
            "scoring_rubric": {"max_score": 100, "criteria": []},
        },
    }


def test_valid_case_file_parses():
    case = CaseFile.model_validate(_valid_payload())
    assert case.case_id == "GP-ChestPain-0001"
    assert case.status == "published"
    assert case.examiner_pack.structured_questions[0].id == "sq-1"


def test_missing_required_field_rejected():
    payload = _valid_payload()
    del payload["title"]
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)


def test_unknown_section_key_rejected():
    payload = _valid_payload()
    payload["sections_language"]["scoring_extra"] = "en"
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)


def test_bad_enum_rejected():
    payload = _valid_payload()
    payload["type"] = "emergency"
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)


def test_empty_structured_questions_rejected():
    payload = _valid_payload()
    payload["examiner_pack"]["structured_questions"] = []
    with pytest.raises(ValidationError):
        CaseFile.model_validate(payload)
