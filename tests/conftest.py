import pytest

from app import config
from app.models import ExtractedFields

COMPLETE_FIELDS = {
    "policyNumber": "POL-2025-000001",
    "policyholderName": "Test User",
    "effectiveDate": "2025-01-01",
    "expiryDate": "2025-12-31",
    "incidentDate": "2025-06-01",
    "incidentTime": "10:30",
    "location": "Bengaluru",
    "description": "Minor scratch on the door.",
    "claimant": "Test User",
    "thirdParties": [],
    "contactDetails": "+91 90000 00000",
    "assetType": "Car",
    "assetId": "KA-01-XX-0001",
    "estimatedDamage": 10000,
    "claimType": "Collision",
    "attachments": ["photo.jpg"],
    "initialEstimate": 10000,
}


@pytest.fixture(autouse=True)
def disable_llm(monkeypatch):
    """Tests must be deterministic, so never call an LLM."""
    monkeypatch.setattr(config, "LLM_API_KEY", "")


@pytest.fixture
def make_fields():
    """Build a complete, valid claim; override any field per test."""

    def _make(**overrides) -> ExtractedFields:
        return ExtractedFields(**{**COMPLETE_FIELDS, **overrides})

    return _make
