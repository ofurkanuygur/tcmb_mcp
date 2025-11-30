"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_cache_path() -> str:
    """Get default cache path in user's home directory."""
    cache_dir = Path.home() / ".cache" / "tcmb-mcp-pro"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir / "tcmb_cache.db")


class Settings(BaseSettings):
    """Application settings with environment and TOML file support."""

    model_config = SettingsConfigDict(
        env_prefix="TCMB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cache settings
    cache_enabled: bool = Field(default=True, description="Enable SQLite caching")
    cache_db_path: str = Field(
        default_factory=_get_default_cache_path,
        description="SQLite database file path",
    )
    cache_ttl_today: int = Field(
        default=3600, description="Cache TTL for today's rates (seconds)"
    )
    cache_ttl_historical: int = Field(
        default=31536000, description="Cache TTL for historical rates (seconds, default 1 year)"
    )

    # TCMB API settings
    timeout: int = Field(default=10, description="API request timeout (seconds)")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Initial retry delay (seconds)")
    request_delay: float = Field(
        default=0.1, description="Delay between consecutive requests (rate limiting)"
    )

    # General settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    def get_cache_path(self) -> Path:
        """Get absolute path for cache database."""
        path = Path(self.cache_db_path)
        if not path.is_absolute():
            # Use home directory cache folder
            cache_dir = Path.home() / ".cache" / "tcmb-mcp-pro"
            cache_dir.mkdir(parents=True, exist_ok=True)
            path = cache_dir / path
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)."""
    global _settings
    _settings = None
