"""Routing engine: deterministic business rules.

Priority (first match wins):
    1. Investigation Flag  - description contains a suspicious keyword
    2. Manual Review       - any mandatory field is missing
    3. Specialist Queue    - claimType is 'injury'
    4. Fast-track          - estimated damage < FAST_TRACK_THRESHOLD
    5. Manual Review       - default when nothing else matched
"""

import re

from app import config
from app.models import ExtractedFields, RoutingDecision
from app.utils import format_rupees


def find_suspicious_keywords(description: str | None) -> list[str]:
    """Case-insensitive keyword search ('FRAUD suspected' -> ['fraud'])."""
    if not description:
        return []
    return [
        keyword
        for keyword in config.INVESTIGATION_KEYWORDS
        if re.search(rf"\b{re.escape(keyword)}", description, re.IGNORECASE)
    ]


def _is_injury_claim(claim_type: str | None) -> bool:
    return (
        claim_type is not None
        and claim_type.strip().lower() == config.SPECIALIST_CLAIM_TYPE
    )


def _is_below_fast_track_limit(damage: int | float | None) -> bool:
    return damage is not None and damage < config.FAST_TRACK_THRESHOLD


def _matching_rules(
    fields: ExtractedFields, missing_fields: list[str]
) -> list[tuple[str, str]]:
    """All rules that match, as (route, reason), in priority order."""
    matches: list[tuple[str, str]] = []
    limit = format_rupees(config.FAST_TRACK_THRESHOLD)

    keywords = find_suspicious_keywords(fields.description)
    if keywords:
        matches.append((
            config.ROUTE_INVESTIGATION,
            f"Description contains suspicious keyword(s): {', '.join(keywords)}.",
        ))
    if missing_fields:
        matches.append((
            config.ROUTE_MANUAL_REVIEW,
            f"Mandatory field(s) missing: {', '.join(missing_fields)}.",
        ))
    if _is_injury_claim(fields.claimType):
        matches.append((
            config.ROUTE_SPECIALIST,
            f"Claim type is '{fields.claimType.strip()}', which must be "
            "handled by the Specialist Queue.",
        ))
    if _is_below_fast_track_limit(fields.estimatedDamage):
        matches.append((
            config.ROUTE_FAST_TRACK,
            f"Estimated damage of {format_rupees(fields.estimatedDamage)} is "
            f"below the {limit} fast-track limit and no higher-priority "
            "routing condition was detected.",
        ))
    return matches


def _fallback_reason(fields: ExtractedFields) -> str:
    limit = format_rupees(config.FAST_TRACK_THRESHOLD)
    damage = fields.estimatedDamage
    if damage is None:
        return "No routing rule matched, so the claim defaults to Manual Review."
    return (
        "No specific routing rule matched: estimated damage of "
        f"{format_rupees(damage)} is not below the {limit} fast-track limit, "
        "so the claim defaults to Manual Review."
    )


def route_claim(
    fields: ExtractedFields, missing_fields: list[str]
) -> RoutingDecision:
    """Pick the route with the highest priority and explain the decision."""
    matches = _matching_rules(fields, missing_fields)
    if not matches:
        return RoutingDecision(
            recommendedRoute=config.ROUTE_MANUAL_REVIEW,
            reasoning=_fallback_reason(fields),
        )

    route, reason = matches[0]
    overridden = [other_route for other_route, _ in matches[1:]]
    if overridden:
        reason += (
            " Other matching rules with lower priority were overridden: "
            f"{', '.join(overridden)}."
        )
    return RoutingDecision(recommendedRoute=route, reasoning=reason)
