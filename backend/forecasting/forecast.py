"""Linear trend sales forecast. Predictions are labelled as forecast, not facts."""

from typing import Any, Dict
import numpy as np
import pandas as pd


def forecast_sales(df: pd.DataFrame, periods: int = 3, min_months: int = 4) -> Dict[str, Any]:
    """
    Forecast next `periods` months of sales from monthly history.
    Returns empty-state metadata when history is insufficient.
    """
    empty = {
        "available": False,
        "message": "Forecast unavailable — insufficient historical data.",
        "historical": pd.DataFrame(),
        "forecast": pd.DataFrame(),
    }
    if df is None or len(df) == 0:
        return empty
    if "_std_order_date" not in df.columns or "_std_sales" not in df.columns:
        return empty

    tdf = df.dropna(subset=["_std_order_date"]).copy()
    if tdf.empty:
        return empty

    tdf["_m"] = tdf["_std_order_date"].dt.to_period("M").dt.to_timestamp()
    magg = tdf.groupby("_m")["_std_sales"].sum().sort_index()
    if len(magg) < min_months:
        return {
            **empty,
            "message": f"Forecast unavailable — insufficient data (need at least {min_months} months of data).",
        }

    x = np.arange(len(magg))
    y = magg.values.astype(float)
    coeffs = np.polyfit(x, y, 1)
    trend_fn = np.poly1d(coeffs)

    last_date = magg.index[-1]
    forecast_dates = pd.date_range(last_date + pd.DateOffset(months=1), periods=periods, freq="MS")
    forecast_x = np.arange(len(magg), len(magg) + periods)
    forecast_y = np.maximum(trend_fn(forecast_x), 0)

    historical = pd.DataFrame({"Date": magg.index, "Sales": y, "Kind": "Historical"})
    forecast = pd.DataFrame({"Date": forecast_dates, "Sales": forecast_y, "Kind": "Forecast"})
    return {
        "available": True,
        "message": "Forecast uses simple linear trend extrapolation. Not a guaranteed prediction.",
        "historical": historical,
        "forecast": forecast,
        "trend": trend_fn(x),
    }
