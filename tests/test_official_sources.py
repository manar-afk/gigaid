"""Unit tests for verified official sources and pan-India/state boundaries."""

from backend.services.official_sources import (
    PAN_INDIA_SOURCES,
    get_verified_guidance_for_worker,
)


def test_pan_india_guidance_unspecified_state():
    """Verify pan-India sources are returned and unverified note is logged when state is omitted."""
    guidance, unverified_notes = get_verified_guidance_for_worker(None)
    assert len(guidance) >= 3
    # Check that Central e-Shram is included
    titles = [g.title for g in guidance]
    assert any("e-Shram" in t for t in titles)
    assert any("National Consumer Helpline" in t for t in titles)

    assert len(unverified_notes) > 0
    assert "State location was not specified" in unverified_notes[0]


def test_rajasthan_state_guidance():
    """Verify Rajasthan 2023 Act is included when Rajasthan is specified."""
    guidance, unverified_notes = get_verified_guidance_for_worker("Rajasthan")
    titles = [g.title for g in guidance]
    assert any("The Rajasthan Platform Based Gig Workers" in t for t in titles)
    assert len(unverified_notes) == 0


def test_karnataka_state_guidance():
    """Verify Karnataka 2025 Act is included when Karnataka is specified."""
    guidance, unverified_notes = get_verified_guidance_for_worker("Karnataka")
    titles = [g.title for g in guidance]
    assert any("The Karnataka Platform-Based Gig Workers" in t for t in titles)
    assert any("2025" in g.verified_date for g in guidance if "Karnataka" in g.title)
    assert len(unverified_notes) == 0


def test_unverified_state_guidance():
    """Verify that states without enacted gig worker legislation get pan-India sources + unverified note."""
    guidance, unverified_notes = get_verified_guidance_for_worker("Goa")
    assert len(guidance) == len(PAN_INDIA_SOURCES)
    assert len(unverified_notes) > 0
    assert "No verified state-specific gig worker legislation is currently on record for 'Goa'" in unverified_notes[0]
