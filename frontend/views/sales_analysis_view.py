"""
frontend/views/sales_analysis_view.py
Interactive Sales Analysis: custom chart builder, date comparison, drill-down.
"""

import io
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.analytics.currency import format_inr, convert_series_to_inr, convert_to_inr
from frontend.components.charts import PLOTLY_CONFIG
from frontend.components.chart_utils import render_plotly
from frontend.components.map import render_geo_map

PALETTE = ["#00D4FF", "#22C55E", "#FACC15", "#A78BFA", "#F97316", "#EF4444", "#14B8A6", "#3B82F6"]
BG_CHART = "#162040"
CLR_TEXT = "#E2E8F0"
CLR_MUTED = "#94A3B8"
MONEY_METRICS = {"Sales", "Profit", "Avg Order Value", "Average Order Value"}

COLOR_PRESETS = {
    "Default": PALETTE,
    "Blue": ["#3B82F6", "#93C5FD", "#1D4ED8"],
    "Teal": ["#14B8A6", "#5EEAD4", "#0F766E"],
    "Purple": ["#A78BFA", "#C4B5FD", "#6D28D9"],
    "Orange": ["#F97316", "#FDBA74", "#C2410C"],
    "Green": ["#22C55E", "#86EFAC", "#15803D"],
    "Red": ["#EF4444", "#FCA5A5", "#B91C1C"],
}


def _apply_dark_layout(fig, title="", height=400):
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.96, font=dict(size=14, color=CLR_TEXT, family="Inter, sans-serif")),
        template="plotly_dark", paper_bgcolor=BG_CHART, plot_bgcolor=BG_CHART, height=height,
        margin=dict(l=12, r=12, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11, color=CLR_MUTED)),
        hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_color=CLR_TEXT),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color=CLR_MUTED))
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color=CLR_MUTED))
    return fig


def _get_available_fields(df):
    fields = {}
    field_map = {
        "Category": "_std_category", "Sub-Category": "_std_sub_category",
        "Product": "_std_product_name", "Region": "_std_region",
        "State": "_std_state", "City": "_std_city", "Segment": "_std_segment",
        "Ship Mode": "_std_ship_mode", "Payment Method": "_std_payment_mode",
        "Customer": "_std_customer_name", "Salesperson": "_std_salesperson",
        "Country": "_std_country",
    }
    for label, col in field_map.items():
        if col in df.columns:
            fields[label] = col
    return fields


def _get_date_fields(df):
    if "_std_order_date" not in df.columns:
        return {}
    return {"Year": "Y", "Quarter": "Q", "Month": "M", "Week": "W", "Day": "D"}


def _png(fig):
    try:
        return fig.to_image(format="png")
    except Exception:
        return None


def _apply_analysis_filters(df):
    work = df.copy()
    if "_std_order_date" in work.columns:
        date_val = st.session_state.get("saf_date")
        if isinstance(date_val, (tuple, list)) and len(date_val) == 2:
            work = work[
                (work["_std_order_date"].dt.date >= date_val[0])
                & (work["_std_order_date"].dt.date <= date_val[1])
            ]
    mapping = {
        "saf_region": "_std_region",
        "saf_category": "_std_category",
        "saf_segment": "_std_segment",
        "saf_state": "_std_state",
    }
    for key, col in mapping.items():
        vals = st.session_state.get(key)
        if vals and col in work.columns:
            work = work[work[col].isin(vals)]
    return work


def render_sales_analysis_view(df: pd.DataFrame):
    st.markdown("""
    <div class="dash-header">
        <h1 class="dash-title">Sales Analysis</h1>
        <div class="dash-subtitle">Build custom analyses from your active dataset.</div>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <div class="empty-state-title">No Data Available</div>
            <div class="empty-state-desc">Upload a dataset to start analyzing your sales data.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    with st.expander("Analysis filters", expanded=False):
        if "_std_order_date" in df.columns:
            vd = df["_std_order_date"].dropna()
            if len(vd) > 0:
                st.date_input(
                    "Analysis date range",
                    value=(vd.min().date(), vd.max().date()),
                    min_value=vd.min().date(),
                    max_value=vd.max().date(),
                    key="saf_date",
                )
        cols = st.columns(4)
        pairs = [
            ("Region", "_std_region", "saf_region"),
            ("Category", "_std_category", "saf_category"),
            ("Segment", "_std_segment", "saf_segment"),
            ("State", "_std_state", "saf_state"),
        ]
        for i, (label, col, key) in enumerate(pairs):
            with cols[i]:
                if col in df.columns:
                    opts = sorted(str(v) for v in df[col].dropna().unique())
                    st.multiselect(label, opts, key=key)

    df = _apply_analysis_filters(df)
    if df.empty:
        st.info("No rows match the current analysis filters.")
        return

    available_fields = _get_available_fields(df)
    date_fields = _get_date_fields(df)
    has_sales = "_std_sales" in df.columns
    has_profit = "_std_profit" in df.columns
    has_qty = "_std_quantity" in df.columns
    has_orders = "_std_order_id" in df.columns
    has_discount = "_std_discount" in df.columns

    metrics = {}
    if has_sales:
        metrics["Sales"] = "_std_sales"
    if has_profit:
        metrics["Profit"] = "_std_profit"
    if has_qty:
        metrics["Quantity"] = "_std_quantity"
    if has_orders:
        metrics["Orders"] = "_std_order_id"
    if has_sales and has_profit:
        metrics["Profit Margin"] = "_margin_"
    if has_sales and has_orders:
        metrics["Average Order Value"] = "_aov_"

    if not metrics:
        st.warning("This dataset does not contain measurable sales metrics.")
        return

    tab_builder, tab_compare, tab_performers, tab_discount = st.tabs([
        "Chart Builder", "Date Comparison", "Top/Bottom Performers", "Discount Analysis"
    ])

    with tab_builder:
        _render_builder(df, metrics, available_fields, date_fields)

    with tab_compare:
        _render_compare_tab(df, metrics, available_fields)

    with tab_performers:
        _render_performers_tab(df, metrics, available_fields)

    with tab_discount:
        _render_discount_tab(df, available_fields, has_discount, has_profit)


def _render_builder(df, metrics, available_fields, date_fields):
    st.markdown("### Build Your Analysis")
    st.caption("1. Metric → 2. Date range (filters) → 3. Group by → 4. Chart → 5. Colors → Generate")

    drill = st.session_state.get("sa_drill") or []
    if drill:
        b1, b2 = st.columns([1, 6])
        with b1:
            if st.button("← Back", key="sa_drill_back"):
                st.session_state["sa_drill"] = drill[:-1]
                st.rerun()
        with b2:
            st.caption(" › ".join(f"{d['level']}: {d['value']}" for d in drill))

    work = df
    for step in drill:
        col = step.get("col")
        if col in work.columns:
            work = work[work[col].astype(str) == str(step["value"])]

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_choice = st.selectbox("Metric", list(metrics.keys()), key="sa_metric")
    group_options = list(date_fields.keys()) + list(available_fields.keys()) if date_fields else list(available_fields.keys())
    with c2:
        group_choice = st.selectbox("Group By", group_options or ["(none)"], key="sa_group")
    chart_types = [
        "Bar", "Horizontal Bar", "Line", "Area", "Pie", "Donut", "Scatter",
        "Histogram", "Treemap", "Map", "Combo", "KPI", "Table",
    ]
    with c3:
        chart_type = st.selectbox("Chart Type", chart_types, key="sa_chart_type")

    c4, c5, c6 = st.columns(3)
    with c4:
        color_choice = st.selectbox("Color palette", list(COLOR_PRESETS.keys()) + ["Custom"], key="sa_color")
        if color_choice == "Custom":
            custom = st.color_picker("Custom color", "#00D4FF", key="sa_custom_color")
            colors = [custom]
        else:
            colors = COLOR_PRESETS[color_choice]
    with c5:
        generate = st.button("Generate Analysis", type="primary", use_container_width=True, key="sa_generate")
    with c6:
        if st.button("Reset Analysis", use_container_width=True, key="sa_reset"):
            for k in list(st.session_state.keys()):
                if k.startswith("sa_"):
                    del st.session_state[k]
            st.rerun()

    if generate:
        st.session_state["sa_last_generated"] = True

    if not st.session_state.get("sa_last_generated"):
        st.caption("Choose options, then click Generate Analysis.")
        return

    try:
        chart_df = _build_analysis_data(work, metric_choice, group_choice, metrics, available_fields, date_fields)
        if chart_df is None or chart_df.empty:
            st.warning("No data available for this combination.")
            return

        if chart_type == "KPI":
            val = chart_df.iloc[:, 1].sum() if chart_df.shape[1] > 1 else 0
            display = format_inr(val, compact=True, convert=False) if metric_choice in MONEY_METRICS else f"{val:,.1f}"
            st.markdown(
                f"""<div class="kpi-card teal"><div class="kpi-title">{metric_choice} by {group_choice}</div>
                <div class="kpi-value">{display}</div></div>""",
                unsafe_allow_html=True,
            )
        elif chart_type == "Map":
            geo_cols = ["State", "Region", "City", "Country"]
            if group_choice in geo_cols or any(c in group_choice for c in geo_cols):
                render_geo_map(work, metric="Sales" if metric_choice == "Sales" else ("Profit" if metric_choice == "Profit" else "Orders"), key="sa_map_chart")
            else:
                st.info(f"Map visualization requires geographic grouping (State, Region, City, Country). '{group_choice}' is not geographic.")
                st.dataframe(chart_df, use_container_width=True, hide_index=True)
        elif chart_type == "Table":
            st.dataframe(chart_df, use_container_width=True, hide_index=True)
        else:
            fig = _build_chart(chart_df, chart_type, metric_choice, group_choice, colors)
            if fig is not None:
                render_plotly(fig, key="sa_custom_chart")
                png = _png(fig)
                if png:
                    st.download_button("Download PNG", png, "analysis_chart.png", "image/png", key="sa_dl_png")
            else:
                st.dataframe(chart_df, use_container_width=True, hide_index=True)

        exp_c1, exp_c2 = st.columns(2)
        with exp_c1:
            csv_data = chart_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv_data, "analysis_data.csv", "text/csv", key="sa_dl_csv")
        with exp_c2:
            try:
                x_buf = io.BytesIO()
                with pd.ExcelWriter(x_buf, engine="openpyxl") as w:
                    chart_df.to_excel(w, index=False, sheet_name="Analysis")
                st.download_button(
                    "Download Excel", x_buf.getvalue(), "analysis_data.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="sa_dl_xlsx"
                )
            except Exception:
                pass

        next_map = {"Category": ("Sub-Category", "_std_category"), "Sub-Category": ("Product", "_std_sub_category"),
                    "Region": ("State", "_std_region"), "State": ("City", "_std_state"),
                    "Year": ("Quarter", None), "Quarter": ("Month", None), "Month": ("Day", None)}
        if group_choice in next_map and chart_df.shape[1] >= 1:
            nxt_label, src_col = next_map[group_choice]
            if nxt_label in (list(available_fields.keys()) + list(date_fields.keys())):
                pick = st.selectbox(f"Drill into {nxt_label}", chart_df.iloc[:, 0].astype(str).tolist(), key="sa_drill_pick")
                if st.button("Drill down", key="sa_do_drill"):
                    col = src_col or available_fields.get(group_choice)
                    path = list(st.session_state.get("sa_drill") or [])
                    path.append({"level": group_choice, "value": pick, "col": col})
                    st.session_state["sa_drill"] = path
                    st.session_state["sa_group"] = nxt_label
                    st.rerun()
    except Exception as e:
        st.error(f"Analysis could not be generated for this selection. {e}")


def _render_compare_tab(df, metrics, available_fields):
    st.markdown("### Date Period Comparison")
    if "_std_order_date" not in df.columns:
        st.info("Date comparison requires an order date field in the dataset.")
        return
    valid_dates = df["_std_order_date"].dropna()
    if valid_dates.empty:
        st.info("No valid dates found.")
        return

    min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
    years = sorted(int(y) for y in valid_dates.dt.year.unique())
    money_metrics = [m for m in metrics if m in MONEY_METRICS or m in ("Quantity", "Orders", "Sales", "Profit")]
    cmp_metric = st.selectbox("Metric", money_metrics, key="sa_cmp_metric")
    cmp_group = st.selectbox("Group By", ["None", "Month"] + list(available_fields.keys()), key="sa_cmp_group")
    cmp_mode = st.radio(
        "Comparison mode",
        ["Year vs Year", "Quarter vs Quarter", "Month vs Month", "Custom date ranges"],
        horizontal=True,
        key="sa_cmp_mode",
    )
    colors = COLOR_PRESETS["Default"]

    if cmp_mode == "Year vs Year":
        if len(years) < 2:
            st.info("Need at least two years in the dataset.")
            return
        c1, c2 = st.columns(2)
        with c1:
            year_a = st.selectbox("Period A (Year)", years, index=0, key="sa_yr_a")
        with c2:
            year_b = st.selectbox("Period B (Year)", years, index=min(1, len(years) - 1), key="sa_yr_b")
        if st.button("Compare", type="primary", key="sa_cmp_btn"):
            df_a = df[df["_std_order_date"].dt.year == year_a]
            df_b = df[df["_std_order_date"].dt.year == year_b]
            _render_period_comparison(df, df_a, df_b, str(year_a), str(year_b), cmp_metric, cmp_group, metrics, available_fields, colors)
    elif cmp_mode == "Month vs Month":
        months = list(range(1, 13))
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            m_a = st.selectbox("Month A", months, format_func=lambda m: labels[m - 1], key="sa_m_a")
        with c2:
            y_a = st.selectbox("Year A", years, key="sa_my_a")
        with c3:
            m_b = st.selectbox("Month B", months, format_func=lambda m: labels[m - 1], key="sa_m_b")
        with c4:
            y_b = st.selectbox("Year B", years, index=min(1, len(years) - 1), key="sa_my_b")
        if st.button("Compare months", type="primary", key="sa_cmp_month"):
            d = df["_std_order_date"]
            a = df[(d.dt.month == m_a) & (d.dt.year == y_a)]
            b = df[(d.dt.month == m_b) & (d.dt.year == y_b)]
            _render_period_comparison(df, a, b, f"{labels[m_a - 1]} {y_a}", f"{labels[m_b - 1]} {y_b}", cmp_metric, cmp_group, metrics, available_fields, colors)
    elif cmp_mode == "Quarter vs Quarter":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            q_a = st.selectbox("Quarter A", [1, 2, 3, 4], format_func=lambda q: f"Q{q}", key="sa_q_a")
        with c2:
            y_a = st.selectbox("Year A", years, key="sa_qy_a")
        with c3:
            q_b = st.selectbox("Quarter B", [1, 2, 3, 4], format_func=lambda q: f"Q{q}", key="sa_q_b")
        with c4:
            y_b = st.selectbox("Year B", years, index=min(1, len(years) - 1), key="sa_qy_b")
        if st.button("Compare quarters", type="primary", key="sa_cmp_q"):
            d = df["_std_order_date"]
            a = df[(d.dt.quarter == q_a) & (d.dt.year == y_a)]
            b = df[(d.dt.quarter == q_b) & (d.dt.year == y_b)]
            _render_period_comparison(df, a, b, f"Q{q_a} {y_a}", f"Q{q_b} {y_b}", cmp_metric, cmp_group, metrics, available_fields, colors)
    else:
        c1, c2 = st.columns(2)
        with c1:
            range_a = st.date_input("Period A", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="sa_range_a")
        with c2:
            range_b = st.date_input("Period B", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="sa_range_b")
        if st.button("Compare ranges", type="primary", key="sa_cmp_btn2"):
            if isinstance(range_a, (tuple, list)) and len(range_a) == 2 and isinstance(range_b, (tuple, list)) and len(range_b) == 2:
                df_a = df[(df["_std_order_date"].dt.date >= range_a[0]) & (df["_std_order_date"].dt.date <= range_a[1])]
                df_b = df[(df["_std_order_date"].dt.date >= range_b[0]) & (df["_std_order_date"].dt.date <= range_b[1])]
                _render_period_comparison(df, df_a, df_b, f"{range_a[0]} to {range_a[1]}", f"{range_b[0]} to {range_b[1]}", cmp_metric, cmp_group, metrics, available_fields, colors)


def _render_performers_tab(df, metrics, available_fields):
    st.markdown("### Top & Bottom Performers")
    if not available_fields:
        st.info("No grouping dimensions are available in this dataset.")
        return
    p1, p2, p3 = st.columns(3)
    with p1:
        perf_dim = st.selectbox("Dimension", list(available_fields.keys()), key="sa_perf_dim")
    with p2:
        perf_metric = st.selectbox("Metric", [m for m in metrics if m not in ["Profit Margin", "Average Order Value"]], key="sa_perf_metric")
    with p3:
        perf_n = st.selectbox("Show", [5, 10, 15, 20], index=1, key="sa_perf_n")

    dim_col = available_fields.get(perf_dim)
    met_col = metrics.get(perf_metric)
    if not dim_col or not met_col:
        return
    if perf_metric == "Orders":
        agg_df = df.groupby(dim_col)[met_col].nunique().reset_index()
    else:
        agg_df = df.groupby(dim_col)[met_col].sum().reset_index()
    agg_df.columns = [perf_dim, perf_metric]
    if perf_metric in MONEY_METRICS:
        agg_df[perf_metric] = convert_series_to_inr(agg_df[perf_metric])

    col_top, col_bottom = st.columns(2)
    with col_top:
        st.caption(f"Top {perf_n}")
        top_df = agg_df.sort_values(perf_metric, ascending=False).head(perf_n)
        fig_top = px.bar(top_df, x=perf_metric, y=perf_dim, orientation="h", color_discrete_sequence=[PALETTE[0]])
        _apply_dark_layout(fig_top, f"Top {perf_n} {perf_dim} by {perf_metric}", 350)
        fig_top.update_layout(yaxis=dict(autorange="reversed"))
        render_plotly(fig_top, key="sa_top_chart")
    with col_bottom:
        st.caption(f"Bottom {perf_n}")
        bottom_df = agg_df.sort_values(perf_metric, ascending=True).head(perf_n)
        fig_bot = px.bar(bottom_df, x=perf_metric, y=perf_dim, orientation="h", color_discrete_sequence=[PALETTE[5]])
        _apply_dark_layout(fig_bot, f"Bottom {perf_n} {perf_dim} by {perf_metric}", 350)
        render_plotly(fig_bot, key="sa_bottom_chart")


def _render_discount_tab(df, available_fields, has_discount, has_profit):
    st.markdown("### Discount vs Profit")
    if not has_discount or not has_profit:
        st.info("This analysis requires Discount and Profit fields in the dataset.")
        return
    color_by_opts = [k for k in available_fields if k in ["Category", "Sub-Category", "Region", "Segment"]]
    color_by = st.selectbox("Color by", ["None"] + color_by_opts, key="sa_disc_color")
    scatter_df = df.dropna(subset=["_std_discount", "_std_profit"]).copy()
    if len(scatter_df) > 2000:
        scatter_df = scatter_df.sample(2000, random_state=42)
    scatter_df["_profit_inr"] = convert_series_to_inr(scatter_df["_std_profit"])
    color_col = available_fields.get(color_by) if color_by != "None" else None
    hover = {c: True for c in ["_std_product_name", "_std_sales", "_std_discount"] if c in scatter_df.columns}
    fig_scatter = px.scatter(
        scatter_df, x="_std_discount", y="_profit_inr",
        color=color_col if color_col else None,
        color_discrete_sequence=PALETTE,
        hover_data=hover, opacity=0.6,
    )
    _apply_dark_layout(fig_scatter, "Discount vs Profit", 450)
    fig_scatter.update_xaxes(title="Discount", tickformat=".0%")
    fig_scatter.update_yaxes(title="Profit (₹)")
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    render_plotly(fig_scatter, key="sa_scatter_chart")

    loss_items = df[df["_std_profit"] < 0]
    if "_std_sub_category" in df.columns and len(loss_items):
        st.markdown("### Loss detection")
        sub_loss = df.groupby("_std_sub_category")["_std_profit"].sum()
        sub_loss = sub_loss[sub_loss < 0].sort_values()
        for name, val in sub_loss.head(6).items():
            st.markdown(
                f"""<div class="insight-box red"><div class="insight-desc">{name} generated a net loss of {format_inr(abs(val), compact=True)}.</div></div>""",
                unsafe_allow_html=True,
            )


def _build_analysis_data(df, metric, group, metrics, fields, date_fields):
    met_col = metrics.get(metric)
    if met_col is None:
        return None
    if group in date_fields and "_std_order_date" in df.columns:
        freq = date_fields[group]
        work_df = df.dropna(subset=["_std_order_date"]).copy()
        work_df["_grp"] = work_df["_std_order_date"].dt.to_period(freq).astype(str)
        grp_col = "_grp"
    elif group in fields:
        grp_col = fields[group]
        work_df = df.copy()
    else:
        return None

    if met_col == "_margin_":
        agg = work_df.groupby(grp_col).agg({"_std_sales": "sum", "_std_profit": "sum"}).reset_index()
        agg[metric] = (agg["_std_profit"] / agg["_std_sales"].replace(0, pd.NA) * 100).round(2)
        agg = agg.rename(columns={grp_col: group})
        return agg[[group, metric]]
    if met_col == "_aov_":
        agg = work_df.groupby(grp_col).agg({"_std_sales": "sum", "_std_order_id": "nunique"}).reset_index()
        agg[metric] = convert_series_to_inr(agg["_std_sales"] / agg["_std_order_id"].replace(0, pd.NA))
        agg = agg.rename(columns={grp_col: group})
        return agg[[group, metric]]
    if metric == "Orders":
        agg = work_df.groupby(grp_col)[met_col].nunique().reset_index()
        agg.columns = [group, metric]
        return agg
    agg = work_df.groupby(grp_col)[met_col].sum().reset_index()
    agg.columns = [group, metric]
    if metric in MONEY_METRICS:
        agg[metric] = convert_series_to_inr(agg[metric])
    return agg


def _build_chart(df, chart_type, metric, group, colors):
    x_col, y_col = group, metric
    if chart_type == "Bar":
        fig = px.bar(df, x=x_col, y=y_col, color_discrete_sequence=colors)
    elif chart_type == "Horizontal Bar":
        fig = px.bar(df, x=y_col, y=x_col, orientation="h", color_discrete_sequence=colors)
    elif chart_type == "Line":
        fig = px.line(df, x=x_col, y=y_col, color_discrete_sequence=colors, markers=True)
    elif chart_type == "Area":
        fig = px.area(df, x=x_col, y=y_col, color_discrete_sequence=colors)
    elif chart_type in ("Pie", "Donut"):
        fig = px.pie(df, names=x_col, values=y_col, hole=0.5 if chart_type == "Donut" else 0, color_discrete_sequence=colors)
    elif chart_type == "Treemap":
        fig = px.treemap(df, path=[x_col], values=y_col, color_discrete_sequence=colors)
    elif chart_type == "Scatter":
        fig = px.scatter(df, x=x_col, y=y_col, color_discrete_sequence=colors)
    elif chart_type == "Histogram":
        fig = px.histogram(df, x=y_col, color_discrete_sequence=colors)
    elif chart_type == "Combo":
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=metric, marker_color=colors[0], opacity=0.75))
        fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], name=f"{metric} trend", line=dict(color=colors[min(1, len(colors)-1)], width=2)))
    else:
        fig = px.bar(df, x=x_col, y=y_col, color_discrete_sequence=colors)
    _apply_dark_layout(fig, f"{metric} by {group}", 420)
    return fig


def _period_kpis(label, val, metric, subtitle):
    display = format_inr(val, compact=True, convert=metric in MONEY_METRICS) if metric in MONEY_METRICS else f"{val:,.0f}"
    if metric in MONEY_METRICS:
        display = format_inr(val, compact=True)
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-title">{label}</div>
        <div class="kpi-value">{display}</div>
        <div class="kpi-meta">{subtitle}</div></div>""",
        unsafe_allow_html=True,
    )


def _render_period_comparison(df, df_a, df_b, label_a, label_b, metric, group, metrics, fields, colors):
    met_col = metrics.get(metric)
    if df_a is None or df_b is None or df_a.empty or df_b.empty:
        st.info("Insufficient data in one or both of the selected periods.")
        return

    if group == "None":
        _render_range_totals(df_a, df_b, metric, met_col, label_a, label_b)
        return

    if group == "Month":
        df_a = df_a.copy()
        df_b = df_b.copy()
        df_a["_grp"] = df_a["_std_order_date"].dt.month_name()
        df_b["_grp"] = df_b["_std_order_date"].dt.month_name()
        grp_col = "_grp"
    else:
        grp_col = fields.get(group)
        if not grp_col or grp_col not in df_a.columns or grp_col not in df_b.columns:
            _render_range_totals(df_a, df_b, metric, met_col, label_a, label_b)
            return

    how = "nunique" if metric == "Orders" else "sum"
    agg_a = df_a.groupby(grp_col)[met_col].agg(how).reset_index()
    agg_a.columns = [group, label_a]
    agg_b = df_b.groupby(grp_col)[met_col].agg(how).reset_index()
    agg_b.columns = [group, label_b]
    merged = agg_a.merge(agg_b, on=group, how="outer").fillna(0)

    merged["Difference"] = merged[label_b] - merged[label_a]
    merged["% Change"] = np.where(
        merged[label_a] != 0,
        ((merged[label_b] - merged[label_a]) / merged[label_a].abs() * 100).round(1),
        np.where(merged[label_b] != 0, 100.0, 0.0)
    )

    plot_merged = merged.copy()
    if metric in MONEY_METRICS:
        plot_merged[label_a] = convert_series_to_inr(plot_merged[label_a])
        plot_merged[label_b] = convert_series_to_inr(plot_merged[label_b])
        plot_merged["Difference"] = convert_series_to_inr(plot_merged["Difference"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=plot_merged[group], y=plot_merged[label_a], name=label_a,
        marker_color=colors[0],
        hovertemplate="%{x}<br>" + label_a + ": " + ("₹%{y:,.0f}" if metric in MONEY_METRICS else "%{y:,.0f}") + "<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=plot_merged[group], y=plot_merged[label_b], name=label_b,
        marker_color=PALETTE[1],
        hovertemplate="%{x}<br>" + label_b + ": " + ("₹%{y:,.0f}" if metric in MONEY_METRICS else "%{y:,.0f}") + "<extra></extra>",
    ))
    _apply_dark_layout(fig, f"{metric} Comparison by {group}: {label_a} vs {label_b}", 400)
    fig.update_layout(barmode="group")
    render_plotly(fig, key="sa_comparison_chart")

    # Detailed table breakdown
    st.markdown("#### Comparison Breakdown")
    table_df = plot_merged.copy()
    if metric in MONEY_METRICS:
        table_df[label_a] = table_df[label_a].apply(lambda v: format_inr(v, convert=False))
        table_df[label_b] = table_df[label_b].apply(lambda v: format_inr(v, convert=False))
        table_df["Difference"] = table_df["Difference"].apply(lambda v: format_inr(v, convert=False))
    else:
        table_df[label_a] = table_df[label_a].apply(lambda v: f"{v:,.0f}")
        table_df[label_b] = table_df[label_b].apply(lambda v: f"{v:,.0f}")
        table_df["Difference"] = table_df["Difference"].apply(lambda v: f"{v:,.0f}")
    table_df["% Change"] = table_df["% Change"].apply(lambda v: f"{v:+.1f}%")
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    d_c1, d_c2 = st.columns(2)
    with d_c1:
        st.download_button("Download Comparison CSV", merged.to_csv(index=False).encode("utf-8"), "comparison_data.csv", "text/csv", key="sa_cmp_dl_csv")
    with d_c2:
        try:
            x_buf = io.BytesIO()
            with pd.ExcelWriter(x_buf, engine="openpyxl") as w:
                merged.to_excel(w, index=False, sheet_name="Comparison")
            st.download_button("Download Comparison Excel", x_buf.getvalue(), "comparison_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="sa_cmp_dl_xlsx")
        except Exception:
            pass


def _render_range_totals(df_a, df_b, metric, met_col, label_a, label_b):
    if metric == "Orders":
        val_a = float(df_a[met_col].nunique()) if met_col in df_a.columns else 0
        val_b = float(df_b[met_col].nunique()) if met_col in df_b.columns else 0
    else:
        val_a = float(df_a[met_col].sum()) if met_col in df_a.columns else 0
        val_b = float(df_b[met_col].sum()) if met_col in df_b.columns else 0
    diff = val_b - val_a
    change = ((val_b - val_a) / abs(val_a) * 100) if val_a != 0 else (100.0 if val_b != 0 else 0.0)
    c1, c2, c3 = st.columns(3)
    with c1:
        _period_kpis("Period A", val_a, metric, label_a)
    with c2:
        _period_kpis("Period B", val_b, metric, label_b)
    with c3:
        pill = "positive" if change >= 0 else "negative"
        arrow = "↑" if change >= 0 else "↓"
        diff_str = format_inr(diff) if metric in MONEY_METRICS else f"{diff:+,.0f}"
        st.markdown(
            f"""<div class="kpi-card"><div class="kpi-title">Change</div>
            <div class="kpi-value"><span class="kpi-pill {pill}">{arrow} {abs(change):.1f}%</span></div>
            <div class="kpi-meta">Diff: {diff_str}</div></div>""",
            unsafe_allow_html=True,
        )
    fig = go.Figure()
    ya = convert_to_inr(val_a) if metric in MONEY_METRICS else val_a
    yb = convert_to_inr(val_b) if metric in MONEY_METRICS else val_b
    fig.add_trace(go.Bar(x=[label_a, label_b], y=[ya, yb], marker_color=["#00D4FF", "#22C55E"], name=metric))
    _apply_dark_layout(fig, f"{metric} Comparison: {label_a} vs {label_b}", 320)
    render_plotly(fig, key="sa_range_cmp_chart")
