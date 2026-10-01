"""
frontend/pages/guided_analysis.py
Guided interactive analysis builder allowing users to select questions,
measures, groupings, chart formats, and export results.
Strictly implements PRD Section 2.1, 4.3, and 4.4.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from frontend.components.charts import PALETTE, _apply_standard_layout


def render_guided_analysis_page(df: pd.DataFrame, meta: Dict[str, Any]):
    """Renders the query and visual builder."""
    st.markdown("## 🔍 Guided Analysis & Visual Builder")
    st.markdown(
        "Build custom analytical queries by choosing your measure, dimension grouping, "
        "ranking, and visual presentation format."
    )

    sym = meta.get("currency_symbol", "$")

    if df is None or len(df) == 0:
        st.warning("No data loaded. Please upload a dataset or load the reference sample.")
        return

    # 1. Builder Controls
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        # Measure
        measure_options = []
        if "_std_sales" in df.columns:
            measure_options.append("Sales")
        if "_std_profit" in df.columns:
            measure_options.append("Profit")
        if "_std_quantity" in df.columns:
            measure_options.append("Quantity")
        if "_std_order_id" in df.columns:
            measure_options.append("Distinct Orders")

        measure = st.selectbox("1. Select Measure", options=measure_options, index=0)

    with c2:
        # Dimension
        dimension_map = {
            "Category": "_std_category",
            "Sub-Category": "_std_sub_category",
            "Region": "_std_region",
            "State": "_std_state",
            "City": "_std_city",
            "Customer Segment": "_std_segment",
            "Ship Mode": "_std_ship_mode",
            "Product": "_std_product_name",
        }
        avail_dims = {k: v for k, v in dimension_map.items() if v in df.columns}
        dimension_name = st.selectbox("2. Group by Dimension", options=list(avail_dims.keys()), index=0)
        dim_col = avail_dims[dimension_name]

    with c3:
        # Ranking / Slice
        ranking_choice = st.selectbox(
            "3. Ranking / Limit",
            options=["Top 10", "Top 5", "Top 20", "Bottom 5", "Bottom 10", "All Items"],
            index=0
        )

    with c4:
        # Chart Chooser (PRD Section 4.3)
        chart_types = ["Bar Chart", "Line Chart", "Donut Chart", "Treemap", "Data Table"]
        chart_format = st.selectbox("4. Result Format", options=chart_types, index=0)

    # 2. Perform Grouping
    measure_col_map = {
        "Sales": "_std_sales",
        "Profit": "_std_profit",
        "Quantity": "_std_quantity",
        "Distinct Orders": "_std_order_id",
    }
    meas_col = measure_col_map[measure]

    if meas_col == "_std_order_id":
        grouped = df.groupby(dim_col, as_index=False)[meas_col].nunique()
    else:
        grouped = df.groupby(dim_col, as_index=False)[meas_col].sum()

    grouped = grouped.rename(columns={dim_col: dimension_name, meas_col: measure})

    # Ranking logic
    if ranking_choice == "Top 5":
        grouped = grouped.sort_values(measure, ascending=False).head(5)
    elif ranking_choice == "Top 10":
        grouped = grouped.sort_values(measure, ascending=False).head(10)
    elif ranking_choice == "Top 20":
        grouped = grouped.sort_values(measure, ascending=False).head(20)
    elif ranking_choice == "Bottom 5":
        grouped = grouped.sort_values(measure, ascending=True).head(5)
    elif ranking_choice == "Bottom 10":
        grouped = grouped.sort_values(measure, ascending=True).head(10)
    else:
        grouped = grouped.sort_values(measure, ascending=False)

    # 3. Render Visual Result on Main Canvas
    st.markdown(f"### Results: {measure} by {dimension_name} ({ranking_choice})")

    if chart_format == "Bar Chart":
        fig = px.bar(
            grouped,
            x=dimension_name,
            y=measure,
            color=measure,
            color_continuous_scale="Blues",
            text_auto=".2s"
        )
        _apply_standard_layout(fig, title=f"{measure} by {dimension_name}")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_format == "Line Chart":
        fig = px.line(
            grouped,
            x=dimension_name,
            y=measure,
            markers=True
        )
        _apply_standard_layout(fig, title=f"{measure} by {dimension_name}")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_format == "Donut Chart":
        fig = px.pie(
            grouped,
            names=dimension_name,
            values=measure,
            hole=0.5
        )
        _apply_standard_layout(fig, title=f"Distribution of {measure} by {dimension_name}")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_format == "Treemap":
        fig = px.treemap(
            grouped,
            path=[dimension_name],
            values=measure
        )
        _apply_standard_layout(fig, title=f"Treemap: {measure} by {dimension_name}")
        st.plotly_chart(fig, use_container_width=True)

    # 4. Accompanying Data Table (PRD Section 4.4)
    st.markdown("#### Aggregate Data Table")
    formatted_grouped = grouped.copy()
    if measure in ["Sales", "Profit"]:
        formatted_grouped[measure] = formatted_grouped[measure].apply(lambda x: f"{sym}{x:,.2f}")
    elif measure in ["Quantity", "Distinct Orders"]:
        formatted_grouped[measure] = formatted_grouped[measure].apply(lambda x: f"{x:,.0f}")

    st.dataframe(formatted_grouped, use_container_width=True)

    # Export Slice
    csv_slice = grouped.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"📥 Download {measure} by {dimension_name} (CSV)",
        data=csv_slice,
        file_name=f"{measure}_{dimension_name}.csv",
        mime="text/csv"
    )
