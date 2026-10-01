"""
backend/analytics/insights.py
Generates data-grounded, deterministic executive insights and anomalies
without speculative claims, adhering to PRD Section 5.3.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


def generate_executive_insights(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes grounded narrative takeaways, key drivers, and transaction anomalies.
    """
    if df is None or len(df) == 0:
        return {"findings": [], "anomalies": pd.DataFrame(), "summary_bullets": []}

    findings = []
    summary_bullets = []

    has_sales = "_std_sales" in df.columns
    has_profit = "_std_profit" in df.columns
    has_category = "_std_category" in df.columns
    has_sub_category = "_std_sub_category" in df.columns
    has_state = "_std_state" in df.columns
    has_region = "_std_region" in df.columns
    has_product = "_std_product_name" in df.columns
    has_order_date = "_std_order_date" in df.columns

    total_sales = float(df["_std_sales"].sum()) if has_sales else 0.0
    total_profit = float(df["_std_profit"].sum()) if has_profit else 0.0

    # 1. Category Findings
    if has_category and has_sales:
        cat_sales = df.groupby("_std_category")["_std_sales"].sum().sort_values(ascending=False)
        top_cat = cat_sales.index[0]
        top_cat_sales = cat_sales.iloc[0]
        top_cat_share = (top_cat_sales / total_sales * 100) if total_sales > 0 else 0
        findings.append({
            "type": "positive",
            "category": "Category Leadership",
            "title": f"Top Category: {top_cat}",
            "text": f"Generates {top_cat_sales:,.2f} in sales, representing {top_cat_share:.1f}% of overall revenue."
        })
        summary_bullets.append(f"**{top_cat}** is the largest revenue category ({top_cat_share:.1f}% share).")

    # 2. Profitability Drivers & Loss-Making Categories / Sub-Categories
    if has_sub_category and has_profit:
        sub_profit = df.groupby("_std_sub_category")["_std_profit"].sum().sort_values(ascending=False)
        best_sub = sub_profit.index[0]
        best_sub_prof = sub_profit.iloc[0]
        worst_sub = sub_profit.index[-1]
        worst_sub_prof = sub_profit.iloc[-1]

        findings.append({
            "type": "info",
            "category": "Sub-Category Performance",
            "title": f"Highest Profit Driver: {best_sub}",
            "text": f"Contributed {best_sub_prof:,.2f} in net profit."
        })

        if worst_sub_prof < 0:
            findings.append({
                "type": "warning",
                "category": "Profit Drain Warning",
                "title": f"Loss-Making Sub-Category: {worst_sub}",
                "text": f"Accumulated a net loss of {abs(worst_sub_prof):,.2f}."
            })
            summary_bullets.append(f"Sub-category **{worst_sub}** generated an aggregate loss of {abs(worst_sub_prof):,.2f}.")

    # 3. Geographic Highlights
    if has_state and has_sales:
        state_sales = df.groupby("_std_state")["_std_sales"].sum().sort_values(ascending=False)
        top_state = state_sales.index[0]
        top_state_sales = state_sales.iloc[0]
        findings.append({
            "type": "positive",
            "category": "Geographic Leader",
            "title": f"Top Performing State: {top_state}",
            "text": f"Leads all states with {top_state_sales:,.2f} in total sales."
        })
        summary_bullets.append(f"State leader is **{top_state}** with {top_state_sales:,.2f} in sales.")

    # 4. Regional Profit Margins
    if has_region and has_sales and has_profit:
        reg_agg = df.groupby("_std_region").agg({"_std_sales": "sum", "_std_profit": "sum"})
        reg_agg["margin"] = reg_agg["_std_profit"] / reg_agg["_std_sales"] * 100
        reg_agg = reg_agg.sort_values("margin", ascending=False)
        best_reg = reg_agg.index[0]
        worst_reg = reg_agg.index[-1]
        findings.append({
            "type": "info",
            "category": "Regional Margin",
            "title": f"Highest Margin Region: {best_reg}",
            "text": f"Achieved a {reg_agg.loc[best_reg, 'margin']:.1f}% profit margin compared to {worst_reg} at {reg_agg.loc[worst_reg, 'margin']:.1f}%."
        })

    # 5. Anomaly Detection (Outlier high transactions & extreme loss items)
    anomalies = pd.DataFrame()
    if has_sales:
        sales_thresh = df["_std_sales"].quantile(0.995)
        outliers = df[df["_std_sales"] >= sales_thresh].copy()
        
        display_cols = []
        for c in ["_std_order_id", "_std_order_date", "_std_customer_name", "_std_product_name", "_std_sales", "_std_profit"]:
            if c in outliers.columns:
                display_cols.append(c)

        if display_cols:
            anomalies = outliers[display_cols].rename(columns={
                "_std_order_id": "Order ID",
                "_std_order_date": "Date",
                "_std_customer_name": "Customer",
                "_std_product_name": "Product",
                "_std_sales": "Sales",
                "_std_profit": "Profit"
            }).sort_values("Sales", ascending=False).head(10)

    # 6. Yearly Growth (if multi-year)
    if has_order_date and has_sales:
        df_valid = df.dropna(subset=["_std_order_date"])
        years = sorted(df_valid["_std_order_date"].dt.year.unique())
        if len(years) >= 2:
            y1, y2 = years[0], years[1]
            s1 = df_valid[df_valid["_std_order_date"].dt.year == y1]["_std_sales"].sum()
            s2 = df_valid[df_valid["_std_order_date"].dt.year == y2]["_std_sales"].sum()
            growth = ((s2 - s1) / s1 * 100) if s1 > 0 else 0
            findings.append({
                "type": "positive" if growth >= 0 else "warning",
                "category": "Annual Growth",
                "title": f"YoY Revenue Change ({y1} to {y2})",
                "text": f"Sales grew from {s1:,.2f} to {s2:,.2f} ({growth:+.1f}%)."
            })
            summary_bullets.append(f"Revenue changed by **{growth:+.1f}%** between {y1} and {y2}.")

    return {
        "findings": findings,
        "anomalies": anomalies,
        "summary_bullets": summary_bullets
    }
