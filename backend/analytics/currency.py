"""
backend/analytics/currency.py
Indian Rupee (INR / ₹) formatting utility with configurable exchange rate conversion.
Supports converting from source currency (e.g., USD) to INR before display.
"""

from typing import Optional
import pandas as pd

# Default exchange rate: 1 USD = 83.5 INR (configurable)
_EXCHANGE_RATE = 83.5
_SOURCE_CURRENCY = "USD"


def set_exchange_rate(rate: float, source: str = "USD"):
    """Configure the exchange rate from source currency to INR."""
    global _EXCHANGE_RATE, _SOURCE_CURRENCY
    _EXCHANGE_RATE = rate
    _SOURCE_CURRENCY = source


def get_exchange_rate() -> float:
    """Return current exchange rate."""
    return _EXCHANGE_RATE


def get_source_currency() -> str:
    """Return current source currency code."""
    return _SOURCE_CURRENCY


def convert_to_inr(val: Optional[float]) -> Optional[float]:
    """Convert a value from source currency to INR using active exchange rate."""
    if val is None or pd.isna(val):
        return None
    try:
        return float(val) * _EXCHANGE_RATE
    except (ValueError, TypeError):
        return None


def convert_series_to_inr(series: pd.Series) -> pd.Series:
    """Convert a numeric Series from source currency to INR."""
    return pd.to_numeric(series, errors="coerce") * _EXCHANGE_RATE


def format_inr(val: Optional[float], compact: bool = False, decimals: int = 2, convert: bool = True) -> str:
    """
    Formats a numeric value into Indian Rupees (₹).
    If convert=True, applies exchange rate conversion first.
    If compact is True:
      >= 1 Crore (10,000,000) -> ₹X.XX Cr
      >= 1 Lakh (100,000) -> ₹X.XX L
      >= 1 Thousand (1,000) -> ₹X.X K
    Otherwise standard comma format: ₹1,565,804.32
    """
    if val is None or pd.isna(val):
        return "₹0.00"

    try:
        val = float(val)
    except (ValueError, TypeError):
        return "₹0.00"

    if convert:
        val = val * _EXCHANGE_RATE

    sign = "-" if val < 0 else ""
    abs_val = abs(val)

    if compact:
        if abs_val >= 10_000_000:
            return f"{sign}₹{abs_val / 10_000_000:.2f} Cr"
        elif abs_val >= 100_000:
            return f"{sign}₹{abs_val / 100_000:.2f} L"
        elif abs_val >= 1_000:
            return f"{sign}₹{abs_val / 1_000:.1f} K"
        else:
            return f"{sign}₹{abs_val:,.{decimals}f}"

    return f"{sign}₹{abs_val:,.{decimals}f}"
