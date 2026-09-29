"""Small helpers shared by the extractor, validator and router."""

import re
from datetime import date, datetime

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%B %d, %Y",
    "%b %d, %Y",
)

# Values that mean "nothing here" in a form.
NOT_PROVIDED = frozenset(
    {"", "none", "n/a", "na", "nil", "no", "not applicable",
     "not provided", "-"}
)

_CURRENCY_PATTERN = re.compile(r"(?i)₹|\brs\.?|\binr\b")
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def normalize_key(label: str) -> str:
    """'Policy Number' -> 'policynumber' (used to match label aliases)."""
    return re.sub(r"[^a-z0-9]", "", label.lower())


def parse_date(value: str | None) -> date | None:
    """Parse a date in one of the supported formats, else return None."""
    if not value:
        return None
    cleaned = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    return None


def parse_amount(value: str | None) -> int | float | None:
    """Turn '₹1,20,000' or 'Rs. 18500/-' into a number; None if no number."""
    if value is None:
        return None
    cleaned = _CURRENCY_PATTERN.sub("", value).replace(",", "")
    match = _NUMBER_PATTERN.search(cleaned)
    if match is None:
        return None
    number = float(match.group())
    return int(number) if number.is_integer() else number


def format_rupees(amount: int | float) -> str:
    """25000 -> '₹25,000'."""
    return f"₹{amount:,}"
