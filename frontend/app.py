"""
frontend/app.py
Sales Analytics Platform — main entry point.
Production architecture strictly adhering to:
- 3 primary navigation sections (Dashboard, Sales Analysis, AI Sales Assistant)
- Dataset-driven cascading filter engine with Apply / Reset workflow
- Universal Indian Rupee (₹) currency engine
- Dynamic dataset adaptation for CSV, XLSX, XLS, and TSV formats
"""

import sys
import io
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
import pandas as pd

from backend.pipeline import run_full_pipeline
from backend.analytics.currency import set_exchange_rate, get_exchange_rate, get_source_currency
from frontend.views.dashboard_view import render_dashboard_view
from frontend.views.sales_analysis_view import render_sales_analysis_view
from frontend.views.ai_assistant_view import render_ai_assistant_view

st.set_page_config(
    page_title="Sales Analytics Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

css_path = Path(__file__).parent / "styles" / "main.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

st.markdown(
    """<style>
[data-testid="stDeployButton"], .stDeployButton, .stAppDeployButton,
div[class*="stAppDeployButton"], button[kind="header"],
[data-testid="stToolbar"] {display:none!important;visibility:hidden!important}
#MainMenu {visibility:hidden!important}
header [data-testid="stHeader"] {background:transparent!important}
</style>""",
    unsafe_allow_html=True,
)

WIDGET_PREFIXES = ("flt_", "sa_", "ai_", "dash_", "cfg_")
CLEAR_KEYS = {
    "pipeline_result", "dataset_name", "raw_df", "clean_df", "mapping",
    "pipeline_steps", "chat_history", "chat_context", "sa_last_generated",
    "sales_chat_history", "drill_path", "loaded_upload_token", "active_filters",
}


def _clear_all_state(preserve=None):
    """Clear dataset-derived session state. Does not delete files on disk."""
    preserve = set(preserve or [])
    keys = set(CLEAR_KEYS)
    for k in list(st.session_state.keys()):
        if any(k.startswith(p) for p in WIDGET_PREFIXES) or k in CLEAR_KEYS:
            keys.add(k)
    for k in keys:
        if k in preserve:
            continue
        if k in st.session_state:
            del st.session_state[k]


def _load_default_dataset():
    if st.session_state.get("pipeline_result") is not None:
        return
    if st.session_state.get("skip_default_dataset"):
        return
    sample = Path(ROOT_DIR) / "data" / "sample" / "SuperStore_Sales_Dataset.csv"
    if sample.exists():
        res = run_full_pipeline(str(sample), file_name="SuperStore_Sales_Dataset.csv")
        if res.get("success"):
            _store_pipeline_result(res, "SuperStore_Sales_Dataset.csv")


def _store_pipeline_result(res, name):
    _clear_all_state()
    st.session_state["pipeline_result"] = res
    st.session_state["dataset_name"] = name
    st.session_state["raw_df"] = res["raw_df"]
    st.session_state["clean_df"] = res["clean_df"]
    st.session_state["mapping"] = res.get("mapping", {})
    st.session_state["pipeline_steps"] = res.get("pipeline_steps", [])
    st.session_state["skip_default_dataset"] = False
    st.session_state["active_filters"] = {}


def _apply_filters(df):
    """Filters df using criteria stored in active_filters."""
    if df is None:
        return None
    filtered = df.copy()
    active_filters = st.session_state.get("active_filters", {})
    if not active_filters:
        return filtered

    # Date Filters
    if "_std_order_date" in filtered.columns and "date_range" in active_filters:
        dr = active_filters["date_range"]
        if isinstance(dr, (tuple, list)) and len(dr) == 2:
            filtered = filtered[
                (filtered["_std_order_date"].dt.date >= dr[0])
                & (filtered["_std_order_date"].dt.date <= dr[1])
            ]
    if "_std_order_date" in filtered.columns:
        if active_filters.get("years"):
            filtered = filtered[filtered["_std_order_date"].dt.year.isin(active_filters["years"])]
        if active_filters.get("quarters"):
            qmap = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
            qnums = [qmap[q] for q in active_filters["quarters"] if q in qmap]
            if qnums:
                filtered = filtered[filtered["_std_order_date"].dt.quarter.isin(qnums)]
        if active_filters.get("months"):
            filtered = filtered[filtered["_std_order_date"].dt.month_name().isin(active_filters["months"])]

    # Categorical Filters
    col_map = {
        "regions": "_std_region",
        "states": "_std_state",
        "cities": "_std_city",
        "countries": "_std_country",
        "categories": "_std_category",
        "subcats": "_std_sub_category",
        "products": "_std_product_name",
        "segments": "_std_segment",
        "shipmodes": "_std_ship_mode",
        "customers": "_std_customer_name",
        "payment": "_std_payment_mode",
        "salesperson": "_std_salesperson",
    }
    for fk, col in col_map.items():
        vals = active_filters.get(fk)
        if vals and col in filtered.columns:
            filtered = filtered[filtered[col].isin(vals)]

    return filtered


def main():
    # Handle chart click-to-filter events
    pending = st.session_state.pop("pending_click_filters", None)
    if pending:
        if "active_filters" not in st.session_state:
            st.session_state["active_filters"] = {}
        for k, v in pending.items():
            st.session_state[k] = v
            k_to_fk = {
                "flt_regions": "regions",
                "flt_cats": "categories",
                "flt_subcats": "subcats",
                "flt_segs": "segments",
                "flt_states": "states",
                "flt_cities": "cities",
            }
            if k in k_to_fk:
                st.session_state["active_filters"][k_to_fk[k]] = v

    if "app_booted" not in st.session_state:
        st.session_state["app_booted"] = True
        _load_default_dataset()
    else:
        _load_default_dataset()

    # SIDEBAR: Main Brand & Navigation
    st.sidebar.markdown("## 📈 Sales Performance")
    nav = st.sidebar.radio(
        "Navigation",
        options=["📊 Dashboard", "🔎 Sales Analysis", "🤖 AI Sales Assistant"],
        index=0,
        label_visibility="collapsed",
        key="nav_main",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 Dataset")
    current_name = st.session_state.get("dataset_name")

    if current_name:
        st.sidebar.caption(f"Current dataset: **{current_name}**")
        clean_df = st.session_state.get("clean_df")
        if clean_df is not None:
            row_info = f"{len(clean_df):,} rows"
            if "_std_order_date" in clean_df.columns:
                vd = clean_df["_std_order_date"].dropna()
                if len(vd) > 0:
                    row_info += f" · {vd.min().strftime('%b %Y')} – {vd.max().strftime('%b %Y')}"
            st.sidebar.caption(row_info)
        if st.sidebar.button("Clear Current Dataset", use_container_width=True, key="btn_clear_ds"):
            uploaded_now = st.session_state.get("file_uploader")
            ignore = None
            if uploaded_now is not None:
                ignore = (getattr(uploaded_now, "name", ""), getattr(uploaded_now, "size", 0))
            _clear_all_state()
            st.session_state["skip_default_dataset"] = True
            if ignore:
                st.session_state["ignore_upload_sig"] = ignore
            st.rerun()
    else:
        st.sidebar.info("No dataset loaded")

    # Upload Dataset in Sidebar
    uploaded = st.sidebar.file_uploader(
        "Upload New Dataset",
        type=["csv", "xlsx", "xls", "tsv"],
        key="file_uploader",
        help="Upload CSV, Excel, or TSV dataset (up to 50MB)",
    )
    if uploaded is not None:
        sig = (uploaded.name, getattr(uploaded, "size", 0))
        if sig != st.session_state.get("ignore_upload_sig"):
            token = f"{uploaded.name}_{getattr(uploaded, 'size', 0)}"
            if st.session_state.get("loaded_upload_token") != token:
                try:
                    with st.spinner("Processing dataset..."):
                        buf = io.BytesIO(uploaded.getvalue())
                        res = run_full_pipeline(buf, file_name=uploaded.name)
                        if res.get("success"):
                            st.session_state["loaded_upload_token"] = token
                            _store_pipeline_result(res, uploaded.name)
                            st.sidebar.success(f"✓ Loaded {len(res['clean_df']):,} rows")
                            st.rerun()
                        else:
                            st.sidebar.error(f"Pipeline error: {res.get('error')}")
                except Exception as ex:
                    st.sidebar.error(f"Upload failed: {ex}")

    # Pipeline Status in Sidebar Expander
    p_res = st.session_state.get("pipeline_result")
    if p_res and p_res.get("pipeline_steps"):
        with st.sidebar.expander("Pipeline Status", expanded=False):
            st.caption(f"Status: **{p_res.get('status', 'Completed')}**")
            st.caption(f"Input: **{p_res.get('file_name', '')}**")
            st.caption(f"Clean rows: **{p_res.get('row_count', 0):,}**")
            missing_count = sum(p_res.get("missing_summary", {}).values()) if isinstance(p_res.get("missing_summary"), dict) else 0
            st.caption(f"Missing values filled: **{missing_count:,}**")
            dup_count = p_res.get("duplicates_removed", 0)
            st.caption(f"Duplicates removed: **{dup_count:,}**")
            st.markdown("**12 Pipeline Steps**")
            for step in p_res.get("pipeline_steps", []):
                st.markdown(f"<span class='pipeline-check'>✓</span> {step}", unsafe_allow_html=True)

    # Currency Settings in Sidebar
    st.sidebar.markdown("---")
    with st.sidebar.expander("Currency Settings", expanded=False):
        src_curr = st.text_input("Source Currency", value=get_source_currency(), key="cfg_src_curr")
        rate = st.number_input(
            "1 source unit = INR",
            value=float(get_exchange_rate()),
            min_value=0.01,
            step=0.5,
            key="cfg_rate",
        )
        set_exchange_rate(float(rate), src_curr or "USD")
        st.caption(f"1 {src_curr or 'USD'} = ₹{float(rate):.2f}")

    clean_df = st.session_state.get("clean_df")
    selected_page = nav.split(" ", 1)[1] if " " in nav else nav

    # Sidebar Filter Controls for AI Sales Assistant (dataset-driven)
    if clean_df is not None and selected_page == "AI Sales Assistant":
        st.sidebar.markdown("---")
        with st.sidebar.expander("Assistant Filters", expanded=False):
            # 1. Date Range
            if "_std_order_date" in clean_df.columns:
                vd = clean_df["_std_order_date"].dropna()
                if len(vd) > 0:
                    st.date_input(
                        "Date Range",
                        value=(vd.min().date(), vd.max().date()),
                        min_value=vd.min().date(),
                        max_value=vd.max().date(),
                        key="sb_flt_date",
                    )
            # 2. Cascading Region -> State
            sel_reg = []
            if "_std_region" in clean_df.columns:
                reg_opts = sorted(str(r) for r in clean_df["_std_region"].dropna().unique())
                sel_reg = st.multiselect("Region", reg_opts, key="sb_flt_regions")
            if "_std_state" in clean_df.columns:
                st_pool = clean_df[clean_df["_std_region"].isin(sel_reg)] if sel_reg else clean_df
                st_opts = sorted(str(s) for s in st_pool["_std_state"].dropna().unique())
                st.multiselect("State", st_opts, key="sb_flt_states")
            # 3. Cascading Category -> Sub-Category
            sel_cat = []
            if "_std_category" in clean_df.columns:
                cat_opts = sorted(str(c) for c in clean_df["_std_category"].dropna().unique())
                sel_cat = st.multiselect("Category", cat_opts, key="sb_flt_cats")
            if "_std_sub_category" in clean_df.columns:
                sub_pool = clean_df[clean_df["_std_category"].isin(sel_cat)] if sel_cat else clean_df
                sub_opts = sorted(str(sc) for sc in sub_pool["_std_sub_category"].dropna().unique())
                st.multiselect("Sub-Category", sub_opts, key="sb_flt_subcats")
            # 4. Segment
            if "_std_segment" in clean_df.columns:
                seg_opts = sorted(str(s) for s in clean_df["_std_segment"].dropna().unique())
                st.multiselect("Segment", seg_opts, key="sb_flt_segs")
            # 5. Ship Mode
            if "_std_ship_mode" in clean_df.columns:
                sm_opts = sorted(str(sm) for sm in clean_df["_std_ship_mode"].dropna().unique())
                st.multiselect("Ship Mode", sm_opts, key="sb_flt_shipmodes")

            if st.button("⚡ Apply Filters", type="primary", use_container_width=True, key="btn_apply_flt_sidebar"):
                new_f = {}
                for k, fk in [("sb_flt_date", "date_range"), ("sb_flt_regions", "regions"), ("sb_flt_states", "states"),
                              ("sb_flt_cats", "categories"), ("sb_flt_subcats", "subcats"), ("sb_flt_segs", "segments"),
                              ("sb_flt_shipmodes", "shipmodes")]:
                    v = st.session_state.get(k)
                    if v:
                        new_f[fk] = v
                st.session_state["active_filters"] = new_f
                st.rerun()

        if st.sidebar.button("Reset All Filters", use_container_width=True, key="btn_reset_flt"):
            st.session_state["active_filters"] = {}
            for k in list(st.session_state.keys()):
                if k.startswith("flt_") or k.startswith("sb_flt_"):
                    del st.session_state[k]
            st.rerun()

    # Compute filtered DataFrame from active_filters
    filtered_df = _apply_filters(clean_df)
    st.session_state["filtered_df"] = filtered_df

    if current_name is None and st.session_state.get("pipeline_result") is None:
        _render_empty_state()
        return

    try:
        if selected_page == "Dashboard":
            render_dashboard_view(df=filtered_df, dataset_name=st.session_state.get("dataset_name", ""), clean_df=clean_df)
        elif selected_page == "Sales Analysis":
            render_sales_analysis_view(clean_df)
        elif selected_page == "AI Sales Assistant":
            render_ai_assistant_view(filtered_df if filtered_df is not None else clean_df)
    except Exception as exc:
        st.error("Something went wrong while rendering this page. Check filters or reload the dataset.")
        st.caption(str(exc))


def _render_empty_state():
    st.markdown(
        """
    <div class="empty-state">
        <div class="empty-state-icon">📁</div>
        <div class="empty-state-title">No Dataset Loaded</div>
        <div class="empty-state-desc">Upload a CSV, Excel, or TSV file via the sidebar to start analyzing your sales data, or load the built-in SuperStore sample dataset.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📊 Load Sample SuperStore Dataset", use_container_width=True, key="btn_empty_load_sample"):
            st.session_state["skip_default_dataset"] = False
            _load_default_dataset()
            st.rerun()


if __name__ == "__main__":
    main()
