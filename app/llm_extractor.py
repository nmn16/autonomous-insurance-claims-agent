"""Optional LLM helper that fills gaps left by the rule-based extractor.

Safety rules:
* It only runs when LLM_API_KEY is set AND mandatory fields are missing.
* It may only fill fields that are still missing; it never overwrites.
* The reply is validated with the ExtractedFields Pydantic schema.
* Any failure is logged and ignored, so the pipeline never breaks.
* It never makes the routing decision; router.py does that in plain Python.
"""

import json
import logging

from app import config
from app.models import ExtractedFields
from app.validator import is_field_missing

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You extract fields from insurance FNOL (First Notice of Loss) documents. "
    "Return ONLY one JSON object that follows the given JSON schema. "
    "Use null for any value that is not explicitly stated in the document. "
    "Never guess or invent values. Dates must be YYYY-MM-DD. "
    "Amounts must be plain numbers in rupees."
)


def is_llm_configured() -> bool:
    return bool(config.LLM_API_KEY)


def _request_structured_json(text: str) -> dict:
    """Ask the model for JSON matching the ExtractedFields schema."""
    import anthropic  # imported lazily so the app runs without a key

    client = anthropic.Anthropic(api_key=config.LLM_API_KEY)
    schema = json.dumps(ExtractedFields.model_json_schema())
    response = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"JSON schema:\n{schema}\n\nFNOL document:\n{text}",
            }
        ],
    )
    reply = "".join(
        block.text for block in response.content if block.type == "text"
    )
    start, end = reply.find("{"), reply.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM reply did not contain a JSON object.")
    return json.loads(reply[start : end + 1])


def fill_gaps_with_llm(
    text: str, fields: ExtractedFields, missing_fields: list[str]
) -> tuple[ExtractedFields, list[str]]:
    """Return (possibly improved fields, names of fields the LLM filled)."""
    if not missing_fields or not is_llm_configured():
        return fields, []

    try:
        data = _request_structured_json(text)
        known = {
            key: value
            for key, value in data.items()
            if value is not None and key in ExtractedFields.model_fields
        }
        candidate = ExtractedFields.model_validate(known)
    except Exception as exc:  # LLM problems must never break the pipeline
        logger.warning("LLM extraction skipped: %s", exc)
        return fields, []

    updates = {}
    for name in missing_fields:
        value = getattr(candidate, name)
        if isinstance(value, list) and not value:
            continue  # an empty list from the LLM is a guess, not a fact
        if not is_field_missing(name, value):
            updates[name] = value

    if not updates:
        return fields, []
    return fields.model_copy(update=updates), list(updates)
