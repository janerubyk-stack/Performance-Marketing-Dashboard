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
        margin-bottom: 12px;
        line-height: 1.75;
        font-size: 14px;
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
            "impression"
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
            .str.replace("원", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # 문자
    # --------------------------------------------------------

    for col in [
        "type",
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
                "None"
            ]),
            col
        ] = "미분류"

    return df


df = load_data()


# ============================================================
# 4. 제목
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
# 5. 날짜 확인
# ============================================================

valid_dates = df["date"].dropna()

if len(valid_dates) == 0:

    st.error("날짜 데이터를 확인할 수 없습니다.")
    st.stop()

min_date = valid_dates.min().date()
max_date = valid_dates.max().date()


# ============================================================
# 6. 분석 조건
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
# 7. 기간 선택
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
# 8. 비교 기간 계산
# ============================================================

base_date = pd.Timestamp(base_date)


if compare_mode == "전일":

    base_start = base_date
    base_end = base_date

    compare_start = base_date - timedelta(days=1)
    compare_end = compare_start


elif compare_mode == "전주":

    base_start = base_date
    base_end = base_date

    compare_start = base_date - timedelta(days=7)
    compare_end = compare_start


elif compare_mode == "전월":

    base_start = base_date
    base_end = base_date

    previous_month = base_date - pd.DateOffset(months=1)

    compare_start = previous_month
    compare_end = previous_month


else:

    st.info(
        "지정 비교는 기준 기간과 동일한 일수로 비교합니다."
    )

    custom_compare_start = st.date_input(
        "비교 시작일",
        value=(
            base_date -
            timedelta(days=1)
        ).date(),
        min_value=min_date,
        max_value=max_date
    )

    custom_compare_start = pd.Timestamp(
        custom_compare_start
    )

    base_start = base_date
    base_end = base_date

    compare_start = custom_compare_start

    period_days = (
        base_end -
        base_start
    ).days + 1

    compare_end = (
        compare_start +
        timedelta(
            days=period_days - 1
        )
    )


# ============================================================
# 9. 필터
# ============================================================

condition = (
    df["type"].isin(selected_type)
    &
    df["media"].isin(selected_media)
    &
    df["campaign"].isin(selected_campaign)
)

analysis_df = df[condition].copy()


# ============================================================
# 10. 기간 데이터
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
# 11. 집계 함수
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
# 12. 안전한 변화율
# ============================================================

def safe_rate(current, previous):

    if pd.isna(current):
        return None

    if pd.isna(previous):
        return None

    if previous == 0:
        return None

    return (
        (current - previous)
        / abs(previous)
        * 100
    )


# ============================================================
# 13. 변화 텍스트
# ============================================================

def format_rate(
    current,
    previous,
    metric_type="normal"
):

    rate = safe_rate(
        current,
        previous
    )

    if rate is None:

        if (
            previous == 0
            and current > 0
        ):
            return "신규 발생"

        if (
            current == 0
            and previous > 0
        ):
            return "0건"

        return "-"

    # 일반 지표
    if metric_type == "normal":

        if rate > 0:
            return f"+{rate:.1f}%"

        elif rate < 0:
            return f"{rate:.1f}%"

        return "변화 없음"

    # 효율 지표
    if metric_type == "efficiency":

        if rate < 0:
            return f"-{abs(rate):.1f}% 개선"

        elif rate > 0:
            return f"+{rate:.1f}% 악화"

        return "변화 없음"

    return f"{rate:+.1f}%"


# ============================================================
# 14. KPI
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">📊 핵심 성과 비교</div>',
    unsafe_allow_html=True
)


spend_change = format_rate(
    base["spend"],
    compare["spend"],
    "normal"
)

conversion_change = format_rate(
    base["conversion"],
    compare["conversion"],
    "normal"
)

cpa_change = format_rate(
    base["cpa"],
    compare["cpa"],
    "efficiency"
)

cvr_change = format_rate(
    base["cvr"],
    compare["cvr"],
    "normal"
)


kpi_data = [

    (
        "광고비",
        f"{base['spend']:,.0f}원",
        spend_change
    ),

    (
        "전환수",
        f"{base['conversion']:,.0f}건",
        conversion_change
    ),

    (
        "CPA",
        (
            f"{base['cpa']:,.0f}원"
            if pd.notna(base["cpa"])
            else "-"
        ),
        cpa_change
    ),

    (
        "CVR",
        (
            f"{base['cvr']:.2f}%"
            if pd.notna(base["cvr"])
            else "-"
        ),
        cvr_change
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
    f"{base_end.strftime('%Y-%m-%d')} "
    f"| 비교 기간: "
    f"{compare_start.strftime('%Y-%m-%d')} ~ "
    f"{compare_end.strftime('%Y-%m-%d')}"
)


# ============================================================
# 16. 매체별 집계
# ============================================================

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


# ============================================================
# 17. 매체별 상세 성과 비교
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">'
    '📱 매체별 상세 성과 비교'
    '</div>',
    unsafe_allow_html=True
)


media_base = media_summary(base_df)
media_compare = media_summary(compare_df)


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


# ============================================================
# 18. 매체별 HTML 표
# ============================================================

rows = []


for _, row in media_table.iterrows():

    media_name = row["media"]

    spend_base = (
        row["spend_base"]
        if pd.notna(row["spend_base"])
        else 0
    )

    spend_compare = (
        row["spend_compare"]
        if pd.notna(row["spend_compare"])
        else 0
    )

    conversion_base = (
        row["conversion_base"]
        if pd.notna(row["conversion_base"])
        else 0
    )

    conversion_compare = (
        row["conversion_compare"]
        if pd.notna(row["conversion_compare"])
        else 0
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

    # --------------------------------------------------------
    # 광고비 변화
    # --------------------------------------------------------

    if spend_rate is None:

        if spend_base > 0 and spend_compare == 0:
            spend_change_html = (
                '<span class="neutral">신규 집행</span>'
            )

        else:
            spend_change_html = (
                '<span class="neutral">-</span>'
            )

    elif spend_rate > 0:

        spend_change_html = (
            f'<span class="bad">'
            f'+{spend_rate:.1f}%'
            f'</span>'
        )

    elif spend_rate < 0:

        spend_change_html = (
            f'<span class="good">'
            f'{spend_rate:.1f}%'
            f'</span>'
        )

    else:

        spend_change_html = (
            '<span class="neutral">-</span>'
        )

    # --------------------------------------------------------
    # 전환 변화
    # --------------------------------------------------------

    if conversion_rate is None:

        if (
            conversion_base > 0
            and conversion_compare == 0
        ):
            conversion_change_html = (
                '<span class="good">신규 발생</span>'
            )

        elif (
            conversion_base == 0
            and conversion_compare > 0
        ):
            conversion_change_html = (
                '<span class="bad">0건</span>'
            )

        else:
            conversion_change_html = (
                '<span class="neutral">-</span>'
            )

    elif conversion_rate > 0:

        conversion_change_html = (
            f'<span class="good">'
            f'+{conversion_rate:.1f}%'
            f'</span>'
        )

    elif conversion_rate < 0:

        conversion_change_html = (
            f'<span class="bad">'
            f'{conversion_rate:.1f}%'
            f'</span>'
        )

    else:

        conversion_change_html = (
            '<span class="neutral">-</span>'
        )

    # --------------------------------------------------------
    # CPA 변화
    # --------------------------------------------------------

    if cpa_rate is None:

        cpa_change_html = (
            '<span class="neutral">-</span>'
        )

    elif cpa_rate < 0:

        cpa_change_html = (
            f'<span class="good">'
            f'-{abs(cpa_rate):.1f}%'
            f'</span>'
        )

    elif cpa_rate > 0:

        cpa_change_html = (
            f'<span class="bad">'
            f'+{cpa_rate:.1f}%'
            f'</span>'
        )

    else:

        cpa_change_html = (
            '<span class="neutral">-</span>'
        )

    # --------------------------------------------------------
    # CVR 변화
    # --------------------------------------------------------

    if cvr_rate is None:

        cvr_change_html = (
            '<span class="neutral">-</span>'
        )

    elif cvr_rate > 0:

        cvr_change_html = (
            f'<span class="good">'
            f'+{cvr_rate:.1f}%'
            f'</span>'
        )

    elif cvr_rate < 0:

        cvr_change_html = (
            f'<span class="bad">'
            f'{cvr_rate:.1f}%'
            f'</span>'
        )

    else:

        cvr_change_html = (
            '<span class="neutral">-</span>'
        )

    rows.append(
        f"""
        <tr>

            <td style="
                padding:12px;
                font-weight:700;
            ">
                {html.escape(str(media_name))}
            </td>

            <td style="padding:12px;">

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
                    {spend_change_html}
                </div>

            </td>

            <td style="padding:12px;">

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
                    {conversion_change_html}
                </div>

            </td>

            <td style="padding:12px;">

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
                    {cpa_change_html}
                </div>

            </td>

            <td style="padding:12px;">

                <div>
                    기준:
                    <b>
                        {
                            f"{cvr_base:.2f}%"
                            if pd.notna(cvr_base)
                            else "-"
                        }
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {
                        f"{cvr_compare:.2f}%"
                        if pd.notna(cvr_compare)
                        else "-"
                    }
                </div>

                <div style="margin-top:4px;">
                    {cvr_change_html}
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

    spend_base = (
        row["spend_base"]
        if pd.notna(row["spend_base"])
        else 0
    )

    spend_compare = (
        row["spend_compare"]
        if pd.notna(row["spend_compare"])
        else 0
    )

    conversion_base = (
        row["conversion_base"]
        if pd.notna(row["conversion_base"])
        else 0
    )

    conversion_compare = (
        row["conversion_compare"]
        if pd.notna(row["conversion_compare"])
        else 0
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

    # --------------------------------------------------------
    # 변화 문장
    # --------------------------------------------------------

    if spend_rate is None:

        if (
            spend_base > 0
            and spend_compare == 0
        ):
            spend_text = (
                f"비교 기간에는 광고비 집행이 없었으나 "
                f"기준 기간에 **{spend_base:,.0f}원**을 새롭게 집행했습니다."
            )

        else:
            spend_text = (
                f"광고비는 **{spend_base:,.0f}원**입니다."
            )

    else:

        spend_text = (
            f"광고비는 **{spend_base:,.0f}원**으로 "
            f"비교 기간 대비 **{abs(spend_rate):.1f}% "
            f"{'증가' if spend_rate > 0 else '감소'}**했습니다."
        )

    # --------------------------------------------------------
    # 전환 문장
    # --------------------------------------------------------

    if conversion_rate is None:

        if (
            conversion_base > 0
            and conversion_compare == 0
        ):

            conversion_text = (
                f"전환은 비교 기간 0건에서 "
                f"기준 기간 **{conversion_base:,.0f}건**으로 "
                f"새롭게 발생했습니다."
            )

        elif (
            conversion_base == 0
            and conversion_compare > 0
        ):

            conversion_text = (
                f"전환은 비교 기간 "
                f"**{conversion_compare:,.0f}건**에서 "
                f"기준 기간 **0건**으로 감소했습니다."
            )

        else:

            conversion_text = (
                f"전환은 **{conversion_base:,.0f}건**입니다."
            )

    else:

        conversion_text = (
            f"전환은 **{conversion_base:,.0f}건**으로 "
            f"비교 기간 대비 **{abs(conversion_rate):.1f}% "
            f"{'증가' if conversion_rate > 0 else '감소'}**했습니다."
        )

    # --------------------------------------------------------
    # CPA 문장
    # --------------------------------------------------------

    if pd.notna(cpa_base):

        if cpa_rate is None:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**입니다."
            )

        elif cpa_rate < 0:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**으로 "
                f"비교 기간 대비 **{abs(cpa_rate):.1f}% 개선**됐습니다."
            )

        elif cpa_rate > 0:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**으로 "
                f"비교 기간 대비 **{cpa_rate:.1f}% 상승**했습니다."
            )

        else:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**으로 "
                f"변화가 없습니다."
            )

    else:

        cpa_text = (
            "기준 기간에는 전환이 없어 CPA를 산출할 수 없습니다."
        )

    # --------------------------------------------------------
    # CVR 문장
    # --------------------------------------------------------

    if pd.notna(cvr_base):

        if cvr_rate is None:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**입니다."
            )

        elif cvr_rate > 0:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**로 "
                f"비교 기간 대비 **{abs(cvr_rate):.1f}% 상승**했습니다."
            )

        elif cvr_rate < 0:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**로 "
                f"비교 기간 대비 **{abs(cvr_rate):.1f}% 하락**했습니다."
            )

        else:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**로 "
                f"변화가 없습니다."
            )

    else:

        cvr_text = (
            "클릭 데이터가 없어 CVR을 산출할 수 없습니다."
        )

    # --------------------------------------------------------
    # 종합 판단
    # --------------------------------------------------------

    if (
        cpa_rate is not None
        and cvr_rate is not None
    ):

        if (
            cpa_rate < 0
            and cvr_rate > 0
        ):

            conclusion = (
                "CPA가 개선되는 동시에 CVR도 상승했기 때문에 "
                "유입 이후 전환 효율이 전반적으로 개선된 것으로 볼 수 있습니다. "
                "현재 효율이 유지되는지 확인하면서 우수 캠페인 중심의 "
                "추가 예산 확대를 검토할 수 있습니다."
            )

        elif (
            cpa_rate > 0
            and cvr_rate < 0
        ):

            conclusion = (
                "CPA 상승과 CVR 하락이 동시에 나타나 "
                "유입 이후 전환 효율이 악화된 것으로 판단됩니다. "
                "예산을 즉시 확대하기보다 캠페인별·소재별·타깃별 성과를 "
                "세분화해 효율 저하 원인을 먼저 확인하는 것이 적절합니다."
            )

        elif cpa_rate < 0:

            conclusion = (
                "CPA가 개선되고 있어 비용 효율 측면에서는 긍정적인 흐름입니다. "
                "다만 전환 규모와 CVR 변화도 함께 확인하면서 "
                "효율 개선이 일시적인 현상인지 지속적인 흐름인지 판단하는 것이 좋습니다."
            )

        elif cpa_rate > 0:

            conclusion = (
                "CPA가 상승하면서 비용 효율이 악화된 상태입니다. "
                "전환량을 유지하기 위해 단순 예산 증액을 하기보다 "
                "전환 기여도가 높은 캠페인과 지면 중심으로 예산을 재배분하는 것이 좋습니다."
            )

        else:

            conclusion = (
                "CPA 변화가 크지 않은 만큼 전환 규모와 CVR 변화를 함께 확인하면서 "
                "현재 집행 수준을 유지할지 추가 최적화를 진행할지 판단하는 것이 좋습니다."
            )

    else:

        conclusion = (
            "비교 기간의 데이터가 충분하지 않아 단순 변화율만으로 "
            "성과 방향을 판단하기 어렵습니다. "
            "추가 기간의 데이터를 함께 확인해 성과가 안정적으로 유지되는지 "
            "확인하는 것이 좋습니다."
        )

    comment = (
        f"**{media_name}**는 {spend_text} "
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
    '<div class="section-title">'
    '📊 캠페인별 성과'
    '</div>',
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
)


# ============================================================
# 21. 캠페인 CPA + 전환수 그래프
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
            )
        )
    )

    # --------------------------------------------------------
    # 전환수 꺾은선
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=campaign_base["campaign"],
            y=campaign_base["conversion"],
            name="전환수",
            mode="lines+markers+text",
            yaxis="y2",
            text=[
                f"{x:,.0f}건"
                for x in campaign_base["conversion"]
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
                "전환: %{y:,.0f}건"
                "<extra></extra>"
            )
        )
    )

    # --------------------------------------------------------
    # 전환수 축 범위
    # --------------------------------------------------------

    max_conversion = (
        campaign_base["conversion"].max()
    )

    if max_conversion > 0:

        conversion_axis_max = (
            max_conversion * 1.25
        )

    else:

        conversion_axis_max = 1

    # --------------------------------------------------------
    # 그래프
    # --------------------------------------------------------

    fig.update_layout(

        title={
            "text": "캠페인별 CPA + 전환수",
            "x": 0.02
        },

        xaxis=dict(
            title="캠페인",
            tickangle=-35,
            type="category"
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
            range=[
                0,
                conversion_axis_max
            ],
            tickformat=","
        ),

        height=620,

        hovermode="x unified",

        legend=dict(
            orientation="h",
            y=1.08,
            x=0
        ),

        margin=dict(
            l=80,
            r=90,
            t=100,
            b=170
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
        (
            f"{x:,.0f}원"
            if pd.notna(x)
            else "-"
        )
    )
)


campaign_display["CVR"] = (
    campaign_display["CVR"]
    .map(
        lambda x:
        (
            f"{x:.2f}%"
            if pd.notna(x)
            else "-"
        )
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
        campaign_base["conversion"].sum()
    )

    # --------------------------------------------------------
    # CPA 최우수 캠페인
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
    # 전환수 최다 캠페인
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
    '<div class="section-title">'
    '🔎 캠페인 드릴다운'
    '</div>',
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


# ============================================================
# 25. 캠페인 비교 데이터
# ============================================================

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


# ============================================================
# 26. 캠페인별 상세 코멘트
# ============================================================

if len(campaign_detail) > 0:

    for _, row in campaign_detail.iterrows():

        campaign_name = row["campaign"]

        spend_base = (
            row["spend_base"]
            if pd.notna(row["spend_base"])
            else 0
        )

        spend_compare = (
            row["spend_compare"]
            if pd.notna(row["spend_compare"])
            else 0
        )

        conversion_base = (
            row["conversion_base"]
            if pd.notna(row["conversion_base"])
            else 0
        )

        conversion_compare = (
            row["conversion_compare"]
            if pd.notna(row["conversion_compare"])
            else 0
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

        # ----------------------------------------------------
        # 신규 캠페인
        # ----------------------------------------------------

        if (
            conversion_compare == 0
            and conversion_base > 0
        ):

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**"
                if pd.notna(cpa_base)
                else "CPA는 산출할 수 없으며"
            )

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**"
                if pd.notna(cvr_base)
                else "CVR은 산출할 수 없습니다"
            )

            comment = (
                f"**{campaign_name}**은 비교 기간에는 "
                f"전환이 없었으나 기준 기간에 "
                f"**{conversion_base:,.0f}건**의 전환을 새롭게 만들었습니다. "
                f"광고비는 **{spend_base:,.0f}원**, "
                f"{cpa_text}, {cvr_text}입니다. "
                f"비교 대상 기간에 전환이 없었기 때문에 변화율만으로 "
                f"성과 개선 폭을 판단하기는 어렵지만, "
                f"기준 기간에 실제 전환을 만들어냈다는 점은 긍정적입니다. "
                f"향후에는 현재 전환량이 일시적인 증가인지, "
                f"동일한 효율로 지속 가능한지 추가 기간을 확인하면서 "
                f"예산 확대 여부를 판단하는 것이 좋습니다."
            )

        # ----------------------------------------------------
        # 종료/전환 0 캠페인
        # ----------------------------------------------------

        elif (
            conversion_base == 0
            and conversion_compare > 0
        ):

            comment = (
                f"**{campaign_name}**은 비교 기간에 "
                f"**{conversion_compare:,.0f}건**의 전환이 발생했지만 "
                f"기준 기간에는 전환이 **0건**으로 감소했습니다. "
                f"기준 기간 광고비는 **{spend_base:,.0f}원**이며 "
                f"전환이 발생하지 않아 CPA는 산출되지 않습니다. "
                f"기존에 전환을 만들던 캠페인에서 성과가 끊긴 만큼 "
                f"예산 자체의 문제인지, 유입량 감소인지, "
                f"소재·타깃·랜딩페이지 등의 전환 효율 저하인지 "
                f"세부적으로 확인할 필요가 있습니다. "
                f"원인 확인 전까지는 추가 예산 확대보다 "
                f"전환 재확보를 우선하는 것이 적절합니다."
            )

        # ----------------------------------------------------
        # 일반 캠페인
        # ----------------------------------------------------

        else:

            # 광고비
            if spend_rate is None:

                spend_text = (
                    f"광고비는 **{spend_base:,.0f}원**입니다."
                )

            else:

                spend_text = (
                    f"광고비는 **{spend_base:,.0f}원**으로 "
                    f"비교 기간 대비 **{abs(spend_rate):.1f}% "
                    f"{'증가' if spend_rate > 0 else '감소'}**했습니다."
                )

            # 전환
            if conversion_rate is None:

                conversion_text = (
                    f"전환은 **{conversion_base:,.0f}건**입니다."
                )

            elif conversion_rate > 0:

                conversion_text = (
                    f"전환은 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간 대비 **{conversion_rate:.1f}% 증가**했습니다."
                )

            elif conversion_rate < 0:

                conversion_text = (
                    f"전환은 **{conversion_base:,.0f}건**으로 "
                    f"비교 기간 대비 **{abs(conversion_rate):.1f}% 감소**했습니다."
                )

            else:

                conversion_text = (
                    f"전환은 **{conversion_base:,.0f}건**으로 "
                    f"변화가 없습니다."
                )

            # CPA
            if pd.notna(cpa_base):

                if cpa_rate is None:

                    cpa_text = (
                        f"CPA는 **{cpa_base:,.0f}원**입니다."
                    )

                elif cpa_rate < 0:

                    cpa_text = (
                        f"CPA는 **{cpa_base:,.0f}원**으로 "
                        f"비교 기간 대비 **{abs(cpa_rate):.1f}% 개선**됐습니다."
                    )

                elif cpa_rate > 0:

                    cpa_text = (
                        f"CPA는 **{cpa_base:,.0f}원**으로 "
                        f"비교 기간 대비 **{cpa_rate:.1f}% 상승**했습니다."
                    )

                else:

                    cpa_text = (
                        f"CPA는 **{cpa_base:,.0f}원**으로 "
                        f"변화가 없습니다."
                    )

            else:

                cpa_text = (
                    "CPA는 산출되지 않습니다."
                )

            # CVR
            if pd.notna(cvr_base):

                if cvr_rate is None:

                    cvr_text = (
                        f"CVR은 **{cvr_base:.2f}%**입니다."
                    )

                elif cvr_rate > 0:

                    cvr_text = (
                        f"CVR은 **{cvr_base:.2f}%**로 "
                        f"비교 기간 대비 **{abs(cvr_rate):.1f}% 상승**했습니다."
                    )

                elif cvr_rate < 0:

                    cvr_text = (
                        f"CVR은 **{cvr_base:.2f}%**로 "
                        f"비교 기간 대비 **{abs(cvr_rate):.1f}% 하락**했습니다."
                    )

                else:

                    cvr_text = (
                        f"CVR은 **{cvr_base:.2f}%**로 "
                        f"변화가 없습니다."
                    )

            else:

                cvr_text = (
                    "CVR은 산출되지 않습니다."
                )

            # ------------------------------------------------
            # 성과 해석
            # ------------------------------------------------

            if (
                cpa_rate is not None
                and cvr_rate is not None
            ):

                if (
                    cpa_rate < 0
                    and cvr_rate > 0
                    and conversion_rate is not None
                    and conversion_rate > 0
                ):

                    interpretation = (
                        "전환 증가와 함께 CPA가 개선되고 CVR도 상승해 "
                        "물량과 효율이 동시에 좋아진 구간으로 판단됩니다. "
                        "성과가 유지된다면 예산 확대를 우선 검토할 수 있습니다."
                    )

                elif (
                    cpa_rate > 0
                    and cvr_rate < 0
                ):

                    interpretation = (
                        "CPA 상승과 CVR 하락이 동시에 나타나 "
                        "전환 효율이 악화된 것으로 판단됩니다. "
                        "추가 예산 확대보다는 소재·타깃·매체 지면별 "
                        "성과를 분해해 비효율 원인을 확인하는 것이 우선입니다."
                    )

                elif (
                    cpa_rate < 0
                    and conversion_rate is not None
                    and conversion_rate > 0
                ):

                    interpretation = (
                        "전환이 증가하면서 CPA도 개선돼 "
                        "비용 대비 전환 효율이 긍정적으로 움직이고 있습니다. "
                        "현재 성과를 유지하면서 우수 영역을 중심으로 "
                        "점진적인 예산 확대를 검토할 수 있습니다."
                    )

                elif cpa_rate > 0:

                    interpretation = (
                        "CPA가 상승해 비용 효율이 악화된 만큼 "
                        "현재 예산을 동일하게 유지하기보다 "
                        "전환 기여도가 높은 영역으로 예산을 재배분하고 "
                        "비효율 캠페인의 원인을 확인하는 것이 좋습니다."
                    )

                elif cvr_rate > 0:

                    interpretation = (
                        "CVR이 상승해 유입 이후 전환 효율은 개선되고 있습니다. "
                        "전환량과 CPA까지 함께 안정적으로 유지되는지 확인하면서 "
                        "추가 확장 여부를 판단하는 것이 좋습니다."
                    )

                else:

                    interpretation = (
                        "주요 지표의 변화가 크지 않은 만큼 "
                        "현재 집행 수준을 유지하면서 추가 기간의 데이터를 확인해 "
                        "성과 방향을 판단하는 것이 좋습니다."
                    )

            else:

                interpretation = (
                    "비교 기간 데이터가 충분하지 않아 변화율만으로 "
                    "성과 방향을 판단하기 어렵습니다. "
                    "추가 기간의 데이터를 함께 확인하는 것이 좋습니다."
                )

            comment = (
                f"**{campaign_name}**은 기준 기간에 "
                f"{spend_text} "
                f"{conversion_text} "
                f"{cpa_text} "
                f"{cvr_text} "
                f"{interpretation}"
            )

        st.markdown(
            f'<div class="comment-box">{comment}</div>',
            unsafe_allow_html=True
        )


# ============================================================
# 27. 데이터 새로고침
# ============================================================

st.divider()

if st.button("🔄 데이터 새로고침"):

    st.cache_data.clear()

    st.rerun()
