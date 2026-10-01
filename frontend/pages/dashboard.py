"""
frontend/pages/dashboard.py
Interactive Executive Sales Performance Dashboard.
Implements PRD Section 4: KPI Cards, Multi-level filters, Plotly Visuals, Drill-down, and Exports.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from frontend.components.kpi_card import render_kpi_card
from frontend.components import charts
from backend.analytics.kpi import calculate_kpis, format_metric_value
from backend.analytics.trends import get_time_trends
from backend.analytics.products import get_product_rankings
from backend.analytics.categories import get_category_breakdown, get_subcategory_breakdown
from backend.analytics.geography import get_regional_breakdown, get_state_breakdown, get_city_breakdown
from backend.analytics.customers import get_segment_breakdown
from backend.analytics.shipping import get_shipping_summary
from backend.analytics.returns import get_returns_analysis
from backend.exports.exporter import export_to_csv, export_to_excel


def render_dashboard_page(filtered_df: pd.DataFrame, meta: Dict[str, Any], full_df: pd.DataFrame):
    """Renders the executive dashboard view."""
    sym = meta.get("currency_symbol", "$")
    target = meta.get("sales_target")

    # Compute KPIs
    kpis = calculate_kpis(filtered_df, sales_target=target)

    # 1. Executive KPI Summary Row
    st.markdown("### 📈 Executive Performance Summary")
    k_col1, k_col2, k_col3, k_col4 = st.columns(4)
    with k_col1:
        sales_str = format_metric_value(kpis["total_sales"], prefix=sym, decimals=2)
        target_sub = f"Target: {sym}{target:,.0f} ({kpis['target_achievement_pct']:.1f}%)" if target else "Active records"
        render_kpi_card("Total Sales / Revenue", sales_str, subtitle=target_sub, icon="💰", border_accent="#2563EB")

    with k_col2:
        prof_str = format_metric_value(kpis["total_profit"], prefix=sym, decimals=2)
        prof_pos = kpis["total_profit"] >= 0 if kpis["total_profit"] is not None else True
        margin_sub = f"Margin: {kpis['profit_margin_pct']:.1f}%" if kpis['profit_margin_pct'] is not None else ""
        render_kpi_card(
            "Total Net Profit",
            prof_str,
            delta=f"{kpis['profit_margin_pct']:.1f}% margin" if kpis['profit_margin_pct'] else None,
            delta_positive=prof_pos,
            subtitle="Includes negative profits",
            icon="📈",
            border_accent="#10B981" if prof_pos else "#EF4444"
        )

    with k_col3:
        ord_str = format_metric_value(kpis["total_orders"], decimals=0)
        label = "Total Orders (Distinct)" if kpis["is_distinct_orders"] else "Total Order Lines"
        aov_sub = f"AOV: {sym}{kpis['aov']:,.2f}" if kpis["aov"] else f"{len(filtered_df):,} line items"
        render_kpi_card(label, ord_str, subtitle=aov_sub, icon="📦", border_accent="#6366F1")

    with k_col4:
        qty_str = format_metric_value(kpis["total_quantity"], decimals=0)
        cust_sub = f"{kpis['total_customers']:,} Customers" if kpis["total_customers"] else "Volume sold"
        render_kpi_card("Total Quantity Sold", qty_str, subtitle=cust_sub, icon="🏷️", border_accent="#F59E0B")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Time-Based Trends
    st.markdown("### ⏱️ Revenue & Profit Trends Over Time")
    t_ctrl1, t_ctrl2 = st.columns([2, 4])
    with t_ctrl1:
        time_freq = st.selectbox("Time Grouping", options=["Monthly (M)", "Quarterly (Q)", "Yearly (Y)", "Weekly (W)"], index=0)
        freq_code = time_freq[0]
    with t_ctrl2:
        view_type = st.radio("Trend View", options=["Sales & Profit Combo", "Cumulative Sales"], horizontal=True)

    time_df = get_time_trends(filtered_df, freq=freq_code)
    if not time_df.empty:
        if view_type == "Sales & Profit Combo":
            fig_time = charts.plot_sales_profit_timeline(time_df, currency_symbol=sym)
        else:
            fig_time = charts.plot_cumulative_sales(time_df, currency_symbol=sym)
        st.plotly_chart(fig_time, use_container_width=True)

        with st.expander("📊 View Trend Aggregate Table"):
            st.dataframe(time_df, use_container_width=True)
    else:
        st.info("Date information is not available or filtered out.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Product Performance & Rankings
    st.markdown("### 🏆 Product Performance & Profitability Analysis")
    p_col_ctrl1, p_col_ctrl2, p_col_ctrl3 = st.columns([2, 2, 2])
    with p_col_ctrl1:
        rank_metric = st.selectbox("Ranking Metric", options=["Sales", "Profit", "Quantity"], index=0)
    with p_col_ctrl2:
        top_n_count = st.slider("Number of Products", min_value=5, max_value=20, value=10, step=5)
    with p_col_ctrl3:
        product_display_mode = st.radio("Display Mode", options=["Visual Charts", "Data Tables"], horizontal=True)

    top_prod, bottom_prod = get_product_rankings(filtered_df, metric=rank_metric, n=top_n_count)

    if product_display_mode == "Visual Charts":
        p_ch1, p_ch2 = st.columns(2)
        with p_ch1:
            if not top_prod.empty:
                st.plotly_chart(charts.plot_top_products_bar(top_prod, metric=rank_metric, currency_symbol=sym), use_container_width=True)
        with p_ch2:
            if not bottom_prod.empty:
                st.plotly_chart(charts.plot_loss_products_bar(bottom_prod, currency_symbol=sym), use_container_width=True)
    else:
        t_tab1, t_tab2 = st.tabs(["Top Performers", "Bottom / Loss-Making Performers"])
        with t_tab1:
            st.dataframe(top_prod, use_container_width=True)
        with t_tab2:
            st.dataframe(bottom_prod, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Category & Sub-Category Analysis
    st.markdown("### 📂 Category & Sub-Category Composition")
    cat_df = get_category_breakdown(filtered_df)
    subcat_df = get_subcategory_breakdown(filtered_df)

    cat_tab1, cat_tab2 = st.tabs(["Category Treemap", "Profitability Quadrant (Sales vs Margin %)"])
    with cat_tab1:
        if not subcat_df.empty:
            st.plotly_chart(charts.plot_category_treemap(subcat_df, currency_symbol=sym), use_container_width=True)
            st.dataframe(cat_df, use_container_width=True)
    with cat_tab2:
        if not subcat_df.empty:
            st.plotly_chart(charts.plot_quadrant_scatter(subcat_df, currency_symbol=sym), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. Geographic Drill-Down Analysis
    st.markdown("### 🗺️ Geographic Distribution & Drill-Down")
    g_tab1, g_tab2 = st.tabs(["US States Map", "Interactive Hierarchy Drill-Down (Region → State → City)"])
    
    state_df = get_state_breakdown(filtered_df)
    with g_tab1:
        if not state_df.empty and "State Code" in state_df.columns:
            st.plotly_chart(charts.plot_us_state_choropleth(state_df, metric="Sales", currency_symbol=sym), use_container_width=True)
            st.dataframe(state_df.head(10), use_container_width=True)

    with g_tab2:
        st.write("Drill down from Region to State to City:")
        reg_df = get_regional_breakdown(filtered_df)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**1. Regional Summary**")
            st.dataframe(reg_df[["Region", "Sales", "Profit", "Profit Margin %"]], use_container_width=True)
            regions_list = ["-- Select Region to Drill --"] + list(reg_df["Region"].unique()) if not reg_df.empty else []
            selected_drill_reg = st.selectbox("Choose Region", options=regions_list)

        with c2:
            st.markdown("**2. States in Region**")
            if selected_drill_reg and selected_drill_reg != "-- Select Region to Drill --":
                drill_state_df = get_state_breakdown(filtered_df, region_filter=selected_drill_reg)
                st.dataframe(drill_state_df[["State", "Sales", "Profit", "Profit Margin %"]], use_container_width=True)
                states_list = ["-- Select State to Drill --"] + list(drill_state_df["State"].unique()) if not drill_state_df.empty else []
                selected_drill_state = st.selectbox("Choose State", options=states_list)
            else:
                st.info("Select a region to view states.")
                selected_drill_state = None

        with c3:
            st.markdown("**3. Cities in State**")
            if selected_drill_state and selected_drill_state != "-- Select State to Drill --":
                drill_city_df = get_city_breakdown(filtered_df, state_filter=selected_drill_state)
                st.dataframe(drill_city_df[["City", "Sales", "Profit"]].head(15), use_container_width=True)
            else:
                st.info("Select a state to view cities.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. Customer Segments, Shipping & Returns
    st.markdown("### 👥 Segments, Fulfillment & Returns")
    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        st.markdown("**Customer Segments**")
        seg_df = get_segment_breakdown(filtered_df)
        if not seg_df.empty:
            st.plotly_chart(charts.plot_segment_donut(seg_df, currency_symbol=sym), use_container_width=True)

    with col_s2:
        st.markdown("**Shipping Modes**")
        ship_summary = get_shipping_summary(filtered_df)
        if not ship_summary["mode_breakdown"].empty:
            st.plotly_chart(charts.plot_shipping_modes_bar(ship_summary["mode_breakdown"]), use_container_width=True)
            if ship_summary["avg_days"] is not None:
                st.caption(f"Average fulfillment transit time: **{ship_summary['avg_days']} days** (Ship Date - Order Date).")

    with col_s3:
        st.markdown("**Returns Coverage & Rate**")
        returns_info = get_returns_analysis(filtered_df)
        if returns_info["has_returns_data"]:
            st.metric("Tracked Returns", f"{returns_info['total_returns']:,}", delta=f"{returns_info['return_rate_pct']}% return rate", delta_color="inverse")
            st.warning(returns_info["limitation_note"])
            if not returns_info["category_returns"].empty:
                st.dataframe(returns_info["category_returns"], use_container_width=True)
        else:
            st.info("Returns field not available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 7. Underlying Data Table & Export
    st.markdown("### 📥 Active Dataset Records & Exports")
    st.write(f"Showing active filtered dataset ({len(filtered_df):,} records).")
    
    exp_c1, exp_c2, exp_c3 = st.columns([2, 2, 4])
    with exp_c1:
        mask_names = st.checkbox("Redact Customer Names", value=False)
        csv_bytes = export_to_csv(filtered_df, include_customer_names=(not mask_names))
        st.download_button(
            label="📥 Download Filtered CSV",
            data=csv_bytes,
            file_name="sales_data_filtered.csv",
            mime="text/csv",
            use_container_width=True
        )
    with exp_c2:
        excel_bytes = export_to_excel(
            filtered_df,
            kpis=kpis,
            cat_df=cat_df,
            reg_df=reg_df,
            include_customer_names=(not mask_names)
        )
        st.download_button(
            label="📥 Download Multi-Sheet Excel",
            data=excel_bytes,
            file_name="sales_performance_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Display preview table
    display_cols = [c for c in filtered_df.columns if not c.startswith("_std_")]
    st.dataframe(filtered_df[display_cols].head(100), use_container_width=True)
