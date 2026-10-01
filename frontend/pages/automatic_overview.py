"""
frontend/pages/automatic_overview.py
Automated Executive Briefing & Data-Grounded Insights.
Generates narrative highlights, driver cards, anomaly flags, and PDF exports.
Strictly implements PRD Section 2.1, 5.3, and 5.4.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from backend.analytics.kpi import calculate_kpis
from backend.analytics.insights import generate_executive_insights
from backend.analytics.categories import get_category_breakdown
from backend.analytics.geography import get_state_breakdown
from backend.exports.exporter import generate_executive_pdf, export_to_excel


def render_automatic_overview_page(filtered_df: pd.DataFrame, meta: Dict[str, Any]):
    """Renders automated executive narrative summary and exportable briefing."""
    st.markdown("## ⚡ Automatic Executive Overview & Insights")
    st.markdown(
        "Automated summary generated from deterministic calculations. "
        "Highlights key sales drivers, regional leaders, growth rates, and transaction outliers."
    )

    sym = meta.get("currency_symbol", "$")
    target = meta.get("sales_target")

    if filtered_df is None or len(filtered_df) == 0:
        st.warning("No data loaded. Please upload a dataset or load the reference sample.")
        return

    kpis = calculate_kpis(filtered_df, sales_target=target)
    insights = generate_executive_insights(filtered_df)
    cat_df = get_category_breakdown(filtered_df)
    state_df = get_state_breakdown(filtered_df)

    # 1. Executive Briefing Narrative
    st.markdown("### 📋 Executive Takeaways")
    b_col1, b_col2 = st.columns([3, 1])

    with b_col1:
        if insights["summary_bullets"]:
            for b in insights["summary_bullets"]:
                st.markdown(f"- {b}")
        else:
            st.write("Sufficient dimensions not available for narrative generation.")

    with b_col2:
        date_str = "Full Dataset (2019-2020)"
        if meta.get("date_range"):
            d1, d2 = meta["date_range"]
            date_str = f"{d1} to {d2}"
        
        pdf_bytes = generate_executive_pdf(
            kpis=kpis,
            findings=insights["findings"],
            date_range_str=date_str,
            cat_df=cat_df,
            state_df=state_df,
            currency_symbol=sym
        )
        st.download_button(
            label="📄 Download Executive PDF Briefing",
            data=pdf_bytes,
            file_name="executive_sales_briefing.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Key Driver Insight Cards
    st.markdown("### 💡 Key Performance Drivers")
    findings = insights["findings"]
    if findings:
        cols = st.columns(min(len(findings), 3))
        for idx, finding in enumerate(findings[:6]):
            col_target = cols[idx % 3]
            with col_target:
                border_color = "#10B981" if finding["type"] == "positive" else "#F59E0B" if finding["type"] == "warning" else "#2563EB"
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-top: 3px solid {border_color}; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: #64748B; margin-bottom: 4px;">{finding['category']}</div>
                    <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 6px;">{finding['title']}</div>
                    <div style="font-size: 0.85rem; color: #334155; line-height: 1.4;">{finding['text']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Transaction Anomalies & Review Table (PRD Section 5.3)
    st.markdown("### ⚠️ Transaction Anomaly & Outlier Review")
    st.caption("Flags top 0.5% high-value sales transactions and notable loss-making items for executive inspection.")

    anomalies = insights["anomalies"]
    if not anomalies.empty:
        st.dataframe(anomalies, use_container_width=True)
    else:
        st.info("No transaction anomalies detected in current slice.")
