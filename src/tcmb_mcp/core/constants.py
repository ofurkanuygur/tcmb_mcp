"""Constants and URL helpers for TCMB MCP Pro."""

from datetime import date

# TCMB API URLs
TCMB_BASE_URL = "https://www.tcmb.gov.tr"
TCMB_TODAY_URL = f"{TCMB_BASE_URL}/kurlar/today.xml"

# Minimum date for historical data (TCMB data starts from 1996)
TCMB_MIN_DATE = date(1996, 1, 2)


def get_historical_url(target_date: date) -> str:
    """
    Generate TCMB URL for historical exchange rates.

    IMPORTANT: TCMB URL format is /kurlar/YYYYMM/DDMMYYYY.xml
    Example: 15 January 2024 -> /kurlar/202401/15012024.xml

    Args:
        target_date: The date to get rates for

    Returns:
        Full URL for the historical rates XML
    """
    folder = target_date.strftime("%Y%m")  # 202401
    filename = target_date.strftime("%d%m%Y")  # 15012024
    return f"{TCMB_BASE_URL}/kurlar/{folder}/{filename}.xml"


# Supported currencies with their Turkish names
SUPPORTED_CURRENCIES: dict[str, dict[str, str]] = {
    "USD": {"name": "US Dollar", "name_tr": "ABD Doları"},
    "EUR": {"name": "Euro", "name_tr": "Euro"},
    "GBP": {"name": "British Pound", "name_tr": "İngiliz Sterlini"},
    "CHF": {"name": "Swiss Franc", "name_tr": "İsviçre Frangı"},
    "JPY": {"name": "Japanese Yen", "name_tr": "Japon Yeni"},
    "AUD": {"name": "Australian Dollar", "name_tr": "Avustralya Doları"},
    "CAD": {"name": "Canadian Dollar", "name_tr": "Kanada Doları"},
    "SEK": {"name": "Swedish Krona", "name_tr": "İsveç Kronu"},
    "NOK": {"name": "Norwegian Krone", "name_tr": "Norveç Kronu"},
    "DKK": {"name": "Danish Krone", "name_tr": "Danimarka Kronu"},
    "SAR": {"name": "Saudi Riyal", "name_tr": "Suudi Arabistan Riyali"},
    "KWD": {"name": "Kuwaiti Dinar", "name_tr": "Kuveyt Dinarı"},
    "CNY": {"name": "Chinese Yuan", "name_tr": "Çin Yuanı"},
    "RUB": {"name": "Russian Ruble", "name_tr": "Rus Rublesi"},
    "AZN": {"name": "Azerbaijani Manat", "name_tr": "Azerbaycan Manatı"},
    "BGN": {"name": "Bulgarian Lev", "name_tr": "Bulgar Levası"},
    "RON": {"name": "Romanian Leu", "name_tr": "Rumen Leyi"},
    "IRR": {"name": "Iranian Rial", "name_tr": "İran Riyali"},
    "IQD": {"name": "Iraqi Dinar", "name_tr": "Irak Dinarı"},
    "KRW": {"name": "South Korean Won", "name_tr": "Güney Kore Wonu"},
    "PKR": {"name": "Pakistani Rupee", "name_tr": "Pakistan Rupisi"},
    "QAR": {"name": "Qatari Riyal", "name_tr": "Katar Riyali"},
    "AED": {"name": "UAE Dirham", "name_tr": "BAE Dirhemi"},
    "TRY": {"name": "Turkish Lira", "name_tr": "Türk Lirası"},
}

# Default currencies to show when no filter is specified
DEFAULT_CURRENCIES = ["USD", "EUR", "GBP", "CHF", "JPY"]
