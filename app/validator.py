"""Validation: missing mandatory fields and inconsistent information."""

from datetime import date
from typing import Any

from app import config
from app.models import ExtractedFields, ValidationReport
from app.utils import format_rupees, parse_date


def is_field_missing(name: str, value: Any) -> bool:
    """A mandatory field is missing if empty, or an amount that is not > 0."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if name in config.AMOUNT_FIELDS:
        return value <= 0
    return False  # lists: [] is valid ("None" was stated explicitly)


def find_missing_fields(fields: ExtractedFields) -> list[str]:
    """Return mandatory fields that are missing or unusable."""
    return [
        name
        for name in config.MANDATORY_FIELDS
        if is_field_missing(name, getattr(fields, name))
    ]


def _check_date_formats(fields: ExtractedFields) -> list[str]:
    warnings = []
    for name in config.DATE_FIELDS:
        value = getattr(fields, name)
        if value and parse_date(value) is None:
            warnings.append(
                f"{name} '{value}' is not a recognised date (expected YYYY-MM-DD)."
            )
    return warnings


def _check_policy_period(fields: ExtractedFields) -> list[str]:
    effective = parse_date(fields.effectiveDate)
    expiry = parse_date(fields.expiryDate)
    incident = parse_date(fields.incidentDate)
    warnings = []

    if effective and expiry and expiry < effective:
        warnings.append("expiryDate is earlier than effectiveDate.")
    if incident and effective and incident < effective:
        warnings.append("incidentDate is before the policy effectiveDate.")
    if incident and expiry and incident > expiry:
        warnings.append("incidentDate is after the policy expiryDate.")
    if incident and incident > date.today():
        warnings.append("incidentDate is in the future.")
    return warnings


def _check_amounts(fields: ExtractedFields) -> list[str]:
    warnings = []
    for name in config.AMOUNT_FIELDS:
        value = getattr(fields, name)
        if value is not None and value <= 0:
            warnings.append(f"{name} must be a positive number (found {value}).")

    damage, initial = fields.estimatedDamage, fields.initialEstimate
    if damage and initial and damage > 0 and initial > 0:
        gap = abs(damage - initial) / max(damage, initial)
        if gap > config.ESTIMATE_MISMATCH_TOLERANCE:
            percent = int(config.ESTIMATE_MISMATCH_TOLERANCE * 100)
            warnings.append(
                f"estimatedDamage ({format_rupees(damage)}) and initialEstimate "
                f"({format_rupees(initial)}) differ by more than {percent}%."
            )
    return warnings


def find_warnings(fields: ExtractedFields) -> list[str]:
    """Detect inconsistent or suspicious data (informational only)."""
    return (
        _check_date_formats(fields)
        + _check_policy_period(fields)
        + _check_amounts(fields)
    )


def validate_claim(fields: ExtractedFields) -> ValidationReport:
    return ValidationReport(
        missingFields=find_missing_fields(fields),
        warnings=find_warnings(fields),
    )
