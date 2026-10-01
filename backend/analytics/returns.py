"""
backend/analytics/returns.py
Returns rate and impact analysis with clear data completeness disclosures.
"""

from typing import Dict, Any
import pandas as pd


def get_returns_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes returns metrics and breakdown by category and region.
    Discloses coverage gaps in accordance with PRD Section 4.2 and Section 6.
    """
    if df is None or len(df) == 0 or "_std_returns" not in df.columns:
        return {
            "has_returns_data": False,
            "total_returns": 0,
            "return_rate_pct": 0.0,
            "returned_sales": 0.0,
            "category_returns": pd.DataFrame(),
            "region_returns": pd.DataFrame(),
            "limitation_note": "No Returns field mapped in the current dataset."
        }

    total_records = len(df)
    has_orders = "_std_order_id" in df.columns
    total_orders = df["_std_order_id"].nunique() if has_orders else total_records

    # Tracked returns (value == 1)
    returns_slice = df[df["_std_returns"] == 1]
    return_records_count = len(returns_slice)
    return_orders_count = returns_slice["_std_order_id"].nunique() if has_orders else return_records_count

    return_rate_pct = (return_orders_count / total_orders * 100) if total_orders > 0 else 0.0
    returned_sales = float(returns_slice["_std_sales"].sum()) if "_std_sales" in returns_slice.columns else 0.0

    # Category returns breakdown
    cat_df = pd.DataFrame()
    if "_std_category" in df.columns:
        cat_total = df.groupby("_std_category")["_std_order_id"].nunique() if has_orders else df.groupby("_std_category").size()
        cat_ret = returns_slice.groupby("_std_category")["_std_order_id"].nunique() if has_orders else returns_slice.groupby("_std_category").size()
        cat_df = pd.DataFrame({"Total Orders": cat_total, "Returned Orders": cat_ret}).fillna(0)
        cat_df["Return Rate %"] = (cat_df["Returned Orders"] / cat_df["Total Orders"] * 100).round(2)
        cat_df = cat_df.reset_index().rename(columns={"_std_category": "Category"}).sort_values("Return Rate %", ascending=False)

    # Region returns breakdown
    reg_df = pd.DataFrame()
    if "_std_region" in df.columns:
        reg_total = df.groupby("_std_region")["_std_order_id"].nunique() if has_orders else df.groupby("_std_region").size()
        reg_ret = returns_slice.groupby("_std_region")["_std_order_id"].nunique() if has_orders else returns_slice.groupby("_std_region").size()
        reg_df = pd.DataFrame({"Total Orders": reg_total, "Returned Orders": reg_ret}).fillna(0)
        reg_df["Return Rate %"] = (reg_df["Returned Orders"] / reg_df["Total Orders"] * 100).round(2)
        reg_df = reg_df.reset_index().rename(columns={"_std_region": "Region"}).sort_values("Return Rate %", ascending=False)

    return {
        "has_returns_data": True,
        "total_returns": return_orders_count,
        "return_rate_pct": round(return_rate_pct, 2),
        "returned_sales": round(returned_sales, 2),
        "category_returns": cat_df,
        "region_returns": reg_df,
        "limitation_note": (
            "Notice on Data Coverage: Returns are recorded as positive indicators (1), with remaining rows "
            "unflagged (#N/A). Return percentages represent tracked recorded returns."
        )
    }
