import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from openai import OpenAI
from io import StringIO
from datetime import timedelta, date
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
# OpenAI 설정
# ============================================================

def get_openai_client():

    if "OPENAI_API_KEY" not in st.secrets:
        return None

    return OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
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
st.caption("Performance Marketing Data Dashboard")

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

    # 문자열
    for col in ["media", "campaign"]:

        df[col] = (
            df[col]
            .fillna("미분류")
            .astype(str)
            .str.strip()
        )

        df.loc[
            df[col].isin(["", "nan", "None", "<NA>"]),
            col
        ] = "미분류"

    df = df.dropna(
        subset=["date"]
    ).copy()

    df["date"] = df["date"].dt.normalize()

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    return df


try:

    df = load_data()

except Exception as e:

    st.error(
        "Google Sheets 데이터를 불러오지 못했습니다."
    )

    st.exception(e)

    st.stop()


if df.empty:

    st.warning("데이터가 없습니다.")

    st.stop()


# ============================================================
# 4. 기간 계산
# ============================================================

def get_periods(base_date, period_type):

    base_date = pd.Timestamp(base_date)

    if period_type == "전일":

        current_start = base_date
        current_end = base_date

        previous_start = base_date - timedelta(days=1)
        previous_end = base_date - timedelta(days=1)

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


def format_period(start_date, end_date):

    return (
        f"{start_date.strftime('%Y-%m-%d')}"
        f" ~ "
        f"{end_date.strftime('%Y-%m-%d')}"
    )


# ============================================================
# 5. 성과 집계
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


# ============================================================
# 6. 비교 데이터
# ============================================================

def create_comparison(
    current,
    previous,
    group_col
):

    current = current.copy()
    previous = previous.copy()

    if current.empty and previous.empty:

        return pd.DataFrame(
            columns=[
                group_col,
                "spend_current",
                "spend_previous",
                "conversion_current",
                "conversion_previous",
                "CPA_current",
                "CPA_previous",
                "CVR_current",
                "CVR_previous",
                "spend_change",
                "conversion_change",
                "CPA_change",
                "CVR_change"
            ]
        )

    current = current.set_index(group_col)
    previous = previous.set_index(group_col)

    groups = sorted(
        set(current.index.tolist()) |
        set(previous.index.tolist()),
        key=lambda x: str(x)
    )

    rows = []

    for group in groups:

        if group in current.index:
            c = current.loc[group]
        else:
            c = pd.Series(dtype=float)

        if group in previous.index:
            p = previous.loc[group]
        else:
            p = pd.Series(dtype=float)

        c_spend = float(c.get("spend", 0))
        p_spend = float(p.get("spend", 0))

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

        rows.append(
            {
                group_col: group,
                "spend_current": c_spend,
                "spend_previous": p_spend,
                "conversion_current": c_conversion,
                "conversion_previous": p_conversion,
                "CPA_current": c_cpa,
                "CPA_previous": p_cpa,
                "CVR_current": c_cvr,
                "CVR_previous": p_cvr
            }
        )

    result = pd.DataFrame(rows)

    def change_rate(current_value, previous_value):

        if (
            pd.isna(previous_value)
            or previous_value == 0
            or pd.isna(current_value)
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


# ============================================================
# 7. 상단 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(
    [1, 1, 2]
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
        ["전일", "전주", "전월"],
        horizontal=True
    )

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
# 8. 매체 / 캠페인 선택
# ============================================================

st.subheader("🎯 분석 대상")

media_options = sorted(
    df["media"].dropna().unique().tolist(),
    key=lambda x: str(x)
)

campaign_options = sorted(
    df["campaign"].dropna().unique().tolist(),
    key=lambda x: str(x)
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
# 9. 필터 데이터
# ============================================================

filtered_df = df[
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaigns)
].copy()


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
# 10. 포맷 함수
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


def change_html(value):

    if pd.isna(value):

        return '<span class="neutral">-</span>'

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
# 11. 성과 비교 그래프
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text}  |  "
    f"비교 기간: {previous_period_text}"
)

chart_df = comparison[
    comparison["media"].isin(selected_media)
].copy()

chart_df = chart_df.sort_values(
    "conversion_current",
    ascending=False
)

# ------------------------------------------------------------
# X축 긴 매체명 처리
# ------------------------------------------------------------

x_labels = [
    str(x)
    for x in chart_df["media"].tolist()
]

# ============================================================
# 12. CPA + 전환수
# ============================================================

fig_cpa = go.Figure()

fig_cpa.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["CPA_current"].fillna(0),
        name="기준 CPA",
        text=[
            safe_money(v)
            for v in chart_df["CPA_current"]
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
        y=chart_df["CPA_previous"].fillna(0),
        name="비교 CPA",
        text=[
            safe_money(v)
            for v in chart_df["CPA_previous"]
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
        y=chart_df["conversion_current"].fillna(0),
        name="기준 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_cpa.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df["conversion_previous"].fillna(0),
        name="비교 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_cpa.update_layout(

    title=(
        "CPA + 전환수"
        f"<br><sup>"
        f"기준: {current_period_text}"
        f"  |  "
        f"비교: {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=360,

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
        title="전환수",
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
# 13. 광고비 + 전환수
# ============================================================

fig_spend = go.Figure()

fig_spend.add_trace(
    go.Bar(
        x=x_labels,
        y=chart_df["spend_current"].fillna(0),
        name="기준 광고비",
        text=[
            safe_money(v)
            for v in chart_df["spend_current"]
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
        y=chart_df["spend_previous"].fillna(0),
        name="비교 광고비",
        text=[
            safe_money(v)
            for v in chart_df["spend_previous"]
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
        y=chart_df["conversion_current"].fillna(0),
        name="기준 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "기준 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_spend.add_trace(
    go.Scatter(
        x=x_labels,
        y=chart_df["conversion_previous"].fillna(0),
        name="비교 전환수",
        mode="lines+markers",
        yaxis="y2",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "비교 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
    )
)

fig_spend.update_layout(

    title=(
        "광고비 + 전환수"
        f"<br><sup>"
        f"기준: {current_period_text}"
        f"  |  "
        f"비교: {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=360,

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
        title="전환수",
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
# 14. 매체 비교표
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


def build_comparison_html(
    table_df,
    group_col,
    table_class
):

    if table_df.empty:

        return "<p>비교할 데이터가 없습니다.</p>"

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

        safe_group = html.escape(str(group))

        result_html += (
            f"<th>{safe_group}</th>"
        )

    result_html += "</tr>"

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

            current_value = row[current_col]
            previous_value = row[previous_col]
            change_value = row[change_col]

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
                    if pd.notna(current_value)
                    else "-"
                )

                previous_text = (
                    f"{previous_value:,.0f}건"
                    if pd.notna(previous_value)
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

            </td>
            """

        result_html += "</tr>"

    result_html += """
    </table>
    </div>
    """

    return result_html


st.markdown(
    build_comparison_html(
        media_table,
        "media",
        "performance-table"
    ),
    unsafe_allow_html=True
)


# ============================================================
# AI 성과 분석
# ============================================================

def generate_ai_analysis(
    comparison_df,
    current_period_text,
    previous_period_text,
    period_type
):

    client = get_openai_client()

    if client is None:

        return (
            "⚠️ OpenAI API Key가 설정되어 있지 않습니다.\n\n"
            "Streamlit Cloud → Settings → Secrets에서 "
            "`OPENAI_API_KEY`를 설정해주세요."
        )

    if comparison_df.empty:

        return "분석할 데이터가 없습니다."

    analysis_df = comparison_df.copy()

    # --------------------------------------------------------
    # AI에게 전달할 데이터 정리
    # --------------------------------------------------------

    analysis_data = []

    for _, row in analysis_df.iterrows():

        analysis_data.append({

            "매체": str(row["media"]),

            "기준 광고비":
                round(float(row["spend_current"]), 0),

            "비교 광고비":
                round(float(row["spend_previous"]), 0),

            "광고비 변화율":
                round(float(row["spend_change"]), 1)
                if pd.notna(row["spend_change"])
                else None,

            "기준 전환수":
                round(float(row["conversion_current"]), 0),

            "비교 전환수":
                round(float(row["conversion_previous"]), 0),

            "전환 변화율":
                round(float(row["conversion_change"]), 1)
                if pd.notna(row["conversion_change"])
                else None,

            "기준 CPA":
                round(float(row["CPA_current"]), 0)
                if pd.notna(row["CPA_current"])
                else None,

            "비교 CPA":
                round(float(row["CPA_previous"]), 0)
                if pd.notna(row["CPA_previous"])
                else None,

            "CPA 변화율":
                round(float(row["CPA_change"]), 1)
                if pd.notna(row["CPA_change"])
                else None,

            "기준 CVR":
                round(float(row["CVR_current"]), 2)
                if pd.notna(row["CVR_current"])
                else None,

            "비교 CVR":
                round(float(row["CVR_previous"]), 2)
                if pd.notna(row["CVR_previous"])
                else None,

            "CVR 변화율":
                round(float(row["CVR_change"]), 1)
                if pd.notna(row["CVR_change"])
                else None
        })

    # --------------------------------------------------------
    # 프롬프트
    # --------------------------------------------------------

    prompt = f"""
너는 10년차 퍼포먼스 마케팅 전문가다.

아래 광고 성과 데이터를 분석해서
실무자가 바로 의사결정을 할 수 있도록 분석해라.

[비교 기간]
기준 기간: {current_period_text}
비교 기간: {previous_period_text}
비교 유형: {period_type}

[분석 데이터]
{analysis_data}

반드시 다음 순서로 작성해라.

## 1. 전체 성과 요약

광고비, 전환수, CPA, CVR의 변화를 종합해서
현재 성과가 좋아졌는지 나빠졌는지 설명한다.

단순히 숫자를 나열하지 말고
성과의 방향성을 설명한다.

## 2. 핵심 원인 추론

성과 변화의 원인을 추론한다.

특히 다음 관계를 확인한다.

광고비 → 전환수 → CPA → CVR

예를 들어

- 광고비 증가 대비 전환 증가가 충분한가?
- 전환 증가가 CPA 악화 없이 발생했는가?
- CPA 악화의 원인이 CVR 하락일 가능성이 있는가?
- 예산 확대 과정에서 효율이 떨어지고 있는가?
- 효율은 좋아졌지만 볼륨이 감소하고 있는가?

데이터가 직접 증명하지 못하는 내용은
확정적으로 말하지 말고
"가능성이 있습니다", "확인 필요"라고 표현한다.

## 3. 매체별 진단

각 매체를 분석한다.

각 매체에 대해

- 확대
- 유지
- 관찰
- 축소 검토

중 하나를 판단한다.

판단 근거를 반드시 숫자로 설명한다.

## 4. 우선순위

다음 3가지 그룹을 선정한다.

### 확대 후보
전환과 CPA가 동시에 좋은 매체

### 효율 개선 후보
전환은 있지만 CPA가 악화된 매체

### 점검 후보
전환 감소와 CPA 악화가 동시에 발생한 매체

## 5. 실행 전략

퍼포먼스 마케팅 실무 관점에서
구체적인 액션을 제안한다.

예:

- 예산 재배분
- 입찰 전략 점검
- 소재 A/B 테스트
- 타겟 세분화
- 랜딩페이지 개선
- CVR 개선
- 저효율 캠페인 축소
- 고효율 캠페인 확장

추상적인 표현은 피한다.

"최적화가 필요합니다"가 아니라

"CPA가 악화된 매체의 저효율 캠페인 예산을
고효율 캠페인으로 10~20% 재배분하고
CVR 하락 원인을 랜딩페이지와 소재별로 분해해서 확인"

처럼 실행 가능한 형태로 제안한다.

## 6. 마케터에게 가장 중요한 한 가지

현재 데이터만 보고
가장 먼저 해야 할 액션을 딱 하나 선정한다.

형식:

**🎯 최우선 액션**
→ 내용

마지막으로 전체 분석을
퍼포먼스 마케터가 팀장에게 보고하는 것처럼
간결하고 명확하게 작성한다.
"""

    # --------------------------------------------------------
    # OpenAI API 호출
    # --------------------------------------------------------

    try:

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return response.output_text

    except Exception as e:

        return (
            "❌ AI 분석 중 오류가 발생했습니다.\n\n"
            f"오류 내용: {e}"
        )

# ============================================================
# 15. 성과 해석
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
    # 전체 계산
    # --------------------------------------------------------

    total_current_spend = (
        df_comment["spend_current"].sum()
    )

    total_previous_spend = (
        df_comment["spend_previous"].sum()
    )

    total_current_conv = (
        df_comment["conversion_current"].sum()
    )

    total_previous_conv = (
        df_comment["conversion_previous"].sum()
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

    total_conv_change = (
        (
            total_current_conv -
            total_previous_conv
        )
        / total_previous_conv
        * 100
        if total_previous_conv > 0
        else np.nan
    )

    total_cpa_change = (
        (
            total_current_cpa -
            total_previous_cpa
        )
        / total_previous_cpa
        * 100
        if (
            pd.notna(total_previous_cpa)
            and total_previous_cpa > 0
        )
        else np.nan
    )

    total_spend_change = (
        (
            total_current_spend -
            total_previous_spend
        )
        / total_previous_spend
        * 100
        if total_previous_spend > 0
        else np.nan
    )

    comments.append(
        "### 📊 전체 성과 요약"
    )

    if pd.notna(total_conv_change):

        comments.append(
            f"- 전체 전환수: "
            f"**{total_current_conv:,.0f}건** "
            f"({total_conv_change:+.1f}%)"
        )

    if pd.notna(total_cpa_change):

        if total_cpa_change < 0:

            comments.append(
                f"- 전체 CPA: "
                f"**{total_current_cpa:,.0f}원** "
                f"({total_cpa_change:+.1f}%) "
                f"→ **효율 개선**"
            )

        else:

            comments.append(
                f"- 전체 CPA: "
                f"**{total_current_cpa:,.0f}원** "
                f"({total_cpa_change:+.1f}%) "
                f"→ **효율 악화**"
            )

    if pd.notna(total_spend_change):

        comments.append(
            f"- 전체 광고비: "
            f"**{total_current_spend:,.0f}원** "
            f"({total_spend_change:+.1f}%)"
        )

    comments.append("")

    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

    valid_cpa = df_comment[
        df_comment["CPA_current"].notna() &
        (df_comment["conversion_current"] > 0)
    ]

    if not valid_cpa.empty:

        best_cpa = valid_cpa.loc[
            valid_cpa["CPA_current"].idxmin()
        ]

        comments.append(
            f"🏆 **CPA 최우수:** "
            f"`{best_cpa[group_col]}` "
            f"({best_cpa['CPA_current']:,.0f}원)"
        )

    # --------------------------------------------------------
    # 전환수 최다
    # --------------------------------------------------------

    valid_conv = df_comment[
        df_comment["conversion_current"] > 0
    ]

    if not valid_conv.empty:

        best_conv = valid_conv.loc[
            valid_conv["conversion_current"].idxmax()
        ]

        comments.append(
            f"📈 **전환수 최다:** "
            f"`{best_conv[group_col]}` "
            f"({best_conv['conversion_current']:,.0f}건)"
        )

    # --------------------------------------------------------
    # 전환 증가 최대
    # --------------------------------------------------------

    valid_growth = df_comment[
        df_comment["conversion_change"].notna()
    ]

    if not valid_growth.empty:

        growth = valid_growth.loc[
            valid_growth["conversion_change"].idxmax()
        ]

        if growth["conversion_change"] > 0:

            comments.append(
                f"🚀 **전환 증가폭 최대:** "
                f"`{growth[group_col]}` "
                f"({growth['conversion_change']:+,.1f}%)"
            )

    # --------------------------------------------------------
    # CPA 악화
    # --------------------------------------------------------

    valid_cpa_change = df_comment[
        df_comment["CPA_change"].notna()
    ]

    if not valid_cpa_change.empty:

        worst_cpa = valid_cpa_change.loc[
            valid_cpa_change["CPA_change"].idxmax()
        ]

        if worst_cpa["CPA_change"] > 0:

            comments.append(
                f"⚠️ **CPA 악화 주의:** "
                f"`{worst_cpa[group_col]}` "
                f"({worst_cpa['CPA_change']:+,.1f}%)"
            )

    # --------------------------------------------------------
    # 개별 분석
    # --------------------------------------------------------

    comments.append("")
    comments.append("### 🔎 주요 변화")

    for _, row in df_comment.iterrows():

        target = str(row[group_col])

        conv_change = row["conversion_change"]
        cpa_change = row["CPA_change"]
        cvr_change = row["CVR_change"]

        if (
            pd.notna(conv_change)
            and conv_change > 10
            and pd.notna(cpa_change)
            and cpa_change < -10
        ):

            comments.append(
                f"- **{target}**: "
                f"전환수 {conv_change:+.1f}% / "
                f"CPA {cpa_change:+.1f}% → "
                f"**볼륨과 효율이 동시에 개선**"
            )

        elif (
            pd.notna(conv_change)
            and conv_change > 10
            and pd.notna(cpa_change)
            and cpa_change > 10
        ):

            comments.append(
                f"- **{target}**: "
                f"전환수는 {conv_change:+.1f}% 증가했지만 "
                f"CPA도 {cpa_change:+.1f}% 상승 → "
                f"**확장에 따른 효율 악화 여부 확인 필요**"
            )

        elif (
            pd.notna(conv_change)
            and conv_change < -10
            and pd.notna(cpa_change)
            and cpa_change > 10
        ):

            comments.append(
                f"- **{target}**: "
                f"전환수 {conv_change:+.1f}% / "
                f"CPA {cpa_change:+.1f}% → "
                f"**우선 점검 필요**"
            )

        elif (
            pd.notna(conv_change)
            and conv_change < -10
        ):

            comments.append(
                f"- **{target}**: "
                f"전환수가 {conv_change:+.1f}% 감소 → "
                f"광고비·클릭·CVR 변화 확인 필요"
            )

        elif (
            pd.notna(conv_change)
            and conv_change > 10
        ):

            comments.append(
                f"- **{target}**: "
                f"전환수가 {conv_change:+.1f}% 증가 → "
                f"현재 볼륨 확대 효과 확인"
            )

        if (
            pd.notna(cvr_change)
            and cvr_change > 10
        ):

            comments.append(
                f"  - CVR {cvr_change:+.1f}% 개선"
            )

        elif (
            pd.notna(cvr_change)
            and cvr_change < -10
        ):

            comments.append(
                f"  - CVR {cvr_change:+.1f}% 하락 → "
                f"랜딩페이지/타겟/소재 점검"
            )

    return comments


comments = make_performance_comments(
    comparison,
    "media"
)

for comment in comments:

    st.markdown(comment)


# ============================================================
# 16. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 매체에 포함된 캠페인을 가로로 배치하여 상세 비교합니다."
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
    campaign_comparison["campaign"].isin(
        selected_campaigns
    )
].copy()

campaign_table = campaign_table.sort_values(
    "conversion_current",
    ascending=False
)


# ============================================================
# 17. 캠페인 비교표
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
# 18. 캠페인 성과 코멘트
# ============================================================

st.subheader("📝 캠페인 성과 코멘트")

campaign_comments = make_performance_comments(
    campaign_table,
    "campaign"
)

for comment in campaign_comments:

    st.markdown(comment)


# ============================================================
# 19. ChatGPT 분석
# ============================================================

st.divider()

st.header("🤖 ChatGPT 성과 해석 · 추론 · 전략")

st.caption(
    "현재 선택한 기간과 매체/캠페인 데이터를 바탕으로 "
    "성과 원인과 다음 액션을 분석합니다."
)


def build_ai_data():

    rows = []

    for _, row in comparison.iterrows():

        rows.append(
            {
                "매체": str(row["media"]),
                "기준 광고비": float(
                    row["spend_current"]
                ),
                "비교 광고비": float(
                    row["spend_previous"]
                ),
                "기준 전환": float(
                    row["conversion_current"]
                ),
                "비교 전환": float(
                    row["conversion_previous"]
                ),
                "기준 CPA": (
                    None
                    if pd.isna(row["CPA_current"])
                    else float(row["CPA_current"])
                ),
                "비교 CPA": (
                    None
                    if pd.isna(row["CPA_previous"])
                    else float(row["CPA_previous"])
                ),
                "기준 CVR": (
                    None
                    if pd.isna(row["CVR_current"])
                    else float(row["CVR_current"])
                ),
                "비교 CVR": (
                    None
                    if pd.isna(row["CVR_previous"])
                    else float(row["CVR_previous"])
                ),
                "광고비 변화율": (
                    None
                    if pd.isna(row["spend_change"])
                    else float(row["spend_change"])
                ),
                "전환 변화율": (
                    None
                    if pd.isna(row["conversion_change"])
                    else float(row["conversion_change"])
                ),
                "CPA 변화율": (
                    None
                    if pd.isna(row["CPA_change"])
                    else float(row["CPA_change"])
                ),
                "CVR 변화율": (
                    None
                    if pd.isna(row["CVR_change"])
                    else float(row["CVR_change"])
                )
            }
        )

    return rows


def ask_chatgpt():

    try:

        from openai import OpenAI

    except ImportError:

        return (
            "OpenAI 라이브러리가 설치되어 있지 않습니다. "
            "`requirements.txt`에 `openai`를 추가해주세요."
        )

    if "OPENAI_API_KEY" not in st.secrets:

        return (
            "⚠️ 아직 OpenAI API Key가 연결되지 않았습니다.\n\n"
            "Streamlit Cloud → Settings → Secrets에서 "
            "`OPENAI_API_KEY`를 등록하면 사용할 수 있습니다."
        )

    api_key = st.secrets["OPENAI_API_KEY"]

    client = OpenAI(
        api_key=api_key
    )

    ai_data = build_ai_data()

    prompt = f"""
너는 10년차 퍼포먼스 마케팅 데이터 분석가다.

다음 광고 성과 데이터를 분석해줘.

[분석 기간]
기준 기간: {current_period_text}
비교 기간: {previous_period_text}

[선택 매체]
{selected_media}

[선택 캠페인]
{selected_campaigns}

[데이터]
{ai_data}

반드시 다음 구조로 답변해줘.

### 1. 전체 성과 요약
- 광고비 변화
- 전환수 변화
- CPA 변화
- 가장 중요한 변화 2~3개

### 2. 잘하고 있는 매체
- 어떤 매체가 좋은지
- 왜 좋은지
- 데이터상 근거

### 3. 성과가 낮아진 매체
- 어떤 매체가 문제인지
- CPA/전환/CVR 중 무엇이 원인인지
- 단순히 "성과가 안 좋다"가 아니라 가능한 원인을 추론

### 4. 원인 추론
광고비 → 클릭 → CVR → 전환 → CPA 관점에서
가능한 원인을 분석해줘.

단, 데이터에 없는 사실은 확정적으로 말하지 말고
"가능성이 높다", "확인이 필요하다"처럼 표현해줘.

### 5. 실행 전략
퍼포먼스 마케터가 실제로 바로 실행할 수 있도록
우선순위 순서대로 5개 이내의 액션을 제안해줘.

예:
- 예산 증액
- 예산 감액
- 소재 교체
- 타겟 수정
- 입찰 조정
- 랜딩페이지 점검
- 캠페인 구조 변경
- 저효율 캠페인 중단
- 고효율 캠페인 확장

### 6. 한 줄 결론
경영진에게 보고한다는 생각으로
가장 중요한 결론을 한 문장으로 정리해줘.

숫자를 반드시 활용하고,
불필요하게 장황하지 않게 작성해줘.
"""

    try:

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return response.output_text

    except Exception as e:

        return (
            "ChatGPT 분석 중 오류가 발생했습니다.\n\n"
            f"오류 내용: {e}"
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
