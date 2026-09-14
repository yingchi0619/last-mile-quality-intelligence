"""Independent real East Coast ZIP difficulty page."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.charts import BLUE, ORANGE, RED, SLATE, style_figure
from app.components.kpi_card import kpi_card
from app.components.theme import section_header
from app.i18n import sync_language, tr
from src.analytics.database import project_root

REAL_DATA_PATH = Path("data/real/理赔分析.xlsx")
ZIP_CENTROID_PATH = Path("data/real/us_zip_centroids.csv")
EAST_REGION_CODES = {"NE", "EAST", "东区", "美东", "美东区"}
EASTERN_STATES = {"CT", "DC", "DE", "MA", "MD", "ME", "NH", "NJ", "NY", "PA", "RI", "VA", "VT"}


def _normalize_zip(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if "." in text:
        text = text.split(".", 1)[0]
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    return digits[:5].zfill(5)


def _flatten_summary_headers(raw: pd.DataFrame) -> pd.DataFrame:
    headers = []
    for left, right in zip(raw.iloc[0], raw.iloc[1]):
        left_text = "" if pd.isna(left) else str(left).strip()
        right_text = "" if pd.isna(right) else str(right).strip()
        headers.append(right_text or left_text)
    data = raw.iloc[2:].copy()
    data.columns = headers
    return data


def _score(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0)
    max_value = values.max()
    if max_value <= 0:
        return values * 0
    return values / max_value


def _recommendation(claim_type: object) -> str:
    text = "" if pd.isna(claim_type) else str(claim_type)
    if "丢" in text or "遗失" in text:
        return "加强丢件复盘，抽查交接扫描和异常闭环"
    if "破" in text or "损" in text:
        return "重点复核装卸、分拣和包装保护动作"
    if "延" in text or "迟" in text:
        return "检查提货准点率、线路波次和末端交付节奏"
    return "按邮编建立真实理赔周监控，优先复查高金额样本"


@st.cache_data(show_spinner=False)
def load_real_zip_claims() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    root = project_root()
    workbook_path = root / REAL_DATA_PATH
    fallback_path = Path("/Users/junie/Downloads/理赔分析.xlsx")
    if not workbook_path.exists() and fallback_path.exists():
        workbook_path = fallback_path

    centroid_path = root / ZIP_CENTROID_PATH
    if not workbook_path.exists():
        return pd.DataFrame(), pd.DataFrame(), {"error": f"Missing workbook: {root / REAL_DATA_PATH}"}
    if not centroid_path.exists():
        return pd.DataFrame(), pd.DataFrame(), {"error": f"Missing ZIP centroid file: {centroid_path}"}

    detail = pd.read_excel(workbook_path, sheet_name="【账单明细】", engine="openpyxl")
    dsp_raw = pd.read_excel(workbook_path, sheet_name="【DSP维度】", header=None, engine="openpyxl")
    dsp_summary = _flatten_summary_headers(dsp_raw)

    dsp_map = dsp_summary.rename(columns={"DSP": "dsp", "大区": "region", "站点": "station"})
    dsp_map = dsp_map[[col for col in ["dsp", "region", "station"] if col in dsp_map.columns]].dropna(subset=["dsp"]).drop_duplicates("dsp")

    claims = pd.DataFrame(
        {
            "zip": detail["邮编"].map(_normalize_zip),
            "amount": pd.to_numeric(detail["费用(含税)"], errors="coerce").abs(),
            "date": pd.to_datetime(detail["业务日期"], errors="coerce"),
            "direction": pd.to_numeric(detail["扣款/回款"], errors="coerce"),
            "owner": detail["供应商"].astype(str),
            "dsp": detail["车队"].astype(str),
            "claim_type": detail["理赔类型"].astype(str),
        }
    )
    claims = claims[(claims["direction"] == 1) & claims["zip"].notna() & claims["amount"].notna() & (claims["amount"] > 0)].copy()
    claims = claims.merge(dsp_map, on="dsp", how="left")
    region_key = claims["region"].astype(str).str.upper().str.strip()
    claims = claims[region_key.isin(EAST_REGION_CODES) | claims["region"].astype(str).str.strip().isin(EAST_REGION_CODES)].copy()

    centroids = pd.read_csv(centroid_path, dtype={"zip": str})
    centroids["zip"] = centroids["zip"].map(_normalize_zip)
    claims = claims.merge(centroids[["zip", "place_name", "state", "lat", "lon"]], on="zip", how="left")
    claims = claims[claims["lat"].notna() & claims["lon"].notna()].copy()

    if claims.empty:
        return pd.DataFrame(), pd.DataFrame(), {"error": "No mapped East Coast deduction claims were found in the workbook."}

    type_mix = (
        claims.groupby(["zip", "claim_type"], dropna=False)
        .agg(type_amount=("amount", "sum"), type_count=("amount", "size"))
        .reset_index()
        .sort_values(["zip", "type_amount"], ascending=[True, False])
        .drop_duplicates("zip")
    )
    top_owner = (
        claims.groupby(["zip", "owner"], dropna=False)["amount"]
        .sum()
        .reset_index()
        .sort_values(["zip", "amount"], ascending=[True, False])
        .drop_duplicates("zip")
        .rename(columns={"owner": "top_owner", "amount": "top_owner_amount"})
    )
    top_dsp = (
        claims.groupby(["zip", "dsp"], dropna=False)["amount"]
        .sum()
        .reset_index()
        .sort_values(["zip", "amount"], ascending=[True, False])
        .drop_duplicates("zip")
        .rename(columns={"dsp": "top_dsp", "amount": "top_dsp_amount"})
    )

    zip_summary = (
        claims.groupby(["zip", "place_name", "state", "lat", "lon"], dropna=False)
        .agg(
            claim_amount=("amount", "sum"),
            claim_count=("amount", "size"),
            avg_claim_amount=("amount", "mean"),
            owner_count=("owner", "nunique"),
            dsp_count=("dsp", "nunique"),
            first_claim_date=("date", "min"),
            last_claim_date=("date", "max"),
        )
        .reset_index()
        .merge(type_mix, on="zip", how="left")
        .merge(top_owner, on="zip", how="left")
        .merge(top_dsp, on="zip", how="left")
    )

    total_amount = float(zip_summary["claim_amount"].sum())
    zip_summary["amount_share"] = np.where(total_amount > 0, zip_summary["claim_amount"] / total_amount, 0)
    zip_summary["type_concentration"] = np.where(
        zip_summary["claim_amount"] > 0,
        zip_summary["type_amount"].fillna(0) / zip_summary["claim_amount"],
        0,
    )
    zip_summary["difficulty_score"] = (
        45 * _score(zip_summary["claim_amount"])
        + 25 * _score(zip_summary["claim_count"])
        + 20 * _score(zip_summary["avg_claim_amount"])
        + 10 * zip_summary["type_concentration"].fillna(0)
    ).round(1)
    zip_summary["difficulty_tier"] = pd.cut(
        zip_summary["difficulty_score"],
        bins=[-0.1, 45, 75, 100.1],
        labels=["C 常规", "B 关注", "A 高难度"],
    ).astype(str)
    zip_summary["action"] = zip_summary["claim_type"].map(_recommendation)

    meta = {
        "workbook": str(workbook_path),
        "claim_rows": int(len(claims)),
        "zip_count": int(zip_summary["zip"].nunique()),
        "claim_amount": total_amount,
        "date_min": claims["date"].min(),
        "date_max": claims["date"].max(),
    }
    return zip_summary.sort_values("difficulty_score", ascending=False), claims, meta


def _language_control() -> None:
    _, language_col = st.columns([8.5, 1.5])
    with language_col:
        if "language_choice" not in st.session_state:
            st.session_state.language_choice = "中文" if st.session_state.get("language_zh") else "EN"
        st.selectbox(
            "Language / 语言",
            ["EN", "中文"],
            key="language_choice",
            on_change=sync_language,
            label_visibility="collapsed",
        )


def _header(meta: dict[str, object]) -> None:
    _language_control()
    date_min = meta.get("date_min")
    date_max = meta.get("date_max")
    if pd.notna(date_min) and pd.notna(date_max):
        as_of = f"{pd.Timestamp(date_min):%Y-%m-%d} to {pd.Timestamp(date_max):%Y-%m-%d}"
    else:
        as_of = "Real workbook"
    st.markdown(
        f"""
        <div class="hero-panel">
            <div class="hero-eyebrow">{tr("REAL CLAIM DATA", "真实理赔数据")}</div>
            <div class="hero-title">{tr("East Coast ZIP Difficulty Map", "美东邮编难度地图")}</div>
            <div class="hero-subtitle">{tr(
                "A standalone ZIP-level claims view built from the real workbook. It replaces the former synthetic Route Risk module and is not joined to synthetic route-risk scores.",
                "基于真实 Excel 单独生成的邮编级理赔难度视图。本页已完全取代原来的虚构 Route Risk 模块，并且不与虚构路线风险分数混算。",
            )}</div>
            <div class="hero-meta">{as_of}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render(_routes: pd.DataFrame) -> None:
    zip_summary, claims, meta = load_real_zip_claims()
    if "error" in meta:
        _language_control()
        st.error(meta["error"])
        return

    _header(meta)

    filter_col, tier_col, toggle_col = st.columns([1.2, 1.2, 1])
    all_label = tr("All", "全部")
    with filter_col:
        states = [all_label] + sorted(zip_summary["state"].dropna().astype(str).unique())
        state_choice = st.selectbox(tr("State", "州"), states)
    with tier_col:
        tiers = [all_label, "A 高难度", "B 关注", "C 常规"]
        tier_choice = st.selectbox(tr("Difficulty Tier", "难度等级"), tiers)
    with toggle_col:
        eastern_only = st.toggle(tr("Common East Coast States", "仅显示常见美东州"), value=True)

    current = zip_summary.copy()
    if eastern_only:
        current = current[current["state"].isin(EASTERN_STATES)]
    if state_choice != all_label:
        current = current[current["state"] == state_choice]
    if tier_choice != all_label:
        current = current[current["difficulty_tier"] == tier_choice]

    if current.empty:
        st.info(tr("No ZIP codes match the current filters.", "当前筛选条件下没有匹配的邮编。"))
        return

    top_zip = current.sort_values("difficulty_score", ascending=False).iloc[0]
    cols = st.columns(5)
    with cols[0]:
        kpi_card(tr("Real Claim Rows", "真实理赔行数"), f"{meta['claim_rows']:,}", None, tr("East region deductions", "美东扣款理赔"))
    with cols[1]:
        kpi_card(tr("ZIP Codes", "邮编数量"), f"{current['zip'].nunique():,}", None, tr("selected", "当前筛选"))
    with cols[2]:
        kpi_card(tr("Claim Amount", "理赔金额"), f"${current['claim_amount'].sum():,.0f}", None, tr("selected ZIPs", "当前邮编"))
    with cols[3]:
        kpi_card(tr("High Difficulty ZIPs", "高难度邮编"), f"{int((current['difficulty_tier'] == 'A 高难度').sum()):,}", None, tr("A tier", "A 类"))
    with cols[4]:
        kpi_card(
            tr("Top ZIP", "最高难度邮编"),
            str(top_zip["zip"]),
            None,
            f"{top_zip['difficulty_score']:.1f} · {top_zip['place_name']}",
        )

    section_header(
        tr("ZIP Difficulty Map", "邮编难度地图"),
        tr("Bubble size follows real claim amount; color follows the independently calculated ZIP difficulty tier.", "气泡大小代表真实理赔金额，颜色代表独立计算的邮编难度等级。"),
    )
    color_map = {"A 高难度": RED, "B 关注": ORANGE, "C 常规": BLUE}
    fig = px.scatter_geo(
        current,
        lat="lat",
        lon="lon",
        size="claim_amount",
        color="difficulty_tier",
        color_discrete_map=color_map,
        hover_name="zip",
        hover_data={
            "place_name": True,
            "state": True,
            "claim_amount": ":$,.2f",
            "claim_count": ":,",
            "avg_claim_amount": ":$,.2f",
            "claim_type": True,
            "difficulty_score": ":.1f",
            "lat": False,
            "lon": False,
        },
        scope="usa",
        size_max=30,
    )
    fig.update_geos(
        projection_type="albers usa",
        showland=True,
        landcolor="#F8FAFC",
        showlakes=True,
        lakecolor="#E0F2FE",
        showcountries=False,
        showsubunits=True,
        subunitcolor="#CBD5E1",
        lonaxis_range=[-82, -66],
        lataxis_range=[37, 46],
    )
    fig.update_layout(legend_title_text=tr("Difficulty", "难度"), margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(style_figure(fig, 560, True), use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([1.05, 0.95])
    with left:
        section_header(tr("Top Difficult ZIPs", "高难度邮编清单"), tr("Ranked by real claim severity and concentration, not synthetic route-model output.", "按真实理赔严重度和集中度排序，不使用虚构路线模型输出。"))
        table = current.sort_values("difficulty_score", ascending=False).head(40)
        table = table[
            [
                "zip",
                "place_name",
                "state",
                "difficulty_tier",
                "difficulty_score",
                "claim_amount",
                "amount_share",
                "claim_count",
                "avg_claim_amount",
                "claim_type",
                "top_owner",
                "top_dsp",
                "action",
            ]
        ]
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            height=460,
            column_config={
                "zip": tr("ZIP", "邮编"),
                "place_name": tr("City", "城市"),
                "state": tr("State", "州"),
                "difficulty_tier": tr("Tier", "等级"),
                "difficulty_score": st.column_config.ProgressColumn(tr("Difficulty Score", "难度分"), min_value=0, max_value=100, format="%.1f"),
                "claim_amount": st.column_config.NumberColumn(tr("Claim Amount", "理赔金额"), format="$%.2f"),
                "amount_share": st.column_config.ProgressColumn(tr("Amount Share", "金额占比"), min_value=0, max_value=float(current["amount_share"].max()), format="%.1%%"),
                "claim_count": st.column_config.NumberColumn(tr("Claim Count", "理赔次数"), format="%d"),
                "avg_claim_amount": st.column_config.NumberColumn(tr("Avg Claim", "平均金额"), format="$%.2f"),
                "claim_type": tr("Top Claim Type", "主要理赔类型"),
                "top_owner": tr("Top Supplier", "主要供应商"),
                "top_dsp": "DSP",
                "action": tr("Recommended Action", "建议动作"),
            },
        )
        st.download_button(
            tr("Download Current ZIP View", "下载当前邮编视图"),
            data=current.to_csv(index=False).encode("utf-8-sig"),
            file_name="east_zip_difficulty.csv",
            mime="text/csv",
        )

    with right:
        section_header(tr("Claim Type Mix", "理赔类型构成"), tr("Real claim amount by claim type within the selected ZIP set.", "当前邮编范围内按真实理赔金额汇总的类型构成。"))
        current_claims = claims[claims["zip"].isin(current["zip"])]
        type_amount = current_claims.groupby("claim_type", dropna=False)["amount"].sum().reset_index().sort_values("amount", ascending=True).tail(10)
        fig = px.bar(type_amount, x="amount", y="claim_type", orientation="h", color_discrete_sequence=[SLATE])
        fig.update_xaxes(tickprefix="$")
        st.plotly_chart(style_figure(fig, 300), use_container_width=True, config={"displayModeBar": False})

        section_header(tr("State Concentration", "州别集中度"), tr("Where selected real claim dollars are concentrated.", "当前真实理赔金额集中在哪些州。"))
        state_amount = current.groupby("state", dropna=False)["claim_amount"].sum().reset_index().sort_values("claim_amount", ascending=False)
        fig = px.bar(state_amount, x="state", y="claim_amount", color_discrete_sequence=[BLUE])
        fig.update_yaxes(tickprefix="$")
        st.plotly_chart(style_figure(fig, 300, True), use_container_width=True, config={"displayModeBar": False})

    with st.expander(tr("How this ZIP difficulty score is calculated", "邮编难度分如何计算")):
        st.markdown(
            tr(
                "This page uses only the real claims workbook. The score is a weighted index of ZIP claim amount, claim count, average claim amount, and top-claim-type concentration. It is not combined with the synthetic route-risk model.",
                "本页只使用真实理赔 Excel。难度分由邮编理赔金额、理赔次数、平均理赔金额、主要理赔类型集中度加权计算，不与虚构路线风险模型合并。",
            )
        )
        st.caption(f"{tr('Workbook', '工作簿')}: {meta['workbook']}")
