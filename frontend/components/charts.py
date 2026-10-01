"""
frontend/components/charts.py
Plotly chart builders implementing consistent executive design standards.
Strictly conforms to PRD Section 4.3 and 4.4.
"""

from typing import Optional
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Standard executive colorway
PALETTE = {
    "primary": "#2563EB",
    "secondary": "#6366F1",
    "accent": "#0D9488",
    "positive": "#10B981",
    "negative": "#EF4444",
    "neutral": "#94A3B8",
    "background": "#FFFFFF",
    "grid": "#F1F5F9",
    "text": "#1E293B",
    "series": ["#2563EB", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#64748B"]
}


def _apply_standard_layout(fig, title: str = "", height: int = 380):
    """Applies unified typography, margin, and clean styling to any Plotly chart."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.96,
            "x": 0.02,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 14, "color": PALETTE["text"], "family": "Inter, sans-serif"}
        },
        template="plotly_white",
        paper_bgcolor=PALETTE["background"],
        plot_bgcolor=PALETTE["background"],
        height=height,
        margin=dict(l=20, r=20, t=50, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=PALETTE["text"])
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, sans-serif"
        )
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=PALETTE["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=PALETTE["grid"], zeroline=False)
    return fig


def plot_sales_profit_timeline(df: pd.DataFrame, currency_symbol: str = "") -> go.Figure:
    """Creates a dual-axis monthly timeline of Sales (bar) and Profit (line)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    sym = currency_symbol

    if "Sales" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df["period_label"],
                y=df["Sales"],
                name="Sales",
                marker_color=PALETTE["primary"],
                opacity=0.85,
                hovertemplate=f"Sales: {sym}%{{y:,.2f}}<extra></extra>"
            ),
            secondary_y=False
        )

    if "Profit" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["period_label"],
                y=df["Profit"],
                name="Profit",
                mode="lines+markers",
                line=dict(color=PALETTE["positive"], width=2.5),
                marker=dict(size=6),
                hovertemplate=f"Profit: {sym}%{{y:,.2f}}<extra></extra>"
            ),
            secondary_y=True
        )

    _apply_standard_layout(fig, title="Monthly Sales & Profit Performance")
    fig.update_yaxes(title_text="Sales", secondary_y=False, showgrid=True)
    fig.update_yaxes(title_text="Profit", secondary_y=True, showgrid=False)
    return fig


def plot_cumulative_sales(df: pd.DataFrame, currency_symbol: str = "") -> go.Figure:
    """Creates a cumulative revenue growth curve."""
    fig = go.Figure()
    sym = currency_symbol
    if "Cumulative Sales" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["period_label"],
                y=df["Cumulative Sales"],
                fill="tozeroy",
                mode="lines",
                line=dict(color=PALETTE["primary"], width=2),
                fillcolor="rgba(37, 99, 235, 0.1)",
                name="Cumulative Sales",
                hovertemplate=f"Cumulative: {sym}%{{y:,.2f}}<extra></extra>"
            )
        )
    _apply_standard_layout(fig, title="Cumulative Revenue Over Time")
    return fig


def plot_top_products_bar(top_df: pd.DataFrame, metric: str = "Sales", currency_symbol: str = "") -> go.Figure:
    """Horizontal bar chart for top products."""
    fig = go.Figure()
    sym = currency_symbol if metric in ["Sales", "Profit"] else ""
    if not top_df.empty:
        # Sort ascending for horizontal bar (so top is at top)
        df_sorted = top_df.sort_values(metric, ascending=True)
        fig.add_trace(
            go.Bar(
                y=df_sorted["Product Name"].str.slice(0, 35) + "...",
                x=df_sorted[metric],
                orientation="h",
                marker_color=PALETTE["primary"],
                hovertemplate=f"%{{y}}<br>{metric}: {sym}%{{x:,.2f}}<extra></extra>"
            )
        )
    _apply_standard_layout(fig, title=f"Top Products by {metric}")
    fig.update_layout(margin=dict(l=150, r=20, t=50, b=30))
    return fig


def plot_loss_products_bar(bottom_df: pd.DataFrame, currency_symbol: str = "") -> go.Figure:
    """Horizontal bar chart for bottom/loss-making products."""
    fig = go.Figure()
    sym = currency_symbol
    if not bottom_df.empty and "Profit" in bottom_df.columns:
        df_sorted = bottom_df.sort_values("Profit", ascending=False)
        colors_list = [PALETTE["negative"] if val < 0 else PALETTE["neutral"] for val in df_sorted["Profit"]]
        fig.add_trace(
            go.Bar(
                y=df_sorted["Product Name"].str.slice(0, 35) + "...",
                x=df_sorted["Profit"],
                orientation="h",
                marker_color=colors_list,
                hovertemplate=f"%{{y}}<br>Profit: {sym}%{{x:,.2f}}<extra></extra>"
            )
        )
    _apply_standard_layout(fig, title="Bottom Products by Profit (Loss-Making Alerts)")
    fig.update_layout(margin=dict(l=150, r=20, t=50, b=30))
    return fig


def plot_category_treemap(df: pd.DataFrame, currency_symbol: str = "") -> go.Figure:
    """Interactive Treemap for Category -> Sub-Category hierarchy."""
    sym = currency_symbol
    fig = px.treemap(
        df,
        path=["Category", "Sub-Category"],
        values="Sales",
        color="Profit Margin %",
        color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
        color_continuous_midpoint=0,
        hover_data={"Sales": f":,{sym}.2f", "Profit": f":,{sym}.2f", "Profit Margin %": ":.1f%"}
    )
    _apply_standard_layout(fig, title="Category & Sub-Category Treemap (Sized by Sales, Colored by Margin %)")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def plot_us_state_choropleth(state_df: pd.DataFrame, metric: str = "Sales", currency_symbol: str = "") -> go.Figure:
    """Choropleth map of US States."""
    sym = currency_symbol if metric in ["Sales", "Profit"] else ""
    valid_states = state_df.dropna(subset=["State Code"])
    
    fig = go.Figure(data=go.Choropleth(
        locations=valid_states["State Code"],
        z=valid_states[metric],
        locationmode='USA-states',
        colorscale='Blues',
        colorbar_title=metric,
        text=valid_states["State"],
        hovertemplate=f"<b>%{{text}}</b><br>{metric}: {sym}%{{z:,.2f}}<extra></extra>"
    ))
    
    fig.update_layout(
        geo_scope='usa',
        title={
            "text": f"Geographic Distribution by State ({metric})",
            "y": 0.96,
            "x": 0.02,
            "font": {"size": 14, "color": PALETTE["text"]}
        },
        margin=dict(l=0, r=0, t=40, b=0),
        height=380,
        paper_bgcolor=PALETTE["background"]
    )
    return fig


def plot_segment_donut(segment_df: pd.DataFrame, currency_symbol: str = "") -> go.Figure:
    """Customer segment distribution donut chart."""
    fig = go.Figure(data=[go.Pie(
        labels=segment_df["Segment"],
        values=segment_df["Sales"],
        hole=0.55,
        marker=dict(colors=PALETTE["series"]),
        textinfo='label+percent',
        hovertemplate=f"Segment: %{{label}}<br>Sales: {currency_symbol}%{{value:,.2f}} (%{{percent}})<extra></extra>"
    )])
    _apply_standard_layout(fig, title="Sales by Customer Segment")
    return fig


def plot_shipping_modes_bar(shipping_df: pd.DataFrame) -> go.Figure:
    """Shipping modes distribution and transit days."""
    fig = go.Figure()
    if not shipping_df.empty:
        fig.add_trace(
            go.Bar(
                x=shipping_df["Ship Mode"],
                y=shipping_df["Orders"],
                name="Orders",
                marker_color=PALETTE["primary"],
                opacity=0.85
            )
        )
    _apply_standard_layout(fig, title="Orders by Shipping Mode")
    return fig


def plot_quadrant_scatter(df: pd.DataFrame, currency_symbol: str = "") -> go.Figure:
    """Sales vs Profit Margin Scatter Quadrant."""
    sym = currency_symbol
    fig = px.scatter(
        df,
        x="Sales",
        y="Profit Margin %",
        size="Quantity" if "Quantity" in df.columns else None,
        color="Category" if "Category" in df.columns else None,
        text="Sub-Category" if "Sub-Category" in df.columns else None,
        hover_name="Sub-Category" if "Sub-Category" in df.columns else None,
        color_discrete_sequence=PALETTE["series"],
    )
    fig.add_hline(y=0, line_dash="dash", line_color=PALETTE["negative"], annotation_text="Breakeven (0% Margin)")
    _apply_standard_layout(fig, title="Profitability Matrix: Sales vs Profit Margin %")
    fig.update_traces(textposition='top center')
    return fig
