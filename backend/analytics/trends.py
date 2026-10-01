"""
backend/analytics/trends.py
Aggregates sales and profit metrics across time dimensions (monthly, quarterly, yearly).
"""

from typing import Dict, Any, Optional
import pandas as pd


def get_time_trends(df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """
    Groups data by order date with specified frequency:
    'M' = Monthly, 'Q' = Quarterly, 'Y' = Yearly, 'W' = Weekly
    """
    if df is None or len(df) == 0 or "_std_order_date" not in df.columns:
        return pd.DataFrame()

    valid_df = df.dropna(subset=["_std_order_date"]).copy()
    if len(valid_df) == 0:
        return pd.DataFrame()

    # Set datetime index
    valid_df = valid_df.sort_values("_std_order_date")
    
    # Resample or group by period
    if freq == "M":
        valid_df["period"] = valid_df["_std_order_date"].dt.to_period("M").dt.to_timestamp()
        valid_df["period_label"] = valid_df["_std_order_date"].dt.strftime("%b %Y")
    elif freq == "Q":
        valid_df["period"] = valid_df["_std_order_date"].dt.to_period("Q").dt.to_timestamp()
        valid_df["period_label"] = valid_df["_std_order_date"].dt.to_period("Q").astype(str)
    elif freq == "Y":
        valid_df["period"] = valid_df["_std_order_date"].dt.to_period("Y").dt.to_timestamp()
        valid_df["period_label"] = valid_df["_std_order_date"].dt.strftime("%Y")
    elif freq == "W":
        valid_df["period"] = valid_df["_std_order_date"].dt.to_period("W").dt.to_timestamp()
        valid_df["period_label"] = valid_df["_std_order_date"].dt.strftime("%Y-W%W")
    else:
        valid_df["period"] = valid_df["_std_order_date"].dt.to_period("M").dt.to_timestamp()
        valid_df["period_label"] = valid_df["_std_order_date"].dt.strftime("%b %Y")

    agg_dict = {}
    if "_std_sales" in valid_df.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in valid_df.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in valid_df.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in valid_df.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = valid_df.groupby(["period", "period_label"], as_index=False).agg(agg_dict)
    grouped = grouped.sort_values("period").reset_index(drop=True)

    # Rename columns for clarity
    rename_map = {
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    }
    grouped = grouped.rename(columns=rename_map)

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)
        grouped["Cumulative Sales"] = grouped["Sales"].cumsum()

    return grouped
