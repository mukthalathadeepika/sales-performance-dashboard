"""
frontend/views/dashboard_view.py
Clean, executive Sales Performance Dashboard.
Displays Header, KPI Cards, 4 Core Charts (2x2 grid), and Key Insights.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Clean business color palette
PRIMARY_COLOR = "#2563EB"
SECONDARY_COLOR = "#0F172A"
ACCENT_GREEN = "#10B981"
ACCENT_RED = "#EF4444"
GRID_COLOR = "#F1F5F9"
CHART_BG = "#FFFFFF"


def _apply_clean_layout(fig, title: str, height: int = 340):
    """Unified clean business styling for Plotly charts."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.96,
            "x": 0.02,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 13, "color": SECONDARY_COLOR, "family": "system-ui, sans-serif"}
        },
        template="plotly_white",
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        height=height,
        margin=dict(l=15, r=15, t=45, b=25),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=12)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=GRID_COLOR, zeroline=False)
    return fig


def render_dashboard_view(df: pd.DataFrame, currency_symbol: str = "$"):
    """Renders the executive dashboard view."""
    # 1. Header
    st.markdown("""
    <div class="dashboard-header">
        <h1 class="dashboard-title">Sales Performance Dashboard</h1>
        <div class="dashboard-subtitle">Monitor sales, profitability and business performance</div>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.warning("No records match the current filter selection. Please adjust your filters.")
        return

    sym = currency_symbol

    # Calculations
    has_sales = "_std_sales" in df.columns
    has_profit = "_std_profit" in df.columns
    has_orders = "_std_order_id" in df.columns

    total_sales = float(df["_std_sales"].sum()) if has_sales else 0.0
    total_profit = float(df["_std_profit"].sum()) if has_profit else 0.0
    total_orders = int(df["_std_order_id"].nunique()) if has_orders else len(df)
    profit_margin = (total_profit / total_sales * 100) if (total_sales > 0 and has_profit) else 0.0

    # 2. KPI Cards Row (4 cards in 4 columns)
    k_col1, k_col2, k_col3, k_col4 = st.columns(4)

    with k_col1:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">Total Sales</div>
            <div class="kpi-value">{sym}{total_sales:,.2f}</div>
            <div class="kpi-sub">Across {len(df):,} transactions</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col2:
        prof_color = ACCENT_GREEN if total_profit >= 0 else ACCENT_RED
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">Total Profit</div>
            <div class="kpi-value" style="color: {prof_color};">{sym}{total_profit:,.2f}</div>
            <div class="kpi-sub">Net overall earnings</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col3:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{total_orders:,}</div>
            <div class="kpi-sub">Distinct order identifiers</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col4:
        margin_color = ACCENT_GREEN if profit_margin >= 0 else ACCENT_RED
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">Profit Margin</div>
            <div class="kpi-value" style="color: {margin_color};">{profit_margin:.2f}%</div>
            <div class="kpi-sub">Profit as % of revenue</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Core Charts (2x2 Grid)
    row1_c1, row1_c2 = st.columns(2)

    # Chart 1: Sales Trend Over Time
    with row1_c1:
        if "_std_order_date" in df.columns and has_sales:
            time_df = df.dropna(subset=["_std_order_date"]).copy()
            time_df["Month"] = time_df["_std_order_date"].dt.to_period("M").dt.to_timestamp()
            time_agg = time_df.groupby("Month", as_index=False)["_std_sales"].sum().sort_values("Month")
            time_agg["Month_Label"] = time_agg["Month"].dt.strftime("%b %Y")

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=time_agg["Month_Label"],
                y=time_agg["_std_sales"],
                name="Monthly Sales",
                marker_color=PRIMARY_COLOR,
                opacity=0.85,
                hovertemplate=f"Sales: {sym}%{{y:,.2f}}<extra></extra>"
            ))
            fig_trend.add_trace(go.Scatter(
                x=time_agg["Month_Label"],
                y=time_agg["_std_sales"],
                name="Trend Line",
                mode="lines+markers",
                line=dict(color=SECONDARY_COLOR, width=2),
                marker=dict(size=4),
                hoverinfo="skip"
            ))
            _apply_clean_layout(fig_trend, title="Monthly Sales Trend Over Time")
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Date information is not available.")

    # Chart 2: Sales by Category
    with row1_c2:
        if "_std_category" in df.columns and has_sales:
            cat_df = df.groupby("_std_category", as_index=False)["_std_sales"].sum().sort_values("_std_sales", ascending=True)
            fig_cat = px.bar(
                cat_df,
                x="_std_sales",
                y="_std_category",
                orientation="h",
                text="_std_sales",
                labels={"_std_sales": "Sales", "_std_category": "Category"},
                color_discrete_sequence=[PRIMARY_COLOR]
            )
            fig_cat.update_traces(
                texttemplate=f"{sym}%{{x:,.0f}}",
                textposition="inside",
                hovertemplate=f"<b>%{{y}}</b><br>Sales: {sym}%{{x:,.2f}}<extra></extra>"
            )
            _apply_clean_layout(fig_cat, title="Sales by Category")
            fig_cat.update_layout(yaxis_title=None, xaxis_title="Sales")
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Category field is not available.")

    row2_c1, row2_c2 = st.columns(2)

    # Chart 3: Sales by Region
    with row2_c1:
        if "_std_region" in df.columns and has_sales:
            reg_df = df.groupby("_std_region", as_index=False)["_std_sales"].sum().sort_values("_std_sales", ascending=False)
            fig_reg = px.bar(
                reg_df,
                x="_std_region",
                y="_std_sales",
                text="_std_sales",
                labels={"_std_sales": "Sales", "_std_region": "Region"},
                color_discrete_sequence=[PRIMARY_COLOR]
            )
            fig_reg.update_traces(
                texttemplate=f"{sym}%{{y:,.0f}}",
                textposition="outside",
                hovertemplate=f"<b>%{{x}}</b><br>Sales: {sym}%{{y:,.2f}}<extra></extra>"
            )
            _apply_clean_layout(fig_reg, title="Sales by Region")
            fig_reg.update_layout(xaxis_title=None, yaxis_title="Sales")
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("Region field is not available.")

    # Chart 4: Top 10 Products by Sales or Profit
    with row2_c2:
        if "_std_product_name" in df.columns:
            prod_metric_col = "_std_sales"
            prod_metric_label = "Sales"
            
            p_ctrl1, p_ctrl2 = st.columns([3, 2])
            with p_ctrl2:
                prod_metric_choice = st.selectbox(
                    "Metric",
                    options=["Sales", "Profit"],
                    index=0,
                    key="dash_prod_metric",
                    label_visibility="collapsed"
                )
            if prod_metric_choice == "Profit" and has_profit:
                prod_metric_col = "_std_profit"
                prod_metric_label = "Profit"

            prod_df = df.groupby("_std_product_name", as_index=False)[prod_metric_col].sum()
            prod_df = prod_df.sort_values(prod_metric_col, ascending=False).head(10)
            # Reverse sort so rank #1 is at top of horizontal bar
            prod_df = prod_df.sort_values(prod_metric_col, ascending=True)

            fig_prod = px.bar(
                prod_df,
                x=prod_metric_col,
                y="_std_product_name",
                orientation="h",
                labels={prod_metric_col: prod_metric_label, "_std_product_name": "Product"},
                color_discrete_sequence=[PRIMARY_COLOR if prod_metric_choice == "Sales" else ACCENT_GREEN]
            )
            fig_prod.update_traces(
                hovertemplate=f"<b>%{{y}}</b><br>{prod_metric_label}: {sym}%{{x:,.2f}}<extra></extra>"
            )
            _apply_clean_layout(fig_prod, title=f"Top 10 Products by {prod_metric_label}")
            fig_prod.update_layout(yaxis_title=None, xaxis_title=prod_metric_label, yaxis=dict(showticklabels=False))
            st.plotly_chart(fig_prod, use_container_width=True)
        else:
            st.info("Product Name field is not available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Key Insights Section (3-4 concise data-calculated findings)
    st.markdown("### 💡 Key Insights")
    
    ins_col1, ins_col2, ins_col3, ins_col4 = st.columns(4)

    # 1. Highest Performing Region
    with ins_col1:
        if "_std_region" in df.columns and has_sales:
            reg_agg = df.groupby("_std_region")["_std_sales"].sum().sort_values(ascending=False)
            top_reg = reg_agg.index[0]
            top_reg_val = reg_agg.iloc[0]
            top_reg_pct = (top_reg_val / total_sales * 100) if total_sales > 0 else 0
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-card-title">Top Region</div>
                <div class="insight-card-text">
                    <b>{top_reg}</b> leads with <b>{sym}{top_reg_val:,.1f}</b> in sales ({top_reg_pct:.1f}% share).
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 2. Highest Performing Category
    with ins_col2:
        if "_std_category" in df.columns and has_sales:
            cat_agg = df.groupby("_std_category")["_std_sales"].sum().sort_values(ascending=False)
            top_cat = cat_agg.index[0]
            top_cat_val = cat_agg.iloc[0]
            top_cat_pct = (top_cat_val / total_sales * 100) if total_sales > 0 else 0
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-card-title">Top Category</div>
                <div class="insight-card-text">
                    <b>{top_cat}</b> is the largest category at <b>{sym}{top_cat_val:,.1f}</b> ({top_cat_pct:.1f}% share).
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 3. Most Profitable Product
    with ins_col3:
        if "_std_product_name" in df.columns and has_profit:
            prod_agg = df.groupby("_std_product_name")["_std_profit"].sum().sort_values(ascending=False)
            best_prod = prod_agg.index[0]
            best_prod_prof = prod_agg.iloc[0]
            # Truncate product name if too long
            short_name = best_prod[:32] + "..." if len(best_prod) > 35 else best_prod
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-card-title">Top Product by Profit</div>
                <div class="insight-card-text">
                    <b>{short_name}</b> delivered <b>{sym}{best_prod_prof:,.1f}</b> in net profit.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 4. Strongest Sales Period
    with ins_col4:
        if "_std_order_date" in df.columns and has_sales:
            time_df = df.dropna(subset=["_std_order_date"]).copy()
            if len(time_df) > 0:
                time_df["Month_Str"] = time_df["_std_order_date"].dt.strftime("%b %Y")
                month_agg = time_df.groupby("Month_Str")["_std_sales"].sum().sort_values(ascending=False)
                best_month = month_agg.index[0]
                best_month_val = month_agg.iloc[0]
                st.markdown(f"""
                <div class="insight-card">
                <div class="insight-card-title">Peak Sales Period</div>
                <div class="insight-card-text">
                    <b>{best_month}</b> achieved the highest monthly sales of <b>{sym}{best_month_val:,.1f}</b>.
                </div>
                </div>
                """, unsafe_allow_html=True)
