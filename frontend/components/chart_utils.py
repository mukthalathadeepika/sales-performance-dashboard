"""Shared Plotly render helper with unique keys and optional click-to-filter."""

from typing import Optional
import streamlit as st
from frontend.components.charts import PLOTLY_CONFIG


def render_plotly(fig, key: str, click_filter_key: Optional[str] = None, click_label_keys=None):
    """Render a Plotly figure with toolbar. Optionally store clicked label into session state."""
    kwargs = {
        "use_container_width": True,
        "key": key,
        "config": PLOTLY_CONFIG,
    }
    event = None
    try:
        event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", **kwargs)
    except TypeError:
        st.plotly_chart(fig, **kwargs)
        return

    if not click_filter_key or event is None:
        return
    selection = getattr(event, "selection", None)
    if selection is None:
        return
    points = selection.get("points") if isinstance(selection, dict) else getattr(selection, "points", None)
    if not points:
        return
    pt = points[0]
    label = None
    if isinstance(pt, dict):
        label = pt.get("y") or pt.get("x") or pt.get("label") or pt.get("location")
    if label is None:
        return
    label = str(label).replace("...", "").strip()
    pending = dict(st.session_state.get("pending_click_filters") or {})
    pending[click_filter_key] = [label]
    level = {
        "flt_cats": "Category",
        "flt_subcats": "Sub-Category",
        "flt_regions": "Region",
        "flt_states": "State",
        "flt_cities": "City",
        "flt_segs": "Segment",
    }.get(click_filter_key, click_filter_key)
    path = list(st.session_state.get("drill_path") or [])
    path.append({"level": level, "value": label})
    pending["drill_path"] = path
    st.session_state["pending_click_filters"] = pending
    st.rerun()
