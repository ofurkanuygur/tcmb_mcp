"""Output formatters for TCMB data."""

from decimal import Decimal

from tcmb_mcp.core.exceptions import TCMBError
from tcmb_mcp.models.schemas import ConversionResult, CurrencyRate, ExchangeRates


def format_rate(rate: Decimal | None, precision: int = 4) -> str:
    """Format a rate value for display."""
    if rate is None:
        return "-"
    return f"{rate:.{precision}f}"


def format_currency_rate(rate: CurrencyRate) -> str:
    """
    Format a single currency rate for text display.

    Args:
        rate: Currency rate to format

    Returns:
        Formatted string
    """
    lines = [
        f"{rate.code} - {rate.name_tr}",
        f"  Döviz Alış:    {format_rate(rate.forex_buying)}",
        f"  Döviz Satış:   {format_rate(rate.forex_selling)}",
    ]

    if rate.banknote_buying or rate.banknote_selling:
        lines.extend([
            f"  Efektif Alış:  {format_rate(rate.banknote_buying)}",
            f"  Efektif Satış: {format_rate(rate.banknote_selling)}",
        ])

    if rate.unit != 1:
        lines.insert(1, f"  Birim: {rate.unit}")

    return "\n".join(lines)


def format_rates_text(rates: ExchangeRates) -> str:
    """
    Format exchange rates for text display.

    Args:
        rates: Exchange rates to format

    Returns:
        Formatted string suitable for console output
    """
    lines = [
        f"TCMB Döviz Kurları - {rates.date.strftime('%d.%m.%Y')}",
    ]

    if rates.bulletin_no:
        lines.append(f"Bülten No: {rates.bulletin_no}")

    lines.append("-" * 40)

    for rate in rates.rates:
        lines.append(format_currency_rate(rate))
        lines.append("")

    if rates.warning:
        lines.append(f"⚠️  {rates.warning}")

    return "\n".join(lines)


def format_conversion(result: ConversionResult) -> str:
    """
    Format conversion result for text display.

    Args:
        result: Conversion result to format

    Returns:
        Formatted string
    """
    amount_line = (
        f"{result.from_amount} {result.from_currency} = "
        f"{result.to_amount:.4f} {result.to_currency}"
    )
    lines = [
        amount_line,
        f"Kur: {result.rate:.4f} ({result.rate_type})",
        f"Tarih: {result.date.strftime('%d.%m.%Y')}",
    ]

    if result.warning:
        lines.append(f"⚠️  {result.warning}")

    return "\n".join(lines)


def format_error(error: TCMBError) -> dict:
    """
    Format error for JSON response.

    Args:
        error: TCMB error to format

    Returns:
        Error dictionary
    """
    return error.to_dict()


def format_rates_json(rates: ExchangeRates) -> dict:
    """
    Format exchange rates for JSON output.

    Args:
        rates: Exchange rates to format

    Returns:
        Dictionary suitable for JSON serialization
    """
    return rates.model_dump()
