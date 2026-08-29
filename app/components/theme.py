"""Shared dashboard theme and page chrome."""

from pathlib import Path
from datetime import datetime

import streamlit as st

from app.i18n import sync_language, tr


def inject_theme() -> None:
    css = (Path(__file__).resolve().parents[1] / "styles" / "styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str, data_through: str) -> None:
    if "language_choice" not in st.session_state:
        st.session_state["language_choice"] = "中文" if st.session_state.get("language_zh", False) else "EN"
    _, language_col = st.columns([8.5, 1.5])
    with language_col:
        st.selectbox("Language / 语言", ["EN", "中文"], key="language_choice", on_change=sync_language)
    if st.session_state.get("language_zh"):
        try:
            data_through = datetime.strptime(data_through, "%b %d, %Y").strftime("%Y年%m月%d日")
        except ValueError:
            pass
    st.markdown(
        f"""
        <div class="page-header">
          <div><h1>{title}</h1><p>{subtitle}</p></div>
          <div class="header-meta"><span>{tr('Data through:', '数据截至：')} <strong>{data_through}</strong></span><span class="badge badge-blue">{tr('SYNTHETIC DATA', '虚构数据')}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="section-header"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
