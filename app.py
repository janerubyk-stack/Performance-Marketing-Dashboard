import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    # 실제 컬럼명 출력용
    # --------------------------------------------------------

    print("=" * 70)
    print("Google Sheets 데이터 불러오기 완료")
    print("=" * 70)

    print("데이터 건수:", f"{len(df):,}")
    print("실제 컬럼명:")
    print(df.columns.tolist())

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
        "DATE",
        "날짜"
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

    print("DATE      :", date_col)
    print("MEDIA     :", media_col)
    print("CAMPAIGN  :", campaign_col)
    print("IMPRESS   :", impress_col)
    print("CLICK     :", click_col)
    print("SPEND     :", spend_col)
    print("CONVERSION:", conversion_col)

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
        key for key, value in required.items()
        if value is None
    ]

    if missing:
        raise ValueError(
            f"필수 컬럼을 찾을 수 없습니다: {missing}"
        )

    # --------------------------------------------------------
    # 내부 표준 컬럼으로 변경
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
    # 숫자 컬럼
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
    # 문자 컬럼
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

    # 빈 문자열 처리
    df.loc[df["media"] == "", "media"] = "미분류"
    df.loc[df["campaign"] == "", "campaign"] = "미분류"

    # --------------------------------------------------------
    # 날짜 없는 데이터 제거
    # --------------------------------------------------------

    df = df.dropna(
        subset=["date"]
    ).copy()

    df["date"] = df["date"].dt.normalize()

    # --------------------------------------------------------
    # 안전한 정렬
    # --------------------------------------------------------

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    print("=" * 70)
    print("데이터 정상 처리")
    print("=" * 70)

    if len(df) > 0:

        print(
            "데이터 건수:",
            f"{len(df):,}"
        )

        print(
            "시작 날짜:",
            df["date"].min().date()
        )

        print(
            "최신 날짜:",
            df["date"].max().date()
        )

    print("=" * 70)

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
# 5. 기간 계산 함수
# ============================================================

def get_periods(base_date, period_type):

    base_date = pd.Timestamp(base_date)

    # --------------------------------------------------------
    # 전일
    # 기준일 하루 vs 전일 하루
    # --------------------------------------------------------

    if period_type == "전일":

        current_start = base_date
        current_end = base_date

        previous_start = base_date - timedelta(days=1)
        previous_end = base_date - timedelta(days=1)

    # --------------------------------------------------------
    # 전주
    #
    # 기준일이 속한 주의 월요일 ~ 기준일
    # 전주도 동일한 진행일수
    #
    # 예:
    # 8/26 수요일
    #
    # 기준기간: 8/24 ~ 8/26
    # 비교기간: 8/17 ~ 8/19
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
    #
    # 기준일이 8/26이라면
    #
    # 기준기간: 8/1 ~ 8/26
    # 비교기간: 7/1 ~ 7/26
    #
    # 월 길이가 짧은 경우 마지막 날짜까지 자동 조정
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
# 6. 기간 문자열
# ============================================================

def format_period(start_date, end_date):

    return (
        f"{start_date.strftime('%Y-%m-%d')}"
        f" ~ "
        f"{end_date.strftime('%Y-%m-%d')}"
    )


# ============================================================
# 7. 성과 계산
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

    # --------------------------------------------------------
    # CPA
    # --------------------------------------------------------

    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"] /
        result["conversion"],
        np.nan
    )

    # --------------------------------------------------------
    # CVR
    #
    # 기존 데이터 구조 기준:
    # conversion / click
    # --------------------------------------------------------

    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
        np.nan
    )

    return result


# ============================================================
# 8. 전체 선택 helper
# ============================================================

def select_all_options(
    label,
    options,
    key
):

    selected = st.multiselect(
        label,
        options=options,
        default=options,
        key=key
    )

    return selected


# ============================================================
# 9. 상단 필터
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(
    [1, 1, 2]
)

# ------------------------------------------------------------
# 기준일
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# 비교 기간
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# 기간 계산
# ------------------------------------------------------------

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
        f"""
**기준 기간:** {current_period_text}

**비교 기간:** {previous_period_text}

**동일 진행일수:** {elapsed_days}일
"""
    )


# ============================================================
# 10. 매체 / 캠페인 필터
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
# 11. 전체 선택 버튼
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
# 12. 필터 데이터
# ============================================================

filtered_df = df[
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 13. 현재 / 비교 데이터
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
# 14. 매체 기준 집계
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
        .groupby("media", as_index=False)
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
# 15. 비교 데이터 생성
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
# 16. 변화율 표시
# ============================================================

def change_text(
    value,
    reverse=False
):

    if pd.isna(value):

        return "-"

    value = float(value)

    if value > 0:

        return f"▲ +{value:,.1f}%"

    elif value < 0:

        return f"▼ {value:,.1f}%"

    else:

        return "─ 0.0%"


# ============================================================
# 17. 숫자 표시
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
# 18. 성과 비교 그래프
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text}  |  "
    f"비교 기간: {previous_period_text}  |  "
    f"동일 진행일수: {elapsed_days}일"
)


# ============================================================
# 19. 그래프 데이터
# ============================================================

chart_df = comparison.copy()

chart_df = chart_df[
    chart_df["media"].isin(selected_media)
].copy()

# 현재 성과 기준 정렬
chart_df = chart_df.sort_values(
    "conversion_current",
    ascending=False
)

# X축 문자열
x_labels = chart_df["media"].tolist()


# ============================================================
# 20. CPA + 전환수 차트
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

    title=(
        "CPA + 전환수"
        f"<br><sup>"
        f"기준 {current_period_text}"
        f" vs "
        f"비교 {previous_period_text}"
        f"</sup>"
    ),

    barmode="group",

    height=390,

    margin=dict(
        l=50,
        r=50,
        t=80,
        b=100
    ),

    xaxis=dict(
        title="매체",
        tickmode="array",
        tickvals=x_labels,
        ticktext=x_labels,
        tickangle=-35,
        automargin=True,
        type="category"
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
# 21. 광고비 + 전환수 차트
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
            "비교 전환수: %{y:,.0f}건"
            "<extra></extra>"
        )
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

    height=390,

    margin=dict(
        l=50,
        r=50,
        t=80,
        b=100
    ),

    xaxis=dict(
        title="매체",
        tickmode="array",
        tickvals=x_labels,
        ticktext=x_labels,
        tickangle=-35,
        automargin=True,
        type="category"
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


# ============================================================
# 22. 그래프 표시
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


# ============================================================
# 23. 매체별 비교표
# ============================================================

st.divider()

st.header("📋 매체별 상세 성과 비교")

st.caption(
    "매체를 가로로 배치하고, 성과 지표를 세로로 비교합니다."
)


# ============================================================
# 24. 매체 비교표 데이터
# ============================================================

media_table = comparison[
    comparison["media"].isin(selected_media)
].copy()

media_table = media_table.sort_values(
    "conversion_current",
    ascending=False
)


# ------------------------------------------------------------
# HTML 테이블 생성
# ------------------------------------------------------------

metric_rows = [

    ("광고비", "spend_current", "spend_previous", "spend_change", "money"),

    ("전환수", "conversion_current", "conversion_previous", "conversion_change", "number"),

    ("CPA", "CPA_current", "CPA_previous", "CPA_change", "cpa"),

    ("CVR", "CVR_current", "CVR_previous", "CVR_change", "percent")
]


html = """
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

    html += f"<th>{media}</th>"

html += "</tr>"


for metric_name, current_col, previous_col, change_col, fmt_type in metric_rows:

    html += f"""
    <tr>

    <td class="metric">
        {metric_name}
    </td>
    """

    for _, row in media_table.iterrows():

        current_value = row[current_col]
        previous_value = row[previous_col]
        change_value = row[change_col]

        if fmt_type == "money":

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

        elif fmt_type == "cpa":

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

        # 변화율
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

        html += f"""

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

    html += "</tr>"


html += """

</table>

"""


st.markdown(
    html,
    unsafe_allow_html=True
)


# ============================================================
# 25. 성과 코멘트
# ============================================================

st.divider()

st.header("💡 성과 해석")


# ============================================================
# 26. 코멘트 생성
# ============================================================

def generate_comments(data):

    comments = []

    valid = data[
        data["conversion_current"] > 0
    ].copy()

    if valid.empty:

        return [
            "현재 기간에 전환이 발생한 매체가 없습니다."
        ]

    # --------------------------------------------------------
    # CPA 우수
    # --------------------------------------------------------

    cpa_valid = valid[
        valid["CPA_current"].notna()
    ]

    if not cpa_valid.empty:

        best_cpa = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmin()
        ]

        worst_cpa = cpa_valid.loc[
            cpa_valid["CPA_current"].idxmax()
        ]

        comments.append(
            f"✅ **CPA 우수:** "
            f"{best_cpa['media']}가 "
            f"{best_cpa['CPA_current']:,.0f}원으로 "
            f"가장 낮은 CPA를 기록했습니다."
        )

        if best_cpa["media"] != worst_cpa["media"]:

            comments.append(
                f"⚠️ **CPA 개선 필요:** "
                f"{worst_cpa['media']}는 "
                f"{worst_cpa['CPA_current']:,.0f}원으로 "
                f"선택 매체 중 CPA가 가장 높습니다."
            )

    # --------------------------------------------------------
    # 전환수
    # --------------------------------------------------------

    best_conversion = valid.loc[
        valid["conversion_current"].idxmax()
    ]

    comments.append(
        f"📈 **전환수 최대:** "
        f"{best_conversion['media']}가 "
        f"{best_conversion['conversion_current']:,.0f}건으로 "
        f"가장 많은 전환을 만들었습니다."
    )

    # --------------------------------------------------------
    # 전환 증가
    # --------------------------------------------------------

    conversion_growth = data[
        data["conversion_change"].notna()
    ].copy()

    if not conversion_growth.empty:

        growth = conversion_growth.loc[
            conversion_growth["conversion_change"].idxmax()
        ]

        decline = conversion_growth.loc[
            conversion_growth["conversion_change"].idxmin()
        ]

        if growth["conversion_change"] > 0:

            comments.append(
                f"🚀 **전환 증가폭 최대:** "
                f"{growth['media']}의 전환수가 "
                f"{growth['conversion_change']:+.1f}% "
                f"증가했습니다."
            )

        if decline["conversion_change"] < 0:

            comments.append(
                f"🔻 **전환 감소폭 최대:** "
                f"{decline['media']}의 전환수가 "
                f"{decline['conversion_change']:.1f}% "
                f"감소했습니다."
            )

    # --------------------------------------------------------
    # CPA 개선 / 악화
    # --------------------------------------------------------

    cpa_change = data[
        data["CPA_change"].notna()
    ].copy()

    if not cpa_change.empty:

        best_cpa_change = cpa_change.loc[
            cpa_change["CPA_change"].idxmin()
        ]

        worst_cpa_change = cpa_change.loc[
            cpa_change["CPA_change"].idxmax()
        ]

        if best_cpa_change["CPA_change"] < 0:

            comments.append(
                f"💰 **CPA 개선:** "
                f"{best_cpa_change['media']}의 CPA가 "
                f"{abs(best_cpa_change['CPA_change']):,.1f}% "
                f"개선되었습니다."
            )

        if worst_cpa_change["CPA_change"] > 0:

    comments.append(
        f"⚠️ **CPA 악화:** "
        f"{worst_cpa_change['media']}의 CPA가 "
        f"{worst_cpa_change['CPA_change']:+,.1f}% "
        f"상승했습니다."
   )
    return comments


comments = generate_comments(
    comparison
)


for comment in comments:

    st.markdown(comment)


# ============================================================
# 27. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 매체 안의 캠페인을 가로로 배치해 상세 비교합니다."
)


# ============================================================
# 28. 캠페인 기준 집계
# ============================================================

def aggregate_by_campaign(data):

    if data.empty:

        return pd.DataFrame(
            columns=[
                "campaign",
                "spend",
                "conversion",
                "CPA",
                "CVR"
            ]
        )

    result = (
        data
        .groupby("campaign", as_index=False)
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


# ============================================================
# 29. 캠페인 비교
# ============================================================

campaign_comparison = create_comparison(
    current_campaign.rename(
        columns={
            "spend": "spend",
            "conversion": "conversion"
        }
    ),
    previous_campaign.rename(
        columns={
            "spend": "spend",
            "conversion": "conversion"
        }
    ),
    "campaign"
)


# ============================================================
# 30. 캠페인 필터
# ============================================================

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
# 31. 캠페인 비교 HTML
# ============================================================

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

}

.campaign-table td.metric {

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

<table class="campaign-table">

<tr>

<th>지표</th>

"""


for campaign in campaign_table["campaign"]:

    campaign_html += (
        f"<th>{campaign}</th>"
    )


campaign_html += "</tr>"


for metric_name, current_col, previous_col, change_col, fmt_type in metric_rows:

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
# 32. 캠페인 해석
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

    if not valid_campaigns.empty:

        # ----------------------------------------------------
        # CPA
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
        # 전환
        # ----------------------------------------------------

        best_conversion = valid_campaigns.loc[
            valid_campaigns["conversion_current"].idxmax()
        ]

        st.markdown(
            f"📈 **전환수 최다 캠페인:** "
            f"`{best_conversion['campaign']}` "
            f"({best_conversion['conversion_current']:,.0f}건)"
        )

        # ----------------------------------------------------
        # 전환 증가
        # ----------------------------------------------------

        growth = campaign_table[
            campaign_table["conversion_change"].notna()
        ]

        if not growth.empty:

            growth = growth.loc[
                growth["conversion_change"].idxmax()
            ]

            if growth["conversion_change"] > 0:

                st.markdown(
                    f"🚀 **전환 증가폭 최대:** "
                    f"`{growth['campaign']}` "
                    f"({growth['conversion_change']:+,.1f}%)"
                )

        # ----------------------------------------------------
        # CPA 악화
        # ----------------------------------------------------

        cpa_change = campaign_table[
            campaign_table["CPA_change"].notna()
        ]

        if not cpa_change.empty:

            worst = cpa_change.loc[
                cpa_change["CPA_change"].idxmax()
            ]

            if worst["CPA_change"] > 0:

                st.markdown(
                    f"⚠️ **CPA 악화 주의:** "
                    f"`{worst['campaign']}` "
                    f"({worst['CPA_change']:+,.1f}%)"
                )

    else:

        st.info(
            "현재 기간에 전환이 발생한 캠페인이 없습니다."
        )


# ============================================================
# 33. 하단 데이터 정보
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
