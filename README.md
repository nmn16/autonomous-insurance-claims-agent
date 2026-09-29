# Autonomous Insurance Claims Processing Agent

A small FastAPI application that reads FNOL (First Notice of Loss) documents
(PDF or TXT), extracts the important fields, finds missing or suspicious
information, and recommends which workflow the claim should go to, with a
short explanation and a JSON response.

## Project Overview

When a policyholder reports an accident, the insurer receives an FNOL form.
Someone normally reads it and decides who should handle it. This project
automates that first triage step:

1. Upload an FNOL file.
2. Get the extracted fields, the missing mandatory fields, a recommended route
   and the reasoning behind it.

## Architecture

```
   FNOL file (PDF / TXT)
            |
            v
  +----------------------+
  |  document_parser.py  |  bytes -> plain text (PyMuPDF for PDF)
  +----------------------+
            |
            v
  +----------------------+      +-------------------+
  |    extractor.py      |<-----|  llm_extractor.py |  optional, fills gaps only
  |  (labels + regex)    |      +-------------------+
  +----------------------+
            |  ExtractedFields (Pydantic)
            v
  +----------------------+
  |    validator.py      |  missingFields + warnings
  +----------------------+
            |
            v
  +----------------------+
  |      router.py       |  deterministic rules + precedence
  +----------------------+
            |
            v
     JSON response (FastAPI)
```

Flow: Document -> Text Extraction -> Field Extraction -> Validation ->
Routing Engine -> JSON Response.

## Features

- PDF and TXT upload
- Extraction of 17 FNOL fields with consistent camelCase names
- Missing mandatory field detection
- Inconsistency warnings (dates outside the policy period, estimate mismatch,
  invalid amounts)
- Four routing rules with a clearly defined precedence
- Human-readable reasoning for every decision, including which lower-priority
  rules were overridden
- Optional LLM gap-filling, with a deterministic fallback when no API key is set
- HTTP error handling: 400 / 413 / 415 / 422
- Automated tests (pytest) and 6 sample documents

## Technology Stack

| Technology | Why |
|---|---|
| Python 3.11+ | Modern type hints (`str \| None`) |
| FastAPI | Simple API, automatic validation and Swagger UI |
| Pydantic | Typed data models and validation |
| PyMuPDF | Fast PDF text extraction |
| python-dotenv | Loads the optional `.env` file |
| Anthropic SDK (optional) | Structured LLM extraction for missing fields |
| pytest + httpx | Unit and API tests |

## Installation

```
python -m venv venv
```

Windows:
```
venv\Scripts\activate
```

Linux / macOS:
```
source venv/bin/activate
```

Then:
```
pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` and set `LLM_API_KEY`.
Without a key the app uses only the rule-based extractor, and everything
still works.

## Running the Application

```
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the Swagger UI, where you can click
**POST /process-claim -> Try it out**, choose a file and press **Execute**.

## API Usage

`GET /` returns `{"message": "Autonomous Insurance Claims Processing Agent is running"}`.

`POST /process-claim` takes `multipart/form-data` with a `file` field.

```
curl -X POST "http://127.0.0.1:8000/process-claim" -F "file=@sample_documents/claim_fast_track.txt"
```

Response:

```json
{
  "extractedFields": {
    "policyNumber": "POL-2025-004521",
    "policyholderName": "Ananya Rao",
    "effectiveDate": "2025-01-15",
    "expiryDate": "2026-01-14",
    "incidentDate": "2025-06-12",
    "incidentTime": "18:45",
    "location": "Marathahalli Bridge Parking Lot, Bengaluru, Karnataka",
    "description": "While my car was parked at a shopping complex, another vehicle reversed into the rear bumper. Minor dent and paint scratches on the bumper. No injuries to anyone.",
    "claimant": "Ananya Rao",
    "thirdParties": ["Suresh Menon (driver of white Hyundai i20, KA-03-MN-7788)"],
    "contactDetails": "+91 90000 11111, ananya.rao@example.com",
    "assetType": "Car (Hatchback)",
    "assetId": "KA-01-AB-1234",
    "estimatedDamage": 18500,
    "claimType": "Collision",
    "attachments": ["damage_photos.zip", "repair_quote.pdf"],
    "initialEstimate": 18500
  },
  "missingFields": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage of ₹18,500 is below the ₹25,000 fast-track limit and no higher-priority routing condition was detected.",
  "warnings": []
}
```

`warnings` is an additive field for inconsistencies; it never changes the route.

Errors: `415` unsupported file type, `400` empty file / invalid PDF / no
readable text, `413` file too large, `422` no FNOL fields found or invalid data.

## Routing Rules

| # | Rule | Route |
|---|---|---|
| 1 | Description contains `fraud`, `inconsistent` or `staged` (case-insensitive) | Investigation Flag |
| 2 | Any mandatory field is missing | Manual Review |
| 3 | `claimType` equals `injury` (case-insensitive) | Specialist Queue |
| 4 | Estimated damage < ₹25,000 | Fast-track |
| 5 | None of the above (e.g. damage >= ₹25,000) | Manual Review (default) |

### Precedence

When several rules match, **the first one in the table above wins**:

1. Investigation Flag
2. Manual Review (missing fields)
3. Specialist Queue
4. Fast-track
5. Manual Review (fallback)

Why this order: suspicion must never be hidden by a low amount, and an
incomplete claim must not be fast-tracked or specialist-routed on data we
cannot trust. The reasoning text lists any lower-priority rules that were
overridden.

Details:
- Mandatory fields: everything in `MANDATORY_FIELDS` in `app/config.py`.
  `thirdParties` is optional. `attachments` must be stated in the form, and
  an explicit `Attachments: None` counts as provided.
- An amount that is missing, not numeric, zero or negative counts as missing.
- Keywords match at the start of a word, so `fraudulent` also triggers.

## Sample Results

| Document | Route | Why |
|---|---|---|
| `claim_fast_track.txt` | Fast-track | Damage ₹18,500, complete, no flags |
| `claim_injury.txt` | Specialist Queue | Claim type Injury, complete |
| `claim_investigation.txt` | Investigation Flag | Description mentions "fraud" |
| `claim_missing_fields.txt` | Manual Review | Missing: policyNumber, claimant, estimatedDamage, claimType, initialEstimate |
| `claim_manual_review.txt` | Manual Review | Damage ₹85,000: no rule matched, default |
| `claim_multiple_conditions.txt` | Investigation Flag | Low damage + injury + "inconsistent"/"staged": investigation wins |

Example reasoning for `claim_multiple_conditions.txt`:
> Description contains suspicious keyword(s): inconsistent, staged. Other
> matching rules with lower priority were overridden: Specialist Queue, Fast-track.

To try a PDF: `python scripts/txt_to_pdf.py sample_documents/claim_injury.txt`
and upload the generated PDF.

## Testing

```
pytest
```

Tests never call an LLM. They cover extraction, validation, every routing
rule, every precedence combination, and the API end to end (including PDF
upload and error codes).

## Design Decisions

- **Routing is deterministic.** Same input, same route, every time. It can be
  unit-tested, audited and explained.
- **Extraction and routing are separate.** Extraction can be improved (regex,
  LLM, OCR) without touching the business rules, and the rules can be tested
  without any document.
- **Validation happens before routing.** Routing must know which fields are
  missing, and a claim with unusable data must not be fast-tracked.
- **The LLM never controls the decision.** It is optional, may only fill
  missing fields, must return JSON matching a Pydantic schema, and is ignored
  on any error. The route is always chosen by Python rules.
- **Constants live in `config.py`.** The threshold and keywords can be changed
  in one place.
- **camelCase model fields** match the required JSON exactly, so no
  translation layer is needed.

## Limitations

- Only dummy FNOL documents were used for development.
- The extractor expects "Label: value" style forms; unusual layouts (tables,
  free-form narrative) need better extraction.
- Scanned PDFs (images) are not supported because there is no OCR.
- Keyword matching is simple: "not staged" would still trigger the flag.
- Amounts in words or lakh notation ("1.5 lakh") are not parsed.
- This is a learning/assessment project, not production insurance software.
  No real insurer systems are integrated.

## Future Improvements

- OCR for scanned PDFs (e.g. Tesseract)
- Stronger LLM extraction for unstructured documents
- Database persistence of claims and decisions
- Authentication and rate limiting
- Audit logging of every decision
- A human review dashboard
- Better fraud signals (duplicate claims, claim history, geo/time checks)
