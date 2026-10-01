"""
frontend/app.py
Main Streamlit application entry point for Sales Performance Dashboard.
Coordinates navigation, session state, dynamic filters, and views.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path to enable smooth imports
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
import pandas as pd

from backend.file_handling.loader import load_dataset
from backend.column_mapping.detector import auto_detect_columns
from backend.cleaning.quality import clean_and_normalize_data
from frontend.components.filters import render_sidebar_controls
from frontend.pages.home import render_home_page
from frontend.pages.dashboard import render_dashboard_page
from frontend.pages.guided_analysis import render_guided_analysis_page
from frontend.pages.automatic_overview import render_automatic_overview_page
from frontend.pages.chat_view import render_chat_page
from frontend.pages.data_quality import render_data_quality_page

# Page Configuration
st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
css_path = Path(__file__).parent / "styles" / "main.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def init_session_state():
    """Initializes session state variables and loads default sample if not present."""
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Home"

    # Check if sample needs to be loaded automatically
    if "raw_df" not in st.session_state or st.session_state.get("load_sample_trigger"):
        sample_path = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
        if sample_path.exists():
            raw_df, err = load_dataset(str(sample_path), file_name="SuperStore_Sales_Dataset.csv")
            if raw_df is not None:
                mapping = auto_detect_columns(raw_df)
                clean_df, exclusions = clean_and_normalize_data(raw_df, mapping)
                st.session_state["raw_df"] = raw_df
                st.session_state["clean_df"] = clean_df
                st.session_state["mapping"] = mapping
                st.session_state["dataset_name"] = "SuperStore Reference Dataset"
                st.session_state["load_sample_trigger"] = False


def update_dataset(raw_df: pd.DataFrame, clean_df: pd.DataFrame, mapping: dict, name: str):
    """Callback to update active dataset in session state."""
    st.session_state["raw_df"] = raw_df
    st.session_state["clean_df"] = clean_df
    st.session_state["mapping"] = mapping
    st.session_state["dataset_name"] = name


def main():
    init_session_state()

    # Top App Header
    current_name = st.session_state.get("dataset_name", "No dataset")
    total_records = len(st.session_state["clean_df"]) if "clean_df" in st.session_state else 0

    st.markdown(f"""
    <div class="app-header-container">
        <div class="app-title-group">
            <h1>📈 Sales Performance Dashboard</h1>
            <div class="app-subtitle">Active Data: <b>{current_name}</b> ({total_records:,} records)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top Navigation Bar
    nav_options = [
        "Home",
        "Dashboard",
        "Guided Analysis",
        "Automatic Overview",
        "Ask in Chat",
        "Data Quality & Mapping"
    ]

    selected_page = st.radio(
        "Navigation",
        options=nav_options,
        index=nav_options.index(st.session_state["nav_page"]) if st.session_state["nav_page"] in nav_options else 0,
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state["nav_page"] = selected_page

    st.markdown("<hr style='border: none; border-top: 1px solid #E2E8F0; margin: 0.8rem 0 1.5rem 0;'>", unsafe_allow_html=True)

    clean_df = st.session_state.get("clean_df")
    raw_df = st.session_state.get("raw_df")
    mapping = st.session_state.get("mapping", {})

    # Show filters in sidebar for analytical pages
    if selected_page in ["Dashboard", "Guided Analysis", "Automatic Overview"] and clean_df is not None:
        filtered_df, meta = render_sidebar_controls(clean_df)
    else:
        filtered_df = clean_df
        meta = {"currency_symbol": "$"}

    # Route to Selected Page
    if selected_page == "Home":
        render_home_page()

    elif selected_page == "Dashboard":
        if clean_df is not None:
            render_dashboard_page(filtered_df, meta, full_df=clean_df)
        else:
            st.warning("Please load or upload a dataset first.")

    elif selected_page == "Guided Analysis":
        if clean_df is not None:
            render_guided_analysis_page(filtered_df, meta)
        else:
            st.warning("Please load or upload a dataset first.")

    elif selected_page == "Automatic Overview":
        if clean_df is not None:
            render_automatic_overview_page(filtered_df, meta)
        else:
            st.warning("Please load or upload a dataset first.")

    elif selected_page == "Ask in Chat":
        if clean_df is not None:
            render_chat_page(clean_df, meta)
        else:
            st.warning("Please load or upload a dataset first.")

    elif selected_page == "Data Quality & Mapping":
        render_data_quality_page(raw_df, mapping, on_update_callback=update_dataset)


if __name__ == "__main__":
    main()
