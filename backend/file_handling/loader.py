"""
backend/file_handling/loader.py
Handles loading of CSV, Excel (.xlsx), and TSV files with robust encoding
detection and sheet handling.
"""

import io
import os
from typing import Tuple, List, Optional, Union
import pandas as pd


def get_excel_sheet_names(file_source: Union[str, io.BytesIO]) -> List[str]:
    """Retrieve sheet names from an Excel workbook."""
    try:
        excel_file = pd.ExcelFile(file_source)
        return excel_file.sheet_names
    except Exception as e:
        return []


def load_dataset(
    file_source: Union[str, io.BytesIO, io.StringIO],
    file_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load dataset from a file path or file-like object.
    Supports CSV, Excel (.xlsx, .xls), and TSV.
    Returns (DataFrame, error_message).
    """
    if file_source is None:
        return None, "No file source provided."

    # Determine file name extension
    name = ""
    if file_name:
        name = file_name.lower()
    elif isinstance(file_source, str):
        name = os.path.basename(file_source).lower()

    try:
        # Excel loader
        if name.endswith((".xlsx", ".xls")):
            sheet = sheet_name if sheet_name else 0
            df = pd.read_excel(file_source, sheet_name=sheet)
            df = _clean_headers(df)
            return df, None

        # TSV loader
        if name.endswith(".tsv"):
            df = _read_csv_with_fallback(file_source, sep="\t")
            df = _clean_headers(df)
            return df, None

        # Default to CSV
        df = _read_csv_with_fallback(file_source, sep=",")
        df = _clean_headers(df)
        return df, None

    except Exception as e:
        return None, f"Failed to parse file: {str(e)}"


def _read_csv_with_fallback(file_source, sep=",") -> pd.DataFrame:
    """Try reading CSV with utf-8-sig, utf-8, latin1, cp1252 encodings."""
    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252", "iso-8859-1"]
    last_err = None

    for enc in encodings:
        try:
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            df = pd.read_csv(file_source, sep=sep, encoding=enc, low_memory=False)
            return df
        except Exception as err:
            last_err = err
            continue

    raise last_err or RuntimeError("Unable to decode CSV file with supported encodings.")


def _clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Clean header names by removing BOM, non-printable characters, and leading/trailing whitespace."""
    new_cols = []
    for col in df.columns:
        col_str = str(col).strip()
        # Remove BOM if present
        if col_str.startswith("\ufeff"):
            col_str = col_str[1:]
        new_cols.append(col_str)
    df.columns = new_cols
    return df
