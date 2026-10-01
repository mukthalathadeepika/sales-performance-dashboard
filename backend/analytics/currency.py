"""
backend/analytics/currency.py
Indian Rupee (INR / ₹) formatting utility.
Adheres strictly to the requirement: all monetary values displayed in Indian Rupees (₹).
"""

from typing import Optional
import pandas as pd


def format_inr(val: Optional[float], compact: bool = False, decimals: int = 2) -> str:
    """
    Formats a numeric value into Indian Rupees (₹).
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
