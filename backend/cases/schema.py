"""Pydantic schema for developer-authored case JSON files (phase 1).

Field mapping to the requirements doc section 9 and the Excel template is
documented in docs/case-file-format.md.

NOTE (2026-08-18 user decision): de-identification validation is intentionally
NOT implemented in phase 1 because all phase-1 cases are fictional. ADR-0002
still applies: real-patient cases must be de-identified by the user personally
before entering the library.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CaseType(str, Enum):
    initial_visit = "initial_visit"
    follow_up_visit = "follow_up_visit"


class CaseStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    published = "published"


class Language(str, Enum):
    en = "en"
    zh = "zh"


SECTION_KEYS = {
    "student_instruction",
    "history_taking",
    "case_presentation",
    "structured_questions",
    "scoring",
}


class PatientInfoFile(BaseModel):
    name: str
    age: int = Field(ge=0, le=120)
    gender: str
    occupation: str | None = None
    ethnicity: str | None = None
    patient_language: str | None = None
    chief_complaint: str
    history_of_present_illness: str
    review_of_systems: dict[str, str] = Field(default_factory=dict)
    past_medical_history: list[str] = Field(default_factory=list)
    past_surgical_history: str | None = None
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    family_history: str | None = None
    personal_social_history: dict[str, str] = Field(default_factory=dict)
    sexual_history: str | None = None
    obgyn_history: str | None = None
    opening_statement: str
    affect_style: str | None = None
    ice: dict[str, str] = Field(default_factory=dict)
    disclosure_rules: list[str] = Field(default_factory=list)
    qa_triggers: list[dict[str, Any]] = Field(default_factory=list)
    default_negative_response: str | None = None


class StructuredQuestionFile(BaseModel):
    id: str
    order: int = Field(ge=1)
    question: str
    language: Language
    reveal_items: list[str] = Field(default_factory=list)


class SuggestedAnswerFile(BaseModel):
    question_id: str
    answer: str


class ReleaseItemFile(BaseModel):
    item_id: str
    name: str
    result: str
    reference_range: str | None = None


class ScoringRubricFile(BaseModel):
    max_score: int = Field(gt=0, default=100)
    criteria: list[dict[str, Any]] = Field(default_factory=list)


class ExaminerPackFile(BaseModel):
    case_summary: str
    working_diagnosis: str
    differentials: list[str] = Field(default_factory=list)
    structured_questions: list[StructuredQuestionFile] = Field(min_length=1)
    suggested_answers: list[SuggestedAnswerFile] = Field(default_factory=list)
    physical_exam_release: list[ReleaseItemFile] = Field(default_factory=list)
    investigation_release: list[ReleaseItemFile] = Field(default_factory=list)
    scoring_rubric: ScoringRubricFile | None = None


class CaseReviewRecordFile(BaseModel):
    review_status: str
    reviewer_name: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    published_at: datetime | None = None


class CaseFile(BaseModel):
    case_id: str = Field(min_length=1)
    title: str
    type: CaseType
    system_tags: list[str] = Field(default_factory=list)
    difficulty: str
    language_availability: list[Language] = Field(default_factory=list)
    sections_language: dict[str, Language]
    learning_objectives: list[str] = Field(default_factory=list)
    student_instructions: str
    status: CaseStatus = CaseStatus.draft
    patient_information: PatientInfoFile
    examiner_pack: ExaminerPackFile
    review_record: CaseReviewRecordFile | None = None

    @field_validator("sections_language")
    @classmethod
    def _check_section_keys(cls, v: dict[str, Language]) -> dict[str, Language]:
        unknown = set(v) - SECTION_KEYS
        if unknown:
            raise ValueError(f"unknown section keys: {sorted(unknown)}")
        return v
