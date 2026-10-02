"""
frontend/views/data_quality_view.py
Clean, professional Data Quality audit view with dark navy theme.
Displays:
- Rows, Columns, Missing Values, Duplicate Rows metric cards
- Date Range & Data Validity status
- Important Detected Columns mapping
- Processed Dataset Preview
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from backend.cleaning.quality import run_data_quality_audit


def render_data_quality_view(raw_df: pd.DataFrame, clean_df: pd.DataFrame, mapping: Dict[str, Any]):
    """Renders the data quality page."""
    st.markdown("""
    <div class="dash-header-wrap">
        <div>
            <h1 class="dash-header-title">Data Quality & Health</h1>
            <div class="dash-header-subtitle">Audit completeness, duplicates, column detection, and dataset validation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if raw_df is None or len(raw_df) == 0:
        st.info("No active dataset loaded.")
        return

    audit = run_data_quality_audit(raw_df, mapping)

    total_missing_cells = int(raw_df.isna().sum().sum())
    total_cells = raw_df.shape[0] * raw_df.shape[1]
    missing_pct = (total_missing_cells / total_cells * 100) if total_cells > 0 else 0.0

    # 1. Four Summary Metric Cards
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-val">{audit['total_rows']:,}</div>
            <div class="metric-box-lbl">Total Rows</div>
        </div>
        """, unsafe_allow_html=True)

    with q2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-val">{audit['total_cols']}</div>
            <div class="metric-box-lbl">Total Columns</div>
        </div>
        """, unsafe_allow_html=True)

    with q3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-val">{total_missing_cells:,}</div>
            <div class="metric-box-lbl">Missing Cells ({missing_pct:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)

    with q4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-val">{audit['exact_duplicates']}</div>
            <div class="metric-box-lbl">Duplicate Rows</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # 2. Validity Status & Date Coverage
    st.markdown("### 📋 Dataset Validation & Coverage")
    v_c1, v_c2 = st.columns(2)

    with v_c1:
        distinct_orders = audit.get("distinct_orders")
        if distinct_orders is not None:
            st.success(f"✅ **Order IDs Verified**: {distinct_orders:,} distinct orders tracked across {audit['total_rows']:,} line items.")
        if audit.get("date_range"):
            d = audit["date_range"]
            st.success(f"✅ **Date Range Verified**: {d['min_date']} to {d['max_date']} ({d['valid_count']:,} records).")
        else:
            st.warning("⚠️ **Date Coverage**: Date field is unmapped or contains invalid dates.")

    with v_c2:
        if audit.get("geo_coverage"):
            coverage_str = ", ".join(audit["geo_coverage"][:4])
            st.info(f"ℹ️ **Geographic Coverage**: {coverage_str}.")
        if audit.get("returns_warning"):
            st.warning(f"⚠️ **Returns Notice**: {audit['returns_warning'][:120]}...")
        else:
            st.success("✅ **Returns Status**: Return indicator field mapped and verified.")

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # 3. Important Detected Columns
    st.markdown("### 🔗 Detected Column Mapping")
    detected_rows = []
    for k, v in mapping.items():
        col_name = v.get("column")
        if col_name:
            sample_val = "N/A"
            if col_name in raw_df.columns and not raw_df[col_name].dropna().empty:
                sample_val = str(raw_df[col_name].dropna().iloc[0])
            detected_rows.append({
                "Standard Field": k.replace("_", " ").title(),
                "Source Column": col_name,
                "Confidence": v.get("confidence", "High"),
                "Sample Value": sample_val
            })

    if detected_rows:
        det_df = pd.DataFrame(detected_rows)
        st.dataframe(det_df, use_container_width=True, hide_index=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # 4. Processed Dataset Preview
    st.markdown("### 🔍 Dataset Preview (First 20 Records)")
    preview_df = clean_df if clean_df is not None else raw_df
    display_cols = [c for c in preview_df.columns if not c.startswith("_std_")]
    if display_cols:
        st.dataframe(preview_df[display_cols].head(20), use_container_width=True, hide_index=True)
    else:
        st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
