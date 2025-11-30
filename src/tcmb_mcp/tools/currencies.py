"""Tool for listing available currencies."""

from typing import Any

from tcmb_mcp.core.constants import SUPPORTED_CURRENCIES
from tcmb_mcp.core.container import get_tcmb_client
from tcmb_mcp.core.logging import get_logger

logger = get_logger(__name__)


async def list_currencies(include_rates: bool = False) -> dict[str, Any]:
    """
    List all available currencies from TCMB.

    Args:
        include_rates: If True, include current rates for each currency

    Returns:
        Dictionary with list of currencies

    Example:
        >>> currencies = await list_currencies()
        >>> print(currencies["currencies"][0])
        {"code": "USD", "name": "US Dollar", "name_tr": "ABD Doları"}
    """
    logger.info("listing_currencies", include_rates=include_rates)

    currencies: list[dict[str, Any]] = [
        {
            "code": code,
            "name": info["name"],
            "name_tr": info["name_tr"],
        }
        for code, info in SUPPORTED_CURRENCIES.items()
    ]

    if include_rates:
        # Fetch current rates and add to each currency
        client = await get_tcmb_client()
        rates = await client.get_today_rates()

        for currency in currencies:
            rate = rates.get_rate(currency["code"])
            if rate:
                currency["current_rate"] = {
                    "forex_buying": str(rate.forex_buying) if rate.forex_buying else None,
                    "forex_selling": str(rate.forex_selling) if rate.forex_selling else None,
                    "unit": rate.unit,
                }

    return {
        "currencies": currencies,
        "count": len(currencies),
    }
