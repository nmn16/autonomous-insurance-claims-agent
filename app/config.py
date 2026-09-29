"""Central configuration: business-rule constants and environment settings.

Routing thresholds and keywords live here so they can be changed without
touching the routing logic.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ---- Route names -----------------------------------------------------------
ROUTE_INVESTIGATION = "Investigation Flag"
ROUTE_MANUAL_REVIEW = "Manual Review"
ROUTE_SPECIALIST = "Specialist Queue"
ROUTE_FAST_TRACK = "Fast-track"

# ---- Routing rules ---------------------------------------------------------
FAST_TRACK_THRESHOLD = 25_000  # rupees; damage must be strictly below this
INVESTIGATION_KEYWORDS = ("fraud", "inconsistent", "staged")
SPECIALIST_CLAIM_TYPE = "injury"

# ---- Validation ------------------------------------------------------------
MANDATORY_FIELDS = (
    "policyNumber",
    "policyholderName",
    "effectiveDate",
    "expiryDate",
    "incidentDate",
    "incidentTime",
    "location",
    "description",
    "claimant",
    "contactDetails",
    "assetType",
    "assetId",
    "estimatedDamage",
    "claimType",
    "attachments",
    "initialEstimate",
)
AMOUNT_FIELDS = ("estimatedDamage", "initialEstimate")
DATE_FIELDS = ("effectiveDate", "expiryDate", "incidentDate")
# Warn if estimatedDamage and initialEstimate differ by more than 20%.
ESTIMATE_MISMATCH_TOLERANCE = 0.20

# ---- Document handling -----------------------------------------------------
SUPPORTED_EXTENSIONS = (".pdf", ".txt")
MAX_UPLOAD_MB = 5
# Lines that only label a section of the form (used to end multi-line values).
SECTION_HEADERS = frozenset(
    {
        "POLICY INFORMATION",
        "INCIDENT INFORMATION",
        "INVOLVED PARTIES",
        "ASSET DETAILS",
        "OTHER DETAILS",
    }
)

# ---- Optional LLM settings -------------------------------------------------
_PLACEHOLDER_KEY = "your_api_key_here"
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
if LLM_API_KEY == _PLACEHOLDER_KEY:
    LLM_API_KEY = ""
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001").strip()
