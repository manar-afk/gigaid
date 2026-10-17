"""Unit tests for LLM service fact separation, missing fact questions, and fallback behavior."""

import asyncio
from backend.config import Settings
from backend.schemas import DisputeCategory, DisputeIntakeRequest
from backend.services.llm_service import process_dispute_intake


def test_dispute_intake_fallback_deterministic():
    """Verify deterministic grounded draft generation without API key."""
    settings = Settings(GEMINI_API_KEY="")
    req = DisputeIntakeRequest(
        dispute_text="Swiggy deducted Rs 350 because the app had a GPS glitch and showed wrong delivery location.",
        category=DisputeCategory.PENALTY_OR_FINE,
        platform_or_employer="Swiggy",
        worker_state="Maharashtra",
        preferred_language="English",
    )

    response = asyncio.run(process_dispute_intake(req, settings=settings))

    assert response.subject_line is not None
    assert "Swiggy" in response.grievance_draft
    assert "GPS glitch" in response.grievance_draft
    assert len(response.fact_status.worker_provided_facts) > 0
    assert len(response.worker_controlled_next_steps) >= 3


def test_dispute_intake_generates_missing_questions():
    """Verify that omitting order ID and amount produces targeted optional clarification questions."""
    settings = Settings(GEMINI_API_KEY="")
    req = DisputeIntakeRequest(
        dispute_text="My delivery partner account was suspended yesterday without explanation.",
        category=DisputeCategory.ACCOUNT_DEACTIVATION,
        platform_or_employer="Blinkit",
        worker_state=None,  # No state specified
        preferred_language="English",
    )

    response = asyncio.run(process_dispute_intake(req, settings=settings))

    # Missing questions should ask for state or order/partner ID
    keys = [q.field_key for q in response.missing_questions]
    assert "state_location" in keys or "order_or_ride_id" in keys
    assert all(q.is_optional for q in response.missing_questions)


def test_dispute_intake_pii_masking_notice():
    """Verify that when PII is present in worker text, an explanatory note is included."""
    settings = Settings(GEMINI_API_KEY="")
    req = DisputeIntakeRequest(
        dispute_text="Contact me on 9811223344 about my withheld payout from last week.",
        category=DisputeCategory.PAY_OR_PAYOUT,
        platform_or_employer="Zepto",
        worker_state="Delhi",
    )

    response = asyncio.run(process_dispute_intake(req, settings=settings))

    # Phone should be redacted in draft
    assert "9811223344" not in response.grievance_draft
    # Notice about masking in unverified information
    assert any("identifying numbers" in note for note in response.fact_status.unverified_information)
