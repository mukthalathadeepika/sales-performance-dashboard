"""
frontend/views/dashboard_view.py
Executive Sales Performance Dashboard inspired by reference design.
Features:
- Clean header with dataset status
- 6 High-contrast KPI cards (Total Sales, Total Profit, Distinct Orders, Margin, AOV, Quantity)
- 2x2 Core Chart Grid matching reference image:
    1. Monthly sales and profit timeline
    2. Category sales vs. profit
    3. Profit by sub-category (diverging Green/Red)
    4. Regional profit margins (%) with overall benchmark
- Additional deep dives: Top 10 products and Customer Segment donut
- 4 Key Insight cards at bottom
All monetary amounts strictly in Indian Rupees (₹).
"""

from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd

from backend.analytics.currency import format_inr
from frontend.components.charts import (
    plot_monthly_sales_and_profit,
    plot_category_sales_vs_profit,
    plot_profit_by_subcategory,
    plot_regional_profit_margins,
    plot_top_products_bar,
    plot_customer_segment_donut
)


def render_dashboard_view(df: pd.DataFrame, dataset_name: str = "SuperStore_Sales_Dataset.csv"):
    """Renders the complete executive dashboard view."""
    # 1. Header Area
    total_rows = len(df) if df is not None else 0
    date_str = ""
    if df is not None and "_std_order_date" in df.columns:
        valid_dates = df["_std_order_date"].dropna()
        if len(valid_dates) > 0:
            date_str = f" • {valid_dates.min().strftime('%Y-%m-%d')} to {valid_dates.max().strftime('%Y-%m-%d')}"

    st.markdown(f"""
    <div class="dash-header-wrap">
        <div>
            <h1 class="dash-header-title">Sales Performance Dashboard</h1>
            <div class="dash-header-subtitle">Monitor sales, profitability and business performance across all dimensions</div>
        </div>
        <div>
            <span class="dash-badge">
                <span class="dash-badge-dot"></span>
                <span>Active Data: <b>{dataset_name}</b> ({total_rows:,} rows{date_str})</span>
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.warning("No records match your selected filters. Please adjust your filter criteria or reset filters.")
        return

    # Calculations
    has_sales = "_std_sales" in df.columns
    has_profit = "_std_profit" in df.columns
    has_orders = "_std_order_id" in df.columns
    has_qty = "_std_quantity" in df.columns

    total_sales = float(df["_std_sales"].sum()) if has_sales else 0.0
    total_profit = float(df["_std_profit"].sum()) if has_profit else 0.0
    total_orders = int(df["_std_order_id"].nunique()) if has_orders else len(df)
    total_qty = int(df["_std_quantity"].sum()) if has_qty else 0
    profit_margin = (total_profit / total_sales * 100) if (total_sales > 0 and has_profit) else 0.0
    aov = (total_sales / total_orders) if (total_orders > 0 and has_sales) else 0.0

    # 2. Executive KPI Cards (Row of 6 clean cards)
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Sales</div>
            <div class="kpi-value">{format_inr(total_sales, compact=True)}</div>
            <div class="kpi-meta">
                <span>{format_inr(total_sales, compact=False)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        card_class = "green" if total_profit >= 0 else "red"
        pill_class = "positive" if profit_margin >= 0 else "negative"
        st.markdown(f"""
        <div class="kpi-card {card_class}">
            <div class="kpi-title">Total Profit</div>
            <div class="kpi-value">{format_inr(total_profit, compact=True)}</div>
            <div class="kpi-meta">
                <span class="kpi-pill {pill_class}">{profit_margin:.1f}% margin</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="kpi-card teal">
            <div class="kpi-title">Total Orders</div>
            <div class="kpi-value">{total_orders:,}</div>
            <div class="kpi-meta">
                <span>Distinct order IDs</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        margin_pill = "positive" if profit_margin >= 10 else "negative" if profit_margin < 0 else "neutral"
        st.markdown(f"""
        <div class="kpi-card orange">
            <div class="kpi-title">Profit Margin</div>
            <div class="kpi-value">{profit_margin:.2f}%</div>
            <div class="kpi-meta">
                <span class="kpi-pill {margin_pill}">Target: 10%+</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Avg Order Value</div>
            <div class="kpi-value">{format_inr(aov, compact=True)}</div>
            <div class="kpi-meta">
                <span>{format_inr(aov, compact=False)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c6:
        st.markdown(f"""
        <div class="kpi-card teal">
            <div class="kpi-title">Total Units Sold</div>
            <div class="kpi-value">{total_qty:,}</div>
            <div class="kpi-meta">
                <span>Across {len(df):,} items</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Main Visualizations Grid (Inspired by reference superstore_analysis.png)
    # Row 1: Monthly Timeline + Category Sales vs Profit
    r1_col1, r1_col2 = st.columns(2)

    with r1_col1:
        if "_std_order_date" in df.columns and has_sales:
            fig_time = plot_monthly_sales_and_profit(df)
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("Order date field not available for timeline.")

    with r1_col2:
        if "_std_category" in df.columns and has_sales:
            fig_cat = plot_category_sales_vs_profit(df)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Category field not available.")

    # Row 2: Profit by Sub-Category (Diverging) + Regional Profit Margins
    r2_col1, r2_col2 = st.columns(2)

    with r2_col1:
        if "_std_sub_category" in df.columns and has_profit:
            fig_sub = plot_profit_by_subcategory(df)
            st.plotly_chart(fig_sub, use_container_width=True)
        else:
            st.info("Sub-category field not available.")

    with r2_col2:
        if "_std_region" in df.columns and has_sales and has_profit:
            fig_reg = plot_regional_profit_margins(df)
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("Region field not available.")

    # Row 3: Top Products + Customer Segments
    r3_col1, r3_col2 = st.columns(2)

    with r3_col1:
        if "_std_product_name" in df.columns:
            p_head_c1, p_head_c2 = st.columns([3, 2])
            with p_head_c2:
                prod_metric = st.selectbox(
                    "Metric",
                    options=["Sales", "Profit"],
                    index=0,
                    key="dash_prod_metric_selector",
                    label_visibility="collapsed"
                )
            fig_prod = plot_top_products_bar(df, metric=prod_metric, n=10)
            st.plotly_chart(fig_prod, use_container_width=True)
        else:
            st.info("Product name field not available.")

    with r3_col2:
        if "_std_segment" in df.columns and has_sales:
            fig_seg = plot_customer_segment_donut(df)
            st.plotly_chart(fig_seg, use_container_width=True)
        else:
            st.info("Customer segment field not available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Key Insights Section (4 automatically calculated cards)
    st.markdown("### 💡 Key Business Insights")

    i1, i2, i3, i4 = st.columns(4)

    # Insight 1: Top Region
    with i1:
        if "_std_region" in df.columns and has_sales:
            reg_agg = df.groupby("_std_region")["_std_sales"].sum().sort_values(ascending=False)
            top_reg = reg_agg.index[0]
            top_reg_val = reg_agg.iloc[0]
            top_reg_pct = (top_reg_val / total_sales * 100) if total_sales > 0 else 0
            st.markdown(f"""
            <div class="insight-box">
                <div class="insight-tag">Highest Sales Region</div>
                <div class="insight-headline">{top_reg} Region</div>
                <div class="insight-desc">
                    Generated <b>{format_inr(top_reg_val, compact=True)}</b> ({top_reg_pct:.1f}% share of revenue).
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Insight 2: Top Category
    with i2:
        if "_std_category" in df.columns and has_sales:
            cat_agg = df.groupby("_std_category")["_std_sales"].sum().sort_values(ascending=False)
            top_cat = cat_agg.index[0]
            top_cat_val = cat_agg.iloc[0]
            top_cat_pct = (top_cat_val / total_sales * 100) if total_sales > 0 else 0
            st.markdown(f"""
            <div class="insight-box green">
                <div class="insight-tag">Leading Category</div>
                <div class="insight-headline">{top_cat}</div>
                <div class="insight-desc">
                    Accounts for <b>{format_inr(top_cat_val, compact=True)}</b> ({top_cat_pct:.1f}% share of sales).
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Insight 3: Most Profitable Product
    with i3:
        if "_std_product_name" in df.columns and has_profit:
            prod_agg = df.groupby("_std_product_name")["_std_profit"].sum().sort_values(ascending=False)
            best_prod = prod_agg.index[0]
            best_prof = prod_agg.iloc[0]
            short_p = best_prod[:28] + "..." if len(best_prod) > 30 else best_prod
            st.markdown(f"""
            <div class="insight-box green">
                <div class="insight-tag">Most Profitable Item</div>
                <div class="insight-headline">{short_p}</div>
                <div class="insight-desc">
                    Produced <b>{format_inr(best_prof, compact=True)}</b> in total net profit.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Insight 4: Peak Sales Period
    with i4:
        if "_std_order_date" in df.columns and has_sales:
            valid_d = df.dropna(subset=["_std_order_date"]).copy()
            if len(valid_d) > 0:
                valid_d["Month_Year"] = valid_d["_std_order_date"].dt.strftime("%b %Y")
                m_agg = valid_d.groupby("Month_Year")["_std_sales"].sum().sort_values(ascending=False)
                best_m = m_agg.index[0]
                best_m_val = m_agg.iloc[0]
                st.markdown(f"""
                <div class="insight-box orange">
                    <div class="insight-tag">Strongest Sales Period</div>
                    <div class="insight-headline">{best_m}</div>
                    <div class="insight-desc">
                        Recorded peak monthly turnover of <b>{format_inr(best_m_val, compact=True)}</b>.
                    </div>
                </div>
                """, unsafe_allow_html=True)
