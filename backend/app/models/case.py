"""Case domain models — field mapping to requirements doc section 9.

Case.id             -> Case.id / Case ID
Case.title          -> Case.title
Case.type           -> Case.type (initial_visit | follow_up_visit)
Case.system_tags    -> Case.systemTags
Case.difficulty     -> Case.difficulty
Case.language_availability -> Case.languageAvailability
Case.sections_language      -> requirements section 7 per-section Language Rule
Case.learning_objectives    -> Case.learningObjectives
Case.student_instructions   -> Case.studentInstructions
Case.status         -> Case.status (draft | in_review | approved | published)
PatientInformation  -> requirements section 9.2 (all fields)
ExaminerPack        -> requirements section 9.3 (all fields)
CaseReviewRecord    -> requirements section 9.4 (all fields)

De-identification policy (ADR-0002): first-phase cases are fictional, so no
automatic de-identification validation is performed here. When real cases are
added later, the user personally reviews them before ingestion.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CaseType(str, Enum):
    initial_visit = "initial_visit"
    follow_up_visit = "follow_up_visit"


class CaseStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    published = "published"


class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[CaseType] = mapped_column(SqlEnum(CaseType))
    system_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(40))
    language_availability: Mapped[list[str]] = mapped_column(JSON, default=list)
    sections_language: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    learning_objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    student_instructions: Mapped[str] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(
        SqlEnum(CaseStatus), default=CaseStatus.draft
    )

    patient_information: Mapped[PatientInformation] = relationship(
        back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    examiner_pack: Mapped[ExaminerPack] = relationship(
        back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    review_record: Mapped[CaseReviewRecord | None] = relationship(
        back_populates="case", uselist=False, cascade="all, delete-orphan"
    )


class PatientInformation(TimestampMixin, Base):
    __tablename__ = "patient_information"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(80))
    age: Mapped[int] = mapped_column()
    gender: Mapped[str] = mapped_column(String(20))
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    patient_language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    chief_complaint: Mapped[str] = mapped_column(Text)
    history_of_present_illness: Mapped[str] = mapped_column(Text)
    review_of_systems: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    past_medical_history: Mapped[list[str]] = mapped_column(JSON, default=list)
    past_surgical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications: Mapped[list[str]] = mapped_column(JSON, default=list)
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    family_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_social_history: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    sexual_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    obgyn_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_statement: Mapped[str] = mapped_column(Text)
    affect_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    ice: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    disclosure_rules: Mapped[list[str]] = mapped_column(JSON, default=list)
    qa_triggers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    default_negative_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship(back_populates="patient_information")


class ExaminerPack(TimestampMixin, Base):
    __tablename__ = "examiner_packs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True
    )
    case_summary: Mapped[str] = mapped_column(Text)
    working_diagnosis: Mapped[str] = mapped_column(Text)
    differentials: Mapped[list[str]] = mapped_column(JSON, default=list)
    structured_questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    suggested_answers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    physical_exam_release: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    investigation_release: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    scoring_rubric: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    case: Mapped[Case] = relationship(back_populates="examiner_pack")


class CaseReviewRecord(TimestampMixin, Base):
    __tablename__ = "case_review_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True
    )
    review_status: Mapped[str] = mapped_column(String(40))
    reviewer_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped[Case] = relationship(back_populates="review_record")
