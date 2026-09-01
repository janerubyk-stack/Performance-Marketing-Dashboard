import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
import calendar
import html as html_lib


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

    # F열의 광고유형 / Type
    type_col = find_column([
        "Type",
        "type",
        "광고유형",
        "광고 유형",
        "유형"
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
            f"필수 컬럼을 찾을 수 없습니다: {missing}\n"
            f"현재 컬럼: {df.columns.tolist()}"
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
            .str.replace(" ", "", regex=False)
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # 문자 컬럼
    # --------------------------------------------------------

    text_cols = [
        "type",
        "media",
        "campaign"
    ]

    for col in text_cols:

        df[col] = (
            df[col]
            .fillna("미분류")
            .astype(str)
            .str.strip()
        )

        df.loc[
            df[col].isin(["", "nan", "None"]),
            col
        ] = "미분류"

    # --------------------------------------------------------
    # Type 값 정리
    # --------------------------------------------------------

    df["type"] = (
        df["type"]
        .str.replace(" ", "", regex=False)
        .str.upper()
    )

    # SNS / DA 외 값은 그대로 유지
    df.loc[
        df["type"].isin(["", "NAN", "NONE"]),
        "type"
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

    print("데이터 건수:", f"{len(df):,}")

    if len(df) > 0:

        print(
            "시작 날짜:",
            df["date"].min().date()
        )

        print(
            "최신 날짜:",
            df["date"].max().date()
        )

        print(
            "Type:",
            df["type"].unique().tolist()
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

        current_start = base_date.replace(
            day=1
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
# 7. 성과 계산
# ============================================================

def calculate_metrics(result):

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
# 8. 기간별 집계
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

    return calculate_metrics(result)


# ============================================================
# 9. 매체 기준 집계
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


# ============================================================
# 10. 캠페인 기준 집계
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


# ============================================================
# 11. 비교 데이터 생성
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
            and c_spend > 0
            else np.nan
        )

        p_cpa = (
            p_spend / p_conversion
            if p_conversion > 0
            and p_spend > 0
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
    # 변화율 함수
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
# 12. 상단 분석 조건
# ============================================================

st.subheader("🔎 분석 조건")

col1, col2, col3 = st.columns(
    [1, 1.5, 2]
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
            "전월",
            "지정"
        ],
        horizontal=True
    )


# ============================================================
# 13. 기간 설정
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

else:

    st.markdown("#### 📅 지정 기간")

    custom_col1, custom_col2 = st.columns(2)

    with custom_col1:

        current_start_date = st.date_input(
            "기준 기간 시작일",
            value=(
                pd.Timestamp(base_date)
                - timedelta(days=6)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_current_start"
        )

        current_end_date = st.date_input(
            "기준 기간 종료일",
            value=base_date,
            min_value=min_date,
            max_value=max_date,
            key="custom_current_end"
        )

    with custom_col2:

        previous_start_date = st.date_input(
            "비교 기간 시작일",
            value=(
                pd.Timestamp(base_date)
                - timedelta(days=13)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_start"
        )

        previous_end_date = st.date_input(
            "비교 기간 종료일",
            value=(
                pd.Timestamp(base_date)
                - timedelta(days=7)
            ).date(),
            min_value=min_date,
            max_value=max_date,
            key="custom_previous_end"
        )

    current_start = pd.Timestamp(
        current_start_date
    )

    current_end = pd.Timestamp(
        current_end_date
    )

    previous_start = pd.Timestamp(
        previous_start_date
    )

    previous_end = pd.Timestamp(
        previous_end_date
    )

    current_days = (
        current_end -
        current_start
    ).days + 1

    previous_days = (
        previous_end -
        previous_start
    ).days + 1

    if current_start > current_end:

        st.error(
            "기준 기간의 시작일은 종료일보다 빠르거나 같아야 합니다."
        )

        st.stop()

    if previous_start > previous_end:

        st.error(
            "비교 기간의 시작일은 종료일보다 빠르거나 같아야 합니다."
        )

        st.stop()

    if current_days != previous_days:

        st.error(
            f"⚠️ 두 기간의 일수가 다릅니다. "
            f"기준 기간 {current_days}일 / "
            f"비교 기간 {previous_days}일로 "
            f"동일한 일수로 지정해주세요."
        )

        st.stop()


# ============================================================
# 14. 기간 정보
# ============================================================

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
# 15. Type / 매체 / 캠페인 필터
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
    [1, 1.2, 2]
)


# ------------------------------------------------------------
# Type
# ------------------------------------------------------------

with filter_col1:

    selected_types = st.multiselect(
        "Type 선택",
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
# 16. 전체 선택 버튼
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
# 17. 필터 데이터
# ============================================================

filtered_df = df[
    df["type"].isin(selected_types) &
    df["media"].isin(selected_media) &
    df["campaign"].isin(selected_campaigns)
].copy()


# ============================================================
# 18. 현재 / 비교 데이터
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
# 19. 매체 비교
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


def change_text(value):

    if pd.isna(value):
        return "-"

    value = float(value)

    if value > 0:

        return f"▲ +{value:,.1f}%"

    elif value < 0:

        return f"▼ {value:,.1f}%"

    return "─ 0.0%"


# ============================================================
# 21. 전체 성과 요약
# ============================================================

st.divider()

st.header("📊 전체 성과 요약")

total_current_spend = (
    current_media["spend"].sum()
)

total_previous_spend = (
    previous_media["spend"].sum()
)

total_current_conversion = (
    current_media["conversion"].sum()
)

total_previous_conversion = (
    previous_media["conversion"].sum()
)

total_current_cpa = (
    total_current_spend /
    total_current_conversion
    if total_current_conversion > 0
    and total_current_spend > 0
    else np.nan
)

total_previous_cpa = (
    total_previous_spend /
    total_previous_conversion
    if total_previous_conversion > 0
    and total_previous_spend > 0
    else np.nan
)

total_conversion_change = (
    (
        total_current_conversion -
        total_previous_conversion
    )
    / total_previous_conversion
    * 100
    if total_previous_conversion > 0
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
        pd.notna(total_current_cpa)
        and pd.notna(total_previous_cpa)
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


summary_col1, summary_col2, summary_col3 = st.columns(3)


with summary_col1:

    st.metric(
        "전환수",
        f"{total_current_conversion:,.0f}건",
        (
            f"{total_conversion_change:+.1f}%"
            if pd.notna(total_conversion_change)
            else None
        )
    )


with summary_col2:

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
            else None
        ),
        delta_color="inverse"
    )


with summary_col3:

    st.metric(
        "광고비",
        f"{total_current_spend:,.0f}원",
        (
            f"{total_spend_change:+.1f}%"
            if pd.notna(total_spend_change)
            else None
        )
    )


# ============================================================
# 22. 성과 추이
# ============================================================

st.divider()

st.header("📈 성과 추이")

st.caption(
    "선택한 Type / 매체 / 캠페인 기준으로 전체 기간의 성과 추이를 확인합니다."
)


# ------------------------------------------------------------
# 추이 데이터
# ------------------------------------------------------------

trend_df = filtered_df.copy()

if not trend_df.empty:

    trend_df["date"] = pd.to_datetime(
        trend_df["date"]
    )

    daily_trend = (
        trend_df
        .groupby("date", as_index=False)
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )

    daily_trend["CPA"] = np.where(
        daily_trend["conversion"] > 0,
        daily_trend["spend"] /
        daily_trend["conversion"],
        np.nan
    )

    # 주차별
    weekly_trend = (
        trend_df
        .assign(
            week=trend_df["date"].dt.to_period("W-MON")
        )
        .groupby("week", as_index=False)
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )

    weekly_trend["주차"] = (
        weekly_trend["week"]
        .astype(str)
    )

    weekly_trend["CPA"] = np.where(
        weekly_trend["conversion"] > 0,
        weekly_trend["spend"] /
        weekly_trend["conversion"],
        np.nan
    )

    # 월별
    monthly_trend = (
        trend_df
        .assign(
            month=trend_df["date"].dt.to_period("M")
        )
        .groupby("month", as_index=False)
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
            conversion=("conversion", "sum")
        )
    )

    monthly_trend["월"] = (
        monthly_trend["month"]
        .astype(str)
    )

    monthly_trend["CPA"] = np.where(
        monthly_trend["conversion"] > 0,
        monthly_trend["spend"] /
        monthly_trend["conversion"],
        np.nan
    )

else:

    daily_trend = pd.DataFrame()
    weekly_trend = pd.DataFrame()
    monthly_trend = pd.DataFrame()


trend_tab1, trend_tab2, trend_tab3 = st.tabs(
    [
        "📅 일자별",
        "📆 주차별",
        "🗓️ 월별"
    ]
)


# ============================================================
# 23. 일자별 추이
# ============================================================

def create_trend_chart(
    trend_data,
    x_col,
    title
):

    fig = go.Figure()

    if trend_data.empty:

        fig.update_layout(
            title=title,
            height=420
        )

        return fig

    fig.add_trace(
        go.Bar(
            x=trend_data[x_col],
            y=trend_data["CPA"],
            name="CPA",
            text=[
                cpa_text(v)
                for v in trend_data["CPA"]
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
            x=trend_data[x_col],
            y=trend_data["conversion"],
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

        height=430,

        margin=dict(
            l=60,
            r=70,
            t=80,
            b=80
        ),

        xaxis=dict(
            title="기간",
            type="category",
            tickangle=-45,
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

    return fig


with trend_tab1:

    fig_daily = create_trend_chart(
        daily_trend,
        "date",
        "일자별 CPA + 전환수 추이"
    )

    st.plotly_chart(
        fig_daily,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


# ============================================================
# 24. 주차별 추이
# ============================================================

with trend_tab2:

    fig_weekly = create_trend_chart(
        weekly_trend,
        "주차",
        "주차별 CPA + 전환수 추이"
    )

    st.plotly_chart(
        fig_weekly,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


# ============================================================
# 25. 월별 추이
# ============================================================

with trend_tab3:

    fig_monthly = create_trend_chart(
        monthly_trend,
        "월",
        "월별 CPA + 전환수 추이"
    )

    st.plotly_chart(
        fig_monthly,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


# ============================================================
# 26. 성과 비교
# ============================================================

st.divider()

st.header("📊 성과 비교")

st.caption(
    f"기준 기간: {current_period_text}  |  "
    f"비교 기간: {previous_period_text}  |  "
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
# 27. CPA + 전환수 차트
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
# 28. 광고비 + 전환수 차트
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
# 29. 그래프 표시
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
# 30. 매체별 상세 비교표
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

.change-up {
    color: #d62728;
    font-weight: 700;
}

.change-down {
    color: #2468c7;
    font-weight: 700;
}

.change-neutral {
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
        f"<th>{html_lib.escape(str(media))}</th>"
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
                '<span class="change-neutral">-</span>'
            )

        elif change_value > 0:

            change_html = (
                '<span class="change-up">'
                f'▲ +{change_value:,.1f}%'
                '</span>'
            )

        elif change_value < 0:

            change_html = (
                '<span class="change-down">'
                f'▼ {change_value:,.1f}%'
                '</span>'
            )

        else:

            change_html = (
                '<span class="change-neutral">'
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
# 31. 성과 해석 함수
# ============================================================

def make_performance_comments(
    result_df
):

    comments = []

    if (
        result_df is None
        or result_df.empty
    ):

        return [
            "비교할 데이터가 없습니다."
        ]

    df_comment = result_df.copy()

    # --------------------------------------------------------
    # 컬럼별 숫자 변환
    # --------------------------------------------------------

    numeric_cols = [

        "기준 광고비",
        "비교 광고비",

        "기준 전환수",
        "비교 전환수",

        "기준 CPA",
        "비교 CPA",

        "기준 CVR",
        "비교 CVR"
    ]

    for col in numeric_cols:

        if col in df_comment.columns:

            df_comment[col] = pd.to_numeric(
                df_comment[col],
                errors="coerce"
            )

    # --------------------------------------------------------
    # 개별 분석
    # --------------------------------------------------------

    for _, row in df_comment.iterrows():

        target = str(
            row.get(
                "분석 대상",
                row.get(
                    "media",
                    row.get(
                        "campaign",
                        "전체"
                    )
                )
            )
        )

        if (
            target == "nan"
            or target == "None"
        ):

            target = "전체"

        spend_current = float(
            row.get(
                "기준 광고비",
                0
            )
            or 0
        )

        spend_previous = float(
            row.get(
                "비교 광고비",
                0
            )
            or 0
        )

        conv_current = float(
            row.get(
                "기준 전환수",
                0
            )
            or 0
        )

        conv_previous = float(
            row.get(
                "비교 전환수",
                0
            )
            or 0
        )

        cpa_current = row.get(
            "기준 CPA",
            np.nan
        )

        cpa_previous = row.get(
            "비교 CPA",
            np.nan
        )

        cvr_current = row.get(
            "기준 CVR",
            np.nan
        )

        cvr_previous = row.get(
            "비교 CVR",
            np.nan
        )

        cpa_current = (
            float(cpa_current)
            if pd.notna(cpa_current)
            else np.nan
        )

        cpa_previous = (
            float(cpa_previous)
            if pd.notna(cpa_previous)
            else np.nan
        )

        cvr_current = (
            float(cvr_current)
            if pd.notna(cvr_current)
            else np.nan
        )

        cvr_previous = (
            float(cvr_previous)
            if pd.notna(cvr_previous)
            else np.nan
        )

        # ----------------------------------------------------
        # 변화율
        # ----------------------------------------------------

        spend_change = None

        conv_change = None

        cpa_change = None

        cvr_change = None

        if spend_previous != 0:

            spend_change = (
                (spend_current - spend_previous)
                / spend_previous
                * 100
            )

        if conv_previous != 0:

            conv_change = (
                (conv_current - conv_previous)
                / conv_previous
                * 100
            )

        if (
            pd.notna(cpa_current)
            and pd.notna(cpa_previous)
            and cpa_previous != 0
        ):

            cpa_change = (
                (cpa_current - cpa_previous)
                / cpa_previous
                * 100
            )

        if (
            pd.notna(cvr_current)
            and pd.notna(cvr_previous)
            and cvr_previous != 0
        ):

            cvr_change = (
                (cvr_current - cvr_previous)
                / cvr_previous
                * 100
            )

        target_comments = []

        # ----------------------------------------------------
        # ① 전환 증가 + CPA 개선
        # ----------------------------------------------------

        if (
            conv_change is not None
            and conv_change > 10
            and cpa_change is not None
            and cpa_change < -10
        ):

            target_comments.append(
                f"**{target}**: 전환수는 "
                f"{conv_change:+.1f}% 증가했고 CPA는 "
                f"{cpa_change:+.1f}% 개선되어 "
                f"**볼륨과 효율이 동시에 개선된 좋은 성과**입니다."
            )

        # ----------------------------------------------------
        # ② 전환 증가 + CPA 상승
        # ----------------------------------------------------

        elif (
            conv_change is not None
            and conv_change > 10
            and cpa_change is not None
            and cpa_change > 10
        ):

            target_comments.append(
                f"**{target}**: 전환수는 "
                f"{conv_change:+.1f}% 증가했지만 CPA도 "
                f"{cpa_change:+.1f}% 상승했습니다. "
                f"**볼륨 확대 과정에서 효율이 악화되는지 확인이 필요합니다.**"
            )

        # ----------------------------------------------------
        # ③ 전환 감소 + CPA 개선
        # ----------------------------------------------------

        elif (
            conv_change is not None
            and conv_change < -10
            and cpa_change is not None
            and cpa_change < -10
        ):

            target_comments.append(
                f"**{target}**: CPA는 "
                f"{cpa_change:+.1f}% 개선됐지만 전환수는 "
                f"{conv_change:+.1f}% 감소했습니다. "
                f"**효율은 좋아졌지만 볼륨이 줄어든 상황입니다.**"
            )

        # ----------------------------------------------------
        # ④ 전환 감소 + CPA 악화
        # ----------------------------------------------------

        elif (
            conv_change is not None
            and conv_change < -10
            and cpa_change is not None
            and cpa_change > 10
        ):

            target_comments.append(
                f"**{target}**: 전환수는 "
                f"{conv_change:+.1f}% 감소했고 CPA는 "
                f"{cpa_change:+.1f}% 상승했습니다. "
                f"**성과 악화가 뚜렷해 우선 점검이 필요한 대상입니다.**"
            )

        # ----------------------------------------------------
        # ⑤ 전환 증가
        # ----------------------------------------------------

        elif (
            conv_change is not None
            and conv_change > 10
        ):

            target_comments.append(
                f"**{target}**: 전환수가 "
                f"{conv_change:+.1f}% 증가했습니다. "
                f"**현재 볼륨 확대 효과가 나타나고 있습니다.**"
            )

        # ----------------------------------------------------
        # ⑥ 전환 감소
        # ----------------------------------------------------

        elif (
            conv_change is not None
            and conv_change < -10
        ):

            target_comments.append(
                f"**{target}**: 전환수가 "
                f"{conv_change:+.1f}% 감소했습니다. "
                f"**예산, 유입량, CVR 변화를 함께 점검하는 것이 좋습니다.**"
            )

        # ----------------------------------------------------
        # ⑦ 변화 작음
        # ----------------------------------------------------

        else:

            target_comments.append(
                f"**{target}**: 전반적으로 큰 변동은 없습니다. "
                f"추세를 지속적으로 모니터링하세요."
            )

        # ----------------------------------------------------
        # CVR 분석
        # ----------------------------------------------------

        if (
            cvr_change is not None
            and cvr_change > 10
        ):

            target_comments.append(
                f"→ CVR은 **{cvr_change:+.1f}%** 개선되었습니다."
            )

        elif (
            cvr_change is not None
            and cvr_change < -10
        ):

            target_comments.append(
                f"→ CVR은 **{cvr_change:+.1f}%** 하락했습니다. "
                f"랜딩페이지와 타겟/소재를 점검해보세요."
            )

        comments.extend(
            target_comments
        )

    # ========================================================
    # 전체 성과
    # ========================================================

    total_current_spend = (
        df_comment["기준 광고비"].sum()
        if "기준 광고비" in df_comment.columns
        else 0
    )

    total_previous_spend = (
        df_comment["비교 광고비"].sum()
        if "비교 광고비" in df_comment.columns
        else 0
    )

    total_current_conv = (
        df_comment["기준 전환수"].sum()
        if "기준 전환수" in df_comment.columns
        else 0
    )

    total_previous_conv = (
        df_comment["비교 전환수"].sum()
        if "비교 전환수" in df_comment.columns
        else 0
    )

    if total_previous_spend > 0:

        total_spend_change = (
            (
                total_current_spend -
                total_previous_spend
            )
            / total_previous_spend
            * 100
        )

    else:

        total_spend_change = None

    if total_previous_conv > 0:

        total_conv_change = (
            (
                total_current_conv -
                total_previous_conv
            )
            / total_previous_conv
            * 100
        )

    else:

        total_conv_change = None

    total_current_cpa = (
        total_current_spend /
        total_current_conv
        if (
            total_current_conv > 0
            and total_current_spend > 0
        )
        else np.nan
    )

    total_previous_cpa = (
        total_previous_spend /
        total_previous_conv
        if (
            total_previous_conv > 0
            and total_previous_spend > 0
        )
        else np.nan
    )

    if (
        pd.notna(total_previous_cpa)
        and total_previous_cpa > 0
        and pd.notna(total_current_cpa)
    ):

        total_cpa_change = (
            (
                total_current_cpa -
                total_previous_cpa
            )
            / total_previous_cpa
            * 100
        )

    else:

        total_cpa_change = None

    comments.insert(
        0,
        "### 📊 전체 성과 요약"
    )

    if total_conv_change is not None:

        comments.append(
            f"**전체 전환수:** "
            f"{total_current_conv:,.0f}건 "
            f"({total_conv_change:+.1f}%)"
        )

    if total_cpa_change is not None:

        if total_cpa_change < 0:

            comments.append(
                f"**전체 CPA:** "
                f"{total_current_cpa:,.0f}원 "
                f"({total_cpa_change:+.1f}%) "
                f"→ **효율 개선**"
            )

        else:

            comments.append(
                f"**전체 CPA:** "
                f"{total_current_cpa:,.0f}원 "
                f"({total_cpa_change:+.1f}%) "
                f"→ **효율 악화**"
            )

    if total_spend_change is not None:

        comments.append(
            f"**전체 광고비:** "
            f"{total_current_spend:,.0f}원 "
            f"({total_spend_change:+.1f}%)"
        )

    return comments


# ============================================================
# 32. 성과 해석
# ============================================================

st.divider()

st.header("💡 성과 해석")


# ------------------------------------------------------------
# 매체별 코멘트용 데이터 생성
# ------------------------------------------------------------

comment_media = comparison.copy()

comment_media = comment_media[
    comment_media["media"].isin(
        selected_media
    )
].copy()

comment_media["분석 대상"] = (
    comment_media["media"]
)


comment_media_for_ai = pd.DataFrame({

    "분석 대상":
        comment_media["분석 대상"],

    "기준 광고비":
        comment_media["spend_current"],

    "비교 광고비":
        comment_media["spend_previous"],

    "기준 전환수":
        comment_media["conversion_current"],

    "비교 전환수":
        comment_media["conversion_previous"],

    "기준 CPA":
        comment_media["CPA_current"],

    "비교 CPA":
        comment_media["CPA_previous"],

    "기준 CVR":
        comment_media["CVR_current"],

    "비교 CVR":
        comment_media["CVR_previous"]
})


comments = make_performance_comments(
    comment_media_for_ai
)


# ------------------------------------------------------------
# 전체 성과 요약은 이미 위에 표시했으므로
# 코멘트에서는 전체 요약 부분을 중복 표시하지 않음
# ------------------------------------------------------------

for comment in comments:

    if comment == "### 📊 전체 성과 요약":

        continue

    st.markdown(
        f"- {comment}"
    )


# ============================================================
# 33. 캠페인 드릴다운
# ============================================================

st.divider()

st.header("🔍 캠페인 드릴다운")

st.caption(
    "선택한 캠페인을 기준으로 현재 기간과 비교 기간의 상세 성과를 확인합니다."
)


# ============================================================
# 34. 캠페인 기준 집계
# ============================================================

current_campaign = aggregate_by_campaign(
    current_df
)

previous_campaign = aggregate_by_campaign(
    previous_df
)


# ============================================================
# 35. 캠페인 비교
# ============================================================

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
# 36. 캠페인 비교 HTML
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

.campaign-up {

    color: #d62728;

    font-weight: 700;

}

.campaign-down {

    color: #2468c7;

    font-weight: 700;

}

.campaign-neutral {

    color: #666666;

    font-weight: 700;

}

</style>

<table class="campaign-table">

<tr>

<th>지표</th>

"""


for campaign in campaign_table["campaign"]:

    campaign_html += (
        f"<th>{html_lib.escape(str(campaign))}</th>"
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

        if pd.isna(change_value):

            change_html = (
                '<span class="campaign-neutral">-</span>'
            )

        elif change_value > 0:

            change_html = (
                '<span class="campaign-up">'
                f'▲ +{change_value:,.1f}%'
                '</span>'
            )

        elif change_value < 0:

            change_html = (
                '<span class="campaign-down">'
                f'▼ {change_value:,.1f}%'
                '</span>'
            )

        else:

            change_html = (
                '<span class="campaign-neutral">'
                '─ 0.0%'
                '</span>'
            )

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
# 37. 캠페인 성과 코멘트
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
        # CPA 최우수
        # ----------------------------------------------------
        # 중요:
        # 광고비가 0원이면 CPA를 계산하지 않음.
        # CPA 0원 캠페인은 최우수 후보에서 제외.
        # ----------------------------------------------------

        cpa_valid = campaign_table[
            (campaign_table["conversion_current"] > 0) &
            (campaign_table["spend_current"] > 0) &
            (campaign_table["CPA_current"].notna()) &
            (campaign_table["CPA_current"] > 0)
        ].copy()

        if not cpa_valid.empty:

            best = cpa_valid.loc[
                cpa_valid["CPA_current"].idxmin()
            ]

            st.markdown(
                f"🏆 **CPA 최우수 캠페인:** "
                f"`{best['campaign']}` "
                f"({best['CPA_current']:,.0f}원 / "
                f"전환 {best['conversion_current']:,.0f}건 / "
                f"광고비 {best['spend_current']:,.0f}원)"
            )

        else:

            st.info(
                "현재 기간에 광고비와 전환이 정상적으로 발생하여 "
                "CPA를 산출할 수 있는 캠페인이 없습니다."
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
        # 전환 증가폭 최대
        # ----------------------------------------------------

        growth = campaign_table[
            campaign_table[
                "conversion_change"
            ].notna()
        ].copy()

        if not growth.empty:

            growth_best = growth.loc[
                growth[
                    "conversion_change"
                ].idxmax()
            ]

            if growth_best[
                "conversion_change"
            ] > 0:

                st.markdown(
                    f"🚀 **전환 증가폭 최대:** "
                    f"`{growth_best['campaign']}` "
                    f"({growth_best['conversion_change']:+,.1f}%)"
                )

        # ----------------------------------------------------
        # CPA 악화
        # ----------------------------------------------------

        cpa_change = campaign_table[
            campaign_table[
                "CPA_change"
            ].notna()
        ].copy()

        if not cpa_change.empty:

            worst = cpa_change.loc[
                cpa_change[
                    "CPA_change"
                ].idxmax()
            ]

            if worst[
                "CPA_change"
            ] > 0:

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
# 38. 데이터 정보
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
        f"선택 Type: "
        f"{', '.join(selected_types)}"
    )

    st.write(
        f"선택 매체: "
        f"{', '.join(selected_media)}"
    )

    st.write(
        f"선택 캠페인: "
        f"{len(selected_campaigns):,}개"
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
