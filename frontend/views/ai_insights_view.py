"""
frontend/views/ai_insights_view.py
AI Insights & Sales Assistant view with dark navy theme.
Combines:
1. "Ask Your Data" Sales Assistant (deterministic NL querying with INR & charts)
2. Automated Business Insights (narrative findings, performance drivers, PDF export)
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px

from backend.chat.engine import process_query, EXAMPLE_PROMPTS
from backend.analytics.insights import generate_executive_insights
from backend.analytics.kpi import calculate_kpis
from backend.analytics.categories import get_category_breakdown
from backend.analytics.geography import get_state_breakdown
from backend.exports.exporter import generate_executive_pdf
from backend.analytics.currency import format_inr
from frontend.components.charts import _dark_chart_layout, CLR_CYAN, BG_PAPER, BG_CHART, CLR_TEXT


def render_ai_insights_view(df: pd.DataFrame):
    """Renders the AI Insights & Sales Assistant page."""
    st.markdown("""
    <div class="dash-header-wrap">
        <div>
            <h1 class="dash-header-title">AI Insights & Sales Assistant</h1>
            <div class="dash-header-subtitle">Ask questions about your data and explore automated performance findings</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.info("No active dataset loaded.")
        return

    tab_chat, tab_auto = st.tabs(["💬 Ask Your Data", "⚡ Automated Insights"])

    # TAB 1: Conversational Sales Assistant
    with tab_chat:
        st.markdown("#### Ask a Sales Question")
        st.caption("Click any sample question or type your own. Answers are calculated from active data in ₹.")

        # Quick clickable chips
        col_c1, col_c2 = st.columns(2)
        clicked_query = None

        with col_c1:
            for p in EXAMPLE_PROMPTS[:4]:
                if st.button(f"👉 {p}", key=f"btn_p_{p}", use_container_width=True):
                    clicked_query = p

        with col_c2:
            for p in EXAMPLE_PROMPTS[4:8]:
                if st.button(f"👉 {p}", key=f"btn_p_{p}", use_container_width=True):
                    clicked_query = p

        user_input = st.chat_input("Ask a question about sales, categories, regions, or products...")
        query_to_run = clicked_query or user_input

        if "sales_chat_history" not in st.session_state:
            st.session_state["sales_chat_history"] = []

        if query_to_run:
            query_result = process_query(query_to_run, df, currency_symbol="₹")
            st.session_state["sales_chat_history"].append({
                "question": query_to_run,
                "response": query_result
            })

        # Display latest responses
        if st.session_state["sales_chat_history"]:
            st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
            for idx, item in enumerate(reversed(st.session_state["sales_chat_history"][-4:])):
                q = item["question"]
                res = item["response"]

                st.markdown(f"**🧑 You:** *{q}*")

                if res.get("is_unsupported"):
                    st.warning(f"**Assistant:** {res['answer_text']}")
                else:
                    st.success(f"**Assistant:** {res['answer_text']}")

                # Render chart if provided
                chart_data = res.get("chart_data")
                chart_type = res.get("chart_type")

                if chart_data is not None and not chart_data.empty:
                    cols = list(chart_data.columns)
                    if len(cols) >= 2:
                        x_col, y_col = cols[0], cols[1]
                        fig = px.bar(
                            chart_data,
                            x=x_col,
                            y=y_col,
                            color_discrete_sequence=[CLR_CYAN],
                            text=y_col
                        )
                        fig.update_traces(texttemplate="₹%{y:,.0f}", textposition="inside")
                        _dark_chart_layout(fig, title=f"{y_col} by {x_col}", height=300)
                        st.plotly_chart(fig, key=f"chat_chart_{idx}", use_container_width=True, config={"displayModeBar": False})

                st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

    # TAB 2: Automated Business Insights
    with tab_auto:
        insights = generate_executive_insights(df)
        kpis = calculate_kpis(df)
        cat_df = get_category_breakdown(df)
        state_df = get_state_breakdown(df)

        st.markdown("### 📋 Executive Takeaways")
        summary_bullets = insights.get("summary_bullets", [])
        if summary_bullets:
            for bullet in summary_bullets:
                st.markdown(f"- {bullet}")

        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.markdown("### 🔍 Key Performance Drivers")

        findings = insights.get("findings", [])
        if findings:
            f_cols = st.columns(min(len(findings), 3))
            for idx, finding in enumerate(findings[:6]):
                col = f_cols[idx % 3]
                with col:
                    box_cls = "green" if finding["type"] == "positive" else "orange" if finding["type"] == "warning" else ""
                    st.markdown(f"""
                    <div class="insight-box {box_cls}">
                        <div class="insight-tag">{finding['category']}</div>
                        <div class="insight-headline">{finding['title']}</div>
                        <div class="insight-desc">{finding['text']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.markdown("### ⚠️ Transaction Anomalies")
        anomalies = insights.get("anomalies", pd.DataFrame())
        if not anomalies.empty:
            st.dataframe(anomalies, use_container_width=True, hide_index=True)
        else:
            st.caption("No significant anomalies detected in the current filtered records.")

        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        st.markdown("### 📄 Export Executive Report")

        pdf_bytes = generate_executive_pdf(
            kpis=kpis,
            findings=findings,
            date_range_str="Active Filtered Scope",
            cat_df=cat_df,
            state_df=state_df,
            currency_symbol="₹"
        )
        st.download_button(
            label="📥 Download Executive Briefing (PDF)",
            data=pdf_bytes,
            file_name="sales_performance_briefing.pdf",
            mime="application/pdf",
            type="primary"
        )
