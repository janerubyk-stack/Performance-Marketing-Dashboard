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
    "기존 성과 비교 대시보드와 별도로 캠페인 단위의 성과를 상세하게 분석합니다."
)


# ============================================================
# 2. Google Sheets 설정
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

    # --------------------------------------------------------
    # 컬럼명 정리
    # --------------------------------------------------------

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]


    # --------------------------------------------------------
    # 컬럼 자동 찾기
    # --------------------------------------------------------

    def find_column(candidates):

        # 정확히 일치
        for candidate in candidates:

            for col in df.columns:

                if str(col).strip().lower() == candidate.lower():

                    return col


        # 부분 일치
        for candidate in candidates:

            for col in df.columns:

                if candidate.lower() in str(col).strip().lower():

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
        "media",
        "매체"
    ])

    campaign_col = find_column([
        "campaign",
        "캠페인"
    ])

    impress_col = find_column([
        "impress",
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


    # --------------------------------------------------------
    # 필수 컬럼 확인
    # --------------------------------------------------------

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
            f"필수 컬럼을 찾을 수 없습니다: {missing}"
        )


    # --------------------------------------------------------
    # 내부 표준 컬럼명으로 변경
    # --------------------------------------------------------

    df = df.rename(
        columns={
            date_col: "date",
            type_col: "type",
            media_col: "media",
            campaign_col: "campaign",
            impress_col: "impress",
            click_col: "click",
            spend_col: "spend",
            conversion_col: "conversion"
        }
    )


    # --------------------------------------------------------
    # 날짜
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # 숫자
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 문자
    # --------------------------------------------------------

    for col in [
        "type",
        "media",
        "campaign"
    ]:

        df[col] = (
            df[col]
            .fillna("미분류")
            .astype(str)
            .str.strip()
        )

        df.loc[
            df[col] == "",
            col
        ] = "미분류"


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
# 4. 데이터 로드
# ============================================================

try:

    df = load_data()

except Exception as e:

    st.error(
        f"Google Sheets 데이터를 불러오지 못했습니다.\n\n{e}"
    )

    st.stop()


if df.empty:

    st.warning("데이터가 없습니다.")

    st.stop()


# ============================================================
# 5. 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")


available_dates = sorted(
    df["date"].dropna().unique()
)


min_date = pd.Timestamp(
    min(available_dates)
).date()


max_date = pd.Timestamp(
    max(available_dates)
).date()


col1, col2, col3 = st.columns([1, 2, 2])


# ------------------------------------------------------------
# 날짜
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 카테고리
# ------------------------------------------------------------

with col2:

    type_options = sorted(
        df["type"].unique().tolist()
    )


    selected_type = st.multiselect(
        "카테고리",
        options=type_options,
        default=type_options,
        key="detail_type"
    )


# ------------------------------------------------------------
# 매체
# ------------------------------------------------------------

with col3:

    media_options = sorted(
        df["media"].unique().tolist()
    )


    selected_media = st.multiselect(
        "매체",
        options=media_options,
        default=media_options,
        key="detail_media"
    )


# ============================================================
# 6. 기간 오류 확인
# ============================================================

if analysis_start > analysis_end:

    st.error(
        "시작일은 종료일보다 빠르거나 같아야 합니다."
    )

    st.stop()


# ============================================================
# 7. 필터
# ============================================================

filtered_df = df[
    (df["date"] >= pd.Timestamp(analysis_start)) &
    (df["date"] <= pd.Timestamp(analysis_end)) &
    (df["type"].isin(selected_type)) &
    (df["media"].isin(selected_media))
].copy()


# ============================================================
# 8. 전체 성과 계산
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
# 9. 전체 성과
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
# 10. 캠페인별 집계
# ============================================================

campaign = (
    filtered_df
    .groupby(
        ["type", "media", "campaign"],
        as_index=False
    )
    .agg(
        impress=("impress", "sum"),
        click=("click", "sum"),
        spend=("spend", "sum"),
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


# 전체 전환 비중

if total_conversion > 0:

    campaign["conversion_share"] = (
        campaign["conversion"] /
        total_conversion *
        100
    )

else:

    campaign["conversion_share"] = np.nan


campaign = campaign.sort_values(
    "conversion",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 11. 캠페인 상세 필터
# ============================================================

st.divider()

st.header("🎯 캠페인 선택")


campaign_options = sorted(
    campaign["campaign"].unique().tolist()
)


selected_campaigns = st.multiselect(
    "분석할 캠페인",
    options=campaign_options,
    default=campaign_options,
    key="detail_campaign"
)


campaign_filtered = campaign[
    campaign["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 12. 캠페인별 성과 차트
# ============================================================

st.divider()

st.header("📈 캠페인별 성과")


if campaign_filtered.empty:

    st.info(
        "선택한 조건에 해당하는 캠페인이 없습니다."
    )

else:

    chart_df = campaign_filtered.sort_values(
        "conversion",
        ascending=False
    )


    x = chart_df["campaign"].tolist()


    # --------------------------------------------------------
    # CPA + 전환수
    # --------------------------------------------------------

    fig_cpa = go.Figure()


    fig_cpa.add_trace(
        go.Bar(
            x=x,
            y=chart_df["CPA"],
            name="CPA",
            text=[
                (
                    f"{v:,.0f}원"
                    if pd.notna(v)
                    else "-"
                )
                for v in chart_df["CPA"]
            ],
            textposition="outside"
        )
    )


    fig_cpa.add_trace(
        go.Scatter(
            x=x,
            y=chart_df["conversion"],
            name="전환수",
            mode="lines+markers",
            yaxis="y2"
        )
    )


    fig_cpa.update_layout(

        title="캠페인별 CPA + 전환수",

        height=450,

        xaxis=dict(
            title="캠페인",
            type="category",
            tickangle=-35,
            automargin=True
        ),

        yaxis=dict(
            title="CPA"
        ),

        yaxis2=dict(
            title="전환수",
            overlaying="y",
            side="right"
        ),

        hovermode="x unified",

        margin=dict(
            l=60,
            r=60,
            t=70,
            b=120
        )
    )


    st.plotly_chart(
        fig_cpa,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


# ============================================================
# 13. 캠페인 TOP 분석
# ============================================================

st.divider()

st.header("🏆 캠페인 성과 TOP")


if campaign_filtered.empty:

    st.info(
        "분석할 캠페인이 없습니다."
    )

else:

    top1, top2, top3 = st.columns(3)


    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

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

            st.markdown("### 🏆 CPA 최우수")

            st.markdown(
                f"**{best_cpa['campaign']}**"
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


    # --------------------------------------------------------
    # 전환수 최다
    # --------------------------------------------------------

    conversion_valid = campaign_filtered[
        campaign_filtered["conversion"] > 0
    ]


    if not conversion_valid.empty:

        best_conversion = conversion_valid.loc[
            conversion_valid["conversion"].idxmax()
        ]


        with top2:

            st.markdown("### 📈 전환수 최다")

            st.markdown(
                f"**{best_conversion['campaign']}**"
            )

            st.write(
                f"전환: "
                f"{best_conversion['conversion']:,.0f}건"
            )

            st.write(
                f"CPA: "
                f"{best_conversion['CPA']:,.0f}원"
            )

            st.write(
                f"전체 전환의 "
                f"{best_conversion['conversion_share']:.1f}%"
            )


    # --------------------------------------------------------
    # CVR 최우수
    # --------------------------------------------------------

    cvr_valid = campaign_filtered[
        (campaign_filtered["click"] > 0) &
        campaign_filtered["CVR"].notna()
    ]


    if not cvr_valid.empty:

        best_cvr = cvr_valid.loc[
            cvr_valid["CVR"].idxmax()
        ]


        with top3:

            st.markdown("### 🎯 CVR 최우수")

            st.markdown(
                f"**{best_cvr['campaign']}**"
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
# 14. 개선 필요 캠페인
# ============================================================

st.divider()

st.header("⚠️ 개선 필요 캠페인")


if campaign_filtered.empty:

    st.info(
        "분석할 캠페인이 없습니다."
    )

else:

    # CPA가 높은 순
    high_cpa = campaign_filtered[
        (campaign_filtered["conversion"] > 0) &
        campaign_filtered["CPA"].notna()
    ].sort_values(
        "CPA",
        ascending=False
    )


    # 전환이 발생한 캠페인 중 CPA 상위 5개
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
            use_container_width=True,
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


# ============================================================
# 15. 캠페인 상세 데이터
# ============================================================

st.divider()

st.header("📋 캠페인 상세 성과")


if campaign_filtered.empty:

    st.info(
        "선택한 캠페인의 데이터가 없습니다."
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

        use_container_width=True,

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
# 16. 데이터 정보
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
        f"선택 캠페인: "
        f"{len(selected_campaigns)}개"
    )
