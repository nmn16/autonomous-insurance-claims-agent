from pathlib import Path

import pytest

from app.extractor import extract_fields
from app.validator import find_missing_fields, find_warnings, validate_claim

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"


def test_complete_document_has_no_missing_fields():
    text = (SAMPLE_DIR / "claim_fast_track.txt").read_text(encoding="utf-8")
    report = validate_claim(extract_fields(text))
    assert report.missingFields == []
    assert report.warnings == []


def test_sample_with_missing_fields_is_detected():
    text = (SAMPLE_DIR / "claim_missing_fields.txt").read_text(encoding="utf-8")
    report = validate_claim(extract_fields(text))
    assert report.missingFields == [
        "policyNumber", "claimant", "estimatedDamage",
        "claimType", "initialEstimate",
    ]


@pytest.mark.parametrize(
    "field_name",
    ["policyNumber", "claimant", "claimType", "estimatedDamage", "attachments"],
)
def test_each_missing_mandatory_field_is_reported(make_fields, field_name):
    fields = make_fields(**{field_name: None})
    assert field_name in find_missing_fields(fields)


def test_blank_string_counts_as_missing(make_fields):
    assert "location" in find_missing_fields(make_fields(location="   "))


@pytest.mark.parametrize("bad_amount", [None, 0, -500])
def test_invalid_or_missing_estimated_damage_is_missing(make_fields, bad_amount):
    fields = make_fields(estimatedDamage=bad_amount)
    assert "estimatedDamage" in find_missing_fields(fields)


def test_optional_fields_are_not_reported_missing(make_fields):
    fields = make_fields(thirdParties=[], attachments=[])
    assert find_missing_fields(fields) == []


def test_warns_when_incident_is_after_policy_expiry(make_fields):
    warnings = find_warnings(make_fields(incidentDate="2026-03-01"))
    assert any("after the policy expiryDate" in w for w in warnings)


def test_warns_when_incident_is_before_policy_start(make_fields):
    warnings = find_warnings(make_fields(incidentDate="2024-12-01"))
    assert any("before the policy effectiveDate" in w for w in warnings)


def test_warns_when_expiry_before_effective(make_fields):
    warnings = find_warnings(
        make_fields(effectiveDate="2025-12-31", expiryDate="2025-01-01")
    )
    assert any("earlier than effectiveDate" in w for w in warnings)


def test_warns_on_future_incident_date(make_fields):
    warnings = find_warnings(make_fields(incidentDate="2999-01-01"))
    assert any("future" in w for w in warnings)


def test_warns_on_unrecognised_date(make_fields):
    warnings = find_warnings(make_fields(incidentDate="sometime last week"))
    assert any("not a recognised date" in w for w in warnings)


def test_warns_when_estimates_differ_a_lot(make_fields):
    warnings = find_warnings(
        make_fields(estimatedDamage=100000, initialEstimate=50000)
    )
    assert any("differ" in w for w in warnings)
