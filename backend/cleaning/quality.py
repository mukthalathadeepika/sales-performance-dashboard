"""
backend/cleaning/quality.py
Performs comprehensive data quality audit and safe, non-destructive cleaning.
Adheres strictly to PRD Section 3.4 and Section 6 rules.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


def run_data_quality_audit(df: pd.DataFrame, mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Examines the dataset against standard quality metrics and returns an audit dictionary.
    Does NOT mutate the original dataframe.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    
    # 1. Exact duplicate rows (entire row duplicated)
    exact_duplicates = int(df.duplicated().sum())

    # 2. Blank or uninformative columns (100% empty or whitespace)
    blank_columns = []
    for col in df.columns:
        series = df[col]
        if series.isna().all():
            blank_columns.append(col)
        elif series.dtype == object:
            # check if stripped values are all empty or #N/A
            non_empty = series.dropna().astype(str).str.strip()
            if len(non_empty) == 0 or (non_empty == "").all():
                blank_columns.append(col)

    # 3. Column-by-column missing / placeholder counts
    column_stats = []
    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        
        # Check string representations like #N/A, N/A, null, none
        placeholder_count = 0
        if series.dtype == object:
            s_str = series.dropna().astype(str).str.strip().str.upper()
            placeholder_count = int(s_str.isin(["#N/A", "N/A", "NA", "NULL", "NONE", "-", "NAN", ""]).sum())

        effective_missing = null_count + placeholder_count
        pct_missing = (effective_missing / total_rows * 100) if total_rows > 0 else 0.0

        column_stats.append({
            "column": col,
            "null_count": null_count,
            "placeholder_count": placeholder_count,
            "total_missing": effective_missing,
            "pct_missing": round(pct_missing, 1),
            "sample_values": [str(x) for x in series.dropna().unique()[:3]]
        })

    # 4. Check Order ID vs Distinct Order IDs
    order_id_col = mapping.get("order_id", {}).get("column")
    distinct_orders = None
    if order_id_col and order_id_col in df.columns:
        distinct_orders = int(df[order_id_col].nunique())

    # 5. Check Returns field completeness
    returns_col = mapping.get("returns", {}).get("column")
    returns_limitation_warning = None
    returns_breakdown = {}
    if returns_col and returns_col in df.columns:
        # In pandas, '#N/A' is read as NaN by default
        null_count = int(df[returns_col].isna().sum())
        val_counts = df[returns_col].dropna().astype(str).str.strip().value_counts().to_dict()
        returns_breakdown = {str(k): int(v) for k, v in val_counts.items()}
        if null_count > 0:
            returns_breakdown["#N/A"] = null_count
        na_count = null_count + int(df[returns_col].dropna().astype(str).str.strip().isin(["#N/A", "N/A", "nan"]).sum())
        if total_rows > 0 and (na_count / total_rows) > 0.5:
            returns_limitation_warning = (
                f"Returns data is incomplete: {na_count:,} out of {total_rows:,} rows "
                f"({na_count/total_rows*100:.1f}%) contain '#N/A'. Only positive returns (1) are recorded. "
                "Calculated return rates reflect tracked returns only."
            )

    # 6. Check Geographic coverage
    country_col = mapping.get("country", {}).get("column")
    geo_coverage = []
    if country_col and country_col in df.columns:
        geo_coverage = [str(c) for c in df[country_col].dropna().unique()]

    # 7. Check Dates coverage
    date_col = mapping.get("order_date", {}).get("column")
    date_range_info = None
    invalid_dates_count = 0
    if date_col and date_col in df.columns:
        parsed_dates = _safe_parse_dates(df[date_col])
        valid_dates = parsed_dates.dropna()
        invalid_dates_count = int(parsed_dates.isna().sum()) - int(df[date_col].isna().sum())
        if len(valid_dates) > 0:
            date_range_info = {
                "min_date": valid_dates.min().strftime("%Y-%m-%d"),
                "max_date": valid_dates.max().strftime("%Y-%m-%d"),
                "valid_count": int(len(valid_dates)),
                "invalid_count": max(0, invalid_dates_count)
            }

    # 8. Check Profit & Sales validity
    sales_col = mapping.get("sales", {}).get("column")
    profit_col = mapping.get("profit", {}).get("column")
    sales_invalid = 0
    profit_negative_count = 0
    if sales_col and sales_col in df.columns:
        s_num = pd.to_numeric(df[sales_col].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce')
        sales_invalid = int(s_num.isna().sum()) - int(df[sales_col].isna().sum())
    if profit_col and profit_col in df.columns:
        p_num = pd.to_numeric(df[profit_col].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce')
        profit_negative_count = int((p_num < 0).sum())

    # Build summary
    return {
        "total_rows": total_rows,
        "total_cols": total_cols,
        "exact_duplicates": exact_duplicates,
        "distinct_orders": distinct_orders,
        "blank_columns": blank_columns,
        "column_stats": column_stats,
        "returns_warning": returns_limitation_warning,
        "returns_breakdown": returns_breakdown,
        "geo_coverage": geo_coverage,
        "date_range": date_range_info,
        "sales_invalid_count": max(0, sales_invalid),
        "profit_negative_count": profit_negative_count,
        "unmapped_critical_fields": [
            k for k in ["order_id", "order_date", "sales"]
            if not mapping.get(k, {}).get("column")
        ]
    }


def _safe_parse_dates(series: pd.Series) -> pd.Series:
    """
    Attempts parsing dates using dayfirst=True fallback if standard parsing fails or format is DD-MM-YYYY.
    """
    # Sample check for DD-MM-YYYY
    sample = series.dropna().astype(str).head(50)
    has_high_first_token = False
    for s in sample:
        parts = s.split("-") if "-" in s else s.split("/")
        if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) <= 2 and int(parts[0]) > 12:
            has_high_first_token = True
            break
            
    try:
        if has_high_first_token:
            return pd.to_datetime(series, dayfirst=True, errors="coerce")
        else:
            return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.to_datetime(series, format="mixed", errors="coerce")


def clean_and_normalize_data(df: pd.DataFrame, mapping: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Creates a standardized working dataframe without deleting raw rows.
    Standardized columns begin with '_standard_' to avoid collisions.
    Exclusions for invalid dates/sales are logged.
    """
    clean_df = df.copy()
    exclusions = {
        "unparsable_date_rows": 0,
        "unparsable_sales_rows": 0,
    }

    # Map standardized columns
    for canonical_key, map_info in mapping.items():
        src_col = map_info.get("column")
        if not src_col or src_col not in df.columns:
            continue

        std_col = f"_std_{canonical_key}"

        if canonical_key in ["order_date", "ship_date"]:
            parsed = _safe_parse_dates(clean_df[src_col])
            clean_df[std_col] = parsed
            if canonical_key == "order_date":
                exclusions["unparsable_date_rows"] = int(parsed.isna().sum() - clean_df[src_col].isna().sum())

        elif canonical_key in ["sales", "profit", "discount"]:
            # Clean string symbols like $, commas, percent signs
            s = clean_df[src_col].astype(str).str.replace(r'[\$,\s%]', '', regex=True)
            # Replace placeholder representations with NaN
            s = s.replace(["#N/A", "N/A", "nan", "None", ""], np.nan)
            num = pd.to_numeric(s, errors="coerce")
            if canonical_key == "discount":
                # Convert 10 (percent) to 0.10; leave 0-1 fractions unchanged
                if num.dropna().gt(1).any() and not num.dropna().gt(100).any():
                    num = num / 100.0
            clean_df[std_col] = num
            if canonical_key == "sales":
                exclusions["unparsable_sales_rows"] = int(num.isna().sum() - clean_df[src_col].isna().sum())

        elif canonical_key == "quantity":
            s = clean_df[src_col].astype(str).str.replace(r'[\$,\s]', '', regex=True)
            num = pd.to_numeric(s, errors="coerce")
            clean_df[std_col] = num

        elif canonical_key == "returns":
            # Normalize returns: 1 if 1/1.0/'yes'/'true'/'returned'; otherwise 0
            def _normalize_return(val):
                if pd.isna(val):
                    return 0
                val_str = str(val).strip().lower()
                if val_str in ["1", "1.0", "yes", "true", "returned", "y"]:
                    return 1
                try:
                    if float(val) == 1.0:
                        return 1
                except (ValueError, TypeError):
                    pass
                return 0
            clean_df[std_col] = clean_df[src_col].apply(_normalize_return)

        else:
            # Categorical / string fields: strip and keep
            clean_df[std_col] = clean_df[src_col].astype(str).str.strip()
            # Restore genuine NaNs
            clean_df.loc[clean_df[src_col].isna(), std_col] = np.nan

    # Add shipping delay in days if both order_date and ship_date are available
    if "_std_order_date" in clean_df.columns and "_std_ship_date" in clean_df.columns:
        clean_df["_std_shipping_duration_days"] = (
            clean_df["_std_ship_date"] - clean_df["_std_order_date"]
        ).dt.days

    return clean_df, exclusions
