import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


# ============================================================
# 0. 페이지 설정
# ============================================================

st.set_page_config(
    page_title="캠페인 상세 분석",
    page_icon="🔎",
    layout="wide"
)


# ============================================================
# 1. 제목
# ============================================================

st.title("🔎 캠페인 상세 분석")

st.caption(
    "기존 성과 비교 대시보드와 별도로 운영되는 분석 페이지입니다."
)


# ============================================================
# 2. Google Sheets
# ============================================================

SHEET_ID = "1M_NGYvpXgY721bV-B0dgXOj5LmITfKoVTIoIJgmv6gk"
GID = "519342112"

SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SHEET_ID}/export?format=csv&gid={GID}"
)


# ============================================================
# 3. 데이터 불러오기
# ============================================================

@st.cache_data(ttl=300)
def load_data():

    df = pd.read_csv(
        SHEET_URL,
        encoding="utf-8-sig"
    )

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    # 날짜
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    # 숫자
    numeric_cols = [
        "impress",
        "click",
        "spend",
        "conversion"
    ]

    for col in numeric_cols:

        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("-", "0", regex=False)
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # 문자
    for col in [
        "type",
        "media",
        "campaign"
    ]:

        if col in df.columns:

            df[col] = (
                df[col]
                .fillna("미분류")
                .astype(str)
                .str.strip()
            )

    return df


df = load_data()


# ============================================================
# 4. 기본 확인
# ============================================================

st.success(
    f"데이터 {len(df):,}건을 불러왔습니다."
)


# ============================================================
# 5. 필터
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(3)


with col1:

    selected_type = st.multiselect(
        "카테고리",
        sorted(df["type"].unique()),
        default=sorted(df["type"].unique())
    )


with col2:

    selected_media = st.multiselect(
        "매체",
        sorted(df["media"].unique()),
        default=sorted(df["media"].unique())
    )


with col3:

    selected_campaign = st.multiselect(
        "캠페인",
        sorted(df["campaign"].unique()),
        default=sorted(df["campaign"].unique())
    )


filtered_df = df[
    df["type"].isin(selected_type) &
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaign)
].copy()


# ============================================================
# 6. 전체 성과
# ============================================================

spend = filtered_df["spend"].sum()
conversion = filtered_df["conversion"].sum()
click = filtered_df["click"].sum()

cpa = (
    spend / conversion
    if conversion > 0
    else np.nan
)

cvr = (
    conversion / click * 100
    if click > 0
    else np.nan
)


col1, col2, col3, col4 = st.columns(4)


with col1:
    st.metric(
        "광고비",
        f"{spend:,.0f}원"
    )


with col2:
    st.metric(
        "전환",
        f"{conversion:,.0f}건"
    )


with col3:
    st.metric(
        "CPA",
        (
            f"{cpa:,.0f}원"
            if pd.notna(cpa)
            else "-"
        )
    )


with col4:
    st.metric(
        "CVR",
        (
            f"{cvr:.2f}%"
            if pd.notna(cvr)
            else "-"
        )
    )


# ============================================================
# 7. 캠페인별 성과
# ============================================================

st.divider()

st.header("📊 캠페인별 성과")


campaign = (
    filtered_df
    .groupby("campaign", as_index=False)
    .agg(
        spend=("spend", "sum"),
        click=("click", "sum"),
        conversion=("conversion", "sum")
    )
)


campaign["CPA"] = np.where(
    campaign["conversion"] > 0,
    campaign["spend"] /
    campaign["conversion"],
    np.nan
)


campaign["CVR"] = np.where(
    campaign["click"] > 0,
    campaign["conversion"] /
    campaign["click"] *
    100,
    np.nan
)


campaign = campaign.sort_values(
    "conversion",
    ascending=False
)


st.dataframe(
    campaign,
    use_container_width=True
)
