"""Pytest fixtures and configuration."""

from datetime import date
from pathlib import Path

import pytest

from tcmb_mcp.core.config import Settings, reset_settings


@pytest.fixture
def sample_xml() -> str:
    """Load sample TCMB XML for testing."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    xml_path = fixtures_dir / "sample_rates.xml"
    return xml_path.read_text(encoding="utf-8")


@pytest.fixture
def sample_date() -> date:
    """Sample date for testing."""
    return date(2024, 1, 15)


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    reset_settings()
    return Settings(
        cache_enabled=False,
        cache_db_path=":memory:",
        debug=True,
    )


@pytest.fixture(autouse=True)
def cleanup_settings():
    """Clean up settings after each test."""
    yield
    reset_settings()
