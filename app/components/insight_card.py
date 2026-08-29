"""Reusable diagnostic insight card."""

import streamlit as st


def insight_card(label: str, headline: str, detail: str, tone: str = "blue") -> None:
    st.markdown(
        f'<div class="insight-card tone-{tone}"><div class="insight-label">{label}</div><div class="insight-headline">{headline}</div><div class="insight-detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )
