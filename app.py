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
    # 내부 표준 컬럼으로 변경
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
# 5. 기간 계산
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
# 6. 기간 문자열
# ============================================================

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


    # CPA
    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"] / result["conversion"],
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
# 8. 상단 분석 조건
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


    # 현재 기간 일수
    custom_elapsed_days = (
        pd.Timestamp(custom_current_end)
        - pd.Timestamp(custom_current_start)
    ).days + 1


    with custom_col2:

        st.markdown(
            f"**기준 기간 일수: {custom_elapsed_days}일**"
        )

        custom_previous_start = st.date_input(
            "비교 시작일",
            value=(
                pd.Timestamp(custom_current_start)
                - timedelta(days=custom_elapsed_days)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_start"
        )

        custom_previous_end = st.date_input(
            "비교 종료일",
            value=(
                pd.Timestamp(custom_previous_start)
                + timedelta(days=custom_elapsed_days - 1)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_end"
        )


    previous_elapsed_days = (
        pd.Timestamp(custom_previous_end)
        - pd.Timestamp(custom_previous_start)
    ).days + 1


    # 동일 일수 체크
    if custom_elapsed_days != previous_elapsed_days:

        st.error(
            f"⚠️ 기준 기간은 {custom_elapsed_days}일인데 "
            f"비교 기간은 {previous_elapsed_days}일입니다. "
            f"동일한 일수로 설정해주세요."
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
# 9. TYPE / 매체 / 캠페인 필터
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
# 매체
# ------------------------------------------------------------

with filter_col2:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_options,
        default=media_options,
        key="media_filter"
    )


# ------------------------------------------------------------
# 캠페인
# ------------------------------------------------------------

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

button_col1, button_col2, button_col3 = st.columns(
    [1, 1, 1]
)


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
# 13. 매체 기준 집계
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
            or pd.isna(current_value)
        ):

            return np.nan


        return (
            (current_value - previous_value)
            / previous_value
            * 100
        )


    result["spend_change"] = result.apply(
        lambda x:
        change_rate(
            x["spend_current"],
            x["spend_previous"]
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


def calc_change(current, previous):

    if (
        pd.isna(previous)
        or previous == 0
        or pd.isna(current)
    ):

        return np.nan

    return (
        (current - previous)
        / previous
        * 100
    )


total_spend_change = calc_change(
    total_current_spend,
    total_previous_spend
)

total_conversion_change = calc_change(
    total_current_conversion,
    total_previous_conversion
)

total_cpa_change = calc_change(
    total_current_cpa,
    total_previous_cpa
)

total_cvr_change = calc_change(
    total_current_cvr,
    total_previous_cvr
)


summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)


with summary_col1:

    st.metric(
        "광고비",
        f"{total_current_spend:,.0f}원",
        (
            f"{total_spend_change:+.1f}%"
            if pd.notna(total_spend_change)
            else "-"
        )
    )


with summary_col2:

    st.metric(
        "전환수",
        f"{total_current_conversion:,.0f}건",
        (
            f"{total_conversion_change:+.1f}%"
            if pd.notna(total_conversion_change)
            else "-"
        )
    )


with summary_col3:

    st.metric(
        "CPA",
        (
            f"{total_current_cpa:,.0f}원"
            if pd.notna(total_current_cpa)
            else "-"
        ),
        (
            f"{total_cpa_change:+.1f}%"
            if pd.notna(total_cpa_change)
            else "-"
        ),
        delta_color="inverse"
    )


with summary_col4:

    st.metric(
        "CVR",
        (
            f"{total_current_cvr:.2f}%"
            if pd.notna(total_current_cvr)
            else "-"
        ),
        (
            f"{total_cvr_change:+.1f}%"
            if pd.notna(total_cvr_change)
            else "-"
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


# ============================================================
# 추이 집계 함수
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


    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"] /
        result["click"] *
        100,
        np.nan
    )


    return result.sort_values("period")


# ============================================================
# 추이 탭
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
            "선택한 기간에 데이터가 없습니다."
        )

        return


    # --------------------------------------------------------
    # X축
    # --------------------------------------------------------

    if trend_type == "일자별":

        x_values = trend_df["period"].dt.strftime(
            "%m/%d"
        )

    elif trend_type == "주차별":

        x_values = trend_df["period"].dt.strftime(
            "%m/%d"
        )

    else:

        x_values = trend_df["period"].dt.strftime(
            "%Y-%m"
        )


    # --------------------------------------------------------
    # 그래프
    # --------------------------------------------------------

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

chart_df = chart_df[
    chart_df["media"].isin(selected_media)
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
# 20. 매체별 상세 비교
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


table_html = """
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

    table_html += (
        f"<th>{html.escape(str(media))}</th>"
    )


table_html += "</tr>"


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


# ============================================================
# 21. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 TYPE / 매체 안의 캠페인을 상세 비교합니다."
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
        f"<th>{html.escape(str(campaign))}</th>"
    )


campaign_html += "</tr>"


for (
    metric_name,
    current_col,
    previous_col,
    change_col,
    fmt_type
) in metric_rows:

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


if campaign_table.empty:

    st.info(
        "선택한 캠페인의 성과 데이터가 없습니다."
    )

else:

    st.markdown(
        campaign_html,
        unsafe_allow_html=True
    )


# ============================================================
# 22. 캠페인 성과 코멘트
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
        # 전환 > 0인 캠페인만
        # ----------------------------------------------------

        cpa_valid = valid_campaigns[
            valid_campaigns["CPA_current"].notna() &
            (valid_campaigns["CPA_current"] > 0)
        ]


        if not cpa_valid.empty:

            best = cpa_valid.loc[
                cpa_valid["CPA_current"].idxmin()
            ]


            st.markdown(
                f"🏆 **CPA 최우수 캠페인:** "
                f"`{best['campaign']}` "
                f"— CPA **{best['CPA_current']:,.0f}원** "
                f"/ 전환 **{best['conversion_current']:,.0f}건**"
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
            f"— 전환 **{best_conversion['conversion_current']:,.0f}건** "
            f"/ CPA **{best_conversion['CPA_current']:,.0f}원**"
        )


        # ----------------------------------------------------
        # 전환 증가폭 최대
        # ----------------------------------------------------

        growth = campaign_table[
            campaign_table["conversion_change"].notna()
        ]


        if not growth.empty:

            growth_best = growth.loc[
                growth["conversion_change"].idxmax()
            ]


            if growth_best["conversion_change"] > 0:

                st.markdown(
                    f"🚀 **전환 증가폭 최대:** "
                    f"`{growth_best['campaign']}` "
                    f"— 전환 "
                    f"**{growth_best['conversion_change']:+,.1f}%**"
                )


        # ----------------------------------------------------
        # CPA 악화
        # ----------------------------------------------------

        cpa_change_df = campaign_table[
            campaign_table["CPA_change"].notna()
        ]


        if not cpa_change_df.empty:

            worst = cpa_change_df.loc[
                cpa_change_df["CPA_change"].idxmax()
            ]


            if worst["CPA_change"] > 0:

                st.markdown(
                    f"⚠️ **CPA 악화 주의:** "
                    f"`{worst['campaign']}` "
                    f"— CPA "
                    f"**{worst['CPA_change']:+,.1f}%**"
                )


        # ----------------------------------------------------
        # CVR 변화
        # ----------------------------------------------------

        cvr_change_df = campaign_table[
            campaign_table["CVR_change"].notna()
        ]


        if not cvr_change_df.empty:

            best_cvr = cvr_change_df.loc[
                cvr_change_df["CVR_change"].idxmax()
            ]


            if best_cvr["CVR_change"] > 10:

                st.markdown(
                    f"📈 **CVR 최대 개선:** "
                    f"`{best_cvr['campaign']}` "
                    f"— CVR "
                    f"**{best_cvr['CVR_change']:+,.1f}%**"
                )


# ============================================================
# 23. 전체 성과 해석
# ============================================================

st.divider()

st.header("💡 성과 해석")


# ------------------------------------------------------------
# 전체 요약
# ------------------------------------------------------------

if total_conversion_change > 10:

    st.markdown(
        f"📈 **전체 전환수는 "
        f"{total_conversion_change:+.1f}% 증가했습니다.** "
        f"볼륨 확대 효과가 나타나고 있습니다."
    )

elif total_conversion_change < -10:

    st.markdown(
        f"📉 **전체 전환수는 "
        f"{total_conversion_change:+.1f}% 감소했습니다.** "
        f"예산, 유입량, CVR 변화를 함께 점검할 필요가 있습니다."
    )

else:

    st.markdown(
        "📊 **전체 전환수는 큰 변동이 없습니다.** "
        "현재 추세를 지속적으로 모니터링하는 것이 좋습니다."
    )


# ------------------------------------------------------------
# CPA
# ------------------------------------------------------------

if pd.notna(total_cpa_change):

    if total_cpa_change < -10:

        st.markdown(
            f"✅ **전체 CPA는 "
            f"{total_cpa_change:+.1f}% 개선되었습니다.** "
            f"효율과 볼륨이 함께 개선되는지 확인해보세요."
        )

    elif total_cpa_change > 10:

        st.markdown(
            f"⚠️ **전체 CPA는 "
            f"{total_cpa_change:+.1f}% 상승했습니다.** "
            f"예산 확대에 따른 효율 악화 여부를 확인할 필요가 있습니다."
        )


# ------------------------------------------------------------
# CVR
# ------------------------------------------------------------

if pd.notna(total_cvr_change):

    if total_cvr_change > 10:

        st.markdown(
            f"📈 **전체 CVR은 "
            f"{total_cvr_change:+.1f}% 개선되었습니다.**"
        )

    elif total_cvr_change < -10:

        st.markdown(
            f"📉 **전체 CVR은 "
            f"{total_cvr_change:+.1f}% 하락했습니다.** "
            f"랜딩페이지, 타겟, 소재 변화를 점검해보세요."
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
