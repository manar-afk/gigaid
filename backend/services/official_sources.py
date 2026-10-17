"""Verified official sources for Pan-India and state-specific worker guidance.

This module provides source-grounded references from official Central Government
and State portals. It strictly adheres to:
1. Pan-India sources by default (Central Government portals).
2. State-specific sources ONLY when the worker specifies the state and official
   enacted legislation/portals exist (e.g. Rajasthan 2023 Act, Karnataka 2025 Act).
3. Explicit disclosure when state-specific guidance cannot be confirmed.
4. Distinguishing verified guidance from worker-provided facts.
"""

from typing import List, Optional, Tuple
from backend.schemas import VerifiedSourceGuidance


# Pan-India Central Government Sources
PAN_INDIA_SOURCES = [
    VerifiedSourceGuidance(
        title="e-Shram Portal & National Unorganized Workers Registry",
        jurisdiction="Pan-India (Central Government)",
        source_name="Ministry of Labour & Employment, Government of India",
        source_url="https://eshram.gov.in/",
        verified_date="2021 (Ongoing Portal)",
        summary_simple_language=(
            "Central portal for unorganized and gig workers across India. Provides a 12-digit Universal "
            "Account Number (UAN) for social security schemes. Includes official grievance helpline at 14434."
        ),
    ),
    VerifiedSourceGuidance(
        title="National Consumer Helpline (NCH)",
        jurisdiction="Pan-India (Central Government)",
        source_name="Department of Consumer Affairs, Government of India",
        source_url="https://consumerhelpline.gov.in/",
        verified_date="Consumer Protection Act, 2019",
        summary_simple_language=(
            "For unfair platform deductions, withheld payments, or service disputes. Workers can lodge complaints "
            "via toll-free number 1915 or online at consumerhelpline.gov.in."
        ),
    ),
    VerifiedSourceGuidance(
        title="Statutory Platform Grievance Officer Mechanism",
        jurisdiction="Pan-India (Statutory Mandate)",
        source_name="Information Technology (Intermediary Guidelines) Rules, 2021",
        source_url="https://www.meity.gov.in/content/information-technology-intermediary-guidelines-and-digital-media-ethics-code-rules-2021",
        verified_date="2021",
        summary_simple_language=(
            "Under central IT rules, digital platform companies must publish the name and email of an Indian Resident "
            "Grievance Officer. Platforms are required to acknowledge grievances within 24 hours."
        ),
    ),
]


# Verified State-Specific Sources (referenced only when state is specified)
STATE_SOURCES = {
    "rajasthan": [
        VerifiedSourceGuidance(
            title="The Rajasthan Platform Based Gig Workers (Registration and Welfare) Act, 2023",
            jurisdiction="State: Rajasthan",
            source_name="Government of Rajasthan / State Legislative Assembly",
            source_url="https://prsindia.org/bills/states/the-rajasthan-platform-based-gig-workers-registration-and-welfare-bill-2023",
            verified_date="Passed July 2023",
            summary_simple_language=(
                "Establishes the Rajasthan Gig Workers Welfare Board, mandatory registration, welfare fund fee per transaction, "
                "and an official state dispute resolution and grievance procedure for gig workers within Rajasthan."
            ),
        )
    ],
    "karnataka": [
        VerifiedSourceGuidance(
            title="The Karnataka Platform-Based Gig Workers (Social Security and Welfare) Act, 2025",
            jurisdiction="State: Karnataka",
            source_name="Government of Karnataka / State Legislative Assembly (Act 72 of 2025)",
            source_url="https://prsindia.org/files/bills_acts/acts_states/karnataka/2025/Act72of2025KA.pdf",
            verified_date="Enacted 2025 (following 2024 draft bill)",
            summary_simple_language=(
                "Mandates fair contract terms, transparency in automated monitoring/deactivation, welfare fund contributions, "
                "internal dispute mechanisms, and state welfare board grievance resolution for gig workers in Karnataka."
            ),
        )
    ],
}


def get_verified_guidance_for_worker(
    worker_state: Optional[str] = None,
) -> Tuple[List[VerifiedSourceGuidance], List[str]]:
    """Retrieve verified official guidance based on worker's location.

    Returns:
        Tuple of (verified_guidance_list, unverified_information_notes).
    """
    guidance: List[VerifiedSourceGuidance] = list(PAN_INDIA_SOURCES)
    unverified_notes: List[str] = []

    if not worker_state or worker_state.strip() == "":
        unverified_notes.append(
            "State location was not specified. Nationwide central government mechanisms (e-Shram, NCH 1915, "
            "IT Rules Grievance Officer) apply. State-specific protections could not be determined without knowing the state."
        )
        return guidance, unverified_notes

    normalized_state = worker_state.strip().lower()

    # Check known state-specific legislation
    matched_state = None
    for state_key in STATE_SOURCES:
        if state_key in normalized_state:
            matched_state = state_key
            break

    if matched_state:
        guidance.extend(STATE_SOURCES[matched_state])
    else:
        unverified_notes.append(
            f"No verified state-specific gig worker legislation is currently on record for '{worker_state.strip()}'. "
            "Only nationwide central government guidance and general consumer/labor remedies are verified for this location."
        )

    return guidance, unverified_notes
