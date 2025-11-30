"""Tests for XML parser."""

from datetime import date
from decimal import Decimal

import pytest

from tcmb_mcp.core.exceptions import TCMBAPIError
from tcmb_mcp.models.enums import RateType
from tcmb_mcp.utils.xml_parser import parse_tcmb_xml


class TestParseTcmbXml:
    """Tests for parse_tcmb_xml function."""

    def test_parse_valid_xml(self, sample_xml: str):
        """Test parsing valid TCMB XML."""
        result = parse_tcmb_xml(sample_xml)

        assert result.date == date(2024, 1, 15)
        assert result.bulletin_no == "2024/10"
        assert len(result.rates) == 5

    def test_parse_usd_rate(self, sample_xml: str):
        """Test USD rate parsing."""
        result = parse_tcmb_xml(sample_xml)
        usd = result.get_rate("USD")

        assert usd is not None
        assert usd.code == "USD"
        assert usd.name == "US DOLLAR"
        assert usd.name_tr == "ABD DOLARI"
        assert usd.unit == 1
        assert usd.forex_buying == Decimal("30.2145")
        assert usd.forex_selling == Decimal("30.2678")
        assert usd.cross_rate_usd == Decimal("1.0000")

    def test_parse_jpy_rate_with_unit(self, sample_xml: str):
        """Test JPY rate parsing with unit=100."""
        result = parse_tcmb_xml(sample_xml)
        jpy = result.get_rate("JPY")

        assert jpy is not None
        assert jpy.unit == 100
        assert jpy.forex_buying == Decimal("20.3456")

        # Test unit rate calculation
        unit_rate = jpy.get_unit_rate(RateType.FOREX_BUYING)
        assert unit_rate == Decimal("20.3456") / 100

    def test_get_rate_case_insensitive(self, sample_xml: str):
        """Test get_rate is case insensitive."""
        result = parse_tcmb_xml(sample_xml)

        assert result.get_rate("usd") is not None
        assert result.get_rate("USD") is not None
        assert result.get_rate("Usd") is not None

    def test_get_rate_not_found(self, sample_xml: str):
        """Test get_rate returns None for unknown currency."""
        result = parse_tcmb_xml(sample_xml)
        assert result.get_rate("XYZ") is None

    def test_filter_currencies(self, sample_xml: str):
        """Test filtering currencies."""
        result = parse_tcmb_xml(sample_xml)
        filtered = result.filter_currencies(["USD", "EUR"])

        assert len(filtered.rates) == 2
        assert filtered.get_rate("USD") is not None
        assert filtered.get_rate("EUR") is not None
        assert filtered.get_rate("GBP") is None

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML raises error."""
        with pytest.raises(TCMBAPIError, match="parse hatası"):
            parse_tcmb_xml("not valid xml")

    def test_parse_missing_date(self):
        """Test parsing XML without date raises error."""
        xml = '<?xml version="1.0"?><Tarih_Date></Tarih_Date>'
        with pytest.raises(TCMBAPIError, match="tarih bilgisi"):
            parse_tcmb_xml(xml)

    def test_parse_empty_rates(self):
        """Test parsing XML with no currencies."""
        xml = '<?xml version="1.0"?><Tarih_Date Tarih="15.01.2024"></Tarih_Date>'
        result = parse_tcmb_xml(xml)

        assert result.date == date(2024, 1, 15)
        assert len(result.rates) == 0

    def test_cross_rate_parsing(self, sample_xml: str):
        """Test cross rate parsing."""
        result = parse_tcmb_xml(sample_xml)
        eur = result.get_rate("EUR")

        assert eur is not None
        assert eur.cross_rate_usd == Decimal("1.0881")
