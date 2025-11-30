"""Date parsing and validation utilities."""

from datetime import date, timedelta

from dateutil import parser as date_parser

from tcmb_mcp.core.constants import TCMB_MIN_DATE
from tcmb_mcp.core.exceptions import TCMBDateRangeError


def parse_date(date_str: str) -> date:
    """
    Parse a date string into a date object.

    Supports various formats including:
    - YYYY-MM-DD (ISO format)
    - DD.MM.YYYY (Turkish format)
    - DD/MM/YYYY
    - Natural language (e.g., "yesterday", "last week")

    Args:
        date_str: Date string to parse

    Returns:
        Parsed date object

    Raises:
        TCMBDateRangeError: If the date cannot be parsed
    """
    try:
        # Handle special keywords
        date_lower = date_str.lower().strip()
        today = date.today()

        if date_lower in ("today", "bugün"):
            return today
        elif date_lower in ("yesterday", "dün"):
            return today - timedelta(days=1)

        # Try to parse with dateutil
        parsed = date_parser.parse(date_str, dayfirst=True)
        return parsed.date()

    except (ValueError, TypeError) as e:
        raise TCMBDateRangeError(f"Geçersiz tarih formatı: '{date_str}'") from e


def format_date(d: date, format_type: str = "iso") -> str:
    """
    Format a date object to string.

    Args:
        d: Date to format
        format_type: Format type ('iso', 'turkish', 'display')

    Returns:
        Formatted date string
    """
    formats = {
        "iso": "%Y-%m-%d",
        "turkish": "%d.%m.%Y",
        "display": "%d %B %Y",
        "tcmb_folder": "%Y%m",
        "tcmb_file": "%d%m%Y",
    }
    fmt = formats.get(format_type, "%Y-%m-%d")
    return d.strftime(fmt)


def validate_date_range(
    start_date: date,
    end_date: date,
    max_days: int = 365,
) -> None:
    """
    Validate a date range.

    Args:
        start_date: Start of the range
        end_date: End of the range
        max_days: Maximum allowed days in range

    Raises:
        TCMBDateRangeError: If the range is invalid
    """
    today = date.today()

    # Check if dates are in valid range
    if start_date < TCMB_MIN_DATE:
        raise TCMBDateRangeError(
            f"Başlangıç tarihi {TCMB_MIN_DATE.isoformat()}'den önce olamaz"
        )

    if end_date > today:
        raise TCMBDateRangeError("Bitiş tarihi bugünden sonra olamaz")

    # Check order
    if start_date > end_date:
        raise TCMBDateRangeError("Başlangıç tarihi bitiş tarihinden sonra olamaz")

    # Check range size
    days_diff = (end_date - start_date).days
    if days_diff > max_days:
        raise TCMBDateRangeError(
            f"Tarih aralığı en fazla {max_days} gün olabilir ({days_diff} gün seçildi)"
        )


def get_date_range(start_date: date, end_date: date) -> list[date]:
    """
    Generate a list of dates in a range.

    Args:
        start_date: Start of the range (inclusive)
        end_date: End of the range (inclusive)

    Returns:
        List of dates in the range
    """
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates
