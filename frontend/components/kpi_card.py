"""
frontend/components/kpi_card.py
Renders executive KPI metric cards with custom HTML/CSS styling.
"""

from typing import Optional
import streamlit as st


def render_kpi_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_positive: Optional[bool] = None,
    subtitle: Optional[str] = None,
    icon: str = "📊",
    border_accent: Optional[str] = None
):
    """Renders a single high-contrast executive KPI card."""
    delta_html = ""
    if delta is not None:
        if delta_positive is True:
            delta_class = "delta-pos"
            arrow = "▲ "
        elif delta_positive is False:
            delta_class = "delta-neg"
            arrow = "▼ "
        else:
            delta_class = "delta-neu"
            arrow = "• "
        delta_html = f'<span class="delta-badge {delta_class}">{arrow}{delta}</span>'

    sub_html = f'<span style="color: #64748B;">{subtitle}</span>' if subtitle else ""
    border_style = f"border-top: 3px solid {border_accent};" if border_accent else ""

    card_html = f"""
    <div class="kpi-card" style="{border_style}">
        <div class="kpi-card-header">
            <span class="kpi-title">{title}</span>
            <span class="kpi-icon">{icon}</span>
        </div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-footer">
            {delta_html}
            {sub_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
