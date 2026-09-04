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
    # 컬럼명 통일
    # --------------------------------------------------------

    rename_map = {}

    for col in df.columns:

        col_lower = str(col).strip().lower()

        if col_lower in [
            "광고유형",
            "광고 유형",
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
            "click",
            "clicks"
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
            "conversion",
            "conversions"
        ]:
            rename_map[col] = "conversion"

        elif col_lower in [
            "날짜",
            "date"
        ]:
            rename_map[col] = "date"

    df = df.rename(columns=rename_map)

    # --------------------------------------------------------
    # 필수 컬럼 보정
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
    # 날짜 처리
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # 숫자 컬럼 처리
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
            .astype("string")
            .str.replace(",", "", regex=False)
            .str.replace("-", "0", regex=False)
            .str.replace("원", "", regex=False)
            .str.replace("건", "", regex=False)
            .str.strip()
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # 문자 컬럼 처리
    #
    # 핵심 수정 부분
    # .str.strip() 전에 string 타입으로 강제 변환
    # --------------------------------------------------------

    text_cols = [
        "type",
        "media",
        "campaign"
    ]

    for col in text_cols:

        df[col] = (
            df[col]
            .astype("string")
            .fillna("미분류")
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

    return df


# ============================================================
# 4. 데이터 실행
# ============================================================

try:

    df = load_data()

except Exception as e:

    st.error("Google Sheets 데이터를 불러오는 과정에서 오류가 발생했습니다.")

    st.code(
        str(e)
    )

    st.stop()


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
        df["type"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_type = st.multiselect(
        "카테고리",
        type_options,
        default=type_options
    )


with col2:

    media_options = sorted(
        df["media"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_media = st.multiselect(
        "매체",
        media_options,
        default=media_options
    )


with col3:

    campaign_options = sorted(
        df["campaign"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
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

    base_date_input = st.date_input(
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

base_date = pd.Timestamp(
    base_date_input
)


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
        "지정 비교는 기준 기간과 동일한 일수로 비교합니다."
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

    period_days = (
        base_end - base_start
    ).days + 1

    compare_end = (
        compare_start +
        timedelta(days=period_days - 1)
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
    (
        analysis_df["date"]
        >= base_start
    )
    &
    (
        analysis_df["date"]
        <= base_end
    )
].copy()


compare_df = analysis_df[
    (
        analysis_df["date"]
        >= compare_start
    )
    &
    (
        analysis_df["date"]
        <= compare_end
    )
].copy()


# ============================================================
# 12. 집계 함수
# ============================================================

def summarize(data):

    spend = float(
        data["spend"].sum()
    )

    click = float(
        data["click"].sum()
    )

    conversion = float(
        data["conversion"].sum()
    )

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


base = summarize(
    base_df
)

compare = summarize(
    compare_df
)


# ============================================================
# 13. 안전한 변화율
# ============================================================

def safe_rate(
    current,
    previous
):

    if (
        current is None
        or previous is None
    ):
        return None

    if pd.isna(current) or pd.isna(previous):
        return None

    if previous == 0:
        return None

    return (
        (current - previous)
        / abs(previous)
        * 100
    )


# ============================================================
# 14. KPI 변화 텍스트
# ============================================================

def metric_change_text(
    current,
    previous,
    unit="",
    decimals=0
):

    if (
        current is None
        or previous is None
    ):
        return "-"

    if pd.isna(current) or pd.isna(previous):
        return "-"

    if previous == 0:

        if current == 0:
            return "변화 없음"

        return "신규 발생"

    diff = current - previous

    rate = (
        diff
        / abs(previous)
        * 100
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
# 15. KPI
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
            if (
                pd.notna(base["cpa"])
                and
                pd.notna(compare["cpa"])
            )
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
            if (
                pd.notna(base["cvr"])
                and
                pd.notna(compare["cvr"])
            )
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
# 16. 기간 표시
# ============================================================

st.caption(
    f"기준 기간: "
    f"{base_start.strftime('%Y-%m-%d')}"
    f" ~ "
    f"{base_end.strftime('%Y-%m-%d')}"
    f"  |  "
    f"비교 기간: "
    f"{compare_start.strftime('%Y-%m-%d')}"
    f" ~ "
    f"{compare_end.strftime('%Y-%m-%d')}"
)


# ============================================================
# 17. 매체별 집계 함수
# ============================================================

def media_summary(data):

    if len(data) == 0:

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


media_base = media_summary(
    base_df
)

media_compare = media_summary(
    compare_df
)


# ============================================================
# 18. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">'
    '📱 매체별 상세 성과 비교'
    '</div>',
    unsafe_allow_html=True
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


# 문자열/숫자 안전 처리

for col in [
    "spend_base",
    "spend_compare",
    "click_base",
    "click_compare",
    "conversion_base",
    "conversion_compare",
    "CPA_base",
    "CPA_compare",
    "CVR_base",
    "CVR_compare"
]:

    if col in media_table.columns:

        media_table[col] = pd.to_numeric(
            media_table[col],
            errors="coerce"
        ).fillna(0)


media_table["media"] = (
    media_table["media"]
    .astype("string")
    .fillna("미분류")
)


# ============================================================
# 19. 변화율 HTML 함수
# ============================================================

def rate_html(
    rate,
    positive_good=True
):

    if rate is None:
        return '<span class="neutral">-</span>'

    if pd.isna(rate):
        return '<span class="neutral">-</span>'

    if abs(rate) < 0.05:
        return '<span class="neutral">-</span>'

    if positive_good:

        if rate > 0:

            return (
                f'<span class="good">'
                f'+{rate:.1f}%'
                f'</span>'
            )

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

        return (
            f'<span class="bad">'
            f'+{rate:.1f}%'
            f'</span>'
        )


# ============================================================
# 20. 매체 HTML 표
# ============================================================

rows = []


for _, row in media_table.iterrows():

    media_name = html.escape(
        str(row["media"])
    )

    spend_base = row["spend_base"]
    spend_compare = row["spend_compare"]

    conversion_base = (
        row["conversion_base"]
    )

    conversion_compare = (
        row["conversion_compare"]
    )

    cpa_base = row["CPA_base"]
    cpa_compare = row["CPA_compare"]

    cvr_base = row["CVR_base"]
    cvr_compare = row["CVR_compare"]


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


    cpa_base_text = (
        f"{cpa_base:,.0f}원"
        if cpa_base > 0
        else "-"
    )

    cpa_compare_text = (
        f"{cpa_compare:,.0f}원"
        if cpa_compare > 0
        else "-"
    )

    cvr_base_text = (
        f"{cvr_base:.2f}%"
        if cvr_base > 0
        else "-"
    )

    cvr_compare_text = (
        f"{cvr_compare:.2f}%"
        if cvr_compare > 0
        else "-"
    )


    rows.append(
        f"""
        <tr>

            <td class="metric">
                {media_name}
            </td>


            <td>

                <div>
                    기준:
                    <b>
                        {spend_base:,.0f}원
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {spend_compare:,.0f}원
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        spend_rate,
                        positive_good=False
                    )}
                </div>

            </td>


            <td>

                <div>
                    기준:
                    <b>
                        {conversion_base:,.0f}건
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {conversion_compare:,.0f}건
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        conversion_rate,
                        positive_good=True
                    )}
                </div>

            </td>


            <td>

                <div>
                    기준:
                    <b>
                        {cpa_base_text}
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {cpa_compare_text}
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        cpa_rate,
                        positive_good=False
                    )}
                </div>

            </td>


            <td>

                <div>
                    기준:
                    <b>
                        {cvr_base_text}
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {cvr_compare_text}
                </div>

                <div style="margin-top:4px;">
                    {rate_html(
                        cvr_rate,
                        positive_good=True
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
# 21. 매체별 상세 코멘트
# ============================================================

st.markdown(
    "### 💬 매체별 성과 코멘트"
)


for _, row in media_table.iterrows():

    media_name = row["media"]

    spend_base = row["spend_base"]
    spend_compare = row["spend_compare"]

    conversion_base = row["conversion_base"]
    conversion_compare = row["conversion_compare"]

    cpa_base = row["CPA_base"]
    cpa_compare = row["CPA_compare"]

    cvr_base = row["CVR_base"]
    cvr_compare = row["CVR_compare"]


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
    # 신규 전환
    # --------------------------------------------------------

    if (
        conversion_compare == 0
        and
        conversion_base > 0
    ):

        comment = (
            f"**{media_name}**는 비교 기간에는 "
            f"전환이 없었지만 기준 기간에 "
            f"**{conversion_base:,.0f}건**의 전환이 "
            f"발생했습니다. "
            f"광고비는 **{spend_base:,.0f}원**, "
            f"CPA는 **{cpa_base:,.0f}원** 수준입니다. "
            f"전환이 새롭게 발생했다는 점은 긍정적이지만, "
            f"비교 기준이 0건이기 때문에 단순 증감률로 "
            f"성과를 판단하기보다는 현재 CPA가 목표 수준에 "
            f"부합하는지와 이후 전환량이 안정적으로 유지되는지를 "
            f"확인하는 것이 중요합니다."
        )


    # --------------------------------------------------------
    # 비교 기간 전환 존재
    # --------------------------------------------------------

    else:

        # 전환
        if conversion_rate is not None:

            if conversion_rate > 0:

                conversion_text = (
                    f"전환수는 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간 **{conversion_compare:,.0f}건** 대비 "
                    f"**{conversion_rate:.1f}% 증가**했습니다."
                )

            elif conversion_rate < 0:

                conversion_text = (
                    f"전환수는 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간 **{conversion_compare:,.0f}건** 대비 "
                    f"**{abs(conversion_rate):.1f}% 감소**했습니다."
                )

            else:

                conversion_text = (
                    f"전환수는 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간과 동일한 수준입니다."
                )

        else:

            conversion_text = (
                f"전환수는 **{conversion_base:,.0f}건**입니다."
            )


        # CPA
        if cpa_rate is not None:

            if cpa_rate < 0:

                cpa_text = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간 **{cpa_compare:,.0f}원** 대비 "
                    f"**{abs(cpa_rate):.1f}% 개선**되었습니다."
                )

            elif cpa_rate > 0:

                cpa_text = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간 **{cpa_compare:,.0f}원** 대비 "
                    f"**{cpa_rate:.1f}% 상승**했습니다."
                )

            else:

                cpa_text = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간과 동일한 수준입니다."
                )

        else:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**입니다."
            )


        # CVR
        if cvr_rate is not None:

            if cvr_rate > 0:

                cvr_text = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간 **{cvr_compare:.2f}%** 대비 "
                    f"**{cvr_rate:.1f}% 상승**했습니다."
                )

            elif cvr_rate < 0:

                cvr_text = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간 **{cvr_compare:.2f}%** 대비 "
                    f"**{abs(cvr_rate):.1f}% 하락**했습니다."
                )

            else:

                cvr_text = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간과 동일한 수준입니다."
                )

        else:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**입니다."
            )


        # 종합 해석
        if (
            cpa_rate is not None
            and
            cvr_rate is not None
        ):

            if (
                cpa_rate < 0
                and
                cvr_rate > 0
            ):

                conclusion = (
                    "전환 효율과 유입 이후 전환 효율이 "
                    "동시에 개선된 형태이므로 현재의 "
                    "타겟·소재·랜딩 조합을 유지하면서 "
                    "예산 확대 가능성을 검토할 수 있습니다."
                )

            elif (
                cpa_rate > 0
                and
                cvr_rate < 0
            ):

                conclusion = (
                    "CPA 상승과 CVR 하락이 동시에 나타나 "
                    "효율이 악화된 상태입니다. "
                    "예산을 단순 확대하기보다는 "
                    "저효율 캠페인·소재·타겟을 우선적으로 "
                    "분리해 원인을 확인하는 것이 좋습니다."
                )

            elif cpa_rate < 0:

                conclusion = (
                    "CPA가 개선되고 있어 전반적인 효율은 "
                    "긍정적인 방향으로 움직이고 있습니다. "
                    "다만 전환 규모와 함께 확인하면서 "
                    "추가 예산 투입 시에도 현재 효율이 "
                    "유지되는지를 검증할 필요가 있습니다."
                )

            elif cpa_rate > 0:

                conclusion = (
                    "CPA가 상승한 만큼 비용 효율에 대한 "
                    "점검이 필요합니다. 특히 전환량을 "
                    "유지하기 위해 광고비가 과도하게 증가한 것인지, "
                    "또는 CVR 하락으로 인해 CPA가 상승한 것인지 "
                    "세부 캠페인 단위에서 확인하는 것이 좋습니다."
                )

            else:

                conclusion = (
                    "전체적인 효율 변화가 크지 않은 만큼 "
                    "단기간의 변동보다는 캠페인별 전환 기여도와 "
                    "CPA 수준을 함께 확인해 후속 최적화 방향을 "
                    "판단하는 것이 좋습니다."
                )

        else:

            conclusion = (
                "비교 기간 데이터가 충분하지 않아 단순 증감률만으로 "
                "성과를 판단하기 어렵습니다. "
                "추가 기간 데이터를 확보한 뒤 전환 규모와 "
                "CPA 추이를 함께 확인하는 것이 좋습니다."
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
# 22. 캠페인별 성과
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">'
    '📊 캠페인별 성과'
    '</div>',
    unsafe_allow_html=True
)


def campaign_summary(data):

    if len(data) == 0:

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

    return result.sort_values(
        "conversion",
        ascending=False
    )


campaign_base = campaign_summary(
    base_df
)


# ============================================================
# 23. 캠페인 CPA + 전환수 그래프
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
                    f"{value:,.0f}원"
                    if pd.notna(value)
                    else "-"
                )
                for value in campaign_base["CPA"]
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CPA: %{y:,.0f}원"
                "<extra></extra>"
            )
        )
    )


    # --------------------------------------------------------
    # 전환수 꺾은선
    #
    # 기존 문제:
    # CPA와 전환수를 동일 축에 섞으면
    # 전환선이 왜곡되어 보일 수 있음.
    #
    # 따라서 y2 별도 축 사용
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=campaign_base["campaign"],
            y=campaign_base["conversion"],
            name="전환수",
            mode="lines+markers+text",
            yaxis="y2",
            text=[
                f"{value:,.0f}건"
                for value in campaign_base["conversion"]
            ],
            textposition="top center",
            line=dict(
                width=3
            ),
            marker=dict(
                size=9
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "전환수: %{y:,.0f}건"
                "<extra></extra>"
            )
        )
    )


    fig.update_layout(

        title={
            "text": "캠페인별 CPA + 전환수",
            "x": 0.02
        },

        xaxis=dict(
            title="캠페인",
            tickangle=-35,
            automargin=True
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
            rangemode="tozero",
            showgrid=False
        ),

        height=600,

        hovermode="x unified",

        legend=dict(
            orientation="h",
            y=1.08,
            x=0
        ),

        margin=dict(
            l=80,
            r=100,
            t=100,
            b=160
        )
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# 24. 캠페인 상세 표
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
# 25. 캠페인 핵심 코멘트
# ============================================================

st.markdown(
    "### 💬 캠페인 성과 코멘트"
)


if len(campaign_base) > 0:

    total_conversion = (
        campaign_base["conversion"].sum()
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
    # 전환수 최다
    # --------------------------------------------------------

    best_conversion_row = campaign_base.loc[
        campaign_base["conversion"].idxmax()
    ]


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
# 26. 캠페인 비교 데이터
# ============================================================

campaign_compare = campaign_summary(
    compare_df
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


# 숫자 안전 처리

for col in [
    "spend_base",
    "spend_compare",
    "click_base",
    "click_compare",
    "conversion_base",
    "conversion_compare",
    "CPA_base",
    "CPA_compare",
    "CVR_base",
    "CVR_compare"
]:

    if col in campaign_detail.columns:

        campaign_detail[col] = pd.to_numeric(
            campaign_detail[col],
            errors="coerce"
        ).fillna(0)


campaign_detail["campaign"] = (
    campaign_detail["campaign"]
    .astype("string")
    .fillna("미분류")
)


# ============================================================
# 27. 캠페인별 상세 분석
# ============================================================

st.markdown(
    "### 🔎 캠페인별 상세 분석"
)


for _, row in campaign_detail.iterrows():

    campaign_name = row["campaign"]

    spend_base = row["spend_base"]
    spend_compare = row["spend_compare"]

    conversion_base = (
        row["conversion_base"]
    )

    conversion_compare = (
        row["conversion_compare"]
    )

    cpa_base = row["CPA_base"]
    cpa_compare = row["CPA_compare"]

    cvr_base = row["CVR_base"]
    cvr_compare = row["CVR_compare"]


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
    # 신규 캠페인 / 신규 전환
    # --------------------------------------------------------

    if (
        conversion_compare == 0
        and
        conversion_base > 0
    ):

        comment = (
            f"**{campaign_name}**은 비교 기간에는 "
            f"전환이 없었으나 기준 기간에 "
            f"**{conversion_base:,.0f}건**의 전환을 "
            f"만들었습니다. "
            f"광고비는 **{spend_base:,.0f}원**, "
            f"CPA는 **{cpa_base:,.0f}원**입니다. "
            f"비교 기간 전환이 0건이기 때문에 "
            f"증감률보다는 현재 CPA가 목표 수준에 "
            f"부합하는지와 전환량이 일시적인 현상인지 "
            f"지속적으로 유지되는지를 확인하는 것이 중요합니다."
        )


    else:

        # ----------------------------------------------------
        # 전환
        # ----------------------------------------------------

        if conversion_rate is not None:

            if conversion_rate > 0:

                conversion_part = (
                    f"전환수는 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간 **{conversion_compare:,.0f}건** 대비 "
                    f"**{conversion_rate:.1f}% 증가**했습니다."
                )

            elif conversion_rate < 0:

                conversion_part = (
                    f"전환수는 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간 **{conversion_compare:,.0f}건** 대비 "
                    f"**{abs(conversion_rate):.1f}% 감소**했습니다."
                )

            else:

                conversion_part = (
                    f"전환수는 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간과 동일한 수준입니다."
                )

        else:

            conversion_part = (
                f"전환수는 **{conversion_base:,.0f}건**입니다."
            )


        # ----------------------------------------------------
        # CPA
        # ----------------------------------------------------

        if cpa_rate is not None:

            if cpa_rate < 0:

                cpa_part = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간 **{cpa_compare:,.0f}원** 대비 "
                    f"**{abs(cpa_rate):.1f}% 개선**되었습니다."
                )

            elif cpa_rate > 0:

                cpa_part = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간 **{cpa_compare:,.0f}원** 대비 "
                    f"**{cpa_rate:.1f}% 상승**했습니다."
                )

            else:

                cpa_part = (
                    f"CPA는 **{cpa_base:,.0f}원**으로 "
                    f"비교 기간과 동일한 수준입니다."
                )

        else:

            cpa_part = (
                f"CPA는 **{cpa_base:,.0f}원**입니다."
            )


        # ----------------------------------------------------
        # CVR
        # ----------------------------------------------------

        if cvr_rate is not None:

            if cvr_rate > 0:

                cvr_part = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간 **{cvr_compare:.2f}%** 대비 "
                    f"**{cvr_rate:.1f}% 상승**했습니다."
                )

            elif cvr_rate < 0:

                cvr_part = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간 **{cvr_compare:.2f}%** 대비 "
                    f"**{abs(cvr_rate):.1f}% 하락**했습니다."
                )

            else:

                cvr_part = (
                    f"CVR은 **{cvr_base:.2f}%**로 "
                    f"비교 기간과 동일한 수준입니다."
                )

        else:

            cvr_part = (
                f"CVR은 **{cvr_base:.2f}%**입니다."
            )


        # ----------------------------------------------------
        # 종합 해석
        # ----------------------------------------------------

        if (
            cpa_rate is not None
            and
            cvr_rate is not None
        ):

            if (
                cpa_rate < 0
                and
                cvr_rate > 0
            ):

                conclusion = (
                    "CPA와 CVR이 동시에 개선된 만큼 "
                    "전반적인 효율은 긍정적인 방향으로 "
                    "움직이고 있습니다. 현재의 타겟·소재·랜딩 "
                    "조합을 유지하면서 전환량을 훼손하지 않는 "
                    "범위에서 추가 예산 확대 가능성을 검토할 수 있습니다."
                )


            elif (
                cpa_rate > 0
                and
                cvr_rate < 0
            ):

                conclusion = (
                    "CPA 상승과 CVR 하락이 동시에 나타나 "
                    "효율이 악화된 상태입니다. "
                    "예산을 단순히 확대하기보다는 "
                    "저효율 타겟이나 소재를 우선적으로 분리하고 "
                    "랜딩 이후 전환 과정에서 이탈이 증가했는지도 "
                    "함께 확인하는 것이 좋습니다."
                )


            elif cpa_rate < 0:

                conclusion = (
                    "CPA가 개선되고 있어 비용 효율 측면에서는 "
                    "긍정적입니다. 다만 전환 증가가 충분히 "
                    "동반되고 있는지 확인하면서 현재 효율이 "
                    "추가 예산 투입 이후에도 유지되는지를 "
                    "검증하는 것이 중요합니다."
                )


            elif cpa_rate > 0:

                conclusion = (
                    "CPA가 상승한 만큼 비용 효율에 대한 "
                    "점검이 필요합니다. 광고비 증가 대비 "
                    "전환 증가가 충분했는지, 또는 CVR 하락이 "
                    "CPA 상승의 주요 원인인지 세부 매체·소재 "
                    "단위까지 내려가 확인하는 것이 좋습니다."
                )


            else:

                conclusion = (
                    "성과 변화가 크지 않은 만큼 단기간의 "
                    "변동보다는 전환 기여도와 CPA 수준을 "
                    "함께 확인하면서 후속 최적화 방향을 "
                    "판단하는 것이 좋습니다."
                )


        else:

            conclusion = (
                "비교 기간 데이터가 충분하지 않아 "
                "단순 증감률만으로 성과를 판단하기 어렵습니다. "
                "추가 기간 데이터를 확보한 뒤 전환 규모와 "
                "CPA 추이를 함께 확인하는 것이 좋습니다."
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
# 28. 데이터 새로고침
# ============================================================

st.divider()


if st.button("🔄 데이터 새로고침"):

    st.cache_data.clear()

    st.rerun()
