import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
import calendar


# ============================================================
# 0. 페이지 설정
# ============================================================

st.set_page_config(
    page_title="성과 비교 대시보드",
    page_icon="📈",
    layout="wide"
)


# ============================================================
# 1. Google Sheets 설정
# ============================================================

SHEET_ID = "1M_NGYvpXgY721bV-B0dgXOj5LmITfKoVTIoIJgmv6gk"
GID = "519342112"

SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{SHEET_ID}/export?format=csv&gid={GID}"
)


# ============================================================
# 2. 제목
# ============================================================

st.title("📈 성과 비교 대시보드")


# ============================================================
# 3. Google Sheets 데이터 불러오기
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
    # 컬럼 자동 탐색
    # --------------------------------------------------------

    def find_column(candidates):

        # 정확히 일치
        for candidate in candidates:

            for col in df.columns:

                if (
                    str(col).strip().lower()
                    == str(candidate).strip().lower()
                ):
                    return col


        # 부분 일치
        for candidate in candidates:

            for col in df.columns:

                if (
                    str(candidate).strip().lower()
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
        "TYPE",
        "광고유형",
        "유형"
    ])

    media_col = find_column([
        "media",
        "MEDIA",
        "매체",
        "media2"
    ])

    campaign_col = find_column([
        "campaign",
        "CAMPAIGN",
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
        "DB",
        "전환"
    ])


    required = {
        "DATE": date_col,
        "TYPE": type_col,
        "MEDIA": media_col,
        "CAMPAIGN": campaign_col,
        "IMPRESS": impress_col,
        "CLICK": click_col,
        "SPEND": spend_col,
        "CONVERSION": conversion_col
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
    # 내부 표준 컬럼명
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
    # 날짜 처리
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # 숫자 처리
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
    # 문자 컬럼 처리
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


    # --------------------------------------------------------
    # 정렬
    # --------------------------------------------------------

    df = (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )


    return df


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
# 5. 공통 함수
# ============================================================

def safe_change(current, previous):

    """
    전기/비교기간 대비 변화율 계산.

    비교값이 0이거나 존재하지 않는 경우
    억지로 무한대나 nan을 표시하지 않고 None 반환.
    """

    if current is None or previous is None:
        return None

    if pd.isna(current) or pd.isna(previous):
        return None

    if previous == 0:
        return None

    return (
        (current - previous)
        / previous
        * 100
    )


def safe_cpa(spend, conversion):

    if conversion > 0:
        return spend / conversion

    return np.nan


def safe_cvr(conversion, click):

    if click > 0:
        return conversion / click * 100

    return np.nan


def fmt_money(value):

    if value is None or pd.isna(value):
        return "-"

    return f"{value:,.0f}원"


def fmt_number(value):

    if value is None or pd.isna(value):
        return "-"

    return f"{value:,.0f}건"


def fmt_percent(value):

    if value is None or pd.isna(value):
        return "-"

    return f"{value:.2f}%"


def fmt_change(value):

    """
    변화율을 화면에 표시하는 함수.

    nan / inf / None은 절대 출력하지 않음.
    """

    if value is None:
        return "-"

    if pd.isna(value):
        return "-"

    if np.isinf(value):
        return "신규"

    if value > 0:
        return f"▲ +{value:.1f}%"

    if value < 0:
        return f"▼ {value:.1f}%"

    return "─ 0.0%"


def change_status(
    value,
    inverse=False
):

    """
    CPA처럼 낮을수록 좋은 지표와
    전환/CVR처럼 높을수록 좋은 지표의
    상태 표시를 분리.
    """

    if value is None or pd.isna(value):
        return "neutral"

    if value == 0:
        return "neutral"

    if inverse:

        if value < 0:
            return "good"

        return "bad"

    else:

        if value > 0:
            return "good"

        return "bad"


# ============================================================
# 6. 기간 계산
# ============================================================

def get_periods(
    base_date,
    period_type
):

    base_date = pd.Timestamp(base_date)


    # --------------------------------------------------------
    # 전일
    # --------------------------------------------------------

    if period_type == "전일":

        current_start = base_date
        current_end = base_date

        previous_start = (
            base_date -
            timedelta(days=1)
        )

        previous_end = previous_start


    # --------------------------------------------------------
    # 전주
    # --------------------------------------------------------

    elif period_type == "전주":

        weekday = base_date.weekday()

        current_start = (
            base_date -
            timedelta(days=weekday)
        )

        current_end = base_date

        elapsed_days = (
            current_end -
            current_start
        ).days + 1

        previous_end = (
            current_end -
            timedelta(days=7)
        )

        previous_start = (
            previous_end -
            timedelta(days=elapsed_days - 1)
        )


    # --------------------------------------------------------
    # 전월
    # --------------------------------------------------------

    elif period_type == "전월":

        current_start = base_date.replace(day=1)
        current_end = base_date

        elapsed_days = (
            current_end -
            current_start
        ).days + 1

        previous_month_last = (
            base_date.replace(day=1)
            - timedelta(days=1)
        )

        previous_year = previous_month_last.year
        previous_month = previous_month_last.month

        previous_month_days = calendar.monthrange(
            previous_year,
            previous_month
        )[1]

        previous_day = min(
            base_date.day,
            previous_month_days
        )

        previous_start = pd.Timestamp(
            previous_year,
            previous_month,
            1
        )

        previous_end = pd.Timestamp(
            previous_year,
            previous_month,
            previous_day
        )


    else:

        raise ValueError(
            "잘못된 기간 유형입니다."
        )


    return (
        pd.Timestamp(current_start),
        pd.Timestamp(current_end),
        pd.Timestamp(previous_start),
        pd.Timestamp(previous_end)
    )


def format_period(
    start_date,
    end_date
):

    return (
        f"{pd.Timestamp(start_date).strftime('%Y-%m-%d')}"
        f" ~ "
        f"{pd.Timestamp(end_date).strftime('%Y-%m-%d')}"
    )


# ============================================================
# 7. 성과 집계
# ============================================================

def aggregate_performance(
    data,
    start_date,
    end_date
):

    temp = data[
        (data["date"] >= pd.Timestamp(start_date)) &
        (data["date"] <= pd.Timestamp(end_date))
    ].copy()


    if temp.empty:

        return pd.DataFrame(
            columns=[
                "type",
                "media",
                "campaign",
                "impress",
                "click",
                "spend",
                "conversion",
                "CPA",
                "CVR"
            ]
        )


    result = (
        temp
        .groupby(
            [
                "type",
                "media",
                "campaign"
            ],
            as_index=False
        )
        .agg(
            impress=("impress", "sum"),
            click=("click", "sum"),
            spend=("spend", "sum"),
            conversion=("conversion", "sum")
        )
    )


    result["CPA"] = result.apply(
        lambda x:
        safe_cpa(
            x["spend"],
            x["conversion"]
        ),
        axis=1
    )


    result["CVR"] = result.apply(
        lambda x:
        safe_cvr(
            x["conversion"],
            x["click"]
        ),
        axis=1
    )


    return result


# ============================================================
# 8. 분석 조건
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


col1, col2, col3 = st.columns(
    [1, 1.5, 2]
)


# ------------------------------------------------------------
# 기준일
# ------------------------------------------------------------

with col1:

    base_date = st.date_input(
        "기준일",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )


# ------------------------------------------------------------
# 비교 기간
# ------------------------------------------------------------

with col2:

    period_type = st.radio(
        "비교 기간",
        [
            "전일",
            "전주",
            "전월",
            "지정"
        ],
        horizontal=True
    )


# ============================================================
# 9. 기간 설정
# ============================================================

if period_type != "지정":

    (
        current_start,
        current_end,
        previous_start,
        previous_end
    ) = get_periods(
        base_date,
        period_type
    )

    elapsed_days = (
        current_end -
        current_start
    ).days + 1


else:

    st.markdown("### 📅 지정 기간")


    custom_col1, custom_col2 = st.columns(2)


    # --------------------------------------------------------
    # 기준 기간
    # --------------------------------------------------------

    with custom_col1:

        custom_current_start = st.date_input(
            "기준 시작일",
            value=(
                pd.Timestamp(base_date)
                - timedelta(days=6)
            ).date(),
            min_value=min_date,
            max_value=base_date,
            key="custom_current_start"
        )


        custom_current_end = st.date_input(
            "기준 종료일",
            value=base_date,
            min_value=min_date,
            max_value=max_date,
            key="custom_current_end"
        )


    custom_elapsed_days = (
        pd.Timestamp(custom_current_end)
        -
        pd.Timestamp(custom_current_start)
    ).days + 1


    # --------------------------------------------------------
    # 비교 기간
    # --------------------------------------------------------

    with custom_col2:

        st.markdown(
            f"**기준 기간 일수: {custom_elapsed_days}일**"
        )


        custom_previous_start = st.date_input(
            "비교 시작일",
            value=(
                pd.Timestamp(custom_current_start)
                -
                timedelta(days=custom_elapsed_days)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_start"
        )


        # ----------------------------------------------------
        # 비교 종료일은 기준 기간과 동일한 일수로 자동 계산
        # ----------------------------------------------------

        calculated_previous_end = (
            pd.Timestamp(custom_previous_start)
            +
            timedelta(days=custom_elapsed_days - 1)
        )


        custom_previous_end = calculated_previous_end.date()


        st.info(
            f"비교 종료일: "
            f"**{custom_previous_end.strftime('%Y-%m-%d')}**\n\n"
            f"기준 기간과 동일하게 "
            f"**{custom_elapsed_days}일**로 자동 설정됩니다."
        )


    current_start = pd.Timestamp(
        custom_current_start
    )

    current_end = pd.Timestamp(
        custom_current_end
    )

    previous_start = pd.Timestamp(
        custom_previous_start
    )

    previous_end = pd.Timestamp(
        custom_previous_end
    )

    elapsed_days = custom_elapsed_days


# ============================================================
# 10. 기간 표시
# ============================================================

current_period_text = format_period(
    current_start,
    current_end
)

previous_period_text = format_period(
    previous_start,
    previous_end
)


with col3:

    st.info(
        f"""
**기준 기간:** {current_period_text}

**비교 기간:** {previous_period_text}

**동일 진행일수:** {elapsed_days}일
"""
    )


# ============================================================
# 11. TYPE / 매체 / 캠페인 필터
# ============================================================

type_options = sorted(
    df["type"].unique().tolist()
)

media_options = sorted(
    df["media"].unique().tolist()
)

campaign_options = sorted(
    df["campaign"].unique().tolist()
)


filter_col1, filter_col2, filter_col3 = st.columns(
    [1, 2, 2]
)


# ------------------------------------------------------------
# TYPE
# ------------------------------------------------------------

with filter_col1:

    selected_types = st.multiselect(
        "TYPE",
        options=type_options,
        default=type_options,
        key="type_filter"
    )


# ------------------------------------------------------------
# 선택 TYPE에 맞는 매체
# ------------------------------------------------------------

media_filtered_options = sorted(
    df[
        df["type"].isin(selected_types)
    ]["media"]
    .dropna()
    .unique()
    .tolist()
)


# ------------------------------------------------------------
# 매체
# ------------------------------------------------------------

with filter_col2:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_filtered_options,
        default=media_filtered_options,
        key="media_filter"
    )


# ------------------------------------------------------------
# 선택 TYPE + 매체에 맞는 캠페인
# ------------------------------------------------------------

campaign_filtered_options = sorted(
    df[
        df["type"].isin(selected_types) &
        df["media"].isin(selected_media)
    ]["campaign"]
    .dropna()
    .unique()
    .tolist()
)


# ------------------------------------------------------------
# 캠페인
# ------------------------------------------------------------

with filter_col3:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=campaign_filtered_options,
        default=campaign_filtered_options,
        key="campaign_filter"
    )


# ============================================================
# 12. 전체 선택 버튼
# ============================================================

button_col1, button_col2, button_col3 = st.columns(3)


with button_col1:

    if st.button(
        "📌 TYPE 전체 선택",
        use_container_width=True
    ):

        st.session_state["type_filter"] = type_options

        st.rerun()


with button_col2:

    if st.button(
        "📌 매체 전체 선택",
        use_container_width=True
    ):

        st.session_state["media_filter"] = media_filtered_options

        st.rerun()


with button_col3:

    if st.button(
        "📌 캠페인 전체 선택",
        use_container_width=True
    ):

        st.session_state["campaign_filter"] = campaign_filtered_options

        st.rerun()


# ============================================================
# 13. 필터 데이터
# ============================================================

filtered_df = df[
    df["type"].isin(selected_types) &
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 14. 현재 / 비교 데이터
# ============================================================

current_df = aggregate_performance(
    filtered_df,
    current_start,
    current_end
)

previous_df = aggregate_performance(
    filtered_df,
    previous_start,
    previous_end
)


# ============================================================
# 15. 매체별 집계
# ============================================================

def aggregate_by_media(data):

    if data.empty:

        return pd.DataFrame(
            columns=[
                "media",
                "impress",
                "click",
                "spend",
                "conversion",
                "CPA",
                "CVR"
            ]
        )


    result = (
        data
        .groupby(
            "media",
            as_index=False
        )
        .agg(
            impress=("impress", "sum"),
            click=("click", "sum"),
            spend=("spend", "sum"),
            conversion=("conversion", "sum")
        )
    )


    result["CPA"] = result.apply(
        lambda x:
        safe_cpa(
            x["spend"],
            x["conversion"]
        ),
        axis=1
    )


    result["CVR"] = result.apply(
        lambda x:
        safe_cvr(
            x["conversion"],
            x["click"]
        ),
        axis=1
    )


    return result


current_media = aggregate_by_media(
    current_df
)

previous_media = aggregate_by_media(
    previous_df
)


# ============================================================
# 16. 비교 데이터 생성
# ============================================================

def create_comparison(
    current,
    previous,
    group_col
):

    current = current.copy()
    previous = previous.copy()


    if current.empty:

        current = pd.DataFrame(
            columns=[
                group_col,
                "spend",
                "click",
                "conversion"
            ]
        )


    if previous.empty:

        previous = pd.DataFrame(
            columns=[
                group_col,
                "spend",
                "click",
                "conversion"
            ]
        )


    current = current.set_index(
        group_col
    )

    previous = previous.set_index(
        group_col
    )


    groups = sorted(
        set(current.index) |
        set(previous.index)
    )


    rows = []


    for group in groups:

        c = (
            current.loc[group]
            if group in current.index
            else pd.Series(dtype=float)
        )

        p = (
            previous.loc[group]
            if group in previous.index
            else pd.Series(dtype=float)
        )


        c_spend = float(
            c.get("spend", 0)
        )

        p_spend = float(
            p.get("spend", 0)
        )


        c_click = float(
            c.get("click", 0)
        )

        p_click = float(
            p.get("click", 0)
        )


        c_conversion = float(
            c.get("conversion", 0)
        )

        p_conversion = float(
            p.get("conversion", 0)
        )


        c_cpa = safe_cpa(
            c_spend,
            c_conversion
        )

        p_cpa = safe_cpa(
            p_spend,
            p_conversion
        )


        c_cvr = safe_cvr(
            c_conversion,
            c_click
        )

        p_cvr = safe_cvr(
            p_conversion,
            p_click
        )


        rows.append({

            group_col: group,

            "spend_current": c_spend,
            "spend_previous": p_spend,

            "conversion_current": c_conversion,
            "conversion_previous": p_conversion,

            "click_current": c_click,
            "click_previous": p_click,

            "CPA_current": c_cpa,
            "CPA_previous": p_cpa,

            "CVR_current": c_cvr,
            "CVR_previous": p_cvr

        })


    result = pd.DataFrame(rows)


    # --------------------------------------------------------
    # 변화율
    # --------------------------------------------------------

    if result.empty:

        return result


    result["spend_change"] = result.apply(
        lambda x:
        safe_change(
            x["spend_current"],
            x["spend_previous"]
        ),
        axis=1
    )


    result["conversion_change"] = result.apply(
        lambda x:
        safe_change(
            x["conversion_current"],
            x["conversion_previous"]
        ),
        axis=1
    )


    result["CPA_change"] = result.apply(
        lambda x:
        safe_change(
            x["CPA_current"],
            x["CPA_previous"]
        ),
        axis=1
    )


    result["CVR_change"] = result.apply(
        lambda x:
        safe_change(
            x["CVR_current"],
            x["CVR_previous"]
        ),
        axis=1
    )


    return result


comparison = create_comparison(
    current_media,
    previous_media,
    "media"
)


# ============================================================
# 17. 전체 성과 요약
# ============================================================

st.divider()

st.header("📊 전체 성과 요약")


total_current_spend = current_df["spend"].sum()
total_previous_spend = previous_df["spend"].sum()

total_current_conversion = current_df["conversion"].sum()
total_previous_conversion = previous_df["conversion"].sum()

total_current_click = current_df["click"].sum()
total_previous_click = previous_df["click"].sum()


total_current_cpa = safe_cpa(
    total_current_spend,
    total_current_conversion
)

total_previous_cpa = safe_cpa(
    total_previous_spend,
    total_previous_conversion
)


total_current_cvr = safe_cvr(
    total_current_conversion,
    total_current_click
)

total_previous_cvr = safe_cvr(
    total_previous_conversion,
    total_previous_click
)


total_spend_change = safe_change(
    total_current_spend,
    total_previous_spend
)

total_conversion_change = safe_change(
    total_current_conversion,
    total_previous_conversion
)

total_cpa_change = safe_change(
    total_current_cpa,
    total_previous_cpa
)

total_cvr_change = safe_change(
    total_current_cvr,
    total_previous_cvr
)


summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)


with summary_col1:

    st.metric(
        "광고비",
        fmt_money(total_current_spend),
        fmt_change(total_spend_change)
    )


with summary_col2:

    st.metric(
        "전환수",
        fmt_number(total_current_conversion),
        fmt_change(total_conversion_change)
    )


with summary_col3:

    st.metric(
        "CPA",
        fmt_money(total_current_cpa),
        fmt_change(total_cpa_change),
        delta_color="inverse"
    )


with summary_col4:

    st.metric(
        "CVR",
        fmt_percent(total_current_cvr),
        fmt_change(total_cvr_change)
    )


# ============================================================
# 18. 성과 추이
# ============================================================

st.divider()

st.header("📈 성과 추이")

st.caption(
    f"현재 설정한 기준 기간 {current_period_text} 내 데이터만 표시합니다."
)


# ============================================================
# 추이 데이터
# ============================================================

def create_trend_data(
    data,
    start_date,
    end_date,
    trend_type
):

    temp = data[
        (data["date"] >= pd.Timestamp(start_date)) &
        (data["date"] <= pd.Timestamp(end_date))
    ].copy()


    if temp.empty:

        return pd.DataFrame()


    if trend_type == "일자별":

        temp["period"] = temp["date"]


    elif trend_type == "주차별":

        temp["period"] = (
            temp["date"]
            -
            pd.to_timedelta(
                temp["date"].dt.weekday,
                unit="D"
            )
        )


    else:

        temp["period"] = (
            temp["date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )


    result = (
        temp
        .groupby(
            "period",
            as_index=False
        )
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )


    result["CPA"] = result.apply(
        lambda x:
        safe_cpa(
            x["spend"],
            x["conversion"]
        ),
        axis=1
    )


    result["CVR"] = result.apply(
        lambda x:
        safe_cvr(
            x["conversion"],
            x["click"]
        ),
        axis=1
    )


    return result.sort_values(
        "period"
    )


# ============================================================
# 추이 차트
# ============================================================

trend_tab1, trend_tab2, trend_tab3 = st.tabs(
    [
        "📅 일자별",
        "📆 주차별",
        "🗓️ 월별"
    ]
)


def draw_trend_chart(
    trend_type
):

    trend_df = create_trend_data(
        filtered_df,
        current_start,
        current_end,
        trend_type
    )


    if trend_df.empty:

        st.info(
            "선택한 기준 기간에 데이터가 없습니다."
        )

        return


    if trend_type in [
        "일자별",
        "주차별"
    ]:

        x_values = (
            trend_df["period"]
            .dt.strftime("%m/%d")
        )

    else:

        x_values = (
            trend_df["period"]
            .dt.strftime("%Y-%m")
        )


    fig = go.Figure()


    # CPA 막대
    fig.add_trace(
        go.Bar(
            x=x_values,
            y=trend_df["CPA"],
            name="CPA",
            text=[
                (
                    f"{v:,.0f}원"
                    if pd.notna(v)
                    else "-"
                )
                for v in trend_df["CPA"]
            ],
            textposition="outside",
            hovertemplate=(
                "%{x}<br>"
                "CPA: %{y:,.0f}원"
                "<extra></extra>"
            )
        )
    )


    # 전환수 라인
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=trend_df["conversion"],
            name="전환수",
            mode="lines+markers",
            yaxis="y2",
            hovertemplate=(
                "%{x}<br>"
                "전환수: %{y:,.0f}건"
                "<extra></extra>"
            )
        )
    )


    fig.update_layout(

        title=(
            f"{trend_type} CPA + 전환수"
            f"<br><sup>{current_period_text}</sup>"
        ),

        height=420,

        margin=dict(
            l=60,
            r=60,
            t=90,
            b=70
        ),

        xaxis=dict(
            title=trend_type,
            type="category",
            tickangle=-30,
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

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        )
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


with trend_tab1:
    draw_trend_chart("일자별")

with trend_tab2:
    draw_trend_chart("주차별")

with trend_tab3:
    draw_trend_chart("월별")


# ============================================================
# 19. 성과 비교
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text} | "
    f"비교 기간: {previous_period_text} | "
    f"동일 진행일수: {elapsed_days}일"
)


chart_df = comparison.copy()


if not chart_df.empty:

    chart_df = chart_df[
        chart_df["media"].isin(
            selected_media
        )
    ].copy()


    chart_df = chart_df.sort_values(
        "conversion_current",
        ascending=False
    )


if not chart_df.empty:

    x_labels = chart_df["media"].tolist()


    # --------------------------------------------------------
    # CPA + 전환수
    # --------------------------------------------------------

    fig_cpa = go.Figure()


    fig_cpa.add_trace(
        go.Bar(
            x=x_labels,
            y=chart_df["CPA_current"],
            name="기준 CPA",
            text=[
                (
                    f"{v:,.0f}원"
                    if pd.notna(v)
                    else "-"
                )
                for v in chart_df["CPA_current"]
            ],
            textposition="outside"
        )
    )


    fig_cpa.add_trace(
        go.Bar(
            x=x_labels,
            y=chart_df["CPA_previous"],
            name="비교 CPA",
            text=[
                (
                    f"{v:,.0f}원"
                    if pd.notna(v)
                    else "-"
                )
                for v in chart_df["CPA_previous"]
            ],
            textposition="outside"
        )
    )


    fig_cpa.add_trace(
        go.Scatter(
            x=x_labels,
            y=chart_df["conversion_current"],
            name="기준 전환수",
            mode="lines+markers",
            yaxis="y2"
        )
    )


    fig_cpa.add_trace(
        go.Scatter(
            x=x_labels,
            y=chart_df["conversion_previous"],
            name="비교 전환수",
            mode="lines+markers",
            yaxis="y2"
        )
    )


    fig_cpa.update_layout(

        title="CPA + 전환수",

        barmode="group",

        height=390,

        margin=dict(
            l=50,
            r=50,
            t=70,
            b=100
        ),

        xaxis=dict(
            title="매체",
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

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.30,
            xanchor="center",
            x=0.5
        ),

        hovermode="x unified"
    )


    # --------------------------------------------------------
    # 광고비 + 전환수
    # --------------------------------------------------------

    fig_spend = go.Figure()


    fig_spend.add_trace(
        go.Bar(
            x=x_labels,
            y=chart_df["spend_current"],
            name="기준 광고비",
            text=[
                f"{v:,.0f}"
                for v in chart_df["spend_current"]
            ],
            textposition="outside"
        )
    )


    fig_spend.add_trace(
        go.Bar(
            x=x_labels,
            y=chart_df["spend_previous"],
            name="비교 광고비",
            text=[
                f"{v:,.0f}"
                for v in chart_df["spend_previous"]
            ],
            textposition="outside"
        )
    )


    fig_spend.add_trace(
        go.Scatter(
            x=x_labels,
            y=chart_df["conversion_current"],
            name="기준 전환수",
            mode="lines+markers",
            yaxis="y2"
        )
    )


    fig_spend.add_trace(
        go.Scatter(
            x=x_labels,
            y=chart_df["conversion_previous"],
            name="비교 전환수",
            mode="lines+markers",
            yaxis="y2"
        )
    )


    fig_spend.update_layout(

        title="광고비 + 전환수",

        barmode="group",

        height=390,

        margin=dict(
            l=50,
            r=50,
            t=70,
            b=100
        ),

        xaxis=dict(
            title="매체",
            type="category",
            tickangle=-35,
            automargin=True
        ),

        yaxis=dict(
            title="광고비"
        ),

        yaxis2=dict(
            title="전환수",
            overlaying="y",
            side="right"
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.30,
            xanchor="center",
            x=0.5
        ),

        hovermode="x unified"
    )


    graph_col1, graph_col2 = st.columns(2)


    with graph_col1:

        st.plotly_chart(
            fig_cpa,
            use_container_width=True,
            config={
                "displayModeBar": False
            }
        )


    with graph_col2:

        st.plotly_chart(
            fig_spend,
            use_container_width=True,
            config={
                "displayModeBar": False
            }
        )

else:

    st.info(
        "선택한 조건에 해당하는 성과 데이터가 없습니다."
    )


# ============================================================
# 20. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "선택한 TYPE / 매체 기준으로 현재 기간과 비교 기간의 성과를 비교합니다."
)


media_table = comparison.copy()


if not media_table.empty:

    media_table = media_table[
        media_table["media"].isin(
            selected_media
        )
    ].copy()


    media_table = media_table.sort_values(
        "conversion_current",
        ascending=False
    )


# ============================================================
# 표를 HTML이 아닌 Streamlit DataFrame으로 생성
# ============================================================

if media_table.empty:

    st.info(
        "선택한 매체의 성과 데이터가 없습니다."
    )

else:

    media_display = pd.DataFrame(
        index=[
            "광고비",
            "전환수",
            "CPA",
            "CVR"
        ]
    )


    for _, row in media_table.iterrows():

        media = row["media"]


        spend_change = row["spend_change"]
        conversion_change = row["conversion_change"]
        cpa_change = row["CPA_change"]
        cvr_change = row["CVR_change"]


        media_display[media] = [

            (
                f"기준: {fmt_money(row['spend_current'])}\n"
                f"비교: {fmt_money(row['spend_previous'])}\n"
                f"{fmt_change(spend_change)}"
            ),

            (
                f"기준: {fmt_number(row['conversion_current'])}\n"
                f"비교: {fmt_number(row['conversion_previous'])}\n"
                f"{fmt_change(conversion_change)}"
            ),

            (
                f"기준: {fmt_money(row['CPA_current'])}\n"
                f"비교: {fmt_money(row['CPA_previous'])}\n"
                f"{fmt_change(cpa_change)}"
            ),

            (
                f"기준: {fmt_percent(row['CVR_current'])}\n"
                f"비교: {fmt_percent(row['CVR_previous'])}\n"
                f"{fmt_change(cvr_change)}"
            )

        ]


    st.dataframe(
        media_display,
        use_container_width=True,
        height=300
    )


# ============================================================
# 21. 매체 성과 코멘트
# ============================================================

st.subheader("📝 매체 성과 코멘트")


if media_table.empty:

    st.info(
        "선택한 매체의 성과 데이터가 없습니다."
    )

else:

    total_media_conversion = (
        media_table["conversion_current"]
        .sum()
    )


    # --------------------------------------------------------
    # 매체별 순위
    # --------------------------------------------------------

    media_rank = media_table.sort_values(
        "conversion_current",
        ascending=False
    ).reset_index(drop=True)


    for rank, row in media_rank.iterrows():

        media = row["media"]

        spend = row["spend_current"]
        conversion = row["conversion_current"]
        cpa = row["CPA_current"]
        cvr = row["CVR_current"]

        spend_change = row["spend_change"]
        conversion_change = row["conversion_change"]
        cpa_change = row["CPA_change"]
        cvr_change = row["CVR_change"]


        share = (
            conversion /
            total_media_conversion *
            100
            if total_media_conversion > 0
            else np.nan
        )


        # ----------------------------------------------------
        # 핵심 상태
        # ----------------------------------------------------

        if (
            pd.notna(cpa_change)
            and cpa_change < -10
            and pd.notna(conversion_change)
            and conversion_change > 0
        ):

            status = (
                "효율과 볼륨이 동시에 개선된 매체"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change > 10
            and pd.notna(conversion_change)
            and conversion_change < 0
        ):

            status = (
                "효율과 볼륨이 동시에 악화된 매체"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change < -10
        ):

            status = (
                "CPA 효율이 개선된 매체"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change > 10
        ):

            status = (
                "CPA 효율 점검이 필요한 매체"
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change > 10
        ):

            status = (
                "전환 볼륨이 확대된 매체"
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change < -10
        ):

            status = (
                "전환 볼륨이 감소한 매체"
            )

        else:

            status = (
                "성과 변동을 지속적으로 확인할 매체"
            )


        # ----------------------------------------------------
        # 기본 코멘트
        # ----------------------------------------------------

        st.markdown(
            f"### {rank + 1}. `{media}` — {status}"
        )


        st.markdown(
            f"""
**광고비:** {fmt_money(spend)} "
**({fmt_change(spend_change)})**  
**전환:** {fmt_number(conversion)} "
**({fmt_change(conversion_change)})**  
**CPA:** {fmt_money(cpa)} "
**({fmt_change(cpa_change)})**  
**CVR:** {fmt_percent(cvr)} "
**({fmt_change(cvr_change)})**  
**전체 선택 매체 전환 비중:** "
**{share:.1f}%**
"""
        )


        # ----------------------------------------------------
        # 상세 분석 문장
        # ----------------------------------------------------

        detail_sentences = []


        if (
            pd.notna(conversion_change)
            and conversion_change > 10
            and pd.notna(cpa_change)
            and cpa_change < 0
        ):

            detail_sentences.append(
                "전환수가 증가하는 동시에 CPA가 하락해 "
                "볼륨과 효율이 함께 개선된 흐름입니다."
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change > 10
            and pd.notna(cpa_change)
            and cpa_change > 0
        ):

            detail_sentences.append(
                "전환 볼륨은 증가했지만 CPA도 상승해 "
                "추가 예산 확대 시 효율 악화 여부를 확인할 필요가 있습니다."
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change < -10
            and pd.notna(cpa_change)
            and cpa_change < 0
        ):

            detail_sentences.append(
                "전환수는 감소했지만 CPA는 개선되어 "
                "효율은 좋아졌으나 볼륨이 축소된 상태입니다."
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change < -10
            and pd.notna(cpa_change)
            and cpa_change > 0
        ):

            detail_sentences.append(
                "전환수가 감소하는 동시에 CPA가 상승해 "
                "현재 매체의 볼륨과 효율을 함께 점검할 필요가 있습니다."
            )


        if (
            pd.notna(cvr_change)
            and cvr_change > 10
        ):

            detail_sentences.append(
                "CVR이 개선되어 동일한 클릭 대비 전환 효율이 "
                "좋아진 것으로 볼 수 있습니다."
            )

        elif (
            pd.notna(cvr_change)
            and cvr_change < -10
        ):

            detail_sentences.append(
                "CVR이 하락해 클릭 이후 전환 단계에서 "
                "이탈이 증가했는지 확인할 필요가 있습니다."
            )


        if (
            pd.notna(spend_change)
            and spend_change > 20
            and pd.notna(conversion_change)
            and conversion_change < 0
        ):

            detail_sentences.append(
                "광고비는 크게 증가했지만 전환수는 감소했기 때문에 "
                "예산 확대 대비 성과가 충분히 따라오고 있는지 확인이 필요합니다."
            )


        if not detail_sentences:

            detail_sentences.append(
                "현재 성과는 비교 기간 대비 큰 변동이 없어 "
                "추가적인 추세 확인이 필요합니다."
            )


        for sentence in detail_sentences:

            st.markdown(
                f"- {sentence}"
            )


# ============================================================
# 22. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 TYPE / 매체 조건 안에서 캠페인별 성과를 상세 비교합니다."
)


# ============================================================
# 캠페인 집계
# ============================================================

def aggregate_by_campaign(data):

    if data.empty:

        return pd.DataFrame(
            columns=[
                "campaign",
                "spend",
                "click",
                "conversion",
                "CPA",
                "CVR"
            ]
        )


    result = (
        data
        .groupby(
            "campaign",
            as_index=False
        )
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )


    result["CPA"] = result.apply(
        lambda x:
        safe_cpa(
            x["spend"],
            x["conversion"]
        ),
        axis=1
    )


    result["CVR"] = result.apply(
        lambda x:
        safe_cvr(
            x["conversion"],
            x["click"]
        ),
        axis=1
    )


    return result


current_campaign = aggregate_by_campaign(
    current_df
)

previous_campaign = aggregate_by_campaign(
    previous_df
)


campaign_comparison = create_comparison(
    current_campaign,
    previous_campaign,
    "campaign"
)


campaign_table = campaign_comparison.copy()


if not campaign_table.empty:

    campaign_table = campaign_table[
        campaign_table["campaign"].isin(
            selected_campaigns
        )
    ].copy()


    campaign_table = campaign_table.sort_values(
        "conversion_current",
        ascending=False
    )


# ============================================================
# 캠페인 상세표
# ============================================================

if campaign_table.empty:

    st.info(
        "선택한 캠페인의 성과 데이터가 없습니다."
    )

else:

    campaign_display = pd.DataFrame(
        index=[
            "광고비",
            "전환수",
            "CPA",
            "CVR"
        ]
    )


    for _, row in campaign_table.iterrows():

        campaign = row["campaign"]


        campaign_display[campaign] = [

            (
                f"기준: {fmt_money(row['spend_current'])}\n"
                f"비교: {fmt_money(row['spend_previous'])}\n"
                f"{fmt_change(row['spend_change'])}"
            ),

            (
                f"기준: {fmt_number(row['conversion_current'])}\n"
                f"비교: {fmt_number(row['conversion_previous'])}\n"
                f"{fmt_change(row['conversion_change'])}"
            ),

            (
                f"기준: {fmt_money(row['CPA_current'])}\n"
                f"비교: {fmt_money(row['CPA_previous'])}\n"
                f"{fmt_change(row['CPA_change'])}"
            ),

            (
                f"기준: {fmt_percent(row['CVR_current'])}\n"
                f"비교: {fmt_percent(row['CVR_previous'])}\n"
                f"{fmt_change(row['CVR_change'])}"
            )

        ]


    st.dataframe(
        campaign_display,
        use_container_width=True,
        height=400
    )


# ============================================================
# 23. 캠페인 성과 코멘트
# ============================================================

st.subheader("📝 캠페인 성과 코멘트")


if campaign_table.empty:

    st.info(
        "선택한 캠페인의 성과 데이터가 없습니다."
    )

else:

    valid_campaigns = campaign_table[
        campaign_table["conversion_current"] > 0
    ].copy()


    total_campaign_conversion = (
        campaign_table["conversion_current"]
        .sum()
    )


    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

    cpa_valid = valid_campaigns[
        valid_campaigns["CPA_current"].notna() &
        (valid_campaigns["CPA_current"] > 0)
    ].copy()


    if not cpa_valid.empty:

        best = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmin()
        ]


        best_share = (
            best["conversion_current"]
            /
            total_campaign_conversion
            *
            100
            if total_campaign_conversion > 0
            else np.nan
        )


        st.markdown(
            f"🏆 **CPA 최우수 캠페인:** "
            f"`{best['campaign']}` — "
            f"CPA **{best['CPA_current']:,.0f}원**, "
            f"전환 **{best['conversion_current']:,.0f}건** "
            f"(전체 전환의 **{best_share:.1f}%**)"
        )


    # --------------------------------------------------------
    # 전환수 최다
    # --------------------------------------------------------

    if not valid_campaigns.empty:

        best_conversion = valid_campaigns.loc[
            valid_campaigns[
                "conversion_current"
            ].idxmax()
        ]


        best_conversion_share = (
            best_conversion["conversion_current"]
            /
            total_campaign_conversion
            *
            100
            if total_campaign_conversion > 0
            else np.nan
        )


        best_conversion_cpa = (
            fmt_money(
                best_conversion["CPA_current"]
            )
        )


        st.markdown(
            f"📈 **전환수 최다 캠페인:** "
            f"`{best_conversion['campaign']}` — "
            f"전환 **{best_conversion['conversion_current']:,.0f}건**, "
            f"CPA **{best_conversion_cpa}** "
            f"(전체 전환의 **{best_conversion_share:.1f}%**)"
        )


    # --------------------------------------------------------
    # 전환 증가폭 최대
    # --------------------------------------------------------

    growth_df = campaign_table[
        campaign_table["conversion_change"].notna()
    ].copy()


    if not growth_df.empty:

        growth_best = growth_df.loc[
            growth_df["conversion_change"].idxmax()
        ]


        if growth_best["conversion_change"] > 0:

            st.markdown(
                f"🚀 **전환 증가폭 최대 캠페인:** "
                f"`{growth_best['campaign']}` — "
                f"전환 **{growth_best['conversion_change']:+.1f}%** "
                f"증가"
            )


    # --------------------------------------------------------
    # CPA 개선 최대
    # --------------------------------------------------------

    cpa_improved = campaign_table[
        campaign_table["CPA_change"].notna()
    ].copy()


    if not cpa_improved.empty:

        cpa_best = cpa_improved.loc[
            cpa_improved["CPA_change"].idxmin()
        ]


        if cpa_best["CPA_change"] < 0:

            st.markdown(
                f"💰 **CPA 개선폭 최대 캠페인:** "
                f"`{cpa_best['campaign']}` — "
                f"CPA **{cpa_best['CPA_change']:+.1f}%** 개선"
            )


    # --------------------------------------------------------
    # CPA 악화 최대
    # --------------------------------------------------------

    cpa_worst_df = campaign_table[
        campaign_table["CPA_change"].notna()
    ].copy()


    if not cpa_worst_df.empty:

        cpa_worst = cpa_worst_df.loc[
            cpa_worst_df["CPA_change"].idxmax()
        ]


        if cpa_worst["CPA_change"] > 10:

            st.markdown(
                f"⚠️ **CPA 악화 주의 캠페인:** "
                f"`{cpa_worst['campaign']}` — "
                f"CPA **{cpa_worst['CPA_change']:+.1f}%** 상승"
            )


    # --------------------------------------------------------
    # CVR 개선 최대
    # --------------------------------------------------------

    cvr_df = campaign_table[
        campaign_table["CVR_change"].notna()
    ].copy()


    if not cvr_df.empty:

        cvr_best = cvr_df.loc[
            cvr_df["CVR_change"].idxmax()
        ]


        if cvr_best["CVR_change"] > 10:

            st.markdown(
                f"📊 **CVR 개선폭 최대 캠페인:** "
                f"`{cvr_best['campaign']}` — "
                f"CVR **{cvr_best['CVR_change']:+.1f}%** 개선"
            )


    # ========================================================
    # 캠페인별 상세 코멘트
    # ========================================================

    st.markdown("#### 캠페인별 상세 분석")


    for rank, (_, row) in enumerate(
        campaign_table.iterrows(),
        start=1
    ):

        campaign = row["campaign"]

        spend = row["spend_current"]
        conversion = row["conversion_current"]
        cpa = row["CPA_current"]
        cvr = row["CVR_current"]

        spend_change = row["spend_change"]
        conversion_change = row["conversion_change"]
        cpa_change = row["CPA_change"]
        cvr_change = row["CVR_change"]


        share = (
            conversion /
            total_campaign_conversion *
            100
            if total_campaign_conversion > 0
            else np.nan
        )


        # ----------------------------------------------------
        # 캠페인 상태 판단
        # ----------------------------------------------------

        if (
            pd.notna(cpa_change)
            and cpa_change < -10
            and pd.notna(conversion_change)
            and conversion_change > 10
        ):

            status = (
                "효율과 전환 볼륨이 함께 개선된 캠페인"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change > 10
            and pd.notna(conversion_change)
            and conversion_change < -10
        ):

            status = (
                "효율과 볼륨 모두 점검이 필요한 캠페인"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change < -10
        ):

            status = (
                "CPA 효율이 개선된 캠페인"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change > 10
        ):

            status = (
                "CPA 상승으로 효율 점검이 필요한 캠페인"
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change > 10
        ):

            status = (
                "전환 볼륨이 확대된 캠페인"
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change < -10
        ):

            status = (
                "전환 볼륨이 감소한 캠페인"
            )

        else:

            status = (
                "성과 추이를 지속적으로 확인할 캠페인"
            )


        st.markdown(
            f"**{rank}. `{campaign}` — {status}**"
        )


        # ----------------------------------------------------
        # 기본 지표
        # ----------------------------------------------------

        st.markdown(
            f"""
- 광고비: **{fmt_money(spend)}** "
  ({fmt_change(spend_change)})
- 전환: **{fmt_number(conversion)}** "
  ({fmt_change(conversion_change)})
- CPA: **{fmt_money(cpa)}** "
  ({fmt_change(cpa_change)})
- CVR: **{fmt_percent(cvr)}** "
  ({fmt_change(cvr_change)})
- 전체 캠페인 전환 비중: **{share:.1f}%**
"""
        )


        # ----------------------------------------------------
        # 상세 진단
        # ----------------------------------------------------

        campaign_sentences = []


        # 전환 + CPA
        if (
            pd.notna(conversion_change)
            and conversion_change > 10
            and pd.notna(cpa_change)
            and cpa_change < 0
        ):

            campaign_sentences.append(
                "전환수 증가와 CPA 개선이 동시에 나타나 "
                "현재 기간에서 가장 긍정적인 성과 흐름을 보이고 있습니다."
            )


        elif (
            pd.notna(conversion_change)
            and conversion_change > 10
            and pd.notna(cpa_change)
            and cpa_change > 0
        ):

            campaign_sentences.append(
                "전환 볼륨은 증가했지만 CPA도 상승했기 때문에 "
                "볼륨 확대 과정에서 효율이 희생되고 있는지 확인할 필요가 있습니다."
            )


        elif (
            pd.notna(conversion_change)
            and conversion_change < -10
            and pd.notna(cpa_change)
            and cpa_change < 0
        ):

            campaign_sentences.append(
                "전환수는 감소했지만 CPA는 개선되어 "
                "효율 측면에서는 긍정적이나 볼륨 확보가 필요한 상태입니다."
            )


        elif (
            pd.notna(conversion_change)
            and conversion_change < -10
            and pd.notna(cpa_change)
            and cpa_change > 0
        ):

            campaign_sentences.append(
                "전환수가 감소하는 동시에 CPA가 상승해 "
                "효율과 볼륨 모두 점검이 필요한 상태입니다."
            )


        # CVR
        if (
            pd.notna(cvr_change)
            and cvr_change > 10
        ):

            campaign_sentences.append(
                "CVR이 개선되어 클릭 이후 전환 효율이 "
                "이전 기간보다 좋아진 흐름입니다."
            )


        elif (
            pd.notna(cvr_change)
            and cvr_change < -10
        ):

            campaign_sentences.append(
                "CVR이 하락해 랜딩페이지, 타겟, 소재 또는 "
                "전환 과정에서의 이탈 증가 여부를 확인할 필요가 있습니다."
            )


        # 광고비와 전환 관계
        if (
            pd.notna(spend_change)
            and spend_change > 20
            and pd.notna(conversion_change)
            and conversion_change < 0
        ):

            campaign_sentences.append(
                "광고비가 증가했음에도 전환수가 감소했기 때문에 "
                "추가 예산 투입보다는 타겟·소재·캠페인 구조를 우선 점검하는 것이 좋습니다."
            )


        elif (
            pd.notna(spend_change)
            and spend_change < -20
            and pd.notna(conversion_change)
            and conversion_change > 0
        ):

            campaign_sentences.append(
                "광고비가 감소했음에도 전환수가 증가해 "
                "비용 효율 측면에서 긍정적인 흐름으로 볼 수 있습니다."
            )


        if not campaign_sentences:

            campaign_sentences.append(
                "비교 기간 대비 주요 지표의 변동성이 크지 않아 "
                "추가 기간 데이터를 통해 추세를 확인하는 것이 좋습니다."
            )


        for sentence in campaign_sentences:

            st.markdown(
                f"- {sentence}"
            )


# ============================================================
# 24. 데이터 정보
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
        f"데이터 시작일: "
        f"{df['date'].min().strftime('%Y-%m-%d')}"
    )

    st.write(
        f"데이터 최신일: "
        f"{df['date'].max().strftime('%Y-%m-%d')}"
    )

    st.write(
        f"기준 기간: {current_period_text}"
    )

    st.write(
        f"비교 기간: {previous_period_text}"
    )

    st.write(
        f"동일 진행일수: {elapsed_days}일"
    )

    st.write(
        f"선택 TYPE: "
        f"{', '.join(selected_types) if selected_types else '없음'}"
    )

    st.write(
        f"선택 매체: {len(selected_media)}개"
    )

    st.write(
        f"선택 캠페인: {len(selected_campaigns)}개"
    )
