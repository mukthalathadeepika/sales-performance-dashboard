"""
frontend/views/dashboard_view.py
Executive Sales Performance Dashboard.
Production implementation conforming to:
- Restored professional executive BI KPI cards in responsive .kpi-grid
- Horizontal Swipe/Carousel Information Introduction Cards
- Dataset-driven cascading filter system with prominent 'Apply Filters' and 'Reset All Filters'
- Filter status banner and zero-result filter safety
- Preserved all reference visualizations, currency formatting, insights, forecast, and exports.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io
from typing import Optional, Dict, Any, List

from backend.analytics.currency import format_inr, convert_series_to_inr, convert_to_inr
from backend.analytics.insights import generate_executive_insights
from backend.analytics.kpi import calculate_kpis
from backend.analytics.categories import get_category_breakdown
from backend.analytics.geography import get_state_breakdown
from backend.analytics.shipping import get_shipping_summary
from backend.exports.exporter import generate_executive_pdf, export_to_csv, export_to_excel
from backend.forecasting.forecast import forecast_sales
from frontend.components.charts import PLOTLY_CONFIG
from frontend.components.chart_utils import render_plotly
from frontend.components.map import render_geo_map


def _png(fig):
    try:
        return fig.to_image(format="png")
    except Exception:
        return None


# Curated visual palette using the two complementary blues
PALETTE = ["#2563EB", "#38BDF8", "#10B981", "#F59E0B", "#8B5CF6", "#EF4444", "#14B8A6", "#60A5FA"]
BG = "#121D38"
TXT = "#F1F5F9"
MUTED = "#94A3B8"
GRID = "rgba(59, 130, 246, 0.08)"

COLOR_PRESETS = {
    "Executive Blue": ("#2563EB", "#38BDF8"),
    "Cyan & Green": ("#00D4FF", "#22C55E"),
    "Teal & Ice": ("#14B8A6", "#7DD3FC"),
    "Purple & Sky": ("#818CF8", "#38BDF8"),
    "Amber & Emerald": ("#F59E0B", "#10B981"),
    "Custom": ("#2563EB", "#38BDF8"),
}


def _dl(fig, title="", h=360):
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.96, font=dict(size=13, color=TXT, family="Inter, sans-serif")),
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=h,
        margin=dict(l=12, r=12, t=48, b=28),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right", font=dict(size=11, color=MUTED)),
        hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_color=TXT),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, tickfont=dict(size=10, color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, tickfont=dict(size=10, color=MUTED))
    return fig


def _h(df, c):
    return c in df.columns if df is not None else False


def _inr_col(s):
    return convert_series_to_inr(s)


def _render_swipe_introduction():
    """Renders 3 compact horizontal swipe/carousel introduction cards."""
    st.markdown(
        """
        <div class="swipe-carousel-wrapper">
            <div class="swipe-cards-container">
                <div class="swipe-card">
                    <div class="swipe-card-top">
                        <div class="swipe-card-icon">💼</div>
                        <div class="swipe-step-pill">1 of 3 · <span class="dots">● ○ ○</span></div>
                    </div>
                    <div class="swipe-card-title">Understand Your Business</div>
                    <div class="swipe-card-desc">Analyze sales, profitability, orders, customers, products and overall business performance from your dataset.</div>
                    <div class="swipe-card-tags">
                        <span class="swipe-tag">Sales & Profit</span>
                        <span class="swipe-tag">Volume & Margin</span>
                        <span class="swipe-tag">Customer Segments</span>
                    </div>
                </div>
                <div class="swipe-card">
                    <div class="swipe-card-top">
                        <div class="swipe-card-icon">🔍</div>
                        <div class="swipe-step-pill">2 of 3 · <span class="dots">○ ● ○</span></div>
                    </div>
                    <div class="swipe-card-title">Explore & Compare</div>
                    <div class="swipe-card-desc">Track sales and profit, analyze products and categories, compare regions and locations, study shipping/fulfillment, apply cascading filters, and compare time periods (YoY, QoQ, MoM).</div>
                    <div class="swipe-card-tags">
                        <span class="swipe-tag">Period Comparison</span>
                        <span class="swipe-tag">Regional Maps</span>
                        <span class="swipe-tag">Fulfillment Analytics</span>
                    </div>
                </div>
                <div class="swipe-card">
                    <div class="swipe-card-top">
                        <div class="swipe-card-icon">⚡</div>
                        <div class="swipe-step-pill">3 of 3 · <span class="dots">○ ○ ●</span></div>
                    </div>
                    <div class="swipe-card-title">Ask, Analyze & Export</div>
                    <div class="swipe-card-desc">Ask questions using the AI Sales Assistant, build custom analyses, generate charts, export CSV/Excel results, generate executive PDF reports, and upload your own supported datasets.</div>
                    <div class="swipe-card-tags">
                        <span class="swipe-tag">AI Assistant</span>
                        <span class="swipe-tag">Custom Charts</span>
                        <span class="swipe-tag">PDF / Excel Export</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_cards(df, period_changes):
    """
    Renders the 6 required executive BI KPI cards in a responsive grid.
    Conforms strictly to Section 2:
    1. Total Sales
    2. Total Profit
    3. Total Orders
    4. Total Quantity
    5. Profit Margin %
    6. Average Order Value
    """
    hs = _h(df, "_std_sales")
    hp = _h(df, "_std_profit")
    ho = _h(df, "_std_order_id")
    hq = _h(df, "_std_quantity")

    ts = float(df["_std_sales"].sum()) if hs else 0.0
    tp = float(df["_std_profit"].sum()) if hp else 0.0
    to = int(df["_std_order_id"].nunique()) if ho else len(df)
    tq = int(df["_std_quantity"].sum()) if hq else len(df)
    margin = (tp / ts * 100) if ts > 0 and hp else None
    aov = ts / to if to > 0 and hs else None

    kpis = [
        {
            "title": "Total Sales",
            "icon": "💰",
            "value": format_inr(ts, compact=True) if hs else "—",
            "change_key": "Total Sales",
            "subtitle": "Gross revenue",
            "color_cls": "",
            "accent": "#2563EB",
        },
        {
            "title": "Total Profit",
            "icon": "📈",
            "value": format_inr(tp, compact=True) if hp else "—",
            "change_key": "Total Profit",
            "subtitle": f"{margin:.1f}% net margin" if margin is not None else "Net earnings",
            "color_cls": "green",
            "accent": "#10B981",
        },
        {
            "title": "Total Orders",
            "icon": "📦",
            "value": f"{to:,}",
            "change_key": "Total Orders",
            "subtitle": "Distinct orders" if ho else "Line items",
            "color_cls": "teal",
            "accent": "#0EA5E9",
        },
        {
            "title": "Total Quantity",
            "icon": "🏷️",
            "value": f"{tq:,}" if hq else f"{len(df):,}",
            "change_key": "Units Sold",
            "subtitle": "Units shipped" if hq else "Total records",
            "color_cls": "purple",
            "accent": "#818CF8",
        },
        {
            "title": "Profit Margin",
            "icon": "🎯",
            "value": f"{margin:.1f}%" if margin is not None else "—",
            "change_key": "Profit Margin",
            "subtitle": "Net profit / sales",
            "color_cls": "orange",
            "accent": "#F59E0B",
        },
        {
            "title": "Average Order Value",
            "icon": "💳",
            "value": format_inr(aov, compact=True) if aov is not None else "—",
            "change_key": "Average Order Value",
            "subtitle": f"{to:,} transactions",
            "color_cls": "cyan",
            "accent": "#38BDF8",
        },
    ]

    st.markdown(
        """
        <style>
        .kpi-card {
            background: #121D38;
            border: 1px solid rgba(59, 130, 246, 0.22);
            border-radius: 10px;
            padding: 1.05rem 1.15rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.32);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 136px;
            position: relative;
            overflow: hidden;
            box-sizing: border-box;
            width: 100%;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
            border-color: rgba(59, 130, 246, 0.45);
        }
        .kpi-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.45rem;
        }
        .kpi-title {
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #94A3B8;
        }
        .kpi-icon {
            font-size: 1.05rem;
            opacity: 0.9;
        }
        .kpi-value {
            font-size: 1.55rem;
            font-weight: 800;
            color: #F8FAFC;
            letter-spacing: -0.025em;
            line-height: 1.15;
            margin-bottom: 0.45rem;
        }
        .kpi-footer {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-top: auto;
            padding-top: 4px;
        }
        .kpi-pill {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 7px;
            border-radius: 5px;
            font-weight: 600;
            font-size: 0.69rem;
            width: fit-content;
        }
        .kpi-pill.positive {
            background: rgba(34, 197, 94, 0.14);
            color: #34D399;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .kpi-pill.negative {
            background: rgba(239, 68, 68, 0.14);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .kpi-pill.neutral {
            background: rgba(37, 99, 235, 0.15);
            color: #60A5FA;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
        .kpi-subtitle {
            font-size: 0.72rem;
            color: #94A3B8;
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.3;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
    cols = [c1, c2, c3, c4, c5, c6]

    for col, k in zip(cols, kpis):
        change = period_changes.get(k["change_key"])
        if change is not None:
            arrow = "↑" if change >= 0 else "↓"
            c_cls = "positive" if change >= 0 else "negative"
            pill_text = f"{arrow} {abs(change):.1f}% vs prev period"
            pill_style = (
                "background: rgba(34, 197, 94, 0.14); color: #34D399; border: 1px solid rgba(34, 197, 94, 0.3);"
                if change >= 0
                else "background: rgba(239, 68, 68, 0.14); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3);"
            )
        else:
            c_cls = "neutral"
            pill_text = "• Active scope"
            pill_style = "background: rgba(37, 99, 235, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3);"

        pill_html = (
            f'<span class="kpi-pill {c_cls}" '
            f'style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; border-radius: 5px; '
            f'font-weight: 600; font-size: 0.69rem; width: fit-content; {pill_style}">'
            f'{pill_text}</span>'
        )

        card = (
            f'<div class="kpi-card {k["color_cls"]}" '
            f'style="background: #121D38; border: 1px solid rgba(59, 130, 246, 0.22); '
            f'border-top: 3px solid {k["accent"]}; border-radius: 10px; padding: 1.05rem 1.15rem; '
            f'min-height: 136px; display: flex; flex-direction: column; justify-content: space-between; '
            f'box-shadow: 0 4px 20px rgba(0,0,0,0.32); position: relative; overflow: hidden; '
            f'box-sizing: border-box; width: 100%;">'
            f'<div class="kpi-card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">'
            f'<span class="kpi-title" style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8;">{k["title"]}</span>'
            f'<span class="kpi-icon" style="font-size: 1.05rem; opacity: 0.9;">{k["icon"]}</span>'
            f'</div>'
            f'<div class="kpi-value" style="font-size: 1.55rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.025em; line-height: 1.15; margin-bottom: 0.45rem;">{k["value"]}</div>'
            f'<div class="kpi-footer" style="display: flex; flex-direction: column; gap: 4px; margin-top: auto; padding-top: 4px;">'
            f'<div style="display: flex; align-items: center;">{pill_html}</div>'
            f'<div class="kpi-subtitle" style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.3;" title="{k["subtitle"]}">{k["subtitle"]}</div>'
            f'</div>'
            f'</div>'
        )
        with col:
            st.markdown(card, unsafe_allow_html=True)


def _render_filter_controls(clean_df):
    """
    Renders dataset-driven cascading filter controls and action buttons.
    Conforms to Sections 3, 4, 5, 6, 11:
    - Inspects ONLY columns present in clean_df.
    - Implements cascading options.
    - Prominent 'Apply Filters' and 'Reset All Filters' buttons.
    - Filter status indicator.
    """
    if clean_df is None or len(clean_df) == 0:
        return

    active_filters = st.session_state.get("active_filters", {})
    has_active = bool(active_filters)

    with st.expander("🔍 Filter Controls & Dimensions", expanded=has_active):
        # 1. Date Filters (only if _std_order_date exists)
        if _h(clean_df, "_std_order_date"):
            vd = clean_df["_std_order_date"].dropna()
            if len(vd) > 0:
                min_d = vd.min().date()
                max_d = vd.max().date()
                dc1, dc2, dc3, dc4 = st.columns(4)
                with dc1:
                    cur_dr = active_filters.get("date_range", (min_d, max_d))
                    st.date_input(
                        "Date Range",
                        value=cur_dr,
                        min_value=min_d,
                        max_value=max_d,
                        key="flt_date_range",
                    )
                with dc2:
                    years = sorted(int(y) for y in vd.dt.year.unique())
                    st.multiselect("Year", years, default=active_filters.get("years", []), key="flt_years")
                with dc3:
                    st.multiselect("Quarter", ["Q1", "Q2", "Q3", "Q4"], default=active_filters.get("quarters", []), key="flt_quarters")
                with dc4:
                    months = list(vd.dt.month_name().unique())
                    st.multiselect("Month", months, default=active_filters.get("months", []), key="flt_months")

        # 2. Cascading Geographic Filters
        geo_cols_exist = any(_h(clean_df, c) for c in ["_std_region", "_std_state", "_std_city", "_std_country"])
        if geo_cols_exist:
            g1, g2, g3 = st.columns(3)
            # Region
            with g1:
                if _h(clean_df, "_std_region"):
                    reg_opts = sorted(str(r) for r in clean_df["_std_region"].dropna().unique())
                    sel_regions = st.multiselect("Region", reg_opts, default=active_filters.get("regions", []), key="flt_regions")
                else:
                    sel_regions = []

            # State (cascaded from Region)
            with g2:
                if _h(clean_df, "_std_state"):
                    st_pool = clean_df[clean_df["_std_region"].isin(sel_regions)] if sel_regions else clean_df
                    state_opts = sorted(str(s) for s in st_pool["_std_state"].dropna().unique())
                    default_states = [s for s in active_filters.get("states", []) if s in state_opts]
                    sel_states = st.multiselect("State", state_opts, default=default_states, key="flt_states")
                else:
                    sel_states = []

            # City (cascaded from State / Region)
            with g3:
                if _h(clean_df, "_std_city"):
                    city_base = st_pool if "_std_state" in clean_df.columns else clean_df
                    c_pool = city_base[city_base["_std_state"].isin(sel_states)] if sel_states else city_base
                    city_opts = sorted(str(c) for c in c_pool["_std_city"].dropna().unique())
                    default_cities = [c for c in active_filters.get("cities", []) if c in city_opts]
                    st.multiselect("City", city_opts, default=default_cities, key="flt_cities")

        # 3. Cascading Product Filters
        prod_cols_exist = any(_h(clean_df, c) for c in ["_std_category", "_std_sub_category", "_std_product_name"])
        if prod_cols_exist:
            p1, p2, p3 = st.columns(3)
            # Category
            with p1:
                if _h(clean_df, "_std_category"):
                    cat_opts = sorted(str(c) for c in clean_df["_std_category"].dropna().unique())
                    sel_cats = st.multiselect("Category", cat_opts, default=active_filters.get("categories", []), key="flt_cats")
                else:
                    sel_cats = []

            # Sub-Category (cascaded from Category)
            with p2:
                if _h(clean_df, "_std_sub_category"):
                    cat_pool = clean_df[clean_df["_std_category"].isin(sel_cats)] if sel_cats else clean_df
                    subcat_opts = sorted(str(sc) for sc in cat_pool["_std_sub_category"].dropna().unique())
                    default_subcats = [sc for sc in active_filters.get("subcats", []) if sc in subcat_opts]
                    sel_subcats = st.multiselect("Sub-Category", subcat_opts, default=default_subcats, key="flt_subcats")
                else:
                    sel_subcats = []

            # Product (cascaded from Sub-Category)
            with p3:
                if _h(clean_df, "_std_product_name"):
                    sub_pool = cat_pool if "_std_sub_category" in clean_df.columns else clean_df
                    prod_pool = sub_pool[sub_pool["_std_sub_category"].isin(sel_subcats)] if sel_subcats else sub_pool
                    prod_opts = sorted(str(p) for p in prod_pool["_std_product_name"].dropna().unique())
                    default_prods = [p for p in active_filters.get("products", []) if p in prod_opts]
                    st.multiselect("Product", prod_opts[:400], default=default_prods, key="flt_products")

        # 4. Customer, Segment, Ship Mode (only if present in dataset!)
        other_cols = [c for c in ["_std_segment", "_std_ship_mode", "_std_customer_name"] if _h(clean_df, c)]
        if other_cols:
            oc_cols = st.columns(len(other_cols))
            for i, col in enumerate(other_cols):
                with oc_cols[i]:
                    if col == "_std_segment":
                        seg_opts = sorted(str(s) for s in clean_df["_std_segment"].dropna().unique())
                        st.multiselect("Segment", seg_opts, default=active_filters.get("segments", []), key="flt_segs")
                    elif col == "_std_ship_mode":
                        sm_opts = sorted(str(sm) for sm in clean_df["_std_ship_mode"].dropna().unique())
                        st.multiselect("Ship Mode", sm_opts, default=active_filters.get("shipmodes", []), key="flt_shipmodes")
                    elif col == "_std_customer_name":
                        cust_opts = sorted(str(cn) for cn in clean_df["_std_customer_name"].dropna().unique())[:400]
                        st.multiselect("Customer", cust_opts, default=active_filters.get("customers", []), key="flt_customers")

        # 5. Filter Action Buttons
        b_c1, b_c2, b_space = st.columns([1.3, 1.3, 4])
        with b_c1:
            if st.button("⚡ Apply Filters", type="primary", use_container_width=True, key="dash_apply_filters"):
                new_filters = {}
                # Capture Date
                dr = st.session_state.get("flt_date_range")
                if isinstance(dr, (tuple, list)) and len(dr) == 2:
                    min_vd = clean_df["_std_order_date"].dropna().min().date() if _h(clean_df, "_std_order_date") else None
                    max_vd = clean_df["_std_order_date"].dropna().max().date() if _h(clean_df, "_std_order_date") else None
                    if min_vd and max_vd and (dr[0] != min_vd or dr[1] != max_vd):
                        new_filters["date_range"] = dr
                for k, fk in [("flt_years", "years"), ("flt_quarters", "quarters"), ("flt_months", "months"),
                              ("flt_regions", "regions"), ("flt_states", "states"), ("flt_cities", "cities"),
                              ("flt_cats", "categories"), ("flt_subcats", "subcats"), ("flt_products", "products"),
                              ("flt_segs", "segments"), ("flt_shipmodes", "shipmodes"), ("flt_customers", "customers")]:
                    v = st.session_state.get(k)
                    if v:
                        new_filters[fk] = v
                st.session_state["active_filters"] = new_filters
                st.rerun()

        with b_c2:
            if st.button("🔄 Reset All Filters", use_container_width=True, key="dash_reset_filters"):
                st.session_state["active_filters"] = {}
                for k in list(st.session_state.keys()):
                    if k.startswith("flt_"):
                        del st.session_state[k]
                st.rerun()

    # Filter Status Banner
    active_count = len(active_filters)
    clean_count = len(clean_df)
    filtered_df = st.session_state.get("filtered_df", clean_df)
    filtered_count = len(filtered_df) if filtered_df is not None else 0

    if active_count > 0:
        st.markdown(
            f'<div class="filter-status-banner active">'
            f'<span class="filter-status-badge"><span class="dot"></span>Showing filtered results</span>'
            f'<span><b>{active_count}</b> filter{"s" if active_count != 1 else ""} active · <b>{filtered_count:,}</b> of <b>{clean_count:,}</b> records</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="filter-status-banner">'
            f'<span class="filter-status-badge"><span class="dot" style="background:#64748B;"></span>Showing all data</span>'
            f'<span><b>{clean_count:,}</b> records</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_zero_results(clean_df):
    """Zero-result safety card when filters return no data."""
    st.markdown(
        '<div class="zero-results-card">'
        '<div class="zero-results-icon">🔍</div>'
        '<div class="zero-results-title">No Data Matches the Selected Filters</div>'
        '<div class="zero-results-desc">'
        'Your active filter criteria returned 0 matching records from the active dataset.<br>'
        'Try selecting different dimensions or click below to restore the complete dataset.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Reset All Filters", key="btn_zero_reset", type="primary", use_container_width=True):
            st.session_state["active_filters"] = {}
            for k in list(st.session_state.keys()):
                if k.startswith("flt_"):
                    del st.session_state[k]
            st.rerun()


def render_dashboard_view(df=None, dataset_name="", clean_df=None):
    """
    Main Executive Dashboard View.
    df: Currently filtered DataFrame slice.
    clean_df: Complete active dataset (used for filter option calculation).
    """
    if clean_df is None:
        clean_df = st.session_state.get("clean_df", df)

    rows = f"{len(df):,}" if df is not None else "0"
    date_str = ""
    if clean_df is not None and _h(clean_df, "_std_order_date"):
        vd = clean_df["_std_order_date"].dropna()
        if len(vd) > 0:
            date_str = f"{vd.min().strftime('%b %d, %Y')} – {vd.max().strftime('%b %d, %Y')}"

    # 1. Dashboard Header & Dataset Information
    st.markdown(
        f"""
    <div class="dash-header">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
            <div>
                <h1 class="dash-title">Sales Performance Dashboard</h1>
                <div class="dash-subtitle">Monitor sales, profitability and business performance across your active dataset.</div>
            </div>
            <span class="dash-badge"><span class="dash-badge-dot"></span>
                Active Dataset: {dataset_name or '—'} · Rows: {rows}{' · ' + date_str if date_str else ''}
            </span>
        </div>
    </div>""",
        unsafe_allow_html=True,
    )

    # 2. Swipe Introduction Cards (Section 7)
    _render_swipe_introduction()

    # Empty State Check if dataset is missing
    if df is None:
        st.markdown(
            """<div class="empty-state"><div class="empty-state-icon">📊</div>
            <div class="empty-state-title">No Data Available</div>
            <div class="empty-state-desc">Upload a dataset or adjust filters to see the dashboard.</div></div>""",
            unsafe_allow_html=True,
        )
        return

    # 3. Compact Period Comparison Mode Selector
    cmp_mode = st.selectbox(
        "KPI Comparison Mode",
        ["Previous period", "Month-over-month", "Quarter-over-quarter", "Year-over-year"],
        key="dash_cmp_mode",
    )
    period_changes = _calc_period_comparison(df, cmp_mode)

    # 4. Restored Professional Executive BI KPI Cards (Section 2)
    _render_kpi_cards(df, period_changes)

    # 5, 6, 7. Dataset-Driven Cascading Filters & Filter Status Banner (Section 3, 4, 5, 6, 11)
    _render_filter_controls(clean_df)

    # 13. Zero-Result Filter Safety check (Section 13)
    if len(df) == 0:
        _render_zero_results(clean_df)
        return

    # Controls & Variables for Visualizations
    hs = _h(df, "_std_sales")
    hp = _h(df, "_std_profit")
    hq = _h(df, "_std_quantity")
    ts = float(df["_std_sales"].sum()) if hs else 0.0
    tp = float(df["_std_profit"].sum()) if hp else 0.0
    margin = (tp / ts * 100) if ts > 0 and hp else None

    # Chart Customization Expander
    with st.expander("🎨 Chart Customization", expanded=False):
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            preset = st.selectbox("Palette", list(COLOR_PRESETS.keys()), key="dash_color_preset")
        with cc2:
            granularity = st.selectbox("Date granularity", ["Year", "Quarter", "Month", "Week", "Day"], index=2, key="dash_granularity")
        with cc3:
            trend_type = st.selectbox("Trend chart type", ["Combo", "Line", "Bar"], index=0, key="dash_trend_type")
        with cc4:
            show_markers = st.checkbox("Markers", value=True, key="dash_markers")
            show_labels = st.checkbox("Data labels", value=False, key="dash_labels")
        if preset == "Custom":
            csa, cpr = st.columns(2)
            with csa:
                sales_color = st.color_picker("Sales color", COLOR_PRESETS["Executive Blue"][0], key="dash_sales_color")
            with cpr:
                profit_color = st.color_picker("Profit color", COLOR_PRESETS["Executive Blue"][1], key="dash_profit_color")
        else:
            sales_color, profit_color = COLOR_PRESETS[preset]

    gran_map = {"Year": "Y", "Quarter": "Q", "Month": "M", "Week": "W", "Day": "D"}
    gran = st.session_state.get("dash_granularity", "Month")

    # Breadcrumb drill-down navigation
    drill = st.session_state.get("drill_path") or []
    if drill:
        crumbs = " › ".join(f"{d['level']}: {d['value']}" for d in drill)
        b1, b2 = st.columns([1, 6])
        with b1:
            if st.button("← Back", key="dash_drill_back"):
                st.session_state["drill_path"] = drill[:-1]
                st.rerun()
        with b2:
            st.caption(f"Drill-down: {crumbs}")

    # 8. Main Charts Grid: Monthly Sales & Profit Trend and Category Performance
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        if _h(df, "_std_order_date") and hs:
            tdf = df.dropna(subset=["_std_order_date"]).copy()
            tdf["_p"] = tdf["_std_order_date"].dt.to_period(gran_map.get(gran, "M")).astype(str)
            agg_cols = {"_std_sales": "sum"}
            if hp:
                agg_cols["_std_profit"] = "sum"
            tagg = tdf.groupby("_p", as_index=False).agg(agg_cols).sort_values("_p")
            tagg["_std_sales"] = _inr_col(tagg["_std_sales"])
            if hp:
                tagg["_std_profit"] = _inr_col(tagg["_std_profit"])
                tagg["_margin"] = np.where(tagg["_std_sales"] != 0, tagg["_std_profit"] / tagg["_std_sales"] * 100, 0)

            fig = go.Figure()
            mode = "lines+markers" if show_markers else "lines"
            hover_sales = "Date: %{x}<br>Sales: ₹%{y:,.0f}"
            if hp:
                hover_sales += "<br>Profit: ₹%{customdata[0]:,.0f}<br>Margin: %{customdata[1]:.1f}%"
            hover_sales += "<extra></extra>"
            custom = list(zip(tagg["_std_profit"], tagg["_margin"])) if hp else None

            if trend_type == "Bar":
                fig.add_trace(go.Bar(
                    x=tagg["_p"], y=tagg["_std_sales"], name="Sales",
                    marker_color=sales_color, customdata=custom,
                    hovertemplate=hover_sales,
                ))
                if hp:
                    fig.add_trace(go.Bar(
                        x=tagg["_p"], y=tagg["_std_profit"], name="Profit",
                        marker_color=profit_color,
                        hovertemplate="Profit: ₹%{y:,.0f}<extra></extra>",
                    ))
            elif trend_type == "Combo":
                fig.add_trace(go.Bar(
                    x=tagg["_p"], y=tagg["_std_sales"], name="Sales",
                    marker_color=sales_color, opacity=0.85, customdata=custom,
                    hovertemplate=hover_sales,
                ))
                if hp:
                    fig.add_trace(go.Scatter(
                        x=tagg["_p"], y=tagg["_std_profit"], name="Profit",
                        mode=mode, line=dict(color=profit_color, width=2.5),
                        hovertemplate="Profit: ₹%{y:,.0f}<extra></extra>",
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=tagg["_p"], y=tagg["_std_sales"], name="Sales",
                    mode=mode, line=dict(color=sales_color, width=2.5),
                    fill="tozeroy", customdata=custom,
                    text=[format_inr(v, compact=True, convert=False) for v in tagg["_std_sales"]] if show_labels else None,
                    textposition="top center",
                    hovertemplate=hover_sales,
                ))
                if hp:
                    fig.add_trace(go.Scatter(
                        x=tagg["_p"], y=tagg["_std_profit"], name="Profit",
                        mode=mode, line=dict(color=profit_color, width=2.5),
                        hovertemplate="Profit: ₹%{y:,.0f}<extra></extra>",
                    ))
            _dl(fig, f"{gran}ly Sales & Profit Trend")
            if trend_type == "Bar":
                fig.update_layout(barmode="group")
            render_plotly(fig, key="monthly_sales_profit_chart")
            png_bytes = _png(fig)
            if png_bytes:
                st.download_button("Download Trend PNG", png_bytes, "trend_chart.png", "image/png", key="dash_dl_trend_png")

    with r1c2:
        if _h(df, "_std_category") and hs:
            agg_dict = {"_std_sales": "sum"}
            if hp:
                agg_dict["_std_profit"] = "sum"
            if hq:
                agg_dict["_std_quantity"] = "sum"
            cagg = df.groupby("_std_category", as_index=False).agg(agg_dict).sort_values("_std_sales", ascending=True)
            cagg["_std_sales"] = _inr_col(cagg["_std_sales"])
            if hp:
                cagg["_std_profit"] = _inr_col(cagg["_std_profit"])

            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(
                y=cagg["_std_category"], x=cagg["_std_sales"], name="Sales",
                orientation="h", marker_color=PALETTE[1],
                hovertemplate="Sales: ₹%{x:,.0f}<extra></extra>",
            ))
            if hp:
                fig_c.add_trace(go.Bar(
                    y=cagg["_std_category"], x=cagg["_std_profit"], name="Profit",
                    orientation="h", marker_color=PALETTE[2],
                    hovertemplate="Profit: ₹%{x:,.0f}<extra></extra>",
                ))
            if hq:
                fig_c.add_trace(go.Bar(
                    y=cagg["_std_category"], x=cagg["_std_quantity"], name="Quantity",
                    orientation="h", marker_color=PALETTE[3], visible="legendonly",
                    hovertemplate="Qty: %{x:,}<extra></extra>",
                ))
            _dl(fig_c, "Category Performance (Sales, Profit, Quantity)")
            fig_c.update_layout(barmode="group")
            render_plotly(fig_c, key="category_sales_profit_chart", click_filter_key="flt_cats")

    # 9. Sub-Category and Regional Breakdowns
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        if _h(df, "_std_sub_category") and hp:
            sub = df.groupby("_std_sub_category")["_std_profit"].sum().reset_index()
            sub["_std_profit"] = _inr_col(sub["_std_profit"])
            sub = sub.sort_values("_std_profit", ascending=True)
            colors = ["#10B981" if v >= 0 else "#EF4444" for v in sub["_std_profit"]]
            fig_sub = go.Figure(go.Bar(
                y=sub["_std_sub_category"], x=sub["_std_profit"], orientation="h",
                marker_color=colors, hovertemplate="Profit: ₹%{x:,.0f}<extra></extra>",
            ))
            _dl(fig_sub, "Profit by Sub-Category (Profits vs Losses)", 400)
            render_plotly(fig_sub, key="subcategory_profit_chart", click_filter_key="flt_subcats")

    with r2c2:
        if _h(df, "_std_region") and hs:
            agg_r = {"_std_sales": "sum"}
            if hp:
                agg_r["_std_profit"] = "sum"
            r_df = df.groupby("_std_region", as_index=False).agg(agg_r).sort_values("_std_sales", ascending=False)
            r_df["_std_sales"] = _inr_col(r_df["_std_sales"])
            if hp:
                r_df["_std_profit"] = _inr_col(r_df["_std_profit"])

            fig_r = go.Figure()
            fig_r.add_trace(go.Bar(
                x=r_df["_std_region"], y=r_df["_std_sales"], name="Sales",
                marker_color=PALETTE[0], hovertemplate="Sales: ₹%{y:,.0f}<extra></extra>",
            ))
            if hp:
                fig_r.add_trace(go.Bar(
                    x=r_df["_std_region"], y=r_df["_std_profit"], name="Profit",
                    marker_color=PALETTE[2], hovertemplate="Profit: ₹%{y:,.0f}<extra></extra>",
                ))
            _dl(fig_r, "Sales & Profit by Region")
            fig_r.update_layout(barmode="group")
            render_plotly(fig_r, key="regional_margins_chart", click_filter_key="flt_regions")

    # 10. Product & Segment Rankings
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        if _h(df, "_std_product_name") and (hs or hp):
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                pm = st.selectbox("Rank metric", [m for m, ok in [("Sales", hs), ("Profit", hp), ("Quantity", hq)] if ok], key="dash_prod_metric")
            with c_p2:
                p_rank = st.selectbox("Rank filter", ["Top 5", "Top 10", "Bottom 5"], key="dash_prod_rank")
            col_target = {"Sales": "_std_sales", "Profit": "_std_profit", "Quantity": "_std_quantity"}[pm]
            p_agg = df.groupby("_std_product_name")[col_target].sum().reset_index()
            if pm in ("Sales", "Profit"):
                p_agg[col_target] = _inr_col(p_agg[col_target])
            asc = p_rank.startswith("Bottom")
            n = 5 if "5" in p_rank else 10
            p_agg = p_agg.sort_values(col_target, ascending=asc).head(n)
            fig = go.Figure(go.Bar(
                y=p_agg["_std_product_name"], x=p_agg[col_target], orientation="h",
                marker_color=PALETTE[0] if not asc else "#EF4444",
                hovertemplate="%{y}: " + ("₹%{x:,.0f}" if pm in ("Sales", "Profit") else "%{x:,.0f}") + "<extra></extra>",
            ))
            _dl(fig, f"{p_rank} Products by {pm}")
            fig.update_layout(showlegend=False)
            render_plotly(fig, key="top_products_chart")

    with r3c2:
        if _h(df, "_std_segment") and hs:
            seg = df.groupby("_std_segment")["_std_sales"].sum().reset_index()
            seg["_std_sales"] = _inr_col(seg["_std_sales"])
            fig = go.Figure(go.Pie(
                labels=seg["_std_segment"], values=seg["_std_sales"], hole=0.6,
                marker=dict(colors=PALETTE[: len(seg)], line=dict(color=BG, width=2)),
                textinfo="label+percent", textfont=dict(size=11, color=TXT),
                hovertemplate="%{label}: ₹%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            _dl(fig, "Customer Segment Distribution")
            render_plotly(fig, key="segment_donut_chart", click_filter_key="flt_segs")

    # 11. Geographic Performance
    st.markdown("### Geographic Performance")
    if _h(df, "_std_state") or _h(df, "_std_country") or _h(df, "_std_city") or _h(df, "_std_region"):
        g_c1, g_c2 = st.columns(2)
        with g_c1:
            geo_opts = [l for l in ["US State Choropleth", "Region Breakdown", "City Breakdown"]
                        if (l.startswith("US") and _h(df, "_std_state")) or
                           (l.startswith("Region") and _h(df, "_std_region")) or
                           (l.startswith("City") and _h(df, "_std_city"))]
            metric_opts = [m for m, ok in [("Sales", hs), ("Profit", hp), ("Orders", True)] if ok]
            metric_col = st.selectbox("Metric", metric_opts, key="dash_geo_met")
            render_geo_map(df, metric=metric_col, key="dash_geo_map")

        with g_c2:
            if _h(df, "_std_city") and hs:
                top_cities = df.groupby("_std_city")["_std_sales"].sum().reset_index().sort_values("_std_sales", ascending=True).tail(10)
                top_cities["_std_sales"] = _inr_col(top_cities["_std_sales"])
                fig_city = go.Figure(go.Bar(
                    y=top_cities["_std_city"], x=top_cities["_std_sales"], orientation="h",
                    marker_color=PALETTE[1], hovertemplate="Sales: ₹%{x:,.0f}<extra></extra>",
                ))
                _dl(fig_city, "Top 10 Cities by Sales", 420)
                render_plotly(fig_city, key="top_cities_chart")

    # 12. Shipping & Fulfillment
    if _h(df, "_std_ship_mode") or (_h(df, "_std_order_date") and _h(df, "_std_ship_date")):
        st.markdown("### Shipping & Fulfillment")
        ship_sum = get_shipping_summary(df)
        mode_df = ship_sum.get("mode_breakdown", pd.DataFrame())
        avg_transit = ship_sum.get("avg_days")
        if not mode_df.empty:
            fig_ship = go.Figure()
            val_col = "Orders" if "Orders" in mode_df.columns else "Sales"
            fig_ship.add_trace(go.Bar(
                x=mode_df["Ship Mode"], y=mode_df[val_col],
                name=val_col, marker_color=PALETTE[0],
                hovertemplate="%{x}<br>" + val_col + ": %{y:,}<extra></extra>",
            ))
            if "Avg Shipping Days" in mode_df.columns and avg_transit is not None:
                fig_ship.add_trace(go.Scatter(
                    x=mode_df["Ship Mode"], y=mode_df["Avg Shipping Days"],
                    name="Avg Transit Days", yaxis="y2", mode="lines+markers",
                    line=dict(color="#FACC15", width=2.5),
                    hovertemplate="%{x}<br>Avg Days: %{y:.1f} days<extra></extra>",
                ))
                fig_ship.update_layout(
                    yaxis2=dict(title="Days", overlaying="y", side="right", showgrid=False, tickfont=dict(color="#FACC15")),
                )
            _dl(fig_ship, "Fulfillment Volume & Transit Time by Ship Mode", 340)
            render_plotly(fig_ship, key="shipping_performance_chart")

    # 13. Discount vs Profit Analysis
    if _h(df, "_std_discount") and hp:
        st.markdown("### Discount vs Profit")
        color_opts = [k for k, c in [("Category", "_std_category"), ("Sub-Category", "_std_sub_category"), ("Region", "_std_region")] if _h(df, c)]
        color_by = st.selectbox("Color by", ["None"] + color_opts, key="dash_disc_color")
        sample = df.dropna(subset=["_std_discount", "_std_profit"])
        if len(sample) > 2000:
            sample = sample.sample(2000, random_state=42)
        color_col = {"Category": "_std_category", "Sub-Category": "_std_sub_category", "Region": "_std_region"}.get(color_by)
        hover = {c: True for c in ["_std_product_name", "_std_sales", "_std_discount"] if c in sample.columns}
        plot_df = sample.copy()
        plot_df["_profit_inr"] = _inr_col(plot_df["_std_profit"])
        fig_s = px.scatter(
            plot_df, x="_std_discount", y="_profit_inr", color=color_col,
            color_discrete_sequence=PALETTE, hover_data=hover, opacity=0.55,
        )
        _dl(fig_s, "Discount vs Profit", 400)
        fig_s.update_xaxes(title="Discount", tickformat=".0%")
        fig_s.update_yaxes(title="Profit (₹)")
        fig_s.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
        render_plotly(fig_s, key="discount_profit_chart")

    # 14. Top & Bottom Performers
    _render_performers(df, hs, hp, hq)

    # 15. Loss & Risk Alerts
    _render_alerts(df)

    # 16. Smart Business Insights
    st.markdown("### Smart Business Insights")
    _render_insights(df, ts, tp, margin)

    # 17. Sales Forecast
    st.markdown("### Sales Forecast")
    _render_forecast(df)

    # 18. Export Center
    st.markdown("### Export Center")
    _render_exports(df, dataset_name, date_str)


def _render_performers(df, hs, hp, hq):
    dims = [(l, c) for l, c in [
        ("Products", "_std_product_name"), ("Categories", "_std_category"),
        ("Regions", "_std_region"), ("Customers", "_std_customer_name"),
    ] if c in df.columns]
    if not dims:
        return
    st.markdown("### Top & Bottom Performers")
    c1, c2, c3 = st.columns(3)
    with c1:
        dim_label = st.selectbox("Dimension", [d[0] for d in dims], key="dash_perf_dim")
    with c2:
        metrics = [m for m, ok in [("Sales", hs), ("Profit", hp), ("Quantity", hq), ("Orders", True)] if ok]
        met = st.selectbox("Metric", metrics, key="dash_perf_met")
    with c3:
        n = st.selectbox("Count", [5, 10], key="dash_perf_n")
    dim_col = dict(dims)[dim_label]
    if met == "Orders" and "_std_order_id" in df.columns:
        agg = df.groupby(dim_col)["_std_order_id"].nunique()
    elif met == "Quantity":
        agg = df.groupby(dim_col)["_std_quantity"].sum()
    elif met == "Profit":
        agg = df.groupby(dim_col)["_std_profit"].sum()
    else:
        agg = df.groupby(dim_col)["_std_sales"].sum()
    money = met in ("Sales", "Profit")
    top = agg.sort_values(ascending=False).head(n)
    bot = agg.sort_values(ascending=True).head(n)
    t1, t2 = st.columns(2)
    with t1:
        st.caption(f"Top {n}")
        for name, val in top.items():
            st.write(f"**{name}** — {format_inr(val, compact=True) if money else f'{val:,.0f}'}")
    with t2:
        st.caption(f"Bottom {n}")
        for name, val in bot.items():
            st.write(f"**{name}** — {format_inr(val, compact=True) if money else f'{val:,.0f}'}")


def _render_alerts(df):
    alerts = []
    if "_std_profit" in df.columns:
        for col, label in [("_std_product_name", "product"), ("_std_category", "category"), ("_std_sub_category", "sub-category")]:
            if col not in df.columns:
                continue
            g = df.groupby(col)["_std_profit"].sum()
            losers = g[g < 0].sort_values()
            for name, val in losers.head(3).items():
                alerts.append(("red", f"{name} generated a loss of {format_inr(abs(val), compact=True)}."))
        if "_std_sales" in df.columns and "_std_product_name" in df.columns:
            p = df.groupby("_std_product_name").agg({"_std_sales": "sum", "_std_profit": "sum"})
            high_sales = p["_std_sales"] >= p["_std_sales"].quantile(0.75)
            low_profit = p["_std_profit"] <= 0
            risky = p[high_sales & low_profit].sort_values("_std_sales", ascending=False).head(3)
            for name, row in risky.iterrows():
                alerts.append(("orange", f"{name} has high sales ({format_inr(row['_std_sales'], compact=True)}) but low/negative profit."))
        if "_std_discount" in df.columns:
            high_disc = df[df["_std_discount"] >= df["_std_discount"].quantile(0.8)]
            if len(high_disc) and high_disc["_std_profit"].sum() < 0:
                alerts.append(("orange", f"High-discount transactions produced a net loss of {format_inr(abs(high_disc['_std_profit'].sum()), compact=True)}."))
    if "_std_region" in df.columns and "_std_profit" in df.columns and "_std_order_date" in df.columns:
        vd = df.dropna(subset=["_std_order_date"])
        if vd["_std_order_date"].dt.year.nunique() >= 2:
            years = sorted(vd["_std_order_date"].dt.year.unique())
            y1, y2 = years[-2], years[-1]
            r1 = vd[vd["_std_order_date"].dt.year == y1].groupby("_std_region")["_std_profit"].sum()
            r2 = vd[vd["_std_order_date"].dt.year == y2].groupby("_std_region")["_std_profit"].sum()
            both = r1.index.intersection(r2.index)
            for r in both:
                if r1[r] != 0 and r2[r] < r1[r]:
                    alerts.append(("red", f"{r} profit declined from {format_inr(r1[r], compact=True)} to {format_inr(r2[r], compact=True)}."))
    if not alerts:
        return
    st.markdown("### Loss & Risk Detection")
    for cls, text in alerts[:8]:
        st.markdown(f"""<div class="insight-box {cls}"><div class="insight-desc">{text}</div></div>""", unsafe_allow_html=True)


def _calc_period_comparison(df, mode="Previous period"):
    changes = {}
    if df is None or "_std_order_date" not in df.columns:
        return changes
    vd = df.dropna(subset=["_std_order_date"])
    if vd.empty:
        return changes
    d = vd["_std_order_date"]
    cur, prev = None, None
    if mode == "Year-over-year":
        y = int(d.max().year)
        cur, prev = vd[d.dt.year == y], vd[d.dt.year == y - 1]
    elif mode == "Quarter-over-quarter":
        last = d.max()
        q, y = last.quarter, last.year
        pq, py = (4, y - 1) if q == 1 else (q - 1, y)
        cur = vd[(d.dt.year == y) & (d.dt.quarter == q)]
        prev = vd[(d.dt.year == py) & (d.dt.quarter == pq)]
    elif mode == "Month-over-month":
        last = d.max().to_period("M")
        prev_p = last - 1
        cur = vd[d.dt.to_period("M") == last]
        prev = vd[d.dt.to_period("M") == prev_p]
    else:
        mid = d.min() + (d.max() - d.min()) / 2
        prev, cur = vd[d <= mid], vd[d > mid]
    if cur is None or prev is None or len(cur) == 0 or len(prev) == 0:
        return changes
    pairs = [("Total Sales", "_std_sales"), ("Total Profit", "_std_profit"), ("Units Sold", "_std_quantity")]
    if "_std_order_id" in df.columns:
        c_ord, p_ord = cur["_std_order_id"].nunique(), prev["_std_order_id"].nunique()
        if p_ord:
            changes["Total Orders"] = ((c_ord - p_ord) / abs(p_ord)) * 100
    for label, col in pairs:
        if col in df.columns:
            v1, v2 = prev[col].sum(), cur[col].sum()
            if v1 != 0:
                changes[label] = ((v2 - v1) / abs(v1)) * 100
    if "_std_sales" in df.columns and "_std_profit" in df.columns:
        m1 = prev["_std_profit"].sum() / prev["_std_sales"].sum() if prev["_std_sales"].sum() else 0
        m2 = cur["_std_profit"].sum() / cur["_std_sales"].sum() if cur["_std_sales"].sum() else 0
        if m1:
            changes["Profit Margin"] = ((m2 - m1) / abs(m1)) * 100
    return changes


def _render_insights(df, ts, tp, margin):
    insights = []
    if _h(df, "_std_region") and _h(df, "_std_sales"):
        rr = df.groupby("_std_region")["_std_sales"].sum()
        insights.append(("teal", "Top Region", f"{rr.idxmax()} leads with {format_inr(rr.max(), compact=True)}"))
    if _h(df, "_std_category") and _h(df, "_std_sales"):
        cc = df.groupby("_std_category")["_std_sales"].sum()
        insights.append(("green", "Top Category", f"{cc.idxmax()} at {format_inr(cc.max(), compact=True)}"))
    if _h(df, "_std_product_name") and _h(df, "_std_profit"):
        pp = df.groupby("_std_product_name")["_std_profit"].sum()
        insights.append(("green", "Most Profitable Product", f"{pp.idxmax()} with {format_inr(pp.max(), compact=True)}"))
    if _h(df, "_std_order_date") and _h(df, "_std_sales"):
        md = df.dropna(subset=["_std_order_date"]).copy()
        md["_m"] = md["_std_order_date"].dt.strftime("%b %Y")
        ms = md.groupby("_m")["_std_sales"].sum()
        insights.append(("", "Best Sales Period", f"{ms.idxmax()} with {format_inr(ms.max(), compact=True)}"))
    if _h(df, "_std_sub_category") and _h(df, "_std_profit"):
        sp = df.groupby("_std_sub_category")["_std_profit"].sum()
        if sp.min() < 0:
            insights.append(("red", "Biggest Loss Area", f"{sp.idxmin()} lost {format_inr(abs(sp.min()), compact=True)}"))
    if _h(df, "_std_region") and _h(df, "_std_sales") and _h(df, "_std_profit"):
        ragg = df.groupby("_std_region").agg({"_std_sales": "sum", "_std_profit": "sum"})
        ragg["m"] = ragg["_std_profit"] / ragg["_std_sales"].replace(0, np.nan)
        ragg = ragg.dropna()
        if not ragg.empty:
            insights.append(("teal", "Highest Margin Area", f"{ragg['m'].idxmax()} at {ragg['m'].max()*100:.1f}%"))
    if _h(df, "_std_order_date") and _h(df, "_std_sales") and _h(df, "_std_category"):
        vd = df.dropna(subset=["_std_order_date"])
        years = sorted(vd["_std_order_date"].dt.year.unique())
        if len(years) >= 2:
            y1, y2 = years[-2], years[-1]
            a = vd[vd["_std_order_date"].dt.year == y1].groupby("_std_category")["_std_sales"].sum()
            b = vd[vd["_std_order_date"].dt.year == y2].groupby("_std_category")["_std_sales"].sum()
            growth = ((b - a) / a.replace(0, np.nan) * 100).dropna()
            if not growth.empty:
                insights.append(("green", "Highest Growth Area", f"{growth.idxmax()} grew {growth.max():.1f}% ({int(y1)} → {int(y2)})"))
    if not insights:
        st.caption("Insufficient data for automated insights.")
        return
    cols = st.columns(min(len(insights), 4))
    for i, (cls, tag, text) in enumerate(insights[:8]):
        with cols[i % len(cols)]:
            st.markdown(
                f"""<div class="insight-box {cls}">
                <div class="insight-tag">{tag}</div>
                <div class="insight-desc">{text}</div>
            </div>""",
                unsafe_allow_html=True,
            )


def _render_forecast(df):
    result = forecast_sales(df)
    if not result.get("available"):
        st.info(result.get("message", "Forecast unavailable — insufficient historical data."))
        return
    hist, fc = result["historical"].copy(), result["forecast"].copy()
    hist["Sales"] = _inr_col(hist["Sales"])
    fc["Sales"] = _inr_col(fc["Sales"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Sales"], name="Historical", line=dict(color=PALETTE[1], width=2),
                             hovertemplate="₹%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=fc["Date"], y=fc["Sales"], name="Forecast",
                             line=dict(color="#FACC15", width=2, dash="dash"),
                             hovertemplate="Forecast: ₹%{y:,.0f}<extra></extra>"))
    _dl(fig, "Sales Forecast (next 3 months)", 350)
    render_plotly(fig, key="forecast_chart")
    st.caption(result["message"])


def _render_exports(df, dataset_name, date_str):
    if df is None:
        return
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Download filtered CSV", export_to_csv(df), "filtered_data.csv", "text/csv", key="dash_dl_csv")
    with c2:
        try:
            kpis = calculate_kpis(df)
            xls = export_to_excel(df, kpis, get_category_breakdown(df) if _h(df, "_std_category") else None)
            st.download_button(
                "Download filtered Excel", xls, "filtered_data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dash_dl_xlsx",
            )
        except Exception:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df.to_excel(w, index=False, sheet_name="Sales Data")
            st.download_button("Download filtered Excel", buf.getvalue(), "filtered_data.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dash_dl_xlsx")
    with c3:
        try:
            kpis = calculate_kpis(df)
            insights = generate_executive_insights(df)
            pdf = generate_executive_pdf(
                kpis=kpis,
                findings=insights.get("findings", []),
                date_range_str=date_str or "Active scope",
                cat_df=get_category_breakdown(df) if _h(df, "_std_category") else None,
                state_df=get_state_breakdown(df) if _h(df, "_std_state") else None,
                currency_symbol="₹",
                dataset_name=dataset_name,
            )
            st.download_button("Download executive PDF", pdf, "executive_report.pdf", "application/pdf", key="dash_dl_pdf")
        except Exception:
            st.caption("PDF export unavailable for this dataset.")
