"""Tools for fetching exchange rates."""

from datetime import date

from tcmb_mcp.core.config import get_settings
from tcmb_mcp.core.container import get_cache_service, get_tcmb_client
from tcmb_mcp.core.logging import get_logger
from tcmb_mcp.utils.date_utils import parse_date

logger = get_logger(__name__)


async def get_current_rates(currencies: list[str] | None = None) -> dict:
    """
    Get current exchange rates from TCMB.

    Args:
        currencies: Optional list of currency codes to filter.
                   If None, returns all available currencies.

    Returns:
        Dictionary with exchange rates data

    Example:
        >>> rates = await get_current_rates(["USD", "EUR"])
        >>> print(rates["rates"][0]["code"])
        "USD"
    """
    settings = get_settings()
    cache = await get_cache_service()
    client = await get_tcmb_client()

    today = date.today()

    # Try cache first
    if settings.cache_enabled:
        cached = await cache.get_rates(today, ttl_seconds=settings.cache_ttl_today)
        if cached:
            logger.info("rates_from_cache", date=today.isoformat())
            if currencies:
                cached = cached.filter_currencies(currencies)
            return cached.model_dump()

    # Fetch from API
    rates = await client.get_today_rates()

    # Cache the result
    if settings.cache_enabled:
        await cache.set_rates(rates, ttl_seconds=settings.cache_ttl_today)

    # Filter if requested
    if currencies:
        rates = rates.filter_currencies(currencies)

    return rates.model_dump()


async def get_historical_rates(
    date_str: str,
    currencies: list[str] | None = None,
) -> dict:
    """
    Get historical exchange rates for a specific date.

    Args:
        date_str: Date string in various formats (YYYY-MM-DD, DD.MM.YYYY, etc.)
        currencies: Optional list of currency codes to filter

    Returns:
        Dictionary with exchange rates data

    Example:
        >>> rates = await get_historical_rates("2024-01-15", ["USD"])
        >>> print(rates["date"])
        "2024-01-15"
    """
    settings = get_settings()
    cache = await get_cache_service()
    client = await get_tcmb_client()

    # Parse date
    target_date = parse_date(date_str)

    # Try cache first (historical data can be cached longer)
    if settings.cache_enabled:
        cached = await cache.get_rates(
            target_date,
            ttl_seconds=settings.cache_ttl_historical,
        )
        if cached:
            logger.info("rates_from_cache", date=target_date.isoformat())
            if currencies:
                cached = cached.filter_currencies(currencies)
            return cached.model_dump()

    # Fetch from API (with holiday handling)
    rates = await client.get_rates_for_date(target_date, handle_holidays=True)

    # Cache the result
    if settings.cache_enabled:
        await cache.set_rates(rates, ttl_seconds=settings.cache_ttl_historical)

    # Filter if requested
    if currencies:
        rates = rates.filter_currencies(currencies)

    return rates.model_dump()
