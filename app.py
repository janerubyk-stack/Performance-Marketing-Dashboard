import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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

    # --------------------------------------------------------
    # 컬럼 자동 매칭
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
    # 내부 컬럼명 통일
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
            .str.strip()
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)


    # --------------------------------------------------------
    # 문자 처리
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

    이전값이 0이면 억지로 %를 만들지 않는다.
    """

    if pd.isna(current):
        return np.nan

    if pd.isna(previous):
        return np.nan

    if previous == 0:
        return np.nan

    return (
        (current - previous)
        / previous
        * 100
    )


def format_number(value, suffix=""):

    if pd.isna(value):
        return "-"

    return f"{value:,.0f}{suffix}"


def format_percent(value):

    if pd.isna(value):
        return "-"

    return f"{value:,.2f}%"


def format_change(value):

    if pd.isna(value):
        return "-"

    if value > 0:
        return f"▲ +{value:,.1f}%"

    if value < 0:
        return f"▼ {value:,.1f}%"

    return "─ 0.0%"


def change_class(value):

    if pd.isna(value):
        return "neutral"

    if value > 0:
        return "up"

    if value < 0:
        return "down"

    return "neutral"


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


def format_period(
    start_date,
    end_date
):

    return (
        f"{start_date.strftime('%Y-%m-%d')}"
        f" ~ "
        f"{end_date.strftime('%Y-%m-%d')}"
    )


# ============================================================
# 7. 분석 조건
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
    [1, 1.8, 2]
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
# 8. 기간 설정
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
            f"**기준 기간: {custom_elapsed_days}일**"
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

        custom_previous_end = st.date_input(
            "비교 종료일",
            value=(
                pd.Timestamp(custom_previous_start)
                +
                timedelta(days=custom_elapsed_days - 1)
            ).date(),
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
    # 날짜 역전 체크
    # --------------------------------------------------------

    if custom_current_start > custom_current_end:

        st.error(
            "기준 시작일은 기준 종료일보다 빠르거나 같아야 합니다."
        )

        st.stop()


    if custom_previous_start > custom_previous_end:

        st.error(
            "비교 시작일은 비교 종료일보다 빠르거나 같아야 합니다."
        )

        st.stop()


    # --------------------------------------------------------
    # 동일 일수 체크
    # --------------------------------------------------------

    if custom_elapsed_days != previous_elapsed_days:

        st.error(
            f"⚠️ 기준 기간은 {custom_elapsed_days}일, "
            f"비교 기간은 {previous_elapsed_days}일입니다. "
            f"두 기간의 일수를 동일하게 설정해주세요."
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
# 9. 필터
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


with filter_col1:

    selected_types = st.multiselect(
        "TYPE",
        options=type_options,
        default=type_options,
        key="type_filter"
    )


with filter_col2:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_options,
        default=media_options,
        key="media_filter"
    )


with filter_col3:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=campaign_options,
        default=campaign_options,
        key="campaign_filter"
    )


# ============================================================
# 10. 전체 선택
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
# 11. 필터 적용
# ============================================================

filtered_df = df[
    df["type"].isin(selected_types)
    &
    df["media"].isin(selected_media)
    &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 12. 기간별 집계
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
            "media",
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

    current = current.copy()
    previous = previous.copy()


    # --------------------------------------------------------
    # 빈 데이터 처리
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 인덱스
    # --------------------------------------------------------

    current = current.set_index(group_col)
    previous = previous.set_index(group_col)


    groups = sorted(
        set(current.index)
        |
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


        c_conversion = float(
            c.get("conversion", 0)
        )

        p_conversion = float(
            p.get("conversion", 0)
        )


        c_click = float(
            c.get("click", 0)
        )

        p_click = float(
            p.get("click", 0)
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

            "click_current":
                c_click,

            "click_previous":
                p_click,

            "CPA_current":
                c_cpa,

            "CPA_previous":
                p_cpa,

            "CVR_current":
                c_cvr,

            "CVR_previous":
                p_cvr
        })


    result = pd.DataFrame(rows)


    if result.empty:
        return result


    # --------------------------------------------------------
    # 변화율
    # --------------------------------------------------------

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
        format_number(
            total_current_spend,
            "원"
        ),
        format_change(
            total_spend_change
        )
    )


with summary_col2:

    st.metric(
        "전환수",
        format_number(
            total_current_conversion,
            "건"
        ),
        format_change(
            total_conversion_change
        )
    )


with summary_col3:

    st.metric(
        "CPA",
        format_number(
            total_current_cpa,
            "원"
        ),
        format_change(
            total_cpa_change
        ),
        delta_color="inverse"
    )


with summary_col4:

    st.metric(
        "CVR",
        format_percent(
            total_current_cvr
        ),
        format_change(
            total_cvr_change
        )
    )


# ============================================================
# 16. 성과 추이
# ============================================================

st.divider()

st.header("📈 성과 추이")

st.caption(
    f"현재 설정한 분석 기간 {current_period_text} 내 데이터만 표시합니다."
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
            "선택한 기간에 데이터가 없습니다."
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


    # CPA = 막대
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


    # 전환수 = 꺾은선
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


# ------------------------------------------------------------
# CPA + 전환수
# ------------------------------------------------------------

if chart_df.empty:

    st.info(
        "선택한 조건의 비교 데이터가 없습니다."
    )

else:

    x_labels = chart_df["media"].tolist()

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


# ============================================================
# 18. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "선택한 TYPE / 매체 기준으로 현재 기간과 비교 기간의 성과를 확인합니다."
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


# ------------------------------------------------------------
# HTML 테이블 함수
# ------------------------------------------------------------

def render_comparison_table(
    table_df,
    name_col
):

    if table_df.empty:

        st.info(
            "선택한 조건에서 표시할 성과 데이터가 없습니다."
        )

        return


    table_html = """
    <style>

    .performance-table {

        width: 100%;
        border-collapse: collapse;
        font-size: 13px;

    }

    .performance-table th,
    .performance-table td {

        border: 1px solid #dddddd;
        padding: 10px;
        text-align: center;
        white-space: nowrap;

    }

    .performance-table th {

        background-color: #f5f5f5;
        font-weight: 700;

    }

    .performance-table td.metric {

        text-align: left;
        font-weight: 700;
        background-color: #fafafa;

    }

    .up {

        color: #d62728;
        font-weight: 700;

    }

    .down {

        color: #2468c7;
        font-weight: 700;

    }

    .neutral {

        color: #666666;
        font-weight: 700;

    }

    </style>

    <table class="performance-table">

    <tr>

    <th>지표</th>
    """


    for name in table_df[name_col]:

        table_html += (
            f"<th>{html.escape(str(name))}</th>"
        )


    table_html += "</tr>"


    metric_rows = [

        (
            "광고비",
            "spend_current",
            "spend_previous",
            "spend_change",
            "money"
        ),

        (
            "전환수",
            "conversion_current",
            "conversion_previous",
            "conversion_change",
            "number"
        ),

        (
            "CPA",
            "CPA_current",
            "CPA_previous",
            "CPA_change",
            "cpa"
        ),

        (
            "CVR",
            "CVR_current",
            "CVR_previous",
            "CVR_change",
            "percent"
        )

    ]


    for (
        metric_name,
        current_col,
        previous_col,
        change_col,
        fmt_type
    ) in metric_rows:

        table_html += f"""
        <tr>
        <td class="metric">
        {metric_name}
        </td>
        """


        for _, row in table_df.iterrows():

            current_value = row[current_col]
            previous_value = row[previous_col]
            change_value = row[change_col]


            # ------------------------------------------------
            # 숫자 포맷
            # ------------------------------------------------

            if fmt_type in [
                "money",
                "cpa"
            ]:

                current_text = (
                    f"{current_value:,.0f}원"
                    if pd.notna(current_value)
                    else "-"
                )

                previous_text = (
                    f"{previous_value:,.0f}원"
                    if pd.notna(previous_value)
                    else "-"
                )


            elif fmt_type == "number":

                current_text = (
                    f"{current_value:,.0f}건"
                    if pd.notna(current_value)
                    else "-"
                )

                previous_text = (
                    f"{previous_value:,.0f}건"
                    if pd.notna(previous_value)
                    else "-"
                )


            else:

                current_text = (
                    f"{current_value:,.2f}%"
                    if pd.notna(current_value)
                    else "-"
                )

                previous_text = (
                    f"{previous_value:,.2f}%"
                    if pd.notna(previous_value)
                    else "-"
                )


            # ------------------------------------------------
            # 변화율 표시
            # ------------------------------------------------

            if pd.isna(change_value):

                if (
                    pd.notna(previous_value)
                    and previous_value == 0
                    and pd.notna(current_value)
                    and current_value != 0
                ):

                    change_html = (
                        '<span class="neutral">'
                        '비교 0 → 신규'
                        '</span>'
                    )

                else:

                    change_html = (
                        '<span class="neutral">'
                        '-'
                        '</span>'
                    )

            else:

                css_class = change_class(
                    change_value
                )

                change_html = (
                    f'<span class="{css_class}">'
                    f'{format_change(change_value)}'
                    f'</span>'
                )


            table_html += f"""

            <td>

            <div>
            기준: <b>{current_text}</b>
            </div>

            <div style="color:#888;">
            비교: {previous_text}
            </div>

            <div style="margin-top:4px;">
            {change_html}
            </div>

            </td>

            """


        table_html += "</tr>"


    table_html += """

    </table>
    """


    st.markdown(
        table_html,
        unsafe_allow_html=True
    )


render_comparison_table(
    media_table,
    "media"
)


# ============================================================
# 19. 매체별 성과 코멘트
# ============================================================

st.subheader("📝 매체별 성과 코멘트")


if media_table.empty:

    st.info(
        "선택한 매체의 성과 데이터가 없습니다."
    )

else:

    # --------------------------------------------------------
    # 매체별 개별 분석
    # --------------------------------------------------------

    for _, row in media_table.iterrows():

        media_name = row["media"]

        current_conversion = row[
            "conversion_current"
        ]

        previous_conversion = row[
            "conversion_previous"
        ]

        current_cpa = row[
            "CPA_current"
        ]

        previous_cpa = row[
            "CPA_previous"
        ]

        current_cvr = row[
            "CVR_current"
        ]

        previous_cvr = row[
            "CVR_previous"
        ]

        spend_change = row[
            "spend_change"
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


        # ----------------------------------------------------
        # 기본 문장
        # ----------------------------------------------------

        comments = []


        # ----------------------------------------------------
        # 전환
        # ----------------------------------------------------

        if pd.isna(conversion_change):

            if (
                previous_conversion == 0
                and current_conversion > 0
            ):

                comments.append(
                    f"비교 기간에는 전환이 없었으나 "
                    f"현재 기간에는 {current_conversion:,.0f}건이 발생했습니다."
                )

        elif conversion_change > 10:

            comments.append(
                f"전환수는 "
                f"{conversion_change:+.1f}% 증가하여 "
                f"볼륨이 개선되었습니다."
            )

        elif conversion_change < -10:

            comments.append(
                f"전환수는 "
                f"{conversion_change:+.1f}% 감소하여 "
                f"볼륨 감소 여부를 확인할 필요가 있습니다."
            )

        else:

            comments.append(
                f"전환수는 "
                f"{conversion_change:+.1f}%로 "
                f"큰 변동 없이 유지되었습니다."
            )


        # ----------------------------------------------------
        # CPA
        # ----------------------------------------------------

        if pd.notna(cpa_change):

            if cpa_change < -10:

                comments.append(
                    f"CPA는 "
                    f"{cpa_change:+.1f}% 개선되어 "
                    f"전환 효율이 좋아졌습니다."
                )

            elif cpa_change > 10:

                comments.append(
                    f"CPA는 "
                    f"{cpa_change:+.1f}% 상승하여 "
                    f"효율 악화가 나타났습니다."
                )

            else:

                comments.append(
                    f"CPA는 "
                    f"{cpa_change:+.1f}%로 "
                    f"큰 변화가 없습니다."
                )

        elif (
            previous_cpa != previous_cpa
            and pd.notna(current_cpa)
        ):

            comments.append(
                "비교 기간에 전환이 없어 CPA 비교는 어렵습니다."
            )


        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

        if pd.notna(cvr_change):

            if cvr_change > 10:

                comments.append(
                    f"CVR도 "
                    f"{cvr_change:+.1f}% 개선되어 "
                    f"유입 이후 전환 효율이 좋아졌습니다."
                )

            elif cvr_change < -10:

                comments.append(
                    f"CVR은 "
                    f"{cvr_change:+.1f}% 하락하여 "
                    f"랜딩페이지·타겟·소재 측면을 점검할 필요가 있습니다."
                )


        # ----------------------------------------------------
        # 광고비
        # ----------------------------------------------------

        if pd.notna(spend_change):

            if spend_change > 20:

                comments.append(
                    f"광고비는 "
                    f"{spend_change:+.1f}% 증가했습니다."
                )

            elif spend_change < -20:

                comments.append(
                    f"광고비는 "
                    f"{spend_change:+.1f}% 감소했습니다."
                )


        # ----------------------------------------------------
        # 종합 판단
        # ----------------------------------------------------

        if (
            pd.notna(conversion_change)
            and pd.notna(cpa_change)
            and conversion_change > 10
            and cpa_change < -10
        ):

            conclusion = (
                "➡️ **전환 볼륨과 효율이 동시에 개선된 매체로, "
                "예산 확대 후보로 검토할 수 있습니다.**"
            )

        elif (
            pd.notna(conversion_change)
            and pd.notna(cpa_change)
            and conversion_change < -10
            and cpa_change > 10
        ):

            conclusion = (
                "➡️ **전환 감소와 CPA 상승이 동시에 나타나고 있어 "
                "예산·캠페인·소재별 원인 분석이 우선입니다.**"
            )

        elif (
            pd.notna(conversion_change)
            and conversion_change > 10
            and (
                pd.isna(cpa_change)
                or cpa_change <= 10
            )
        ):

            conclusion = (
                "➡️ **볼륨 측면에서 긍정적인 흐름입니다. "
                "증가한 전환이 실제 유효 DB 품질까지 이어지는지 확인하는 것이 좋습니다.**"
            )

        elif (
            pd.notna(cpa_change)
            and cpa_change < -10
        ):

            conclusion = (
                "➡️ **효율이 개선되고 있으므로 "
                "현재 효율을 유지하면서 추가 볼륨 확보 가능성을 검토할 수 있습니다.**"
            )

        else:

            conclusion = (
                "➡️ **현재 성과 흐름을 유지하면서 "
                "캠페인·소재·타겟 단위의 세부 성과를 추가 확인하는 것이 좋습니다.**"
            )


        st.markdown(
            f"""
### 📌 {media_name}

- 현재 전환: **{current_conversion:,.0f}건**
- 비교 전환: **{previous_conversion:,.0f}건**
- 현재 CPA: **{format_number(current_cpa, "원")}**
- 비교 CPA: **{format_number(previous_cpa, "원")}**
- 현재 CVR: **{format_percent(current_cvr)}**
- 비교 CVR: **{format_percent(previous_cvr)}**

{" ".join(comments)}

{conclusion}
"""
        )


# ============================================================
# 20. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 TYPE / 매체 / 캠페인 조건 안에서 캠페인별 상세 성과를 비교합니다."
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


render_comparison_table(
    campaign_table,
    "campaign"
)


# ============================================================
# 21. 캠페인 성과 코멘트
# ============================================================

st.subheader("📝 캠페인 성과 코멘트")


if campaign_table.empty:

    st.info(
        "선택한 캠페인의 성과 데이터가 없습니다."
    )

else:

    # --------------------------------------------------------
    # 현재 전환 캠페인
    # --------------------------------------------------------

    valid_campaigns = campaign_table[
        campaign_table["conversion_current"] > 0
    ].copy()


    if valid_campaigns.empty:

        st.info(
            "현재 기간에 전환이 발생한 캠페인이 없습니다."
        )

    else:

        # ====================================================
        # 1. CPA 최우수
        # ====================================================

        cpa_valid = valid_campaigns[
            valid_campaigns["CPA_current"].notna()
            &
            (valid_campaigns["CPA_current"] > 0)
        ].copy()


        if not cpa_valid.empty:

            best = cpa_valid.loc[
                cpa_valid["CPA_current"].idxmin()
            ]


            st.markdown(
                f"""
🏆 **CPA 최우수 캠페인:**  
`{best['campaign']}` — CPA **{best['CPA_current']:,.0f}원** / 전환 **{best['conversion_current']:,.0f}건**

현재 기간에 실제 전환이 발생한 캠페인 중 CPA가 가장 낮습니다.
"""
            )


        # ====================================================
        # 2. 전환수 최다
        # ====================================================

        best_conversion = valid_campaigns.loc[
            valid_campaigns[
                "conversion_current"
            ].idxmax()
        ]


        best_conversion_cpa = (
            format_number(
                best_conversion["CPA_current"],
                "원"
            )
        )


        st.markdown(
            f"""
📈 **전환수 최다 캠페인:**  
`{best_conversion['campaign']}` — 전환 **{best_conversion['conversion_current']:,.0f}건** / CPA **{best_conversion_cpa}**

단순히 CPA가 낮은 캠페인뿐 아니라 실제 전환 볼륨을 가장 많이 만들어낸 캠페인입니다.
"""
        )


        # ====================================================
        # 3. 전환 증가폭
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
                    f"""
🚀 **전환 증가폭 최대:**  
`{growth_best['campaign']}` — 전환 **{growth_best['conversion_change']:+,.1f}%**

비교 기간 대비 전환 볼륨이 가장 크게 증가한 캠페인입니다.
"""
                )


        # ====================================================
        # 4. CPA 개선
        # ====================================================

        cpa_improved = campaign_table[
            campaign_table["CPA_change"].notna()
            &
            (campaign_table["CPA_change"] < 0)
        ].copy()


        if not cpa_improved.empty:

            cpa_best = cpa_improved.loc[
                cpa_improved["CPA_change"].idxmin()
            ]


            st.markdown(
                f"""
✅ **CPA 개선폭 최대:**  
`{cpa_best['campaign']}` — CPA **{cpa_best['CPA_change']:+,.1f}%**

비교 기간보다 전환 확보 비용이 가장 크게 개선된 캠페인입니다.
"""
            )


        # ====================================================
        # 5. CPA 악화
        # ====================================================

        cpa_worse = campaign_table[
            campaign_table["CPA_change"].notna()
            &
            (campaign_table["CPA_change"] > 0)
        ].copy()


        if not cpa_worse.empty:

            worst = cpa_worse.loc[
                cpa_worse["CPA_change"].idxmax()
            ]


            st.markdown(
                f"""
⚠️ **CPA 악화 주의:**  
`{worst['campaign']}` — CPA **{worst['CPA_change']:+,.1f}%**

전환 효율이 악화된 캠페인으로, 광고비 증가·클릭 품질·랜딩페이지·타겟 변화 등을 점검할 필요가 있습니다.
"""
            )


        # ====================================================
        # 6. CVR 개선
        # ====================================================

        cvr_improved = campaign_table[
            campaign_table["CVR_change"].notna()
            &
            (campaign_table["CVR_change"] > 0)
        ].copy()


        if not cvr_improved.empty:

            best_cvr = cvr_improved.loc[
                cvr_improved["CVR_change"].idxmax()
            ]


            st.markdown(
                f"""
📈 **CVR 개선폭 최대:**  
`{best_cvr['campaign']}` — CVR **{best_cvr['CVR_change']:+,.1f}%**

클릭 이후 전환 효율이 가장 크게 개선된 캠페인입니다.
"""
            )


        # ====================================================
        # 7. 캠페인별 상세 코멘트
        # ====================================================

        st.markdown("### 🔎 캠페인별 상세 분석")


        for _, row in campaign_table.iterrows():

            campaign_name = row[
                "campaign"
            ]

            current_conversion = row[
                "conversion_current"
            ]

            previous_conversion = row[
                "conversion_previous"
            ]

            current_cpa = row[
                "CPA_current"
            ]

            previous_cpa = row[
                "CPA_previous"
            ]

            current_cvr = row[
                "CVR_current"
            ]

            previous_cvr = row[
                "CVR_previous"
            ]

            spend_change = row[
                "spend_change"
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


            campaign_comments = []


            # ------------------------------------------------
            # 전환 분석
            # ------------------------------------------------

            if (
                previous_conversion == 0
                and current_conversion > 0
            ):

                campaign_comments.append(
                    "비교 기간에는 전환이 없었으나 현재 기간에 신규 전환이 발생했습니다."
                )

            elif (
                pd.notna(conversion_change)
                and conversion_change > 10
            ):

                campaign_comments.append(
                    f"전환수가 {conversion_change:+.1f}% 증가했습니다."
                )

            elif (
                pd.notna(conversion_change)
                and conversion_change < -10
            ):

                campaign_comments.append(
                    f"전환수가 {conversion_change:+.1f}% 감소했습니다."
                )


            # ------------------------------------------------
            # CPA 분석
            # ------------------------------------------------

            if pd.notna(cpa_change):

                if cpa_change < -10:

                    campaign_comments.append(
                        f"CPA는 {cpa_change:+.1f}% 개선되어 효율이 좋아졌습니다."
                    )

                elif cpa_change > 10:

                    campaign_comments.append(
                        f"CPA는 {cpa_change:+.1f}% 상승하여 효율이 악화되었습니다."
                    )


            elif (
                previous_conversion == 0
                and current_conversion > 0
            ):

                campaign_comments.append(
                    "비교 기간에 전환이 없어 CPA 증감률 비교는 어렵습니다."
                )


            # ------------------------------------------------
            # CVR 분석
            # ------------------------------------------------

            if pd.notna(cvr_change):

                if cvr_change > 10:

                    campaign_comments.append(
                        f"CVR은 {cvr_change:+.1f}% 개선되었습니다."
                    )

                elif cvr_change < -10:

                    campaign_comments.append(
                        f"CVR은 {cvr_change:+.1f}% 하락했습니다."
                    )


            # ------------------------------------------------
            # 광고비
            # ------------------------------------------------

            if pd.notna(spend_change):

                if spend_change > 20:

                    campaign_comments.append(
                        f"광고비는 {spend_change:+.1f}% 증가했습니다."
                    )

                elif spend_change < -20:

                    campaign_comments.append(
                        f"광고비는 {spend_change:+.1f}% 감소했습니다."
                    )


            # ------------------------------------------------
            # 종합 판단
            # ------------------------------------------------

            if (
                pd.notna(conversion_change)
                and pd.notna(cpa_change)
                and conversion_change > 10
                and cpa_change < -10
            ):

                conclusion = (
                    "성과 확대와 효율 개선이 동시에 나타나고 있어 "
                    "예산 확대 또는 유사 소재·타겟 확장을 검토할 수 있습니다."
                )

            elif (
                pd.notna(conversion_change)
                and pd.notna(cpa_change)
                and conversion_change < -10
                and cpa_change > 10
            ):

                conclusion = (
                    "볼륨과 효율이 동시에 악화된 캠페인으로, "
                    "예산·타겟·소재·랜딩 단계의 원인 분석이 우선입니다."
                )

            elif (
                pd.notna(cpa_change)
                and cpa_change < -10
            ):

                conclusion = (
                    "효율 개선이 확인되므로 현재 성과를 유지하면서 "
                    "추가 전환 확보 가능성을 확인할 필요가 있습니다."
                )

            elif (
                pd.notna(conversion_change)
                and conversion_change > 10
            ):

                conclusion = (
                    "전환 볼륨이 증가하고 있으므로 "
                    "추가 예산 투입 시 CPA가 유지되는지 확인하는 것이 중요합니다."
                )

            elif (
                pd.notna(conversion_change)
                and conversion_change < -10
            ):

                conclusion = (
                    "전환 감소 원인을 확인하기 위해 "
                    "광고비·클릭·CVR을 캠페인 세부 단위로 추가 분석하는 것이 좋습니다."
                )

            else:

                conclusion = (
                    "현재 성과를 유지하면서 추이를 지속적으로 모니터링하는 것이 좋습니다."
                )


            st.markdown(
                f"""
**`{campaign_name}`**

현재 전환 **{current_conversion:,.0f}건** → 비교 **{previous_conversion:,.0f}건**  
현재 CPA **{format_number(current_cpa, "원")}** → 비교 **{format_number(previous_cpa, "원")}**  
현재 CVR **{format_percent(current_cvr)}** → 비교 **{format_percent(previous_cvr)}**

{" ".join(campaign_comments)}

💡 **판단:** {conclusion}
"""
            )


# ============================================================
# 22. 데이터 정보
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
