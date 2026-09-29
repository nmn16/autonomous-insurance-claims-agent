import pytest

from app.router import find_suspicious_keywords, route_claim
from app.validator import find_missing_fields


def route(fields):
    """Validate first, then route (the same order the real pipeline uses)."""
    return route_claim(fields, find_missing_fields(fields))


# ---- Each rule on its own -------------------------------------------------
def test_low_damage_goes_to_fast_track(make_fields):
    decision = route(make_fields(estimatedDamage=10000))
    assert decision.recommendedRoute == "Fast-track"
    assert "₹25,000" in decision.reasoning


def test_high_damage_falls_back_to_manual_review(make_fields):
    decision = route(make_fields(estimatedDamage=30000))
    assert decision.recommendedRoute == "Manual Review"
    assert "defaults to Manual Review" in decision.reasoning


def test_threshold_boundary_is_exclusive(make_fields):
    assert route(make_fields(estimatedDamage=24999)).recommendedRoute == "Fast-track"
    assert route(make_fields(estimatedDamage=25000)).recommendedRoute == "Manual Review"


def test_injury_goes_to_specialist_queue(make_fields):
    fields = make_fields(claimType="injury", estimatedDamage=90000)
    assert route(fields).recommendedRoute == "Specialist Queue"


@pytest.mark.parametrize("claim_type", ["INJURY", "Injury", "  injury  "])
def test_injury_match_is_case_insensitive(make_fields, claim_type):
    fields = make_fields(claimType=claim_type)
    assert route(fields).recommendedRoute == "Specialist Queue"


def test_fraud_goes_to_investigation(make_fields):
    fields = make_fields(description="Possible fraud reported", estimatedDamage=90000)
    assert route(fields).recommendedRoute == "Investigation Flag"


@pytest.mark.parametrize(
    "description",
    ["FRAUD suspected", "Staged accident", "Inconsistent statements", "fraudulent bill"],
)
def test_keywords_are_case_insensitive(make_fields, description):
    fields = make_fields(description=description)
    assert route(fields).recommendedRoute == "Investigation Flag"


def test_missing_mandatory_field_goes_to_manual_review(make_fields):
    decision = route(make_fields(policyNumber=None))
    assert decision.recommendedRoute == "Manual Review"
    assert "policyNumber" in decision.reasoning


# ---- Precedence: Investigation > Manual Review > Specialist > Fast-track ---
def test_fraud_beats_fast_track(make_fields):
    fields = make_fields(description="fraud", estimatedDamage=10000)
    assert route(fields).recommendedRoute == "Investigation Flag"


def test_injury_beats_fast_track(make_fields):
    fields = make_fields(claimType="injury", estimatedDamage=10000)
    assert route(fields).recommendedRoute == "Specialist Queue"


def test_missing_field_beats_fast_track(make_fields):
    fields = make_fields(claimant=None, estimatedDamage=10000)
    assert route(fields).recommendedRoute == "Manual Review"


def test_missing_field_beats_specialist_queue(make_fields):
    fields = make_fields(claimType="injury", location=None)
    assert route(fields).recommendedRoute == "Manual Review"


def test_investigation_beats_missing_field(make_fields):
    fields = make_fields(description="Looks staged", policyNumber=None)
    assert route(fields).recommendedRoute == "Investigation Flag"


def test_all_rules_match_investigation_wins_and_others_are_listed(make_fields):
    fields = make_fields(
        description="Inconsistent story, staged", claimType="injury",
        estimatedDamage=10000, policyNumber=None,
    )
    decision = route(fields)
    assert decision.recommendedRoute == "Investigation Flag"
    assert "overridden" in decision.reasoning
    for lower_priority in ("Manual Review", "Specialist Queue", "Fast-track"):
        assert lower_priority in decision.reasoning


def test_missing_estimated_damage_never_fast_tracks(make_fields):
    assert route(make_fields(estimatedDamage=None)).recommendedRoute == "Manual Review"


# ---- Keyword helper --------------------------------------------------------
def test_find_suspicious_keywords_handles_empty():
    assert find_suspicious_keywords(None) == []
    assert find_suspicious_keywords("") == []
    assert find_suspicious_keywords("Nothing odd here") == []
