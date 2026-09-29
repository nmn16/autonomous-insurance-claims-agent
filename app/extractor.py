"""Rule-based field extraction (deterministic, no API key needed).

Strategy:
1. Read every "Label: value" line and map the label to a known field
   using an alias table (so 'Date of Loss' also works for incidentDate).
2. Let the description continue over following lines until the next known
   label or section header.
3. Convert values: dates -> YYYY-MM-DD, amounts -> numbers, lists -> lists.
4. A regex fallback finds the policy number if its label is missing.

Nothing is invented: a value that is not found stays None (or []).
"""

import re

from app import config
from app.exceptions import ExtractionError
from app.models import ExtractedFields
from app.utils import (
    NOT_PROVIDED,
    normalize_key,
    parse_amount,
    parse_date,
)

# field name -> accepted labels (normalised: lowercase letters/digits only)
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "policyNumber": ("policynumber", "policyno", "policyid"),
    "policyholderName": (
        "policyholdername", "policyholder", "insuredname", "nameofinsured",
    ),
    "effectiveDate": (
        "effectivedate", "policyeffectivedate", "policystartdate",
    ),
    "expiryDate": (
        "expirydate", "policyexpirydate", "expirationdate", "policyenddate",
    ),
    "incidentDate": (
        "incidentdate", "dateofloss", "dateofincident", "lossdate",
    ),
    "incidentTime": ("incidenttime", "timeofloss", "timeofincident"),
    "location": (
        "location", "incidentlocation", "placeofincident", "locationofloss",
    ),
    "description": (
        "description", "descriptionofincident", "incidentdescription",
        "descriptionofloss",
    ),
    "claimant": ("claimant", "claimantname"),
    "thirdParties": (
        "thirdparties", "thirdparty", "thirdpartydetails",
        "thirdpartiesinvolved",
    ),
    "contactDetails": (
        "contactdetails", "contactnumber", "contactphone", "phone",
        "mobile", "email", "contactemail",
    ),
    "assetType": ("assettype", "vehicletype", "typeofasset"),
    "assetId": (
        "assetid", "vehicleregistration", "vehicleregistrationnumber",
        "registrationnumber", "vehicleno",
    ),
    "estimatedDamage": (
        "estimateddamage", "estimateddamageamount", "damageestimate",
    ),
    "claimType": ("claimtype", "typeofclaim"),
    "attachments": ("attachments", "attachmentlist", "documentsattached"),
    "initialEstimate": ("initialestimate", "initialrepairestimate"),
}

ALIAS_TO_FIELD: dict[str, str] = {
    alias: field
    for field, aliases in FIELD_ALIASES.items()
    for alias in aliases
}

# "Label: value" at the start of a line.
KEY_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /().'-]{0,40}?)\s*:\s*(.*)$")
POLICY_NUMBER_FALLBACK = re.compile(r"\bPOL-[A-Z0-9-]+\b")
# Split on ';' or on commas that are NOT inside parentheses.
LIST_SPLIT_PATTERN = re.compile(r";|,(?![^()]*\))")


def _collect_raw_values(text: str) -> dict[str, str]:
    """Map field name -> raw string value for every recognised label."""
    values: dict[str, str] = {}
    current_field: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.upper() in config.SECTION_HEADERS:
            current_field = None
            continue

        match = KEY_VALUE_PATTERN.match(stripped)
        field = ALIAS_TO_FIELD.get(normalize_key(match.group(1))) if match else None

        if field:
            value = match.group(2).strip()
            if field not in values:
                values[field] = value
            elif field == "contactDetails" and value:
                values[field] = f"{values[field]}, {value}"
            current_field = field
        elif current_field == "description":
            values["description"] = f"{values['description']} {stripped}".strip()

    return values


def _clean_text(value: str | None) -> str | None:
    """Collapse whitespace; treat 'N/A', 'none', '' as not provided."""
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return None if cleaned.lower() in NOT_PROVIDED else cleaned


def _normalize_date(value: str | None) -> str | None:
    """Return YYYY-MM-DD when the date is recognised, else the cleaned text."""
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    parsed = parse_date(cleaned)
    return parsed.isoformat() if parsed else cleaned


def _split_list(value: str | None) -> list[str] | None:
    """None = label absent/blank, [] = explicitly 'None', else the items."""
    if value is None or not value.strip():
        return None
    if " ".join(value.split()).lower() in NOT_PROVIDED:
        return []
    parts = LIST_SPLIT_PATTERN.split(value)
    return [part.strip() for part in parts if part.strip()]


def extract_fields(text: str) -> ExtractedFields:
    """Extract all FNOL fields from plain text using rules only."""
    if not text or not text.strip():
        raise ExtractionError("Document text is empty; nothing to extract.")

    raw = _collect_raw_values(text)
    policy_fallback = POLICY_NUMBER_FALLBACK.search(text)
    if not raw and not policy_fallback:
        raise ExtractionError(
            "No recognisable FNOL fields (e.g. 'Policy Number:') were found."
        )

    policy_number = _clean_text(raw.get("policyNumber"))
    if policy_number is None and policy_fallback:
        policy_number = policy_fallback.group()

    return ExtractedFields(
        policyNumber=policy_number,
        policyholderName=_clean_text(raw.get("policyholderName")),
        effectiveDate=_normalize_date(raw.get("effectiveDate")),
        expiryDate=_normalize_date(raw.get("expiryDate")),
        incidentDate=_normalize_date(raw.get("incidentDate")),
        incidentTime=_clean_text(raw.get("incidentTime")),
        location=_clean_text(raw.get("location")),
        description=_clean_text(raw.get("description")),
        claimant=_clean_text(raw.get("claimant")),
        thirdParties=_split_list(raw.get("thirdParties")) or [],
        contactDetails=_clean_text(raw.get("contactDetails")),
        assetType=_clean_text(raw.get("assetType")),
        assetId=_clean_text(raw.get("assetId")),
        estimatedDamage=parse_amount(raw.get("estimatedDamage")),
        claimType=_clean_text(raw.get("claimType")),
        attachments=_split_list(raw.get("attachments")),
        initialEstimate=parse_amount(raw.get("initialEstimate")),
    )
