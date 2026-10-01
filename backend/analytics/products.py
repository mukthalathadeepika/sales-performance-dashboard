"""
backend/analytics/products.py
Product-level sales, profitability, and ranking analysis.
"""

from typing import Tuple
import pandas as pd


def get_product_rankings(
    df: pd.DataFrame,
    metric: str = "Sales",
    n: int = 10
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (top_n_df, bottom_n_df) for products based on selected metric:
    'Sales', 'Profit', or 'Quantity'.
    """
    prod_col = "_std_product_name" if "_std_product_name" in df.columns else None
    if not prod_col:
        return pd.DataFrame(), pd.DataFrame()

    agg_dict = {}
    if "_std_sales" in df.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in df.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in df.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in df.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = df.groupby(prod_col, as_index=False).agg(agg_dict)
    grouped = grouped.rename(columns={
        prod_col: "Product Name",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    })

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    sort_col = metric if metric in grouped.columns else "Sales"
    top_n = grouped.sort_values(sort_col, ascending=False).head(n).reset_index(drop=True)
    bottom_n = grouped.sort_values(sort_col, ascending=True).head(n).reset_index(drop=True)

    return top_n, bottom_n
