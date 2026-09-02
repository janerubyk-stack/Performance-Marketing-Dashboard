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
# 3. 데이터 로드
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

    # --------------------------------------------------------
    # 컬럼 자동 매칭
    # --------------------------------------------------------

    def find_column(candidates):

        # 정확히 일치
        for candidate in candidates:

            for col in df.columns:

                if str(col).strip().lower() == str(candidate).lower():
                    return col

        # 부분 일치
        for candidate in candidates:

            for col in df.columns:

                if str(candidate).lower() in str(col).strip().lower():
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
        "매체"
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
    # 날짜 없는 행 제거
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

def format_period(start_date, end_date):

    return (
        f"{pd.Timestamp(start_date).strftime('%Y-%m-%d')}"
        f" ~ "
        f"{pd.Timestamp(end_date).strftime('%Y-%m-%d')}"
    )


def safe_change(current, previous):

    if (
        pd.isna(current)
        or pd.isna(previous)
        or previous == 0
    ):
        return np.nan

    return (
        (current - previous)
        / previous
        * 100
    )


def format_change(value):

    if pd.isna(value):
        return "-"

    return f"{value:+,.1f}%"


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


def get_share(value, total):

    if (
        pd.isna(value)
        or total <= 0
    ):
        return np.nan

    return value / total * 100


# ============================================================
# 6. 기간 계산
# ============================================================

def get_periods(base_date, period_type):

    base_date = pd.Timestamp(base_date)


    # --------------------------------------------------------
    # 전일
    # --------------------------------------------------------

    if period_type == "전일":

        current_start = base_date
        current_end = base_date

        previous_start = base_date - timedelta(days=1)
        previous_end = base_date - timedelta(days=1)


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
        ).days

        previous_end = (
            current_end -
            timedelta(days=7)
        )

        previous_start = (
            previous_end -
            timedelta(days=elapsed_days)
        )


    # --------------------------------------------------------
    # 전월
    # --------------------------------------------------------

    elif period_type == "전월":

        current_start = base_date.replace(day=1)
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


    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"] / result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
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
            max_value=base_date,
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

        # 비교 종료일은 시작일 + 기준기간일수 - 1
        calculated_previous_end = (
            pd.Timestamp(custom_previous_start)
            +
            timedelta(
                days=custom_elapsed_days - 1
            )
        ).date()


        custom_previous_end = st.date_input(
            "비교 종료일",
            value=calculated_previous_end,
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_end"
        )


    previous_elapsed_days = (
        pd.Timestamp(custom_previous_end)
        -
        pd.Timestamp(custom_previous_start)
    ).days + 1


    # --------------------------------------------------------
    # 동일 일수 검증
    # --------------------------------------------------------

    if custom_elapsed_days != previous_elapsed_days:

        st.error(
            f"⚠️ 기간 일수가 다릅니다. "
            f"기준 기간 {custom_elapsed_days}일 / "
            f"비교 기간 {previous_elapsed_days}일"
        )

        st.stop()


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
# 기간 표시
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
# 9. 카테고리 / 매체 / 캠페인 필터
# ============================================================

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
# 카테고리
# ============================================================

with filter_col1:

    selected_types = st.multiselect(
        "카테고리",
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
# 10. 전체 선택 버튼
# ============================================================

button_col1, button_col2, button_col3 = st.columns(3)


with button_col1:

    if st.button(
        "📌 카테고리 전체 선택",
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
# 11. 필터 데이터
# ============================================================

filtered_df = df[
    df["type"].isin(selected_types) &
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 12. 현재 / 비교 데이터
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
# 13. 매체별 집계
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
        result["spend"] /
        result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
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
# 14. 비교 데이터 생성
# ============================================================

def create_comparison(
    current,
    previous,
    group_col
):

    groups = sorted(
        set(
            current[group_col].tolist()
            if not current.empty
            else []
        )
        |
        set(
            previous[group_col].tolist()
            if not previous.empty
            else []
        )
    )


    rows = []


    for group in groups:

        c = (
            current[
                current[group_col] == group
            ]
            .iloc[0]
            if not current[
                current[group_col] == group
            ].empty
            else None
        )


        p = (
            previous[
                previous[group_col] == group
            ]
            .iloc[0]
            if not previous[
                previous[group_col] == group
            ].empty
            else None
        )


        c_spend = (
            float(c["spend"])
            if c is not None
            else 0
        )

        p_spend = (
            float(p["spend"])
            if p is not None
            else 0
        )


        c_click = (
            float(c["click"])
            if c is not None
            else 0
        )

        p_click = (
            float(p["click"])
            if p is not None
            else 0
        )


        c_conversion = (
            float(c["conversion"])
            if c is not None
            else 0
        )

        p_conversion = (
            float(p["conversion"])
            if p is not None
            else 0
        )


        c_cpa = (
            c_spend / c_conversion
            if c_conversion > 0
            else np.nan
        )

        p_cpa = (
            p_spend / p_conversion
            if p_conversion > 0
            else np.nan
        )


        c_cvr = (
            c_conversion /
            c_click *
            100
            if c_click > 0
            else np.nan
        )

        p_cvr = (
            p_conversion /
            p_click *
            100
            if p_click > 0
            else np.nan
        )


        rows.append({

            group_col: group,

            "spend_current":
                c_spend,

            "spend_previous":
                p_spend,

            "conversion_current":
                c_conversion,

            "conversion_previous":
                p_conversion,

            "CPA_current":
                c_cpa,

            "CPA_previous":
                p_cpa,

            "CVR_current":
                c_cvr,

            "CVR_previous":
                p_cvr,

            "click_current":
                c_click,

            "click_previous":
                p_click
        })


    result = pd.DataFrame(rows)


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
# 15. 전체 성과 요약
# ============================================================

st.divider()

st.header("📊 전체 성과 요약")


total_current_spend = current_df["spend"].sum()
total_previous_spend = previous_df["spend"].sum()

total_current_conversion = current_df["conversion"].sum()
total_previous_conversion = previous_df["conversion"].sum()

total_current_click = current_df["click"].sum()
total_previous_click = previous_df["click"].sum()


total_current_cpa = (
    total_current_spend /
    total_current_conversion
    if total_current_conversion > 0
    else np.nan
)

total_previous_cpa = (
    total_previous_spend /
    total_previous_conversion
    if total_previous_conversion > 0
    else np.nan
)


total_current_cvr = (
    total_current_conversion /
    total_current_click *
    100
    if total_current_click > 0
    else np.nan
)

total_previous_cvr = (
    total_previous_conversion /
    total_previous_click *
    100
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

    st.metric(
        "광고비",
        format_money(total_current_spend),
        format_change(total_spend_change)
    )


with summary_col2:

    st.metric(
        "전환수",
        format_number(total_current_conversion),
        format_change(total_conversion_change)
    )


with summary_col3:

    st.metric(
        "CPA",
        format_money(total_current_cpa),
        format_change(total_cpa_change),
        delta_color="inverse"
    )


with summary_col4:

    st.metric(
        "CVR",
        format_percent(total_current_cvr),
        format_change(total_cvr_change)
    )


# ============================================================
# 16. 성과 추이
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
        (data["date"] >= pd.Timestamp(start_date)) &
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


    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"] /
        result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
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


def draw_trend_chart(trend_type):

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

        x_values = trend_df["period"].dt.strftime(
            "%m/%d"
        )

    else:

        x_values = trend_df["period"].dt.strftime(
            "%Y-%m"
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
# 17. 성과 비교
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text} | "
    f"비교 기간: {previous_period_text} | "
    f"동일 진행일수: {elapsed_days}일"
)


chart_df = comparison[
    comparison["media"].isin(selected_media)
].copy()


chart_df = chart_df.sort_values(
    "conversion_current",
    ascending=False
)


x_labels = chart_df["media"].tolist()


# ============================================================
# 18. CPA + 전환수
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
# 19. 광고비 + 전환수
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
# 20. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "선택한 카테고리 / 매체 기준으로 현재 기간과 비교 기간의 성과를 확인합니다."
)


media_table = comparison[
    comparison["media"].isin(selected_media)
].copy()


media_table = media_table.sort_values(
    "conversion_current",
    ascending=False
)


if media_table.empty:

    st.info(
        "선택한 조건에 해당하는 매체 성과 데이터가 없습니다."
    )

else:

    # --------------------------------------------------------
    # 이전에 사용하던 형태와 동일하게
    # 지표 = 세로 / 매체 = 가로
    # --------------------------------------------------------

    table_rows = []

    for _, row in media_table.iterrows():

        media_name = row["media"]

        table_rows.append({
            "매체": media_name,
            "광고비": (
                f"기준: {format_money(row['spend_current'])}\n"
                f"비교: {format_money(row['spend_previous'])}\n"
                f"변화: {format_change(row['spend_change'])}"
            ),
            "전환수": (
                f"기준: {format_number(row['conversion_current'])}\n"
                f"비교: {format_number(row['conversion_previous'])}\n"
                f"변화: {format_change(row['conversion_change'])}"
            ),
            "CPA": (
                f"기준: {format_money(row['CPA_current'])}\n"
                f"비교: {format_money(row['CPA_previous'])}\n"
                f"변화: {format_change(row['CPA_change'])}"
            ),
            "CVR": (
                f"기준: {format_percent(row['CVR_current'])}\n"
                f"비교: {format_percent(row['CVR_previous'])}\n"
                f"변화: {format_change(row['CVR_change'])}"
            )
        })


    media_display = pd.DataFrame(
        table_rows
    ).set_index("매체").T


    st.dataframe(
        media_display,
        use_container_width=True,
        height=260
    )


# ============================================================
# 21. 매체별 성과 코멘트
# ============================================================

st.subheader("📝 매체별 성과 코멘트")


if media_table.empty:

    st.info(
        "선택한 매체의 성과 데이터가 없습니다."
    )

else:

    total_media_conversion = media_table[
        "conversion_current"
    ].sum()


    # --------------------------------------------------------
    # 전체 매체 중 전환 최다
    # --------------------------------------------------------

    valid_media = media_table[
        media_table["conversion_current"] > 0
    ].copy()


    if not valid_media.empty:

        best_media = valid_media.loc[
            valid_media["conversion_current"].idxmax()
        ]


        best_media_share = get_share(
            best_media["conversion_current"],
            total_media_conversion
        )


        share_text = (
            f"전체 전환의 {best_media_share:.1f}%"
            if pd.notna(best_media_share)
            else "전체 전환 비중 확인 불가"
        )


        st.markdown(
            f"🏆 **전환수 최다 매체:** "
            f"`{best_media['media']}` — "
            f"전환 **{best_media['conversion_current']:,.0f}건**, "
            f"CPA **{best_media['CPA_current']:,.0f}원** "
            f"(**{share_text}**)"
        )


        # ----------------------------------------------------
        # CPA 최우수 매체
        # ----------------------------------------------------

        valid_cpa_media = valid_media[
            valid_media["CPA_current"].notna() &
            (valid_media["CPA_current"] > 0)
        ]


        if not valid_cpa_media.empty:

            best_cpa_media = valid_cpa_media.loc[
                valid_cpa_media["CPA_current"].idxmin()
            ]


            best_cpa_share = get_share(
                best_cpa_media["conversion_current"],
                total_media_conversion
            )


            share_text = (
                f"전체 전환의 {best_cpa_share:.1f}%"
                if pd.notna(best_cpa_share)
                else "전체 전환 비중 확인 불가"
            )


            st.markdown(
                f"💰 **CPA 최우수 매체:** "
                f"`{best_cpa_media['media']}` — "
                f"CPA **{best_cpa_media['CPA_current']:,.0f}원**, "
                f"전환 **{best_cpa_media['conversion_current']:,.0f}건** "
                f"(**{share_text}**)"
            )


    # --------------------------------------------------------
    # 매체별 상세 분석
    # --------------------------------------------------------

    for _, row in media_table.iterrows():

        media_name = row["media"]

        current_spend = row["spend_current"]
        previous_spend = row["spend_previous"]

        current_conversion = row["conversion_current"]
        previous_conversion = row["conversion_previous"]

        current_cpa = row["CPA_current"]
        previous_cpa = row["CPA_previous"]

        current_cvr = row["CVR_current"]
        previous_cvr = row["CVR_previous"]


        spend_change = row["spend_change"]
        conversion_change = row["conversion_change"]
        cpa_change = row["CPA_change"]
        cvr_change = row["CVR_change"]


        # 비교 데이터가 아예 없는 경우
        if (
            previous_spend == 0 and
            previous_conversion == 0
        ):

            st.markdown(
                f"🆕 **`{media_name}`** — "
                f"현재 광고비 **{current_spend:,.0f}원**, "
                f"전환 **{current_conversion:,.0f}건**, "
                f"CPA **{format_money(current_cpa)}**, "
                f"CVR **{format_percent(current_cvr)}**로 "
                f"신규 집행 또는 비교 기간 데이터가 없는 매체입니다."
            )

            continue


        sentences = []


        # 전환
        if pd.notna(conversion_change):

            if conversion_change > 10:

                sentences.append(
                    f"전환은 **{conversion_change:+.1f}% 증가**했습니다."
                )

            elif conversion_change < -10:

                sentences.append(
                    f"전환은 **{conversion_change:+.1f}% 감소**했습니다."
                )

            else:

                sentences.append(
                    f"전환은 **{conversion_change:+.1f}%**로 큰 변동이 없습니다."
                )


        # CPA
        if pd.notna(cpa_change):

            if cpa_change < -10:

                sentences.append(
                    f"CPA는 **{cpa_change:+.1f}% 개선**되어 효율이 좋아졌습니다."
                )

            elif cpa_change > 10:

                sentences.append(
                    f"CPA는 **{cpa_change:+.1f}% 상승**해 효율 악화 여부를 확인할 필요가 있습니다."
                )

            else:

                sentences.append(
                    f"CPA는 **{cpa_change:+.1f}%**로 비교적 안정적입니다."
                )


        # CVR
        if pd.notna(cvr_change):

            if cvr_change > 10:

                sentences.append(
                    f"CVR은 **{cvr_change:+.1f}% 개선**되었습니다."
                )

            elif cvr_change < -10:

                sentences.append(
                    f"CVR은 **{cvr_change:+.1f}% 하락**해 클릭 이후 전환 구간 점검이 필요합니다."
                )


        # 광고비
        if pd.notna(spend_change):

            if spend_change > 10:

                sentences.append(
                    f"광고비는 **{spend_change:+.1f}% 증가**했습니다."
                )

            elif spend_change < -10:

                sentences.append(
                    f"광고비는 **{spend_change:+.1f}% 감소**했습니다."
                )


        st.markdown(
            f"🔎 **`{media_name}`** — "
            +
            " ".join(sentences)
        )


# ============================================================
# 22. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 카테고리 / 매체 / 캠페인 조건 안에서 캠페인별 성과를 비교합니다."
)


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
        result["spend"] /
        result["conversion"],
        np.nan
    )


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
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

    campaign_rows = []

    for _, row in campaign_table.iterrows():

        campaign_name = row["campaign"]

        campaign_rows.append({
            "캠페인": campaign_name,
            "광고비": (
                f"기준: {format_money(row['spend_current'])}\n"
                f"비교: {format_money(row['spend_previous'])}\n"
                f"변화: {format_change(row['spend_change'])}"
            ),
            "전환수": (
                f"기준: {format_number(row['conversion_current'])}\n"
                f"비교: {format_number(row['conversion_previous'])}\n"
                f"변화: {format_change(row['conversion_change'])}"
            ),
            "CPA": (
                f"기준: {format_money(row['CPA_current'])}\n"
                f"비교: {format_money(row['CPA_previous'])}\n"
                f"변화: {format_change(row['CPA_change'])}"
            ),
            "CVR": (
                f"기준: {format_percent(row['CVR_current'])}\n"
                f"비교: {format_percent(row['CVR_previous'])}\n"
                f"변화: {format_change(row['CVR_change'])}"
            )
        })


    campaign_display = pd.DataFrame(
        campaign_rows
    ).set_index("캠페인").T


    # 캠페인이 많아도 표가 깨지지 않도록 높이 조정
    table_height = min(
        700,
        max(
            280,
            len(campaign_display.index) * 70
        )
    )


    st.dataframe(
        campaign_display,
        use_container_width=True,
        height=table_height
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


    if valid_campaigns.empty:

        st.info(
            "현재 기간에 전환이 발생한 캠페인이 없습니다."
        )

    else:

        total_campaign_conversion = valid_campaigns[
            "conversion_current"
        ].sum()


        # ====================================================
        # CPA 최우수
        # ====================================================

        cpa_valid = valid_campaigns[
            valid_campaigns["CPA_current"].notna() &
            (valid_campaigns["CPA_current"] > 0)
        ]


        if not cpa_valid.empty:

            best = cpa_valid.loc[
                cpa_valid["CPA_current"].idxmin()
            ]


            best_share = get_share(
                best["conversion_current"],
                total_campaign_conversion
            )


            share_text = (
                f"전체 전환의 {best_share:.1f}%"
                if pd.notna(best_share)
                else "전체 전환 비중 확인 불가"
            )


            st.markdown(
                f"🏆 **CPA 최우수 캠페인:** "
                f"`{best['campaign']}` — "
                f"CPA **{best['CPA_current']:,.0f}원**, "
                f"전환 **{best['conversion_current']:,.0f}건** "
                f"(**{share_text}**)"
            )


        # ====================================================
        # 전환수 최다
        # ====================================================

        best_conversion = valid_campaigns.loc[
            valid_campaigns[
                "conversion_current"
            ].idxmax()
        ]


        conversion_share = get_share(
            best_conversion["conversion_current"],
            total_campaign_conversion
        )


        share_text = (
            f"전체 전환의 {conversion_share:.1f}%"
            if pd.notna(conversion_share)
            else "전체 전환 비중 확인 불가"
        )


        cpa_text = (
            f"{best_conversion['CPA_current']:,.0f}원"
            if pd.notna(best_conversion["CPA_current"])
            else "-"
        )


        st.markdown(
            f"📈 **전환수 최다 캠페인:** "
            f"`{best_conversion['campaign']}` — "
            f"전환 **{best_conversion['conversion_current']:,.0f}건**, "
            f"CPA **{cpa_text}** "
            f"(**{share_text}**)"
        )


        # ====================================================
        # 전환 증가폭 최대
        # ====================================================

        growth = campaign_table[
            campaign_table["conversion_change"].notna()
        ].copy()


        if not growth.empty:

            growth_best = growth.loc[
                growth["conversion_change"].idxmax()
            ]


            if growth_best["conversion_change"] > 0:

                st.markdown(
                    f"🚀 **전환 증가폭 최대 캠페인:** "
                    f"`{growth_best['campaign']}` — "
                    f"전환 **{growth_best['conversion_change']:+,.1f}%** "
                    f"증가 "
                    f"(기준 **{growth_best['conversion_current']:,.0f}건**)"
                )


        # ====================================================
        # CPA 개선 최대
        # ====================================================

        cpa_improve = campaign_table[
            campaign_table["CPA_change"].notna() &
            (campaign_table["CPA_change"] < 0)
        ].copy()


        if not cpa_improve.empty:

            cpa_best = cpa_improve.loc[
                cpa_improve["CPA_change"].idxmin()
            ]


            st.markdown(
                f"💰 **CPA 개선폭 최대 캠페인:** "
                f"`{cpa_best['campaign']}` — "
                f"CPA **{cpa_best['CPA_change']:+,.1f}%** "
                f"개선 "
                f"(현재 **{cpa_best['CPA_current']:,.0f}원**)"
            )


        # ====================================================
        # CPA 악화
        # ====================================================

        cpa_worst_df = campaign_table[
            campaign_table["CPA_change"].notna() &
            (campaign_table["CPA_change"] > 0)
        ].copy()


        if not cpa_worst_df.empty:

            worst = cpa_worst_df.loc[
                cpa_worst_df["CPA_change"].idxmax()
            ]


            st.markdown(
                f"⚠️ **CPA 악화 주의 캠페인:** "
                f"`{worst['campaign']}` — "
                f"CPA **{worst['CPA_change']:+,.1f}%** 상승 "
                f"(현재 **{worst['CPA_current']:,.0f}원**, "
                f"전환 **{worst['conversion_current']:,.0f}건**)"
            )


        # ====================================================
        # CVR 개선
        # ====================================================

        cvr_best_df = campaign_table[
            campaign_table["CVR_change"].notna()
        ].copy()


        if not cvr_best_df.empty:

            best_cvr = cvr_best_df.loc[
                cvr_best_df["CVR_change"].idxmax()
            ]


            if best_cvr["CVR_change"] > 10:

                st.markdown(
                    f"📈 **CVR 개선폭 최대 캠페인:** "
                    f"`{best_cvr['campaign']}` — "
                    f"CVR **{best_cvr['CVR_change']:+,.1f}%** 개선 "
                    f"(현재 **{best_cvr['CVR_current']:.2f}%**)"
                )


        # ====================================================
        # CVR 악화
        # ====================================================

        cvr_worst_df = campaign_table[
            campaign_table["CVR_change"].notna()
        ].copy()


        if not cvr_worst_df.empty:

            worst_cvr = cvr_worst_df.loc[
                cvr_worst_df["CVR_change"].idxmin()
            ]


            if worst_cvr["CVR_change"] < -10:

                st.markdown(
                    f"⚠️ **CVR 하락 주의 캠페인:** "
                    f"`{worst_cvr['campaign']}` — "
                    f"CVR **{worst_cvr['CVR_change']:+,.1f}%** 하락 "
                    f"(현재 **{worst_cvr['CVR_current']:.2f}%**)"
                )


        # ====================================================
        # 캠페인별 상세 코멘트
        # ====================================================

        st.markdown("#### 🔎 캠페인별 상세 분석")


        for _, row in campaign_table.iterrows():

            campaign_name = row["campaign"]

            current_conversion = row[
                "conversion_current"
            ]

            previous_conversion = row[
                "conversion_previous"
            ]

            current_cpa = row[
                "CPA_current"
            ]

            current_cvr = row[
                "CVR_current"
            ]

            conversion_change = row[
                "conversion_change"
            ]

            cpa_change = row[
                "CPA_change"
            ]

            cvr_change = row[
                "CVR_change"
            ]

            spend_change = row[
                "spend_change"
            ]


            # ------------------------------------------------
            # 신규
            # ------------------------------------------------

            if (
                previous_conversion == 0 and
                row["spend_previous"] == 0
            ):

                st.markdown(
                    f"🆕 **`{campaign_name}`** — "
                    f"현재 광고비 **{row['spend_current']:,.0f}원**, "
                    f"전환 **{current_conversion:,.0f}건**, "
                    f"CPA **{format_money(current_cpa)}**, "
                    f"CVR **{format_percent(current_cvr)}**입니다. "
                    f"비교 기간 데이터가 없어 증감률보다는 현재 효율과 "
                    f"전환 규모를 기준으로 판단하는 것이 적절합니다."
                )

                continue


            sentences = []


            # 전환
            if pd.notna(conversion_change):

                if conversion_change > 10:

                    sentences.append(
                        f"전환은 **{conversion_change:+.1f}% 증가**했습니다."
                    )

                elif conversion_change < -10:

                    sentences.append(
                        f"전환은 **{conversion_change:+.1f}% 감소**했습니다."
                    )

                else:

                    sentences.append(
                        f"전환은 **{conversion_change:+.1f}%**로 큰 변동이 없습니다."
                    )


            # CPA
            if pd.notna(cpa_change):

                if cpa_change < -10:

                    sentences.append(
                        f"CPA는 **{cpa_change:+.1f}% 개선**되었습니다."
                    )

                elif cpa_change > 10:

                    sentences.append(
                        f"CPA는 **{cpa_change:+.1f}% 상승**해 효율 악화가 나타났습니다."
                    )

                else:

                    sentences.append(
                        f"CPA는 **{cpa_change:+.1f}%**로 안정적인 수준입니다."
                    )


            # CVR
            if pd.notna(cvr_change):

                if cvr_change > 10:

                    sentences.append(
                        f"CVR은 **{cvr_change:+.1f}% 개선**되었습니다."
                    )

                elif cvr_change < -10:

                    sentences.append(
                        f"CVR은 **{cvr_change:+.1f}% 하락**했습니다."
                    )


            # 광고비
            if pd.notna(spend_change):

                if spend_change > 20:

                    sentences.append(
                        f"광고비도 **{spend_change:+.1f}% 증가**해 "
                        f"예산 확대가 전환 변화에 미친 영향을 함께 볼 필요가 있습니다."
                    )

                elif spend_change < -20:

                    sentences.append(
                        f"광고비는 **{spend_change:+.1f}% 감소**했습니다."
                    )


            # 최종
            st.markdown(
                f"• **`{campaign_name}`** — "
                +
                " ".join(sentences)
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
        f"선택 카테고리: "
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
