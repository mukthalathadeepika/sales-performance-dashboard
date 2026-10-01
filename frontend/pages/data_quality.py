"""
frontend/pages/data_quality.py
File upload, Column mapping review, and Data Quality audit interface.
Strictly implements PRD Section 3.1, 3.3, 3.4, and Section 6.
"""

from typing import Dict, Any, Callable
import streamlit as st
import pandas as pd

from backend.column_mapping.detector import CANONICAL_FIELDS, auto_detect_columns, get_field_options
from backend.cleaning.quality import run_data_quality_audit, clean_and_normalize_data
from backend.file_handling.loader import load_dataset, get_excel_sheet_names


def render_data_quality_page(raw_df: pd.DataFrame, current_mapping: Dict[str, Any], on_update_callback: Callable):
    """Renders the data upload, column mapping editor, and quality health audit."""
    st.markdown("## 🛡️ Data Quality Audit & Column Mapping")
    st.markdown(
        "Inspect data integrity, audit missing values / placeholders, verify geographic and date coverage, "
        "and customize semantic column mappings."
    )

    # 1. File Upload Zone
    with st.expander("📤 Upload New Dataset (CSV, Excel, TSV)", expanded=(raw_df is None)):
        uploaded_file = st.file_uploader(
            "Upload sales spreadsheet",
            type=["csv", "xlsx", "xls", "tsv"],
            help="Upload your business sales transaction file."
        )

        sheet_to_use = None
        if uploaded_file and uploaded_file.name.endswith((".xlsx", ".xls")):
            sheet_names = get_excel_sheet_names(uploaded_file)
            if len(sheet_names) > 1:
                sheet_to_use = st.selectbox("Select Excel Sheet", options=sheet_names)

        if uploaded_file:
            if st.button("📥 Parse & Load Uploaded File", type="primary"):
                df_loaded, err = load_dataset(uploaded_file, file_name=uploaded_file.name, sheet_name=sheet_to_use)
                if err:
                    st.error(f"Error loading file: {err}")
                elif df_loaded is not None:
                    new_mapping = auto_detect_columns(df_loaded)
                    clean_df, _ = clean_and_normalize_data(df_loaded, new_mapping)
                    on_update_callback(df_loaded, clean_df, new_mapping, uploaded_file.name)
                    st.success(f"Successfully loaded '{uploaded_file.name}' with {len(df_loaded):,} rows!")
                    st.rerun()

    if raw_df is None or len(raw_df) == 0:
        st.info("No active dataset. Please upload a file above or click 'Load Sample Dataset'.")
        return

    # 2. Quality Audit Health Card
    audit = run_data_quality_audit(raw_df, current_mapping)

    st.markdown("### 📊 Dataset Integrity & Acceptance Summary")
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.metric("Total Input Rows", f"{audit['total_rows']:,}")
    with q2:
        st.metric("Distinct Orders", f"{audit['distinct_orders']:,}" if audit['distinct_orders'] else "Unmapped")
    with q3:
        st.metric("Exact Duplicate Rows", f"{audit['exact_duplicates']:,}", help="Rows where every single cell is identical")
    with q4:
        st.metric("Blank Columns", f"{len(audit['blank_columns'])}", help="Columns with 100% missing values")

    # Important Quality Alerts (PRD Section 6)
    if audit.get("returns_warning"):
        st.warning(f"⚠️ **Returns Coverage Limitation:** {audit['returns_warning']}")

    if audit.get("blank_columns"):
        st.info(f"ℹ️ **Unused / Empty Columns Detected:** {', '.join(audit['blank_columns'])}. These will be safely ignored without deleting rows.")

    if audit.get("date_range"):
        d = audit["date_range"]
        st.success(f"📅 **Date Coverage Verified:** {d['min_date']} to {d['max_date']} ({d['valid_count']:,} valid dates).")

    if audit.get("geo_coverage"):
        geo_str = ", ".join(audit["geo_coverage"])
        st.caption(f"🌍 **Geographic Coverage:** {geo_str}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Column Mapping Review & Customization (PRD Section 3.3)
    st.markdown("### 🔗 Semantic Column Mapping")
    st.markdown("Review detected fields. You can override any column assignment below:")

    col_options = get_field_options(raw_df)
    updated_mapping = dict(current_mapping)

    mapping_cols = st.columns(2)
    idx = 0
    for field_key, field_info in CANONICAL_FIELDS.items():
        with mapping_cols[idx % 2]:
            curr_val = current_mapping.get(field_key, {}).get("column")
            conf = current_mapping.get(field_key, {}).get("confidence", "Unmapped")
            
            # Badge color
            conf_badge = "🟢 High" if conf == "High" else "🟡 Medium" if conf == "Medium" else "⚪ Unmapped"

            label = f"{field_info['label']} ({conf_badge})"
            selected_idx = col_options.index(curr_val) if curr_val in col_options else 0

            chosen_col = st.selectbox(
                label,
                options=col_options,
                index=selected_idx,
                key=f"map_select_{field_key}",
                help=field_info["description"]
            )

            updated_mapping[field_key] = {
                "column": None if chosen_col == "-- Not Mapped --" else chosen_col,
                "confidence": "Manual" if chosen_col != curr_val else conf,
                "reason": "User specified" if chosen_col != curr_val else current_mapping.get(field_key, {}).get("reason", "")
            }
        idx += 1

    if st.button("💾 Apply & Save Column Mappings", type="primary"):
        clean_df, _ = clean_and_normalize_data(raw_df, updated_mapping)
        on_update_callback(raw_df, clean_df, updated_mapping, st.session_state.get("dataset_name", "SuperStore Dataset"))
        st.success("Column mappings updated successfully!")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Detailed Missing Values & Placeholder Inspection
    st.markdown("### 📋 Missing Values & Placeholders Breakdown")
    stats_df = pd.DataFrame(audit["column_stats"])
    if not stats_df.empty:
        st.dataframe(
            stats_df[["column", "total_missing", "pct_missing", "null_count", "placeholder_count", "sample_values"]],
            use_container_width=True
        )
