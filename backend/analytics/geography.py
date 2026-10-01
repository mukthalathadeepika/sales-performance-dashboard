"""
backend/analytics/geography.py
Geographic sales distribution and multi-level drill-down (Region -> State -> City).
Includes US state abbreviation mapping for Plotly Choropleth maps.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

# US State to 2-letter postal code mapping for Plotly choropleth
US_STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC"
}


def get_regional_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates metrics by Region."""
    if df is None or len(df) == 0 or "_std_region" not in df.columns:
        return pd.DataFrame()

    agg_dict = {}
    if "_std_sales" in df.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in df.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in df.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in df.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = df.groupby("_std_region", as_index=False).agg(agg_dict)
    grouped = grouped.rename(columns={
        "_std_region": "Region",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    })

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).reset_index(drop=True)


def get_state_breakdown(df: pd.DataFrame, region_filter: Optional[str] = None) -> pd.DataFrame:
    """Aggregates metrics by State, optionally filtered by Region."""
    if df is None or len(df) == 0 or "_std_state" not in df.columns:
        return pd.DataFrame()

    filtered = df
    if region_filter and "_std_region" in df.columns:
        filtered = df[df["_std_region"] == region_filter]

    agg_dict = {}
    if "_std_sales" in filtered.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in filtered.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in filtered.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in filtered.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = filtered.groupby("_std_state", as_index=False).agg(agg_dict)
    grouped = grouped.rename(columns={
        "_std_state": "State",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    })

    # Add State Code for US Map
    grouped["State Code"] = grouped["State"].map(US_STATE_CODES)

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).reset_index(drop=True)


def get_city_breakdown(df: pd.DataFrame, state_filter: Optional[str] = None) -> pd.DataFrame:
    """Aggregates metrics by City, optionally filtered by State."""
    if df is None or len(df) == 0 or "_std_city" not in df.columns:
        return pd.DataFrame()

    filtered = df
    if state_filter and "_std_state" in df.columns:
        filtered = df[df["_std_state"] == state_filter]

    agg_dict = {}
    if "_std_sales" in filtered.columns:
        agg_dict["_std_sales"] = "sum"
    if "_std_profit" in filtered.columns:
        agg_dict["_std_profit"] = "sum"
    if "_std_quantity" in filtered.columns:
        agg_dict["_std_quantity"] = "sum"
    if "_std_order_id" in filtered.columns:
        agg_dict["_std_order_id"] = "nunique"

    grouped = filtered.groupby("_std_city", as_index=False).agg(agg_dict)
    grouped = grouped.rename(columns={
        "_std_city": "City",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_quantity": "Quantity",
        "_std_order_id": "Orders",
    })

    if "Sales" in grouped.columns and "Profit" in grouped.columns:
        grouped["Profit Margin %"] = (grouped["Profit"] / grouped["Sales"] * 100).round(2)

    return grouped.sort_values("Sales", ascending=False).reset_index(drop=True)
