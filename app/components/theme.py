"""Shared dashboard theme and page chrome."""

from pathlib import Path

import streamlit as st


def inject_theme() -> None:
    css = (Path(__file__).resolve().parents[1] / "styles" / "styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str, data_through: str) -> None:
    st.markdown(
        f"""
        <div class="page-header">
          <div><h1>{title}</h1><p>{subtitle}</p></div>
          <div class="header-meta"><span>Data through: <strong>{data_through}</strong></span><span class="badge badge-blue">SYNTHETIC DATA</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="section-header"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
