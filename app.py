import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
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
# 2. CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 36px;
        font-weight: 800;
        color: #1f2937;
        margin-bottom: 5px;
    }

    .sub-title {
        color: #6b7280;
        font-size: 15px;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 25px;
        font-weight: 700;
        color: #1f2937;
        margin-top: 25px;
        margin-bottom: 12px;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .metric-title {
        font-size: 14px;
        color: #6b7280;
        margin-bottom: 5px;
    }

    .metric-value {
        font-size: 25px;
        font-weight: 700;
        color: #111827;
    }

    .comment-box {
        background: #f8fafc;
        border-left: 4px solid #64748b;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 10px;
        margin-bottom: 10px;
        line-height: 1.75;
    }

    .good {
        color: #15803d;
        font-weight: 700;
    }

    .bad {
        color: #dc2626;
        font-weight: 700;
    }

    .neutral {
        color: #6b7280;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. 데이터 불러오기
# ============================================================

@st.cache_data(ttl=300)
def load_data():

    try:

        df = pd.read_csv(
            SHEET_URL,
            encoding="utf-8-sig"
        )

    except Exception as e:

        st.error("Google Sheets 데이터를 불러오는 과정에서 오류가 발생했습니다.")
        st.code(str(e))
        st.stop()


    # --------------------------------------------------------
    # 컬럼명 문자열 변환
    # --------------------------------------------------------

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]


    # --------------------------------------------------------
    # 중복 컬럼명 제거 / 고유 컬럼명 생성
    #
    # 같은 이름의 컬럼이 있으면
    # pandas에서 df["컬럼"]이 DataFrame이 될 수 있음.
    # 이 문제를 여기서 방지
    # --------------------------------------------------------

    new_columns = []
    column_count = {}

    for col in df.columns:

        if col not in column_count:

            column_count[col] = 0
            new_columns.append(col)

        else:

            column_count[col] += 1
            new_columns.append(
                f"{col}_{column_count[col]}"
            )

    df.columns = new_columns


    # --------------------------------------------------------
    # 컬럼명 통일
    # --------------------------------------------------------

    rename_map = {}

    for col in df.columns:

        col_lower = str(col).strip().lower()

        if col_lower in [
            "광고유형",
            "유형",
            "type"
        ]:
            rename_map[col] = "type"

        elif col_lower in [
            "매체",
            "media",
            "media2"
        ]:
            rename_map[col] = "media"

        elif col_lower in [
            "캠페인",
            "campaign"
        ]:
            rename_map[col] = "campaign"

        elif col_lower in [
            "노출",
            "노출수",
            "impress",
            "impression",
            "impressions"
        ]:
            rename_map[col] = "impress"

        elif col_lower in [
            "클릭",
            "클릭수",
            "click"
        ]:
            rename_map[col] = "click"

        elif col_lower in [
            "광고비",
            "spend",
            "cost"
        ]:
            rename_map[col] = "spend"

        elif col_lower in [
            "전환",
            "전환수",
            "conversion"
        ]:
            rename_map[col] = "conversion"

        elif col_lower in [
            "날짜",
            "date"
        ]:
            rename_map[col] = "date"


    # --------------------------------------------------------
    # rename
    # --------------------------------------------------------

    df = df.rename(
        columns=rename_map
    )


    # --------------------------------------------------------
    # 필수 컬럼
    # --------------------------------------------------------

    required_cols = [
        "date",
        "type",
        "media",
        "campaign",
        "impress",
        "click",
        "spend",
        "conversion"
    ]


    for col in required_cols:

        if col not in df.columns:

            if col in [
                "type",
                "media",
                "campaign"
            ]:

                df[col] = "미분류"

            else:

                df[col] = 0


    # --------------------------------------------------------
    # 혹시 rename 과정에서 중복된 표준 컬럼이 생긴 경우
    # 첫 번째 컬럼만 사용
    # --------------------------------------------------------

    for col in required_cols:

        duplicated_positions = [
            i
            for i, name in enumerate(df.columns)
            if name == col
        ]

        if len(duplicated_positions) > 1:

            first_position = duplicated_positions[0]

            keep_columns = []

            for i, name in enumerate(df.columns):

                if name == col and i != first_position:
                    continue

                keep_columns.append(name)

            df = df.iloc[:, :len(keep_columns)]
            df.columns = keep_columns


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

        # 혹시 DataFrame으로 들어오는 경우
        if isinstance(df[col], pd.DataFrame):

            df[col] = df[col].iloc[:, 0]


        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("-", "0", regex=False)
            .str.replace("원", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
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

        # 가장 중요한 오류 방지 부분
        # DataFrame이면 첫 번째 컬럼을 Series로 변환
        if isinstance(df[col], pd.DataFrame):

            df[col] = df[col].iloc[:, 0]


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
                "NaN"
            ]),
            col
        ] = "미분류"


    return df


# ============================================================
# 4. 데이터 실행
# ============================================================

df = load_data()


# ============================================================
# 5. 제목
# ============================================================

st.markdown(
    '<div class="main-title">📈 성과 비교 대시보드</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    '기간별 광고 성과를 비교하고 매체·캠페인별 성과 변화를 확인합니다.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# 6. 데이터 기간
# ============================================================

valid_dates = df["date"].dropna()


if len(valid_dates) == 0:

    st.error("날짜 데이터를 확인할 수 없습니다.")
    st.stop()


min_date = valid_dates.min().date()
max_date = valid_dates.max().date()


# ============================================================
# 7. 분석 조건
# ============================================================

st.markdown(
    '<div class="section-title">🔎 분석 조건</div>',
    unsafe_allow_html=True
)


col1, col2, col3 = st.columns(3)


with col1:

    type_options = sorted(
        df["type"].dropna().unique().tolist()
    )

    selected_type = st.multiselect(
        "카테고리",
        type_options,
        default=type_options
    )


with col2:

    media_options = sorted(
        df["media"].dropna().unique().tolist()
    )

    selected_media = st.multiselect(
        "매체",
        media_options,
        default=media_options
    )


with col3:

    campaign_options = sorted(
        df["campaign"].dropna().unique().tolist()
    )

    selected_campaign = st.multiselect(
        "캠페인",
        campaign_options,
        default=campaign_options
    )


# ============================================================
# 8. 기간 선택
# ============================================================

period_col1, period_col2 = st.columns(2)


with period_col1:

    base_date = st.date_input(
        "기준일",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )


with period_col2:

    compare_mode = st.selectbox(
        "비교 기준",
        [
            "전일",
            "전주",
            "전월",
            "지정"
        ]
    )


# ============================================================
# 9. 비교 기간 계산
# ============================================================

base_date = pd.Timestamp(base_date)


if compare_mode == "전일":

    base_start = base_date
    base_end = base_date

    compare_start = (
        base_date -
        timedelta(days=1)
    )

    compare_end = compare_start


elif compare_mode == "전주":

    base_start = base_date
    base_end = base_date

    compare_start = (
        base_date -
        timedelta(days=7)
    )

    compare_end = compare_start


elif compare_mode == "전월":

    base_start = base_date
    base_end = base_date

    previous_month = (
        base_date -
        pd.DateOffset(months=1)
    )

    compare_start = previous_month
    compare_end = previous_month


else:

    st.info(
        "지정 비교는 기준일과 동일한 일수의 기간을 비교합니다."
    )

    custom_compare = st.date_input(
        "비교 시작일",
        value=(
            base_date -
            timedelta(days=1)
        ).date(),
        min_value=min_date,
        max_value=max_date
    )

    compare_start = pd.Timestamp(
        custom_compare
    )

    period_days = 1

    compare_end = (
        compare_start +
        timedelta(
            days=period_days - 1
        )
    )

    base_start = base_date
    base_end = base_date


# ============================================================
# 10. 필터 적용
# ============================================================

condition = (
    df["type"].isin(selected_type)
    &
    df["media"].isin(selected_media)
    &
    df["campaign"].isin(selected_campaign)
)


analysis_df = df[
    condition
].copy()


# ============================================================
# 11. 기간 데이터
# ============================================================

base_df = analysis_df[
    (analysis_df["date"] >= base_start)
    &
    (analysis_df["date"] <= base_end)
].copy()


compare_df = analysis_df[
    (analysis_df["date"] >= compare_start)
    &
    (analysis_df["date"] <= compare_end)
].copy()


# ============================================================
# 12. 집계 함수
# ============================================================

def summarize(data):

    spend = data["spend"].sum()
    click = data["click"].sum()
    conversion = data["conversion"].sum()

    cpa = (
        spend / conversion
        if conversion > 0
        else np.nan
    )

    cvr = (
        conversion / click * 100
        if click > 0
        else np.nan
    )

    return {
        "spend": spend,
        "click": click,
        "conversion": conversion,
        "cpa": cpa,
        "cvr": cvr
    }


base = summarize(base_df)
compare = summarize(compare_df)


# ============================================================
# 13. 변화율 함수
# ============================================================

def safe_rate(current, previous):

    if (
        pd.isna(current)
        or pd.isna(previous)
        or previous == 0
    ):
        return None

    return (
        (current - previous)
        / abs(previous)
        * 100
    )


def format_rate(rate):

    if rate is None or pd.isna(rate):
        return "-"

    return f"{rate:+.1f}%"


def metric_change_text(
    base_value,
    compare_value,
    unit="",
    decimals=0
):

    if pd.isna(base_value):

        return "-"


    if pd.isna(compare_value):

        return "-"


    if compare_value == 0:

        if base_value == 0:
            return "변화 없음"

        return "신규 발생"


    diff = (
        base_value -
        compare_value
    )

    rate = (
        diff /
        abs(compare_value) *
        100
    )


    if decimals == 0:

        value_text = (
            f"{abs(diff):,.0f}{unit}"
        )

    else:

        value_text = (
            f"{abs(diff):,.{decimals}f}{unit}"
        )


    if diff > 0:

        return (
            f"+{value_text} "
            f"(+{rate:.1f}%)"
        )

    elif diff < 0:

        return (
            f"-{value_text} "
            f"({rate:.1f}%)"
        )

    return "변화 없음"


# ============================================================
# 14. 핵심 성과 비교
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">📊 핵심 성과 비교</div>',
    unsafe_allow_html=True
)


kpi_data = [

    (
        "광고비",
        f"{base['spend']:,.0f}원",
        metric_change_text(
            base["spend"],
            compare["spend"],
            "원"
        )
    ),

    (
        "전환수",
        f"{base['conversion']:,.0f}건",
        metric_change_text(
            base["conversion"],
            compare["conversion"],
            "건"
        )
    ),

    (
        "CPA",
        (
            f"{base['cpa']:,.0f}원"
            if pd.notna(base["cpa"])
            else "-"
        ),
        (
            metric_change_text(
                base["cpa"],
                compare["cpa"],
                "원"
            )
            if pd.notna(base["cpa"])
            and pd.notna(compare["cpa"])
            else "-"
        )
    ),

    (
        "CVR",
        (
            f"{base['cvr']:.2f}%"
            if pd.notna(base["cvr"])
            else "-"
        ),
        (
            metric_change_text(
                base["cvr"],
                compare["cvr"],
                "%",
                2
            )
            if pd.notna(base["cvr"])
            and pd.notna(compare["cvr"])
            else "-"
        )
    )
]


kpi_cols = st.columns(4)


for col, item in zip(
    kpi_cols,
    kpi_data
):

    with col:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-title">
                    {item[0]}
                </div>

                <div class="metric-value">
                    {item[1]}
                </div>

                <div style="
                    margin-top:8px;
                    color:#6b7280;
                ">
                    비교: {item[2]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# 15. 기간 설명
# ============================================================

st.caption(
    f"기준 기간: "
    f"{base_start.strftime('%Y-%m-%d')} ~ "
    f"{base_end.strftime('%Y-%m-%d')}"
    f"  |  "
    f"비교 기간: "
    f"{compare_start.strftime('%Y-%m-%d')} ~ "
    f"{compare_end.strftime('%Y-%m-%d')}"
)


# ============================================================
# 16. 매체별 성과 비교
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">📱 매체별 상세 성과 비교</div>',
    unsafe_allow_html=True
)


def media_summary(data):

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


media_base = media_summary(
    base_df
)

media_compare = media_summary(
    compare_df
)


media_table = pd.merge(
    media_base,
    media_compare,
    on="media",
    how="outer",
    suffixes=(
        "_base",
        "_compare"
    )
)


# NaN을 무조건 0으로 바꾸지 않음
# CPA/CVR까지 0이 되어버리는 문제 방지

for col in [
    "spend_base",
    "click_base",
    "conversion_base",
    "spend_compare",
    "click_compare",
    "conversion_compare"
]:

    if col in media_table.columns:

        media_table[col] = (
            media_table[col]
            .fillna(0)
        )


media_table = media_table.sort_values(
    "conversion_base",
    ascending=False
)


# ============================================================
# 17. HTML 변화 표시 함수
# ============================================================

def rate_html(
    rate,
    positive_good=True
):

    if rate is None:

        return (
            '<span class="neutral">-</span>'
        )


    if positive_good:

        if rate > 0:

            return (
                f'<span class="good">'
                f'+{rate:.1f}%'
                f'</span>'
            )

        elif rate < 0:

            return (
                f'<span class="bad">'
                f'{rate:.1f}%'
                f'</span>'
            )

    else:

        if rate < 0:

            return (
                f'<span class="good">'
                f'{rate:.1f}%'
                f'</span>'
            )

        elif rate > 0:

            return (
                f'<span class="bad">'
                f'+{rate:.1f}%'
                f'</span>'
            )


    return (
        '<span class="neutral">-</span>'
    )


# ============================================================
# 18. 매체 HTML 표
# ============================================================

rows = []


for _, row in media_table.iterrows():

    media_name = row["media"]


    spend_base = float(
        row.get(
            "spend_base",
            0
        )
    )

    spend_compare = float(
        row.get(
            "spend_compare",
            0
        )
    )


    conversion_base = float(
        row.get(
            "conversion_base",
            0
        )
    )

    conversion_compare = float(
        row.get(
            "conversion_compare",
            0
        )
    )


    cpa_base = row.get(
        "CPA_base",
        np.nan
    )

    cpa_compare = row.get(
        "CPA_compare",
        np.nan
    )


    cvr_base = row.get(
        "CVR_base",
        np.nan
    )

    cvr_compare = row.get(
        "CVR_compare",
        np.nan
    )


    spend_rate = safe_rate(
        spend_base,
        spend_compare
    )


    conversion_rate = safe_rate(
        conversion_base,
        conversion_compare
    )


    cpa_rate = safe_rate(
        cpa_base,
        cpa_compare
    )


    cvr_rate = safe_rate(
        cvr_base,
        cvr_compare
    )


    rows.append(
        f"""
        <tr>

            <td style="
                padding:14px;
                border-bottom:1px solid #eee;
                font-weight:700;
            ">
                {html.escape(str(media_name))}
            </td>

            <td style="
                padding:14px;
                border-bottom:1px solid #eee;
            ">

                <div>
                    기준:
                    <b>{spend_base:,.0f}원</b>
                </div>

                <div style="color:#888;">
                    비교:
                    {spend_compare:,.0f}원
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        spend_rate,
                        True
                    )}
                </div>

            </td>


            <td style="
                padding:14px;
                border-bottom:1px solid #eee;
            ">

                <div>
                    기준:
                    <b>{conversion_base:,.0f}건</b>
                </div>

                <div style="color:#888;">
                    비교:
                    {conversion_compare:,.0f}건
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        conversion_rate,
                        True
                    )}
                </div>

            </td>


            <td style="
                padding:14px;
                border-bottom:1px solid #eee;
            ">

                <div>
                    기준:
                    <b>
                    {
                        f"{cpa_base:,.0f}원"
                        if pd.notna(cpa_base)
                        and cpa_base > 0
                        else "-"
                    }
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {
                        f"{cpa_compare:,.0f}원"
                        if pd.notna(cpa_compare)
                        and cpa_compare > 0
                        else "-"
                    }
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        cpa_rate,
                        False
                    )}
                </div>

            </td>


            <td style="
                padding:14px;
                border-bottom:1px solid #eee;
            ">

                <div>
                    기준:
                    <b>
                    {
                        f"{cvr_base:.2f}%"
                        if pd.notna(cvr_base)
                        and cvr_base > 0
                        else "-"
                    }
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {
                        f"{cvr_compare:.2f}%"
                        if pd.notna(cvr_compare)
                        and cvr_compare > 0
                        else "-"
                    }
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        cvr_rate,
                        True
                    )}
                </div>

            </td>

        </tr>
        """
    )


media_html = f"""
<table style="
    width:100%;
    border-collapse:collapse;
    font-size:14px;
">

<thead>

<tr style="
    background:#f8fafc;
    border-bottom:1px solid #ddd;
">

<th style="
    padding:12px;
    text-align:left;
">
매체
</th>

<th style="
    padding:12px;
    text-align:left;
">
광고비
</th>

<th style="
    padding:12px;
    text-align:left;
">
전환수
</th>

<th style="
    padding:12px;
    text-align:left;
">
CPA
</th>

<th style="
    padding:12px;
    text-align:left;
">
CVR
</th>

</tr>

</thead>

<tbody>

{''.join(rows)}

</tbody>

</table>
"""


st.markdown(
    media_html,
    unsafe_allow_html=True
)


# ============================================================
# 19. 매체별 상세 코멘트
# ============================================================

st.markdown(
    "### 💬 매체별 성과 코멘트"
)


for _, row in media_table.iterrows():

    media_name = row["media"]


    spend_base = float(
        row.get("spend_base", 0)
    )

    spend_compare = float(
        row.get("spend_compare", 0)
    )


    conversion_base = float(
        row.get(
            "conversion_base",
            0
        )
    )

    conversion_compare = float(
        row.get(
            "conversion_compare",
            0
        )
    )


    cpa_base = row.get(
        "CPA_base",
        np.nan
    )

    cpa_compare = row.get(
        "CPA_compare",
        np.nan
    )


    cvr_base = row.get(
        "CVR_base",
        np.nan
    )

    cvr_compare = row.get(
        "CVR_compare",
        np.nan
    )


    spend_rate = safe_rate(
        spend_base,
        spend_compare
    )

    conversion_rate = safe_rate(
        conversion_base,
        conversion_compare
    )

    cpa_rate = safe_rate(
        cpa_base,
        cpa_compare
    )

    cvr_rate = safe_rate(
        cvr_base,
        cvr_compare
    )


    # --------------------------------------------------------
    # 신규 발생
    # --------------------------------------------------------

    if (
        conversion_compare == 0
        and conversion_base > 0
    ):

        comment = (
            f"**{media_name}**는 비교 기간에 "
            f"전환이 발생하지 않았으나 기준 기간에는 "
            f"**{conversion_base:,.0f}건**의 전환을 확보했습니다. "
            f"광고비는 **{spend_base:,.0f}원**, "
            f"CPA는 "
            f"**{cpa_base:,.0f}원** 수준입니다. "
            f"이처럼 비교 기간 대비 전환이 새롭게 발생한 경우에는 "
            f"단순히 전환 증가를 긍정적으로 판단하기보다 "
            f"증가한 광고비가 실제 전환 증가로 연결되었는지와 "
            f"CPA가 목표 효율을 유지하고 있는지를 함께 확인하는 것이 중요합니다. "
            f"특히 이후 기간에서도 전환량이 유지되는지 확인한 뒤 "
            f"추가 예산 확대 여부를 판단하는 것이 적절합니다."
        )


    else:

        # ----------------------------------------------------
        # 전환
        # ----------------------------------------------------

        if conversion_rate is not None:

            conversion_direction = (
                "증가"
                if conversion_rate > 0
                else "감소"
                if conversion_rate < 0
                else "변화 없음"
            )

            conversion_text = (
                f"전환수는 **{conversion_base:,.0f}건**으로 "
                f"비교 기간 대비 "
                f"**{abs(conversion_rate):.1f}% "
                f"{conversion_direction}**했습니다."
            )

        else:

            conversion_text = (
                f"전환수는 **{conversion_base:,.0f}건**입니다."
            )


        # ----------------------------------------------------
        # CPA
        # ----------------------------------------------------

        if pd.notna(cpa_base):

            if cpa_rate is not None:

                cpa_direction = (
                    "개선"
                    if cpa_rate < 0
                    else "상승"
                    if cpa_rate > 0
                    else "변화 없음"
                )

                cpa_text = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간 대비 "
                    f"**{abs(cpa_rate):.1f}% "
                    f"{cpa_direction}**했습니다."
                )

            else:

                cpa_text = (
                    f"CPA는 **{cpa_base:,.0f}원**입니다."
                )

        else:

            cpa_text = (
                "기준 기간에는 전환이 없어 CPA를 "
                "산출할 수 없습니다."
            )


        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

        if pd.notna(cvr_base):

            if cvr_rate is not None:

                cvr_direction = (
                    "상승"
                    if cvr_rate > 0
                    else "하락"
                    if cvr_rate < 0
                    else "변화 없음"
                )

                cvr_text = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간 대비 "
                    f"**{abs(cvr_rate):.1f}% "
                    f"{cvr_direction}**했습니다."
                )

            else:

                cvr_text = (
                    f"CVR은 **{cvr_base:.2f}%**입니다."
                )

        else:

            cvr_text = (
                "클릭이 없어 CVR을 산출할 수 없습니다."
            )


        # ----------------------------------------------------
        # 종합
        # ----------------------------------------------------

        if (
            conversion_rate is not None
            and conversion_rate > 0
            and cpa_rate is not None
            and cpa_rate < 0
        ):

            conclusion = (
                "전환 증가와 CPA 개선이 동시에 나타나 "
                "물량과 효율 측면에서 모두 긍정적인 흐름입니다. "
                "현재 효율을 유지하면서 추가 예산 투입 여력이 있는지 "
                "검토할 가치가 있습니다."
            )

        elif (
            conversion_rate is not None
            and conversion_rate > 0
            and cpa_rate is not None
            and cpa_rate > 0
        ):

            conclusion = (
                "전환 규모는 증가했지만 CPA도 상승해 "
                "추가 물량 확보 과정에서 효율이 일부 희석된 것으로 볼 수 있습니다. "
                "예산 확대보다는 효율이 좋은 캠페인·타겟·소재 중심으로 "
                "세부 구간을 나눠 확인하는 것이 필요합니다."
            )

        elif (
            conversion_rate is not None
            and conversion_rate < 0
            and cpa_rate is not None
            and cpa_rate > 0
        ):

            conclusion = (
                "전환 감소와 CPA 상승이 동시에 나타나 "
                "효율과 물량 모두 부진한 상황입니다. "
                "광고비 집행 규모를 재검토하고 "
                "성과가 낮은 캠페인이나 세부 구간의 조정이 필요합니다."
            )

        elif (
            conversion_rate is not None
            and conversion_rate < 0
            and cpa_rate is not None
            and cpa_rate < 0
        ):

            conclusion = (
                "전환 규모는 감소했지만 CPA는 개선되어 "
                "물량보다 효율 중심의 변화가 나타났습니다. "
                "전환 감소 원인이 예산 축소인지, 유입량 감소인지, "
                "또는 전환율 변화인지 추가적으로 확인하는 것이 좋습니다."
            )

        else:

            conclusion = (
                "전환수·CPA·CVR의 변화를 함께 확인해 "
                "단일 지표만으로 판단하기보다 "
                "광고비 변화가 실제 전환과 효율에 어떤 영향을 미쳤는지 "
                "종합적으로 판단하는 것이 적절합니다."
            )


        comment = (
            f"**{media_name}**는 기준 기간에 "
            f"광고비 **{spend_base:,.0f}원**을 집행했습니다. "
            f"{conversion_text} "
            f"{cpa_text} "
            f"{cvr_text} "
            f"{conclusion}"
        )


    st.markdown(
        f'<div class="comment-box">{comment}</div>',
        unsafe_allow_html=True
    )


# ============================================================
# 20. 캠페인별 성과
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">📊 캠페인별 성과</div>',
    unsafe_allow_html=True
)


campaign_base = (
    base_df
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


campaign_base["CPA"] = np.where(
    campaign_base["conversion"] > 0,
    campaign_base["spend"] /
    campaign_base["conversion"],
    np.nan
)


campaign_base["CVR"] = np.where(
    campaign_base["click"] > 0,
    campaign_base["conversion"] /
    campaign_base["click"] *
    100,
    np.nan
)


campaign_base = campaign_base.sort_values(
    "conversion",
    ascending=False
).reset_index(
    drop=True
)


# ============================================================
# 21. 캠페인 그래프
# ============================================================

if len(campaign_base) > 0:

    fig = go.Figure()


    # --------------------------------------------------------
    # CPA 막대
    # --------------------------------------------------------

    fig.add_trace(
        go.Bar(
            x=campaign_base["campaign"],
            y=campaign_base["CPA"],
            name="CPA",
            text=[
                (
                    f"{x:,.0f}원"
                    if pd.notna(x)
                    else "-"
                )
                for x in campaign_base["CPA"]
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CPA: %{y:,.0f}원"
                "<extra></extra>"
            ),
            yaxis="y"
        )
    )


    # --------------------------------------------------------
    # 전환수 라인
    #
    # 기존 문제:
    # CPA와 전환수가 서로 다른 단위인데
    # 축 범위가 제대로 잡히지 않아
    # 전환 라인이 이상하게 보일 수 있음.
    #
    # 별도 y축 + 명확한 range 사용
    # --------------------------------------------------------

    conversion_values = (
        campaign_base["conversion"]
        .fillna(0)
        .astype(float)
    )


    max_conversion = (
        conversion_values.max()
        if len(conversion_values) > 0
        else 0
    )


    conversion_axis_max = max(
        max_conversion * 1.20,
        1
    )


    fig.add_trace(
        go.Scatter(
            x=campaign_base["campaign"],
            y=conversion_values,
            name="전환수",
            mode="lines+markers+text",
            yaxis="y2",
            text=[
                f"{x:,.0f}건"
                for x in conversion_values
            ],
            textposition="top center",
            line=dict(
                width=3
            ),
            marker=dict(
                size=8
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "전환수: %{y:,.0f}건"
                "<extra></extra>"
            )
        )
    )


    fig.update_layout(

        title="캠페인별 CPA + 전환수",

        xaxis=dict(
            title="캠페인",
            tickangle=-35,
            categoryorder="array",
            categoryarray=campaign_base[
                "campaign"
            ].tolist()
        ),

        yaxis=dict(
            title="CPA",
            tickformat=",",
            rangemode="tozero"
        ),

        yaxis2=dict(
            title="전환수",
            overlaying="y",
            side="right",
            range=[
                0,
                conversion_axis_max
            ],
            rangemode="tozero"
        ),

        height=620,

        hovermode="x unified",

        legend=dict(
            orientation="h",
            y=1.08,
            x=0
        ),

        margin=dict(
            l=70,
            r=90,
            t=100,
            b=160
        )
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# 22. 캠페인 상세 표
# ============================================================

st.markdown(
    "### 📋 캠페인 상세 성과"
)


campaign_display = campaign_base.copy()


campaign_display["광고비"] = (
    campaign_display["spend"]
    .map(
        lambda x:
        f"{x:,.0f}원"
    )
)


campaign_display["전환수"] = (
    campaign_display["conversion"]
    .map(
        lambda x:
        f"{x:,.0f}건"
    )
)


campaign_display["CPA"] = (
    campaign_display["CPA"]
    .map(
        lambda x:
        f"{x:,.0f}원"
        if pd.notna(x)
        else "-"
    )
)


campaign_display["CVR"] = (
    campaign_display["CVR"]
    .map(
        lambda x:
        f"{x:.2f}%"
        if pd.notna(x)
        else "-"
    )
)


campaign_display = campaign_display[
    [
        "campaign",
        "광고비",
        "전환수",
        "CPA",
        "CVR"
    ]
].rename(
    columns={
        "campaign": "캠페인"
    }
)


st.dataframe(
    campaign_display,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 23. 캠페인 핵심 코멘트
# ============================================================

st.markdown(
    "### 💬 캠페인 성과 코멘트"
)


if len(campaign_base) > 0:

    total_conversion = (
        campaign_base["conversion"]
        .sum()
    )


    # --------------------------------------------------------
    # CPA 최우수
    # --------------------------------------------------------

    valid_cpa = campaign_base[
        campaign_base["conversion"] > 0
    ].copy()


    if len(valid_cpa) > 0:

        best_cpa_row = valid_cpa.loc[
            valid_cpa["CPA"].idxmin()
        ]


        best_cpa_campaign = (
            best_cpa_row["campaign"]
        )

        best_cpa = (
            best_cpa_row["CPA"]
        )

        best_cpa_conversion = (
            best_cpa_row["conversion"]
        )


        share = (
            best_cpa_conversion /
            total_conversion *
            100
            if total_conversion > 0
            else 0
        )


        st.markdown(
            f"""
            🏆 **CPA 최우수 캠페인:** `{best_cpa_campaign}` —
            CPA **{best_cpa:,.0f}원**,
            전환 **{best_cpa_conversion:,.0f}건**
            (**전체 전환의 {share:.1f}%**)
            """
        )


    # --------------------------------------------------------
    # 전환 최다
    # --------------------------------------------------------

    best_conversion_row = (
        campaign_base.loc[
            campaign_base["conversion"].idxmax()
        ]
    )


    best_conversion_campaign = (
        best_conversion_row["campaign"]
    )

    best_conversion = (
        best_conversion_row["conversion"]
    )

    best_conversion_cpa = (
        best_conversion_row["CPA"]
    )


    conversion_share = (
        best_conversion /
        total_conversion *
        100
        if total_conversion > 0
        else 0
    )


    best_conversion_cpa_text = (
        f"{best_conversion_cpa:,.0f}원"
        if pd.notna(best_conversion_cpa)
        else "-"
    )


    st.markdown(
        f"""
        📈 **전환수 최다 캠페인:** `{best_conversion_campaign}` —
        전환 **{best_conversion:,.0f}건**,
        CPA **{best_conversion_cpa_text}**
        (**전체 전환의 {conversion_share:.1f}%**)
        """
    )


# ============================================================
# 24. 캠페인 드릴다운
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">🔎 캠페인 드릴다운</div>',
    unsafe_allow_html=True
)


campaign_compare = (
    compare_df
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


campaign_compare["CPA"] = np.where(
    campaign_compare["conversion"] > 0,
    campaign_compare["spend"] /
    campaign_compare["conversion"],
    np.nan
)


campaign_compare["CVR"] = np.where(
    campaign_compare["click"] > 0,
    campaign_compare["conversion"] /
    campaign_compare["click"] *
    100,
    np.nan
)


campaign_detail = pd.merge(
    campaign_base,
    campaign_compare,
    on="campaign",
    how="outer",
    suffixes=(
        "_base",
        "_compare"
    )
)


# 숫자 컬럼만 0 처리
for col in [
    "spend_base",
    "click_base",
    "conversion_base",
    "spend_compare",
    "click_compare",
    "conversion_compare"
]:

    if col in campaign_detail.columns:

        campaign_detail[col] = (
            campaign_detail[col]
            .fillna(0)
        )


campaign_detail = campaign_detail.sort_values(
    "conversion_base",
    ascending=False
)


# ============================================================
# 25. 캠페인 상세 코멘트
# ============================================================

for _, row in campaign_detail.iterrows():

    campaign_name = row["campaign"]


    spend_base = float(
        row.get(
            "spend_base",
            0
        )
    )

    spend_compare = float(
        row.get(
            "spend_compare",
            0
        )
    )


    conversion_base = float(
        row.get(
            "conversion_base",
            0
        )
    )

    conversion_compare = float(
        row.get(
            "conversion_compare",
            0
        )
    )


    cpa_base = row.get(
        "CPA_base",
        np.nan
    )

    cpa_compare = row.get(
        "CPA_compare",
        np.nan
    )


    cvr_base = row.get(
        "CVR_base",
        np.nan
    )

    cvr_compare = row.get(
        "CVR_compare",
        np.nan
    )


    conversion_rate = safe_rate(
        conversion_base,
        conversion_compare
    )


    cpa_rate = safe_rate(
        cpa_base,
        cpa_compare
    )


    cvr_rate = safe_rate(
        cvr_base,
        cvr_compare
    )


    # --------------------------------------------------------
    # 신규 캠페인
    # --------------------------------------------------------

    if (
        conversion_compare == 0
        and conversion_base > 0
    ):

        cpa_text = (
            f"CPA는 **{cpa_base:,.0f}원**"
            if pd.notna(cpa_base)
            else "CPA는 산출할 수 없는 상태"
        )


        comment = (
            f"**{campaign_name}**은 비교 기간에는 "
            f"전환이 발생하지 않았으나 기준 기간에는 "
            f"**{conversion_base:,.0f}건**의 전환을 확보했습니다. "
            f"광고비는 **{spend_base:,.0f}원**이며 "
            f"{cpa_text}입니다. "
            f"비교 기간 대비 신규로 전환이 발생했다는 점은 긍정적이지만, "
            f"한 기간의 성과만으로 안정적인 우수 캠페인이라고 판단하기보다는 "
            f"향후 동일한 광고비 수준에서 전환량과 CPA가 유지되는지 "
            f"추가로 확인할 필요가 있습니다."
        )


    else:

        # ----------------------------------------------------
        # 전환
        # ----------------------------------------------------

        if conversion_rate is not None:

            conversion_direction = (
                "증가"
                if conversion_rate > 0
                else "감소"
                if conversion_rate < 0
                else "변화 없음"
            )


            conversion_part = (
                f"전환수는 **{conversion_base:,.0f}건**으로 "
                f"비교 기간 대비 "
                f"**{abs(conversion_rate):.1f}% "
                f"{conversion_direction}**했습니다."
            )

        else:

            conversion_part = (
                f"전환수는 **{conversion_base:,.0f}건**입니다."
            )


        # ----------------------------------------------------
        # CPA
        # ----------------------------------------------------

        if pd.notna(cpa_base):

            if cpa_rate is not None:

                cpa_direction = (
                    "개선"
                    if cpa_rate < 0
                    else "상승"
                    if cpa_rate > 0
                    else "변화 없음"
                )


                cpa_part = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간 대비 "
                    f"**{abs(cpa_rate):.1f}% "
                    f"{cpa_direction}**했습니다."
                )

            else:

                cpa_part = (
                    f"CPA는 **{cpa_base:,.0f}원**입니다."
                )

        else:

            cpa_part = (
                "기준 기간에 전환이 없어 "
                "CPA를 산출할 수 없습니다."
            )


        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

        if pd.notna(cvr_base):

            if cvr_rate is not None:

                cvr_direction = (
                    "상승"
                    if cvr_rate > 0
                    else "하락"
                    if cvr_rate < 0
                    else "변화 없음"
                )


                cvr_part = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간 대비 "
                    f"**{abs(cvr_rate):.1f}% "
                    f"{cvr_direction}**했습니다."
                )

            else:

                cvr_part = (
                    f"CVR은 **{cvr_base:.2f}%**입니다."
                )

        else:

            cvr_part = (
                "클릭이 없어 CVR을 산출할 수 없습니다."
            )


        # ----------------------------------------------------
        # 상세 판단
        # ----------------------------------------------------

        if (
            conversion_rate is not None
            and conversion_rate > 0
            and cpa_rate is not None
            and cpa_rate < 0
        ):

            conclusion = (
                "전환 증가와 CPA 개선이 동시에 나타나 "
                "물량과 효율이 함께 좋아진 캠페인입니다. "
                "예산을 확대하더라도 현재 CPA 수준이 유지되는지 "
                "확인하면서 우선적으로 스케일업을 검토할 수 있습니다."
            )


        elif (
            conversion_rate is not None
            and conversion_rate > 0
            and cpa_rate is not None
            and cpa_rate > 0
        ):

            conclusion = (
                "전환은 증가했지만 CPA도 상승해 "
                "물량 확대 과정에서 효율이 희석된 모습입니다. "
                "추가 예산 확대보다는 성과가 좋은 세부 캠페인·소재·타겟으로 "
                "예산을 재배분해 효율을 방어하는 전략이 적절합니다."
            )


        elif (
            conversion_rate is not None
            and conversion_rate < 0
            and cpa_rate is not None
            and cpa_rate > 0
        ):

            conclusion = (
                "전환 감소와 CPA 상승이 동시에 나타나 "
                "물량과 효율 모두 악화된 캠페인입니다. "
                "광고비를 유지하기보다 유입량과 CVR 하락 원인을 먼저 확인하고 "
                "저성과 구간의 예산 축소 또는 소재·타겟 개선을 검토하는 것이 좋습니다."
            )


        elif (
            conversion_rate is not None
            and conversion_rate < 0
            and cpa_rate is not None
            and cpa_rate < 0
        ):

            conclusion = (
                "전환 규모는 감소했지만 CPA는 개선되어 "
                "물량보다 효율 중심으로 변화한 캠페인입니다. "
                "전환 감소가 광고비 축소 때문인지, 클릭 또는 CVR 감소 때문인지 "
                "추가로 확인한 뒤 운영 방향을 판단하는 것이 좋습니다."
            )


        elif (
            cvr_rate is not None
            and cvr_rate > 0
        ):

            conclusion = (
                "CVR이 개선된 만큼 유입 이후 전환 효율은 긍정적인 흐름입니다. "
                "다만 전체 전환 규모와 CPA까지 함께 확인해 "
                "단순 전환율 개선이 실제 사업 성과 개선으로 이어졌는지 "
                "판단할 필요가 있습니다."
            )


        elif (
            cvr_rate is not None
            and cvr_rate < 0
        ):

            conclusion = (
                "CVR이 하락해 클릭 이후 전환 효율이 약화된 모습입니다. "
                "랜딩페이지, 타겟, 소재 또는 유입 품질 측면에서 "
                "전환 저하 원인을 세부적으로 확인할 필요가 있습니다."
            )


        else:

            conclusion = (
                "전환수와 CPA의 절대 수준뿐 아니라 "
                "비교 기간 대비 변화 방향을 함께 확인해 "
                "광고비 증가가 실제 전환 증가로 연결됐는지와 "
                "효율이 안정적으로 유지되고 있는지를 중심으로 "
                "후속 최적화 방향을 판단하는 것이 좋습니다."
            )


        comment = (
            f"**{campaign_name}**은 기준 기간에 "
            f"광고비 **{spend_base:,.0f}원**을 집행했습니다. "
            f"{conversion_part} "
            f"{cpa_part} "
            f"{cvr_part} "
            f"{conclusion}"
        )


    st.markdown(
        f'<div class="comment-box">{comment}</div>',
        unsafe_allow_html=True
    )


# ============================================================
# 26. 데이터 새로고침
# ============================================================

st.divider()


if st.button(
    "🔄 데이터 새로고침"
):

    st.cache_data.clear()

    st.rerun()
