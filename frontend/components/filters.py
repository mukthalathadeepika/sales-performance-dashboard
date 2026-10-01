"""
frontend/components/filters.py
Sidebar and control bar filter component supporting dynamic fields,
date pickers, sales targets, currency selection, and one-click reset.
Strictly conforms to PRD Section 2.3 and 4.4.
"""

from typing import Dict, Any, Tuple
import streamlit as st
import pandas as pd


def render_sidebar_controls(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Renders filter controls dynamically based on available columns in the DataFrame.
    Returns (filtered_dataframe, active_filter_metadata).
    """
    st.sidebar.markdown("### ⚙️ Dashboard Controls")

    # 1. Reset Filters Button (PRD Section 2.3 & 4.4)
    if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("filter_"):
                del st.session_state[key]
        st.rerun()

    active_meta = {
        "currency_symbol": "$",
        "sales_target": None,
        "date_range": None,
        "selected_regions": [],
        "selected_categories": [],
        "selected_segments": [],
        "selected_states": [],
    }

    filtered_df = df.copy()

    # 2. Currency Selector (PRD Section 6.1)
    currency = st.sidebar.selectbox(
        "Currency Display",
        options=["$", "€", "£", "₹", "¥", "None"],
        index=0,
        key="filter_currency"
    )
    active_meta["currency_symbol"] = "" if currency == "None" else currency

    # 3. User-Entered Sales Target (PRD Section 4.4)
    default_target = 0.0
    if "_std_sales" in df.columns:
        default_target = float(round(df["_std_sales"].sum(), -3))
    
    use_target = st.sidebar.checkbox("Set Sales Target", value=False, key="filter_use_target")
    if use_target:
        sales_target = st.sidebar.number_input(
            "Sales Target Amount",
            min_value=0.0,
            value=default_target,
            step=50000.0,
            key="filter_target_val"
        )
        active_meta["sales_target"] = sales_target

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filters")

    # 4. Date Range Filter (only if usable date field exists per PRD 2.3)
    if "_std_order_date" in df.columns:
        valid_dates = df["_std_order_date"].dropna()
        if len(valid_dates) > 0:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            date_range = st.sidebar.date_input(
                "Order Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="filter_date_range"
            )

            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
                start_date, end_date = date_range
                active_meta["date_range"] = (start_date, end_date)
                mask = (
                    (filtered_df["_std_order_date"].dt.date >= start_date) &
                    (filtered_df["_std_order_date"].dt.date <= end_date)
                )
                filtered_df = filtered_df[mask]

    # 5. Region Filter
    if "_std_region" in df.columns:
        regions = sorted([str(r) for r in df["_std_region"].dropna().unique()])
        sel_regions = st.sidebar.multiselect("Region", options=regions, key="filter_region")
        if sel_regions:
            active_meta["selected_regions"] = sel_regions
            filtered_df = filtered_df[filtered_df["_std_region"].isin(sel_regions)]

    # 6. Category Filter
    if "_std_category" in df.columns:
        categories = sorted([str(c) for c in df["_std_category"].dropna().unique()])
        sel_categories = st.sidebar.multiselect("Category", options=categories, key="filter_category")
        if sel_categories:
            active_meta["selected_categories"] = sel_categories
            filtered_df = filtered_df[filtered_df["_std_category"].isin(sel_categories)]

    # 7. Sub-Category Filter (cascaded from Category if selected)
    if "_std_sub_category" in filtered_df.columns:
        sub_cats = sorted([str(sc) for sc in filtered_df["_std_sub_category"].dropna().unique()])
        sel_subcats = st.sidebar.multiselect("Sub-Category", options=sub_cats, key="filter_sub_category")
        if sel_subcats:
            filtered_df = filtered_df[filtered_df["_std_sub_category"].isin(sel_subcats)]

    # 8. Customer Segment Filter
    if "_std_segment" in df.columns:
        segments = sorted([str(s) for s in df["_std_segment"].dropna().unique()])
        sel_segments = st.sidebar.multiselect("Customer Segment", options=segments, key="filter_segment")
        if sel_segments:
            active_meta["selected_segments"] = sel_segments
            filtered_df = filtered_df[filtered_df["_std_segment"].isin(sel_segments)]

    # 9. State Filter
    if "_std_state" in filtered_df.columns:
        states = sorted([str(st_val) for st_val in filtered_df["_std_state"].dropna().unique()])
        sel_states = st.sidebar.multiselect("State", options=states, key="filter_state")
        if sel_states:
            active_meta["selected_states"] = sel_states
            filtered_df = filtered_df[filtered_df["_std_state"].isin(sel_states)]

    return filtered_df, active_meta
