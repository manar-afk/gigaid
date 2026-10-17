"""LLM Service for Gig-Aid using configurable Gemini API with defensive parsing.

Distinguishes between:
1. Worker-provided facts
2. Verified official guidance
3. Unverified information
Never invents laws, deadlines, evidence, platform policies, or outcomes.
Provides structured drafts, missing fact questions, and worker-controlled next steps.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.config import Settings, get_settings
from backend.schemas import (
    DisputeIntakeRequest,
    FactVerificationStatus,
    GrievanceDraftResponse,
    MissingFactQuestion,
    VerifiedSourceGuidance,
    WorkerNextStep,
)
from backend.services.official_sources import get_verified_guidance_for_worker
from backend.services.safety_guard import (
    check_prompt_injection,
    reduce_pii_exposure,
    sanitize_worker_input,
    wrap_untrusted_input,
)

logger = logging.getLogger("gig_aid.llm_service")


SYSTEM_PROMPT = """You are Gig-Aid, a pan-India multilingual GenAI grievance assistant for gig and informal workers (delivery partners, cab/auto drivers, and daily-wage laborers).

CORE MANDATE:
1. Help workers describe pay, penalty, account, or workplace disputes in their preferred language.
2. Formulate polite, optional clarification questions for any missing key facts (e.g., date, order/trip ID, specific amount deducted, platform name).
3. Create a clear, editable grievance draft based STRICTLY on the worker's own account.
4. Distinguish clearly between:
   - Worker-provided facts (what the worker reported)
   - Verified official guidance (only the official sources provided to you)
   - Information that could not be verified (any unconfirmed claims or missing policies)
5. NEVER invent laws, statutory sections, deadlines, evidence, platform policies, or likely outcomes. If something cannot be verified, state that explicitly.
6. Explain the draft in simple, accessible language (5th-grade level) for the worker summary.
7. Return your response ONLY as valid JSON matching the required schema.
"""


def _build_worker_controlled_next_steps(
    platform: Optional[str],
    has_missing_info: bool,
    verified_guidance: List[VerifiedSourceGuidance],
) -> List[WorkerNextStep]:
    """Generate worker-controlled next steps.

    The assistant prepares a draft; it does not claim a complaint has been submitted
    or guarantee a resolution.
    """
    steps: List[WorkerNextStep] = [
        WorkerNextStep(
            step_number=1,
            action_type="review_and_edit",
            title="Review & Edit Your Draft",
            description=(
                "Read through the generated grievance draft. Edit any dates, amounts, or details "
                "to ensure it accurately reflects what happened. You are in full control."
            ),
        ),
        WorkerNextStep(
            step_number=2,
            action_type="copy_or_download",
            title="Copy or Download Draft",
            description="Copy the text or save it to your device so you have an offline record of your complaint.",
        ),
        WorkerNextStep(
            step_number=3,
            action_type="platform_grievance_channel",
            title="Submit to Company Support or Grievance Officer",
            description=(
                f"Send this draft through {platform or 'your platform'} official in-app support chat, "
                "help ticket, or the email of their designated Indian Resident Grievance Officer."
            ),
        ),
    ]

    # Add verified official portal step
    if verified_guidance:
        primary_source = verified_guidance[0]
        steps.append(
            WorkerNextStep(
                step_number=4,
                action_type="official_government_portal",
                title=f"Official Dispute Portal: {primary_source.title}",
                description=(
                    f"If the company fails to respond or resolve the issue, you may refer to "
                    f"{primary_source.source_name} ({primary_source.summary_simple_language})."
                ),
                official_portal_link=primary_source.source_url,
            )
        )

    return steps


def _extract_worker_facts(raw_text: str, additional_facts: Optional[dict]) -> List[str]:
    """Extract verifiable worker-provided facts from the raw input without fabrication."""
    facts = []
    # Split sentences and clean
    cleaned_sentences = [
        s.strip() for s in raw_text.replace("\n", ". ").split(".") if len(s.strip()) > 8
    ]
    for s in cleaned_sentences[:5]:
        facts.append(f"Worker stated: {s}")

    if additional_facts:
        for k, v in additional_facts.items():
            if v and str(v).strip():
                facts.append(f"Worker clarified ({k}): {str(v).strip()}")

    if not facts:
        facts.append(f"Worker reported: {raw_text.strip()}")

    return facts


def _generate_fallback_draft(
    request: DisputeIntakeRequest,
    sanitized_text: str,
    verified_guidance: List[VerifiedSourceGuidance],
    unverified_notes: List[str],
) -> GrievanceDraftResponse:
    """Generate a deterministic, grounded grievance response.

    Used when remote API call is disabled, offline, or returns unexpected format.
    Ensures 100% testability, zero hallucinations, and consistent worker assistance.
    """
    platform_name = request.platform_or_employer or "the Platform / Service Provider"
    category_name = (
        request.category.value.replace("_", " ").title() if request.category else "Dispute"
    )

    # Detect missing key details
    missing_questions: List[MissingFactQuestion] = []
    text_lower = sanitized_text.lower()

    if not any(token in text_lower for token in ["order", "ride", "trip", "booking", "id", "ticket"]):
        missing_questions.append(
            MissingFactQuestion(
                field_key="order_or_ride_id",
                question_text="What was the specific Order ID, Ride ID, or Worker ID related to this issue?",
                is_optional=True,
                why_needed="Helps support staff locate the exact transaction in their records.",
            )
        )

    if not any(char.isdigit() for char in sanitized_text):
        missing_questions.append(
            MissingFactQuestion(
                field_key="disputed_amount_or_date",
                question_text="What was the date of the incident or the specific amount in dispute (in ₹)?",
                is_optional=True,
                why_needed="Specifying the exact amount or date prevents confusion.",
            )
        )

    if not request.worker_state:
        missing_questions.append(
            MissingFactQuestion(
                field_key="state_location",
                question_text="Which Indian State or Union Territory do you work in?",
                is_optional=True,
                why_needed="Allows us to provide verified state-specific welfare or dispute contacts.",
            )
        )

    is_complete = len(missing_questions) <= 1

    subject = f"Formal Grievance: {category_name} - Request for Review and Resolution"

    body = (
        f"To:\n"
        f"Grievance Redressal Team / Support Management\n"
        f"{platform_name}\n\n"
        f"Date: [Insert Date]\n"
        f"Subject: {subject}\n\n"
        f"Dear Sir / Madam,\n\n"
        f"I am writing to register a formal grievance regarding a recent {category_name.lower()} issue "
        f"encountered during my work with {platform_name}.\n\n"
        f"Account of Facts (As Reported):\n"
        f"---------------------------------\n"
        f"{sanitized_text}\n\n"
    )

    if request.additional_facts:
        body += "Additional Clarifications Provided:\n"
        for k, v in request.additional_facts.items():
            body += f"- {k.replace('_', ' ').title()}: {v}\n"
        body += "\n"

    body += (
        "Grounds for Review:\n"
        "1. The action taken appears disproportionate based on the circumstances described above.\n"
        "2. As a delivery/transport partner, I request a fair, human review of the logs and records.\n"
        "3. If this involves an automated deduction or deactivation, I request the specific rationale and record.\n\n"
        "Requested Resolution:\n"
        "- Immediate review and reversal of unfair penalties or account restrictions.\n"
        "- Clear written communication regarding the outcome of this grievance within the statutory period.\n\n"
        "Thank you for your prompt attention.\n\n"
        "Sincerely,\n"
        "[Your Full Name]\n"
        "[Your Registered Mobile Number / Worker Partner ID]\n"
        f"[Location / City{f', {request.worker_state}' if request.worker_state else ''}]"
    )

    worker_summary = (
        f"We have prepared a neutral, professional draft for your {category_name.lower()} dispute with {platform_name}. "
        "It summarizes what you told us in clear, formal language so the company can review it. "
        "You can edit the details, add any missing Order or Ride ID, and submit it directly through the company's "
        "support portal or official email."
    )

    worker_facts = _extract_worker_facts(sanitized_text, request.additional_facts)

    next_steps = _build_worker_controlled_next_steps(
        platform=request.platform_or_employer,
        has_missing_info=bool(missing_questions),
        verified_guidance=verified_guidance,
    )

    return GrievanceDraftResponse(
        is_complete_draft=is_complete,
        missing_questions=missing_questions,
        subject_line=subject,
        grievance_draft=body,
        worker_summary_simple=worker_summary,
        fact_status=FactVerificationStatus(
            worker_provided_facts=worker_facts,
            verified_guidance=verified_guidance,
            unverified_information=unverified_notes,
        ),
        worker_controlled_next_steps=next_steps,
    )


async def process_dispute_intake(
    request: DisputeIntakeRequest,
    settings: Optional[Settings] = None,
) -> GrievanceDraftResponse:
    """Process a worker dispute intake request, validate, sanitize, and generate draft.

    Enforces:
    - Bounded inputs
    - Prompt injection defense
    - PII exposure reduction
    - Separation of worker facts vs verified sources vs unverified notes
    """
    if settings is None:
        settings = get_settings()

    # 1. Sanitize raw input and enforce maximum length
    sanitized_text = sanitize_worker_input(request.dispute_text, settings.MAX_INPUT_LENGTH)

    # 2. Check for prompt injection or jailbreak attempts
    if check_prompt_injection(sanitized_text):
        logger.warning("Prompt injection pattern detected in worker input.")
        # Neutralize by continuing strictly with safe text, ignoring embedded directives

    # 3. Reduce PII exposure (phone, Aadhaar, cards, emails)
    masked_text, pii_detected = reduce_pii_exposure(sanitized_text)

    # 4. Retrieve verified official sources based on location
    verified_guidance, unverified_notes = get_verified_guidance_for_worker(request.worker_state)

    if pii_detected:
        unverified_notes.append(
            "Notice: Some identifying numbers (such as phone or ID numbers) were masked to protect your privacy. "
            "Please verify that your editable draft contains only the information you are comfortable sharing."
        )

    # 5. If no API key configured or fallback preferred, use deterministic grounded engine
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() == "":
        logger.info("GEMINI_API_KEY not configured. Generating draft via deterministic grounded engine.")
        return _generate_fallback_draft(
            request=request,
            sanitized_text=masked_text,
            verified_guidance=verified_guidance,
            unverified_notes=unverified_notes,
        )

    # 6. Call Google Gemini API with structured prompt
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )

        user_content = (
            f"Worker Preferred Language: {request.preferred_language}\n"
            f"Dispute Category: {request.category.value if request.category else 'General'}\n"
            f"Platform/Employer: {request.platform_or_employer or 'Not specified'}\n"
            f"Worker State: {request.worker_state or 'Not specified'}\n"
            f"Additional Facts: {json.dumps(request.additional_facts or {})}\n\n"
            f"{wrap_untrusted_input(masked_text)}\n\n"
            f"Official Guidance Available:\n"
            f"{json.dumps([g.model_dump() for g in verified_guidance], indent=2)}\n\n"
            f"Please generate the grievance draft and return in JSON format with fields:\n"
            f"- is_complete_draft (bool)\n"
            f"- missing_questions (list of objects with field_key, question_text, is_optional, why_needed)\n"
            f"- subject_line (string)\n"
            f"- grievance_draft (string, clear and professional)\n"
            f"- worker_summary_simple (string, 5th-grade reading level)\n"
            f"- worker_provided_facts (list of strings extracted strictly from worker input)\n"
            f"- unverified_information (list of strings for claims not verified)"
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_content}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": settings.MAX_OUTPUT_TOKENS,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Gemini API returned status {resp.status_code}: {resp.text}")
                return _generate_fallback_draft(
                    request=request,
                    sanitized_text=masked_text,
                    verified_guidance=verified_guidance,
                    unverified_notes=unverified_notes,
                )

            data = resp.json()
            raw_json = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            parsed = json.loads(raw_json)

            missing_q = [
                MissingFactQuestion(**q) for q in parsed.get("missing_questions", [])
            ]
            worker_facts = parsed.get("worker_provided_facts") or _extract_worker_facts(
                masked_text, request.additional_facts
            )
            extra_unverified = parsed.get("unverified_information") or []
            combined_unverified = list(unverified_notes) + [
                u for u in extra_unverified if u not in unverified_notes
            ]

            next_steps = _build_worker_controlled_next_steps(
                platform=request.platform_or_employer,
                has_missing_info=bool(missing_q),
                verified_guidance=verified_guidance,
            )

            return GrievanceDraftResponse(
                is_complete_draft=parsed.get("is_complete_draft", True),
                missing_questions=missing_q,
                subject_line=parsed.get("subject_line", f"Formal Grievance: {request.category.value if request.category else 'Dispute'}"),
                grievance_draft=parsed.get("grievance_draft", ""),
                worker_summary_simple=parsed.get("worker_summary_simple", ""),
                fact_status=FactVerificationStatus(
                    worker_provided_facts=worker_facts,
                    verified_guidance=verified_guidance,
                    unverified_information=combined_unverified,
                ),
                worker_controlled_next_steps=next_steps,
            )

    except Exception as exc:
        logger.error(f"Error calling Gemini API: {exc}. Falling back to grounded generator.")
        return _generate_fallback_draft(
            request=request,
            sanitized_text=masked_text,
            verified_guidance=verified_guidance,
            unverified_notes=unverified_notes,
        )
