"""Pydantic schemas for Gig-Aid dispute and grievance workflow."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DisputeCategory(str, Enum):
    """Categories of disputes for gig and informal workers."""

    PAY_OR_PAYOUT = "pay_or_payout"
    PENALTY_OR_FINE = "penalty_or_fine"
    ACCOUNT_DEACTIVATION = "account_deactivation"
    ACCIDENT_OR_SAFETY = "accident_or_safety"
    WORKPLACE_OR_HARASSMENT = "workplace_or_harassment"
    OTHER = "other"


class VerifiedSourceGuidance(BaseModel):
    """Guidance verified against official central or state government portals."""

    title: str = Field(..., description="Official title of the scheme, portal, or rule")
    jurisdiction: str = Field(
        ..., description="Pan-India (Central) or specific state (e.g., Karnataka, Rajasthan)"
    )
    source_name: str = Field(..., description="Name of the official governing authority")
    source_url: Optional[str] = Field(None, description="Direct URL to official portal or act")
    verified_date: Optional[str] = Field(None, description="Date or year verified from official publication")
    summary_simple_language: str = Field(
        ..., description="Plain-language explanation of what this guidance means for the worker"
    )


class FactVerificationStatus(BaseModel):
    """Explicitly distinguishes worker facts, verified guidance, and unverified information."""

    worker_provided_facts: List[str] = Field(
        default_factory=list,
        description="Factual statements directly provided by the worker in their account",
    )
    verified_guidance: List[VerifiedSourceGuidance] = Field(
        default_factory=list,
        description="Verified guidance from official Central or State sources",
    )
    unverified_information: List[str] = Field(
        default_factory=list,
        description="Statements, policy claims, or deadlines that could not be independently verified",
    )


class MissingFactQuestion(BaseModel):
    """Questions asking for missing facts needed to strengthen the grievance draft."""

    field_key: str = Field(..., description="Key identifying the missing detail")
    question_text: str = Field(..., description="Question in simple, accessible language")
    is_optional: bool = Field(
        default=True,
        description="Workers stay in control and may omit personal or identifying details",
    )
    why_needed: str = Field(..., description="Brief reason why this detail helps the draft")


class WorkerNextStep(BaseModel):
    """Worker-controlled next steps for reviewing, downloading, and sending the grievance."""

    step_number: int
    action_type: str = Field(
        ...,
        description="'review_and_edit', 'copy_or_download', 'platform_grievance_channel', or 'official_government_portal'",
    )
    title: str
    description: str
    official_portal_link: Optional[str] = None


class DisputeIntakeRequest(BaseModel):
    """Worker request describing a dispute."""

    dispute_text: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="Worker's description of what happened in their preferred language",
    )
    category: Optional[DisputeCategory] = Field(
        default=DisputeCategory.OTHER, description="Category of the dispute"
    )
    platform_or_employer: Optional[str] = Field(
        default=None, max_length=100, description="Platform or employer name if provided"
    )
    worker_state: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Worker's State or Union Territory in India for location-specific guidance",
    )
    preferred_language: str = Field(
        default="English",
        max_length=50,
        description="Language for draft output (e.g., Hindi, English, Hinglish, Tamil, Telugu, etc.)",
    )
    additional_facts: Optional[dict] = Field(
        default=None,
        description="Answers to previously asked missing fact questions, if any",
    )

    @field_validator("dispute_text")
    @classmethod
    def strip_and_validate_text(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("Dispute description must contain at least 10 characters.")
        return cleaned


class GrievanceDraftResponse(BaseModel):
    """The complete response with grievance draft, source guidance, and worker-controlled steps."""

    is_complete_draft: bool = Field(
        ...,
        description="True if enough facts are available for a draft; False if critical details are missing",
    )
    missing_questions: List[MissingFactQuestion] = Field(
        default_factory=list,
        description="Targeted questions if key facts are missing",
    )
    subject_line: str = Field(
        ..., description="Clear, professional subject line for the grievance"
    )
    grievance_draft: str = Field(
        ...,
        description="Editable, structured grievance draft based on worker's provided facts",
    )
    worker_summary_simple: str = Field(
        ...,
        description="Simple 5th-grade plain language explanation of the draft and recommendations",
    )
    fact_status: FactVerificationStatus = Field(
        ...,
        description="Breakdown of worker facts vs verified guidance vs unverified info",
    )
    worker_controlled_next_steps: List[WorkerNextStep] = Field(
        default_factory=list,
        description="Next steps the worker can choose to take",
    )
    privacy_notice: str = Field(
        default=(
            "Privacy Notice: Gig-Aid does not retain your grievance text by default. "
            "Identifying information can be omitted. Text is processed securely via the AI provider "
            "to create this draft. You retain full control over reviewing, editing, and submitting."
        )
    )


class HealthResponse(BaseModel):
    """Liveness/readiness health check response."""

    status: str
    service: str
    environment: str
    model_configured: str
