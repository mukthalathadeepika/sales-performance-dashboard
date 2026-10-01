"""
backend/analytics/kpi.py
Computes core executive sales KPIs in strict accordance with PRD Section 4.1 and 6.1.
Ensures deterministic calculation and explicit handling of edge cases (e.g. distinct orders).
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def calculate_kpis(
    df: pd.DataFrame,
    sales_target: Optional[float] = None,
    previous_period_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Computes all standard KPIs for the provided DataFrame slice.
    If previous_period_df is provided, calculates period-over-period growth rates.
    """
    if df is None or len(df) == 0:
        return {
            "total_sales": 0.0,
            "total_profit": 0.0,
            "total_orders": 0,
            "is_distinct_orders": False,
            "total_quantity": 0,
            "total_customers": 0,
            "aov": 0.0,
            "profit_margin_pct": 0.0,
            "sales_growth_pct": None,
            "profit_growth_pct": None,
            "orders_growth_pct": None,
            "target_sales": sales_target,
            "target_achievement_pct": None,
            "loss_making_orders_count": 0,
            "loss_making_sales": 0.0,
        }

    # 1. Total Sales
    has_sales = "_std_sales" in df.columns
    total_sales = float(df["_std_sales"].dropna().sum()) if has_sales else 0.0

    # 2. Total Profit (may include negative values per PRD)
    has_profit = "_std_profit" in df.columns
    total_profit = float(df["_std_profit"].dropna().sum()) if has_profit else None

    # 3. Total Orders (MUST be DISTINCT Order IDs if available per PRD)
    has_order_id = "_std_order_id" in df.columns
    if has_order_id:
        total_orders = int(df["_std_order_id"].dropna().nunique())
        is_distinct_orders = True
    else:
        total_orders = int(len(df))
        is_distinct_orders = False

    # 4. Total Quantity
    has_qty = "_std_quantity" in df.columns
    total_qty = float(df["_std_quantity"].dropna().sum()) if has_qty else None

    # 5. Total Customers
    has_cust_id = "_std_customer_id" in df.columns
    has_cust_name = "_std_customer_name" in df.columns
    if has_cust_id:
        total_customers = int(df["_std_customer_id"].dropna().nunique())
    elif has_cust_name:
        total_customers = int(df["_std_customer_name"].dropna().nunique())
    else:
        total_customers = None

    # 6. Average Order Value (AOV = total sales / distinct orders)
    aov = None
    if has_sales and is_distinct_orders and total_orders > 0:
        aov = total_sales / total_orders

    # 7. Profit Margin % (total profit / total sales * 100)
    profit_margin_pct = None
    if has_sales and has_profit and total_sales != 0:
        profit_margin_pct = (total_profit / total_sales) * 100

    # 8. Loss-making items
    loss_orders_count = 0
    loss_sales = 0.0
    if has_profit:
        loss_slice = df[df["_std_profit"] < 0]
        loss_orders_count = int(loss_slice["_std_order_id"].nunique()) if has_order_id else len(loss_slice)
        loss_sales = float(loss_slice["_std_sales"].sum()) if has_sales else 0.0

    # 9. Target Achievement
    target_achievement_pct = None
    if sales_target and sales_target > 0:
        target_achievement_pct = (total_sales / sales_target) * 100

    # 10. Growth Metrics (Period-over-Period)
    sales_growth_pct = None
    profit_growth_pct = None
    orders_growth_pct = None

    if previous_period_df is not None and len(previous_period_df) > 0:
        prev_kpis = calculate_kpis(previous_period_df, sales_target=None, previous_period_df=None)
        
        # Sales Growth
        prev_sales = prev_kpis["total_sales"]
        if prev_sales > 0:
            sales_growth_pct = ((total_sales - prev_sales) / prev_sales) * 100
        
        # Profit Growth
        prev_profit = prev_kpis["total_profit"]
        if prev_profit is not None and prev_profit != 0:
            profit_growth_pct = ((total_profit - prev_profit) / abs(prev_profit)) * 100
            
        # Orders Growth
        prev_orders = prev_kpis["total_orders"]
        if prev_orders and prev_orders > 0 and total_orders is not None:
            orders_growth_pct = ((total_orders - prev_orders) / prev_orders) * 100

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "total_orders": total_orders,
        "is_distinct_orders": is_distinct_orders,
        "total_quantity": total_qty,
        "total_customers": total_customers,
        "aov": aov,
        "profit_margin_pct": profit_margin_pct,
        "target_sales": sales_target,
        "target_achievement_pct": target_achievement_pct,
        "sales_growth_pct": sales_growth_pct,
        "profit_growth_pct": profit_growth_pct,
        "orders_growth_pct": orders_growth_pct,
        "loss_making_orders_count": loss_orders_count,
        "loss_making_sales": loss_sales,
    }


def format_metric_value(val: Optional[float], prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    """Format numbers into readable executive strings with optional symbol and commas."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        formatted = f"{val:,.{decimals}f}"
        if decimals == 0:
            formatted = f"{int(round(val)):,}"
        return f"{prefix}{formatted}{suffix}"
    except Exception:
        return str(val)
