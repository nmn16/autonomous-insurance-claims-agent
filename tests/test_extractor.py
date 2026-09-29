import pytest

from app.exceptions import ExtractionError
from app.extractor import extract_fields

SAMPLE_TEXT = """\
POLICY INFORMATION
Policy Number: POL-2025-004521
Policyholder Name: Ananya Rao
Effective Date: 15/01/2025
Expiry Date: 2026-01-14

INCIDENT INFORMATION
Incident Date: 12 June 2025
Incident Time: 18:45
Location: Bengaluru
Description: Rear bumper hit while parked.
Minor scratches only.

INVOLVED PARTIES
Claimant: Ananya Rao
Third Parties: Suresh Menon (driver, KA-03-MN-7788); Ravi K
Contact Details: +91 90000 11111

ASSET DETAILS
Asset Type: Car
Asset ID: KA-01-AB-1234
Estimated Damage: Rs. 1,20,000/-

OTHER DETAILS
Claim Type: INJURY
Attachments: None
Initial Estimate: ₹95,000
"""


@pytest.fixture
def fields():
    return extract_fields(SAMPLE_TEXT)


def test_extracts_policy_number(fields):
    assert fields.policyNumber == "POL-2025-004521"


def test_extracts_claimant(fields):
    assert fields.claimant == "Ananya Rao"


def test_extracts_and_normalizes_incident_date(fields):
    assert fields.incidentDate == "2025-06-12"


def test_normalizes_other_date_formats(fields):
    assert fields.effectiveDate == "2025-01-15"


def test_extracts_estimated_damage_as_number(fields):
    assert fields.estimatedDamage == 120000
    assert fields.initialEstimate == 95000


def test_extracts_claim_type(fields):
    assert fields.claimType == "INJURY"


def test_multiline_description_is_joined(fields):
    assert fields.description == "Rear bumper hit while parked. Minor scratches only."


def test_third_parties_are_split_but_not_inside_brackets(fields):
    assert fields.thirdParties == ["Suresh Menon (driver, KA-03-MN-7788)", "Ravi K"]


def test_explicit_none_attachments_is_empty_list(fields):
    assert fields.attachments == []


def test_missing_fields_are_none_not_invented():
    result = extract_fields("Policy Number: POL-1")
    assert result.claimant is None
    assert result.estimatedDamage is None
    assert result.attachments is None
    assert result.thirdParties == []


def test_labels_are_case_insensitive():
    result = extract_fields("POLICY NUMBER: POL-9\ndate of loss: 2025-02-02")
    assert result.policyNumber == "POL-9"
    assert result.incidentDate == "2025-02-02"


def test_policy_number_regex_fallback():
    result = extract_fields("Claim for POL-2025-000123 was filed\nClaimant: A")
    assert result.policyNumber == "POL-2025-000123"


def test_non_numeric_damage_becomes_none():
    result = extract_fields("Estimated Damage: Not yet assessed")
    assert result.estimatedDamage is None


def test_unrecognised_document_raises():
    with pytest.raises(ExtractionError):
        extract_fields("Hello, this is just a random letter with no form fields.")


def test_empty_text_raises():
    with pytest.raises(ExtractionError):
        extract_fields("   ")
