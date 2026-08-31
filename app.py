import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from openai import OpenAI
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
# 1. OpenAI 설정
# ============================================================

def get_openai_client():

    if "OPENAI_API_KEY" not in st.secrets:
        return None

    api_key = st.secrets["OPENAI_API_KEY"]

    if not api_key:
        return None

    return OpenAI(api_key=api_key)


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
# 3. 제목
# ============================================================

st.title("📈 성과 비교 대시보드")
st.caption("Performance Marketing Data Dashboard")


# ============================================================
# 4. 데이터 로드
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
    # 컬럼 찾기
    # --------------------------------------------------------

    def find_column(candidates):

        # 정확히 일치
        for candidate in candidates:

            for col in df.columns:

                if (
                    str(col).strip().lower()
                    == candidate.lower()
                ):
                    return col

        # 부분 일치
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

    required = {
        "DATE": date_col,
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
    # 컬럼명 통일
    # --------------------------------------------------------

    df = df.rename(
        columns={
            date_col: "date",
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

    df["date"] = df["date"].dt.normalize()

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
            .str.replace(" ", "", regex=False)
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # 문자열
    # --------------------------------------------------------

    for col in [
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
            df[col].isin([
                "",
                "nan",
                "None",
                "<NA>"
            ]),
            col
        ] = "미분류"

    # --------------------------------------------------------
    # 날짜 없는 행 제거
    # --------------------------------------------------------

    df = df.dropna(
        subset=["date"]
    ).copy()

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
# 5. 데이터 로드 실행
# ============================================================

try:

    df = load_data()

except Exception as e:

    st.error(
        "Google Sheets 데이터를 불러오지 못했습니다."
    )

    st.exception(e)

    st.stop()


if df.empty:

    st.warning(
        "데이터가 없습니다."
    )

    st.stop()


# ============================================================
# 6. 실제 성과가 있는 최신일 계산
# ============================================================

daily_performance = (
    df
    .groupby("date", as_index=False)
    .agg(
        impress=("impress", "sum"),
        click=("click", "sum"),
        spend=("spend", "sum"),
        conversion=("conversion", "sum")
    )
)

valid_performance_dates = daily_performance[
    (
        daily_performance["spend"] > 0
    )
    |
    (
        daily_performance["click"] > 0
    )
    |
    (
        daily_performance["conversion"] > 0
    )
]["date"]


if len(valid_performance_dates) > 0:

    latest_performance_date = (
        valid_performance_dates.max()
    )

else:

    latest_performance_date = df["date"].max()


# ============================================================
# 7. 기간 계산
# ============================================================

def get_periods(
    base_date,
    period_type
):

    base_date = pd.Timestamp(
        base_date
    ).normalize()

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

        previous_end = (
            base_date -
            timedelta(days=1)
        )

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

        current_start = (
            base_date.replace(day=1)
        )

        current_end = base_date

        day_number = base_date.day

        previous_month_last = (
            base_date.replace(day=1)
            - timedelta(days=1)
        )

        previous_year = (
            previous_month_last.year
        )

        previous_month = (
            previous_month_last.month
        )

        previous_month_days = (
            calendar.monthrange(
                previous_year,
                previous_month
            )[1]
        )

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
# 8. 성과 집계
# ============================================================

def aggregate_performance(
    data,
    start_date,
    end_date
):

    temp = data[
        (data["date"] >= start_date)
        &
        (data["date"] <= end_date)
    ].copy()

    if temp.empty:

        return pd.DataFrame(
            columns=[
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

    # CPA
    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"] /
        result["conversion"],
        np.nan
    )

    # CVR
    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
        np.nan
    )

    return result


# ============================================================
# 9. 매체 집계
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


# ============================================================
# 10. 캠페인 집계
# ============================================================

def aggregate_by_campaign(data):

    if data.empty:

        return pd.DataFrame(
            columns=[
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
        data
        .groupby(
            "campaign",
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


# ============================================================
# 11. 비교 데이터 생성
# ============================================================

def create_comparison(
    current,
    previous,
    group_col
):

    columns = [
        group_col,
        "spend_current",
        "spend_previous",
        "click_current",
        "click_previous",
        "conversion_current",
        "conversion_previous",
        "CPA_current",
        "CPA_previous",
        "CVR_current",
        "CVR_previous",
        "spend_change",
        "click_change",
        "conversion_change",
        "CPA_change",
        "CVR_change",
        "CVR_point_change"
    ]

    if current.empty and previous.empty:

        return pd.DataFrame(
            columns=columns
        )

    current = current.copy()
    previous = previous.copy()

    current = current.set_index(
        group_col
    )

    previous = previous.set_index(
        group_col
    )

    groups = sorted(
        set(current.index.tolist())
        |
        set(previous.index.tolist()),
        key=lambda x: str(x)
    )

    rows = []

    for group in groups:

        if group in current.index:
            c = current.loc[group]
        else:
            c = pd.Series(
                dtype=float
            )

        if group in previous.index:
            p = previous.loc[group]
        else:
            p = pd.Series(
                dtype=float
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

        # ----------------------------------------------------
        # CPA
        # ----------------------------------------------------

        c_cpa = (
            c_spend /
            c_conversion
            if c_conversion > 0
            else np.nan
        )

        p_cpa = (
            p_spend /
            p_conversion
            if p_conversion > 0
            else np.nan
        )

        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

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

        rows.append(
            {
                group_col: group,

                "spend_current":
                    c_spend,

                "spend_previous":
                    p_spend,

                "click_current":
                    c_click,

                "click_previous":
                    p_click,

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
            }
        )

    result = pd.DataFrame(
        rows
    )

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
            or pd.isna(current_value)
        ):
            return np.nan

        return (
            (
                current_value -
                previous_value
            )
            /
            previous_value
            *
            100
        )

    result["spend_change"] = result.apply(
        lambda x:
        change_rate(
            x["spend_current"],
            x["spend_previous"]
        ),
        axis=1
    )

    result["click_change"] = result.apply(
        lambda x:
        change_rate(
            x["click_current"],
            x["click_previous"]
        ),
        axis=1
    )

    result["conversion_change"] = result.apply(
        lambda x:
        change_rate(
            x["conversion_current"],
            x["conversion_previous"]
        ),
        axis=1
    )

    result["CPA_change"] = result.apply(
        lambda x:
        change_rate(
            x["CPA_current"],
            x["CPA_previous"]
        ),
        axis=1
    )

    result["CVR_change"] = result.apply(
        lambda x:
        change_rate(
            x["CVR_current"],
            x["CVR_previous"]
        ),
        axis=1
    )

    # --------------------------------------------------------
    # CVR %p 변화
    # --------------------------------------------------------

    result["CVR_point_change"] = (
        result["CVR_current"]
        -
        result["CVR_previous"]
    )

    return result


# ============================================================
# 12. 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(
    [1, 1, 2]
)


# ============================================================
# 13. 날짜 설정
# ============================================================

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

default_date = (
    latest_performance_date.date()
)


with col1:

    base_date = st.date_input(
        "기준일",
        value=default_date,
        min_value=min_date,
        max_value=max_date
    )


# ============================================================
# 14. 비교 기간
# ============================================================

with col2:

    period_type = st.radio(
        "비교 기간",
        [
            "전일",
            "전주",
            "전월"
        ],
        horizontal=True
    )


# ============================================================
# 15. 기간 계산
# ============================================================

(
    current_start,
    current_end,
    previous_start,
    previous_end
) = get_periods(
    base_date,
    period_type
)

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


with col3:

    st.info(
        f"**기준 기간:** {current_period_text}\n\n"
        f"**비교 기간:** {previous_period_text}\n\n"
        f"**동일 진행일수:** {elapsed_days}일"
    )


# ============================================================
# 16. 분석 대상
# ============================================================

st.subheader("🎯 분석 대상")

media_options = sorted(
    df["media"]
    .dropna()
    .unique()
    .tolist(),
    key=lambda x: str(x)
)

campaign_options = sorted(
    df["campaign"]
    .dropna()
    .unique()
    .tolist(),
    key=lambda x: str(x)
)


# ============================================================
# 17. 매체 필터
# ============================================================

filter_col1, filter_col2 = st.columns(2)


if "media_filter" not in st.session_state:

    st.session_state[
        "media_filter"
    ] = media_options


if "campaign_filter" not in st.session_state:

    st.session_state[
        "campaign_filter"
    ] = campaign_options


with filter_col1:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_options,
        key="media_filter"
    )


with filter_col2:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=campaign_options,
        key="campaign_filter"
    )


# ============================================================
# 18. 전체 선택 버튼
# ============================================================

button_col1, button_col2, button_col3 = st.columns(
    [1, 1, 4]
)


with button_col1:

    if st.button(
        "📌 매체 전체 선택",
        use_container_width=True
    ):

        st.session_state[
            "media_filter"
        ] = media_options

        st.rerun()


with button_col2:

    if st.button(
        "📌 캠페인 전체 선택",
        use_container_width=True
    ):

        st.session_state[
            "campaign_filter"
        ] = campaign_options

        st.rerun()


# ============================================================
# 19. 필터 데이터
# ============================================================

filtered_df = df[
    df["media"].isin(
        selected_media
    )
    &
    df["campaign"].isin(
        selected_campaigns
    )
].copy()


# ============================================================
# 20. 기준/비교 데이터
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
# 21. 매체 데이터
# ============================================================

current_media = aggregate_by_media(
    current_df
)

previous_media = aggregate_by_media(
    previous_df
)


comparison = create_comparison(
    current_media,
    previous_media,
    "media"
)


# ============================================================
# 22. 포맷 함수
# ============================================================

def safe_number(value):

    if pd.isna(value):
        return "-"

    return f"{float(value):,.0f}"


def safe_money(value):

    if pd.isna(value):
        return "-"

    return f"{float(value):,.0f}원"


def safe_percent(value):

    if pd.isna(value):
        return "-"

    return f"{float(value):,.2f}%"


def safe_point(value):

    if pd.isna(value):
        return "-"

    sign = "+" if value > 0 else ""

    return (
        f"{sign}"
        f"{float(value):,.2f}%p"
    )


def change_html(value):

    if pd.isna(value):

        return (
            '<span class="neutral">-</span>'
        )

    value = float(value)

    if value > 0:

        return (
            '<span class="up">'
            f'▲ +{value:,.1f}%'
            '</span>'
        )

    if value < 0:

        return (
            '<span class="down">'
            f'▼ {value:,.1f}%'
            '</span>'
        )

    return (
        '<span class="neutral">'
        '─ 0.0%'
        '</span>'
    )


# ============================================================
# 23. 그래프
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text}  |  "
    f"비교 기간: {previous_period_text}"
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


x_labels = [
    str(x)
    for x in chart_df["media"].tolist()
]


# ============================================================
# 24. CPA + DB
# ============================================================

fig_cpa = go.Figure()


fig_cpa.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df[
            "CPA_current"
        ].fillna(0),
        name="기준 CPA",
        text=[
            safe_money(v)
            for v in chart_df[
                "CPA_current"
            ]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 CPA: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)


fig_cpa.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df[
            "CPA_previous"
        ].fillna(0),
        name="비교 CPA",
        text=[
            safe_money(v)
            for v in chart_df[
                "CPA_previous"
            ]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 CPA: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)


fig_cpa.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df[
            "conversion_current"
        ].fillna(0),
        name="기준 DB",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 DB: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)


fig_cpa.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df[
            "conversion_previous"
        ].fillna(0),
        name="비교 DB",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 DB: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)


fig_cpa.update_layout(

    title=(
        "CPA + DB"
        f"<br><sup>"
        f"기준: {current_period_text}"
        f" | "
        f"비교: {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=380,

    margin=dict(
        l=55,
        r=55,
        t=90,
        b=125
    ),

    xaxis=dict(
        title="매체",
        type="category",
        tickangle=-45,
        automargin=True,
        tickfont=dict(size=11)
    ),

    yaxis=dict(
        title="CPA",
        tickformat=","
    ),

    yaxis2=dict(
        title="DB",
        overlaying="y",
        side="right",
        tickformat=","
    ),

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.38,
        xanchor="center",
        x=0.5
    ),

    hovermode="x unified"
)


# ============================================================
# 25. 광고비 + DB
# ============================================================

fig_spend = go.Figure()


fig_spend.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df[
            "spend_current"
        ].fillna(0),
        name="기준 광고비",
        text=[
            safe_money(v)
            for v in chart_df[
                "spend_current"
            ]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 광고비: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)


fig_spend.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df[
            "spend_previous"
        ].fillna(0),
        name="비교 광고비",
        text=[
            safe_money(v)
            for v in chart_df[
                "spend_previous"
            ]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 광고비: %{y:,.0f}원"
            "<extra></extra>"
        )
    )
)


fig_spend.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df[
            "conversion_current"
        ].fillna(0),
        name="기준 DB",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 DB: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)


fig_spend.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df[
            "conversion_previous"
        ].fillna(0),
        name="비교 DB",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 DB: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)


fig_spend.update_layout(

    title=(
        "광고비 + DB"
        f"<br><sup>"
        f"기준: {current_period_text}"
        f" | "
        f"비교: {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=380,

    margin=dict(
        l=55,
        r=55,
        t=90,
        b=125
    ),

    xaxis=dict(
        title="매체",
        type="category",
        tickangle=-45,
        automargin=True,
        tickfont=dict(size=11)
    ),

    yaxis=dict(
        title="광고비",
        tickformat=","
    ),

    yaxis2=dict(
        title="DB",
        overlaying="y",
        side="right",
        tickformat=","
    ),

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.38,
        xanchor="center",
        x=0.5
    ),

    hovermode="x unified"
)


# ============================================================
# 26. CVR 그래프
# ============================================================

fig_cvr = go.Figure()


fig_cvr.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df[
            "CVR_current"
        ].fillna(0),
        name="기준 CVR",
        text=[
            safe_percent(v)
            for v in chart_df[
                "CVR_current"
            ]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 CVR: %{y:.2f}%"
            "<extra></extra>"
        )
    )
)


fig_cvr.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df[
            "CVR_previous"
        ].fillna(0),
        name="비교 CVR",
        text=[
            safe_percent(v)
            for v in chart_df[
                "CVR_previous"
            ]
        ],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 CVR: %{y:.2f}%"
            "<extra></extra>"
        )
    )
)


fig_cvr.update_layout(

    title=(
        "CVR 비교"
        f"<br><sup>"
        f"기준: {current_period_text}"
        f" | "
        f"비교: {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=380,

    margin=dict(
        l=55,
        r=55,
        t=90,
        b=125
    ),

    xaxis=dict(
        title="매체",
        type="category",
        tickangle=-45,
        automargin=True,
        tickfont=dict(size=11)
    ),

    yaxis=dict(
        title="CVR (%)",
        ticksuffix="%"
    ),

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.38,
        xanchor="center",
        x=0.5
    ),

    hovermode="x unified"
)


# ============================================================
# 27. 그래프 출력
# ============================================================

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


st.plotly_chart(
    fig_cvr,
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)


# ============================================================
# 28. 비교표 HTML
# ============================================================

def build_comparison_html(
    table_df,
    group_col,
    table_class
):

    if table_df.empty:

        return (
            "<p>비교할 데이터가 없습니다.</p>"
        )

    result_html = f"""
    <style>

    .{table_class} {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}

    .{table_class} th,
    .{table_class} td {{
        border: 1px solid #dddddd;
        padding: 9px;
        text-align: center;
        white-space: nowrap;
    }}

    .{table_class} th {{
        background-color: #f5f5f5;
        font-weight: 700;
    }}

    .{table_class} td.metric {{
        text-align: left;
        font-weight: 700;
        background-color: #fafafa;
        position: sticky;
        left: 0;
        z-index: 2;
    }}

    .up {{
        color: #d62728;
        font-weight: 700;
    }}

    .down {{
        color: #2468c7;
        font-weight: 700;
    }}

    .neutral {{
        color: #777777;
        font-weight: 700;
    }}

    </style>

    <div style="overflow-x:auto;">

    <table class="{table_class}">

    <tr>

    <th>지표</th>
    """

    for group in table_df[group_col]:

        safe_group = html.escape(
            str(group)
        )

        result_html += (
            f"<th>{safe_group}</th>"
        )

    result_html += "</tr>"


    # ========================================================
    # 지표
    # ========================================================

    metric_rows = [

        (
            "광고비",
            "spend_current",
            "spend_previous",
            "spend_change",
            "money"
        ),

        (
            "클릭",
            "click_current",
            "click_previous",
            "click_change",
            "number"
        ),

        (
            "DB",
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
            "money"
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

        result_html += f"""
        <tr>

        <td class="metric">
        {metric_name}
        </td>
        """

        for _, row in table_df.iterrows():

            current_value = row[
                current_col
            ]

            previous_value = row[
                previous_col
            ]

            change_value = row[
                change_col
            ]

            if fmt_type == "money":

                current_text = safe_money(
                    current_value
                )

                previous_text = safe_money(
                    previous_value
                )

            elif fmt_type == "number":

                current_text = (
                    f"{current_value:,.0f}건"
                    if pd.notna(
                        current_value
                    )
                    else "-"
                )

                previous_text = (
                    f"{previous_value:,.0f}건"
                    if pd.notna(
                        previous_value
                    )
                    else "-"
                )

            else:

                current_text = safe_percent(
                    current_value
                )

                previous_text = safe_percent(
                    previous_value
                )

            result_html += f"""
            <td>

            <div>
            기준:
            <b>{current_text}</b>
            </div>

            <div style="color:#888;">
            비교:
            {previous_text}
            </div>

            <div style="margin-top:4px;">
            {change_html(change_value)}
            </div>

            """

            # CVR일 경우 %p도 표시
            if metric_name == "CVR":

                point_value = row[
                    "CVR_point_change"
                ]

                result_html += f"""
                <div style="
                    color:#666;
                    font-size:11px;
                    margin-top:2px;
                ">
                {safe_point(point_value)}
                </div>
                """

            result_html += """
            </td>
            """

        result_html += "</tr>"


    result_html += """
    </table>
    </div>
    """

    return result_html


# ============================================================
# 29. 매체 비교표
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "기준 기간과 비교 기간의 광고비·클릭·DB·CPA·CVR을 비교합니다."
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


st.markdown(
    build_comparison_html(
        media_table,
        "media",
        "performance-table"
    ),
    unsafe_allow_html=True
)


# ============================================================
# 30. 자동 성과 해석
# ============================================================

st.divider()

st.header("💡 성과 해석")


def make_performance_comments(
    result_df,
    group_col
):

    comments = []

    if result_df.empty:

        return [
            "비교할 데이터가 없습니다."
        ]

    df_comment = result_df.copy()

    # --------------------------------------------------------
    # 전체
    # --------------------------------------------------------

    total_current_spend = (
        df_comment[
            "spend_current"
        ].sum()
    )

    total_previous_spend = (
        df_comment[
            "spend_previous"
        ].sum()
    )

    total_current_click = (
        df_comment[
            "click_current"
        ].sum()
    )

    total_previous_click = (
        df_comment[
            "click_previous"
        ].sum()
    )

    total_current_conv = (
        df_comment[
            "conversion_current"
        ].sum()
    )

    total_previous_conv = (
        df_comment[
            "conversion_previous"
        ].sum()
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

    total_conv_change = (
        (
            total_current_conv -
            total_previous_conv
        )
        /
        total_previous_conv
        *
        100
        if total_previous_conv > 0
        else np.nan
    )

    total_cpa_change = (
        (
            total_current_cpa -
            total_previous_cpa
        )
        /
        total_previous_cpa
        *
        100
        if (
            pd.notna(
                total_previous_cpa
            )
            and
            total_previous_cpa > 0
        )
        else np.nan
    )

    total_spend_change = (
        (
            total_current_spend -
            total_previous_spend
        )
        /
        total_previous_spend
        *
        100
        if total_previous_spend > 0
        else np.nan
    )

    total_click_change = (
        (
            total_current_click -
            total_previous_click
        )
        /
        total_previous_click
        *
        100
        if total_previous_click > 0
        else np.nan
    )

    total_cvr_point_change = (
        total_current_cvr -
        total_previous_cvr
        if (
            pd.notna(
                total_current_cvr
            )
            and
            pd.notna(
                total_previous_cvr
            )
        )
        else np.nan
    )

    # --------------------------------------------------------
    # 전체 요약
    # --------------------------------------------------------

    comments.append(
        "### 📊 전체 성과 요약"
    )

    if pd.notna(
        total_spend_change
    ):

        comments.append(
            f"- 광고비: "
            f"**{total_current_spend:,.0f}원** "
            f"({total_spend_change:+.1f}%)"
        )

    if pd.notna(
        total_click_change
    ):

        comments.append(
            f"- 클릭: "
            f"**{total_current_click:,.0f}회** "
            f"({total_click_change:+.1f}%)"
        )

    if pd.notna(
        total_conv_change
    ):

        comments.append(
            f"- DB: "
            f"**{total_current_conv:,.0f}건** "
            f"({total_conv_change:+.1f}%)"
        )

    if pd.notna(
        total_cpa_change
    ):

        if total_cpa_change < 0:

            comments.append(
                f"- CPA: "
                f"**{total_current_cpa:,.0f}원** "
                f"({total_cpa_change:+.1f}%) "
                f"→ **효율 개선**"
            )

        else:

            comments.append(
                f"- CPA: "
                f"**{total_current_cpa:,.0f}원** "
                f"({total_cpa_change:+.1f}%) "
                f"→ **효율 악화**"
            )

    if pd.notna(
        total_cvr_point_change
    ):

        comments.append(
            f"- CVR: "
            f"**{total_current_cvr:.2f}%** "
            f"(전기 대비 "
            f"{total_cvr_point_change:+.2f}%p)"
        )

    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

    valid_cpa = df_comment[
        df_comment[
            "CPA_current"
        ].notna()
        &
        (
            df_comment[
                "conversion_current"
            ] > 0
        )
    ]

    if not valid_cpa.empty:

        best_cpa = valid_cpa.loc[
            valid_cpa[
                "CPA_current"
            ].idxmin()
        ]

        comments.append(
            f"🏆 **CPA 최우수:** "
            f"`{best_cpa[group_col]}` "
            f"({best_cpa['CPA_current']:,.0f}원)"
        )

    # --------------------------------------------------------
    # 전환 최다
    # --------------------------------------------------------

    valid_conv = df_comment[
        df_comment[
            "conversion_current"
        ] > 0
    ]

    if not valid_conv.empty:

        best_conv = valid_conv.loc[
            valid_conv[
                "conversion_current"
            ].idxmax()
        ]

        comments.append(
            f"📈 **DB 최다:** "
            f"`{best_conv[group_col]}` "
            f"({best_conv['conversion_current']:,.0f}건)"
        )

    # --------------------------------------------------------
    # 전환 증가
    # --------------------------------------------------------

    valid_growth = df_comment[
        df_comment[
            "conversion_change"
        ].notna()
    ]

    if not valid_growth.empty:

        growth = valid_growth.loc[
            valid_growth[
                "conversion_change"
            ].idxmax()
        ]

        if (
            growth[
                "conversion_change"
            ] > 0
        ):

            comments.append(
                f"🚀 **DB 증가폭 최대:** "
                f"`{growth[group_col]}` "
                f"({growth['conversion_change']:+,.1f}%)"
            )

    # --------------------------------------------------------
    # CPA 악화
    # --------------------------------------------------------

    valid_cpa_change = df_comment[
        df_comment[
            "CPA_change"
        ].notna()
    ]

    if not valid_cpa_change.empty:

        worst_cpa = valid_cpa_change.loc[
            valid_cpa_change[
                "CPA_change"
            ].idxmax()
        ]

        if (
            worst_cpa[
                "CPA_change"
            ] > 0
        ):

            comments.append(
                f"⚠️ **CPA 악화 주의:** "
                f"`{worst_cpa[group_col]}` "
                f"({worst_cpa['CPA_change']:+,.1f}%)"
            )

    # --------------------------------------------------------
    # 개별 분석
    # --------------------------------------------------------

    comments.append("")
    comments.append(
        "### 🔎 주요 변화"
    )

    for _, row in df_comment.iterrows():

        target = str(
            row[group_col]
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
        # 볼륨 + 효율 개선
        # ----------------------------------------------------

        if (
            pd.notna(conv_change)
            and conv_change > 10
            and pd.notna(cpa_change)
            and cpa_change < -10
        ):

            comments.append(
                f"- **{target}**: "
                f"DB {conv_change:+.1f}% / "
                f"CPA {cpa_change:+.1f}% "
                f"→ **볼륨과 효율이 동시에 개선**"
            )

        # ----------------------------------------------------
        # 볼륨 증가 + CPA 악화
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change > 10
            and pd.notna(cpa_change)
            and cpa_change > 10
        ):

            comments.append(
                f"- **{target}**: "
                f"DB는 {conv_change:+.1f}% 증가했지만 "
                f"CPA도 {cpa_change:+.1f}% 상승 "
                f"→ **확장에 따른 효율 악화 확인 필요**"
            )

        # ----------------------------------------------------
        # 볼륨 감소 + CPA 악화
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change < -10
            and pd.notna(cpa_change)
            and cpa_change > 10
        ):

            comments.append(
                f"- **{target}**: "
                f"DB {conv_change:+.1f}% / "
                f"CPA {cpa_change:+.1f}% "
                f"→ **우선 점검 필요**"
            )

        # ----------------------------------------------------
        # DB 감소
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change < -10
        ):

            comments.append(
                f"- **{target}**: "
                f"DB가 {conv_change:+.1f}% 감소 "
                f"→ 광고비·클릭·CVR 변화 확인 필요"
            )

        # ----------------------------------------------------
        # DB 증가
        # ----------------------------------------------------

        elif (
            pd.notna(conv_change)
            and conv_change > 10
        ):

            comments.append(
                f"- **{target}**: "
                f"DB가 {conv_change:+.1f}% 증가 "
                f"→ 현재 볼륨 확대 효과 확인"
            )

        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

        if (
            pd.notna(cvr_change)
            and cvr_change > 10
        ):

            comments.append(
                f"  - CVR "
                f"{cvr_change:+.1f}% 개선"
            )

        elif (
            pd.notna(cvr_change)
            and cvr_change < -10
        ):

            comments.append(
                f"  - CVR "
                f"{cvr_change:+.1f}% 하락 "
                f"→ 랜딩페이지/타겟/소재 점검"
            )

    return comments


comments = make_performance_comments(
    comparison,
    "media"
)


for comment in comments:

    st.markdown(comment)


# ============================================================
# 31. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "현재 선택된 매체/캠페인의 세부 성과를 비교합니다."
)


campaign_current = aggregate_by_campaign(
    current_df
)

campaign_previous = aggregate_by_campaign(
    previous_df
)


campaign_comparison = create_comparison(
    campaign_current,
    campaign_previous,
    "campaign"
)


campaign_table = campaign_comparison[
    campaign_comparison[
        "campaign"
    ].isin(
        selected_campaigns
    )
].copy()


campaign_table = campaign_table.sort_values(
    "conversion_current",
    ascending=False
)


# ============================================================
# 32. 캠페인 비교표
# ============================================================

st.markdown(
    build_comparison_html(
        campaign_table,
        "campaign",
        "campaign-table"
    ),
    unsafe_allow_html=True
)


# ============================================================
# 33. 캠페인 코멘트
# ============================================================

st.subheader(
    "📝 캠페인 성과 코멘트"
)


campaign_comments = make_performance_comments(
    campaign_table,
    "campaign"
)


for comment in campaign_comments:

    st.markdown(comment)


# ============================================================
# 34. ChatGPT 분석 데이터
# ============================================================

def build_ai_data():

    rows = []

    for _, row in comparison.iterrows():

        rows.append(
            {
                "매체":
                    str(row["media"]),

                "기준 광고비":
                    float(
                        row[
                            "spend_current"
                        ]
                    ),

                "비교 광고비":
                    float(
                        row[
                            "spend_previous"
                        ]
                    ),

                "기준 클릭":
                    float(
                        row[
                            "click_current"
                        ]
                    ),

                "비교 클릭":
                    float(
                        row[
                            "click_previous"
                        ]
                    ),

                "기준 DB":
                    float(
                        row[
                            "conversion_current"
                        ]
                    ),

                "비교 DB":
                    float(
                        row[
                            "conversion_previous"
                        ]
                    ),

                "기준 CPA":
                    (
                        None
                        if pd.isna(
                            row[
                                "CPA_current"
                            ]
                        )
                        else float(
                            row[
                                "CPA_current"
                            ]
                        )
                    ),

                "비교 CPA":
                    (
                        None
                        if pd.isna(
                            row[
                                "CPA_previous"
                            ]
                        )
                        else float(
                            row[
                                "CPA_previous"
                            ]
                        )
                    ),

                "기준 CVR":
                    (
                        None
                        if pd.isna(
                            row[
                                "CVR_current"
                            ]
                        )
                        else float(
                            row[
                                "CVR_current"
                            ]
                        )
                    ),

                "비교 CVR":
                    (
                        None
                        if pd.isna(
                            row[
                                "CVR_previous"
                            ]
                        )
                        else float(
                            row[
                                "CVR_previous"
                            ]
                        )
                    ),

                "광고비 변화율":
                    (
                        None
                        if pd.isna(
                            row[
                                "spend_change"
                            ]
                        )
                        else float(
                            row[
                                "spend_change"
                            ]
                        )
                    ),

                "클릭 변화율":
                    (
                        None
                        if pd.isna(
                            row[
                                "click_change"
                            ]
                        )
                        else float(
                            row[
                                "click_change"
                            ]
                        )
                    ),

                "DB 변화율":
                    (
                        None
                        if pd.isna(
                            row[
                                "conversion_change"
                            ]
                        )
                        else float(
                            row[
                                "conversion_change"
                            ]
                        )
                    ),

                "CPA 변화율":
                    (
                        None
                        if pd.isna(
                            row[
                                "CPA_change"
                            ]
                        )
                        else float(
                            row[
                                "CPA_change"
                            ]
                        )
                    ),

                "CVR 변화율":
                    (
                        None
                        if pd.isna(
                            row[
                                "CVR_change"
                            ]
                        )
                        else float(
                            row[
                                "CVR_change"
                            ]
                        )
                    ),

                "CVR 변화폭":
                    (
                        None
                        if pd.isna(
                            row[
                                "CVR_point_change"
                            ]
                        )
                        else float(
                            row[
                                "CVR_point_change"
                            ]
                        )
                    )
            }
        )

    return rows


# ============================================================
# 35. ChatGPT 분석
# ============================================================

def ask_chatgpt():

    client = get_openai_client()

    if client is None:

        return (
            "⚠️ OpenAI API Key가 연결되지 않았습니다.\n\n"
            "Streamlit Cloud → Settings → Secrets에서 "
            "`OPENAI_API_KEY`를 등록해주세요."
        )

    ai_data = build_ai_data()

    prompt = f"""
너는 10년차 퍼포먼스 마케팅 데이터 분석가다.

광고 성과 데이터를 보고
팀장에게 보고하는 수준으로 분석해라.

==================================================
[분석 기간]
==================================================

기준 기간:
{current_period_text}

비교 기간:
{previous_period_text}

비교 유형:
{period_type}

==================================================
[선택 조건]
==================================================

선택 매체:
{selected_media}

선택 캠페인:
{selected_campaigns}

==================================================
[데이터]
==================================================

{ai_data}


==================================================
[중요한 분석 원칙]
==================================================

1. 광고비 → 클릭 → CVR → DB → CPA 순서로 생각한다.

2. 단순히 숫자를 나열하지 않는다.

3. 데이터에서 직접 확인할 수 없는 원인은
확정적으로 말하지 않는다.

예:
"랜딩페이지가 문제다" ❌

"CVR 하락이 확인되므로 랜딩페이지/소재/타겟 변화 여부를 확인할 필요가 있다" ⭕

4. CPA는 낮을수록 좋다.

5. DB는 많을수록 좋지만,
광고비가 크게 증가해서 DB가 증가한 경우
효율까지 함께 판단한다.

6. CVR 변화는 반드시
"변화율 %"와 "변화폭 %p"를 구분한다.

7. 예산 확대 때문에 CPA가 악화된 경우와
클릭 또는 CVR 문제가 발생한 경우를 구분해서 추론한다.


==================================================
[분석 구조]
==================================================

### 1. 전체 성과 요약

다음 내용을 반드시 포함한다.

- 광고비 변화
- 클릭 변화
- DB 변화
- CPA 변화
- CVR 변화

그리고 가장 중요한 성과 변화 2~3개를 설명한다.


### 2. 잘하고 있는 매체

현재 기준에서 성과가 좋은 매체를 선정한다.

각 매체별로:

- DB
- CPA
- CVR
- 광고비

를 근거로 설명한다.

"좋다"라고만 하지 말고 숫자를 사용한다.


### 3. 성과가 낮아진 매체

문제가 있는 매체를 선정한다.

다음 순서로 분석한다.

광고비
↓
클릭
↓
CVR
↓
DB
↓
CPA

어느 단계에서 문제가 발생했을 가능성이 높은지 설명한다.


### 4. 원인 추론

가능한 원인을 데이터 기반으로 추론한다.

예:

광고비 ↑
클릭 ↑
CVR ↓
DB ↓
CPA ↑

라면

"예산 확대 자체보다 클릭 이후 CVR 저하가
CPA 악화에 영향을 줬을 가능성이 높다."

와 같이 설명한다.

단, 데이터에 없는 사실은 확정하지 않는다.


### 5. 매체별 액션

각 매체에 대해 다음 중 하나를 판단한다.

- 확대
- 유지
- 관찰
- 축소 검토

그리고 반드시 숫자로 근거를 설명한다.


### 6. 실행 전략

실제 퍼포먼스 마케팅 담당자가 바로 실행할 수 있도록
우선순위 순으로 최대 5개를 제안한다.

예:

1. CPA가 높은 캠페인 예산 20% 감액
2. CPA가 낮고 DB 증가가 확인된 캠페인 예산 10~20% 확대
3. CVR 하락 매체의 랜딩페이지/소재별 CVR 분해
4. 저효율 소재 교체
5. 타겟/입찰 전략 점검


### 7. 최우선 액션

현재 데이터만 보고
가장 먼저 해야 할 액션 하나만 선정한다.

형식:

**🎯 최우선 액션**
→ 내용


### 8. 팀장 보고용 한 줄 결론

전체 상황을 한 문장으로 요약한다.

숫자를 반드시 포함한다.
"""


    try:

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return response.output_text

    except Exception as e:

        return (
            "❌ ChatGPT 분석 중 오류가 발생했습니다.\n\n"
            f"오류 내용: {e}"
        )


# ============================================================
# 36. ChatGPT 버튼
# ============================================================

st.divider()

st.header(
    "🤖 ChatGPT 성과 해석 · 추론 · 전략"
)

st.caption(
    "현재 선택한 기간과 매체/캠페인 데이터를 "
    "기반으로 성과 원인과 실행 전략을 분석합니다."
)


if st.button(
    "🤖 ChatGPT로 성과 분석하기",
    type="primary",
    use_container_width=True
):

    with st.spinner(
        "성과 데이터를 분석하고 있습니다..."
    ):

        ai_result = ask_chatgpt()

    st.markdown(
        ai_result
    )


# ============================================================
# 37. 데이터 정보
# ============================================================

st.divider()

with st.expander(
    "📌 데이터 정보"
):

    st.write(
        f"전체 데이터: "
        f"{len(df):,}건"
    )

    st.write(
        f"분석 데이터: "
        f"{len(filtered_df):,}건"
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
        f"실제 성과 최신일: "
        f"{latest_performance_date.strftime('%Y-%m-%d')}"
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
