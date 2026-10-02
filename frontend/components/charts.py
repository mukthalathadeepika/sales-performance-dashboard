"""
frontend/components/charts.py
Premium dark-theme Plotly charts for the Sales Performance Dashboard.
Features:
- Monthly Sales and Profit dual-line timeline
- Category Sales vs. Profit comparative bar chart
- Diverging Sub-Category profit bar chart (Green positive / Red losses)
- Regional Profit Margin % with overall benchmark
- Top Products bar chart
- Customer Segment donut chart
All formatted in Indian Rupees (₹).
"""

from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.analytics.currency import format_inr, convert_series_to_inr, get_exchange_rate

# Dark theme palette
CLR_CYAN = "#00D4FF"
CLR_BLUE = "#3B82F6"
CLR_TEAL = "#14B8A6"
CLR_GREEN = "#22C55E"
CLR_RED = "#EF4444"
CLR_YELLOW = "#FACC15"
CLR_ORANGE = "#F97316"
CLR_PURPLE = "#A78BFA"

# Background colors
BG_CHART = "#162040"
BG_PAPER = "#162040"
BG_GRID = "rgba(255, 255, 255, 0.04)"
CLR_TEXT = "#E2E8F0"
CLR_TEXT_MUTED = "#94A3B8"

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "png", "filename": "chart", "height": 720, "width": 1280, "scale": 2},
}


def _inr(series: pd.Series) -> pd.Series:
    return convert_series_to_inr(series)


def _dark_chart_layout(fig, title: str = "", height: int = 360):
    """Applies premium dark theme layout to Plotly charts."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.96,
            "x": 0.02,
            "xanchor": "left",
            "yanchor": "top",
            "font": {
                "size": 14,
                "color": CLR_TEXT,
                "family": "Inter, system-ui, sans-serif",
                "weight": 700
            }
        },
        template="plotly_dark",
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_CHART,
        height=height,
        margin=dict(l=12, r=12, t=50, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=CLR_TEXT_MUTED),
            bgcolor="rgba(0,0,0,0)"
        ),
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=12,
            font_color=CLR_TEXT,
            bordercolor="rgba(0, 212, 255, 0.3)"
        )
    )
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=BG_GRID,
        zeroline=False,
        tickfont=dict(size=10, color=CLR_TEXT_MUTED)
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=BG_GRID,
        zeroline=False,
        tickfont=dict(size=10, color=CLR_TEXT_MUTED)
    )
    return fig


def plot_monthly_sales_and_profit(df: pd.DataFrame) -> go.Figure:
    """
    Dual line chart of Monthly Sales (Cyan) and Profit (Green).
    With area fill for visual depth.
    """
    time_df = df.dropna(subset=["_std_order_date"]).copy()
    time_df["Month"] = time_df["_std_order_date"].dt.to_period("M").dt.to_timestamp()
    time_agg = time_df.groupby("Month", as_index=False).agg({
        "_std_sales": "sum",
        "_std_profit": "sum"
    }).sort_values("Month")
    time_agg["_std_sales"] = _inr(time_agg["_std_sales"])
    time_agg["_std_profit"] = _inr(time_agg["_std_profit"])
    time_agg["Label"] = time_agg["Month"].dt.strftime("%Y-%m")

    fig = go.Figure()

    # Sales area + line
    fig.add_trace(go.Scatter(
        x=time_agg["Label"],
        y=time_agg["_std_sales"],
        mode="lines",
        name="Sales",
        line=dict(color=CLR_CYAN, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 255, 0.08)",
        hovertemplate="<b>Sales</b>: ₹%{y:,.0f}<extra></extra>"
    ))

    # Profit area + line
    fig.add_trace(go.Scatter(
        x=time_agg["Label"],
        y=time_agg["_std_profit"],
        mode="lines",
        name="Profit",
        line=dict(color=CLR_GREEN, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(34, 197, 94, 0.06)",
        hovertemplate="<b>Profit</b>: ₹%{y:,.0f}<extra></extra>"
    ))

    _dark_chart_layout(fig, title="Monthly Sales & Profit Trend")
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_category_sales_vs_profit(df: pd.DataFrame) -> go.Figure:
    """
    Category sales vs. profit horizontal comparative bar chart.
    """
    cat_agg = df.groupby("_std_category", as_index=False).agg({
        "_std_sales": "sum",
        "_std_profit": "sum"
    }).sort_values("_std_sales", ascending=True)
    cat_agg["_std_sales"] = _inr(cat_agg["_std_sales"])
    cat_agg["_std_profit"] = _inr(cat_agg["_std_profit"])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=cat_agg["_std_category"],
        x=cat_agg["_std_sales"],
        orientation="h",
        name="Sales",
        marker_color=CLR_CYAN,
        marker_line=dict(width=0),
        hovertemplate="<b>%{y} Sales</b>: ₹%{x:,.0f}<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        y=cat_agg["_std_category"],
        x=cat_agg["_std_profit"],
        orientation="h",
        name="Profit",
        marker_color=CLR_GREEN,
        marker_line=dict(width=0),
        hovertemplate="<b>%{y} Profit</b>: ₹%{x:,.0f}<extra></extra>"
    ))

    _dark_chart_layout(fig, title="Category: Sales vs Profit")
    fig.update_layout(barmode="group", yaxis_title=None)
    fig.update_xaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_profit_by_subcategory(df: pd.DataFrame) -> go.Figure:
    """
    Profit by sub-category horizontal diverging bar chart.
    Green for positive, Red for losses.
    """
    sub_agg = df.groupby("_std_sub_category", as_index=False)["_std_profit"].sum()
    sub_agg["_std_profit"] = _inr(sub_agg["_std_profit"])
    sub_agg = sub_agg.sort_values("_std_profit", ascending=True)

    colors = [CLR_RED if p < 0 else CLR_TEAL for p in sub_agg["_std_profit"]]

    fig = go.Figure(go.Bar(
        y=sub_agg["_std_sub_category"],
        x=sub_agg["_std_profit"],
        orientation="h",
        marker_color=colors,
        marker_line=dict(width=0),
        hovertemplate="<b>%{y}</b><br>Profit: ₹%{x:,.0f}<extra></extra>"
    ))

    _dark_chart_layout(fig, title="Profit by Sub-Category", height=400)
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.15)")
    fig.update_layout(yaxis_title=None, showlegend=False)
    fig.update_xaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_regional_profit_margins(df: pd.DataFrame) -> go.Figure:
    """
    Regional profit margins (%) with overall benchmark line.
    """
    reg_agg = df.groupby("_std_region", as_index=False).agg({
        "_std_sales": "sum",
        "_std_profit": "sum"
    })
    reg_agg["Margin_Pct"] = (reg_agg["_std_profit"] / reg_agg["_std_sales"] * 100).round(2)
    reg_agg = reg_agg.sort_values("Margin_Pct", ascending=False)

    overall_margin = (df["_std_profit"].sum() / df["_std_sales"].sum() * 100) if df["_std_sales"].sum() > 0 else 0

    # Color bars based on whether above or below overall margin
    colors = [CLR_CYAN if m >= overall_margin else CLR_YELLOW for m in reg_agg["Margin_Pct"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=reg_agg["_std_region"],
        y=reg_agg["Margin_Pct"],
        name="Region Margin",
        marker_color=colors,
        marker_line=dict(width=0),
        hovertemplate="<b>%{x}</b>: %{y:.2f}%<extra></extra>"
    ))

    fig.add_hline(
        y=overall_margin,
        line_dash="dash",
        line_color=CLR_RED,
        line_width=2,
        annotation_text=f"Avg: {overall_margin:.1f}%",
        annotation_position="top right",
        annotation_font_color=CLR_RED,
        annotation_font_size=11
    )

    _dark_chart_layout(fig, title="Regional Profit Margins (%)", height=380)
    fig.update_layout(xaxis_title=None, yaxis_title="Margin (%)", showlegend=False)
    fig.update_yaxes(ticksuffix="%")
    return fig


def plot_top_products_bar(df: pd.DataFrame, metric: str = "Sales", n: int = 10) -> go.Figure:
    """Horizontal bar chart for top 10 products by Sales or Profit."""
    col = "_std_sales" if metric == "Sales" else "_std_profit"
    top_p = df.groupby("_std_product_name", as_index=False)[col].sum().sort_values(col, ascending=False).head(n)
    top_p[col] = _inr(top_p[col])
    top_p = top_p.sort_values(col, ascending=True)

    color = CLR_CYAN if metric == "Sales" else CLR_GREEN

    fig = go.Figure(go.Bar(
        y=top_p["_std_product_name"].str.slice(0, 32) + "...",
        x=top_p[col],
        orientation="h",
        marker_color=color,
        marker_line=dict(width=0),
        hovertemplate=f"<b>%{{y}}</b><br>{metric}: ₹%{{x:,.0f}}<extra></extra>"
    ))
    _dark_chart_layout(fig, title=f"Top {n} Products by {metric}", height=360)
    fig.update_layout(yaxis_title=None, showlegend=False)
    fig.update_xaxes(tickprefix="₹", tickformat="~s")
    return fig


def plot_customer_segment_donut(df: pd.DataFrame) -> go.Figure:
    """Customer segment sales share donut chart."""
    seg_agg = df.groupby("_std_segment", as_index=False)["_std_sales"].sum()
    seg_agg["_std_sales"] = _inr(seg_agg["_std_sales"])

    fig = go.Figure(go.Pie(
        labels=seg_agg["_std_segment"],
        values=seg_agg["_std_sales"],
        hole=0.65,
        marker=dict(
            colors=[CLR_CYAN, CLR_GREEN, CLR_YELLOW, CLR_PURPLE, CLR_ORANGE],
            line=dict(color=BG_CHART, width=2)
        ),
        textinfo="label+percent",
        textfont=dict(size=11, color=CLR_TEXT),
        hovertemplate="<b>%{label}</b><br>Sales: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>"
    ))
    _dark_chart_layout(fig, title="Sales by Customer Segment", height=360)
    fig.update_layout(showlegend=True)
    return fig
