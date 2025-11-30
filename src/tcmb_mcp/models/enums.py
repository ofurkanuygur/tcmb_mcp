"""Enumeration types for TCMB MCP Pro."""

from enum import Enum


class RateType(str, Enum):
    """
    TCMB exchange rate types.

    TCMB provides four different rate types:
    - Forex rates: For electronic transfers
    - Banknote rates: For physical currency exchange
    """

    FOREX_BUYING = "forex_buying"
    FOREX_SELLING = "forex_selling"
    BANKNOTE_BUYING = "banknote_buying"
    BANKNOTE_SELLING = "banknote_selling"

    @classmethod
    def from_simple(cls, simple: str, is_forex: bool = True) -> "RateType":
        """
        Convert simple rate type to full enum.

        Args:
            simple: 'buying' or 'selling'
            is_forex: True for forex rates, False for banknote rates

        Returns:
            Corresponding RateType enum value

        Raises:
            ValueError: If simple is not 'buying' or 'selling'
        """
        if simple not in ("buying", "selling"):
            raise ValueError(f"Invalid rate type: {simple}. Must be 'buying' or 'selling'")

        prefix = "forex" if is_forex else "banknote"
        return cls(f"{prefix}_{simple}")

    @property
    def is_buying(self) -> bool:
        """Check if this is a buying rate."""
        return "buying" in self.value

    @property
    def is_selling(self) -> bool:
        """Check if this is a selling rate."""
        return "selling" in self.value

    @property
    def is_forex(self) -> bool:
        """Check if this is a forex rate."""
        return "forex" in self.value

    @property
    def is_banknote(self) -> bool:
        """Check if this is a banknote rate."""
        return "banknote" in self.value

    @property
    def turkish_name(self) -> str:
        """Get Turkish name for the rate type."""
        names = {
            RateType.FOREX_BUYING: "Döviz Alış",
            RateType.FOREX_SELLING: "Döviz Satış",
            RateType.BANKNOTE_BUYING: "Efektif Alış",
            RateType.BANKNOTE_SELLING: "Efektif Satış",
        }
        return names[self]
