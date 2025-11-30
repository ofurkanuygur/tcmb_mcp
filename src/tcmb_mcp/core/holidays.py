"""Turkish holidays and business day utilities."""

from datetime import date, timedelta

# Fixed official holidays (same date every year)
FIXED_HOLIDAYS: set[tuple[int, int]] = {
    (1, 1),   # Yılbaşı (New Year's Day)
    (4, 23),  # Ulusal Egemenlik ve Çocuk Bayramı
    (5, 1),   # Emek ve Dayanışma Günü
    (5, 19),  # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    (7, 15),  # Demokrasi ve Milli Birlik Günü
    (8, 30),  # Zafer Bayramı
    (10, 29), # Cumhuriyet Bayramı
}

# Religious holidays (vary by Hijri calendar, manually defined)
RELIGIOUS_HOLIDAYS: dict[date, str] = {
    # 2024
    date(2024, 4, 10): "Ramazan Bayramı",
    date(2024, 4, 11): "Ramazan Bayramı",
    date(2024, 4, 12): "Ramazan Bayramı",
    date(2024, 6, 16): "Kurban Bayramı",
    date(2024, 6, 17): "Kurban Bayramı",
    date(2024, 6, 18): "Kurban Bayramı",
    date(2024, 6, 19): "Kurban Bayramı",
    # 2025
    date(2025, 3, 30): "Ramazan Bayramı",
    date(2025, 3, 31): "Ramazan Bayramı",
    date(2025, 4, 1): "Ramazan Bayramı",
    date(2025, 6, 6): "Kurban Bayramı",
    date(2025, 6, 7): "Kurban Bayramı",
    date(2025, 6, 8): "Kurban Bayramı",
    date(2025, 6, 9): "Kurban Bayramı",
    # 2026
    date(2026, 3, 20): "Ramazan Bayramı",
    date(2026, 3, 21): "Ramazan Bayramı",
    date(2026, 3, 22): "Ramazan Bayramı",
    date(2026, 5, 27): "Kurban Bayramı",
    date(2026, 5, 28): "Kurban Bayramı",
    date(2026, 5, 29): "Kurban Bayramı",
    date(2026, 5, 30): "Kurban Bayramı",
}


def is_weekend(d: date) -> bool:
    """Check if date is a weekend (Saturday=5, Sunday=6)."""
    return d.weekday() >= 5


def is_fixed_holiday(d: date) -> bool:
    """Check if date is a fixed official holiday."""
    return (d.month, d.day) in FIXED_HOLIDAYS


def is_religious_holiday(d: date) -> bool:
    """Check if date is a religious holiday."""
    return d in RELIGIOUS_HOLIDAYS


def is_holiday(d: date) -> bool:
    """
    Check if the given date is a non-business day.

    A date is considered a holiday if it's:
    - A weekend (Saturday or Sunday)
    - A fixed official holiday
    - A religious holiday

    Args:
        d: Date to check

    Returns:
        True if the date is a holiday/non-business day
    """
    return is_weekend(d) or is_fixed_holiday(d) or is_religious_holiday(d)


def get_holiday_name(d: date) -> str | None:
    """Get the name of the holiday for a given date."""
    if is_weekend(d):
        return "Cumartesi" if d.weekday() == 5 else "Pazar"

    if is_fixed_holiday(d):
        names = {
            (1, 1): "Yılbaşı",
            (4, 23): "Ulusal Egemenlik ve Çocuk Bayramı",
            (5, 1): "Emek ve Dayanışma Günü",
            (5, 19): "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
            (7, 15): "Demokrasi ve Milli Birlik Günü",
            (8, 30): "Zafer Bayramı",
            (10, 29): "Cumhuriyet Bayramı",
        }
        return names.get((d.month, d.day))

    return RELIGIOUS_HOLIDAYS.get(d)


def get_previous_business_day(d: date) -> date:
    """
    Find the most recent business day before the given date.

    Args:
        d: Starting date

    Returns:
        The previous business day

    Raises:
        ValueError: If no business day is found within 30 days
    """
    current = d - timedelta(days=1)
    max_lookback = 30

    while is_holiday(current):
        current -= timedelta(days=1)
        if (d - current).days > max_lookback:
            raise ValueError(f"{max_lookback} gün içinde iş günü bulunamadı")

    return current


def get_next_business_day(d: date) -> date:
    """
    Find the next business day after the given date.

    Args:
        d: Starting date

    Returns:
        The next business day

    Raises:
        ValueError: If no business day is found within 30 days
    """
    current = d + timedelta(days=1)
    max_lookforward = 30

    while is_holiday(current):
        current += timedelta(days=1)
        if (current - d).days > max_lookforward:
            raise ValueError(f"{max_lookforward} gün içinde iş günü bulunamadı")

    return current


def get_last_business_day() -> date:
    """Get the most recent business day (today if business day, else previous)."""
    today = date.today()
    if is_holiday(today):
        return get_previous_business_day(today)
    return today
