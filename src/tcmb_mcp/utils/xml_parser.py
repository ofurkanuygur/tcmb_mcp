"""Secure XML parsing for TCMB data."""

from datetime import date
from decimal import Decimal, InvalidOperation

import defusedxml.ElementTree as ET

from tcmb_mcp.core.exceptions import TCMBAPIError
from tcmb_mcp.models.schemas import CurrencyRate, ExchangeRates


def _parse_decimal(value: str | None) -> Decimal | None:
    """Safely parse a decimal value from string."""
    if value is None or value.strip() == "":
        return None
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return None


def _parse_date(date_str: str) -> date:
    """Parse TCMB date format (DD.MM.YYYY)."""
    parts = date_str.split(".")
    if len(parts) != 3:
        raise TCMBAPIError(f"Geçersiz tarih formatı: {date_str}")

    day, month, year = parts
    return date(int(year), int(month), int(day))


def parse_tcmb_xml(xml_content: str) -> ExchangeRates:
    """
    Parse TCMB XML response into ExchangeRates model.

    TCMB XML structure:
    ```xml
    <Tarih_Date Tarih="30.11.2025" Bulten_No="2025/228">
        <Currency CurrencyCode="USD">
            <Unit>1</Unit>
            <Isim>ABD DOLARI</Isim>
            <CurrencyName>US DOLLAR</CurrencyName>
            <ForexBuying>34.5678</ForexBuying>
            <ForexSelling>34.6123</ForexSelling>
            <BanknoteBuying>34.5432</BanknoteBuying>
            <BanknoteSelling>34.6543</BanknoteSelling>
            <CrossRateUSD>1.0000</CrossRateUSD>
            <CrossRateOther></CrossRateOther>
        </Currency>
        ...
    </Tarih_Date>
    ```

    Args:
        xml_content: Raw XML string from TCMB

    Returns:
        Parsed ExchangeRates object

    Raises:
        TCMBAPIError: If XML parsing fails
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise TCMBAPIError(f"XML parse hatası: {e}") from e

    # Parse date and bulletin number
    date_str = root.get("Tarih")
    if not date_str:
        raise TCMBAPIError("XML'de tarih bilgisi bulunamadı")

    rates_date = _parse_date(date_str)
    bulletin_no = root.get("Bulten_No")

    # Parse currency rates
    rates: list[CurrencyRate] = []

    for currency_elem in root.findall("Currency"):
        code = currency_elem.get("CurrencyCode")
        if not code:
            continue

        # Extract text content from child elements
        def get_text(tag: str) -> str | None:
            elem = currency_elem.find(tag)
            return elem.text if elem is not None else None

        # Parse unit (default 1)
        unit_str = get_text("Unit")
        unit = int(unit_str) if unit_str else 1

        rate = CurrencyRate(
            code=code,
            name=get_text("CurrencyName") or code,
            name_tr=get_text("Isim") or code,
            unit=unit,
            forex_buying=_parse_decimal(get_text("ForexBuying")),
            forex_selling=_parse_decimal(get_text("ForexSelling")),
            banknote_buying=_parse_decimal(get_text("BanknoteBuying")),
            banknote_selling=_parse_decimal(get_text("BanknoteSelling")),
            cross_rate_usd=_parse_decimal(get_text("CrossRateUSD")),
            cross_rate_other=_parse_decimal(get_text("CrossRateOther")),
        )
        rates.append(rate)

    return ExchangeRates(
        date=rates_date,
        bulletin_no=bulletin_no,
        rates=rates,
        warning=None,
    )
