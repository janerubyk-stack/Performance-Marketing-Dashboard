import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta, date
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

    # --------------------------------------------------------
    # 컬럼명 정리
    # --------------------------------------------------------

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    print("=" * 70)
    print("Google Sheets 데이터 불러오기 완료")
    print("=" * 70)

    print("데이터 건수:", f"{len(df):,}")
    print("실제 컬럼명:", df.columns.tolist())

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
        "유형",
        "광고유형"
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
        "IMPRESS",
        "노출"
    ])

    click_col = find_column([
        "click",
        "CLICK",
        "클릭"
    ])

    spend_col = find_column([
        "spend",
        "SPEND",
        "광고비"
    ])

    conversion_col = find_column([
        "conversion",
        "CONVERSION",
        "db",
        "DB",
        "전환"
    ])

    print("=" * 70)
    print("컬럼 매칭 결과")
    print("=" * 70)

    print("DATE       :", date_col)
    print("TYPE       :", type_col)
    print("MEDIA      :", media_col)
    print("CAMPAIGN   :", campaign_col)
    print("IMPRESS    :", impress_col)
    print("CLICK      :", click_col)
    print("SPEND      :", spend_col)
    print("CONVERSION :", conversion_col)

    # Type은 이번 버전부터 필수
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

    for col in ["type", "media", "campaign"]:

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

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    print("=" * 70)
    print("데이터 정상 처리")
    print("=" * 70)

    if len(df) > 0:

        print("데이터 건수:", f"{len(df):,}")
        print("시작 날짜:", df["date"].min().date())
        print("최신 날짜:", df["date"].max().date())

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
# 5. 기간 계산
# ============================================================

def get_periods(
    base_date,
    period_type,
    custom_current_start=None,
    custom_current_end=None,
    custom_previous_start=None,
    custom_previous_end=None
):

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

    # --------------------------------------------------------
    # 지정
    # --------------------------------------------------------

    elif period_type == "지정":

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

        current_days = (
            current_end -
            current_start
        ).days + 1

        previous_days = (
            previous_end -
            previous_start
        ).days + 1

        if current_days != previous_days:

            raise ValueError(
                f"기준 기간과 비교 기간의 일수가 다릅니다. "
                f"기준 기간: {current_days}일 / "
                f"비교 기간: {previous_days}일"
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
# 6. 기간 표시
# ============================================================

def format_period(start_date, end_date):

    return (
        f"{start_date.strftime('%Y-%m-%d')}"
        f" ~ "
        f"{end_date.strftime('%Y-%m-%d')}"
    )


# ============================================================
# 7. 성과 집계
# ============================================================

def calculate_metrics(result):

    if result.empty:

        return result

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


def aggregate_performance(
    data,
    start_date,
    end_date
):

    temp = data[
        (data["date"] >= start_date) &
        (data["date"] <= end_date)
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

    return calculate_metrics(result)


# ============================================================
# 8. 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(
    [1, 1.5, 2]
)


# ============================================================
# 9. 기준일
# ============================================================

available_dates = sorted(
    df["date"].dropna().unique()
)

min_date = pd.Timestamp(
    min(available_dates)
).date()

max_date = pd.Timestamp(
    max(available_dates)
).date()

with col1:

    base_date = st.date_input(
        "기준일",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )


# ============================================================
# 10. 비교 기간
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
# 11. 지정 기간
# ============================================================

custom_current_start = None
custom_current_end = None
custom_previous_start = None
custom_previous_end = None

if period_type == "지정":

    st.markdown("### 📅 지정 기간 설정")

    custom_col1, custom_col2 = st.columns(2)

    with custom_col1:

        st.markdown("**기준 기간**")

        custom_current_start = st.date_input(
            "기준 시작일",
            value=max(
                min_date,
                pd.Timestamp(base_date).date()
                - timedelta(days=19)
            ),
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

    with custom_col2:

        st.markdown("**비교 기간**")

        custom_previous_start = st.date_input(
            "비교 시작일",
            value=max(
                min_date,
                pd.Timestamp(base_date).date()
                - timedelta(days=50)
            ),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_start"
        )

        custom_previous_end = st.date_input(
            "비교 종료일",
            value=max(
                min_date,
                pd.Timestamp(base_date).date()
                - timedelta(days=31)
            ),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_end"
        )


# ============================================================
# 12. 기간 계산
# ============================================================

try:

    (
        current_start,
        current_end,
        previous_start,
        previous_end
    ) = get_periods(
        base_date,
        period_type,
        custom_current_start,
        custom_current_end,
        custom_previous_start,
        custom_previous_end
    )

except ValueError as e:

    st.error(str(e))

    st.stop()


current_period_text = format_period(
    current_start,
    current_end
)

previous_period_text = format_period(
    previous_start,
    previous_end
)

elapsed_days = (
    current_end -
    current_start
).days + 1


# ============================================================
# 13. 기간 정보
# ============================================================

with col3:

    st.info(
        f"""
**기준 기간:** {current_period_text}

**비교 기간:** {previous_period_text}

**동일 진행일수:** {elapsed_days}일
"""
    )


# ============================================================
# 14. Type / 매체 / 캠페인 필터
# ============================================================

st.markdown("### 🎯 분석 대상")

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
    [1, 1.5, 2.5]
)


# ============================================================
# Type 필터
# ============================================================

with filter_col1:

    selected_types = st.multiselect(
        "Type 선택",
        options=type_options,
        default=type_options,
        key="type_filter"
    )


# ============================================================
# Type에 따른 매체 옵션
# ============================================================

type_media_df = df[
    df["type"].isin(selected_types)
]

filtered_media_options = sorted(
    type_media_df["media"]
    .dropna()
    .unique()
    .tolist()
)

# 기존 선택값 중 존재하는 것만 유지
existing_media = st.session_state.get(
    "media_filter",
    filtered_media_options
)

selected_media_default = [
    x
    for x in existing_media
    if x in filtered_media_options
]

if not selected_media_default:

    selected_media_default = filtered_media_options


with filter_col2:

    selected_media = st.multiselect(
        "매체 선택",
        options=filtered_media_options,
        default=selected_media_default,
        key="media_filter"
    )


# ============================================================
# Type + Media에 따른 캠페인
# ============================================================

type_media_campaign_df = df[
    df["type"].isin(selected_types) &
    df["media"].isin(selected_media)
]

filtered_campaign_options = sorted(
    type_media_campaign_df["campaign"]
    .dropna()
    .unique()
    .tolist()
)

existing_campaigns = st.session_state.get(
    "campaign_filter",
    filtered_campaign_options
)

selected_campaigns_default = [
    x
    for x in existing_campaigns
    if x in filtered_campaign_options
]

if not selected_campaigns_default:

    selected_campaigns_default = filtered_campaign_options


with filter_col3:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=filtered_campaign_options,
        default=selected_campaigns_default,
        key="campaign_filter"
    )


# ============================================================
# 15. 전체 선택
# ============================================================

button_col1, button_col2, button_col3 = st.columns(
    [1, 1, 1]
)

with button_col1:

    if st.button(
        "📌 Type 전체 선택",
        use_container_width=True
    ):

        st.session_state["type_filter"] = type_options

        st.rerun()


with button_col2:

    if st.button(
        "📌 매체 전체 선택",
        use_container_width=True
    ):

        st.session_state["media_filter"] = filtered_media_options

        st.rerun()


with button_col3:

    if st.button(
        "📌 캠페인 전체 선택",
        use_container_width=True
    ):

        st.session_state["campaign_filter"] = filtered_campaign_options

        st.rerun()


# ============================================================
# 16. 필터 데이터
# ============================================================

filtered_df = df[
    df["type"].isin(selected_types) &
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 17. 현재 / 비교 데이터
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
# 18. 매체 기준 집계
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

    return calculate_metrics(result)


current_media = aggregate_by_media(
    current_df
)

previous_media = aggregate_by_media(
    previous_df
)


# ============================================================
# 19. 비교 데이터 생성
# ============================================================

def create_comparison(
    current,
    previous,
    group_col
):

    current = current.copy()
    previous = previous.copy()

    current = current.set_index(group_col)
    previous = previous.set_index(group_col)

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
            c_conversion / c_click * 100
            if c_click > 0
            else np.nan
        )

        p_cvr = (
            p_conversion / p_click * 100
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
                p_cvr
        })

    result = pd.DataFrame(rows)

    # --------------------------------------------------------
    # 변화율
    # --------------------------------------------------------

    def change_rate(
        current_value,
        previous_value
    ):

        if (
            pd.isna(previous_value)
            or previous_value == 0
        ):

            return np.nan

        return (
            (current_value - previous_value)
            / previous_value
            * 100
        )

    result["spend_change"] = result.apply(
        lambda x: change_rate(
            x["spend_current"],
            x["spend_previous"]
        ),
        axis=1
    )

    result["conversion_change"] = result.apply(
        lambda x: change_rate(
            x["conversion_current"],
            x["conversion_previous"]
        ),
        axis=1
    )

    result["CPA_change"] = result.apply(
        lambda x: change_rate(
            x["CPA_current"],
            x["CPA_previous"]
        ),
        axis=1
    )

    result["CVR_change"] = result.apply(
        lambda x: change_rate(
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
# 20. 표시 함수
# ============================================================

def number_text(value):

    if pd.isna(value):

        return "-"

    return f"{value:,.0f}"


def cpa_text(value):

    if pd.isna(value):

        return "-"

    return f"{value:,.0f}원"


def percent_text(value):

    if pd.isna(value):

        return "-"

    return f"{value:,.2f}%"


# ============================================================
# 21. 추이 데이터
# ============================================================

def get_trend_data(
    data,
    start_date,
    end_date,
    frequency
):

    temp = data[
        (data["date"] >= start_date) &
        (data["date"] <= end_date)
    ].copy()

    if temp.empty:

        return pd.DataFrame(
            columns=[
                "period",
                "spend",
                "conversion",
                "CPA"
            ]
        )

    if frequency == "일자별":

        temp["period"] = temp["date"]

    elif frequency == "주차별":

        temp["period"] = (
            temp["date"]
            - pd.to_timedelta(
                temp["date"].dt.weekday,
                unit="D"
            )
        )

    elif frequency == "월별":

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
            conversion=("conversion", "sum")
        )
    )

    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"] /
        result["conversion"],
        np.nan
    )

    return result.sort_values("period")


# ============================================================
# 22. 성과 추이
# ============================================================

st.divider()

st.header("📈 성과 추이")

st.caption(
    "선택한 기간의 광고비와 전환 흐름을 확인합니다. "
    "CPA는 막대, 전환수는 꺾은선으로 표시합니다."
)

trend_tab1, trend_tab2, trend_tab3 = st.tabs(
    [
        "📅 일자별",
        "📆 주차별",
        "🗓️ 월별"
    ]
)


def draw_trend_chart(
    trend_df,
    title,
    x_format
):

    if trend_df.empty:

        st.info("해당 기간에 데이터가 없습니다.")

        return

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=trend_df["period"],
            y=trend_df["CPA"],
            name="CPA",
            text=[
                f"{v:,.0f}원"
                if pd.notna(v)
                else "-"
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

    fig.add_trace(
        go.Scatter(
            x=trend_df["period"],
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

        title=title,

        height=420,

        margin=dict(
            l=60,
            r=60,
            t=70,
            b=80
        ),

        xaxis=dict(
            title="기간",
            tickformat=x_format,
            automargin=True
        ),

        yaxis=dict(
            title="CPA (원)"
        ),

        yaxis2=dict(
            title="전환수 (건)",
            overlaying="y",
            side="right"
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),

        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


with trend_tab1:

    trend_daily = get_trend_data(
        filtered_df,
        current_start,
        current_end,
        "일자별"
    )

    draw_trend_chart(
        trend_daily,
        f"일자별 CPA + 전환수 추이 ({current_period_text})",
        "%m/%d"
    )


with trend_tab2:

    trend_weekly = get_trend_data(
        filtered_df,
        current_start,
        current_end,
        "주차별"
    )

    draw_trend_chart(
        trend_weekly,
        f"주차별 CPA + 전환수 추이 ({current_period_text})",
        "%m/%d"
    )


with trend_tab3:

    trend_monthly = get_trend_data(
        filtered_df,
        current_start,
        current_end,
        "월별"
    )

    draw_trend_chart(
        trend_monthly,
        f"월별 CPA + 전환수 추이 ({current_period_text})",
        "%Y-%m"
    )


# ============================================================
# 23. 성과 비교
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text}  |  "
    f"비교 기간: {previous_period_text}  |  "
    f"동일 진행일수: {elapsed_days}일"
)


# ============================================================
# 24. 그래프 데이터
# ============================================================

chart_df = comparison.copy()

chart_df = chart_df[
    chart_df["media"].isin(selected_media)
].copy()

chart_df = chart_df.sort_values(
    "conversion_current",
    ascending=False
)

x_labels = chart_df["media"].tolist()


# ============================================================
# 25. CPA + 전환수
# ============================================================

fig_cpa = go.Figure()

fig_cpa.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["CPA_current"],
        name="기준 CPA",
        text=[
            cpa_text(v)
            for v in chart_df["CPA_current"]
        ],
        textposition="outside",
        hovertemplate=(
            "%{x}<br>"
            "기준 CPA: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)

fig_cpa.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["CPA_previous"],
        name="비교 CPA",
        text=[
            cpa_text(v)
            for v in chart_df["CPA_previous"]
        ],
        textposition="outside",
        hovertemplate=(
            "%{x}<br>"
            "비교 CPA: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)

fig_cpa.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df["conversion_current"],
        name="기준 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "%{x}<br>"
            "기준 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_cpa.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df["conversion_previous"],
        name="비교 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "%{x}<br>"
            "비교 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_cpa.update_layout(

    title="CPA + 전환수",

    barmode="group",

    height=420,

    margin=dict(
        l=50,
        r=50,
        t=80,
        b=100
    ),

    xaxis=dict(
        title="매체",
        tickangle=-35,
        automargin=True,
        type="category"
    ),

    yaxis=dict(
        title="CPA (원)"
    ),

    yaxis2=dict(
        title="전환수 (건)",
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
# 26. 광고비 + 전환수
# ============================================================

fig_spend = go.Figure()

fig_spend.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["spend_current"],
        name="기준 광고비",
        text=[
            number_text(v)
            for v in chart_df["spend_current"]
        ],
        textposition="outside",
        hovertemplate=(
            "%{x}<br>"
            "기준 광고비: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)

fig_spend.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["spend_previous"],
        name="비교 광고비",
        text=[
            number_text(v)
            for v in chart_df["spend_previous"]
        ],
        textposition="outside",
        hovertemplate=(
            "%{x}<br>"
            "비교 광고비: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)

fig_spend.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df["conversion_current"],
        name="기준 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "%{x}<br>"
            "기준 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_spend.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df["conversion_previous"],
        name="비교 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "%{x}<br>"
            "기준 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_spend.update_layout(

    title="광고비 + 전환수",

    barmode="group",

    height=420,

    margin=dict(
        l=50,
        r=50,
        t=80,
        b=100
    ),

    xaxis=dict(
        title="매체",
        tickangle=-35,
        automargin=True,
        type="category"
    ),

    yaxis=dict(
        title="광고비 (원)"
    ),

    yaxis2=dict(
        title="전환수 (건)",
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
# 27. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "기준 기간과 비교 기간의 성과 및 변화율을 매체별로 비교합니다."
)


media_table = comparison[
    comparison["media"].isin(selected_media)
].copy()

media_table = media_table.sort_values(
    "conversion_current",
    ascending=False
)


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


# ============================================================
# 28. HTML 매체 테이블
# ============================================================

media_html = """

<style>

.performance-table {

    width: 100%;
    border-collapse: collapse;
    font-size: 14px;

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


for media in media_table["media"]:

    media_html += (
        f"<th>{html.escape(str(media))}</th>"
    )


media_html += "</tr>"


for (
    metric_name,
    current_col,
    previous_col,
    change_col,
    fmt_type
) in metric_rows:

    media_html += f"""

<tr>

<td class="metric">
{metric_name}
</td>

"""


    for _, row in media_table.iterrows():

        current_value = row[current_col]
        previous_value = row[previous_col]
        change_value = row[change_col]

        if fmt_type in ["money", "cpa"]:

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

        if pd.isna(change_value):

            change_html = (
                '<span class="neutral">-</span>'
            )

        elif change_value > 0:

            change_html = (
                f'<span class="up">'
                f'▲ +{change_value:,.1f}%'
                f'</span>'
            )

        elif change_value < 0:

            change_html = (
                f'<span class="down">'
                f'▼ {change_value:,.1f}%'
                f'</span>'
            )

        else:

            change_html = (
                '<span class="neutral">'
                '─ 0.0%'
                '</span>'
            )

        media_html += f"""

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


    media_html += "</tr>"


media_html += """

</table>

"""

st.markdown(
    media_html,
    unsafe_allow_html=True
)


# ============================================================
# 29. 분석 코멘트
# ============================================================

st.divider()

st.header("💡 성과 해석")

st.caption(
    "전환수, CPA, CVR의 변화 방향을 기준으로 성과가 좋아진 매체와 "
    "개선이 필요한 대상을 자동으로 정리합니다."
)


# ============================================================
# 30. 매체별 코멘트 생성
# ============================================================

def generate_media_comments(comparison_df):

    comments = []

    if comparison_df.empty:

        return [
            "비교할 데이터가 없습니다."
        ]

    for _, row in comparison_df.iterrows():

        target = str(
            row["media"]
        )

        conv_change = row[
            "conversion_change"
        ]

        cpa_change = row[
            "CPA_change"
        ]

        cvr_change = row[
            "CVR_change"
        ]

        # ----------------------------------------------------
        # 전환 증가 + CPA 개선
        # ----------------------------------------------------

        if (
            pd.notna(conv_change)
            and conv_change > 10
            and pd.notna(cpa_change)
            and cpa_change < -10
        ):

            comments.append(
                f"• **{target}**: "
                f"전환수 **{conv_change:+.1f}%** 증가 / "
                f"CPA **{cpa_change:+.1f}%** 개선 "
                f"→ **볼륨과 효율이 동시에 개선된 우수 매체**"
            )

        # ----------------------------------------------------
        # 전환 증가 + CPA 악화
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change > 10
            and pd.notna(cpa_change)
            and cpa_change > 10
        ):

            comments.append(
                f"• **{target}**: "
                f"전환수 **{conv_change:+.1f}%** 증가했지만 "
                f"CPA는 **{cpa_change:+.1f}%** 상승 "
                f"→ **볼륨 확대 효과는 있으나 효율 악화 여부 확인 필요**"
            )

        # ----------------------------------------------------
        # 전환 감소 + CPA 개선
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change < -10
            and pd.notna(cpa_change)
            and cpa_change < -10
        ):

            comments.append(
                f"• **{target}**: "
                f"CPA **{cpa_change:+.1f}%** 개선됐지만 "
                f"전환수는 **{conv_change:+.1f}%** 감소 "
                f"→ **효율은 개선됐지만 볼륨 축소 상황**"
            )

        # ----------------------------------------------------
        # 전환 감소 + CPA 악화
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change < -10
            and pd.notna(cpa_change)
            and cpa_change > 10
        ):

            comments.append(
                f"• **{target}**: "
                f"전환수 **{conv_change:+.1f}%** 감소 / "
                f"CPA **{cpa_change:+.1f}%** 상승 "
                f"→ **성과 악화가 뚜렷해 우선 점검 필요**"
            )

        # ----------------------------------------------------
        # 전환 증가
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change > 10
        ):

            comments.append(
                f"• **{target}**: "
                f"전환수가 **{conv_change:+.1f}%** 증가 "
                f"→ **볼륨 확대 효과가 나타나는 매체**"
            )

        # ----------------------------------------------------
        # 전환 감소
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change < -10
        ):

            comments.append(
                f"• **{target}**: "
                f"전환수가 **{conv_change:+.1f}%** 감소 "
                f"→ **예산·유입량·CVR 변화를 함께 점검 필요**"
            )

        else:

            comments.append(
                f"• **{target}**: "
                f"전반적으로 큰 변동이 없습니다."
            )

        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

        if (
            pd.notna(cvr_change)
            and cvr_change > 10
        ):

            comments.append(
                f"  → CVR **{cvr_change:+.1f}% 개선**"
            )

        elif (
            pd.notna(cvr_change)
            and cvr_change < -10
        ):

            comments.append(
                f"  → CVR **{cvr_change:+.1f}% 하락** "
                f"→ 랜딩페이지·타겟·소재 점검 필요"
            )

    return comments


media_comments = generate_media_comments(
    comparison
)


for comment in media_comments:

    st.markdown(comment)


# ============================================================
# 31. 전체 성과 요약
# ============================================================

st.subheader("📊 전체 성과 요약")


total_current_spend = (
    current_df["spend"].sum()
    if not current_df.empty
    else 0
)

total_previous_spend = (
    previous_df["spend"].sum()
    if not previous_df.empty
    else 0
)

total_current_conv = (
    current_df["conversion"].sum()
    if not current_df.empty
    else 0
)

total_previous_conv = (
    previous_df["conversion"].sum()
    if not previous_df.empty
    else 0
)

total_current_click = (
    current_df["click"].sum()
    if not current_df.empty
    else 0
)

total_previous_click = (
    previous_df["click"].sum()
    if not previous_df.empty
    else 0
)


total_current_cpa = (
    total_current_spend /
    total_current_conv
    if total_current_conv > 0
    else np.nan
)

total_previous_cpa = (
    total_previous_spend /
    total_previous_conv
    if total_previous_conv > 0
    else np.nan
)

total_current_cvr = (
    total_current_conv /
    total_current_click *
    100
    if total_current_click > 0
    else np.nan
)

total_previous_cvr = (
    total_previous_conv /
    total_previous_click *
    100
    if total_previous_click > 0
    else np.nan
)


def safe_change(current, previous):

    if (
        pd.isna(previous)
        or previous == 0
    ):

        return np.nan

    return (
        (current - previous)
        / previous
        * 100
    )


total_spend_change = safe_change(
    total_current_spend,
    total_previous_spend
)

total_conv_change = safe_change(
    total_current_conv,
    total_previous_conv
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
        "전체 광고비",
        f"{total_current_spend:,.0f}원",
        (
            f"{total_spend_change:+.1f}%"
            if pd.notna(total_spend_change)
            else None
        )
    )


with summary_col2:

    st.metric(
        "전체 전환수",
        f"{total_current_conv:,.0f}건",
        (
            f"{total_conv_change:+.1f}%"
            if pd.notna(total_conv_change)
            else None
        )
    )


with summary_col3:

    st.metric(
        "전체 CPA",
        (
            f"{total_current_cpa:,.0f}원"
            if pd.notna(total_current_cpa)
            else "-"
        ),
        (
            f"{total_cpa_change:+.1f}%"
            if pd.notna(total_cpa_change)
            else None
        )
    )


with summary_col4:

    st.metric(
        "전체 CVR",
        (
            f"{total_current_cvr:.2f}%"
            if pd.notna(total_current_cvr)
            else "-"
        ),
        (
            f"{total_cvr_change:+.1f}%"
            if pd.notna(total_cvr_change)
            else None
        )
    )


# ============================================================
# 32. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 Type·매체·캠페인 기준으로 캠페인별 성과를 상세 비교합니다."
)


# ============================================================
# 33. 캠페인 집계
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

    return calculate_metrics(result)


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
# 34. 캠페인 상세표
# ============================================================

campaign_metric_rows = [

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


campaign_html = """

<style>

.campaign-table {

    width: 100%;
    border-collapse: collapse;
    font-size: 13px;

}

.campaign-table th,
.campaign-table td {

    border: 1px solid #dddddd;
    padding: 9px;
    text-align: center;
    white-space: nowrap;

}

.campaign-table th {

    background-color: #f5f5f5;
    font-weight: 700;

}

.campaign-table td.metric {

    text-align: left;
    font-weight: 700;
    background-color: #fafafa;

}

</style>

<table class="campaign-table">

<tr>

<th>지표</th>

"""


for campaign in campaign_table["campaign"]:

    campaign_html += (
        f"<th>{html.escape(str(campaign))}</th>"
    )


campaign_html += "</tr>"


for (
    metric_name,
    current_col,
    previous_col,
    change_col,
    fmt_type
) in campaign_metric_rows:

    campaign_html += f"""

<tr>

<td class="metric">

{metric_name}

</td>

"""


    for _, row in campaign_table.iterrows():

        current_value = row[current_col]
        previous_value = row[previous_col]
        change_value = row[change_col]

        if fmt_type in ["money", "cpa"]:

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

        if pd.isna(change_value):

            change_html = "-"

        elif change_value > 0:

            change_html = (
                f'<span class="up">'
                f'▲ +{change_value:,.1f}%'
                f'</span>'
            )

        elif change_value < 0:

            change_html = (
                f'<span class="down">'
                f'▼ {change_value:,.1f}%'
                f'</span>'
            )

        else:

            change_html = "─ 0.0%"

        campaign_html += f"""

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


    campaign_html += "</tr>"


campaign_html += """

</table>

"""


st.markdown(
    campaign_html,
    unsafe_allow_html=True
)


# ============================================================
# 35. 캠페인 성과 코멘트
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

        # ----------------------------------------------------
        # CPA 최우수
        # ----------------------------------------------------

        cpa_valid = valid_campaigns[
            valid_campaigns["CPA_current"].notna()
        ]

        if not cpa_valid.empty:

            best = cpa_valid.loc[
                cpa_valid["CPA_current"].idxmin()
            ]

            st.markdown(
                f"🏆 **CPA 최우수 캠페인:** "
                f"`{best['campaign']}` "
                f"({best['CPA_current']:,.0f}원)"
            )

        # ----------------------------------------------------
        # 전환수 최다
        # ----------------------------------------------------

        best_conversion = valid_campaigns.loc[
            valid_campaigns[
                "conversion_current"
            ].idxmax()
        ]

        st.markdown(
            f"📈 **전환수 최다 캠페인:** "
            f"`{best_conversion['campaign']}` "
            f"({best_conversion['conversion_current']:,.0f}건)"
        )

        # ----------------------------------------------------
        # 전환 증가 최대
        # ----------------------------------------------------

        growth = campaign_table[
            campaign_table[
                "conversion_change"
            ].notna()
        ]

        if not growth.empty:

            growth_best = growth.loc[
                growth["conversion_change"].idxmax()
            ]

            if growth_best["conversion_change"] > 0:

                st.markdown(
                    f"🚀 **전환 증가폭 최대:** "
                    f"`{growth_best['campaign']}` "
                    f"({growth_best['conversion_change']:+,.1f}%)"
                )

        # ----------------------------------------------------
        # CPA 개선 최대
        # ----------------------------------------------------

        cpa_improved = campaign_table[
            campaign_table["CPA_change"].notna() &
            (campaign_table["CPA_change"] < 0)
        ]

        if not cpa_improved.empty:

            best_cpa_improved = cpa_improved.loc[
                cpa_improved["CPA_change"].idxmin()
            ]

            st.markdown(
                f"💰 **CPA 개선폭 최대:** "
                f"`{best_cpa_improved['campaign']}` "
                f"({best_cpa_improved['CPA_change']:+,.1f}%)"
            )

        # ----------------------------------------------------
        # CPA 악화
        # ----------------------------------------------------

        cpa_worsened = campaign_table[
            campaign_table["CPA_change"].notna() &
            (campaign_table["CPA_change"] > 0)
        ]

        if not cpa_worsened.empty:

            worst = cpa_worsened.loc[
                cpa_worsened["CPA_change"].idxmax()
            ]

            st.markdown(
                f"⚠️ **CPA 악화 주의:** "
                f"`{worst['campaign']}` "
                f"({worst['CPA_change']:+,.1f}%)"
            )

        # ----------------------------------------------------
        # 종합 개선 캠페인
        # ----------------------------------------------------

        excellent = campaign_table[
            campaign_table["conversion_change"].notna() &
            campaign_table["CPA_change"].notna() &
            (campaign_table["conversion_change"] > 10) &
            (campaign_table["CPA_change"] < -10)
        ]

        if not excellent.empty:

            st.markdown(
                "### ⭐ 볼륨 + 효율 동시 개선 캠페인"
            )

            for _, row in excellent.iterrows():

                st.markdown(
                    f"- **{row['campaign']}**: "
                    f"전환수 {row['conversion_change']:+,.1f}% / "
                    f"CPA {row['CPA_change']:+,.1f}%"
                )

        # ----------------------------------------------------
        # 악화 캠페인
        # ----------------------------------------------------

        danger = campaign_table[
            campaign_table["conversion_change"].notna() &
            campaign_table["CPA_change"].notna() &
            (campaign_table["conversion_change"] < -10) &
            (campaign_table["CPA_change"] > 10)
        ]

        if not danger.empty:

            st.markdown(
                "### 🚨 우선 점검 캠페인"
            )

            for _, row in danger.iterrows():

                st.markdown(
                    f"- **{row['campaign']}**: "
                    f"전환수 {row['conversion_change']:+,.1f}% / "
                    f"CPA {row['CPA_change']:+,.1f}%"
                )


# ============================================================
# 36. 데이터 정보
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
        f"선택 Type: "
        f"{', '.join(selected_types)}"
    )

    st.write(
        f"선택 매체: "
        f"{', '.join(selected_media)}"
    )

    st.write(
        f"선택 캠페인 수: "
        f"{len(selected_campaigns):,}개"
    )
