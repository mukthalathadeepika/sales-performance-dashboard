"""
backend/pipeline.py
End-to-end data processing pipeline adhering strictly to Section 5 requirements:
Upload -> File Validation -> Ingestion -> Column Detection -> Cleaning ->
Missing-Value Handling -> Data Type Normalization -> Date Normalization ->
Numeric Field Validation -> Duplicate Check -> Quality Summary -> Analytics
"""

import io
from typing import Tuple, Dict, Any, List, Optional, Union
import pandas as pd

from backend.file_handling.loader import load_dataset
from backend.column_mapping.detector import auto_detect_columns
from backend.cleaning.quality import run_data_quality_audit, clean_and_normalize_data
from backend.analytics.kpi import calculate_kpis


def run_full_pipeline(
    file_source: Union[str, io.BytesIO, io.StringIO],
    file_name: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the comprehensive 12-step validation and ingestion pipeline.
    Returns:
    {
        "success": bool,
        "error": Optional[str],
        "raw_df": pd.DataFrame,
        "clean_df": pd.DataFrame,
        "mapping": Dict,
        "quality_audit": Dict,
        "pipeline_steps": List[str],
        "kpis": Dict,
        "file_name": str,
        "row_count": int,
        "col_count": int
    }
    """
    steps_log = []

    # Step 1 & 2: File Validation and Ingestion
    raw_df, err = load_dataset(file_source, file_name=file_name, sheet_name=sheet_name)
    if err or raw_df is None:
        return {
            "success": False,
            "error": err or "Failed to read file.",
            "pipeline_steps": ["✗ File read failed"]
        }
    
    row_count = len(raw_df)
    col_count = len(raw_df.columns)
    if row_count == 0:
        return {
            "success": False,
            "error": "The uploaded file is empty.",
            "pipeline_steps": ["✗ Empty file"]
        }

    actual_name = file_name or (file_source if isinstance(file_source, str) else "uploaded_file.csv")
    steps_log.append(f"✓ File '{actual_name}' loaded successfully")
    steps_log.append(f"✓ {row_count:,} rows and {col_count} columns detected")

    # Step 3: Column Detection and Mapping
    mapping = auto_detect_columns(raw_df)
    mapped_count = sum(1 for m in mapping.values() if m.get("column") is not None)
    steps_log.append(f"✓ {mapped_count} semantic sales columns mapped")

    # Step 4, 5, 6, 7, 8: Cleaning, Missing values, Types, Dates, Numeric validation
    clean_df, exclusions = clean_and_normalize_data(raw_df, mapping)
    steps_log.append("✓ Data types, dates (DD-MM-YYYY), and numeric values normalized")
    steps_log.append("✓ Negative profits and loss-making transactions preserved")

    # Step 9 & 10: Duplicate Check and Quality Audit
    audit = run_data_quality_audit(raw_df, mapping)
    steps_log.append(f"✓ Quality verified: {audit['exact_duplicates']} duplicate rows, {audit['distinct_orders'] or 'N/A'} distinct orders")
    steps_log.append("✓ Dataset ready for analytics")

    # Step 11: Analytics Calculations
    kpis = calculate_kpis(clean_df)

    return {
        "success": True,
        "error": None,
        "raw_df": raw_df,
        "clean_df": clean_df,
        "mapping": mapping,
        "quality_audit": audit,
        "pipeline_steps": steps_log,
        "kpis": kpis,
        "file_name": actual_name,
        "row_count": row_count,
        "col_count": col_count
    }
