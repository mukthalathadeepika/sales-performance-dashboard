"""
frontend/pages/chat_view.py
Natural Language Sales Query Interface.
Executes deterministic queries using Pandas, shows concise text answers,
and renders visual results directly on the main screen per PRD Section 2.4, 5.1, and 5.2.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px

from backend.chat.engine import process_query, EXAMPLE_PROMPTS
from frontend.components.charts import _apply_standard_layout


def render_chat_page(df: pd.DataFrame, meta: Dict[str, Any]):
    """Renders natural language query workspace."""
    st.markdown("## 💬 Natural Language Sales Assistant")
    st.markdown(
        "Ask plain-English questions about sales, profits, rankings, categories, or trends. "
        "Calculations are strictly deterministic with no external AI API dependency."
    )

    sym = meta.get("currency_symbol", "$")

    if df is None or len(df) == 0:
        st.warning("No data loaded. Please upload a dataset or load the reference sample.")
        return

    # Example Prompt Suggestions (PRD Section 5.1)
    st.markdown("##### 💡 Suggested Questions (Click to run):")
    cols = st.columns(3)
    clicked_prompt = None
    for idx, prompt_text in enumerate(EXAMPLE_PROMPTS[:6]):
        with cols[idx % 3]:
            if st.button(f"💬 {prompt_text}", key=f"chip_{idx}", use_container_width=True):
                clicked_prompt = prompt_text

    # Query Input
    user_query = st.chat_input("Ask a question about your sales data...")
    if clicked_prompt:
        user_query = clicked_prompt

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Process Query
    if user_query:
        query_result = process_query(user_query, df, currency_symbol=sym)
        st.session_state["chat_history"].append({
            "query": user_query,
            "result": query_result
        })

    # Render Active Query Result
    if st.session_state["chat_history"]:
        last_exchange = st.session_state["chat_history"][-1]
        q_text = last_exchange["query"]
        res = last_exchange["result"]

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"#### ❓ Question: *\"{q_text}\"*")

        # Answer Bubble
        if res.get("is_unsupported"):
            st.warning(f"**Answer:** {res['answer_text']}")
        else:
            st.success(f"**Answer:** {res['answer_text']}")

        # Context & Fields Used (PRD Section 5.2)
        ctx = res.get("context", {})
        fields_str = ", ".join(ctx.get("fields_used", [])) if ctx.get("fields_used") else "Standard Sales Data"
        st.caption(f"ℹ️ **Calculation Context:** Fields Used: [{fields_str}] | Scope: {ctx.get('date_coverage', 'Active filter')}")

        # Render Main-Canvas Visual if requested or available (PRD Section 2.4 & 5.2)
        chart_data = res.get("chart_data")
        chart_type = res.get("chart_type")

        if chart_data is not None and not chart_data.empty:
            st.markdown("### 📊 Visual Result (Rendered on Main Canvas)")
            cols_list = list(chart_data.columns)

            if len(cols_list) >= 2:
                dim_col, val_col = cols_list[0], cols_list[1]
                
                # Render chart according to type
                if chart_type == "bar":
                    fig = px.bar(
                        chart_data,
                        x=dim_col,
                        y=val_col,
                        color=val_col,
                        color_continuous_scale="Blues",
                        text_auto=".2s"
                    )
                    _apply_standard_layout(fig, title=f"{val_col} by {dim_col}")
                    st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "pie":
                    fig = px.pie(
                        chart_data,
                        names=dim_col,
                        values=val_col,
                        hole=0.4
                    )
                    _apply_standard_layout(fig, title=f"{val_col} Distribution")
                    st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "line":
                    fig = px.line(
                        chart_data,
                        x=dim_col,
                        y=val_col,
                        markers=True
                    )
                    _apply_standard_layout(fig, title=f"{val_col} Trend")
                    st.plotly_chart(fig, use_container_width=True)

                # Accompanying Data Table (PRD Section 2.4)
                with st.expander("📋 View Underlying Data Table"):
                    st.dataframe(chart_data, use_container_width=True)
