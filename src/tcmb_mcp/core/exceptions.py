"""Custom exceptions for TCMB MCP Pro."""


class TCMBError(Exception):
    """Base exception for TCMB MCP Pro."""

    def __init__(self, message: str, code: str = "TCMB_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
        }


class TCMBAPIError(TCMBError):
    """TCMB API call failed."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message, "TCMB_API_ERROR")
        self.status_code = status_code

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.status_code:
            result["status_code"] = self.status_code
        return result


class TCMBHolidayError(TCMBError):
    """Holiday - no data available."""

    def __init__(self, date: str, suggestion: str | None = None) -> None:
        message = f"'{date}' tarihi için kur bilgisi yok (tatil/hafta sonu)"
        super().__init__(message, "TCMB_HOLIDAY")
        self.date = date
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["date"] = self.date
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


class TCMBDateRangeError(TCMBError):
    """Invalid date range."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "TCMB_DATE_RANGE")


class TCMBCurrencyNotFoundError(TCMBError):
    """Currency not found."""

    def __init__(self, currency: str) -> None:
        message = f"'{currency}' para birimi bulunamadı"
        super().__init__(message, "TCMB_CURRENCY_NOT_FOUND")
        self.currency = currency

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["currency"] = self.currency
        return result


class TCMBCacheError(TCMBError):
    """Cache error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "TCMB_CACHE_ERROR")


class TCMBConnectionError(TCMBError):
    """Connection error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "TCMB_CONNECTION_ERROR")
