"""
frontend/app.py
Main Streamlit application entry point.
Implements a simple, professional 3-view navigation:
1. Dashboard (Default)
2. Data Quality
3. AI Insights
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
import pandas as pd

from backend.file_handling.loader import load_dataset
from backend.column_mapping.detector import auto_detect_columns
from backend.cleaning.quality import clean_and_normalize_data
from frontend.views.dashboard_view import render_dashboard_view
from frontend.views.data_quality_view import render_data_quality_view
from frontend.views.ai_insights_view import render_ai_insights_view

# Page Configuration
st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load clean minimal CSS
css_path = Path(__file__).parent / "styles" / "main.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_initial_data():
    """Loads default reference dataset if not already in session state."""
    if "clean_df" not in st.session_state or st.session_state["clean_df"] is None:
        sample_path = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
        if sample_path.exists():
            raw_df, err = load_dataset(str(sample_path), file_name="SuperStore_Sales_Dataset.csv")
            if raw_df is not None:
                mapping = auto_detect_columns(raw_df)
                clean_df, _ = clean_and_normalize_data(raw_df, mapping)
                st.session_state["raw_df"] = raw_df
                st.session_state["clean_df"] = clean_df
                st.session_state["mapping"] = mapping
                st.session_state["dataset_name"] = "SuperStore Reference Dataset"


def on_dataset_updated(raw_df: pd.DataFrame, clean_df: pd.DataFrame, mapping: dict, name: str):
    """Callback when user uploads a new dataset."""
    st.session_state["raw_df"] = raw_df
    st.session_state["clean_df"] = clean_df
    st.session_state["mapping"] = mapping
    st.session_state["dataset_name"] = name


def main():
    load_initial_data()

    # --- SIDEBAR NAVIGATION (Strictly 3 items) ---
    st.sidebar.markdown("## 📈 Sales Analytics")
    
    selected_view = st.sidebar.radio(
        "Navigation",
        options=["Dashboard", "Data Quality", "AI Insights"],
        index=0,
        label_visibility="collapsed"
    )

    clean_df = st.session_state.get("clean_df")
    raw_df = st.session_state.get("raw_df")
    mapping = st.session_state.get("mapping", {})

    filtered_df = clean_df.copy() if clean_df is not None else None

    # --- SIDEBAR FILTERS (Only shown when viewing Dashboard) ---
    if selected_view == "Dashboard" and clean_df is not None:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Filter Bar")

        # 1. Date Range Filter
        if "_std_order_date" in clean_df.columns:
            valid_dates = clean_df["_std_order_date"].dropna()
            if len(valid_dates) > 0:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()

                date_val = st.sidebar.date_input(
                    "Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="sidebar_date_range"
                )

                if isinstance(date_val, (tuple, list)) and len(date_val) == 2:
                    d_start, d_end = date_val
                    filtered_df = filtered_df[
                        (filtered_df["_std_order_date"].dt.date >= d_start) &
                        (filtered_df["_std_order_date"].dt.date <= d_end)
                    ]

        # 2. Region Filter
        if "_std_region" in clean_df.columns:
            region_list = sorted([str(r) for r in clean_df["_std_region"].dropna().unique()])
            chosen_regions = st.sidebar.multiselect(
                "Region",
                options=region_list,
                default=[],
                key="sidebar_regions"
            )
            if chosen_regions:
                filtered_df = filtered_df[filtered_df["_std_region"].isin(chosen_regions)]

        # 3. Category Filter
        if "_std_category" in clean_df.columns:
            cat_list = sorted([str(c) for c in clean_df["_std_category"].dropna().unique()])
            chosen_cats = st.sidebar.multiselect(
                "Category",
                options=cat_list,
                default=[],
                key="sidebar_categories"
            )
            if chosen_cats:
                filtered_df = filtered_df[filtered_df["_std_category"].isin(chosen_cats)]

        # 4. Optional Segment Filter
        if "_std_segment" in clean_df.columns:
            seg_list = sorted([str(s) for s in clean_df["_std_segment"].dropna().unique()])
            chosen_segs = st.sidebar.multiselect(
                "Customer Segment",
                options=seg_list,
                default=[],
                key="sidebar_segments"
            )
            if chosen_segs:
                filtered_df = filtered_df[filtered_df["_std_segment"].isin(chosen_segs)]

        # 5. Reset Filters Action
        if st.sidebar.button("🔄 Reset Filters", use_container_width=True):
            for k in ["sidebar_date_range", "sidebar_regions", "sidebar_categories", "sidebar_segments"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # --- MAIN VIEW ROUTING ---
    if selected_view == "Dashboard":
        render_dashboard_view(filtered_df, currency_symbol="$")

    elif selected_view == "Data Quality":
        render_data_quality_view(raw_df, mapping, on_update_callback=on_dataset_updated)

    elif selected_view == "AI Insights":
        render_ai_insights_view(clean_df, currency_symbol="$")


if __name__ == "__main__":
    main()
