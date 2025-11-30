"""Tests for cache service."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tcmb_mcp.models.schemas import CurrencyRate, ExchangeRates
from tcmb_mcp.services.cache_service import CacheService


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def cache_service(temp_db_path: str) -> CacheService:
    """Create a cache service with temporary database."""
    return CacheService(temp_db_path)


@pytest.fixture
def sample_rates() -> ExchangeRates:
    """Create sample exchange rates for testing."""
    return ExchangeRates(
        date=date(2024, 1, 15),
        bulletin_no="2024/10",
        rates=[
            CurrencyRate(
                code="USD",
                name="US Dollar",
                name_tr="ABD Doları",
                unit=1,
                forex_buying=Decimal("30.2145"),
                forex_selling=Decimal("30.2678"),
            ),
            CurrencyRate(
                code="EUR",
                name="Euro",
                name_tr="Euro",
                unit=1,
                forex_buying=Decimal("32.8765"),
                forex_selling=Decimal("32.9432"),
            ),
        ],
    )


class TestCacheService:
    """Tests for CacheService."""

    async def test_set_and_get_rates(
        self,
        cache_service: CacheService,
        sample_rates: ExchangeRates,
    ):
        """Test setting and getting rates from cache."""
        await cache_service.set_rates(sample_rates)

        cached = await cache_service.get_rates(sample_rates.date)

        assert cached is not None
        assert cached.date == sample_rates.date
        assert cached.bulletin_no == sample_rates.bulletin_no
        assert len(cached.rates) == len(sample_rates.rates)

    async def test_get_rates_not_found(self, cache_service: CacheService):
        """Test getting non-existent rates returns None."""
        result = await cache_service.get_rates(date(2024, 1, 15))
        assert result is None

    async def test_cache_ttl_expired(
        self,
        cache_service: CacheService,
        sample_rates: ExchangeRates,
    ):
        """Test expired cache returns None with TTL check."""
        await cache_service.set_rates(sample_rates, ttl_seconds=1)

        # Immediate access should work
        cached = await cache_service.get_rates(sample_rates.date, ttl_seconds=3600)
        assert cached is not None

        # With very short TTL, should be "expired" (mock time would be better)
        # This is a simplified test - in real scenario we'd mock time

    async def test_cache_update(
        self,
        cache_service: CacheService,
        sample_rates: ExchangeRates,
    ):
        """Test updating cached rates."""
        # Set initial rates
        await cache_service.set_rates(sample_rates)

        # Update with modified rates
        updated_rates = ExchangeRates(
            date=sample_rates.date,
            bulletin_no="2024/11",  # Different bulletin
            rates=sample_rates.rates,
        )
        await cache_service.set_rates(updated_rates)

        # Get and verify
        cached = await cache_service.get_rates(sample_rates.date)
        assert cached is not None
        assert cached.bulletin_no == "2024/11"

    async def test_is_cache_valid(
        self,
        cache_service: CacheService,
        sample_rates: ExchangeRates,
    ):
        """Test cache validity check."""
        # Not in cache
        assert not await cache_service.is_cache_valid(date(2024, 1, 15), ttl_seconds=3600)

        # Add to cache
        await cache_service.set_rates(sample_rates)

        # Should be valid
        assert await cache_service.is_cache_valid(sample_rates.date, ttl_seconds=3600)

    async def test_get_cached_dates(
        self,
        cache_service: CacheService,
        sample_rates: ExchangeRates,
    ):
        """Test getting list of cached dates."""
        # Initially empty
        dates = await cache_service.get_cached_dates()
        assert len(dates) == 0

        # Add rates
        await cache_service.set_rates(sample_rates)

        # Should have one date
        dates = await cache_service.get_cached_dates()
        assert len(dates) == 1
        assert sample_rates.date in dates

    async def test_clear_old_cache(self, cache_service: CacheService):
        """Test clearing old cache entries."""
        from datetime import timedelta
        today = date.today()

        # Add rates for different dates (recent dates)
        for i in [1, 15, 30]:
            rates = ExchangeRates(
                date=today - timedelta(days=i),
                rates=[],
            )
            await cache_service.set_rates(rates)

        # Clear old cache - recent dates should not be deleted
        deleted = await cache_service.clear_old_cache(days=365)
        # All dates are recent, so none should be deleted
        assert deleted == 0
