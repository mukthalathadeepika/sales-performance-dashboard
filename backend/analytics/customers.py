"""
backend/analytics/customers.py
Customer segment and individual customer performance analysis.
"""

from typing import Tuple
import pandas as pd


def get_segment_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates metrics by customer segment."""
    if df is None or len(df) == 0 or "_std_segment" not in df.columns:
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
    if "_std_customer_id" in df.columns:
        agg_dict["_std_customer_id"] = "nunique"

    grouped = df.groupby("_std_segment", as_index=False).agg(agg_dict)
    grouped = grouped.rename(columns={
        "_std_segment": "Segment",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
        "_std_customer_id": "Customers",
    })

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).reset_index(drop=True)


def get_top_customers(df: pd.DataFrame, n: int = 10, include_names: bool = True) -> pd.DataFrame:
    """Ranks top customers by total sales."""
    cust_id_col = "_std_customer_id" if "_std_customer_id" in df.columns else None
    cust_name_col = "_std_customer_name" if "_std_customer_name" in df.columns else None

    if not cust_id_col and not cust_name_col:
        return pd.DataFrame()

    group_cols = []
    if cust_id_col:
        group_cols.append(cust_id_col)
    if cust_name_col and include_names:
        group_cols.append(cust_name_col)

    agg_dict = {}
    if "_std_sales" in df.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in df.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_order_id" in df.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = df.groupby(group_cols, as_index=False).agg(agg_dict)
    
    rename_map = {
        "_std_customer_id": "Customer ID",
        "_std_customer_name": "Customer Name",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_order_id": "Orders",
    }
    grouped = grouped.rename(columns=rename_map)

    if not include_names and "Customer Name" in grouped.columns:
        grouped = grouped.drop(columns=["Customer Name"])

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).head(n).reset_index(drop=True)
