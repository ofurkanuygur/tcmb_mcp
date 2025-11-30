"""Tests for date utilities."""

from datetime import date, timedelta

import pytest

from tcmb_mcp.core.exceptions import TCMBDateRangeError
from tcmb_mcp.utils.date_utils import (
    format_date,
    get_date_range,
    parse_date,
    validate_date_range,
)


class TestParseDate:
    """Tests for parse_date function."""

    def test_iso_format(self):
        """Test ISO format parsing."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_turkish_format(self):
        """Test Turkish format (DD.MM.YYYY) parsing."""
        result = parse_date("15.01.2024")
        assert result == date(2024, 1, 15)

    def test_slash_format(self):
        """Test slash format (DD/MM/YYYY) parsing."""
        result = parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_today_keyword(self):
        """Test 'today' keyword."""
        result = parse_date("today")
        assert result == date.today()

    def test_bugun_keyword(self):
        """Test 'bugün' keyword."""
        result = parse_date("bugün")
        assert result == date.today()

    def test_yesterday_keyword(self):
        """Test 'yesterday' keyword."""
        result = parse_date("yesterday")
        assert result == date.today() - timedelta(days=1)

    def test_dun_keyword(self):
        """Test 'dün' keyword."""
        result = parse_date("dün")
        assert result == date.today() - timedelta(days=1)

    def test_invalid_format(self):
        """Test invalid date format raises error."""
        with pytest.raises(TCMBDateRangeError):
            parse_date("invalid-date")


class TestFormatDate:
    """Tests for format_date function."""

    def test_iso_format(self):
        """Test ISO format output."""
        result = format_date(date(2024, 1, 15), "iso")
        assert result == "2024-01-15"

    def test_turkish_format(self):
        """Test Turkish format output."""
        result = format_date(date(2024, 1, 15), "turkish")
        assert result == "15.01.2024"

    def test_tcmb_folder_format(self):
        """Test TCMB folder format (YYYYMM)."""
        result = format_date(date(2024, 1, 15), "tcmb_folder")
        assert result == "202401"

    def test_tcmb_file_format(self):
        """Test TCMB file format (DDMMYYYY)."""
        result = format_date(date(2024, 1, 15), "tcmb_file")
        assert result == "15012024"


class TestValidateDateRange:
    """Tests for validate_date_range function."""

    def test_valid_range(self):
        """Test valid date range passes."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        validate_date_range(start, end)  # Should not raise

    def test_start_before_min_date(self):
        """Test start date before minimum raises error."""
        start = date(1990, 1, 1)
        end = date(1990, 1, 31)
        with pytest.raises(TCMBDateRangeError, match="1996"):
            validate_date_range(start, end)

    def test_end_in_future(self):
        """Test end date in future raises error."""
        start = date.today()
        end = date.today() + timedelta(days=30)
        with pytest.raises(TCMBDateRangeError, match="bugünden sonra"):
            validate_date_range(start, end)

    def test_start_after_end(self):
        """Test start after end raises error."""
        start = date(2024, 2, 1)
        end = date(2024, 1, 1)
        with pytest.raises(TCMBDateRangeError, match="sonra olamaz"):
            validate_date_range(start, end)

    def test_range_too_large(self):
        """Test range larger than max_days raises error."""
        start = date(2023, 1, 1)
        end = date(2024, 1, 2)  # 366 days, exceeds max_days=365
        with pytest.raises(TCMBDateRangeError, match="365 gün"):
            validate_date_range(start, end, max_days=365)


class TestGetDateRange:
    """Tests for get_date_range function."""

    def test_single_day(self):
        """Test single day range."""
        start = end = date(2024, 1, 15)
        result = get_date_range(start, end)
        assert result == [date(2024, 1, 15)]

    def test_week_range(self):
        """Test week range."""
        start = date(2024, 1, 15)
        end = date(2024, 1, 21)
        result = get_date_range(start, end)
        assert len(result) == 7
        assert result[0] == start
        assert result[-1] == end
