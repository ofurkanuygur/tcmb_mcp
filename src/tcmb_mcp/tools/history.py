"""Tool for fetching rate history."""

from datetime import timedelta
from decimal import Decimal
from statistics import mean, stdev

from tcmb_mcp.core.config import get_settings
from tcmb_mcp.core.container import get_cache_service, get_tcmb_client
from tcmb_mcp.core.exceptions import TCMBCurrencyNotFoundError
from tcmb_mcp.core.holidays import is_holiday
from tcmb_mcp.core.logging import get_logger
from tcmb_mcp.models.enums import RateType
from tcmb_mcp.models.schemas import RateDataPoint, RateHistory, RateStatistics
from tcmb_mcp.utils.date_utils import parse_date, validate_date_range

logger = get_logger(__name__)


async def get_rate_history(
    currency: str,
    start_date: str,
    end_date: str,
    rate_type: str = "selling",
) -> dict:
    """
    Get exchange rate history for a currency over a date range.

    Args:
        currency: Currency code (e.g., "USD", "EUR")
        start_date: Start date string
        end_date: End date string
        rate_type: Rate type ("buying" or "selling")

    Returns:
        Dictionary with rate history and statistics

    Example:
        >>> history = await get_rate_history("USD", "2024-01-01", "2024-01-31")
        >>> print(history["statistics"]["avg_rate"])
        "30.45"
    """
    settings = get_settings()
    cache = await get_cache_service()
    client = await get_tcmb_client()

    # Parse and validate dates
    start = parse_date(start_date)
    end = parse_date(end_date)
    validate_date_range(start, end, max_days=365)

    currency_code = currency.upper()
    rate_type_enum = RateType.from_simple(rate_type.lower(), is_forex=True)

    logger.info(
        "fetching_rate_history",
        currency=currency_code,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )

    # Collect data points
    data_points: list[RateDataPoint] = []
    current = start
    missing_days = 0

    while current <= end:
        # Skip weekends/holidays (no data available)
        if is_holiday(current):
            current += timedelta(days=1)
            continue

        # Try cache first
        rates = None
        if settings.cache_enabled:
            rates = await cache.get_rates(
                current,
                ttl_seconds=settings.cache_ttl_historical,
            )

        # Fetch from API if not cached
        if rates is None:
            try:
                rates = await client.get_rates_for_date(current, handle_holidays=False)
                if settings.cache_enabled:
                    await cache.set_rates(rates, ttl_seconds=settings.cache_ttl_historical)
            except Exception as e:
                logger.warning("failed_to_fetch", date=current.isoformat(), error=str(e))
                missing_days += 1
                current += timedelta(days=1)
                continue

        # Extract rate for currency
        currency_rate = rates.get_rate(currency_code)
        if currency_rate is None:
            if data_points:  # Only raise if we had previous data
                logger.warning("currency_not_found", date=current.isoformat())
            else:
                raise TCMBCurrencyNotFoundError(currency_code)
            current += timedelta(days=1)
            continue

        # Add data point
        data_points.append(
            RateDataPoint(
                date=current,
                buying=currency_rate.get_unit_rate(RateType.FOREX_BUYING),
                selling=currency_rate.get_unit_rate(RateType.FOREX_SELLING),
            )
        )

        current += timedelta(days=1)

    if not data_points:
        raise TCMBCurrencyNotFoundError(currency_code)

    # Calculate statistics
    rate_values = []
    for dp in data_points:
        rate = dp.selling if rate_type_enum.is_selling else dp.buying
        if rate is not None:
            rate_values.append(float(rate))

    if rate_values:
        min_rate = Decimal(str(min(rate_values)))
        max_rate = Decimal(str(max(rate_values)))
        avg_rate = Decimal(str(mean(rate_values)))

        # Calculate change percentage
        first_rate = rate_values[0]
        last_rate = rate_values[-1]
        change_percent = Decimal(str(((last_rate - first_rate) / first_rate) * 100))

        # Calculate volatility (standard deviation)
        volatility = Decimal(str(stdev(rate_values))) if len(rate_values) > 1 else Decimal("0")

        statistics = RateStatistics(
            min_rate=min_rate.quantize(Decimal("0.0001")),
            max_rate=max_rate.quantize(Decimal("0.0001")),
            avg_rate=avg_rate.quantize(Decimal("0.0001")),
            change_percent=change_percent.quantize(Decimal("0.01")),
            volatility=volatility.quantize(Decimal("0.0001")),
        )
    else:
        statistics = None

    # Build result
    history = RateHistory(
        currency=currency_code,
        start_date=start,
        end_date=end,
        data_points=data_points,
        statistics=statistics,
        warning=f"{missing_days} gün için veri alınamadı" if missing_days > 0 else None,
    )

    logger.info(
        "rate_history_complete",
        currency=currency_code,
        data_points=len(data_points),
        missing_days=missing_days,
    )

    return history.model_dump()
