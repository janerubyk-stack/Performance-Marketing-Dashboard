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
# 3. Google Sheets 데이터 불러오기
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

    print("=" * 70)
    print("Google Sheets 데이터 불러오기 완료")
    print("데이터 건수:", f"{len(df):,}")
    print("실제 컬럼명:", df.columns.tolist())
    print("=" * 70)

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
    # 표준 컬럼명
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

    df["media"] = (
        df["media"]
        .fillna("미분류")
        .astype(str)
        .str.strip()
    )

    df["campaign"] = (
        df["campaign"]
        .fillna("미분류")
        .astype(str)
        .str.strip()
    )

    df.loc[df["media"] == "", "media"] = "미분류"
    df.loc[df["campaign"] == "", "campaign"] = "미분류"

    # --------------------------------------------------------
    # 날짜 없는 데이터 제거
    # --------------------------------------------------------

    df = df.dropna(
        subset=["date"]
    ).copy()

    df["date"] = df["date"].dt.normalize()

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

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
    custom_start=None,
    custom_end=None
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

        if custom_start is None or custom_end is None:

            raise ValueError(
                "지정 기간의 시작일과 종료일이 필요합니다."
            )

        current_start = pd.Timestamp(custom_start)
        current_end = pd.Timestamp(custom_end)

        elapsed_days = (
            current_end -
            current_start
        ).days

        previous_end = (
            current_start -
            timedelta(days=1)
        )

        previous_start = (
            previous_end -
            timedelta(days=elapsed_days)
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
# 6. 기간 문자열
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

def aggregate_performance(
    data,
    start_date,
    end_date
):

    temp = data[
        (data["date"] >= start_date) &
        (data["date"] <= end_date)
    ].copy()

    result = (
        temp
        .groupby(
            ["media", "campaign"],
            as_index=False
        )
        .agg(
            impress=("impress", "sum"),
            click=("click", "sum"),
            spend=("spend", "sum"),
            conversion=("conversion", "sum")
        )
    )

    if result.empty:
        return result

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
# 8. 기간 필터 UI
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(
    [1, 1.5, 2]
)

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
# 9. 지정 기간
# ============================================================

custom_start = None
custom_end = None

if period_type == "지정":

    custom_col1, custom_col2 = st.columns(2)

    with custom_col1:

        custom_start = st.date_input(
            "비교 기준기간 시작일",
            value=base_date,
            min_value=min_date,
            max_value=max_date,
            key="custom_start"
        )

    with custom_col2:

        custom_end = st.date_input(
            "비교 기준기간 종료일",
            value=base_date,
            min_value=min_date,
            max_value=max_date,
            key="custom_end"
        )

    if custom_start > custom_end:

        st.error(
            "시작일은 종료일보다 빠르거나 같아야 합니다."
        )

        st.stop()


# ============================================================
# 10. 기간 계산
# ============================================================

(
    current_start,
    current_end,
    previous_start,
    previous_end
) = get_periods(
    base_date,
    period_type,
    custom_start,
    custom_end
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
        f"""
**기준 기간:** {current_period_text}

**비교 기간:** {previous_period_text}

**동일 진행일수:** {elapsed_days}일
"""
    )


# ============================================================
# 11. 매체 / 캠페인 필터
# ============================================================

media_options = sorted(
    df["media"].dropna().unique().tolist()
)

campaign_options = sorted(
    df["campaign"].dropna().unique().tolist()
)

filter_col1, filter_col2 = st.columns(2)


with filter_col1:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_options,
        default=media_options,
        key="media_filter"
    )


with filter_col2:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=campaign_options,
        default=campaign_options,
        key="campaign_filter"
    )


# ============================================================
# 12. 전체 선택
# ============================================================

button_col1, button_col2, button_col3 = st.columns(
    [1, 1, 4]
)


with button_col1:

    if st.button(
        "📌 매체 전체 선택",
        use_container_width=True
    ):

        st.session_state["media_filter"] = media_options

        st.rerun()


with button_col2:

    if st.button(
        "📌 캠페인 전체 선택",
        use_container_width=True
    ):

        st.session_state["campaign_filter"] = campaign_options

        st.rerun()


# ============================================================
# 13. 필터 데이터
# ============================================================

filtered_df = df[
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
# 15. 매체 집계
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
# 16. 비교 데이터 생성
# ============================================================

def create_comparison(
    current,
    previous,
    group_col
):

    current = current.copy()
    previous = previous.copy()

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

            "spend_current": c_spend,
            "spend_previous": p_spend,

            "conversion_current": c_conversion,
            "conversion_previous": p_conversion,

            "CPA_current": c_cpa,
            "CPA_previous": p_cpa,

            "CVR_current": c_cvr,
            "CVR_previous": p_cvr
        })

    result = pd.DataFrame(rows)

    if result.empty:
        return result

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
# 17. 성과 추이 데이터
# ============================================================

def create_trend_data(
    data,
    start_date,
    end_date,
    granularity
):

    temp = data[
        (data["date"] >= start_date) &
        (data["date"] <= end_date)
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    if granularity == "일자별":

        temp["period"] = temp["date"]

    elif granularity == "주차별":

        temp["period"] = (
            temp["date"]
            - pd.to_timedelta(
                temp["date"].dt.weekday,
                unit="D"
            )
        )

    elif granularity == "월별":

        temp["period"] = (
            temp["date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )

    result = (
        temp
        .groupby("period", as_index=False)
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

    return result.sort_values(
        "period"
    )


# ============================================================
# 18. 성과 추이 차트
# ============================================================

st.divider()

st.header("📈 성과 추이")

st.caption(
    "선택한 기준기간의 성과 흐름을 일자별·주차별·월별로 확인합니다. "
    "CPA는 막대, 전환수는 꺾은선으로 표시됩니다."
)


trend_tabs = st.tabs([
    "📅 일자별",
    "📆 주차별",
    "🗓️ 월별"
])


def draw_trend_chart(
    trend_df,
    title
):

    if trend_df.empty:

        st.info(
            "선택한 기간에 데이터가 없습니다."
        )

        return

    x = trend_df["period"]

    labels = []

    for value in x:

        timestamp = pd.Timestamp(value)

        if title == "일자별":

            labels.append(
                timestamp.strftime("%m/%d")
            )

        elif title == "주차별":

            labels.append(
                timestamp.strftime("%m/%d")
                + " 주"
            )

        else:

            labels.append(
                timestamp.strftime("%Y-%m")
            )

    fig = go.Figure()

    # CPA 막대
    fig.add_trace(
        go.Bar(
            x=labels,
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

    # 전환수 꺾은선
    fig.add_trace(
        go.Scatter(
            x=labels,
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
            f"{title} CPA + 전환수"
            f"<br><sup>"
            f"{current_period_text}"
            f"</sup>"
        ),

        height=400,

        margin=dict(
            l=60,
            r=60,
            t=85,
            b=70
        ),

        xaxis=dict(
            title="기간",
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


with trend_tabs[0]:

    daily_trend = create_trend_data(
        filtered_df,
        current_start,
        current_end,
        "일자별"
    )

    draw_trend_chart(
        daily_trend,
        "일자별"
    )


with trend_tabs[1]:

    weekly_trend = create_trend_data(
        filtered_df,
        current_start,
        current_end,
        "주차별"
    )

    draw_trend_chart(
        weekly_trend,
        "주차별"
    )


with trend_tabs[2]:

    monthly_trend = create_trend_data(
        filtered_df,
        current_start,
        current_end,
        "월별"
    )

    draw_trend_chart(
        monthly_trend,
        "월별"
    )


# ============================================================
# 19. 성과 비교
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text}  |  "
    f"비교 기간: {previous_period_text}  |  "
    f"동일 진행일수: {elapsed_days}일"
)


# ============================================================
# 20. 매체 비교 차트
# ============================================================

chart_df = comparison[
    comparison["media"].isin(selected_media)
].copy()

chart_df = chart_df.sort_values(
    "conversion_current",
    ascending=False
)

x_labels = chart_df["media"].tolist()


# ------------------------------------------------------------
# CPA
# ------------------------------------------------------------

fig_cpa = go.Figure()

fig_cpa.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["CPA_current"],
        name="기준 CPA",
        text=[
            f"{v:,.0f}원"
            if pd.notna(v)
            else "-"
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
            f"{v:,.0f}원"
            if pd.notna(v)
            else "-"
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

    title=(
        "CPA + 전환수"
        f"<br><sup>"
        f"기준 {current_period_text}"
        f" vs "
        f"비교 {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=420,

    margin=dict(
        l=55,
        r=65,
        t=90,
        b=120
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


# ------------------------------------------------------------
# 광고비
# ------------------------------------------------------------

fig_spend = go.Figure()

fig_spend.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["spend_current"],
        name="기준 광고비",
        text=[
            f"{v:,.0f}원"
            if pd.notna(v)
            else "-"
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
            f"{v:,.0f}원"
            if pd.notna(v)
            else "-"
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

    title=(
        "광고비 + 전환수"
        f"<br><sup>"
        f"기준 {current_period_text}"
        f" vs "
        f"비교 {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=420,

    margin=dict(
        l=55,
        r=65,
        t=90,
        b=120
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
# 21. 매체 상세 비교
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "매체를 가로로 배치하고 성과 지표를 세로로 비교합니다."
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
# 22. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "어떤 매체의 어떤 캠페인에서 성과가 개선·악화되었는지 확인합니다."
)


# ============================================================
# 23. 캠페인 비교 데이터
# ============================================================

campaign_comparison = create_comparison(
    current_df,
    previous_df,
    "campaign"
)


# 매체 정보 다시 붙이기
campaign_media_current = (
    current_df
    .groupby(
        ["campaign", "media"],
        as_index=False
    )
    .agg(
        spend=("spend", "sum"),
        conversion=("conversion", "sum")
    )
)


campaign_media_previous = (
    previous_df
    .groupby(
        ["campaign", "media"],
        as_index=False
    )
    .agg(
        spend=("spend", "sum"),
        conversion=("conversion", "sum")
    )
)


# ============================================================
# 24. 캠페인 + 매체 기준으로 정확하게 비교
# ============================================================

def create_campaign_media_comparison(
    current_data,
    previous_data
):

    current = (
        current_data
        .groupby(
            ["media", "campaign"],
            as_index=False
        )
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )

    previous = (
        previous_data
        .groupby(
            ["media", "campaign"],
            as_index=False
        )
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )

    keys = (
        pd.concat(
            [
                current[["media", "campaign"]],
                previous[["media", "campaign"]]
            ]
        )
        .drop_duplicates()
        .reset_index(drop=True)
    )

    result = keys.copy()

    result = result.merge(
        current,
        on=["media", "campaign"],
        how="left",
        suffixes=("", "_current")
    )

    result = result.rename(
        columns={
            "spend": "spend_current",
            "click": "click_current",
            "conversion": "conversion_current"
        }
    )

    result = result.merge(
        previous,
        on=["media", "campaign"],
        how="left",
        suffixes=("", "_previous")
    )

    result = result.rename(
        columns={
            "spend": "spend_previous",
            "click": "click_previous",
            "conversion": "conversion_previous"
        }
    )

    for col in [
        "spend_current",
        "click_current",
        "conversion_current",
        "spend_previous",
        "click_previous",
        "conversion_previous"
    ]:

        result[col] = result[col].fillna(0)

    # CPA
    result["CPA_current"] = np.where(
        result["conversion_current"] > 0,
        result["spend_current"] /
        result["conversion_current"],
        np.nan
    )

    result["CPA_previous"] = np.where(
        result["conversion_previous"] > 0,
        result["spend_previous"] /
        result["conversion_previous"],
        np.nan
    )

    # CVR
    result["CVR_current"] = np.where(
        result["click_current"] > 0,
        result["conversion_current"] /
        result["click_current"] *
        100,
        np.nan
    )

    result["CVR_previous"] = np.where(
        result["click_previous"] > 0,
        result["conversion_previous"] /
        result["click_previous"] *
        100,
        np.nan
    )

    def change_rate(c, p):

        if pd.isna(p) or p == 0:
            return np.nan

        return (
            (c - p) /
            p *
            100
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


campaign_table = create_campaign_media_comparison(
    current_df,
    previous_df
)


campaign_table = campaign_table[
    campaign_table["media"].isin(selected_media) &
    campaign_table["campaign"].isin(selected_campaigns)
].copy()


campaign_table = campaign_table.sort_values(
    [
        "conversion_current",
        "media"
    ],
    ascending=[
        False,
        True
    ]
)


# ============================================================
# 25. 분석 대상 Type
# ============================================================

analysis_type = st.radio(
    "분석 대상 Type",
    [
        "전체",
        "매체",
        "캠페인"
    ],
    horizontal=True,
    key="analysis_type"
)


# ============================================================
# 26. 주요 변화
# ============================================================

st.subheader("🔎 주요 변화")


def format_change(value):

    if pd.isna(value):
        return "-"

    return f"{value:+,.1f}%"


if analysis_type in ["전체", "캠페인"]:

    valid = campaign_table[
        campaign_table["conversion_current"] > 0
    ].copy()

    # --------------------------------------------------------
    # 성과 개선
    # --------------------------------------------------------

    if not valid.empty:

        improved = valid[
            (
                valid["conversion_change"] > 10
            ) &
            (
                valid["CPA_change"] < -10
            )
        ].copy()

        if not improved.empty:

            improved = improved.sort_values(
                "conversion_change",
                ascending=False
            )

            st.markdown("### 🚀 볼륨 + 효율 동시 개선")

            for _, row in improved.head(10).iterrows():

                st.markdown(
                    f"- **Type: 캠페인 | "
                    f"매체: {row['media']} | "
                    f"분석대상: {row['campaign']}**  \n"
                    f"  전환수 "
                    f"**{format_change(row['conversion_change'])}** / "
                    f"CPA "
                    f"**{format_change(row['CPA_change'])}**"
                )

        # ----------------------------------------------------
        # 전환 증가
        # ----------------------------------------------------

        volume_up = valid[
            valid["conversion_change"] > 10
        ].sort_values(
            "conversion_change",
            ascending=False
        )

        if not volume_up.empty:

            st.markdown("### 📈 전환 증가")

            for _, row in volume_up.head(10).iterrows():

                st.markdown(
                    f"- **Type: 캠페인 | "
                    f"매체: {row['media']} | "
                    f"분석대상: {row['campaign']}**  \n"
                    f"  전환수 "
                    f"**{format_change(row['conversion_change'])}**"
                )

        # ----------------------------------------------------
        # CPA 개선
        # ----------------------------------------------------

        cpa_up = valid[
            valid["CPA_change"].notna() &
            (valid["CPA_change"] < -10)
        ].sort_values(
            "CPA_change"
        )

        if not cpa_up.empty:

            st.markdown("### 💰 CPA 개선")

            for _, row in cpa_up.head(10).iterrows():

                st.markdown(
                    f"- **Type: 캠페인 | "
                    f"매체: {row['media']} | "
                    f"분석대상: {row['campaign']}**  \n"
                    f"  CPA "
                    f"**{format_change(row['CPA_change'])}**"
                )

        # ----------------------------------------------------
        # 악화
        # ----------------------------------------------------

        worsened = valid[
            (
                valid["conversion_change"] < -10
            ) |
            (
                valid["CPA_change"] > 10
            )
        ].copy()

        if not worsened.empty:

            worsened = worsened.sort_values(
                "CPA_change",
                ascending=False
            )

            st.markdown("### ⚠️ 점검 필요")

            for _, row in worsened.head(10).iterrows():

                st.markdown(
                    f"- **Type: 캠페인 | "
                    f"매체: {row['media']} | "
                    f"분석대상: {row['campaign']}**  \n"
                    f"  전환수 "
                    f"**{format_change(row['conversion_change'])}** / "
                    f"CPA "
                    f"**{format_change(row['CPA_change'])}**"
                )


# ============================================================
# 27. 캠페인 상세 비교표
# ============================================================

st.subheader("📋 캠페인 상세 비교")


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

.campaign-detail-table {

    width: 100%;
    border-collapse: collapse;
    font-size: 13px;

}

.campaign-detail-table th,
.campaign-detail-table td {

    border: 1px solid #dddddd;
    padding: 9px;
    text-align: center;
    white-space: nowrap;

}

.campaign-detail-table th {

    background-color: #f5f5f5;
    font-weight: 700;

}

.campaign-detail-table td.metric {

    text-align: left;
    font-weight: 700;
    background-color: #fafafa;

}

.campaign-name {

    font-weight: 700;

}

.media-name {

    color: #777777;
    font-size: 12px;

}

.up {

    color: #d62728;
    font-weight: 700;

}

.down {

    color: #2468c7;
    font-weight: 700;

}

</style>

<table class="campaign-detail-table">

<tr>

<th>Type</th>
<th>매체</th>
<th>캠페인</th>
"""


for (
    metric_name,
    current_col,
    previous_col,
    change_col,
    fmt_type
) in campaign_metric_rows:

    pass


# 세로형 테이블로 변경
campaign_html = """

<style>

.campaign-detail-table {

    width: 100%;
    border-collapse: collapse;
    font-size: 13px;

}

.campaign-detail-table th,
.campaign-detail-table td {

    border: 1px solid #dddddd;
    padding: 9px 10px;
    text-align: center;
    white-space: nowrap;

}

.campaign-detail-table th {

    background-color: #f5f5f5;
    font-weight: 700;

}

.campaign-detail-table td.left {

    text-align: left;

}

.up {

    color: #d62728;
    font-weight: 700;

}

.down {

    color: #2468c7;
    font-weight: 700;

}

</style>

<table class="campaign-detail-table">

<tr>
<th>Type</th>
<th>매체</th>
<th>캠페인</th>
<th>지표</th>
<th>기준</th>
<th>비교</th>
<th>변화율</th>
</tr>
"""


for _, row in campaign_table.iterrows():

    for (
        metric_name,
        current_col,
        previous_col,
        change_col,
        fmt_type
    ) in campaign_metric_rows:

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

        <tr>

        <td>캠페인</td>

        <td class="left">
        {html.escape(str(row["media"]))}
        </td>

        <td class="left">
        <b>{html.escape(str(row["campaign"]))}</b>
        </td>

        <td>
        {metric_name}
        </td>

        <td>
        <b>{current_text}</b>
        </td>

        <td>
        {previous_text}
        </td>

        <td>
        {change_html}
        </td>

        </tr>

        """


campaign_html += """

</table>

"""


if campaign_table.empty:

    st.info(
        "선택한 조건에 해당하는 캠페인 데이터가 없습니다."
    )

else:

    st.markdown(
        campaign_html,
        unsafe_allow_html=True
    )


# ============================================================
# 28. 캠페인 성과 하이라이트
# ============================================================

st.subheader("🏆 캠페인 성과 하이라이트")


valid_campaigns = campaign_table[
    campaign_table["conversion_current"] > 0
].copy()


if not valid_campaigns.empty:

    col1, col2, col3, col4 = st.columns(4)

    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

    cpa_valid = valid_campaigns[
        valid_campaigns["CPA_current"].notna()
    ]

    if not cpa_valid.empty:

        best_cpa = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmin()
        ]

        with col1:

            st.metric(
                "🏆 CPA 최우수",
                f"{best_cpa['CPA_current']:,.0f}원",
                f"{best_cpa['campaign']}"
            )

    # --------------------------------------------------------
    # 전환 최다
    # --------------------------------------------------------

    best_conversion = valid_campaigns.loc[
        valid_campaigns["conversion_current"].idxmax()
    ]

    with col2:

        st.metric(
            "📈 전환수 최다",
            f"{best_conversion['conversion_current']:,.0f}건",
            f"{best_conversion['campaign']}"
        )

    # --------------------------------------------------------
    # 전환 증가 최대
    # --------------------------------------------------------

    conversion_growth = campaign_table[
        campaign_table["conversion_change"].notna()
    ]

    if not conversion_growth.empty:

        best_growth = conversion_growth.loc[
            conversion_growth["conversion_change"].idxmax()
        ]

        with col3:

            st.metric(
                "🚀 전환 증가폭 최대",
                f"{best_growth['conversion_change']:+,.1f}%",
                f"{best_growth['campaign']}"
            )

    # --------------------------------------------------------
    # CPA 악화 최대
    # --------------------------------------------------------

    cpa_worst = campaign_table[
        campaign_table["CPA_change"].notna()
    ]

    if not cpa_worst.empty:

        worst_cpa = cpa_worst.loc[
            cpa_worst["CPA_change"].idxmax()
        ]

        with col4:

            st.metric(
                "⚠️ CPA 악화 최대",
                f"{worst_cpa['CPA_change']:+,.1f}%",
                f"{worst_cpa['campaign']}"
            )


else:

    st.info(
        "현재 기간에 전환이 발생한 캠페인이 없습니다."
    )


# ============================================================
# 29. 데이터 정보
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
