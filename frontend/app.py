"""
frontend/app.py
Main application entry point for the redesigned Sales Performance Dashboard.
Features:
- Left Sidebar with Dataset Upload & Pipeline Execution
- 3 Primary Views: Dashboard (Default), Data Quality, AI Insights / Assistant
- Interactive Left Control Panel Filters (Date, Region, Category, Sub-Category, Segment)
- Real-time recalculation of KPIs, charts, and assistant context across all views
- 100% Indian Rupee (₹) monetary formatting
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

from backend.pipeline import run_full_pipeline
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

# Load CSS Stylesheet
css_path = Path(__file__).parent / "styles" / "main.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def initialize_session():
    """Initializes session state and executes initial pipeline on reference dataset."""
    if "pipeline_result" not in st.session_state or st.session_state["pipeline_result"] is None:
        sample_path = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
        if sample_path.exists():
            res = run_full_pipeline(str(sample_path), file_name="SuperStore_Sales_Dataset.csv")
            if res["success"]:
                st.session_state["pipeline_result"] = res
                st.session_state["dataset_name"] = "SuperStore_Sales_Dataset.csv"
                st.session_state["raw_df"] = res["raw_df"]
                st.session_state["clean_df"] = res["clean_df"]
                st.session_state["mapping"] = res["mapping"]
                st.session_state["pipeline_steps"] = res["pipeline_steps"]


def main():
    initialize_session()

    # --- SIDEBAR HEADER & NAVIGATION ---
    st.sidebar.markdown("## 📈 Sales Performance")
    
    selected_view = st.sidebar.radio(
        "Navigation",
        options=["Dashboard", "Data Quality", "AI Insights / Assistant"],
        index=0,
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    # --- SIDEBAR: DATASET UPLOAD (CORE FEATURE) ---
    st.sidebar.markdown("### 📁 Dataset")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload sales file",
        type=["csv", "xlsx", "xls", "tsv"],
        help="Upload CSV, Excel, or TSV sales spreadsheet"
    )

    current_name = st.session_state.get("dataset_name", "SuperStore_Sales_Dataset.csv")
    file_size_str = ""

    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        file_size_str = f"({file_size_mb:.2f} MB)"
        st.sidebar.caption(f"Selected: **{uploaded_file.name}** {file_size_str}")

        if st.sidebar.button("📥 Load Dataset", type="primary", use_container_width=True):
            with st.spinner("Processing uploaded dataset through 12-step pipeline..."):
                pipe_res = run_full_pipeline(uploaded_file, file_name=uploaded_file.name)
                if pipe_res["success"]:
                    st.session_state["pipeline_result"] = pipe_res
                    st.session_state["dataset_name"] = uploaded_file.name
                    st.session_state["raw_df"] = pipe_res["raw_df"]
                    st.session_state["clean_df"] = pipe_res["clean_df"]
                    st.session_state["mapping"] = pipe_res["mapping"]
                    st.session_state["pipeline_steps"] = pipe_res["pipeline_steps"]
                    # Reset any active filters
                    for k in ["flt_date", "flt_regions", "flt_cats", "flt_subcats", "flt_segs"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.sidebar.success("Dataset successfully loaded and verified!")
                    st.rerun()
                else:
                    st.sidebar.error(f"Error: {pipe_res['error']}")
    else:
        st.sidebar.caption(f"Active: **{current_name}**")

    # Show small Data Processing Status in Sidebar
    steps = st.session_state.get("pipeline_steps", [])
    if steps:
        with st.sidebar.expander("⚡ Pipeline Status", expanded=False):
            for step in steps:
                st.markdown(f"<span class='pipeline-check'>{step}</span>", unsafe_allow_html=True)

    clean_df = st.session_state.get("clean_df")
    raw_df = st.session_state.get("raw_df")
    mapping = st.session_state.get("mapping", {})

    filtered_df = clean_df.copy() if clean_df is not None else None

    # --- SIDEBAR: FILTER BAR ---
    if clean_df is not None and selected_view in ["Dashboard", "AI Insights / Assistant"]:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Filter Controls")

        # 1. Date Range Filter
        if "_std_order_date" in clean_df.columns:
            valid_dates = clean_df["_std_order_date"].dropna()
            if len(valid_dates) > 0:
                min_d = valid_dates.min().date()
                max_d = valid_dates.max().date()

                date_choice = st.sidebar.date_input(
                    "Date Range",
                    value=(min_d, max_d),
                    min_value=min_d,
                    max_value=max_d,
                    key="flt_date"
                )

                if isinstance(date_choice, (tuple, list)) and len(date_choice) == 2:
                    start_d, end_d = date_choice
                    filtered_df = filtered_df[
                        (filtered_df["_std_order_date"].dt.date >= start_d) &
                        (filtered_df["_std_order_date"].dt.date <= end_d)
                    ]

        # 2. Region Filter
        if "_std_region" in clean_df.columns:
            reg_opts = sorted([str(r) for r in clean_df["_std_region"].dropna().unique()])
            sel_regions = st.sidebar.multiselect("Region", options=reg_opts, key="flt_regions")
            if sel_regions:
                filtered_df = filtered_df[filtered_df["_std_region"].isin(sel_regions)]

        # 3. Category Filter
        if "_std_category" in clean_df.columns:
            cat_opts = sorted([str(c) for c in clean_df["_std_category"].dropna().unique()])
            sel_cats = st.sidebar.multiselect("Category", options=cat_opts, key="flt_cats")
            if sel_cats:
                filtered_df = filtered_df[filtered_df["_std_category"].isin(sel_cats)]

        # 4. Sub-Category Filter (Cascaded)
        if "_std_sub_category" in filtered_df.columns:
            subcat_opts = sorted([str(sc) for sc in filtered_df["_std_sub_category"].dropna().unique()])
            sel_subcats = st.sidebar.multiselect("Sub-Category", options=subcat_opts, key="flt_subcats")
            if sel_subcats:
                filtered_df = filtered_df[filtered_df["_std_sub_category"].isin(sel_subcats)]

        # 5. Customer Segment Filter
        if "_std_segment" in clean_df.columns:
            seg_opts = sorted([str(s) for s in clean_df["_std_segment"].dropna().unique()])
            sel_segs = st.sidebar.multiselect("Customer Segment", options=seg_opts, key="flt_segs")
            if sel_segs:
                filtered_df = filtered_df[filtered_df["_std_segment"].isin(sel_segs)]

        # 6. Reset Filters Button
        if st.sidebar.button("🔄 Reset Filters", use_container_width=True):
            for k in ["flt_date", "flt_regions", "flt_cats", "flt_subcats", "flt_segs"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # --- MAIN VIEW ROUTER ---
    if selected_view == "Dashboard":
        render_dashboard_view(filtered_df, dataset_name=st.session_state.get("dataset_name", "SuperStore_Sales_Dataset.csv"))

    elif selected_view == "Data Quality":
        render_data_quality_view(raw_df, clean_df, mapping)

    elif selected_view == "AI Insights / Assistant":
        render_ai_insights_view(filtered_df)


if __name__ == "__main__":
    main()
