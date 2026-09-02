import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import timedelta
import calendar
import html


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
    # 컬럼 자동 매칭
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
            f"필수 컬럼을 찾을 수 없습니다: {missing}\n\n"
            f"현재 컬럼: {df.columns.tolist()}"
        )


    # --------------------------------------------------------
    # 내부 표준 컬럼
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
            .str.strip()
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
    변화율 계산

    이전값이 0이면:
    - 현재도 0 → 0%
    - 현재 > 0 → NaN
      (표에서는 신규로 표시)
    """

    if pd.isna(current) or pd.isna(previous):

        return np.nan

    if previous == 0:

        if current == 0:
            return 0.0

        return np.nan

    return (
        (current - previous)
        / previous
        * 100
    )


def format_money(value):

    if pd.isna(value):
        return "-"

    return f"{value:,.0f}원"


def format_number(value):

    if pd.isna(value):
        return "-"

    return f"{value:,.0f}건"


def format_percent(value):

    if pd.isna(value):
        return "-"

    return f"{value:.2f}%"


def format_change(
    current,
    previous,
    change,
    inverse=False
):

    # 둘 다 0
    if (
        pd.notna(current)
        and pd.notna(previous)
        and current == 0
        and previous == 0
    ):

        return "─ 0.0%", "neutral"


    # 이전값 0 + 현재값 존재
    if (
        pd.notna(current)
        and pd.notna(previous)
        and previous == 0
        and current != 0
    ):

        return "신규", "neutral"


    # 변화율 없음
    if pd.isna(change):

        return "-", "neutral"


    if change > 0:

        arrow = "▲"

        # CPA는 상승이 나쁨
        if inverse:
            css_class = "bad"
        else:
            css_class = "up"

        return (
            f"{arrow} +{change:,.1f}%",
            css_class
        )


    if change < 0:

        arrow = "▼"

        # CPA는 하락이 좋음
        if inverse:
            css_class = "good"
        else:
            css_class = "down"

        return (
            f"{arrow} {change:,.1f}%",
            css_class
        )


    return "─ 0.0%", "neutral"


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
            base_date - timedelta(days=1)
        )

        previous_end = (
            base_date - timedelta(days=1)
        )


    # --------------------------------------------------------
    # 전주
    # --------------------------------------------------------

    elif period_type == "전주":

        weekday = base_date.weekday()

        current_start = (
            base_date
            - timedelta(days=weekday)
        )

        current_end = base_date

        elapsed_days = (
            current_end - current_start
        ).days

        previous_end = (
            current_end
            - timedelta(days=7)
        )

        previous_start = (
            previous_end
            - timedelta(days=elapsed_days)
        )


    # --------------------------------------------------------
    # 전월
    # --------------------------------------------------------

    elif period_type == "전월":

        current_start = base_date.replace(
            day=1
        )

        current_end = base_date

        day_number = base_date.day

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
            day_number,
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


# ============================================================
# 7. 성과 집계
# ============================================================

def aggregate_performance(
    data,
    start_date,
    end_date
):

    temp = data[
        (data["date"] >= pd.Timestamp(start_date))
        &
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


    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"]
        / result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"]
        / result["click"]
        * 100,
        np.nan
    )


    return result


# ============================================================
# 8. 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")


available_dates = sorted(
    df["date"]
    .dropna()
    .unique()
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


# ============================================================
# 기준일
# ============================================================

with col1:

    base_date = st.date_input(
        "기준일",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )


# ============================================================
# 비교 기간
# ============================================================

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
# 기간 설정
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
        current_end
        - current_start
    ).days + 1


else:

    st.markdown("### 📅 지정 기간")

    custom_col1, custom_col2 = st.columns(2)


    # ========================================================
    # 기준 기간
    # ========================================================

    with custom_col1:

        st.markdown("**기준 기간**")

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
            max_value=base_date,
            key="custom_current_end"
        )


    current_start = pd.Timestamp(
        custom_current_start
    )

    current_end = pd.Timestamp(
        custom_current_end
    )


    current_days = (
        current_end - current_start
    ).days + 1


    # ========================================================
    # 비교 기간
    # ========================================================

    with custom_col2:

        st.markdown("**비교 기간**")

        custom_previous_start = st.date_input(
            "비교 시작일",
            value=(
                current_start
                - timedelta(days=current_days)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_start"
        )

        custom_previous_end = st.date_input(
            "비교 종료일",
            value=(
                pd.Timestamp(custom_previous_start)
                + timedelta(days=current_days - 1)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_end"
        )


    previous_start = pd.Timestamp(
        custom_previous_start
    )

    previous_end = pd.Timestamp(
        custom_previous_end
    )


    previous_days = (
        previous_end - previous_start
    ).days + 1


    # ========================================================
    # 날짜 역전 체크
    # ========================================================

    if current_start > current_end:

        st.error(
            "⚠️ 기준 시작일은 기준 종료일보다 "
            "빠르거나 같아야 합니다."
        )

        st.stop()


    if previous_start > previous_end:

        st.error(
            "⚠️ 비교 시작일은 비교 종료일보다 "
            "빠르거나 같아야 합니다."
        )

        st.stop()


    # ========================================================
    # 동일 일수 체크
    # ========================================================

    if current_days != previous_days:

        st.error(
            f"⚠️ 동일 일수로 설정해야 합니다.\n\n"
            f"기준 기간: {current_days}일\n"
            f"비교 기간: {previous_days}일"
        )

        st.stop()


    elapsed_days = current_days


# ============================================================
# 기간 텍스트
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
# 9. TYPE / 매체 / 캠페인
# ============================================================

st.divider()

type_options = sorted(
    df["type"]
    .dropna()
    .unique()
    .tolist()
)

media_options = sorted(
    df["media"]
    .dropna()
    .unique()
    .tolist()
)

campaign_options = sorted(
    df["campaign"]
    .dropna()
    .unique()
    .tolist()
)


filter_col1, filter_col2, filter_col3 = st.columns(
    [1, 2, 2]
)


# ============================================================
# TYPE
# ============================================================

with filter_col1:

    selected_types = st.multiselect(
        "TYPE",
        options=type_options,
        default=type_options,
        key="type_filter"
    )


# ============================================================
# 매체
# ============================================================

with filter_col2:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_options,
        default=media_options,
        key="media_filter"
    )


# ============================================================
# 캠페인
# ============================================================

with filter_col3:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=campaign_options,
        default=campaign_options,
        key="campaign_filter"
    )


# ============================================================
# 전체 선택
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

        st.session_state["media_filter"] = media_options

        st.rerun()


with button_col3:

    if st.button(
        "📌 캠페인 전체 선택",
        use_container_width=True
    ):

        st.session_state["campaign_filter"] = campaign_options

        st.rerun()


# ============================================================
# 10. 필터 데이터
# ============================================================

filtered_df = df[
    df["type"].isin(selected_types)
    &
    df["media"].isin(selected_media)
    &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 11. 현재 / 비교 데이터
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
# 12. 매체별 집계
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


    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"]
        / result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"]
        / result["click"]
        * 100,
        np.nan
    )


    return result


current_media = aggregate_by_media(
    current_df
)

previous_media = aggregate_by_media(
    previous_df
)


# ============================================================
# 13. 비교 데이터 생성
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


    current = current[
        [
            group_col,
            "spend",
            "click",
            "conversion"
        ]
    ]

    previous = previous[
        [
            group_col,
            "spend",
            "click",
            "conversion"
        ]
    ]


    current = (
        current
        .groupby(
            group_col,
            as_index=False
        )
        .sum()
    )

    previous = (
        previous
        .groupby(
            group_col,
            as_index=False
        )
        .sum()
    )


    merged = pd.merge(
        current,
        previous,
        on=group_col,
        how="outer",
        suffixes=(
            "_current",
            "_previous"
        )
    )


    for col in [
        "spend_current",
        "spend_previous",
        "click_current",
        "click_previous",
        "conversion_current",
        "conversion_previous"
    ]:

        if col not in merged.columns:

            merged[col] = 0

        merged[col] = (
            pd.to_numeric(
                merged[col],
                errors="coerce"
            )
            .fillna(0)
        )


    # --------------------------------------------------------
    # CPA
    # --------------------------------------------------------

    merged["CPA_current"] = np.where(
        merged["conversion_current"] > 0,
        merged["spend_current"]
        / merged["conversion_current"],
        np.nan
    )


    merged["CPA_previous"] = np.where(
        merged["conversion_previous"] > 0,
        merged["spend_previous"]
        / merged["conversion_previous"],
        np.nan
    )


    # --------------------------------------------------------
    # CVR
    # --------------------------------------------------------

    merged["CVR_current"] = np.where(
        merged["click_current"] > 0,
        merged["conversion_current"]
        / merged["click_current"]
        * 100,
        np.nan
    )


    merged["CVR_previous"] = np.where(
        merged["click_previous"] > 0,
        merged["conversion_previous"]
        / merged["click_previous"]
        * 100,
        np.nan
    )


    # --------------------------------------------------------
    # 변화율
    # --------------------------------------------------------

    merged["spend_change"] = [
        safe_change(c, p)
        for c, p in zip(
            merged["spend_current"],
            merged["spend_previous"]
        )
    ]


    merged["conversion_change"] = [
        safe_change(c, p)
        for c, p in zip(
            merged["conversion_current"],
            merged["conversion_previous"]
        )
    ]


    merged["CPA_change"] = [
        safe_change(c, p)
        for c, p in zip(
            merged["CPA_current"],
            merged["CPA_previous"]
        )
    ]


    merged["CVR_change"] = [
        safe_change(c, p)
        for c, p in zip(
            merged["CVR_current"],
            merged["CVR_previous"]
        )
    ]


    return merged


comparison = create_comparison(
    current_media,
    previous_media,
    "media"
)


# ============================================================
# 14. 전체 성과 요약
# ============================================================

st.divider()

st.header("📊 전체 성과 요약")


total_current_spend = (
    current_df["spend"].sum()
)

total_previous_spend = (
    previous_df["spend"].sum()
)

total_current_conversion = (
    current_df["conversion"].sum()
)

total_previous_conversion = (
    previous_df["conversion"].sum()
)

total_current_click = (
    current_df["click"].sum()
)

total_previous_click = (
    previous_df["click"].sum()
)


total_current_cpa = (
    total_current_spend
    / total_current_conversion
    if total_current_conversion > 0
    else np.nan
)


total_previous_cpa = (
    total_previous_spend
    / total_previous_conversion
    if total_previous_conversion > 0
    else np.nan
)


total_current_cvr = (
    total_current_conversion
    / total_current_click
    * 100
    if total_current_click > 0
    else np.nan
)


total_previous_cvr = (
    total_previous_conversion
    / total_previous_click
    * 100
    if total_previous_click > 0
    else np.nan
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

    delta = (
        f"{total_spend_change:+.1f}%"
        if pd.notna(total_spend_change)
        else (
            "신규"
            if total_previous_spend == 0
            and total_current_spend > 0
            else "-"
        )
    )

    st.metric(
        "광고비",
        format_money(total_current_spend),
        delta
    )


with summary_col2:

    delta = (
        f"{total_conversion_change:+.1f}%"
        if pd.notna(total_conversion_change)
        else (
            "신규"
            if total_previous_conversion == 0
            and total_current_conversion > 0
            else "-"
        )
    )

    st.metric(
        "전환수",
        format_number(total_current_conversion),
        delta
    )


with summary_col3:

    delta = (
        f"{total_cpa_change:+.1f}%"
        if pd.notna(total_cpa_change)
        else "-"
    )

    st.metric(
        "CPA",
        format_money(total_current_cpa),
        delta,
        delta_color="inverse"
    )


with summary_col4:

    delta = (
        f"{total_cvr_change:+.1f}%"
        if pd.notna(total_cvr_change)
        else "-"
    )

    st.metric(
        "CVR",
        format_percent(total_current_cvr),
        delta
    )


# ============================================================
# 15. 성과 추이
# ============================================================

st.divider()

st.header("📈 성과 추이")

st.caption(
    f"현재 설정한 기준 기간 {current_period_text} 내 데이터만 표시합니다."
)


def create_trend_data(
    data,
    start_date,
    end_date,
    trend_type
):

    temp = data[
        (data["date"] >= pd.Timestamp(start_date))
        &
        (data["date"] <= pd.Timestamp(end_date))
    ].copy()


    if temp.empty:

        return pd.DataFrame(
            columns=[
                "period",
                "spend",
                "click",
                "conversion",
                "CPA",
                "CVR"
            ]
        )


    # --------------------------------------------------------
    # 일자별
    # --------------------------------------------------------

    if trend_type == "일자별":

        temp["period"] = temp["date"]


    # --------------------------------------------------------
    # 주차별
    # --------------------------------------------------------

    elif trend_type == "주차별":

        temp["period"] = (
            temp["date"]
            - pd.to_timedelta(
                temp["date"].dt.weekday,
                unit="D"
            )
        )


    # --------------------------------------------------------
    # 월별
    # --------------------------------------------------------

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


    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"]
        / result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"]
        / result["click"]
        * 100,
        np.nan
    )


    return result.sort_values("period")


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


    # CPA
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


    # 전환수
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
            f"<br><sup>"
            f"{current_period_text}"
            f"</sup>"
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
# 16. 성과 비교
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text} | "
    f"비교 기간: {previous_period_text} | "
    f"동일 진행일수: {elapsed_days}일"
)


chart_df = comparison[
    comparison["media"].isin(
        selected_media
    )
].copy()


chart_df = chart_df.sort_values(
    "conversion_current",
    ascending=False
)


x_labels = chart_df[
    "media"
].tolist()


# ============================================================
# CPA + 전환수
# ============================================================

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


# ============================================================
# 광고비 + 전환수
# ============================================================

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


# ============================================================
# 17. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "선택한 TYPE / 매체 조건을 기준으로 "
    "기준 기간과 비교 기간의 성과를 비교합니다."
)


media_table = comparison[
    comparison["media"].isin(
        selected_media
    )
].copy()


media_table = media_table.sort_values(
    "conversion_current",
    ascending=False
)


# ============================================================
# HTML 표 생성
# ============================================================

def build_performance_table(
    table_df,
    entity_col,
    entity_title
):

    if table_df.empty:

        return """
        <div style="
            padding:30px;
            text-align:center;
            color:#777;
            font-size:14px;
        ">
        선택한 조건의 데이터가 없습니다.
        </div>
        """


    rows = []


    metric_rows = [

        (
            "광고비",
            "spend_current",
            "spend_previous",
            "spend_change",
            "money",
            False
        ),

        (
            "전환수",
            "conversion_current",
            "conversion_previous",
            "conversion_change",
            "number",
            False
        ),

        (
            "CPA",
            "CPA_current",
            "CPA_previous",
            "CPA_change",
            "money",
            True
        ),

        (
            "CVR",
            "CVR_current",
            "CVR_previous",
            "CVR_change",
            "percent",
            False
        )
    ]


    # --------------------------------------------------------
    # CSS
    # --------------------------------------------------------

    css = """
    <style>

    .performance-wrapper {
        width: 100%;
        overflow-x: auto;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
    }

    .performance-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        background: white;
    }

    .performance-table th,
    .performance-table td {
        border: 1px solid #dddddd;
        padding: 10px 8px;
        text-align: center;
        white-space: nowrap;
    }

    .performance-table th {
        background: #f5f6f8;
        font-weight: 700;
        color: #333;
    }

    .performance-table th.metric-header {
        min-width: 80px;
    }

    .performance-table td.metric {
        text-align: left;
        font-weight: 700;
        background: #fafafa;
        color: #333;
    }

    .current-value {
        font-weight: 700;
        color: #222;
    }

    .previous-value {
        color: #888;
        margin-top: 4px;
    }

    .change-value {
        margin-top: 5px;
        font-weight: 700;
    }

    .up {
        color: #d62728;
    }

    .down {
        color: #2468c7;
    }

    .good {
        color: #2468c7;
    }

    .bad {
        color: #d62728;
    }

    .neutral {
        color: #777;
    }

    </style>
    """


    table_html = css

    table_html += """
    <div class="performance-wrapper">
    <table class="performance-table">
    <thead>
    <tr>
    <th class="metric-header">지표</th>
    """


    # --------------------------------------------------------
    # 헤더
    # --------------------------------------------------------

    for entity in table_df[entity_col]:

        table_html += (
            "<th>"
            f"{html.escape(str(entity))}"
            "</th>"
        )


    table_html += """
    </tr>
    </thead>
    <tbody>
    """


    # --------------------------------------------------------
    # 지표
    # --------------------------------------------------------

    for (
        metric_name,
        current_col,
        previous_col,
        change_col,
        fmt_type,
        inverse
    ) in metric_rows:


        table_html += (
            "<tr>"
            f'<td class="metric">{metric_name}</td>'
        )


        for _, row in table_df.iterrows():

            current_value = row[current_col]
            previous_value = row[previous_col]
            change_value = row[change_col]


            # ------------------------------------------------
            # 현재 / 비교 값
            # ------------------------------------------------

            if fmt_type == "money":

                current_text = format_money(
                    current_value
                )

                previous_text = format_money(
                    previous_value
                )

            elif fmt_type == "number":

                current_text = format_number(
                    current_value
                )

                previous_text = format_number(
                    previous_value
                )

            else:

                current_text = format_percent(
                    current_value
                )

                previous_text = format_percent(
                    previous_value
                )


            # ------------------------------------------------
            # 변화율
            # ------------------------------------------------

            change_text, change_class = format_change(
                current_value,
                previous_value,
                change_value,
                inverse=inverse
            )


            table_html += f"""
            <td>
                <div class="current-value">
                    기준: {current_text}
                </div>

                <div class="previous-value">
                    비교: {previous_text}
                </div>

                <div class="change-value {change_class}">
                    {change_text}
                </div>
            </td>
            """


        table_html += "</tr>"


    table_html += """
    </tbody>
    </table>
    </div>
    """


    return table_html


if media_table.empty:

    st.info(
        "선택한 매체의 성과 데이터가 없습니다."
    )

else:

    media_html = build_performance_table(
        media_table,
        "media",
        "매체"
    )

    components.html(
        media_html,
        height=max(
            260,
            115 + len(media_table) * 65
        ),
        scrolling=True
    )


# ============================================================
# 18. 매체별 성과 코멘트
# ============================================================

st.subheader("📝 매체별 성과 코멘트")


def create_media_comments(
    table_df
):

    if table_df.empty:

        st.info(
            "선택한 매체의 성과 데이터가 없습니다."
        )

        return


    valid = table_df[
        table_df["conversion_current"] > 0
    ].copy()


    if valid.empty:

        st.info(
            "현재 기간에 전환이 발생한 매체가 없습니다."
        )

        return


    # --------------------------------------------------------
    # 전체 현재 전환
    # --------------------------------------------------------

    total_conversion = (
        valid["conversion_current"].sum()
    )


    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

    cpa_valid = valid[
        valid["CPA_current"].notna()
        &
        (valid["CPA_current"] > 0)
    ]


    if not cpa_valid.empty:

        best_cpa = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmin()
        ]

        share = (
            best_cpa["conversion_current"]
            / total_conversion
            * 100
            if total_conversion > 0
            else 0
        )

        st.markdown(
            f"🏆 **CPA 최우수 매체:** "
            f"`{best_cpa['media']}` — "
            f"CPA **{best_cpa['CPA_current']:,.0f}원**, "
            f"전환 **{best_cpa['conversion_current']:,.0f}건** "
            f"(전체 전환의 {share:.1f}%)"
        )


    # --------------------------------------------------------
    # 전환 최다
    # --------------------------------------------------------

    best_conversion = valid.loc[
        valid["conversion_current"].idxmax()
    ]


    share = (
        best_conversion["conversion_current"]
        / total_conversion
        * 100
        if total_conversion > 0
        else 0
    )


    st.markdown(
        f"📈 **전환수 최다 매체:** "
        f"`{best_conversion['media']}` — "
        f"전환 **{best_conversion['conversion_current']:,.0f}건**, "
        f"CPA **{best_conversion['CPA_current']:,.0f}원**, "
        f"전체 전환의 **{share:.1f}%**"
    )


    # --------------------------------------------------------
    # CPA가 가장 높은 매체
    # --------------------------------------------------------

    if len(cpa_valid) >= 2:

        worst_cpa = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmax()
        ]


        st.markdown(
            f"⚠️ **CPA 관리 필요 매체:** "
            f"`{worst_cpa['media']}` — "
            f"CPA **{worst_cpa['CPA_current']:,.0f}원**, "
            f"전환 **{worst_cpa['conversion_current']:,.0f}건**. "
            f"상대적으로 높은 CPA가 발생하고 있어 "
            f"캠페인별 효율을 추가 점검할 필요가 있습니다."
        )


    # --------------------------------------------------------
    # 전환 증감
    # --------------------------------------------------------

    growth_df = table_df[
        table_df["conversion_change"].notna()
    ].copy()


    growth_df = growth_df[
        growth_df["conversion_current"] > 0
    ]


    if not growth_df.empty:

        growth_best = growth_df.loc[
            growth_df["conversion_change"].idxmax()
        ]


        if growth_best["conversion_change"] > 0:

            st.markdown(
                f"🚀 **전환 증가폭 최대:** "
                f"`{growth_best['media']}` — "
                f"전환 "
                f"**{growth_best['conversion_previous']:,.0f}건 "
                f"→ {growth_best['conversion_current']:,.0f}건** "
                f"({growth_best['conversion_change']:+,.1f}%)"
            )


    # --------------------------------------------------------
    # CPA 악화
    # --------------------------------------------------------

    cpa_growth = table_df[
        table_df["CPA_change"].notna()
    ].copy()


    if not cpa_growth.empty:

        cpa_growth = cpa_growth[
            cpa_growth["CPA_current"].notna()
            &
            cpa_growth["CPA_previous"].notna()
        ]


    if not cpa_growth.empty:

        worst_cpa_change = cpa_growth.loc[
            cpa_growth["CPA_change"].idxmax()
        ]


        if worst_cpa_change["CPA_change"] > 0:

            st.markdown(
                f"🔴 **CPA 악화 매체:** "
                f"`{worst_cpa_change['media']}` — "
                f"CPA "
                f"**{worst_cpa_change['CPA_previous']:,.0f}원 "
                f"→ {worst_cpa_change['CPA_current']:,.0f}원**, "
                f"**{worst_cpa_change['CPA_change']:+,.1f}%**"
            )


    # --------------------------------------------------------
    # CVR 개선
    # --------------------------------------------------------

    cvr_growth = table_df[
        table_df["CVR_change"].notna()
    ].copy()


    if not cvr_growth.empty:

        best_cvr = cvr_growth.loc[
            cvr_growth["CVR_change"].idxmax()
        ]


        if best_cvr["CVR_change"] > 5:

            st.markdown(
                f"📊 **CVR 개선 매체:** "
                f"`{best_cvr['media']}` — "
                f"CVR "
                f"**{best_cvr['CVR_previous']:.2f}% "
                f"→ {best_cvr['CVR_current']:.2f}%**, "
                f"**{best_cvr['CVR_change']:+,.1f}%**"
            )


create_media_comments(
    media_table
)


# ============================================================
# 19. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 TYPE / 매체 / 캠페인 조건 안에서 "
    "캠페인별 상세 성과를 비교합니다."
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


    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"]
        / result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"]
        / result["click"]
        * 100,
        np.nan
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


campaign_table = campaign_comparison[
    campaign_comparison["campaign"].isin(
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

    campaign_html = build_performance_table(
        campaign_table,
        "campaign",
        "캠페인"
    )

    components.html(
        campaign_html,
        height=max(
            280,
            115 + len(campaign_table) * 65
        ),
        scrolling=True
    )


# ============================================================
# 20. 캠페인 성과 코멘트
# ============================================================

st.subheader("📝 캠페인 성과 코멘트")


def create_campaign_comments(
    table_df
):

    if table_df.empty:

        st.info(
            "선택한 캠페인의 성과 데이터가 없습니다."
        )

        return


    valid = table_df[
        table_df["conversion_current"] > 0
    ].copy()


    if valid.empty:

        st.info(
            "현재 기간에 전환이 발생한 캠페인이 없습니다."
        )

        return


    total_conversion = (
        valid["conversion_current"].sum()
    )


    # ========================================================
    # 1. CPA 최우수
    # ========================================================

    cpa_valid = valid[
        valid["CPA_current"].notna()
        &
        (valid["CPA_current"] > 0)
    ]


    if not cpa_valid.empty:

        best = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmin()
        ]


        share = (
            best["conversion_current"]
            / total_conversion
            * 100
            if total_conversion > 0
            else 0
        )


        st.markdown(
            f"🏆 **CPA 최우수 캠페인:** "
            f"`{best['campaign']}` — "
            f"CPA **{best['CPA_current']:,.0f}원**, "
            f"전환 **{best['conversion_current']:,.0f}건** "
            f"(전체 전환의 {share:.1f}%)"
        )


    # ========================================================
    # 2. 전환수 최다
    # ========================================================

    best_conversion = valid.loc[
        valid["conversion_current"].idxmax()
    ]


    conversion_share = (
        best_conversion["conversion_current"]
        / total_conversion
        * 100
        if total_conversion > 0
        else 0
    )


    st.markdown(
        f"📈 **전환수 최다 캠페인:** "
        f"`{best_conversion['campaign']}` — "
        f"전환 **{best_conversion['conversion_current']:,.0f}건**, "
        f"CPA **{best_conversion['CPA_current']:,.0f}원**, "
        f"전체 전환의 **{conversion_share:.1f}%**"
    )


    # ========================================================
    # 3. 전환 증가폭 최대
    # ========================================================

    conversion_growth = table_df[
        table_df["conversion_change"].notna()
    ].copy()


    conversion_growth = conversion_growth[
        conversion_growth["conversion_current"] > 0
    ]


    if not conversion_growth.empty:

        growth_best = conversion_growth.loc[
            conversion_growth[
                "conversion_change"
            ].idxmax()
        ]


        if growth_best["conversion_change"] > 0:

            st.markdown(
                f"🚀 **전환 증가폭 최대:** "
                f"`{growth_best['campaign']}` — "
                f"전환 "
                f"**{growth_best['conversion_previous']:,.0f}건 "
                f"→ {growth_best['conversion_current']:,.0f}건** "
                f"({growth_best['conversion_change']:+,.1f}%)"
            )


    # ========================================================
    # 4. CPA 개선
    # ========================================================

    cpa_improve = table_df[
        table_df["CPA_change"].notna()
    ].copy()


    cpa_improve = cpa_improve[
        cpa_improve["CPA_previous"].notna()
        &
        cpa_improve["CPA_current"].notna()
        &
        (cpa_improve["CPA_change"] < 0)
    ]


    if not cpa_improve.empty:

        best_cpa_improve = cpa_improve.loc[
            cpa_improve["CPA_change"].idxmin()
        ]


        st.markdown(
            f"✅ **CPA 개선폭 최대:** "
            f"`{best_cpa_improve['campaign']}` — "
            f"CPA "
            f"**{best_cpa_improve['CPA_previous']:,.0f}원 "
            f"→ {best_cpa_improve['CPA_current']:,.0f}원**, "
            f"**{best_cpa_improve['CPA_change']:+,.1f}%**"
        )


    # ========================================================
    # 5. CPA 악화
    # ========================================================

    cpa_worsen = table_df[
        table_df["CPA_change"].notna()
    ].copy()


    cpa_worsen = cpa_worsen[
        cpa_worsen["CPA_previous"].notna()
        &
        cpa_worsen["CPA_current"].notna()
        &
        (cpa_worsen["CPA_change"] > 0)
    ]


    if not cpa_worsen.empty:

        worst = cpa_worsen.loc[
            cpa_worsen["CPA_change"].idxmax()
        ]


        st.markdown(
            f"⚠️ **CPA 악화폭 최대:** "
            f"`{worst['campaign']}` — "
            f"CPA "
            f"**{worst['CPA_previous']:,.0f}원 "
            f"→ {worst['CPA_current']:,.0f}원**, "
            f"**{worst['CPA_change']:+,.1f}%**. "
            f"예산, 유입량, CVR 변화를 함께 점검할 필요가 있습니다."
        )


    # ========================================================
    # 6. CVR 개선
    # ========================================================

    cvr_improve = table_df[
        table_df["CVR_change"].notna()
    ].copy()


    if not cvr_improve.empty:

        best_cvr = cvr_improve.loc[
            cvr_improve["CVR_change"].idxmax()
        ]


        if best_cvr["CVR_change"] > 5:

            st.markdown(
                f"📊 **CVR 개선폭 최대:** "
                f"`{best_cvr['campaign']}` — "
                f"CVR "
                f"**{best_cvr['CVR_previous']:.2f}% "
                f"→ {best_cvr['CVR_current']:.2f}%**, "
                f"**{best_cvr['CVR_change']:+,.1f}%**"
            )


    # ========================================================
    # 7. 신규 전환 캠페인
    # ========================================================

    new_conversion = table_df[
        (table_df["conversion_previous"] == 0)
        &
        (table_df["conversion_current"] > 0)
    ].copy()


    if not new_conversion.empty:

        new_conversion = new_conversion.sort_values(
            "conversion_current",
            ascending=False
        )


        top_new = new_conversion.iloc[0]


        st.markdown(
            f"🆕 **신규 전환 발생 캠페인:** "
            f"`{top_new['campaign']}` — "
            f"기존 **0건 → 현재 "
            f"{top_new['conversion_current']:,.0f}건**, "
            f"CPA **{top_new['CPA_current']:,.0f}원**"
        )


    # ========================================================
    # 8. 종합 코멘트
    # ========================================================

    st.markdown(
        "---"
    )


    # 현재 전환 상위 3개
    top_campaigns = (
        valid
        .sort_values(
            "conversion_current",
            ascending=False
        )
        .head(3)
    )


    if not top_campaigns.empty:

        ranking_text = ", ".join(
            [
                (
                    f"{row['campaign']} "
                    f"({row['conversion_current']:,.0f}건)"
                )
                for _, row in top_campaigns.iterrows()
            ]
        )


        st.markdown(
            f"📌 **현재 전환 기여 상위 캠페인:** "
            f"{ranking_text}"
        )


    # 비교 기간 전체 데이터가 없는 경우
    if (
        total_previous_conversion == 0
        and total_previous_spend == 0
    ):

        st.markdown(
            "💡 **비교 기간에는 집행/전환 데이터가 없어 "
            "증감률 비교가 제한됩니다.** "
            "따라서 현재 기간의 CPA와 전환 볼륨을 중심으로 "
            "캠페인별 우선순위를 판단하는 것이 적절합니다."
        )


create_campaign_comments(
    campaign_table
)


# ============================================================
# 21. 데이터 정보
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
        f"기준 기간: "
        f"{current_period_text}"
    )

    st.write(
        f"비교 기간: "
        f"{previous_period_text}"
    )

    st.write(
        f"동일 진행일수: "
        f"{elapsed_days}일"
    )

    st.write(
        f"선택 TYPE: "
        f"{', '.join(selected_types) if selected_types else '없음'}"
    )

    st.write(
        f"선택 매체: "
        f"{len(selected_media)}개"
    )

    st.write(
        f"선택 캠페인: "
        f"{len(selected_campaigns)}개"
    )
