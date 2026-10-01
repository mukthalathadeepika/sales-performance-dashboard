"""
backend/analytics/categories.py
Category and Sub-Category comparative breakdown and margin analysis.
"""

import pandas as pd


def get_category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates metrics at Category level."""
    if df is None or len(df) == 0 or "_std_category" not in df.columns:
        return pd.DataFrame()

    agg_dict = {}
    if "_std_sales" in df.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in df.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in df.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in df.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = df.groupby("_std_category", as_index=False).agg(agg_dict)
    grouped = grouped.rename(columns={
        "_std_category": "Category",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    })

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).reset_index(drop=True)


def get_subcategory_breakdown(df: pd.DataFrame, category_filter: str = None) -> pd.DataFrame:
    """Aggregates metrics at Sub-Category level, optionally filtered by Category."""
    if df is None or len(df) == 0 or "_std_sub_category" not in df.columns:
        return pd.DataFrame()

    filtered = df
    if category_filter and "_std_category" in df.columns:
        filtered = df[df["_std_category"] == category_filter]

    group_cols = ["_std_sub_category"]
    if "_std_category" in filtered.columns:
        group_cols = ["_std_category", "_std_sub_category"]

    agg_dict = {}
    if "_std_sales" in filtered.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in filtered.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in filtered.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in filtered.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = filtered.groupby(group_cols, as_index=False).agg(agg_dict)
    rename_map = {
        "_std_category": "Category",
        "_std_sub_category": "Sub-Category",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    }
    grouped = grouped.rename(columns=rename_map)

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).reset_index(drop=True)
