"""Pydantic models for TCMB exchange rate data."""

from datetime import date as DateType
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from tcmb_mcp.models.enums import RateType


class CurrencyRate(BaseModel):
    """Single currency exchange rate."""

    code: str = Field(..., description="Currency code (e.g., USD, EUR)")
    name: str = Field(..., description="Currency name in English")
    name_tr: str = Field(..., description="Currency name in Turkish")
    unit: int = Field(default=1, description="Unit for rate (1 or 100)")

    forex_buying: Decimal | None = Field(None, description="Forex buying rate")
    forex_selling: Decimal | None = Field(None, description="Forex selling rate")
    banknote_buying: Decimal | None = Field(None, description="Banknote buying rate")
    banknote_selling: Decimal | None = Field(None, description="Banknote selling rate")

    # Cross rates from TCMB (more accurate for currency conversions)
    cross_rate_usd: Decimal | None = Field(
        None, description="Cross rate against USD from TCMB"
    )
    cross_rate_other: Decimal | None = Field(
        None, description="Cross rate against other currencies from TCMB"
    )

    @field_serializer(
        "forex_buying",
        "forex_selling",
        "banknote_buying",
        "banknote_selling",
        "cross_rate_usd",
        "cross_rate_other",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        """Serialize Decimal to string for JSON output."""
        if value is None:
            return None
        return str(value)

    def get_rate(self, rate_type: RateType) -> Decimal | None:
        """
        Get rate by type.

        Args:
            rate_type: The type of rate to retrieve

        Returns:
            The rate value or None if not available
        """
        rate_map = {
            RateType.FOREX_BUYING: self.forex_buying,
            RateType.FOREX_SELLING: self.forex_selling,
            RateType.BANKNOTE_BUYING: self.banknote_buying,
            RateType.BANKNOTE_SELLING: self.banknote_selling,
        }
        return rate_map.get(rate_type)

    def get_unit_rate(self, rate_type: RateType) -> Decimal | None:
        """
        Get rate normalized to single unit.

        For currencies like JPY where unit=100, this returns rate/100.

        Args:
            rate_type: The type of rate to retrieve

        Returns:
            The normalized rate value or None if not available
        """
        rate = self.get_rate(rate_type)
        if rate is None:
            return None
        return rate / Decimal(self.unit)


class ExchangeRates(BaseModel):
    """Exchange rates for a specific date."""

    date: DateType = Field(..., description="Date of the exchange rates")
    bulletin_no: str | None = Field(None, description="TCMB bulletin number")
    rates: list[CurrencyRate] = Field(default_factory=list, description="List of currency rates")
    warning: str | None = Field(
        None,
        description="Warning message (e.g., when using previous business day for holidays)",
    )

    def get_rate(self, code: str) -> CurrencyRate | None:
        """
        Find rate for a specific currency.

        Args:
            code: Currency code (case-insensitive)

        Returns:
            CurrencyRate or None if not found
        """
        code_upper = code.upper()
        return next((r for r in self.rates if r.code == code_upper), None)

    def filter_currencies(self, codes: list[str]) -> "ExchangeRates":
        """
        Create a new ExchangeRates with only specified currencies.

        Args:
            codes: List of currency codes to include

        Returns:
            New ExchangeRates with filtered rates
        """
        codes_upper = {c.upper() for c in codes}
        filtered_rates = [r for r in self.rates if r.code in codes_upper]
        return ExchangeRates(
            date=self.date,
            bulletin_no=self.bulletin_no,
            rates=filtered_rates,
            warning=self.warning,
        )


class ConversionResult(BaseModel):
    """Result of currency conversion."""

    from_currency: str = Field(..., description="Source currency code")
    from_amount: Decimal = Field(..., description="Source amount")
    to_currency: str = Field(..., description="Target currency code")
    to_amount: Decimal = Field(..., description="Converted amount")
    rate: Decimal = Field(..., description="Exchange rate used")
    rate_type: str = Field(..., description="Type of rate used")
    date: DateType = Field(..., description="Date of exchange rate")
    warning: str | None = Field(None, description="Warning message if applicable")

    @field_serializer("from_amount", "to_amount", "rate")
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize Decimal to string for JSON output."""
        return str(value)


class RateStatistics(BaseModel):
    """Statistics for a currency rate over a period."""

    min_rate: Decimal = Field(..., description="Minimum rate in period")
    max_rate: Decimal = Field(..., description="Maximum rate in period")
    avg_rate: Decimal = Field(..., description="Average rate in period")
    change_percent: Decimal = Field(..., description="Percentage change from start to end")
    volatility: Decimal = Field(..., description="Standard deviation of rates")

    @field_serializer("min_rate", "max_rate", "avg_rate", "change_percent", "volatility")
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize Decimal to string for JSON output."""
        return str(value)


class RateDataPoint(BaseModel):
    """Single data point in rate history."""

    date: DateType
    buying: Decimal | None = None
    selling: Decimal | None = None

    @field_serializer("buying", "selling")
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        """Serialize Decimal to string for JSON output."""
        if value is None:
            return None
        return str(value)


class RateHistory(BaseModel):
    """Historical rate data for a currency."""

    currency: str = Field(..., description="Currency code")
    start_date: DateType = Field(..., description="Start date of the period")
    end_date: DateType = Field(..., description="End date of the period")
    data_points: list[RateDataPoint] = Field(
        default_factory=list, description="Daily rate data"
    )
    statistics: RateStatistics | None = Field(None, description="Period statistics")
    warning: str | None = Field(None, description="Warning message if applicable")
