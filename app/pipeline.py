"""Orchestrates the steps: extract -> validate -> (optional LLM) -> route."""

from app.extractor import extract_fields
from app.llm_extractor import fill_gaps_with_llm
from app.models import ClaimResult
from app.router import route_claim
from app.validator import validate_claim


def process_claim_text(text: str) -> ClaimResult:
    """Run the full FNOL pipeline on plain text."""
    fields = extract_fields(text)
    report = validate_claim(fields)
    notes: list[str] = []

    if report.missingFields:
        fields, filled = fill_gaps_with_llm(text, fields, report.missingFields)
        if filled:
            report = validate_claim(fields)
            notes.append(f"Fields filled by LLM: {', '.join(filled)}.")

    # Routing is always plain Python rules, never an LLM decision.
    decision = route_claim(fields, report.missingFields)

    return ClaimResult(
        extractedFields=fields,
        missingFields=report.missingFields,
        recommendedRoute=decision.recommendedRoute,
        reasoning=decision.reasoning,
        warnings=report.warnings + notes,
    )
