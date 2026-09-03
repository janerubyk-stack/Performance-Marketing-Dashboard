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
    page_title="퍼널 분석 대시보드",
    page_icon="🔍",
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

st.title("🔍 퍼널 분석 대시보드")

st.caption(
    "노출 → 클릭 → 전환 흐름을 분석하여 "
    "어디에서 성과가 발생하고, 어디에서 개선이 필요한지 확인합니다."
)


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

    category_col = find_column([
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
        "date": date_col,
        "category": category_col,
        "media": media_col,
        "campaign": campaign_col,
        "impress": impress_col,
        "click": click_col,
        "spend": spend_col,
        "conversion": conversion_col
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
            category_col: "category",
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
    for col in [
        "impress",
        "click",
        "spend",
        "conversion"
    ]:

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


    # 문자
    for col in [
        "category",
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


    df = df.dropna(
        subset=["date"]
    ).copy()


    df["date"] = df["date"].dt.normalize()


    return (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )


# ============================================================
# 4. 데이터 불러오기
# ============================================================

try:

    df = load_data()

except Exception as e:

    st.error(
        f"Google Sheets 데이터를 불러오지 못했습니다.\n\n{e}"
    )

    st.stop()


if df.empty:

    st.warning(
        "데이터가 없습니다."
    )

    st.stop()


# ============================================================
# 5. 기간 계산
# ============================================================

def get_periods(
    base_date,
    period_type
):

    base_date = pd.Timestamp(
        base_date
    )


    if period_type == "전일":

        current_start = base_date
        current_end = base_date

        previous_start = (
            base_date -
            timedelta(days=1)
        )

        previous_end = previous_start


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

        current_start = base_date.replace(
            day=1
        )

        current_end = base_date

        previous_month_last = (
            base_date.replace(day=1)
            -
            timedelta(days=1)
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
            base_date.day,
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
# 6. 기간 표시
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
    [1, 1.7, 2]
)


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
# 지정 기간
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
            value=max(
                min_date,
                (
                    pd.Timestamp(base_date)
                    -
                    timedelta(days=6)
                ).date()
            ),
            min_value=min_date,
            max_value=base_date,
            key="funnel_current_start"
        )


        custom_current_end = st.date_input(
            "기준 종료일",
            value=base_date,
            min_value=min_date,
            max_value=max_date,
            key="funnel_current_end"
        )


    custom_elapsed_days = (
        pd.Timestamp(custom_current_end)
        -
        pd.Timestamp(custom_current_start)
    ).days + 1


    with custom_col2:

        st.markdown(
            f"**기준 기간 일수: "
            f"{custom_elapsed_days}일**"
        )


        custom_previous_start = st.date_input(
            "비교 시작일",
            value=max(
                min_date,
                (
                    pd.Timestamp(custom_current_start)
                    -
                    timedelta(days=custom_elapsed_days)
                ).date()
            ),
            min_value=min_date,
            max_value=max_date,
            key="funnel_previous_start"
        )


        custom_previous_end = st.date_input(
            "비교 종료일",
            value=max(
                min_date,
                (
                    pd.Timestamp(custom_previous_start)
                    +
                    timedelta(days=custom_elapsed_days - 1)
                ).date()
            ),
            min_value=min_date,
            max_value=max_date,
            key="funnel_previous_end"
        )


    previous_elapsed_days = (
        pd.Timestamp(custom_previous_end)
        -
        pd.Timestamp(custom_previous_start)
    ).days + 1


    if custom_elapsed_days != previous_elapsed_days:

        st.error(
            f"⚠️ 기준 기간은 "
            f"{custom_elapsed_days}일, "
            f"비교 기간은 "
            f"{previous_elapsed_days}일입니다. "
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
# 8. 분석 대상
# ============================================================

st.subheader("🎯 분석 대상")


category_options = sorted(
    df["category"]
    .unique()
    .tolist()
)


media_options = sorted(
    df["media"]
    .unique()
    .tolist()
)


campaign_options = sorted(
    df["campaign"]
    .unique()
    .tolist()
)


filter_col1, filter_col2, filter_col3 = st.columns(
    [1, 2, 2]
)


with filter_col1:

    selected_categories = st.multiselect(
        "카테고리",
        options=category_options,
        default=category_options,
        key="funnel_category_filter"
    )


with filter_col2:

    selected_media = st.multiselect(
        "매체 선택",
        options=media_options,
        default=media_options,
        key="funnel_media_filter"
    )


with filter_col3:

    selected_campaigns = st.multiselect(
        "캠페인 선택",
        options=campaign_options,
        default=campaign_options,
        key="funnel_campaign_filter"
    )


# ============================================================
# 9. 필터 데이터
# ============================================================

filtered_df = df[
    df["category"].isin(
        selected_categories
    )
    &
    df["media"].isin(
        selected_media
    )
    &
    df["campaign"].isin(
        selected_campaigns
    )
].copy()


# ============================================================
# 10. 집계 함수
# ============================================================

def aggregate_performance(
    data,
    start_date,
    end_date,
    group_cols=None
):

    temp = data[
        (data["date"] >= pd.Timestamp(start_date))
        &
        (data["date"] <= pd.Timestamp(end_date))
    ].copy()


    if group_cols is None:

        group_cols = []


    if temp.empty:

        columns = (
            group_cols
            +
            [
                "impress",
                "click",
                "spend",
                "conversion",
                "CTR",
                "CPC",
                "CVR",
                "CPA"
            ]
        )

        return pd.DataFrame(
            columns=columns
        )


    if group_cols:

        result = (
            temp
            .groupby(
                group_cols,
                as_index=False
            )
            .agg(
                impress=("impress", "sum"),
                click=("click", "sum"),
                spend=("spend", "sum"),
                conversion=("conversion", "sum")
            )
        )


    else:

        result = pd.DataFrame([
            {
                "impress":
                    temp["impress"].sum(),

                "click":
                    temp["click"].sum(),

                "spend":
                    temp["spend"].sum(),

                "conversion":
                    temp["conversion"].sum()
            }
        ])


    # CTR
    result["CTR"] = np.where(
        result["impress"] > 0,
        result["click"]
        /
        result["impress"]
        *
        100,
        np.nan
    )


    # CPC
    result["CPC"] = np.where(
        result["click"] > 0,
        result["spend"]
        /
        result["click"],
        np.nan
    )


    # CVR
    result["CVR"] = np.where(
        result["click"] > 0,
        result["conversion"]
        /
        result["click"]
        *
        100,
        np.nan
    )


    # CPA
    result["CPA"] = np.where(
        result["conversion"] > 0,
        result["spend"]
        /
        result["conversion"],
        np.nan
    )


    return result


# ============================================================
# 11. 현재 / 비교 전체
# ============================================================

current_total = aggregate_performance(
    filtered_df,
    current_start,
    current_end
)


previous_total = aggregate_performance(
    filtered_df,
    previous_start,
    previous_end
)


current = current_total.iloc[0]
previous = previous_total.iloc[0]


# ============================================================
# 12. 변화율
# ============================================================

def calc_change(
    current_value,
    previous_value
):

    if (
        pd.isna(current_value)
        or
        pd.isna(previous_value)
        or
        previous_value == 0
    ):

        return np.nan


    return (
        (
            current_value
            -
            previous_value
        )
        /
        previous_value
        *
        100
    )


# ============================================================
# 13. 퍼널 전체 현황
# ============================================================

st.divider()

st.header("🔻 퍼널 전체 현황")


funnel_col1, funnel_col2, funnel_col3 = st.columns(3)


with funnel_col1:

    st.metric(
        "노출",
        f"{current['impress']:,.0f}",
        (
            f"{calc_change(current['impress'], previous['impress']):+.1f}%"
            if pd.notna(
                calc_change(
                    current["impress"],
                    previous["impress"]
                )
            )
            else "-"
        )
    )


with funnel_col2:

    st.metric(
        "클릭",
        f"{current['click']:,.0f}",
        (
            f"{calc_change(current['click'], previous['click']):+.1f}%"
            if pd.notna(
                calc_change(
                    current["click"],
                    previous["click"]
                )
            )
            else "-"
        )
    )


with funnel_col3:

    st.metric(
        "전환",
        f"{current['conversion']:,.0f}",
        (
            f"{calc_change(current['conversion'], previous['conversion']):+.1f}%"
            if pd.notna(
                calc_change(
                    current["conversion"],
                    previous["conversion"]
                )
            )
            else "-"
        )
    )


# ============================================================
# 14. 퍼널 그래프
# ============================================================

st.subheader("📊 현재 기간 퍼널")


funnel_values = [
    current["impress"],
    current["click"],
    current["conversion"]
]


funnel_labels = [
    "노출",
    "클릭",
    "전환"
]


fig_funnel = go.Figure(
    go.Funnel(
        y=funnel_labels,
        x=funnel_values,
        textinfo="label+value+percent initial",
        hovertemplate=(
            "%{y}: %{x:,.0f}"
            "<extra></extra>"
        )
    )
)


fig_funnel.update_layout(
    height=400,
    margin=dict(
        l=50,
        r=50,
        t=30,
        b=30
    )
)


st.plotly_chart(
    fig_funnel,
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)


# ============================================================
# 15. 효율 지표
# ============================================================

st.subheader("📐 퍼널 효율 지표")


metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)


with metric_col1:

    ctr_change = calc_change(
        current["CTR"],
        previous["CTR"]
    )

    st.metric(
        "CTR",
        (
            f"{current['CTR']:.2f}%"
            if pd.notna(current["CTR"])
            else "-"
        ),
        (
            f"{ctr_change:+.1f}%"
            if pd.notna(ctr_change)
            else "-"
        )
    )


with metric_col2:

    cpc_change = calc_change(
        current["CPC"],
        previous["CPC"]
    )

    st.metric(
        "CPC",
        (
            f"{current['CPC']:,.0f}원"
            if pd.notna(current["CPC"])
            else "-"
        ),
        (
            f"{cpc_change:+.1f}%"
            if pd.notna(cpc_change)
            else "-"
        ),
        delta_color="inverse"
    )


with metric_col3:

    cvr_change = calc_change(
        current["CVR"],
        previous["CVR"]
    )

    st.metric(
        "CVR",
        (
            f"{current['CVR']:.2f}%"
            if pd.notna(current["CVR"])
            else "-"
        ),
        (
            f"{cvr_change:+.1f}%"
            if pd.notna(cvr_change)
            else "-"
        )
    )


with metric_col4:

    cpa_change = calc_change(
        current["CPA"],
        previous["CPA"]
    )

    st.metric(
        "CPA",
        (
            f"{current['CPA']:,.0f}원"
            if pd.notna(current["CPA"])
            else "-"
        ),
        (
            f"{cpa_change:+.1f}%"
            if pd.notna(cpa_change)
            else "-"
        ),
        delta_color="inverse"
    )


# ============================================================
# 16. 카테고리별 분석
# ============================================================

st.divider()

st.header("📂 카테고리별 퍼널 분석")


category_current = aggregate_performance(
    filtered_df,
    current_start,
    current_end,
    ["category"]
)


category_previous = aggregate_performance(
    filtered_df,
    previous_start,
    previous_end,
    ["category"]
)


if category_current.empty:

    st.info(
        "선택한 조건에 데이터가 없습니다."
    )

else:

    category_current = category_current.sort_values(
        "conversion",
        ascending=False
    )


    display_category = category_current[
        [
            "category",
            "impress",
            "click",
            "CTR",
            "conversion",
            "CVR",
            "spend",
            "CPC",
            "CPA"
        ]
    ].copy()


    display_category.columns = [
        "카테고리",
        "노출",
        "클릭",
        "CTR",
        "전환",
        "CVR",
        "광고비",
        "CPC",
        "CPA"
    ]


    st.dataframe(
        display_category.style.format(
            {
                "노출": "{:,.0f}",
                "클릭": "{:,.0f}",
                "CTR": "{:.2f}%",
                "전환": "{:,.0f}",
                "CVR": "{:.2f}%",
                "광고비": "{:,.0f}원",
                "CPC": "{:,.0f}원",
                "CPA": "{:,.0f}원"
            },
            na_rep="-"
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 17. 매체별 분석
# ============================================================

st.divider()

st.header("📡 매체별 퍼널 분석")


media_current = aggregate_performance(
    filtered_df,
    current_start,
    current_end,
    ["media"]
)


media_previous = aggregate_performance(
    filtered_df,
    previous_start,
    previous_end,
    ["media"]
)


if media_current.empty:

    st.info(
        "선택한 조건에 데이터가 없습니다."
    )

else:

    media_current = media_current.sort_values(
        "conversion",
        ascending=False
    )


    display_media = media_current[
        [
            "media",
            "impress",
            "click",
            "CTR",
            "conversion",
            "CVR",
            "spend",
            "CPC",
            "CPA"
        ]
    ].copy()


    display_media.columns = [
        "매체",
        "노출",
        "클릭",
        "CTR",
        "전환",
        "CVR",
        "광고비",
        "CPC",
        "CPA"
    ]


    st.dataframe(
        display_media.style.format(
            {
                "노출": "{:,.0f}",
                "클릭": "{:,.0f}",
                "CTR": "{:.2f}%",
                "전환": "{:,.0f}",
                "CVR": "{:.2f}%",
                "광고비": "{:,.0f}원",
                "CPC": "{:,.0f}원",
                "CPA": "{:,.0f}원"
            },
            na_rep="-"
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 18. 매체별 코멘트
# ============================================================

st.subheader("📝 매체별 성과 코멘트")


if not media_current.empty:

    total_conversion = current["conversion"]


    for _, row in media_current.iterrows():

        media = row["media"]

        conversion = row["conversion"]

        cpa = row["CPA"]

        cvr = row["CVR"]

        ctr = row["CTR"]

        share = (
            conversion
            /
            total_conversion
            *
            100
            if total_conversion > 0
            else np.nan
        )


        previous_row = media_previous[
            media_previous["media"] == media
        ]


        if not previous_row.empty:

            prev = previous_row.iloc[0]

            conversion_change = calc_change(
                conversion,
                prev["conversion"]
            )

            media_cpa_change = calc_change(
                cpa,
                prev["CPA"]
            )

            media_cvr_change = calc_change(
                cvr,
                prev["CVR"]
            )

        else:

            conversion_change = np.nan
            media_cpa_change = np.nan
            media_cvr_change = np.nan


        comment = (
            f"📌 **{media}** — "
            f"전환 **{conversion:,.0f}건**, "
            f"CPA "
        )


        if pd.notna(cpa):

            comment += f"**{cpa:,.0f}원**"

        else:

            comment += "**-**"


        if pd.notna(share):

            comment += (
                f", 전체 전환의 "
                f"**{share:.1f}%**"
            )


        if pd.notna(ctr):

            comment += (
                f", CTR **{ctr:.2f}%**"
            )


        if pd.notna(cvr):

            comment += (
                f", CVR **{cvr:.2f}%**"
            )


        if pd.notna(conversion_change):

            comment += (
                f", 전환 "
                f"**{conversion_change:+.1f}%**"
            )


        if pd.notna(media_cpa_change):

            comment += (
                f", CPA "
                f"**{media_cpa_change:+.1f}%**"
            )


        if pd.notna(media_cvr_change):

            comment += (
                f", CVR "
                f"**{media_cvr_change:+.1f}%**"
            )


        comment += "."

        st.markdown(comment)


        # ----------------------------------------------------
        # 개선 방향
        # ----------------------------------------------------

        if (
            pd.notna(cpa)
            and pd.notna(current["CPA"])
            and cpa < current["CPA"]
        ):

            st.caption(
                f"→ {media}: 전체 평균보다 낮은 CPA를 "
                f"기록하고 있어 현재 효율을 유지하면서 "
                f"예산 확대 가능성을 검토할 수 있습니다."
            )


        elif (
            pd.notna(cvr)
            and pd.notna(current["CVR"])
            and cvr < current["CVR"] * 0.8
        ):

            st.caption(
                f"→ {media}: 클릭 대비 전환 효율이 상대적으로 낮습니다. "
                f"랜딩페이지, 상품 적합성, 유입 타겟을 우선 점검하는 것이 좋습니다."
            )


        elif (
            pd.notna(ctr)
            and pd.notna(current["CTR"])
            and ctr < current["CTR"] * 0.8
        ):

            st.caption(
                f"→ {media}: 노출 대비 클릭률이 낮아 "
                f"소재와 타겟팅, 광고 노출 영역을 점검할 필요가 있습니다."
            )


        else:

            st.caption(
                f"→ {media}: 전환 볼륨과 CPA를 함께 확인하면서 "
                f"캠페인 단위의 효율 차이를 추가 분석하는 것이 좋습니다."
            )


# ============================================================
# 19. 캠페인 분석
# ============================================================

st.divider()

st.header("🔎 캠페인별 퍼널 분석")


campaign_current = aggregate_performance(
    filtered_df,
    current_start,
    current_end,
    ["campaign"]
)


campaign_previous = aggregate_performance(
    filtered_df,
    previous_start,
    previous_end,
    ["campaign"]
)


if campaign_current.empty:

    st.info(
        "선택한 조건에 데이터가 없습니다."
    )

else:

    campaign_current = campaign_current.sort_values(
        "conversion",
        ascending=False
    )


    display_campaign = campaign_current[
        [
            "campaign",
            "impress",
            "click",
            "CTR",
            "conversion",
            "CVR",
            "spend",
            "CPC",
            "CPA"
        ]
    ].copy()


    display_campaign.columns = [
        "캠페인",
        "노출",
        "클릭",
        "CTR",
        "전환",
        "CVR",
        "광고비",
        "CPC",
        "CPA"
    ]


    st.dataframe(
        display_campaign.style.format(
            {
                "노출": "{:,.0f}",
                "클릭": "{:,.0f}",
                "CTR": "{:.2f}%",
                "전환": "{:,.0f}",
                "CVR": "{:.2f}%",
                "광고비": "{:,.0f}원",
                "CPC": "{:,.0f}원",
                "CPA": "{:,.0f}원"
            },
            na_rep="-"
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 20. 캠페인 성과 코멘트
# ============================================================

st.subheader("📝 캠페인 성과 코멘트")


if not campaign_current.empty:

    valid_campaigns = campaign_current[
        campaign_current["conversion"] > 0
    ].copy()


    if valid_campaigns.empty:

        st.info(
            "현재 기간에 전환이 발생한 캠페인이 없습니다."
        )

    else:

        total_conversion = current["conversion"]


        # ====================================================
        # CPA 최우수
        # ====================================================

        cpa_valid = valid_campaigns[
            valid_campaigns["CPA"].notna()
            &
            (valid_campaigns["CPA"] > 0)
        ]


        if not cpa_valid.empty:

            best = cpa_valid.loc[
                cpa_valid["CPA"].idxmin()
            ]


            share = (
                best["conversion"]
                /
                total_conversion
                *
                100
                if total_conversion > 0
                else np.nan
            )


            st.markdown(
                f"🏆 **CPA 최우수 캠페인:** "
                f"`{best['campaign']}` — "
                f"CPA **{best['CPA']:,.0f}원**, "
                f"전환 **{best['conversion']:,.0f}건** "
                f"(전체 전환의 **{share:.1f}%**)"
            )


        # ====================================================
        # 전환수 최다
        # ====================================================

        best_conversion = valid_campaigns.loc[
            valid_campaigns["conversion"].idxmax()
        ]


        share = (
            best_conversion["conversion"]
            /
            total_conversion
            *
            100
            if total_conversion > 0
            else np.nan
        )


        st.markdown(
            f"📈 **전환수 최다 캠페인:** "
            f"`{best_conversion['campaign']}` — "
            f"전환 **{best_conversion['conversion']:,.0f}건**, "
            f"CPA "
            f"**{best_conversion['CPA']:,.0f}원** "
            f"(전체 전환의 **{share:.1f}%**)"
        )


        # ====================================================
        # 전환 증가폭
        # ====================================================

        growth_rows = []


        for _, row in campaign_current.iterrows():

            previous_row = campaign_previous[
                campaign_previous["campaign"]
                ==
                row["campaign"]
            ]


            if previous_row.empty:

                continue


            prev = previous_row.iloc[0]


            change = calc_change(
                row["conversion"],
                prev["conversion"]
            )


            if pd.notna(change):

                growth_rows.append({
                    "campaign": row["campaign"],
                    "change": change,
                    "current": row["conversion"],
                    "previous": prev["conversion"]
                })


        if growth_rows:

            growth_df = pd.DataFrame(
                growth_rows
            )


            positive_growth = growth_df[
                growth_df["change"] > 0
            ]


            if not positive_growth.empty:

                growth_best = positive_growth.loc[
                    positive_growth["change"].idxmax()
                ]


                st.markdown(
                    f"🚀 **전환 증가폭 최대 캠페인:** "
                    f"`{growth_best['campaign']}` — "
                    f"전환 "
                    f"**{growth_best['change']:+.1f}%** "
                    f"(비교 "
                    f"{growth_best['previous']:,.0f}건 → "
                    f"기준 "
                    f"{growth_best['current']:,.0f}건)"
                )


        # ====================================================
        # CPA 개선
        # ====================================================

        cpa_rows = []


        for _, row in campaign_current.iterrows():

            if pd.isna(row["CPA"]):

                continue


            previous_row = campaign_previous[
                campaign_previous["campaign"]
                ==
                row["campaign"]
            ]


            if previous_row.empty:

                continue


            prev = previous_row.iloc[0]


            change = calc_change(
                row["CPA"],
                prev["CPA"]
            )


            if pd.notna(change):

                cpa_rows.append({
                    "campaign": row["campaign"],
                    "change": change,
                    "current": row["CPA"],
                    "previous": prev["CPA"]
                })


        if cpa_rows:

            cpa_change_df = pd.DataFrame(
                cpa_rows
            )


            improved = cpa_change_df[
                cpa_change_df["change"] < 0
            ]


            if not improved.empty:

                best_improved = improved.loc[
                    improved["change"].idxmin()
                ]


                st.markdown(
                    f"✅ **CPA 개선폭 최대 캠페인:** "
                    f"`{best_improved['campaign']}` — "
                    f"CPA "
                    f"**{best_improved['change']:+.1f}%** "
                    f"("
                    f"{best_improved['previous']:,.0f}원 → "
                    f"{best_improved['current']:,.0f}원)"
                )


            # CPA 악화
            worsened = cpa_change_df[
                cpa_change_df["change"] > 0
            ]


            if not worsened.empty:

                worst = worsened.loc[
                    worsened["change"].idxmax()
                ]


                st.markdown(
                    f"⚠️ **CPA 악화폭 최대 캠페인:** "
                    f"`{worst['campaign']}` — "
                    f"CPA "
                    f"**{worst['change']:+.1f}%** "
                    f"("
                    f"{worst['previous']:,.0f}원 → "
                    f"{worst['current']:,.0f}원)"
                )


        # ====================================================
        # CVR 개선
        # ====================================================

        cvr_rows = []


        for _, row in campaign_current.iterrows():

            if pd.isna(row["CVR"]):

                continue


            previous_row = campaign_previous[
                campaign_previous["campaign"]
                ==
                row["campaign"]
            ]


            if previous_row.empty:

                continue


            prev = previous_row.iloc[0]


            change = calc_change(
                row["CVR"],
                prev["CVR"]
            )


            if pd.notna(change):

                cvr_rows.append({
                    "campaign": row["campaign"],
                    "change": change,
                    "current": row["CVR"],
                    "previous": prev["CVR"]
                })


        if cvr_rows:

            cvr_df = pd.DataFrame(
                cvr_rows
            )


            cvr_improved = cvr_df[
                cvr_df["change"] > 0
            ]


            if not cvr_improved.empty:

                cvr_best = cvr_improved.loc[
                    cvr_improved["change"].idxmax()
                ]


                st.markdown(
                    f"📊 **CVR 개선폭 최대 캠페인:** "
                    f"`{cvr_best['campaign']}` — "
                    f"CVR "
                    f"**{cvr_best['change']:+.1f}%** "
                    f"("
                    f"{cvr_best['previous']:.2f}% → "
                    f"{cvr_best['current']:.2f}%"
                    f")"
                )


        # ====================================================
        # 상세 저효율 캠페인
        # ====================================================

        if pd.notna(current["CPA"]) and current["CPA"] > 0:

            inefficient = valid_campaigns[
                valid_campaigns["CPA"]
                >
                current["CPA"] * 1.5
            ].copy()


            inefficient = inefficient.sort_values(
                "CPA",
                ascending=False
            )


            for _, row in inefficient.head(3).iterrows():

                ratio = (
                    row["CPA"]
                    /
                    current["CPA"]
                    *
                    100
                )


                st.markdown(
                    f"⚠️ **효율 점검 필요:** "
                    f"`{row['campaign']}` — "
                    f"CPA **{row['CPA']:,.0f}원**, "
                    f"전체 평균 CPA의 "
                    f"**{ratio:.0f}%** 수준이며 "
                    f"전환 **{row['conversion']:,.0f}건**을 "
                    f"기록했습니다."
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
        "선택 카테고리: "
        +
        (
            ", ".join(selected_categories)
            if selected_categories
            else "없음"
        )
    )

    st.write(
        f"선택 매체: "
        f"{len(selected_media)}개"
    )

    st.write(
        f"선택 캠페인: "
        f"{len(selected_campaigns)}개"
    )
