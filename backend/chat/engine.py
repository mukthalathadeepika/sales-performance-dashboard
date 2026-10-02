"""
backend/chat/engine.py
Deterministic NLP query processor for the active sales dataset.
Answers are calculated from data only — never invented.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
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
    "What is the average order value?",
]

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def _has(df, col):
    return col in df.columns


def _get_date_range(df):
    if _has(df, "_std_order_date"):
        valid = df["_std_order_date"].dropna()
        if len(valid) > 0:
            return f"{valid.min().strftime('%Y-%m-%d')} to {valid.max().strftime('%Y-%m-%d')}"
    return "Active Scope"


def process_query(query: str, df: pd.DataFrame, currency_symbol: str = "₹",
                  prev_context: Optional[Dict] = None) -> Dict[str, Any]:
    q = query.lower().strip()
    prev_context = prev_context or {}

    result = {
        "answer_text": "",
        "chart_type": None,
        "chart_data": None,
        "context": {
            "fields_used": [],
            "date_coverage": _get_date_range(df),
            "last_dimension": prev_context.get("last_dimension"),
            "last_metric": prev_context.get("last_metric"),
            "last_entity": prev_context.get("last_entity"),
        },
        "suggested_charts": [],
        "is_unsupported": False,
    }

    if df is None or len(df) == 0:
        result["answer_text"] = "No active data available. Please upload a dataset first."
        result["is_unsupported"] = True
        return result

    coverage = _coverage_limitation(q, df)
    if coverage:
        result["answer_text"] = coverage
        result["is_unsupported"] = True
        return result

    explicit_chart = None
    if any(w in q for w in ["bar chart", "bar graph", "as bar"]):
        explicit_chart = "bar"
    elif any(w in q for w in ["line chart", "line graph", "trend"]):
        explicit_chart = "line"
    elif any(w in q for w in ["pie chart", "donut"]):
        explicit_chart = "pie"
    elif "table" in q:
        explicit_chart = "table"

    n_match = re.search(r"\b(\d+)\b", q)
    top_n = int(n_match.group(1)) if n_match and 1 <= int(n_match.group(1)) <= 100 else 5

    wants_profit = any(w in q for w in ["profit", "profitable", "profitability", "margin", "earnings"])
    wants_sales = any(w in q for w in ["sales", "revenue", "turnover", "sold"])
    wants_qty = any(w in q for w in ["quantity", "units", "volume", "qty"])
    wants_orders = any(w in q for w in ["orders", "order count", "transactions"])

    if not any([wants_profit, wants_sales, wants_qty, wants_orders]):
        last_m = (prev_context.get("last_metric") or "").lower()
        if last_m == "profit" or ("what about" in q and "profit" in q):
            wants_profit = True
        elif last_m == "quantity":
            wants_qty = True
        else:
            wants_sales = True

    metric_col = "_std_profit" if wants_profit else "_std_quantity" if wants_qty else "_std_sales"
    metric_label = "Profit" if wants_profit else "Quantity" if wants_qty else "Sales"
    if wants_orders:
        metric_col = "_std_order_id" if _has(df, "_std_order_id") else metric_col
        metric_label = "Orders" if _has(df, "_std_order_id") else metric_label

    if metric_col not in df.columns:
        result["answer_text"] = (
            f"I can't answer that from the current dataset because {metric_label} is not available."
        )
        result["is_unsupported"] = True
        return result

    is_compare = "compare" in q or " vs " in q or "versus" in q or "compared" in q
    work_df = df
    entity_note = ""
    if not is_compare:
        entities = _find_named_entities(q, df)
        if len(entities) == 1:
            col, val = entities[0]
            work_df = df[df[col].astype(str) == val]
            entity_note = f" for {val}"
            result["context"]["last_entity"] = val
            if work_df.empty:
                result["answer_text"] = f"No rows found for **{val}** in the current dataset."
                result["is_unsupported"] = True
                return result

    if is_compare:
        return _handle_comparison(q, df, metric_col, metric_label, explicit_chart, result, prev_context)

    if "contribut" in q or (("share" in q or "percentage" in q) and _detect_dimension(q, df, prev_context)[0]):
        contrib = _handle_contribution(q, df, work_df, entity_note, metric_col, metric_label, explicit_chart, result)
        if contrib:
            return contrib

    if any(w in q for w in ["monthly", "by month", "over time", "time series", "what happened", "how did", "performance in", "trend in"]) or (
        any(w in q for w in ["show", "display", "plot", "chart"])
        and any(w in q for w in ["month", "year", "week", "daily", "trend"])
    ):
        ts = _handle_timeseries(q, work_df, metric_col, metric_label, explicit_chart, result, entity_note)
        if ts:
            return ts

    if "average order" in q or "aov" in q or "avg order" in q:
        if _has(work_df, "_std_sales") and _has(work_df, "_std_order_id"):
            total_s = work_df["_std_sales"].sum()
            n_orders = work_df["_std_order_id"].nunique()
            aov = total_s / n_orders if n_orders > 0 else 0
            result["answer_text"] = (
                f"Average Order Value{entity_note}: **{format_inr(aov)}** "
                f"across {n_orders:,} distinct orders."
            )
            result["context"]["last_metric"] = "sales"
            return result
        result["answer_text"] = "I can't answer that from the current dataset because order identifiers are not available."
        result["is_unsupported"] = True
        return result

    if _is_total_query(q) and not _is_grouping_query(q):
        val = _metric_sum(work_df, metric_col, metric_label)
        result["answer_text"] = (
            f"Total {metric_label}{entity_note}: **{format_inr(val)}** ({format_inr(val, compact=True)})."
        )
        if metric_label == "Sales" and _has(work_df, "_std_profit"):
            profit = float(work_df["_std_profit"].sum())
            margin = (profit / val * 100) if val else 0
            result["answer_text"] += f" Total Profit: **{format_inr(profit)}** (margin: {margin:.1f}%)."
        result["context"]["last_metric"] = metric_label.lower()
        return result

    if any(w in q for w in ["best month", "peak month", "strongest month", "highest month",
                            "best sales month", "worst month", "weakest month", "lowest month",
                            "which month", "month performed"]):
        if _has(work_df, "_std_order_date"):
            ascending = any(w in q for w in ["worst", "weakest", "lowest"])
            time_df = work_df.dropna(subset=["_std_order_date"]).copy()
            time_df["_period"] = time_df["_std_order_date"].dt.strftime("%b %Y")
            agg = time_df.groupby("_period")[metric_col].sum().sort_values(ascending=ascending).reset_index()
            agg.columns = ["Month", metric_label]
            top = agg.iloc[0]
            word = "worst" if ascending else "best"
            result["answer_text"] = (
                f"The {word} month by {metric_label.lower()}{entity_note} was **{top['Month']}** "
                f"with **{format_inr(top[metric_label])}**."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = agg.head(12)
            result["context"]["last_dimension"] = "month"
            result["context"]["last_metric"] = metric_label.lower()
            return result

    if any(w in q for w in ["loss", "losses", "losing", "negative profit", "loss-making", "loss making", "high sales but", "worst product", "worst products"]):
        if _has(work_df, "_std_profit"):
            group_col = "_std_product_name" if _has(work_df, "_std_product_name") else (
                "_std_sub_category" if _has(work_df, "_std_sub_category") else None
            )
            if group_col:
                label = "Product" if "product" in group_col else "Sub-Category"
                grouped = work_df.groupby(group_col).agg(
                    Profit=("_std_profit", "sum"),
                    Sales=("_std_sales", "sum") if _has(work_df, "_std_sales") else ("_std_profit", "sum"),
                ).reset_index()
                grouped.columns = [label, "Profit", "Sales"] if grouped.shape[1] == 3 else [label, "Profit"]
                if "high sales" in q:
                    loss_df = grouped[grouped["Profit"] <= 0].sort_values("Sales", ascending=False).head(top_n)
                else:
                    loss_df = grouped[grouped["Profit"] < 0].sort_values("Profit").head(top_n)
                    loss_df = loss_df.rename(columns={"Profit": "Net Loss"})
                    if "Net Loss" in loss_df.columns:
                        loss_df["Net Loss"] = loss_df["Net Loss"].abs()
                if not loss_df.empty:
                    first = loss_df.iloc[0]
                    money_col = "Net Loss" if "Net Loss" in loss_df.columns else "Profit"
                    result["answer_text"] = (
                        f"The biggest loss-maker{entity_note} is **{first[label]}** with a net loss of "
                        f"**{format_inr(abs(first[money_col]))}** ({len(loss_df)} loss-making {label.lower()}(s) identified)."
                    )
                    result["chart_type"] = explicit_chart or "bar"
                    result["chart_data"] = loss_df
                else:
                    result["answer_text"] = f"No loss-making items found in the current data{entity_note}."
            else:
                total_loss = float(work_df[work_df["_std_profit"] < 0]["_std_profit"].sum())
                result["answer_text"] = f"Total losses{entity_note}: **{format_inr(abs(total_loss))}**."
            return result
        result["answer_text"] = "I can't answer that from the current dataset because Profit is not available."
        result["is_unsupported"] = True
        return result

    year_match = re.search(r"\b(20\d{2})\b", q)
    month_match = next((m for m in MONTH_NAMES if m in q), None)
    if (year_match or month_match) and _has(work_df, "_std_order_date"):
        time_df = work_df.dropna(subset=["_std_order_date"]).copy()
        if year_match:
            time_df = time_df[time_df["_std_order_date"].dt.year == int(year_match.group(1))]
        if month_match:
            time_df = time_df[time_df["_std_order_date"].dt.month == MONTH_NAMES.index(month_match) + 1]
        if len(time_df) > 0:
            val = _metric_sum(time_df, metric_col, metric_label)
            period = f"{month_match.title() + ' ' if month_match else ''}{year_match.group(1) if year_match else ''}".strip()
            result["answer_text"] = (
                f"{metric_label} for **{period}**{entity_note}: **{format_inr(val)}** "
                f"({format_inr(val, compact=True)}) from {len(time_df):,} records."
            )
            result["context"]["last_metric"] = metric_label.lower()
            monthly = time_df.copy()
            monthly["_p"] = monthly["_std_order_date"].dt.strftime("%b %Y")
            magg = monthly.groupby("_p")[metric_col].agg("sum" if metric_label != "Orders" else "nunique").reset_index()
            magg.columns = ["Month", metric_label]
            result["chart_type"] = explicit_chart or ("line" if "trend" in q else "bar")
            result["chart_data"] = magg
            return result
        result["answer_text"] = f"No data found for the specified period. Available range: {_get_date_range(df)}."
        result["is_unsupported"] = True
        return result

    if any(w in q for w in ["top", "best", "highest", "largest", "biggest", "most"]) or \
       any(w in q for w in ["bottom", "worst", "lowest", "smallest", "least"]):
        ascending = any(w in q for w in ["bottom", "worst", "lowest", "smallest", "least"])
        group_col, group_label = _detect_dimension(q, work_df, prev_context)
        if group_col:
            agg = _group_metric(work_df, group_col, metric_col, metric_label, ascending)
            top_df = agg.head(top_n)
            word = "bottom" if ascending else "top"
            best = top_df.iloc[0]
            result["answer_text"] = (
                f"The {word} {group_label.lower()} by {metric_label.lower()}{entity_note} is "
                f"**{best[group_label]}** with **{format_inr(best[metric_label]) if metric_label != 'Orders' else f'{int(best[metric_label]):,}'}**."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = top_df
            result["context"]["last_dimension"] = group_label.lower()
            result["context"]["last_metric"] = metric_label.lower()
            return result

    if "growing" in q or "growth" in q or "fastest" in q:
        growth = _handle_growth(work_df, metric_col, metric_label, result, entity_note)
        if growth:
            return growth

    if "why" in q and "profit" in q:
        return _handle_why_profit(work_df, result, entity_note)

    if "what about" in q and prev_context:
        last_dim = prev_context.get("last_dimension")
        dim_map = _get_dim_map(work_df)
        if last_dim and last_dim in dim_map:
            group_col = dim_map[last_dim]
            group_label = last_dim.title()
            agg = _group_metric(work_df, group_col, metric_col, metric_label, False)
            best = agg.iloc[0]
            result["answer_text"] = (
                f"For {metric_label.lower()} by {group_label.lower()}{entity_note}: "
                f"**{best[group_label]}** leads with **{format_inr(best[metric_label])}**."
            )
            result["chart_type"] = "bar"
            result["chart_data"] = agg.head(10)
            result["context"]["last_dimension"] = group_label.lower()
            result["context"]["last_metric"] = metric_label.lower()
            return result

    if "which" in q or "what" in q or "who" in q or any(w in q for w in ["show", "display", "give", "list", "get"]):
        group_col, group_label = _detect_dimension(q, work_df, prev_context)
        if group_col:
            agg = _group_metric(work_df, group_col, metric_col, metric_label, False)
            best = agg.iloc[0]
            result["answer_text"] = (
                f"**{best[group_label]}** has the highest {metric_label.lower()}{entity_note} at "
                f"**{format_inr(best[metric_label])}** ({format_inr(best[metric_label], compact=True)})."
            )
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = agg.head(10)
            result["context"]["last_dimension"] = group_label.lower()
            result["context"]["last_metric"] = metric_label.lower()
            return result

    val = _metric_sum(work_df, metric_col, metric_label)
    result["answer_text"] = (
        f"Based on the active dataset{entity_note}, total {metric_label.lower()} is **{format_inr(val)}** "
        f"({format_inr(val, compact=True)}) across {len(work_df):,} records."
    )
    result["context"]["last_metric"] = metric_label.lower()
    return result


def _metric_sum(df, col, label):
    if label == "Orders" and col == "_std_order_id":
        return float(df[col].nunique())
    return round(float(df[col].dropna().sum()), 2)


def _group_metric(df, group_col, metric_col, metric_label, ascending=False):
    if metric_label == "Orders" and metric_col == "_std_order_id":
        agg = df.groupby(group_col)[metric_col].nunique().sort_values(ascending=ascending).reset_index()
    else:
        agg = df.groupby(group_col)[metric_col].sum().sort_values(ascending=ascending).reset_index()
    label = group_col.replace("_std_", "").replace("_", " ").title()
    if "Product Name" in label:
        label = "Product"
    agg.columns = [label, metric_label]
    return agg


def _handle_contribution(q, df, work_df, entity_note, metric_col, metric_label, explicit_chart, result):
    entities = _find_named_entities(q, df)
    total = _metric_sum(df, metric_col, metric_label)
    if entities:
        col, val = entities[0]
        subset = df[df[col].astype(str) == val]
        part = _metric_sum(subset, metric_col, metric_label)
        share = (part / total * 100) if total else 0
        result["answer_text"] = (
            f"**{val}** contributed **{format_inr(part)}** ({share:.1f}%) of total {metric_label.lower()}."
        )
        chart = pd.DataFrame({"Item": [val, "Other"], metric_label: [part, total - part]})
        result["chart_type"] = explicit_chart or "pie"
        result["chart_data"] = chart
        result["context"]["last_entity"] = val
        return result
    group_col, group_label = _detect_dimension(q, df, None)
    if not group_col:
        return None
    agg = _group_metric(df, group_col, metric_col, metric_label, False)
    agg["Share %"] = (agg[metric_label] / total * 100).round(1) if total else 0
    lines = [
        f"**{row[group_label]}**: {format_inr(row[metric_label], compact=True)} ({row['Share %']}%)"
        for _, row in agg.head(5).iterrows()
    ]
    result["answer_text"] = f"{metric_label} contribution by {group_label.lower()}:\n" + "\n".join(lines)
    result["chart_type"] = "pie"
    result["chart_data"] = agg.head(10)
    return result


def _handle_timeseries(q, df, metric_col, metric_label, explicit_chart, result, entity_note):
    if not _has(df, "_std_order_date"):
        result["answer_text"] = "I can't answer that from the current dataset because Order Date is not available."
        result["is_unsupported"] = True
        return result
    time_df = df.dropna(subset=["_std_order_date"]).copy()
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        time_df = time_df[time_df["_std_order_date"].dt.year == int(year_match.group(1))]
    if time_df.empty:
        result["answer_text"] = "No dated records match that request."
        result["is_unsupported"] = True
        return result
    freq = "M"
    if "week" in q:
        freq = "W"
    elif "day" in q or "daily" in q:
        freq = "D"
    elif "year" in q and "month" not in q:
        freq = "Y"
    time_df["_p"] = time_df["_std_order_date"].dt.to_period(freq).astype(str)
    if metric_label == "Orders":
        magg = time_df.groupby("_p")[metric_col].nunique().reset_index()
    else:
        magg = time_df.groupby("_p")[metric_col].sum().reset_index()
    magg.columns = ["Period", metric_label]
    tot_val = magg[metric_label].sum()
    if metric_label in ("Sales", "Profit"):
        tot_str = format_inr(tot_val)
        result["answer_text"] = f"Total {metric_label.lower()}{entity_note} across {len(magg)} periods: **{tot_str}**."
    else:
        result["answer_text"] = f"{metric_label} over time{entity_note} ({len(magg)} periods, total: {tot_val:,})."
    result["chart_type"] = explicit_chart or "line"
    result["chart_data"] = magg
    result["context"]["last_dimension"] = "period"
    result["context"]["last_metric"] = metric_label.lower()
    return result


def _handle_growth(df, metric_col, metric_label, result, entity_note):
    group_col, group_label = None, None
    if _has(df, "_std_category"):
        group_col, group_label = "_std_category", "Category"
    elif _has(df, "_std_region"):
        group_col, group_label = "_std_region", "Region"
    if not group_col or not _has(df, "_std_order_date"):
        return None
    vd = df.dropna(subset=["_std_order_date"])
    years = sorted(vd["_std_order_date"].dt.year.unique())
    if len(years) < 2:
        result["answer_text"] = "Growth comparison needs at least two years of dated records."
        result["is_unsupported"] = True
        return result
    y1, y2 = years[-2], years[-1]
    a = vd[vd["_std_order_date"].dt.year == y1].groupby(group_col)[metric_col].sum()
    b = vd[vd["_std_order_date"].dt.year == y2].groupby(group_col)[metric_col].sum()
    growth = ((b - a) / a.replace(0, pd.NA) * 100).dropna().sort_values(ascending=False)
    if growth.empty:
        return None
    best = growth.index[0]
    result["answer_text"] = (
        f"**{best}** is growing fastest by {metric_label.lower()}{entity_note}: "
        f"{growth.iloc[0]:.1f}% from {int(y1)} to {int(y2)}."
    )
    chart = growth.reset_index()
    chart.columns = [group_label, "Growth %"]
    result["chart_type"] = "bar"
    result["chart_data"] = chart
    result["context"]["last_dimension"] = group_label.lower()
    return result


def _handle_why_profit(df, result, entity_note):
    if not _has(df, "_std_profit") or not _has(df, "_std_order_date"):
        result["answer_text"] = "I can't explain profit movement because profit or dates are missing."
        result["is_unsupported"] = True
        return result
    vd = df.dropna(subset=["_std_order_date"])
    years = sorted(vd["_std_order_date"].dt.year.unique())
    parts = []
    if len(years) >= 2:
        y1, y2 = years[-2], years[-1]
        p1 = vd[vd["_std_order_date"].dt.year == y1]["_std_profit"].sum()
        p2 = vd[vd["_std_order_date"].dt.year == y2]["_std_profit"].sum()
        change = p2 - p1
        direction = "decreased" if change < 0 else "increased"
        parts.append(
            f"Profit {direction} from {format_inr(p1)} in {int(y1)} to {format_inr(p2)} in {int(y2)}."
        )
    if _has(df, "_std_sub_category"):
        g = df.groupby("_std_sub_category")["_std_profit"].sum().sort_values()
        if g.iloc[0] < 0:
            parts.append(f"{g.index[0]} is the largest loss area ({format_inr(abs(g.iloc[0]))}).")
        parts.append(f"{g.index[-1]} is the strongest profit contributor ({format_inr(g.iloc[-1])}).")
    result["answer_text"] = " ".join(parts) if parts else f"Profit{entity_note} totals {format_inr(df['_std_profit'].sum())}."
    return result


def _coverage_limitation(q: str, df: pd.DataFrame) -> Optional[str]:
    out_of_scope = [
        "attrition", "employee", "headcount", "payroll", "salary", "salaries", "hr",
        "human resource", "inventory", "stock level", "weather", "temperature",
        "ebitda", "balance sheet", "stock price", "marketing spend", "ad spend",
        "cpc", "churn rate", "retention rate", "nps",
    ]
    for term in out_of_scope:
        if re.search(r"\b" + re.escape(term) + r"\b", q):
            return (
                f"Coverage Limitation: **{term.title()}** is not tracked in this dataset. "
                "The active dataset covers sales transactions, revenue, profit, orders, "
                "customers, categories, and geographic delivery locations."
            )

    skip = {
        "the", "a", "an", "my", "this", "that", "total", "sales", "profit", "data", "dataset",
        "current", "active", "each", "all", "me", "us", "our", "order", "orders", "product",
        "products", "category", "region", "state", "city", "customer", "month", "year",
        "west", "east", "south", "north", "central",
    }
    skip.update(MONTH_NAMES)
    known = set()
    for col in [
        "_std_country", "_std_region", "_std_state", "_std_city",
        "_std_category", "_std_sub_category", "_std_segment",
    ]:
        if col in df.columns:
            known.update(str(v).strip().lower() for v in df[col].dropna().unique())

    candidates = []
    for m in re.finditer(r"\b(?:in|for|from|of)\s+([a-z][a-z0-9\s\-]+?)(?:\?|$|\.| vs | and |,)", q + "?"):
        token = re.sub(r"\b(the|region|category|state|city|product|segment|area)\b", "", m.group(1)).strip()
        if token and token not in skip and token not in MONTH_NAMES and not token.isdigit():
            candidates.append(token)

    for token in candidates:
        if any(token == k or re.search(r'\b' + re.escape(token) + r'\b', k) or re.search(r'\b' + re.escape(k) + r'\b', token) for k in known if len(k) >= 3):
            continue
        available = []
        if "_std_country" in df.columns:
            available.append("countries: " + ", ".join(sorted(str(v) for v in df["_std_country"].dropna().unique())[:8]))
        if "_std_region" in df.columns:
            available.append("regions: " + ", ".join(sorted(str(v) for v in df["_std_region"].dropna().unique())[:8]))
        if "_std_category" in df.columns:
            available.append("categories: " + ", ".join(sorted(str(v) for v in df["_std_category"].dropna().unique())[:8]))
        scope = "; ".join(available) if available else "the mapped fields in the active file"
        return (
            f"Coverage Limitation: **{token.title()}** is not present in the current dataset. "
            f"Available coverage — {scope}."
        )
    return None


def _is_total_query(q):
    return any(w in q for w in ["total", "overall", "sum", "aggregate", "how much"])


def _is_grouping_query(q):
    return any(w in q for w in ["by", "per", "each", "which", "top", "bottom", "best", "worst",
                                 "highest", "lowest", "compare", "vs", "show", "list", "contribut"])


def _get_dim_map(df):
    m = {}
    if _has(df, "_std_category"):
        m["category"] = "_std_category"
    if _has(df, "_std_sub_category"):
        m["sub-category"] = "_std_sub_category"
        m["subcategory"] = "_std_sub_category"
    if _has(df, "_std_product_name"):
        m["product"] = "_std_product_name"
    if _has(df, "_std_region"):
        m["region"] = "_std_region"
    if _has(df, "_std_state"):
        m["state"] = "_std_state"
    if _has(df, "_std_city"):
        m["city"] = "_std_city"
    if _has(df, "_std_segment"):
        m["segment"] = "_std_segment"
        m["customer segment"] = "_std_segment"
    if _has(df, "_std_customer_name"):
        m["customer"] = "_std_customer_name"
    if _has(df, "_std_ship_mode"):
        m["ship mode"] = "_std_ship_mode"
        m["shipping"] = "_std_ship_mode"
    if _has(df, "_std_payment_mode"):
        m["payment"] = "_std_payment_mode"
    return m


def _detect_dimension(q, df, prev_context=None):
    dim_map = _get_dim_map(df)
    for label, col in dim_map.items():
        if label in q:
            pretty = label.replace("_", " ").title()
            if pretty == "Product Name":
                pretty = "Product"
            return col, pretty
    if "who sold" in q or "who" in q:
        if _has(df, "_std_customer_name"):
            return "_std_customer_name", "Customer"
        if _has(df, "_std_product_name"):
            return "_std_product_name", "Product"
    if prev_context and prev_context.get("last_dimension"):
        last = prev_context["last_dimension"]
        if last in dim_map:
            return dim_map[last], last.title()
    if _has(df, "_std_category"):
        return "_std_category", "Category"
    if _has(df, "_std_region"):
        return "_std_region", "Region"
    if _has(df, "_std_product_name"):
        return "_std_product_name", "Product"
    return None, None


def _find_named_entities(q: str, df: pd.DataFrame) -> List[Tuple[str, str]]:
    found = []
    cols = [
        "_std_region", "_std_category", "_std_sub_category", "_std_segment",
        "_std_country", "_std_state", "_std_city", "_std_ship_mode",
    ]
    for col in cols:
        if col not in df.columns:
            continue
        for v in df[col].dropna().unique():
            vs = str(v).strip()
            if len(vs) >= 3 and vs.lower() in q:
                found.append((col, vs))
    found.sort(key=lambda x: len(x[1]), reverse=True)
    seen = set()
    unique = []
    for item in found:
        if item[1] not in seen:
            seen.add(item[1])
            unique.append(item)
    return unique[:2]


def _handle_comparison(q, df, metric_col, metric_label, explicit_chart, result, prev_context):
    dim_map = _get_dim_map(df)
    entities = _find_named_entities(q, df)
    entity_prefix = ""
    target_df = df
    if entities:
        col, val = entities[0]
        target_df = df[df[col].astype(str) == val]
        entity_prefix = f" for {val}"
        result["context"]["last_entity"] = val

    month_year = re.findall(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})",
        q,
    )
    if len(month_year) >= 2 and _has(target_df, "_std_order_date"):
        (m1, y1), (m2, y2) = month_year[0], month_year[1]
        n1, n2 = MONTH_NAMES.index(m1) + 1, MONTH_NAMES.index(m2) + 1
        vd = target_df.dropna(subset=["_std_order_date"])
        a = vd[(vd["_std_order_date"].dt.year == int(y1)) & (vd["_std_order_date"].dt.month == n1)]
        b = vd[(vd["_std_order_date"].dt.year == int(y2)) & (vd["_std_order_date"].dt.month == n2)]
        v1, v2 = _metric_sum(a, metric_col, metric_label), _metric_sum(b, metric_col, metric_label)
        change = ((v2 - v1) / v1 * 100) if v1 else 0
        p1 = f"{m1.title()} {y1}"
        p2 = f"{m2.title()} {y2}"
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        result["answer_text"] = (
            f"{metric_label}{entity_prefix}: **{p1}** {format_inr(v1)} vs **{p2}** {format_inr(v2)} "
            f"({arrow} {abs(change):.1f}%)."
        )
        result["chart_type"] = "bar"
        result["chart_data"] = pd.DataFrame({"Period": [p1, p2], metric_label: [v1, v2]})
        return result

    for dim_label, dim_col in dim_map.items():
        unique_vals = [str(v) for v in df[dim_col].dropna().unique()]
        found = [v for v in unique_vals if v.lower() in q]
        if len(found) >= 2:
            agg_map = {metric_col: ("nunique" if metric_label == "Orders" else "sum")}
            if metric_col != "_std_profit" and _has(df, "_std_profit"):
                agg_map["_std_profit"] = "sum"
            comp_df = df[df[dim_col].isin(found)].groupby(dim_col).agg(agg_map).reset_index()
            rename = {dim_col: dim_label.title(), metric_col: metric_label}
            if "_std_profit" in comp_df.columns and metric_col != "_std_profit":
                rename["_std_profit"] = "Profit"
            comp_df = comp_df.rename(columns=rename)
            vals = [f"**{row[dim_label.title()]}**: {format_inr(row[metric_label])}" for _, row in comp_df.iterrows()]
            result["answer_text"] = f"{metric_label} comparison:\n" + " vs ".join(vals)
            result["chart_type"] = explicit_chart or "bar"
            result["chart_data"] = comp_df
            result["context"]["last_dimension"] = dim_label
            result["context"]["last_metric"] = metric_label.lower()
            return result

    year_matches = re.findall(r"\b(20\d{2})\b", q)
    if len(year_matches) >= 2 and _has(target_df, "_std_order_date"):
        y1, y2 = int(year_matches[0]), int(year_matches[1])
        df_valid = target_df.dropna(subset=["_std_order_date"])
        v1 = _metric_sum(df_valid[df_valid["_std_order_date"].dt.year == y1], metric_col, metric_label)
        v2 = _metric_sum(df_valid[df_valid["_std_order_date"].dt.year == y2], metric_col, metric_label)
        change = ((v2 - v1) / v1 * 100) if v1 != 0 else 0
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        result["answer_text"] = (
            f"{metric_label} comparison{entity_prefix}: **{y1}**: {format_inr(v1)} vs **{y2}**: {format_inr(v2)} "
            f"({arrow} {abs(change):.1f}%)."
        )
        result["chart_type"] = "bar"
        result["chart_data"] = pd.DataFrame({"Year": [str(y1), str(y2)], metric_label: [v1, v2]})
        return result

    result["answer_text"] = "I couldn't identify two items to compare. Try: 'Compare West and East' or 'Compare January 2019 and January 2020'."
    result["is_unsupported"] = True
    return result
