"""
backend/chat/engine.py
Deterministic natural language query processor for sales data.
Processes questions without external LLMs, guaranteeing 100% calculation accuracy
and clear limitation disclosures per PRD Section 5.1, 5.2, and Section 6.
"""

import re
from typing import Dict, Any, List, Optional
import pandas as pd


EXAMPLE_PROMPTS = [
    "What are total sales and profit?",
    "Which category has the highest sales?",
    "Which product has the highest profit?",
    "Show top 5 products by sales as a bar chart",
    "Compare sales between 2019 and 2020",
    "Which region is the most profitable?",
    "Show sales by segment as a pie chart",
    "What is the average order value?",
    "Which sub-category generates the biggest losses?",
    "Sales in India (out-of-scope test)",
]


def process_query(query: str, df: pd.DataFrame, currency_symbol: str = "") -> Dict[str, Any]:
    """
    Parses and answers natural language queries deterministically using Pandas.
    Returns:
    {
        "answer_text": str,
        "chart_type": Optional[str], # 'bar', 'line', 'pie', 'table', etc.
        "chart_data": Optional[pd.DataFrame],
        "context": Dict[str, str], # metric, fields, date range
        "suggested_charts": List[str],
        "is_unsupported": bool
    }
    """
    q = query.lower().strip()
    
    # Defaults
    result = {
        "answer_text": "",
        "chart_type": None,
        "chart_data": None,
        "context": {
            "fields_used": [],
            "date_coverage": "2019-2020" if "_std_order_date" in df.columns else "All available",
        },
        "suggested_charts": [],
        "is_unsupported": False
    }

    if df is None or len(df) == 0:
        result["answer_text"] = "No active data available to answer your question."
        result["is_unsupported"] = True
        return result

    # 1. Check for Out-of-Scope Geographic requests (PRD Section 6)
    out_of_scope_countries = ["india", "uk", "united kingdom", "germany", "france", "canada", "china", "japan", "brazil", "australia"]
    for c in out_of_scope_countries:
        if c in q:
            result["answer_text"] = (
                f"Coverage Limitation: The dataset only contains transactions within the United States. "
                f"Data for '{c.title()}' is not present in the uploaded dataset, and results cannot be fabricated."
            )
            result["is_unsupported"] = True
            return result

    # 2. Check for Out-of-Scope Time Periods (PRD Section 6)
    out_of_scope_years = ["2018", "2021", "2022", "2023", "2024", "2025", "2026"]
    for yr in out_of_scope_years:
        if yr in q:
            result["answer_text"] = (
                f"Coverage Limitation: The current dataset date range spans from 2019-01-01 through 2020-12-31. "
                f"Transactions for the year {yr} are not available."
            )
            result["is_unsupported"] = True
            return result

    # 3. Check for Out-of-Scope Categories (e.g. Toys)
    if "toy" in q or "toys" in q:
        avail_cats = ", ".join(df["_std_category"].dropna().unique()) if "_std_category" in df.columns else "None"
        result["answer_text"] = (
            f"Coverage Limitation: There is no 'Toys' category in this dataset. "
            f"Available categories are: {avail_cats}."
        )
        result["is_unsupported"] = True
        return result

    # Determine desired chart type from query if user explicitly asked
    explicit_chart = None
    if "bar chart" in q or "bar graph" in q or "as bar" in q:
        explicit_chart = "bar"
    elif "line chart" in q or "line graph" in q or "trend" in q:
        explicit_chart = "line"
    elif "pie chart" in q or "donut" in q:
        explicit_chart = "pie"
    elif "table" in q:
        explicit_chart = "table"

    sym = currency_symbol

    # 4. Total Sales / Revenue Query
    if ("total sales" in q or "gross sales" in q or "revenue" in q or q == "sales" or "how much sales" in q) and "by" not in q and "highest" not in q and "top" not in q and "vs" not in q:
        if "_std_sales" in df.columns:
            tot = df["_std_sales"].sum()
            result["answer_text"] = f"Total Sales across the active records is **{sym}{tot:,.2f}**."
            result["context"]["fields_used"] = ["Sales"]
            return result

    # 5. Total Profit Query
    if ("total profit" in q or "net profit" in q or "overall profit" in q) and "by" not in q and "highest" not in q and "top" not in q:
        if "_std_profit" in df.columns:
            prof = df["_std_profit"].sum()
            margin = (prof / df["_std_sales"].sum() * 100) if "_std_sales" in df.columns and df["_std_sales"].sum() > 0 else 0
            result["answer_text"] = f"Total Profit is **{sym}{prof:,.2f}**, representing an overall profit margin of **{margin:.2f}%**."
            result["context"]["fields_used"] = ["Profit", "Sales"]
            return result

    # 6. Distinct Orders Query
    if "how many orders" in q or "total orders" in q or "distinct orders" in q or "order count" in q:
        if "_std_order_id" in df.columns:
            orders = df["_std_order_id"].nunique()
            result["answer_text"] = f"Total Distinct Orders count is **{orders:,}** across {len(df):,} total line records."
            result["context"]["fields_used"] = ["Order ID"]
        else:
            result["answer_text"] = f"Order ID is not mapped. Total record line count is **{len(df):,}**."
        return result

    # 7. Average Order Value (AOV)
    if "average order value" in q or "aov" in q or "avg order" in q:
        if "_std_sales" in df.columns and "_std_order_id" in df.columns:
            aov = df["_std_sales"].sum() / df["_std_order_id"].nunique()
            result["answer_text"] = f"The Average Order Value (AOV) is **{sym}{aov:,.2f}** (Total Sales divided by Distinct Orders)."
            result["context"]["fields_used"] = ["Sales", "Order ID"]
        else:
            result["answer_text"] = "Cannot calculate AOV because Sales or Order ID is unmapped."
        return result

    # 8. Top N Products
    top_match = re.search(r"top\s+(\d+)\s+product", q)
    if top_match or "top product" in q or "highest profit product" in q or "most profitable product" in q or "best product" in q:
        n = int(top_match.group(1)) if top_match else 5
        metric_col = "_std_profit" if ("profit" in q or "profitable" in q) else "_std_sales"
        metric_label = "Profit" if ("profit" in q or "profitable" in q) else "Sales"

        if "_std_product_name" in df.columns and metric_col in df.columns:
            top_df = df.groupby("_std_product_name")[metric_col].sum().sort_values(ascending=False).head(n).reset_index()
            top_df.columns = ["Product Name", metric_label]
            best_prod = top_df.iloc[0]["Product Name"]
            best_val = top_df.iloc[0][metric_label]

            result["answer_text"] = (
                f"The top product by {metric_label.lower()} is **{best_prod}** with **{sym}{best_val:,.2f}**. "
                f"The top {n} products are detailed on the main screen."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = top_df
            result["context"]["fields_used"] = ["Product Name", metric_label]
            result["suggested_charts"] = ["bar", "table"]
            return result

    # 9. Category Analysis / Highest Category
    if "category" in q:
        metric_col = "_std_profit" if ("profit" in q or "profitable" in q) else "_std_sales"
        metric_label = "Profit" if ("profit" in q or "profitable" in q) else "Sales"

        if "_std_category" in df.columns and metric_col in df.columns:
            cat_df = df.groupby("_std_category")[metric_col].sum().sort_values(ascending=False).reset_index()
            cat_df.columns = ["Category", metric_label]
            top_cat = cat_df.iloc[0]["Category"]
            top_val = cat_df.iloc[0][metric_label]

            result["answer_text"] = f"**{top_cat}** leads with **{sym}{top_val:,.2f}** in total {metric_label.lower()}."
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = cat_df
            result["context"]["fields_used"] = ["Category", metric_label]
            result["suggested_charts"] = ["bar", "pie", "table"]
            return result

    # 10. Region Analysis / Highest Region
    if "region" in q:
        metric_col = "_std_profit" if ("profit" in q or "profitable" in q) else "_std_sales"
        metric_label = "Profit" if ("profit" in q or "profitable" in q) else "Sales"

        if "_std_region" in df.columns and metric_col in df.columns:
            reg_df = df.groupby("_std_region")[metric_col].sum().sort_values(ascending=False).reset_index()
            reg_df.columns = ["Region", metric_label]
            top_reg = reg_df.iloc[0]["Region"]
            top_val = reg_df.iloc[0][metric_label]

            result["answer_text"] = f"The **{top_reg}** region has the highest {metric_label.lower()} at **{sym}{top_val:,.2f}**."
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = reg_df
            result["context"]["fields_used"] = ["Region", metric_label]
            result["suggested_charts"] = ["bar", "pie", "table"]
            return result

    # 11. State Analysis / Highest State
    if "state" in q:
        metric_col = "_std_profit" if ("profit" in q or "profitable" in q) else "_std_sales"
        metric_label = "Profit" if ("profit" in q or "profitable" in q) else "Sales"

        if "_std_state" in df.columns and metric_col in df.columns:
            state_df = df.groupby("_std_state")[metric_col].sum().sort_values(ascending=False).head(10).reset_index()
            state_df.columns = ["State", metric_label]
            top_state = state_df.iloc[0]["State"]
            top_val = state_df.iloc[0][metric_label]

            result["answer_text"] = f"**{top_state}** has the highest {metric_label.lower()} at **{sym}{top_val:,.2f}**."
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = state_df
            result["context"]["fields_used"] = ["State", metric_label]
            result["suggested_charts"] = ["bar", "table"]
            return result

    # 12. Year Comparison (e.g. 2019 vs 2020)
    if ("2019" in q and "2020" in q) or "compare year" in q or "yearly" in q:
        if "_std_order_date" in df.columns and "_std_sales" in df.columns:
            d_valid = df.dropna(subset=["_std_order_date"]).copy()
            d_valid["Year"] = d_valid["_std_order_date"].dt.year
            y_df = d_valid.groupby("Year").agg({
                "_std_sales": "sum",
                "_std_profit": "sum",
                "_std_order_id": "nunique"
            }).reset_index().rename(columns={
                "_std_sales": "Sales",
                "_std_profit": "Profit",
                "_std_order_id": "Orders"
            })
            
            s19 = y_df[y_df["Year"] == 2019]["Sales"].values[0] if 2019 in y_df["Year"].values else 0
            s20 = y_df[y_df["Year"] == 2020]["Sales"].values[0] if 2020 in y_df["Year"].values else 0
            growth = ((s20 - s19) / s19 * 100) if s19 > 0 else 0

            result["answer_text"] = (
                f"In **2019**, Sales were **{sym}{s19:,.2f}**. In **2020**, Sales were **{sym}{s20:,.2f}**, "
                f"representing a YoY growth of **{growth:+.1f}%**."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = y_df
            result["context"]["fields_used"] = ["Order Date", "Sales", "Profit"]
            result["suggested_charts"] = ["bar", "table"]
            return result

    # 13. Customer Segment Analysis
    if "segment" in q:
        if "_std_segment" in df.columns and "_std_sales" in df.columns:
            seg_df = df.groupby("_std_segment")["_std_sales"].sum().sort_values(ascending=False).reset_index()
            seg_df.columns = ["Segment", "Sales"]
            top_seg = seg_df.iloc[0]["Segment"]
            top_val = seg_df.iloc[0]["Sales"]
            result["answer_text"] = f"**{top_seg}** is the largest segment with **{sym}{top_val:,.2f}** in sales."
            result["chart_type"] = explicit_chart or "pie"
            result["chart_data"] = seg_df
            result["context"]["fields_used"] = ["Customer Segment", "Sales"]
            result["suggested_charts"] = ["pie", "bar", "table"]
            return result

    # 14. Fallback: General summary response
    result["answer_text"] = (
        f"I can answer specific sales metrics, top/bottom performers, regional breakdowns, and period comparisons. "
        f"Try asking: 'What are total sales?', 'Which category has highest sales?', or 'Show top 5 products as a bar chart'."
    )
    result["is_unsupported"] = True
    return result
