"""Tool for currency conversion."""

from decimal import Decimal, InvalidOperation

from tcmb_mcp.core.container import get_tcmb_client
from tcmb_mcp.core.exceptions import TCMBCurrencyNotFoundError, TCMBError
from tcmb_mcp.core.logging import get_logger
from tcmb_mcp.models.enums import RateType
from tcmb_mcp.models.schemas import ConversionResult

logger = get_logger(__name__)


async def convert_currency(
    amount: float | str,
    from_currency: str,
    to_currency: str,
    rate_type: str = "selling",
) -> dict:
    """
    Convert between currencies using TCMB rates.

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "USD", "EUR", "TRY")
        to_currency: Target currency code
        rate_type: Rate type to use ("buying" or "selling")

    Returns:
        Dictionary with conversion result

    Example:
        >>> result = await convert_currency(100, "USD", "TRY", "selling")
        >>> print(result["to_amount"])
        "3026.78"

    Notes:
        - For TRY to foreign: Uses buying rate (bank buys foreign currency)
        - For foreign to TRY: Uses selling rate (bank sells foreign currency)
        - Cross rates use TCMB's CrossRateUSD when available for better accuracy
    """
    # Parse amount
    try:
        amount_decimal = Decimal(str(amount))
    except InvalidOperation as e:
        raise TCMBError(f"Geçersiz miktar: {amount}") from e

    if amount_decimal <= 0:
        raise TCMBError("Miktar sıfırdan büyük olmalıdır")

    # Normalize currency codes
    from_code = from_currency.upper()
    to_code = to_currency.upper()

    # Determine rate type
    is_forex = True  # Using forex rates by default
    rate_type_enum = RateType.from_simple(rate_type.lower(), is_forex)

    logger.info(
        "converting_currency",
        amount=str(amount_decimal),
        from_currency=from_code,
        to_currency=to_code,
        rate_type=rate_type_enum.value,
    )

    # Fetch current rates
    client = await get_tcmb_client()
    rates = await client.get_today_rates()

    # Get rates for currencies
    from_rate = rates.get_rate(from_code) if from_code != "TRY" else None
    to_rate = rates.get_rate(to_code) if to_code != "TRY" else None

    # Validate currencies exist
    if from_code != "TRY" and from_rate is None:
        raise TCMBCurrencyNotFoundError(from_code)
    if to_code != "TRY" and to_rate is None:
        raise TCMBCurrencyNotFoundError(to_code)

    # Calculate conversion
    result_amount: Decimal
    used_rate: Decimal

    if from_code == "TRY":
        # TRY -> Foreign: Divide by rate
        assert to_rate is not None
        unit_rate = to_rate.get_unit_rate(rate_type_enum)
        if unit_rate is None or unit_rate == 0:
            raise TCMBError(f"{to_code} için {rate_type_enum.turkish_name} kuru bulunamadı")
        result_amount = amount_decimal / unit_rate
        used_rate = unit_rate

    elif to_code == "TRY":
        # Foreign -> TRY: Multiply by rate
        assert from_rate is not None
        unit_rate = from_rate.get_unit_rate(rate_type_enum)
        if unit_rate is None:
            raise TCMBError(f"{from_code} için {rate_type_enum.turkish_name} kuru bulunamadı")
        result_amount = amount_decimal * unit_rate
        used_rate = unit_rate

    else:
        # Cross conversion (Foreign -> Foreign)
        assert from_rate is not None
        assert to_rate is not None

        # Try to use TCMB cross rates first (more accurate)
        if from_code == "USD" and to_rate.cross_rate_usd:
            # USD -> X: Use target's cross rate
            result_amount = amount_decimal * to_rate.cross_rate_usd
            used_rate = to_rate.cross_rate_usd
        elif to_code == "USD" and from_rate.cross_rate_usd:
            # X -> USD: Divide by source's cross rate
            result_amount = amount_decimal / from_rate.cross_rate_usd
            used_rate = Decimal("1") / from_rate.cross_rate_usd
        else:
            # Fallback: Convert through TRY
            from_unit_rate = from_rate.get_unit_rate(rate_type_enum)
            to_unit_rate = to_rate.get_unit_rate(rate_type_enum)

            if from_unit_rate is None or to_unit_rate is None or to_unit_rate == 0:
                raise TCMBError(
                    f"{from_code} -> {to_code} dönüşümü için kur bulunamadı"
                )

            # from -> TRY -> to
            try_amount = amount_decimal * from_unit_rate
            result_amount = try_amount / to_unit_rate
            used_rate = from_unit_rate / to_unit_rate

    # Build result
    conversion = ConversionResult(
        from_currency=from_code,
        from_amount=amount_decimal,
        to_currency=to_code,
        to_amount=result_amount.quantize(Decimal("0.0001")),
        rate=used_rate.quantize(Decimal("0.0001")),
        rate_type=rate_type_enum.value,
        date=rates.date,
        warning=rates.warning,
    )

    logger.info(
        "conversion_completed",
        from_amount=str(amount_decimal),
        from_currency=from_code,
        to_amount=str(result_amount),
        to_currency=to_code,
    )

    return conversion.model_dump()
