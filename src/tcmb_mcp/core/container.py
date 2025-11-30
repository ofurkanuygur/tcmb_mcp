"""Dependency injection container for service management."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tcmb_mcp.services.cache_service import CacheService
    from tcmb_mcp.services.tcmb_client import TCMBClient

# Singleton instances
_tcmb_client: "TCMBClient | None" = None
_cache_service: "CacheService | None" = None
_initialized: bool = False


async def get_tcmb_client() -> "TCMBClient":
    """
    Get TCMBClient singleton instance.

    The client is lazily initialized on first call and reused thereafter.

    Returns:
        Initialized TCMBClient instance
    """
    global _tcmb_client

    if _tcmb_client is None:
        from tcmb_mcp.core.config import get_settings
        from tcmb_mcp.services.tcmb_client import TCMBClient

        settings = get_settings()
        _tcmb_client = TCMBClient(settings)
        await _tcmb_client.__aenter__()

    return _tcmb_client


async def get_cache_service() -> "CacheService":
    """
    Get CacheService singleton instance.

    The service is lazily initialized on first call and reused thereafter.

    Returns:
        Initialized CacheService instance
    """
    global _cache_service

    if _cache_service is None:
        from tcmb_mcp.core.config import get_settings
        from tcmb_mcp.services.cache_service import CacheService

        settings = get_settings()
        _cache_service = CacheService(str(settings.get_cache_path()))

    return _cache_service


async def initialize() -> None:
    """
    Initialize all services.

    Call this at application startup to ensure all services are ready.
    """
    global _initialized

    if _initialized:
        return

    # Initialize services
    await get_cache_service()
    await get_tcmb_client()

    _initialized = True


async def cleanup() -> None:
    """
    Cleanup all services.

    Call this at application shutdown to properly close connections.
    """
    global _tcmb_client, _cache_service, _initialized

    if _tcmb_client is not None:
        await _tcmb_client.__aexit__(None, None, None)
        _tcmb_client = None

    _cache_service = None
    _initialized = False


async def reset() -> None:
    """
    Reset all services (useful for testing).

    This will cleanup and reinitialize all services.
    """
    await cleanup()
