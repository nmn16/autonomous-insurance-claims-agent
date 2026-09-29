"""Pydantic models shared across the application.

Field names use camelCase on purpose so the Python models, the JSON output
and the FNOL field list in the assignment all use exactly the same names.
"""

from pydantic import BaseModel, Field


class ExtractedFields(BaseModel):
    """All fields extracted from one FNOL document."""

    # Policy information
    policyNumber: str | None = None
    policyholderName: str | None = None
    effectiveDate: str | None = None
    expiryDate: str | None = None
    # Incident information
    incidentDate: str | None = None
    incidentTime: str | None = None
    location: str | None = None
    description: str | None = None
    # Involved parties
    claimant: str | None = None
    thirdParties: list[str] = Field(default_factory=list)
    contactDetails: str | None = None
    # Asset details
    assetType: str | None = None
    assetId: str | None = None
    estimatedDamage: int | float | None = None
    # Other mandatory fields
    claimType: str | None = None
    # None = not stated in the document, [] = document explicitly says "None"
    attachments: list[str] | None = None
    initialEstimate: int | float | None = None


class ValidationReport(BaseModel):
    """Result of validating the extracted fields."""

    missingFields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    """Result of the routing engine."""

    recommendedRoute: str
    reasoning: str


class ClaimResult(BaseModel):
    """Final API response."""

    extractedFields: ExtractedFields
    missingFields: list[str]
    recommendedRoute: str
    reasoning: str
    warnings: list[str] = Field(default_factory=list)
