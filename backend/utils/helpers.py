"""
Utility functions for SupplyChainAI backend.
"""
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def date_range(start: date, end: date):
    """Generate all dates between start and end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def clamp(value, min_val, max_val):
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def safe_divide(numerator, denominator, default=0.0):
    """Safe division avoiding ZeroDivisionError."""
    if denominator == 0:
        return default
    return numerator / denominator


def risk_level_to_int(level: str) -> int:
    """Convert risk level string to integer for sorting."""
    return {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(level, 0)


def format_currency(value: float, currency: str = "INR") -> str:
    """Format a number as currency string."""
    return f"{currency} {value:,.2f}"
