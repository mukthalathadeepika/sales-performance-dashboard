"""
frontend/pages/home.py
Landing page presenting the four analysis paths and welcoming introduction.
Strictly implements PRD Section 2.1 and 2.2.
"""

import streamlit as st


def render_home_page():
    """Renders the executive landing page with 4 option cards and quick start actions."""
    st.markdown("""
    <div style="text-align: center; max-width: 800px; margin: 0 auto 2.5rem auto;">
        <h1 style="font-size: 2.3rem; font-weight: 800; color: #0F172A; margin-bottom: 0.8rem; letter-spacing: -0.03em;">
            Sales Performance Dashboard
        </h1>
        <p style="font-size: 1.05rem; color: #475569; line-height: 1.6;">
            A modern business intelligence platform to explore, compare, and query sales data.
            Upload any sales spreadsheet or load the verified reference dataset to get started instantly.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Four Path Option Cards (PRD Section 2.1)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="mode-card">
            <div>
                <div class="mode-card-icon">📊</div>
                <div class="mode-card-title">Explore Dashboard</div>
                <div class="mode-card-desc">
                    Inspect interactive KPI cards, monthly trends, regional drill-downs, and customizable filters.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Explore Dashboard →", key="btn_path_dash", use_container_width=True):
            st.session_state["nav_page"] = "Dashboard"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="mode-card">
            <div>
                <div class="mode-card-icon">🔍</div>
                <div class="mode-card-title">Build an Analysis</div>
                <div class="mode-card-desc">
                    Pick a question, choose custom measures, select groupings, and customize your visual format.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Build Analysis →", key="btn_path_analysis", use_container_width=True):
            st.session_state["nav_page"] = "Guided Analysis"
            st.rerun()

    with col3:
        st.markdown("""
        <div class="mode-card">
            <div>
                <div class="mode-card-icon">⚡</div>
                <div class="mode-card-title">Automatic Overview</div>
                <div class="mode-card-desc">
                    Receive data-grounded narrative takeaways, driver highlights, anomaly alerts, and PDF export.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Overview →", key="btn_path_overview", use_container_width=True):
            st.session_state["nav_page"] = "Automatic Overview"
            st.rerun()

    with col4:
        st.markdown("""
        <div class="mode-card">
            <div>
                <div class="mode-card-icon">💬</div>
                <div class="mode-card-title">Ask in Chat</div>
                <div class="mode-card-desc">
                    Ask questions in plain language; receive exact calculated answers and rendered charts on screen.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ask in Chat →", key="btn_path_chat", use_container_width=True):
            st.session_state["nav_page"] = "Ask in Chat"
            st.rerun()

    st.markdown("<br><hr style='border: none; border-top: 1px solid #E2E8F0; margin: 2rem 0;'><br>", unsafe_allow_html=True)

    # Quick Start Actions: Sample Dataset or Custom File
    q_col1, q_col2 = st.columns([1, 1])

    with q_col1:
        st.markdown("### 📁 Quick Preview: Reference Dataset")
        st.info(
            "Load the reference **SuperStore Sales Dataset** (5,901 rows, 2019-2020) "
            "to explore the full suite of interactive charts and audits immediately."
        )
        if st.button("⚡ Load SuperStore Reference Dataset", type="primary", use_container_width=True):
            st.session_state["load_sample_trigger"] = True
            st.session_state["nav_page"] = "Dashboard"
            st.rerun()

    with q_col2:
        st.markdown("### 📤 Upload Your Own File")
        st.markdown(
            "Upload a sales dataset in **CSV**, **Excel (.xlsx)**, or **TSV** format. "
            "The system automatically maps columns and reports data quality."
        )
        if st.button("Go to Data Upload & Quality →", use_container_width=True):
            st.session_state["nav_page"] = "Data Quality & Mapping"
            st.rerun()
