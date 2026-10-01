"""
frontend/views/ai_insights_view.py
Simple, data-driven Automated Business Insights view.
Calculates and presents executive findings, key drivers, and anomaly flags
without requiring external LLM APIs.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from backend.analytics.insights import generate_executive_insights
from backend.analytics.kpi import calculate_kpis
from backend.analytics.categories import get_category_breakdown
from backend.analytics.geography import get_state_breakdown
from backend.exports.exporter import generate_executive_pdf


def render_ai_insights_view(df: pd.DataFrame, currency_symbol: str = "$"):
    """Renders the Automated Business Insights view."""
    st.markdown("""
    <div class="dashboard-header">
        <h1 class="dashboard-title">Automated Business Insights</h1>
        <div class="dashboard-subtitle">Data-driven findings and performance drivers calculated directly from sales transactions</div>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.info("No active dataset loaded.")
        return

    sym = currency_symbol
    insights = generate_executive_insights(df)
    kpis = calculate_kpis(df)
    cat_df = get_category_breakdown(df)
    state_df = get_state_breakdown(df)

    # 1. Executive Summary Narrative
    st.markdown("### 📋 Executive Takeaways")
    summary_bullets = insights.get("summary_bullets", [])
    if summary_bullets:
        for bullet in summary_bullets:
            st.markdown(f"- {bullet}")
    else:
        st.write("Sufficient data dimensions are not available to produce automated takeaways.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Key Driver Cards
    st.markdown("### 🔍 Key Performance Drivers")
    findings = insights.get("findings", [])
    if findings:
        cols = st.columns(min(len(findings), 3))
        for idx, finding in enumerate(findings[:6]):
            col = cols[idx % 3]
            with col:
                st.markdown(f"""
                <div class="insight-card">
                    <div class="insight-card-title">{finding['category']}</div>
                    <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 0.35rem;">
                        {finding['title']}
                    </div>
                    <div style="font-size: 0.88rem; color: #334155; line-height: 1.45;">
                        {finding['text']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Notable High-Value Transaction Review
    st.markdown("### ⚠️ High-Impact Transaction Outliers")
    st.caption("Top sales transactions identified for review:")

    anomalies = insights.get("anomalies", pd.DataFrame())
    if not anomalies.empty:
        st.dataframe(anomalies, use_container_width=True)
    else:
        st.info("No transaction outliers identified in the current dataset.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Export PDF Report
    st.markdown("### 📄 Export Insights")
    date_str = "Full Dataset (2019–2020)"
    if "_std_order_date" in df.columns:
        valid_d = df["_std_order_date"].dropna()
        if len(valid_d) > 0:
            date_str = f"{valid_d.min().strftime('%Y-%m-%d')} to {valid_d.max().strftime('%Y-%m-%d')}"

    pdf_data = generate_executive_pdf(
        kpis=kpis,
        findings=findings,
        date_range_str=date_str,
        cat_df=cat_df,
        state_df=state_df,
        currency_symbol=sym
    )

    st.download_button(
        label="📥 Download Executive Summary PDF Report",
        data=pdf_data,
        file_name="executive_sales_insights.pdf",
        mime="application/pdf",
        type="primary"
    )
