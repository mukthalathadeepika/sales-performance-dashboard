"""
backend/column_mapping/detector.py
Intelligent column recognition and semantic mapping for sales datasets.
Uses fuzzy naming patterns and data heuristics to identify roles and confidence.
"""

from typing import Dict, Any, List, Optional
import pandas as pd


# Canonical semantic fields required/supported by the PRD
CANONICAL_FIELDS = {
    "order_id": {
        "label": "Order ID",
        "description": "Unique identifier for each transaction order",
        "required": True,
        "keywords": ["order id", "order_id", "orderid", "order no", "order num", "orderno", "invoice id", "invoice no", "transaction id"],
    },
    "order_date": {
        "label": "Order Date",
        "description": "Date when the order was placed",
        "required": True,
        "keywords": ["order date", "order_date", "orderdate", "date", "invoice date", "transaction date", "sale date"],
    },
    "sales": {
        "label": "Sales / Revenue",
        "description": "Monetary value of sales or gross revenue",
        "required": True,
        "keywords": ["sales", "revenue", "turnover", "total sales", "gross sales", "amount", "order amount"],
    },
    "profit": {
        "label": "Profit",
        "description": "Net profit or margin amount (may include negative values)",
        "required": False,
        "keywords": ["profit", "net profit", "earnings", "operating profit", "net income"],
    },
    "quantity": {
        "label": "Quantity",
        "description": "Number of units purchased",
        "required": False,
        "keywords": ["quantity", "qty", "units", "volume", "order quantity"],
    },
    "category": {
        "label": "Category",
        "description": "High-level product classification",
        "required": False,
        "keywords": ["category", "product category", "dept", "department"],
    },
    "sub_category": {
        "label": "Sub-Category",
        "description": "Detailed product sub-classification",
        "required": False,
        "keywords": ["sub-category", "subcategory", "sub category", "sub_category", "product subcategory"],
    },
    "product_name": {
        "label": "Product Name",
        "description": "Name or title of product item",
        "required": False,
        "keywords": ["product name", "product_name", "product", "item name", "item description", "description"],
    },
    "product_id": {
        "label": "Product ID",
        "description": "Product SKU or item identifier",
        "required": False,
        "keywords": ["product id", "product_id", "sku", "item id", "item code"],
    },
    "customer_id": {
        "label": "Customer ID",
        "description": "Unique identifier for customer",
        "required": False,
        "keywords": ["customer id", "customer_id", "cust id", "client id", "account id"],
    },
    "customer_name": {
        "label": "Customer Name",
        "description": "Full name of the customer",
        "required": False,
        "keywords": ["customer name", "customer_name", "customer", "client name", "buyer"],
    },
    "segment": {
        "label": "Customer Segment",
        "description": "Business or consumer segment (e.g. Consumer, Corporate)",
        "required": False,
        "keywords": ["segment", "customer segment", "market segment"],
    },
    "region": {
        "label": "Region",
        "description": "Geographical territory or sales zone",
        "required": False,
        "keywords": ["region", "sales region", "territory", "zone", "district"],
    },
    "state": {
        "label": "State / Province",
        "description": "State, province, or primary geographic subdivision",
        "required": False,
        "keywords": ["state", "province", "state/province"],
    },
    "city": {
        "label": "City",
        "description": "City or town name",
        "required": False,
        "keywords": ["city", "town", "municipality"],
    },
    "country": {
        "label": "Country",
        "description": "Country of transaction",
        "required": False,
        "keywords": ["country", "nation", "country/region"],
    },
    "ship_date": {
        "label": "Ship Date",
        "description": "Date when goods were shipped",
        "required": False,
        "keywords": ["ship date", "ship_date", "shipdate", "shipping date", "dispatch date"],
    },
    "ship_mode": {
        "label": "Ship Mode",
        "description": "Shipping method or carrier speed",
        "required": False,
        "keywords": ["ship mode", "ship_mode", "shipping mode", "delivery method", "carrier"],
    },
    "returns": {
        "label": "Returns Indicator",
        "description": "Indicator of returned orders or items",
        "required": False,
        "keywords": ["returns", "returned", "return indicator", "return flag", "is returned"],
    },
    "payment_mode": {
        "label": "Payment Mode",
        "description": "Method of payment used",
        "required": False,
        "keywords": ["payment mode", "payment method", "payment type", "pay mode"],
    },
}


def auto_detect_columns(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Analyzes DataFrame columns and suggests matches for canonical fields.
    Returns mapping:
    {
       field_key: {
           "column": matched_col_or_None,
           "confidence": "High" | "Medium" | "Low" | "Unmapped",
           "reason": str
       }
    }
    """
    raw_columns = list(df.columns)
    col_lower_map = {c: c.lower().strip() for c in raw_columns}
    
    mapping_result = {}
    used_columns = set()

    # Pass 1: Exact matches against keywords
    for field_key, field_info in CANONICAL_FIELDS.items():
        matched_col = None
        confidence = "Unmapped"
        reason = "No matching column found"

        # Check exact string match against keywords
        for raw_col, lower_col in col_lower_map.items():
            if raw_col in used_columns:
                continue
            
            # Direct match
            if lower_col in field_info["keywords"]:
                matched_col = raw_col
                confidence = "High"
                reason = f"Exact match for '{lower_col}'"
                break

        if matched_col:
            used_columns.add(matched_col)
            mapping_result[field_key] = {
                "column": matched_col,
                "confidence": confidence,
                "reason": reason,
            }

    # Pass 2: Partial matches / substring matches
    for field_key, field_info in CANONICAL_FIELDS.items():
        if field_key in mapping_result:
            continue

        matched_col = None
        confidence = "Unmapped"
        reason = "No matching column found"

        for raw_col, lower_col in col_lower_map.items():
            if raw_col in used_columns:
                continue

            for kw in field_info["keywords"]:
                # Check substring if keyword length is >= 4
                if len(kw) >= 4 and (kw in lower_col or lower_col in kw):
                    matched_col = raw_col
                    confidence = "Medium"
                    reason = f"Substring match with keyword '{kw}'"
                    break
            if matched_col:
                break

        if matched_col:
            used_columns.add(matched_col)
            mapping_result[field_key] = {
                "column": matched_col,
                "confidence": confidence,
                "reason": reason,
            }
        else:
            mapping_result[field_key] = {
                "column": None,
                "confidence": "Unmapped",
                "reason": "Not detected",
            }

    return mapping_result


def get_field_options(df: pd.DataFrame) -> List[str]:
    """Returns available column names for manual dropdown selection, plus None."""
    return ["-- Not Mapped --"] + list(df.columns)
