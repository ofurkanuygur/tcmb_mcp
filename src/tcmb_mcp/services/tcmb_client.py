"""TCMB API client with retry and rate limiting."""

import asyncio
from datetime import date
from types import TracebackType

import httpx
from typing_extensions import Self

from tcmb_mcp.core.config import Settings
from tcmb_mcp.core.constants import TCMB_TODAY_URL, get_historical_url
from tcmb_mcp.core.exceptions import TCMBAPIError, TCMBConnectionError
from tcmb_mcp.core.holidays import get_previous_business_day, is_holiday
from tcmb_mcp.core.logging import get_logger
from tcmb_mcp.models.schemas import ExchangeRates
from tcmb_mcp.utils.xml_parser import parse_tcmb_xml

logger = get_logger(__name__)


class TCMBClient:
    """
    Async HTTP client for TCMB exchange rate API.

    Features:
    - Automatic retry with exponential backoff
    - Rate limiting between requests
    - Connection pooling
    - Holiday handling
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize TCMB client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.timeout),
            follow_redirects=True,
            headers={
                "User-Agent": "tcmb-mcp-pro/1.0",
                "Accept": "application/xml",
            },
        )
        logger.debug("client_initialized")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("client_closed")

    async def _throttle(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time > 0:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            delay = self.settings.request_delay - elapsed
            if delay > 0:
                await asyncio.sleep(delay)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _fetch_with_retry(self, url: str) -> str:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch

        Returns:
            Response text

        Raises:
            TCMBConnectionError: If all retries fail
            TCMBAPIError: If API returns error status
        """
        if self._client is None:
            raise TCMBConnectionError("Client not initialized. Use 'async with' context.")

        last_error: Exception | None = None
        delays = [
            self.settings.retry_delay * (2**i)
            for i in range(self.settings.max_retries)
        ]

        for attempt, delay in enumerate(delays):
            try:
                await self._throttle()

                logger.debug("fetching_url", url=url, attempt=attempt + 1)
                response = await self._client.get(url)

                if response.status_code == 404:
                    raise TCMBAPIError(f"Veri bulunamadı: {url}", status_code=404)

                response.raise_for_status()
                return response.text

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "request_timeout",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=len(delays),
                )

            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    "connection_error",
                    url=url,
                    attempt=attempt + 1,
                    error=str(e),
                )

            except httpx.HTTPStatusError as e:
                # Don't retry for client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise TCMBAPIError(
                        f"API hatası: {e.response.status_code}",
                        status_code=e.response.status_code,
                    ) from e
                last_error = e
                logger.warning(
                    "http_error",
                    url=url,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                )

            # Wait before retry (except for last attempt)
            if attempt < len(delays) - 1:
                await asyncio.sleep(delay)

        # All retries failed
        raise TCMBConnectionError(
            f"TCMB'ye bağlanılamadı ({self.settings.max_retries} deneme başarısız)"
        ) from last_error

    async def get_today_rates(self) -> ExchangeRates:
        """
        Fetch today's exchange rates.

        Returns:
            Today's exchange rates

        Raises:
            TCMBAPIError: If fetch fails
        """
        logger.info("fetching_today_rates")
        xml_content = await self._fetch_with_retry(TCMB_TODAY_URL)
        rates = parse_tcmb_xml(xml_content)
        logger.info("rates_fetched", date=rates.date.isoformat(), count=len(rates.rates))
        return rates

    async def get_rates_for_date(
        self,
        target_date: date,
        handle_holidays: bool = True,
    ) -> ExchangeRates:
        """
        Fetch exchange rates for a specific date.

        Args:
            target_date: Date to get rates for
            handle_holidays: If True, automatically use previous business day for holidays

        Returns:
            Exchange rates for the date (or previous business day if holiday)

        Raises:
            TCMBAPIError: If fetch fails
        """
        original_date = target_date
        warning: str | None = None

        # Handle holidays if enabled
        if handle_holidays and is_holiday(target_date):
            target_date = get_previous_business_day(target_date)
            warning = (
                f"'{original_date.isoformat()}' tatil günü. "
                f"'{target_date.isoformat()}' tarihli kurlar gösteriliyor."
            )
            logger.info(
                "holiday_fallback",
                original_date=original_date.isoformat(),
                actual_date=target_date.isoformat(),
            )

        url = get_historical_url(target_date)
        logger.info("fetching_historical_rates", date=target_date.isoformat())

        try:
            xml_content = await self._fetch_with_retry(url)
            rates = parse_tcmb_xml(xml_content)

            if warning:
                rates.warning = warning

            logger.info(
                "rates_fetched",
                date=rates.date.isoformat(),
                count=len(rates.rates),
            )
            return rates

        except TCMBAPIError as e:
            if e.status_code == 404 and handle_holidays:
                # Try previous business day if 404
                prev_day = get_previous_business_day(target_date)
                return await self.get_rates_for_date(prev_day, handle_holidays=False)
            raise
