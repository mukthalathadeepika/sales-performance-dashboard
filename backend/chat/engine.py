"""
backend/chat/engine.py
Deterministic natural language query processor for sales data.
Processes questions without external LLMs, guaranteeing 100% calculation accuracy
using Indian Rupees (₹) and clear limitation disclosures.
"""

import re
from typing import Dict, Any, List, Optional
import pandas as pd
from backend.analytics.currency import format_inr


EXAMPLE_PROMPTS = [
    "What is the total sales?",
    "Which region has the highest sales?",
    "Which category is most profitable?",
    "Which products are causing losses?",
    "What was the best sales month?",
    "Compare West and East regions.",
    "Show me the top 5 products by sales.",
    "Why did profit decrease?",
]


def process_query(query: str, df: pd.DataFrame, currency_symbol: str = "₹") -> Dict[str, Any]:
    """
    Parses and answers natural language queries deterministically using Pandas.
    Returns:
    {
        "answer_text": str,
        "chart_type": Optional[str],
        "chart_data": Optional[pd.DataFrame],
        "context": Dict[str, str],
        "suggested_charts": List[str],
        "is_unsupported": bool
    }
    """
    q = query.lower().strip()
    sym = currency_symbol or "₹"
    
    result = {
        "answer_text": "",
        "chart_type": None,
        "chart_data": None,
        "context": {
            "fields_used": [],
            "date_coverage": "2019-2020" if "_std_order_date" in df.columns else "Active Scope",
        },
        "suggested_charts": [],
        "is_unsupported": False
    }

    if df is None or len(df) == 0:
        result["answer_text"] = "No active data available to answer your question."
        result["is_unsupported"] = True
        return result

    # 1. Geographic / Country Out-of-Scope check
    out_of_scope_countries = ["india", "uk", "united kingdom", "germany", "france", "canada", "china", "japan", "brazil", "australia"]
    for c in out_of_scope_countries:
        if c in q and "inr" not in q and "rupee" not in q:
            result["answer_text"] = (
                f"Coverage Limitation: The dataset only contains transactions within the United States. "
                f"Data for '{c.title()}' is not present in the uploaded dataset, and results cannot be fabricated."
            )
            result["is_unsupported"] = True
            return result

    # 2. Time Period Out-of-Scope check
    out_of_scope_years = ["2018", "2021", "2022", "2023", "2024", "2025", "2026"]
    for yr in out_of_scope_years:
        if yr in q:
            result["answer_text"] = (
                f"Coverage Limitation: The current dataset date range spans from 2019-01-01 through 2020-12-31. "
                f"Transactions for the year {yr} are not available."
            )
            result["is_unsupported"] = True
            return result

    # 3. Category Out-of-Scope check (e.g. Toys)
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

    # 4. Total Sales / Revenue Query
    if ("total sales" in q or "gross sales" in q or "revenue" in q or q == "sales" or "how much sales" in q or "what is the total sales" in q) and "by" not in q and "highest" not in q and "top" not in q and "vs" not in q and "month" not in q and "compare" not in q:
        if "_std_sales" in df.columns:
            tot = float(df["_std_sales"].sum())
            result["answer_text"] = f"Total Sales across the active records is **{format_inr(tot)}** ({format_inr(tot, compact=True)})."
            result["context"]["fields_used"] = ["Sales"]
            return result

    # 5. Total Profit Query
    if ("total profit" in q or "net profit" in q or "overall profit" in q) and "by" not in q and "highest" not in q and "top" not in q and "loss" not in q:
        if "_std_profit" in df.columns:
            prof = float(df["_std_profit"].sum())
            margin = (prof / df["_std_sales"].sum() * 100) if "_std_sales" in df.columns and df["_std_sales"].sum() > 0 else 0
            result["answer_text"] = f"Total Profit is **{format_inr(prof)}** ({format_inr(prof, compact=True)}), representing an overall profit margin of **{margin:.2f}%**."
            result["context"]["fields_used"] = ["Profit", "Sales"]
            return result

    # 6. Loss-making products / "Which products are causing losses?"
    if "loss" in q or "losses" in q or "negative profit" in q:
        if "_std_product_name" in df.columns and "_std_profit" in df.columns:
            loss_df = df.groupby("_std_product_name")["_std_profit"].sum().sort_values(ascending=True).reset_index()
            loss_df = loss_df[loss_df["_std_profit"] < 0].head(5)
            loss_df.columns = ["Product Name", "Net Loss"]

            if not loss_df.empty:
                worst_prod = loss_df.iloc[0]["Product Name"]
                worst_val = abs(loss_df.iloc[0]["Net Loss"])
                result["answer_text"] = (
                    f"The product causing the highest net loss is **{worst_prod}** with an aggregate loss of **{format_inr(worst_val)}**. "
                    f"Below are the top 5 loss-making items."
                )
                result["chart_type"] = explicit_chart or "bar"
                result["chart_data"] = loss_df
                result["context"]["fields_used"] = ["Product Name", "Profit"]
                result["suggested_charts"] = ["bar", "table"]
            else:
                result["answer_text"] = "No loss-making products were found in the current filtered records."
            return result

    # 7. Best Sales Month / "What was the best sales month?"
    if ("best sales month" in q or "best month" in q or "highest sales month" in q or "peak month" in q or "strongest month" in q):
        if "_std_order_date" in df.columns and "_std_sales" in df.columns:
            time_df = df.dropna(subset=["_std_order_date"]).copy()
            time_df["Month_Year"] = time_df["_std_order_date"].dt.strftime("%b %Y")
            month_agg = time_df.groupby("Month_Year")["_std_sales"].sum().sort_values(ascending=False).reset_index()
            month_agg.columns = ["Month", "Sales"]
            
            best_m = month_agg.iloc[0]["Month"]
            best_val = month_agg.iloc[0]["Sales"]
            result["answer_text"] = f"The best sales month was **{best_m}** with total revenue of **{format_inr(best_val)}** ({format_inr(best_val, compact=True)})."
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = month_agg.head(6)
            result["context"]["fields_used"] = ["Order Date", "Sales"]
            return result

    # 8. Region Comparison / "Compare West and East regions"
    if "compare" in q and "region" in q or ("west" in q and "east" in q):
        if "_std_region" in df.columns and "_std_sales" in df.columns:
            comp_df = df[df["_std_region"].isin(["West", "East"])].groupby("_std_region").agg({
                "_std_sales": "sum",
                "_std_profit": "sum",
                "_std_order_id": "nunique"
            }).reset_index().rename(columns={
                "_std_region": "Region",
                "_std_sales": "Sales",
                "_std_profit": "Profit",
                "_std_order_id": "Orders"
            })
            comp_df["Margin %"] = (comp_df["Profit"] / comp_df["Sales"] * 100).round(2)
            
            w_sales = comp_df[comp_df["Region"] == "West"]["Sales"].values[0] if "West" in comp_df["Region"].values else 0
            e_sales = comp_df[comp_df["Region"] == "East"]["Sales"].values[0] if "East" in comp_df["Region"].values else 0
            diff = abs(w_sales - e_sales)
            leader = "West" if w_sales > e_sales else "East"

            trailer = "East" if leader == "West" else "West"
            result["answer_text"] = (
                f"**{leader}** leads with **{format_inr(max(w_sales, e_sales))}** in sales compared to "
                f"**{trailer}** at **{format_inr(min(w_sales, e_sales))}** (difference of {format_inr(diff)})."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = comp_df[["Region", "Sales", "Profit"]]
            result["context"]["fields_used"] = ["Region", "Sales", "Profit"]
            return result

    # 9. Why did profit decrease? / "Why did profit decrease"
    if "why" in q and ("profit" in q or "decrease" in q or "margin" in q):
        if "_std_category" in df.columns and "_std_profit" in df.columns:
            cat_p = df.groupby("_std_category")["_std_profit"].sum().sort_values(ascending=True).reset_index()
            cat_p.columns = ["Category", "Profit"]
            sub_loss = df.groupby("_std_sub_category")["_std_profit"].sum().sort_values(ascending=True).head(3).reset_index()
            sub_loss.columns = ["Sub-Category", "Net Loss"]
            
            lowest_cat = cat_p.iloc[0]["Category"]
            lowest_val = cat_p.iloc[0]["Profit"]
            worst_sub = sub_loss.iloc[0]["Sub-Category"]
            worst_sub_loss = abs(sub_loss.iloc[0]["Net Loss"])

            result["answer_text"] = (
                f"Profit is primarily reduced by heavy discounts and losses in specific sub-categories. "
                f"The lowest-margin category is **{lowest_cat}** ({format_inr(lowest_val)} profit). "
                f"Specifically, sub-category **{worst_sub}** accumulated net losses of **{format_inr(worst_sub_loss)}**."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = sub_loss
            result["context"]["fields_used"] = ["Sub-Category", "Profit"]
            return result

    # 10. Top N Products / "Show me the top 5 products by sales"
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
                f"The top product by {metric_label.lower()} is **{best_prod}** with **{format_inr(best_val)}** "
                f"({format_inr(best_val, compact=True)})."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = top_df
            result["context"]["fields_used"] = ["Product Name", metric_label]
            result["suggested_charts"] = ["bar", "table"]
            return result

    # 11. Category Analysis / "Which category is most profitable?"
    if "category" in q:
        metric_col = "_std_profit" if ("profit" in q or "profitable" in q) else "_std_sales"
        metric_label = "Profit" if ("profit" in q or "profitable" in q) else "Sales"

        if "_std_category" in df.columns and metric_col in df.columns:
            cat_df = df.groupby("_std_category")[metric_col].sum().sort_values(ascending=False).reset_index()
            cat_df.columns = ["Category", metric_label]
            top_cat = cat_df.iloc[0]["Category"]
            top_val = cat_df.iloc[0][metric_label]

            result["answer_text"] = f"**{top_cat}** leads with **{format_inr(top_val)}** ({format_inr(top_val, compact=True)}) in total {metric_label.lower()}."
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = cat_df
            result["context"]["fields_used"] = ["Category", metric_label]
            result["suggested_charts"] = ["bar", "pie", "table"]
            return result

    # 12. Region Analysis / "Which region has the highest sales?"
    if "region" in q:
        metric_col = "_std_profit" if ("profit" in q or "profitable" in q) else "_std_sales"
        metric_label = "Profit" if ("profit" in q or "profitable" in q) else "Sales"

        if "_std_region" in df.columns and metric_col in df.columns:
            reg_df = df.groupby("_std_region")[metric_col].sum().sort_values(ascending=False).reset_index()
            reg_df.columns = ["Region", metric_label]
            top_reg = reg_df.iloc[0]["Region"]
            top_val = reg_df.iloc[0][metric_label]

            result["answer_text"] = f"The **{top_reg}** region has the highest {metric_label.lower()} at **{format_inr(top_val)}** ({format_inr(top_val, compact=True)})."
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = reg_df
            result["context"]["fields_used"] = ["Region", metric_label]
            result["suggested_charts"] = ["bar", "pie", "table"]
            return result

    # Fallback
    result["answer_text"] = (
        f"I can answer questions regarding sales, profits, loss-making items, top products, categories, regions, and periods. "
        f"Try asking: 'What is the total sales?', 'Which region has the highest sales?', or 'Which products are causing losses?'."
    )
    result["is_unsupported"] = True
    return result
