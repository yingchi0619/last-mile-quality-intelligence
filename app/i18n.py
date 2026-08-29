"""Global bilingual state and lightweight UI localization helpers."""

from __future__ import annotations

import streamlit as st


def is_zh() -> bool:
    """Return the session-wide language selection."""
    return bool(st.session_state.get("language_zh", False))


def tr(english: str, chinese: str) -> str:
    """Select English or Chinese using the shared session state."""
    return chinese if is_zh() else english


def sync_language() -> None:
    """Synchronize the visible selector with the session-wide language flag."""
    st.session_state["language_zh"] = st.session_state.get("language_choice", "EN") == "中文"


def local_status(status: str) -> str:
    """Translate standard operating-status values for display."""
    if not is_zh():
        return status
    return {"Healthy": "健康", "Watch": "关注", "At Risk": "风险"}.get(status, status)


def local_risk(risk: str) -> str:
    """Translate route-risk tiers for display without changing model data."""
    if not is_zh():
        return risk
    return {"High Risk": "高风险", "Medium Risk": "中风险", "Low Risk": "低风险"}.get(risk, risk)
