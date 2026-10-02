"""
frontend/views/ai_assistant_view.py
AI Sales Assistant with enhanced NLP, chart generation, follow-up support,
and clean chat display (not an endless transcript).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.chat.engine import process_query, EXAMPLE_PROMPTS
from backend.analytics.currency import convert_series_to_inr, format_inr
from frontend.components.chart_utils import render_plotly

PALETTE = ["#00D4FF", "#22C55E", "#FACC15", "#A78BFA", "#F97316", "#EF4444", "#14B8A6", "#3B82F6"]
BG_CHART = "#162040"
CLR_TEXT = "#E2E8F0"
CLR_MUTED = "#94A3B8"


def _apply_dark(fig, title="", h=350):
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.96, font=dict(size=13, color=CLR_TEXT, family="Inter, sans-serif")),
        template="plotly_dark", paper_bgcolor=BG_CHART, plot_bgcolor=BG_CHART, height=h,
        margin=dict(l=12, r=12, t=45, b=25),
        hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_color=CLR_TEXT),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=10, color=CLR_MUTED))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=10, color=CLR_MUTED))
    return fig


def render_ai_assistant_view(df: pd.DataFrame):
    """Renders the AI Sales Assistant page."""
    st.markdown("""
    <div class="dash-header">
        <h1 class="dash-title">AI Sales Assistant</h1>
        <div class="dash-subtitle">Ask any question about your active dataset — answers are calculated directly from the data</div>
    </div>
    """, unsafe_allow_html=True)

    if df is None or len(df) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🤖</div>
            <div class="empty-state-title">No Dataset Loaded</div>
            <div class="empty-state-desc">Upload a dataset to start asking questions about your sales data.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Initialize chat state
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "chat_context" not in st.session_state:
        st.session_state["chat_context"] = {}

    # Clear Chat button
    col_hdr, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("Clear Chat", key="ai_clear_chat", use_container_width=True):
            st.session_state["chat_history"] = []
            st.session_state["chat_context"] = {}
            st.rerun()

    # Sample questions (compact)
    st.caption("Try asking:")
    cols = st.columns(4)
    clicked_query = None
    for i, prompt in enumerate(EXAMPLE_PROMPTS[:8]):
        with cols[i % 4]:
            if st.button(prompt, key=f"ai_sample_{i}", use_container_width=True):
                clicked_query = prompt

    st.markdown("---")

    # Chat input
    user_input = st.chat_input("Ask a question about your sales data...")
    query = clicked_query or user_input

    if query:
        # Build context from previous interaction for follow-ups
        prev_context = st.session_state.get("chat_context", {})
        result = process_query(query, df, currency_symbol="₹", prev_context=prev_context)

        # Store in history (keep only last 20 for memory)
        st.session_state["chat_history"].append({"q": query, "r": result})
        if len(st.session_state["chat_history"]) > 20:
            st.session_state["chat_history"] = st.session_state["chat_history"][-20:]

        # Update context for follow-ups
        st.session_state["chat_context"] = result.get("context", {})

    # Display ONLY the last interaction prominently + compact history
    history = st.session_state.get("chat_history", [])

    if history:
        # Show the latest Q&A prominently
        latest = history[-1]
        st.markdown(f"**You:** {latest['q']}")

        res = latest["r"]
        if res.get("is_unsupported"):
            st.warning(f"{res['answer_text']}")
        else:
            st.success(f"{res['answer_text']}")

        # Context / Filters used
        ctx = res.get("context", {})
        ctx_parts = []
        if ctx.get("last_dimension"):
            ctx_parts.append(f"Dimension: **{str(ctx['last_dimension']).title()}**")
        if ctx.get("last_metric"):
            ctx_parts.append(f"Metric: **{str(ctx['last_metric']).title()}**")
        if ctx.get("last_entity"):
            ctx_parts.append(f"Entity: **{ctx['last_entity']}**")
        if ctx.get("date_coverage") and ctx["date_coverage"] != "Active Scope":
            ctx_parts.append(f"Dates: **{ctx['date_coverage']}**")
        if ctx_parts:
            st.caption(" · ".join(ctx_parts))

        # Render chart if provided
        chart_data = res.get("chart_data")
        if chart_data is not None and isinstance(chart_data, pd.DataFrame) and not chart_data.empty:
            plot_df = chart_data.copy()
            cols_list = list(plot_df.columns)
            if len(cols_list) >= 2:
                x_col, y_col = cols_list[0], cols_list[1]
                if y_col in ("Sales", "Profit", "Net Loss", "Average Order Value"):
                    plot_df[y_col] = convert_series_to_inr(plot_df[y_col])
                chart_type = res.get("chart_type", "bar")

                if chart_type == "line":
                    fig = px.line(plot_df, x=x_col, y=y_col, color_discrete_sequence=PALETTE, markers=True)
                elif chart_type == "pie":
                    fig = px.pie(plot_df, names=x_col, values=y_col, color_discrete_sequence=PALETTE, hole=0.4)
                else:
                    fig = px.bar(plot_df, x=x_col, y=y_col, color_discrete_sequence=PALETTE)

                _apply_dark(fig, f"{y_col} by {x_col}", 320)
                render_plotly(fig, key="ai_latest_chart")

                # Supporting data table per Section 17
                with st.expander("Supporting Data Table", expanded=True):
                    show_table = plot_df.copy()
                    if y_col in ("Sales", "Profit", "Net Loss", "Average Order Value"):
                        show_table[y_col] = show_table[y_col].apply(lambda v: format_inr(v, convert=False))
                    st.dataframe(show_table, use_container_width=True, hide_index=True)

        # Show compact previous history (collapsed)
        if len(history) > 1:
            with st.expander(f"Previous Questions ({len(history)-1})", expanded=False):
                for i, item in enumerate(reversed(history[:-1])):
                    st.markdown(f"**Q:** {item['q']}")
                    r = item["r"]
                    status = "⚠️" if r.get("is_unsupported") else "✅"
                    st.caption(f"{status} {r['answer_text'][:200]}...")
                    if i < len(history) - 2:
                        st.markdown("<hr style='margin:0.3rem 0;border-color:rgba(255,255,255,0.06)'>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#64748B;">
            <p style="font-size:1.1rem;">Ask a question to get started</p>
            <p style="font-size:0.85rem;">Examples: "What is the total sales?" · "Which region performs best?" · "Show top 5 products"</p>
        </div>
        """, unsafe_allow_html=True)
