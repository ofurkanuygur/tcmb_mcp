"""Tests for TCMB client."""

from datetime import date
from pathlib import Path

import pytest
import respx
from httpx import Response

from tcmb_mcp.core.config import Settings
from tcmb_mcp.core.constants import TCMB_TODAY_URL, get_historical_url
from tcmb_mcp.core.exceptions import TCMBAPIError, TCMBConnectionError
from tcmb_mcp.services.tcmb_client import TCMBClient


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        timeout=5,
        max_retries=2,
        retry_delay=0.1,
        request_delay=0.01,
    )


@pytest.fixture
def sample_xml() -> str:
    """Load sample TCMB XML for testing."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    xml_path = fixtures_dir / "sample_rates.xml"
    return xml_path.read_text(encoding="utf-8")


class TestTCMBClient:
    """Tests for TCMBClient."""

    @respx.mock
    async def test_get_today_rates(self, settings: Settings, sample_xml: str):
        """Test fetching today's rates."""
        respx.get(TCMB_TODAY_URL).mock(return_value=Response(200, text=sample_xml))

        async with TCMBClient(settings) as client:
            rates = await client.get_today_rates()

        assert rates.date == date(2024, 1, 15)
        assert len(rates.rates) == 5
        assert rates.get_rate("USD") is not None

    @respx.mock
    async def test_get_historical_rates(self, settings: Settings, sample_xml: str):
        """Test fetching historical rates."""
        target_date = date(2024, 1, 15)
        url = get_historical_url(target_date)

        respx.get(url).mock(return_value=Response(200, text=sample_xml))

        async with TCMBClient(settings) as client:
            rates = await client.get_rates_for_date(target_date)

        assert rates.date == target_date
        assert rates.get_rate("EUR") is not None

    @respx.mock
    async def test_holiday_fallback(self, settings: Settings, sample_xml: str):
        """Test automatic fallback to previous business day on holidays."""
        # Saturday (weekend)
        weekend_date = date(2024, 1, 13)  # This is a Saturday
        friday_date = date(2024, 1, 12)

        # Weekend URL should 404, Friday should work
        respx.get(get_historical_url(weekend_date)).mock(
            return_value=Response(404)
        )
        respx.get(get_historical_url(friday_date)).mock(
            return_value=Response(200, text=sample_xml)
        )

        async with TCMBClient(settings) as client:
            rates = await client.get_rates_for_date(weekend_date, handle_holidays=True)

        # Should have warning about holiday
        assert rates.warning is not None
        assert "tatil" in rates.warning.lower() or "2024-01-13" in rates.warning

    @respx.mock
    async def test_retry_on_timeout(self, settings: Settings, sample_xml: str):
        """Test retry mechanism on timeout."""
        # First request times out, second succeeds
        route = respx.get(TCMB_TODAY_URL)
        route.side_effect = [
            Response(500),  # First attempt fails
            Response(200, text=sample_xml),  # Second attempt succeeds
        ]

        async with TCMBClient(settings) as client:
            rates = await client.get_today_rates()

        assert rates is not None
        assert route.call_count == 2

    @respx.mock
    async def test_404_error(self, settings: Settings):
        """Test 404 error handling."""
        target_date = date(2024, 1, 15)
        url = get_historical_url(target_date)

        respx.get(url).mock(return_value=Response(404))

        async with TCMBClient(settings) as client:
            with pytest.raises(TCMBAPIError) as exc_info:
                await client.get_rates_for_date(target_date, handle_holidays=False)

        assert exc_info.value.status_code == 404

    @respx.mock
    async def test_connection_error_after_retries(self, settings: Settings):
        """Test connection error after all retries fail."""
        respx.get(TCMB_TODAY_URL).mock(return_value=Response(500))

        async with TCMBClient(settings) as client:
            with pytest.raises(TCMBConnectionError):
                await client.get_today_rates()

    async def test_client_not_initialized(self, settings: Settings):
        """Test error when client used without context manager."""
        client = TCMBClient(settings)

        with pytest.raises(TCMBConnectionError, match="not initialized"):
            await client.get_today_rates()


class TestHistoricalUrl:
    """Tests for historical URL generation."""

    def test_url_format(self):
        """Test correct URL format generation."""
        target_date = date(2024, 1, 15)
        url = get_historical_url(target_date)

        assert url == "https://www.tcmb.gov.tr/kurlar/202401/15012024.xml"

    def test_url_format_single_digit_day(self):
        """Test URL format with single digit day."""
        target_date = date(2024, 1, 5)
        url = get_historical_url(target_date)

        assert url == "https://www.tcmb.gov.tr/kurlar/202401/05012024.xml"

    def test_url_format_december(self):
        """Test URL format for December."""
        target_date = date(2024, 12, 25)
        url = get_historical_url(target_date)

        assert url == "https://www.tcmb.gov.tr/kurlar/202412/25122024.xml"
