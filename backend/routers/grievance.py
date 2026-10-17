"""Grievance intake, clarification, and drafting router."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.config import Settings, get_settings
from backend.schemas import (
    DisputeIntakeRequest,
    GrievanceDraftResponse,
    VerifiedSourceGuidance,
)
from backend.services.llm_service import process_dispute_intake
from backend.services.official_sources import get_verified_guidance_for_worker

logger = logging.getLogger("gig_aid.routers.grievance")
router = APIRouter(prefix="/grievance", tags=["Grievance & Dispute"])


@router.post(
    "/intake",
    response_model=GrievanceDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="Process dispute intake, clarify missing details, and draft grievance",
    response_description="Structured grievance draft with verified sources and worker next steps",
)
async def intake_dispute(
    request: DisputeIntakeRequest,
    settings: Settings = Depends(get_settings),
) -> GrievanceDraftResponse:
    """Intake a worker's dispute description in their preferred language.

    - Sanitizes input and applies PII exposure reduction
    - Identifies if critical facts are missing and asks targeted questions
    - Creates a clear, editable grievance draft based on the worker's own account
    - Connects to verified official sources (central or state-specific)
    - Returns worker-controlled next steps
    """
    try:
        response = await process_dispute_intake(request, settings=settings)
        return response
    except ValueError as ve:
        logger.warning(f"Validation error during dispute intake: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in grievance intake: {exc}")
        # Safe error without exposing internal stack traces
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your grievance draft. Please verify your input and try again.",
        )


@router.get(
    "/sources",
    summary="Retrieve verified official sources for worker location",
    response_description="List of verified central or state government portals and laws",
)
async def list_verified_sources(
    worker_state: Optional[str] = Query(
        None,
        description="Worker state (e.g., 'Rajasthan', 'Karnataka', 'Delhi') for state-specific verified acts",
    ),
):
    """Retrieve verified Central and State government sources for transparent worker awareness."""
    try:
        guidance, unverified_notes = get_verified_guidance_for_worker(worker_state)
        return {
            "worker_state_queried": worker_state or "Pan-India / Not specified",
            "verified_sources": [g.model_dump() for g in guidance],
            "unverified_information_notes": unverified_notes,
        }
    except Exception as exc:
        logger.error(f"Error fetching verified sources: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch official sources at this time.",
        )
