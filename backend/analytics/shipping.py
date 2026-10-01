"""
backend/analytics/shipping.py
Shipping mode performance and transit duration analysis.
"""

from typing import Dict, Any, Optional
import pandas as pd


def get_shipping_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes shipping mode distribution, average transit duration,
    and transit time by ship mode.
    """
    if df is None or len(df) == 0:
        return {"mode_breakdown": pd.DataFrame(), "avg_days": None}

    has_duration = "_std_shipping_duration_days" in df.columns
    has_mode = "_std_ship_mode" in df.columns

    avg_days = float(df["_std_shipping_duration_days"].dropna().mean()) if has_duration else None

    if not has_mode:
        return {"mode_breakdown": pd.DataFrame(), "avg_days": avg_days}

    agg_dict = {}
    if "_std_order_id" in df.columns:
        agg_dict["_std_order_id"] = "nunique"
    if "_std_sales" in df.columns:
        agg_dict["_std_sales"] = "sum"
    if has_duration:
        agg_dict["_std_shipping_duration_days"] = "mean"

    grouped = df.groupby("_std_ship_mode", as_index=False).agg(agg_dict)
    rename_map = {
        "_std_ship_mode": "Ship Mode",
        "_std_order_id": "Orders",
        "_std_sales": "Sales",
        "_std_shipping_duration_days": "Avg Shipping Days",
    }
    grouped = grouped.rename(columns=rename_map)

    if "Avg Shipping Days" in grouped.columns:
        grouped["Avg Shipping Days"] = grouped["Avg Shipping Days"].round(1)

    return {
        "mode_breakdown": grouped.sort_values("Orders", ascending=False).reset_index(drop=True),
        "avg_days": round(avg_days, 1) if avg_days is not None else None
    }
