"""SQLite-based cache service for exchange rates."""

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import AsyncGenerator

import aiosqlite

from tcmb_mcp.core.exceptions import TCMBCacheError
from tcmb_mcp.core.logging import get_logger
from tcmb_mcp.models.schemas import ExchangeRates

logger = get_logger(__name__)


class CacheService:
    """SQLite-based cache for exchange rates."""

    def __init__(self, db_path: str = "tcmb_cache.db") -> None:
        """
        Initialize cache service.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Create database tables if they don't exist."""
        if self._initialized:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS exchange_rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL UNIQUE,
                        data TEXT NOT NULL,
                        fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        expires_at TEXT
                    )
                """)
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_date ON exchange_rates(date)"
                )
                await db.commit()

            self._initialized = True
            logger.debug("cache_initialized", db_path=self.db_path)

        except aiosqlite.Error as e:
            logger.error("cache_init_failed", error=str(e))
            raise TCMBCacheError(f"Cache başlatılamadı: {e}") from e

    @asynccontextmanager
    async def _get_db(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get database connection with row factory."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    async def get_rates(
        self,
        target_date: date,
        ttl_seconds: int | None = None,
    ) -> ExchangeRates | None:
        """
        Get cached rates for a date.

        Args:
            target_date: Date to get rates for
            ttl_seconds: Optional TTL to check (if None, returns any cached data)

        Returns:
            Cached ExchangeRates or None if not found/expired
        """
        try:
            async with self._get_db() as db:
                cursor = await db.execute(
                    "SELECT data, fetched_at, expires_at FROM exchange_rates WHERE date = ?",
                    (target_date.isoformat(),),
                )
                row = await cursor.fetchone()

                if row is None:
                    logger.debug("cache_miss", date=target_date.isoformat())
                    return None

                # Check TTL if specified
                if ttl_seconds is not None:
                    fetched_at = datetime.fromisoformat(row["fetched_at"])
                    age = (datetime.now() - fetched_at).total_seconds()
                    if age > ttl_seconds:
                        logger.debug(
                            "cache_expired",
                            date=target_date.isoformat(),
                            age_seconds=age,
                        )
                        return None

                # Parse and return cached data
                data = json.loads(row["data"])
                rates = ExchangeRates.model_validate(data)

                logger.debug("cache_hit", date=target_date.isoformat())
                return rates

        except (aiosqlite.Error, json.JSONDecodeError) as e:
            logger.warning("cache_read_error", error=str(e))
            return None

    async def set_rates(
        self,
        rates: ExchangeRates,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Cache exchange rates.

        Args:
            rates: Exchange rates to cache
            ttl_seconds: Optional TTL in seconds
        """
        try:
            data = rates.model_dump_json()
            expires_at = None
            if ttl_seconds:
                expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()

            async with self._get_db() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO exchange_rates (date, data, fetched_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        rates.date.isoformat(),
                        data,
                        datetime.now().isoformat(),
                        expires_at,
                    ),
                )
                await db.commit()

            logger.debug("cache_set", date=rates.date.isoformat())

        except aiosqlite.Error as e:
            logger.warning("cache_write_error", error=str(e))
            # Don't raise - cache errors shouldn't break the app

    async def is_cache_valid(
        self,
        target_date: date,
        ttl_seconds: int,
    ) -> bool:
        """
        Check if cached data is valid (exists and not expired).

        Args:
            target_date: Date to check
            ttl_seconds: TTL to check against

        Returns:
            True if cache is valid
        """
        rates = await self.get_rates(target_date, ttl_seconds)
        return rates is not None

    async def clear_old_cache(self, days: int = 365) -> int:
        """
        Clear cache entries older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted entries
        """
        try:
            cutoff_date = (date.today() - timedelta(days=days)).isoformat()

            async with self._get_db() as db:
                cursor = await db.execute(
                    "DELETE FROM exchange_rates WHERE date < ?",
                    (cutoff_date,),
                )
                await db.commit()

                deleted = cursor.rowcount
                logger.info("cache_cleared", deleted_count=deleted)
                return deleted

        except aiosqlite.Error as e:
            logger.error("cache_clear_error", error=str(e))
            return 0

    async def get_cached_dates(self) -> list[date]:
        """Get list of all cached dates."""
        try:
            async with self._get_db() as db:
                cursor = await db.execute(
                    "SELECT date FROM exchange_rates ORDER BY date DESC"
                )
                rows = await cursor.fetchall()
                return [date.fromisoformat(row["date"]) for row in rows]

        except aiosqlite.Error:
            return []
