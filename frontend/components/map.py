"""Interactive geographic map with US choropleth fallback and empty states."""

from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.analytics.currency import convert_series_to_inr, format_inr
from backend.analytics.geography import get_state_breakdown
from frontend.components.charts import PLOTLY_CONFIG, _dark_chart_layout, BG_CHART, CLR_TEXT, CLR_TEXT_MUTED

BG = "#162040"


def render_geo_map(df: pd.DataFrame, metric: str = "Sales", key: str = "dash_geo_map"):
    """Render a choropleth when US state codes exist; otherwise a ranked location bar."""
    if df is None or len(df) == 0:
        _empty("Map unavailable — this dataset does not contain geographic information.")
        return None

    has_state = "_std_state" in df.columns
    has_country = "_std_country" in df.columns
    has_city = "_std_city" in df.columns
    if not (has_state or has_country or has_city):
        _empty("Map unavailable — this dataset does not contain geographic information.")
        return None

    if metric == "Profit" and "_std_profit" not in df.columns:
        metric = "Sales" if "_std_sales" in df.columns else "Orders"
    if metric == "Sales" and "_std_sales" not in df.columns:
        metric = "Orders"

    if has_state:
        geo = get_state_breakdown(df)
        loc_col = "State"
    elif has_city:
        geo = df.groupby("_std_city", as_index=False).agg(_agg(df))
        geo = geo.rename(columns=_rename())
        loc_col = "City"
    else:
        geo = df.groupby("_std_country", as_index=False).agg(_agg(df))
        geo = geo.rename(columns=_rename())
        loc_col = "Country"

    if geo is None or geo.empty:
        _empty("Map unavailable — no mappable locations in the filtered data.")
        return None

    val_col = metric if metric in geo.columns else ("Sales" if "Sales" in geo.columns else geo.columns[-1])
    if val_col in ("Sales", "Profit"):
        geo[val_col] = convert_series_to_inr(geo[val_col])

    coded = geo.dropna(subset=["State Code"]) if "State Code" in geo.columns else pd.DataFrame()
    if has_state and len(coded) >= 3:
        fig = px.choropleth(
            coded,
            locations="State Code",
            locationmode="USA-states",
            color=val_col,
            scope="usa",
            hover_name="State",
            color_continuous_scale=["#0B1426", "#14B8A6", "#00D4FF", "#FACC15"],
            hover_data={val_col: ":,.0f", "State Code": False},
        )
        fig.update_layout(
            title=dict(text=f"{metric} by State", x=0.02, y=0.96, font=dict(size=13, color=CLR_TEXT)),
            template="plotly_dark",
            paper_bgcolor=BG,
            plot_bgcolor=BG,
            height=420,
            margin=dict(l=8, r=8, t=48, b=8),
            geo=dict(bgcolor=BG, lakecolor=BG, landcolor="#111D35", subunitcolor="rgba(255,255,255,0.15)"),
            coloraxis_colorbar=dict(title=metric, tickfont=dict(color=CLR_TEXT_MUTED)),
        )
    else:
        ranked = geo.sort_values(val_col, ascending=True).tail(15)
        fig = go.Figure(go.Bar(
            x=ranked[val_col],
            y=ranked[loc_col],
            orientation="h",
            marker_color="#00D4FF",
            hovertemplate="%{y}<br>" + metric + ": ₹%{x:,.0f}<extra></extra>",
        ))
        _dark_chart_layout(fig, title=f"{metric} by {loc_col} (Top 15)", height=420)
        fig.update_layout(showlegend=False)

    st.plotly_chart(fig, key=key, use_container_width=True, config=PLOTLY_CONFIG)
    return geo


def _agg(df):
    d = {}
    if "_std_sales" in df.columns:
        d["_std_sales"] = "sum"
    if "_std_profit" in df.columns:
        d["_std_profit"] = "sum"
    if "_std_order_id" in df.columns:
        d["_std_order_id"] = "nunique"
    elif d:
        pass
    else:
        d["_std_sales"] = "sum"
    return d


def _rename():
    return {
        "_std_city": "City",
        "_std_country": "Country",
        "_std_sales": "Sales",
        "_std_profit": "Profit",
        "_std_order_id": "Orders",
    }


def _empty(msg: str):
    st.markdown(
        f"""<div class="empty-state" style="padding:2rem;margin:0">
        <div class="empty-state-title">{msg}</div>
        </div>""",
        unsafe_allow_html=True,
    )
