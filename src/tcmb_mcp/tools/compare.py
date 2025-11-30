"""Tool for comparing multiple currencies."""

from datetime import date, timedelta
from decimal import Decimal

from tcmb_mcp.core.config import get_settings
from tcmb_mcp.core.container import get_cache_service, get_tcmb_client
from tcmb_mcp.core.holidays import get_previous_business_day, is_holiday
from tcmb_mcp.core.logging import get_logger
from tcmb_mcp.models.enums import RateType

logger = get_logger(__name__)


async def compare_currencies(
    target_currencies: list[str],
    base_currency: str = "TRY",
    days: int = 30,
) -> dict:
    """
    Compare multiple currencies over a period.

    Args:
        target_currencies: List of currency codes to compare
        base_currency: Base currency for comparison (default: TRY)
        days: Number of days to look back (default: 30)

    Returns:
        Dictionary with comparison data

    Example:
        >>> comparison = await compare_currencies(["USD", "EUR", "GBP"], days=30)
        >>> print(comparison["currencies"]["USD"]["change_percent"])
        "2.45"
    """
    settings = get_settings()
    cache = await get_cache_service()
    client = await get_tcmb_client()

    target_codes = [c.upper() for c in target_currencies]
    base_code = base_currency.upper()

    logger.info(
        "comparing_currencies",
        targets=target_codes,
        base=base_code,
        days=days,
    )

    # Determine date range
    end_date = date.today()
    if is_holiday(end_date):
        end_date = get_previous_business_day(end_date)

    start_date = end_date - timedelta(days=days)
    if is_holiday(start_date):
        start_date = get_previous_business_day(start_date)

    # Fetch current and historical rates
    current_rates = await client.get_today_rates()

    # Try to get historical rates
    historical_rates = None
    if settings.cache_enabled:
        historical_rates = await cache.get_rates(
            start_date,
            ttl_seconds=settings.cache_ttl_historical,
        )

    if historical_rates is None:
        try:
            historical_rates = await client.get_rates_for_date(
                start_date,
                handle_holidays=True,
            )
            if settings.cache_enabled:
                await cache.set_rates(
                    historical_rates,
                    ttl_seconds=settings.cache_ttl_historical,
                )
        except Exception as e:
            logger.warning("failed_to_fetch_historical", error=str(e))
            historical_rates = None

    # Build comparison for each currency
    rate_type = RateType.FOREX_SELLING
    currencies_data: dict = {}

    for code in target_codes:
        current_rate = current_rates.get_rate(code)
        if current_rate is None:
            currencies_data[code] = {
                "error": f"'{code}' para birimi bulunamadı",
            }
            continue

        current_value = current_rate.get_unit_rate(rate_type)
        if current_value is None:
            currencies_data[code] = {
                "error": f"'{code}' için kur değeri bulunamadı",
            }
            continue

        currency_data = {
            "code": code,
            "name": current_rate.name,
            "name_tr": current_rate.name_tr,
            "unit": current_rate.unit,
            "current_rate": str(current_value.quantize(Decimal("0.0001"))),
            "date": current_rates.date.isoformat(),
        }

        # Calculate change if historical data available
        if historical_rates:
            historical_rate = historical_rates.get_rate(code)
            if historical_rate:
                historical_value = historical_rate.get_unit_rate(rate_type)
                if historical_value and historical_value != 0:
                    change = current_value - historical_value
                    change_percent = (change / historical_value) * 100

                    currency_data["historical_rate"] = str(
                        historical_value.quantize(Decimal("0.0001"))
                    )
                    currency_data["historical_date"] = historical_rates.date.isoformat()
                    currency_data["change"] = str(change.quantize(Decimal("0.0001")))
                    currency_data["change_percent"] = str(
                        change_percent.quantize(Decimal("0.01"))
                    )

        currencies_data[code] = currency_data

    result = {
        "base_currency": base_code,
        "comparison_period_days": days,
        "current_date": current_rates.date.isoformat(),
        "historical_date": historical_rates.date.isoformat() if historical_rates else None,
        "currencies": currencies_data,
        "warning": current_rates.warning,
    }

    logger.info(
        "comparison_complete",
        currencies_count=len(target_codes),
    )

    return result
