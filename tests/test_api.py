"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify health and readiness check endpoint for Cloud Run."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Gig-Aid"
    assert "model_configured" in data


def test_sources_endpoint_pan_india():
    """Verify official sources endpoint returns pan-India guidance."""
    response = client.get("/api/v1/grievance/sources")
    assert response.status_code == 200
    data = response.json()
    assert len(data["verified_sources"]) >= 3
    assert "e-Shram" in str(data["verified_sources"])


def test_sources_endpoint_karnataka():
    """Verify official sources endpoint includes Karnataka 2025 Act when queried."""
    response = client.get("/api/v1/grievance/sources?worker_state=Karnataka")
    assert response.status_code == 200
    data = response.json()
    assert any("Karnataka" in str(s) for s in data["verified_sources"])


def test_intake_validation_error_short_text():
    """Verify inputs shorter than 10 characters are rejected with 422 error."""
    payload = {
        "dispute_text": "too short",
        "category": "pay_or_payout",
    }
    response = client.post("/api/v1/grievance/intake", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_intake_success_flow():
    """Verify successful dispute intake, draft generation, and fact extraction."""
    payload = {
        "dispute_text": "Zomato deducted Rs 500 penalty claiming order #9823 was delayed. The road was waterlogged due to heavy rain.",
        "category": "penalty_or_fine",
        "platform_or_employer": "Zomato",
        "worker_state": "Delhi",
        "preferred_language": "English",
    }
    response = client.post("/api/v1/grievance/intake", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify response schema fields
    assert "subject_line" in data
    assert "grievance_draft" in data
    assert "worker_summary_simple" in data
    assert "fact_status" in data
    assert "worker_controlled_next_steps" in data

    # Verify fact/source separation
    fact_status = data["fact_status"]
    assert len(fact_status["worker_provided_facts"]) > 0
    assert len(fact_status["verified_guidance"]) > 0

    # Verify worker next steps include review, copy/download, and platform submission
    action_types = [step["action_type"] for step in data["worker_controlled_next_steps"]]
    assert "review_and_edit" in action_types
    assert "copy_or_download" in action_types


def test_intake_with_clarified_facts():
    """Verify updating draft with worker-provided clarification answers."""
    payload = {
        "dispute_text": "Company blocked my account without any prior warning or reason.",
        "category": "account_deactivation",
        "platform_or_employer": "Uber",
        "worker_state": "Karnataka",
        "preferred_language": "English",
        "additional_facts": {
            "order_or_ride_id": "CRN-998822",
            "date_of_incident": "12-10-2026",
        },
    }
    response = client.post("/api/v1/grievance/intake", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "CRN-998822" in data["grievance_draft"]
    assert any("CRN-998822" in str(fact) for fact in data["fact_status"]["worker_provided_facts"])
