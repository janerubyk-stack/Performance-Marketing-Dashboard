import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from io import StringIO


# ============================================================
# 0. 페이지 설정
# ============================================================

st.set_page_config(
    page_title="캠페인 상세 분석",
    page_icon="🔎",
    layout="wide"
)


# ============================================================
# 1. 좌측 사이드바
# ============================================================

with st.sidebar:

    st.markdown("## 🔎 캠페인 상세 분석")

    st.caption(
        "캠페인 단위 성과를 상세하게 분석합니다."
    )

    st.divider()


# ============================================================
# 2. 제목
# ============================================================

st.title("🔎 캠페인 상세 분석")

st.caption(
    "기존 성과 비교 대시보드와 별도로 캠페인 단위의 성과를 상세하게 분석합니다."
)


# ============================================================
# 3. Google Sheets 설정
# ============================================================

SHEET_ID = "1M_NGYvpXgY721bV-B0dgXOj5LmITfKoVTIoIJgmv6gk"
GID = "519342112"

SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SHEET_ID}/export?format=csv&gid={GID}"
)


# ============================================================
# 4. 데이터 불러오기
# ============================================================

@st.cache_data(ttl=300)
def load_data():

    response = requests.get(
        SHEET_URL,
        timeout=30
    )

    response.raise_for_status()

    df = pd.read_csv(
        StringIO(
            response.content.decode("utf-8-sig")
        )
    )

    # --------------------------------------------------------
    # 컬럼명 정리
    # --------------------------------------------------------

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]


    # --------------------------------------------------------
    # 중복 컬럼명 제거
    # --------------------------------------------------------

    df = df.loc[
        :,
        ~df.columns.duplicated()
    ].copy()


    # --------------------------------------------------------
    # 컬럼 자동 찾기
    # --------------------------------------------------------

@st.cache_data(ttl=300)
def load_data():

    response = requests.get(
        SHEET_URL,
        timeout=30
    )

    response.raise_for_status()

    df = pd.read_csv(
        StringIO(
            response.content.decode("utf-8-sig")
        )
    )


    # ========================================================
    # 컬럼명 정리
    # ========================================================

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]


    # ========================================================
    # 컬럼 자동 찾기
    # ========================================================

    def find_column(candidates):

        # ----------------------------------------------------
        # 정확히 일치
        # ----------------------------------------------------

        for candidate in candidates:

            for col in df.columns:

                if (
                    str(col).strip().lower()
                    == candidate.lower()
                ):

                    return col


        # ----------------------------------------------------
        # 부분 일치
        # ----------------------------------------------------

        for candidate in candidates:

            for col in df.columns:

                if (
                    candidate.lower()
                    in str(col).strip().lower()
                ):

                    return col


        return None


    date_col = find_column([
        "date",
        "날짜"
    ])


    type_col = find_column([
        "type",
        "광고유형",
        "유형",
        "카테고리"
    ])


    media_col = find_column([
        "media2",
        "media",
        "매체"
    ])


    campaign_col = find_column([
        "campaign",
        "캠페인"
    ])


    impress_col = find_column([
        "impress",
        "imprress",
        "impression",
        "노출"
    ])


    click_col = find_column([
        "click",
        "클릭"
    ])


    spend_col = find_column([
        "spend",
        "광고비"
    ])


    conversion_col = find_column([
        "conversion",
        "db",
        "전환"
    ])


    # ========================================================
    # 필수 컬럼 확인
    # ========================================================

    required = {
        "date": date_col,
        "type": type_col,
        "media": media_col,
        "campaign": campaign_col,
        "impress": impress_col,
        "click": click_col,
        "spend": spend_col,
        "conversion": conversion_col
    }


    missing = [
        key
        for key, value in required.items()
        if value is None
    ]


    if missing:

        raise ValueError(
            "필수 컬럼을 찾을 수 없습니다.\n\n"
            f"누락 컬럼: {missing}\n\n"
            f"현재 컬럼:\n{df.columns.tolist()}"
        )


    # ========================================================
    # 중요:
    # 원본 컬럼을 직접 rename하지 않고
    # 필요한 컬럼을 Series 단위로 새 DataFrame에 복사
    #
    # → 중복 컬럼명 때문에 DataFrame이 반환되는 문제 방지
    # ========================================================

    def get_series(column_name):

        # 같은 이름의 컬럼이 여러 개 있어도
        # 첫 번째 컬럼만 Series로 가져옴

        positions = [
            i
            for i, col in enumerate(df.columns)
            if str(col).strip() == str(column_name).strip()
        ]


        if not positions:

            raise ValueError(
                f"컬럼을 찾을 수 없습니다: {column_name}"
            )


        return df.iloc[
            :,
            positions[0]
        ].copy()


    clean_df = pd.DataFrame()


    clean_df["date"] = get_series(
        date_col
    )


    clean_df["type"] = get_series(
        type_col
    )


    clean_df["media"] = get_series(
        media_col
    )


    clean_df["campaign"] = get_series(
        campaign_col
    )


    clean_df["impress"] = get_series(
        impress_col
    )


    clean_df["click"] = get_series(
        click_col
    )


    clean_df["spend"] = get_series(
        spend_col
    )


    clean_df["conversion"] = get_series(
        conversion_col
    )


    # ========================================================
    # 날짜
    # ========================================================

    clean_df["date"] = pd.to_datetime(
        clean_df["date"],
        errors="coerce"
    )


    # ========================================================
    # 숫자
    # ========================================================

    numeric_cols = [
        "impress",
        "click",
        "spend",
        "conversion"
    ]


    for col in numeric_cols:

        clean_df[col] = (
            clean_df[col]
            .astype("string")
            .str.replace(
                ",",
                "",
                regex=False
            )
            .str.replace(
                "-",
                "0",
                regex=False
            )
            .str.strip()
        )


        clean_df[col] = pd.to_numeric(
            clean_df[col],
            errors="coerce"
        ).fillna(0)


    # ========================================================
    # 문자
    # ========================================================

    text_cols = [
        "type",
        "media",
        "campaign"
    ]


    for col in text_cols:

        clean_df[col] = (
            clean_df[col]
            .fillna("미분류")
            .astype("string")
            .str.strip()
        )


        clean_df.loc[
            clean_df[col].isna() |
            (clean_df[col] == ""),
            col
        ] = "미분류"


    # ========================================================
    # 날짜 없는 데이터 제거
    # ========================================================

    clean_df = clean_df.dropna(
        subset=["date"]
    ).copy()


    # ========================================================
    # 날짜 정규화
    # ========================================================

    clean_df["date"] = (
        clean_df["date"]
        .dt.normalize()
    )


    # ========================================================
    # 최종 컬럼 순서
    # ========================================================

    clean_df = clean_df[
        [
            "date",
            "type",
            "media",
            "campaign",
            "impress",
            "click",
            "spend",
            "conversion"
        ]
    ]


    return (
        clean_df
        .sort_values("date")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # 날짜 없는 데이터 제거
    # --------------------------------------------------------

    df = df.dropna(
        subset=["date"]
    ).copy()


    df["date"] = df["date"].dt.normalize()


    return (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )


# ============================================================
# 5. 데이터 로드
# ============================================================

try:

    df = load_data()

except Exception as e:

    st.error(
        "Google Sheets 데이터를 불러오지 못했습니다."
    )

    st.code(
        str(e)
    )

    st.stop()


if df.empty:

    st.warning(
        "데이터가 없습니다."
    )

    st.stop()


# ============================================================
# 6. 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")


available_dates = sorted(
    df["date"].dropna().unique()
)


if not available_dates:

    st.warning(
        "분석 가능한 날짜 데이터가 없습니다."
    )

    st.stop()


min_date = pd.Timestamp(
    min(available_dates)
).date()


max_date = pd.Timestamp(
    max(available_dates)
).date()


col1, col2, col3 = st.columns(
    [1, 2, 2]
)


# ============================================================
# 6-1. 날짜
# ============================================================

with col1:

    analysis_start = st.date_input(
        "시작일",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key="analysis_start"
    )


    analysis_end = st.date_input(
        "종료일",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="analysis_end"
    )


# ============================================================
# 6-2. 카테고리
# ============================================================

with col2:

    type_options = sorted(
        df["type"]
        .dropna()
        .unique()
        .tolist()
    )


    selected_type = st.multiselect(
        "카테고리",
        options=type_options,
        default=type_options,
        key="detail_type"
    )


# ============================================================
# 6-3. 매체
# ============================================================

with col3:

    media_options = sorted(
        df["media"]
        .dropna()
        .unique()
        .tolist()
    )


    selected_media = st.multiselect(
        "매체",
        options=media_options,
        default=media_options,
        key="detail_media"
    )


# ============================================================
# 7. 기간 오류 확인
# ============================================================

if analysis_start > analysis_end:

    st.error(
        "시작일은 종료일보다 빠르거나 같아야 합니다."
    )

    st.stop()


# ============================================================
# 8. 필터
# ============================================================

filtered_df = df[
    (df["date"] >= pd.Timestamp(analysis_start)) &
    (df["date"] <= pd.Timestamp(analysis_end)) &
    (df["type"].isin(selected_type)) &
    (df["media"].isin(selected_media))
].copy()


# ============================================================
# 9. 전체 성과 계산
# ============================================================

total_spend = filtered_df["spend"].sum()

total_click = filtered_df["click"].sum()

total_conversion = filtered_df["conversion"].sum()


total_cpa = (
    total_spend / total_conversion
    if total_conversion > 0
    else np.nan
)


total_cvr = (
    total_conversion / total_click * 100
    if total_click > 0
    else np.nan
)


# ============================================================
# 10. 전체 성과
# ============================================================

st.divider()

st.header("📊 전체 성과")


kpi1, kpi2, kpi3, kpi4 = st.columns(4)


with kpi1:

    st.metric(
        "광고비",
        f"{total_spend:,.0f}원"
    )


with kpi2:

    st.metric(
        "클릭",
        f"{total_click:,.0f}회"
    )


with kpi3:

    st.metric(
        "전환",
        f"{total_conversion:,.0f}건"
    )


with kpi4:

    st.metric(
        "CPA",
        (
            f"{total_cpa:,.0f}원"
            if pd.notna(total_cpa)
            else "-"
        )
    )


st.caption(
    f"분석 기간: "
    f"{pd.Timestamp(analysis_start).strftime('%Y-%m-%d')}"
    f" ~ "
    f"{pd.Timestamp(analysis_end).strftime('%Y-%m-%d')}"
)


# ============================================================
# 11. 캠페인별 집계
# ============================================================

campaign = (
    filtered_df
    .groupby("campaign", as_index=False)
    .agg({
        "impress": "sum",
        "click": "sum",
        "spend": "sum",
        "conversion": "sum"
    })
)

# CPA / CVR 계산
campaign["CPA"] = np.where(
    campaign["conversion"] > 0,
    campaign["spend"] / campaign["conversion"],
    np.nan
)

campaign["CVR"] = np.where(
    campaign["click"] > 0,
    campaign["conversion"] / campaign["click"] * 100,
    0
)

# 캠페인별 전환수: 0개 제외 + 전환수 많은 순
campaign_conversion = (
    campaign[campaign["conversion"] > 0]
    .sort_values("conversion", ascending=False)
    .copy()
)


# ============================================================
# 12. CPA / CVR 계산
# ============================================================

campaign["CPA"] = np.where(
    campaign["conversion"] > 0,
    campaign["spend"] /
    campaign["conversion"],
    np.nan
)


campaign["CVR"] = np.where(
    campaign["click"] > 0,
    campaign["conversion"] /
    campaign["click"] * 100,
    np.nan
)


# ============================================================
# 13. 전체 전환 비중
# ============================================================

if total_conversion > 0:

    campaign["conversion_share"] = (
        campaign["conversion"] /
        total_conversion *
        100
    )

else:

    campaign["conversion_share"] = np.nan


# ============================================================
# 14. 그래프용 고유 캠페인명
# ============================================================

campaign["campaign_label"] = (
    campaign["campaign"]
    + " · "
    + campaign["media"]
)


campaign = (
    campaign
    .sort_values(
        "conversion",
        ascending=False
    )
    .reset_index(drop=True)
)


# ============================================================
# 15. 전체 캠페인 자동 분석
# ============================================================

campaign_filtered = campaign.copy()


# ============================================================
# 16. 캠페인별 성과
# ============================================================

st.divider()

st.header("📈 캠페인별 성과")


if campaign_filtered.empty:

    st.info(
        "선택한 조건에 해당하는 캠페인이 없습니다."
    )

else:

    # ========================================================
    # 16-1. 캠페인별 전환수
    # ========================================================

st.subheader("📊 캠페인별 전환수")

fig_conversion = go.Figure()

fig_conversion.add_trace(
    go.Bar(
        x=campaign_conversion["campaign"],
        y=campaign_conversion["conversion"],
        text=campaign_conversion["conversion"],
        textposition="outside"
    )
)

fig_conversion.update_layout(
    xaxis_title="캠페인",
    yaxis_title="전환수",
    height=450
)

st.plotly_chart(
    fig_conversion,
    width="stretch"
)

    # ========================================================
    # 16-2. 캠페인별 CPA
    # ========================================================

st.subheader("💰 캠페인별 CPA")

fig_cpa = go.Figure()

fig_cpa.add_trace(
    go.Bar(
        x=campaign_cpa["campaign"],
        y=campaign_cpa["CPA"],
        text=campaign_cpa["CPA"].round(0).astype(int),
        texttemplate="%{text:,}원",
        textposition="outside"
    )
)

fig_cpa.update_layout(
    xaxis_title="캠페인",
    yaxis_title="CPA",
    height=450,
    yaxis=dict(
        tickformat=","
    )
)

st.plotly_chart(
    fig_cpa,
    width="stretch"
)


# ============================================================
# 17. 캠페인 TOP 분석
# ============================================================

st.divider()

st.header("🏆 캠페인 성과 TOP")


if campaign_filtered.empty:

    st.info(
        "분석할 캠페인이 없습니다."
    )

else:

    top1, top2, top3 = st.columns(3)


    # ========================================================
    # 17-1. CPA 최우수
    # ========================================================

    cpa_valid = campaign_filtered[
        (campaign_filtered["conversion"] > 0) &
        campaign_filtered["CPA"].notna() &
        (campaign_filtered["CPA"] > 0)
    ]


    if not cpa_valid.empty:

        best_cpa = cpa_valid.loc[
            cpa_valid["CPA"].idxmin()
        ]


        with top1:

            st.markdown(
                "### 🏆 CPA 최우수"
            )

            st.markdown(
                f"**{best_cpa['campaign']}**"
            )

            st.write(
                f"매체: {best_cpa['media']}"
            )

            st.write(
                f"CPA: {best_cpa['CPA']:,.0f}원"
            )

            st.write(
                f"전환: {best_cpa['conversion']:,.0f}건"
            )

            st.write(
                f"CVR: {best_cpa['CVR']:.2f}%"
            )


    # ========================================================
    # 17-2. 전환수 최다
    # ========================================================

    conversion_valid = campaign_filtered[
        campaign_filtered["conversion"] > 0
    ]


    if not conversion_valid.empty:

        best_conversion = conversion_valid.loc[
            conversion_valid["conversion"].idxmax()
        ]


        with top2:

            st.markdown(
                "### 📈 전환수 최다"
            )

            st.markdown(
                f"**{best_conversion['campaign']}**"
            )

            st.write(
                f"매체: {best_conversion['media']}"
            )

            st.write(
                f"전환: "
                f"{best_conversion['conversion']:,.0f}건"
            )

            if pd.notna(
                best_conversion["CPA"]
            ):

                st.write(
                    f"CPA: "
                    f"{best_conversion['CPA']:,.0f}원"
                )

            else:

                st.write(
                    "CPA: -"
                )


            st.write(
                f"전체 전환의 "
                f"{best_conversion['conversion_share']:.1f}%"
            )


    # ========================================================
    # 17-3. CVR 최우수
    # ========================================================

    cvr_valid = campaign_filtered[
        (campaign_filtered["click"] > 0) &
        campaign_filtered["CVR"].notna()
    ]


    if not cvr_valid.empty:

        best_cvr = cvr_valid.loc[
            cvr_valid["CVR"].idxmax()
        ]


        with top3:

            st.markdown(
                "### 🎯 CVR 최우수"
            )

            st.markdown(
                f"**{best_cvr['campaign']}**"
            )

            st.write(
                f"매체: {best_cvr['media']}"
            )

            st.write(
                f"CVR: "
                f"{best_cvr['CVR']:.2f}%"
            )

            st.write(
                f"전환: "
                f"{best_cvr['conversion']:,.0f}건"
            )

            st.write(
                f"클릭: "
                f"{best_cvr['click']:,.0f}회"
            )


# ============================================================
# 18. 개선 필요 캠페인
# ============================================================

st.divider()

st.header("⚠️ 개선 필요 캠페인")


if campaign_filtered.empty:

    st.info(
        "분석할 캠페인이 없습니다."
    )

else:

    high_cpa = (
        campaign_filtered[
            (campaign_filtered["conversion"] > 0) &
            campaign_filtered["CPA"].notna()
        ]
        .sort_values(
            "CPA",
            ascending=False
        )
    )


    if not high_cpa.empty:

        st.markdown(
            "#### CPA가 높은 캠페인"
        )


        warning_df = high_cpa[
            [
                "type",
                "media",
                "campaign",
                "spend",
                "conversion",
                "CPA",
                "CVR"
            ]
        ].head(5).copy()


        warning_df = warning_df.rename(
            columns={
                "type": "카테고리",
                "media": "매체",
                "campaign": "캠페인",
                "spend": "광고비",
                "conversion": "전환",
                "CPA": "CPA",
                "CVR": "CVR"
            }
        )


        st.dataframe(

            warning_df,

            width="stretch",

            hide_index=True,

            column_config={

                "광고비": st.column_config.NumberColumn(
                    format="%,d원"
                ),

                "전환": st.column_config.NumberColumn(
                    format="%,d건"
                ),

                "CPA": st.column_config.NumberColumn(
                    format="%,d원"
                ),

                "CVR": st.column_config.NumberColumn(
                    format="%.2f%%"
                )
            }
        )


    else:

        st.info(
            "전환이 발생한 캠페인이 없습니다."
        )


# ============================================================
# 19. 캠페인 상세 데이터
# ============================================================

st.divider()

st.header("📋 캠페인 상세 성과")


if campaign_filtered.empty:

    st.info(
        "분석 조건에 해당하는 캠페인의 데이터가 없습니다."
    )

else:

    detail_table = campaign_filtered[
        [
            "type",
            "media",
            "campaign",
            "impress",
            "click",
            "spend",
            "conversion",
            "CPA",
            "CVR",
            "conversion_share"
        ]
    ].copy()


    detail_table = detail_table.rename(
        columns={
            "type": "카테고리",
            "media": "매체",
            "campaign": "캠페인",
            "impress": "노출",
            "click": "클릭",
            "spend": "광고비",
            "conversion": "전환",
            "CPA": "CPA",
            "CVR": "CVR",
            "conversion_share": "전체 전환 비중"
        }
    )


    st.dataframe(

        detail_table,

        width="stretch",

        hide_index=True,

        column_config={

            "노출": st.column_config.NumberColumn(
                format="%,d"
            ),

            "클릭": st.column_config.NumberColumn(
                format="%,d"
            ),

            "광고비": st.column_config.NumberColumn(
                format="%,d원"
            ),

            "전환": st.column_config.NumberColumn(
                format="%,d건"
            ),

            "CPA": st.column_config.NumberColumn(
                format="%,d원"
            ),

            "CVR": st.column_config.NumberColumn(
                format="%.2f%%"
            ),

            "전체 전환 비중": st.column_config.NumberColumn(
                format="%.1f%%"
            )
        }
    )


# ============================================================
# 20. 데이터 정보
# ============================================================

st.divider()

with st.expander("📌 데이터 정보"):

    st.write(
        f"전체 데이터: {len(df):,}건"
    )

    st.write(
        f"분석 데이터: {len(filtered_df):,}건"
    )

    st.write(
        f"분석 기간: "
        f"{pd.Timestamp(analysis_start).strftime('%Y-%m-%d')}"
        f" ~ "
        f"{pd.Timestamp(analysis_end).strftime('%Y-%m-%d')}"
    )

    st.write(
        f"선택 카테고리: "
        f"{len(selected_type)}개"
    )

    st.write(
        f"선택 매체: "
        f"{len(selected_media)}개"
    )

    st.write(
        f"분석 캠페인: "
        f"{len(campaign_filtered):,}개"
    )
