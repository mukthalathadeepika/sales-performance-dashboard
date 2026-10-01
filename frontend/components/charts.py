"""
frontend/components/charts.py
High-end Plotly charts designed after executive sales dashboard reference (superstore_analysis.png).
Features:
- Monthly Sales and Profit dual-line timeline
- Category Sales vs. Profit comparative bar chart
- Diverging Sub-Category / Top Products profit bar chart (Green for positive, Red for losses)
- Regional Profit Margin % bar chart with overall benchmark line
- Segment performance donut chart
All formatted in Indian Rupees (₹).
"""

from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.analytics.currency import format_inr

# Executive palette from reference
CLR_BLUE = "#1F77B4"
CLR_TEAL = "#1B7F6D"
CLR_RED = "#C53030"
CLR_DARK = "#0F172A"
CLR_GRID = "#F1F5F9"
CLR_MUTED = "#64748B"


def _clean_chart_layout(fig, title: str = "", height: int = 340):
    """Applies clean minimalist executive layout matching reference image."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.95,
            "x": 0.02,
            "xanchor": "left",
            "yanchor": "top",
            "font": {"size": 14, "color": CLR_DARK, "family": "Inter, system-ui, sans-serif"}
        },
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        height=height,
        margin=dict(l=15, r=15, t=45, b=25),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=CLR_DARK)
        ),
        hoverlabel=dict(bgcolor="white", font_size=12)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=CLR_GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=CLR_GRID, zeroline=False)
    return fig


def plot_monthly_sales_and_profit(df: pd.DataFrame) -> go.Figure:
    """
    Dual line chart of Monthly Sales (Blue) and Profit (Teal/Green).
    Exact match to reference top-left chart.
    """
    time_df = df.dropna(subset=["_std_order_date"]).copy()
    time_df["Month"] = time_df["_std_order_date"].dt.to_period("M").dt.to_timestamp()
    time_agg = time_df.groupby("Month", as_index=False).agg({
        "_std_sales": "sum",
        "_std_profit": "sum"
    }).sort_values("Month")
    time_agg["Label"] = time_agg["Month"].dt.strftime("%Y-%m")

    fig = go.Figure()
    
    # Sales Line
    fig.add_trace(go.Scatter(
        x=time_agg["Label"],
        y=time_agg["_std_sales"],
        mode="lines",
        name="Sales",
        line=dict(color=CLR_BLUE, width=2.5),
        hovertemplate="<b>Sales</b>: ₹%{y:,.2f}<extra></extra>"
    ))

    # Profit Line
    fig.add_trace(go.Scatter(
        x=time_agg["Label"],
        y=time_agg["_std_profit"],
        mode="lines",
        name="Profit",
        line=dict(color=CLR_TEAL, width=2.5),
        hovertemplate="<b>Profit</b>: ₹%{y:,.2f}<extra></extra>"
    ))

    _clean_chart_layout(fig, title="Monthly sales and profit")
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_category_sales_vs_profit(df: pd.DataFrame) -> go.Figure:
    """
    Category sales vs. profit horizontal comparative bar chart.
    Exact match to reference top-right chart.
    """
    cat_agg = df.groupby("_std_category", as_index=False).agg({
        "_std_sales": "sum",
        "_std_profit": "sum"
    }).sort_values("_std_sales", ascending=True)

    fig = go.Figure()

    # Sales Bar
    fig.add_trace(go.Bar(
        y=cat_agg["_std_category"],
        x=cat_agg["_std_sales"],
        orientation="h",
        name="Sales",
        marker_color=CLR_BLUE,
        hovertemplate="<b>%{y} Sales</b>: ₹%{x:,.2f}<extra></extra>"
    ))

    # Profit Bar
    fig.add_trace(go.Bar(
        y=cat_agg["_std_category"],
        x=cat_agg["_std_profit"],
        orientation="h",
        name="Profit",
        marker_color=CLR_TEAL,
        hovertemplate="<b>%{y} Profit</b>: ₹%{x:,.2f}<extra></extra>"
    ))

    _clean_chart_layout(fig, title="Category sales vs. profit")
    fig.update_layout(barmode="group", yaxis_title=None)
    fig.update_xaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_profit_by_subcategory(df: pd.DataFrame) -> go.Figure:
    """
    Profit by sub-category horizontal diverging bar chart.
    Green for positive profit, Red for negative loss.
    Exact match to reference bottom-left chart.
    """
    sub_agg = df.groupby("_std_sub_category", as_index=False)["_std_profit"].sum()
    sub_agg = sub_agg.sort_values("_std_profit", ascending=True)

    colors = [CLR_RED if p < 0 else CLR_TEAL for p in sub_agg["_std_profit"]]

    fig = go.Figure(go.Bar(
        y=sub_agg["_std_sub_category"],
        x=sub_agg["_std_profit"],
        orientation="h",
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>Profit: ₹%{x:,.2f}<extra></extra>"
    ))

    _clean_chart_layout(fig, title="Profit by sub-category", height=380)
    fig.add_vline(x=0, line_width=1, line_color="#94A3B8")
    fig.update_layout(yaxis_title=None, showlegend=False)
    fig.update_xaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_regional_profit_margins(df: pd.DataFrame) -> go.Figure:
    """
    Regional profit margins (%) with overall benchmark line.
    Exact match to reference bottom-right chart.
    """
    reg_agg = df.groupby("_std_region", as_index=False).agg({
        "_std_sales": "sum",
        "_std_profit": "sum"
    })
    reg_agg["Margin_Pct"] = (reg_agg["_std_profit"] / reg_agg["_std_sales"] * 100).round(2)
    reg_agg = reg_agg.sort_values("Margin_Pct", ascending=False)

    overall_margin = (df["_std_profit"].sum() / df["_std_sales"].sum() * 100) if df["_std_sales"].sum() > 0 else 0

    fig = go.Figure()
    
    # Regional margin bars
    fig.add_trace(go.Bar(
        x=reg_agg["_std_region"],
        y=reg_agg["Margin_Pct"],
        name="Region Margin",
        marker_color=CLR_BLUE,
        hovertemplate="<b>%{x}</b>: %{y:.2f}%<extra></extra>"
    ))

    # Overall benchmark line
    fig.add_hline(
        y=overall_margin,
        line_dash="dash",
        line_color=CLR_RED,
        annotation_text=f"Overall margin ({overall_margin:.2f}%)",
        annotation_position="top right"
    )

    _clean_chart_layout(fig, title="Regional profit margins (%)", height=380)
    fig.update_layout(xaxis_title=None, yaxis_title="Margin (%)", showlegend=False)
    fig.update_yaxes(ticksuffix="%")
    return fig


def plot_top_products_bar(df: pd.DataFrame, metric: str = "Sales", n: int = 10) -> go.Figure:
    """Horizontal bar chart for top 10 products by Sales or Profit."""
    col = "_std_sales" if metric == "Sales" else "_std_profit"
    top_p = df.groupby("_std_product_name", as_index=False)[col].sum().sort_values(col, ascending=False).head(n)
    top_p = top_p.sort_values(col, ascending=True)

    color = CLR_BLUE if metric == "Sales" else CLR_TEAL

    fig = go.Figure(go.Bar(
        y=top_p["_std_product_name"].str.slice(0, 30) + "...",
        x=top_p[col],
        orientation="h",
        marker_color=color,
        hovertemplate=f"<b>%{{y}}</b><br>{metric}: ₹%{{x:,.2f}}<extra></extra>"
    ))
    _clean_chart_layout(fig, title=f"Top {n} Products by {metric}", height=340)
    fig.update_layout(yaxis_title=None, showlegend=False)
    fig.update_xaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_customer_segment_donut(df: pd.DataFrame) -> go.Figure:
    """Customer segment sales share donut chart."""
    seg_agg = df.groupby("_std_segment", as_index=False)["_std_sales"].sum()
    
    fig = go.Figure(go.Pie(
        labels=seg_agg["_std_segment"],
        values=seg_agg["_std_sales"],
        hole=0.6,
        marker=dict(colors=[CLR_BLUE, CLR_TEAL, "#F59E0B"]),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Sales: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>"
    ))
    _clean_chart_layout(fig, title="Sales by Customer Segment", height=340)
    fig.update_layout(showlegend=True)
    return fig
