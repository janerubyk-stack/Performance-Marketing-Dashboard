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
# 2. 기본 CSS
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
        line-height: 1.7;
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

    # 컬럼명 정리
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

        if col_lower in ["광고유형", "유형", "type"]:
            rename_map[col] = "type"

        elif col_lower in ["매체", "media", "media2"]:
            rename_map[col] = "media"

        elif col_lower in ["캠페인", "campaign"]:
            rename_map[col] = "campaign"

        elif col_lower in ["노출", "노출수", "impress", "impression"]:
            rename_map[col] = "impress"

        elif col_lower in ["클릭", "클릭수", "click"]:
            rename_map[col] = "click"

        elif col_lower in ["광고비", "spend", "cost"]:
            rename_map[col] = "spend"

        elif col_lower in ["전환", "전환수", "conversion"]:
            rename_map[col] = "conversion"

        elif col_lower in ["날짜", "date"]:
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
            .str.replace("원", "", regex=False)
            .str.strip()
        )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # 문자 컬럼
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
            df[col].isin(["", "nan", "None"]),
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
# 5. 데이터 기간
# ============================================================

valid_dates = df["date"].dropna()

if len(valid_dates) == 0:

    st.error("날짜 데이터를 확인할 수 없습니다.")
    st.stop()

min_date = valid_dates.min().date()
max_date = valid_dates.max().date()


# ============================================================
# 6. 분석 기준
# ============================================================

st.markdown(
    '<div class="section-title">🔎 분석 조건</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)


with col1:

    selected_type = st.multiselect(
        "카테고리",
        sorted(df["type"].unique()),
        default=sorted(df["type"].unique())
    )


with col2:

    selected_media = st.multiselect(
        "매체",
        sorted(df["media"].unique()),
        default=sorted(df["media"].unique())
    )


with col3:

    selected_campaign = st.multiselect(
        "캠페인",
        sorted(df["campaign"].unique()),
        default=sorted(df["campaign"].unique())
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
        "지정 비교는 기준일과 동일한 일수의 기간을 비교합니다."
    )

    custom_compare = st.date_input(
        "비교 시작일",
        value=(base_date - timedelta(days=1)).date(),
        min_value=min_date,
        max_value=max_date
    )

    compare_start = pd.Timestamp(custom_compare)

    period_days = 1

    compare_end = (
        compare_start +
        timedelta(days=period_days - 1)
    )

    base_start = base_date
    base_end = base_date


# ============================================================
# 9. 필터 적용
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
# 12. 변화율 함수
# ============================================================

def change_rate(base_value, compare_value):

    if (
        pd.isna(base_value)
        or pd.isna(compare_value)
        or compare_value == 0
    ):
        return None

    return (
        (base_value - compare_value)
        / abs(compare_value)
        * 100
    )


def metric_change_text(
    base_value,
    compare_value,
    unit="",
    decimals=0
):

    if compare_value == 0:

        if base_value == 0:
            return "변화 없음"

        return "신규 발생"

    diff = base_value - compare_value

    rate = (
        diff
        / abs(compare_value)
        * 100
    )

    if decimals == 0:

        value_text = f"{abs(diff):,.0f}{unit}"

    else:

        value_text = (
            f"{abs(diff):,.{decimals}f}{unit}"
        )

    if diff > 0:
        return f"+{value_text} (+{rate:.1f}%)"

    elif diff < 0:
        return f"-{value_text} ({rate:.1f}%)"

    return "변화 없음"


# ============================================================
# 13. KPI
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


for col, item in zip(kpi_cols, kpi_data):

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

                <div style="margin-top:8px;color:#6b7280;">
                    비교: {item[2]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# 14. 기간 설명
# ============================================================

st.caption(
    f"기준 기간: {base_start.strftime('%Y-%m-%d')} ~ "
    f"{base_end.strftime('%Y-%m-%d')}  |  "
    f"비교 기간: {compare_start.strftime('%Y-%m-%d')} ~ "
    f"{compare_end.strftime('%Y-%m-%d')}"
)


# ============================================================
# 15. 매체별 성과 비교
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">📱 매체별 상세 성과 비교</div>',
    unsafe_allow_html=True
)


def media_summary(data):

    result = (
        data
        .groupby("media", as_index=False)
        .agg(
            spend=("spend", "sum"),
            click=("click", "sum"),
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
        result["conversion"] / result["click"] * 100,
        np.nan
    )

    return result


media_base = media_summary(base_df)
media_compare = media_summary(compare_df)


media_table = pd.merge(
    media_base,
    media_compare,
    on="media",
    how="outer",
    suffixes=("_base", "_compare")
).fillna(0)


# ------------------------------------------------------------
# 매체별 HTML 표
# ------------------------------------------------------------

def safe_rate(current, previous):

    if previous == 0:
        return None

    return (
        (current - previous)
        / abs(previous)
        * 100
    )


rows = []


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

            <td class="metric">
                {html.escape(str(media_name))}
            </td>

            <td>
                <div>
                    기준: <b>{spend_base:,.0f}원</b>
                </div>

                <div style="color:#888;">
                    비교: {spend_compare:,.0f}원
                </div>

                <div style="margin-top:4px;">
                    {
                        f'<span class="bad">+{spend_rate:.1f}%</span>'
                        if spend_rate is not None and spend_rate > 0
                        else (
                            f'<span class="good">{spend_rate:.1f}%</span>'
                            if spend_rate is not None
                            else '<span class="neutral">-</span>'
                        )
                    }
                </div>
            </td>


            <td>
                <div>
                    기준: <b>{conversion_base:,.0f}건</b>
                </div>

                <div style="color:#888;">
                    비교: {conversion_compare:,.0f}건
                </div>

                <div style="margin-top:4px;">
                    {
                        f'<span class="good">+{conversion_rate:.1f}%</span>'
                        if conversion_rate is not None and conversion_rate > 0
                        else (
                            f'<span class="bad">{conversion_rate:.1f}%</span>'
                            if conversion_rate is not None
                            else '<span class="neutral">-</span>'
                        )
                    }
                </div>
            </td>


            <td>
                <div>
                    기준:
                    <b>
                        {
                            f"{cpa_base:,.0f}원"
                            if cpa_base > 0
                            else "-"
                        }
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {
                        f"{cpa_compare:,.0f}원"
                        if cpa_compare > 0
                        else "-"
                    }
                </div>

                <div style="margin-top:4px;">
                    {
                        f'<span class="good">-{abs(cpa_rate):.1f}%</span>'
                        if cpa_rate is not None and cpa_rate < 0
                        else (
                            f'<span class="bad">+{cpa_rate:.1f}%</span>'
                            if cpa_rate is not None and cpa_rate > 0
                            else '<span class="neutral">-</span>'
                        )
                    }
                </div>
            </td>


            <td>
                <div>
                    기준:
                    <b>
                        {
                            f"{cvr_base:.2f}%"
                            if cvr_base > 0
                            else "-"
                        }
                    </b>
                </div>

                <div style="color:#888;">
                    비교:
                    {
                        f"{cvr_compare:.2f}%"
                        if cvr_compare > 0
                        else "-"
                    }
                </div>

                <div style="margin-top:4px;">
                    {
                        f'<span class="good">+{cvr_rate:.1f}%</span>'
                        if cvr_rate is not None and cvr_rate > 0
                        else (
                            f'<span class="bad">{cvr_rate:.1f}%</span>'
                            if cvr_rate is not None
                            else '<span class="neutral">-</span>'
                        )
                    }
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

<th style="padding:12px;text-align:left;">
매체
</th>

<th style="padding:12px;text-align:left;">
광고비
</th>

<th style="padding:12px;text-align:left;">
전환수
</th>

<th style="padding:12px;text-align:left;">
CPA
</th>

<th style="padding:12px;text-align:left;">
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
# 16. 매체별 상세 코멘트
# ============================================================

st.markdown("### 💬 매체별 성과 코멘트")


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

    # 신규
    if conversion_compare == 0 and conversion_base > 0:

        comment = (
            f"**{media_name}**는 비교 기간에는 전환이 없었지만 "
            f"기준 기간에 **{conversion_base:,.0f}건**의 전환이 발생했습니다. "
            f"광고비는 **{spend_base:,.0f}원**, "
            f"CPA는 **{cpa_base:,.0f}원** 수준입니다. "
            f"현재 전환이 새롭게 발생한 매체이므로 단순히 전환 규모만 보기보다 "
            f"CPA가 목표 수준에 부합하는지와 이후에도 전환량이 안정적으로 유지되는지를 "
            f"함께 확인할 필요가 있습니다."
        )

    else:

        conversion_text = (
            f"전환수는 **{conversion_base:,.0f}건**으로 "
            f"비교 기간 대비 **{conversion_rate:+.1f}%** "
            f"{'증가' if conversion_rate and conversion_rate > 0 else '감소'}했습니다."
            if conversion_rate is not None
            else
            f"전환수는 **{conversion_base:,.0f}건**입니다."
        )

        if cpa_rate is not None:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**으로 "
                f"비교 기간 대비 **{abs(cpa_rate):.1f}% "
                f"{'개선' if cpa_rate < 0 else '상승'}**했습니다."
            )

        else:

            cpa_text = (
                f"CPA는 **{cpa_base:,.0f}원**입니다."
            )

        if cvr_rate is not None:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**로 "
                f"비교 기간 대비 **{abs(cvr_rate):.1f}% "
                f"{'상승' if cvr_rate > 0 else '하락'}**했습니다."
            )

        else:

            cvr_text = (
                f"CVR은 **{cvr_base:.2f}%**입니다."
            )

        comment = (
            f"**{media_name}**는 기준 기간에 "
            f"광고비 **{spend_base:,.0f}원**을 집행해 "
            f"{conversion_text} "
            f"{cpa_text} "
            f"{cvr_text} "
            f"따라서 이번 기간에는 단순 전환 규모뿐 아니라 "
            f"광고비 증가가 전환 증가로 충분히 연결됐는지, "
            f"그리고 CPA와 CVR 개선이 동시에 나타났는지를 기준으로 "
            f"효율을 판단하는 것이 적절합니다."
        )

    st.markdown(
        f'<div class="comment-box">{comment}</div>',
        unsafe_allow_html=True
    )


# ============================================================
# 17. 캠페인 성과
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">📊 캠페인별 성과</div>',
    unsafe_allow_html=True
)


campaign_base = (
    base_df
    .groupby("campaign", as_index=False)
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
# 18. 캠페인 차트
# ============================================================

if len(campaign_base) > 0:

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=campaign_base["campaign"],
            y=campaign_base["CPA"],
            name="CPA",
            text=[
                f"{x:,.0f}원" if pd.notna(x) else "-"
                for x in campaign_base["CPA"]
            ],
            textposition="outside"
        )
    )

    # 전환수는 별도 축
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
            line=dict(width=3),
            marker=dict(size=8)
        )
    )

    fig.update_layout(
        title="캠페인별 CPA + 전환수",
        xaxis=dict(
            title="캠페인",
            tickangle=-35
        ),
        yaxis=dict(
            title="CPA",
            tickformat=","
        ),
        yaxis2=dict(
            title="전환수",
            overlaying="y",
            side="right",
            rangemode="tozero"
        ),
        height=600,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.08,
            x=0
        ),
        margin=dict(
            l=70,
            r=80,
            t=90,
            b=150
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# 19. 캠페인 상세 표
# ============================================================

st.markdown("### 📋 캠페인 상세 성과")


campaign_display = campaign_base.copy()

campaign_display["광고비"] = (
    campaign_display["spend"]
    .map(lambda x: f"{x:,.0f}원")
)

campaign_display["전환수"] = (
    campaign_display["conversion"]
    .map(lambda x: f"{x:,.0f}건")
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
# 20. 캠페인 핵심 코멘트
# ============================================================

st.markdown("### 💬 캠페인 성과 코멘트")


if len(campaign_base) > 0:

    total_conversion = campaign_base["conversion"].sum()

    # CPA 최우수
    valid_cpa = campaign_base[
        campaign_base["conversion"] > 0
    ].copy()

    if len(valid_cpa) > 0:

        best_cpa_row = valid_cpa.loc[
            valid_cpa["CPA"].idxmin()
        ]

        best_cpa_campaign = best_cpa_row["campaign"]
        best_cpa = best_cpa_row["CPA"]
        best_cpa_conversion = best_cpa_row["conversion"]

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


    # 전환 최다
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

    st.markdown(
        f"""
        📈 **전환수 최다 캠페인:** `{best_conversion_campaign}` —
        전환 **{best_conversion:,.0f}건**,
        CPA **{best_conversion_cpa:,.0f}원**
        (**전체 전환의 {conversion_share:.1f}%**)
        """
    )


# ============================================================
# 21. 개별 캠페인 상세 코멘트
# ============================================================

st.markdown("### 🔎 캠페인별 상세 분석")


campaign_compare = (
    compare_df
    .groupby("campaign", as_index=False)
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
    suffixes=("_base", "_compare")
).fillna(0)


for _, row in campaign_detail.iterrows():

    campaign_name = row["campaign"]

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

    # 신규 캠페인
    if conversion_compare == 0 and conversion_base > 0:

        comment = (
            f"**{campaign_name}**은 비교 기간에는 전환이 없었으나 "
            f"기준 기간에 **{conversion_base:,.0f}건**의 전환을 만들었습니다. "
            f"광고비는 **{spend_base:,.0f}원**, "
            f"CPA는 **{cpa_base:,.0f}원**으로 확인됩니다. "
            f"신규 전환이 발생한 만큼 향후에도 동일한 효율이 유지되는지 "
            f"추가 기간을 통해 확인할 필요가 있습니다."
        )

    else:

        conversion_part = (
            f"전환수는 **{conversion_base:,.0f}건**으로 "
            f"비교 기간 대비 **{abs(conversion_rate):.1f}% "
            f"{'증가' if conversion_rate > 0 else '감소'}**했습니다."
            if conversion_rate is not None
            else
            f"전환수는 **{conversion_base:,.0f}건**입니다."
        )

        cpa_part = (
            f"CPA는 **{cpa_base:,.0f}원**으로 "
            f"비교 기간 대비 **{abs(cpa_rate):.1f}% "
            f"{'개선' if cpa_rate < 0 else '상승'}**했습니다."
            if cpa_rate is not None
            else
            f"CPA는 **{cpa_base:,.0f}원**입니다."
        )

        cvr_part = (
            f"CVR은 **{cvr_base:.2f}%**로 "
            f"비교 기간 대비 **{abs(cvr_rate):.1f}% "
            f"{'상승' if cvr_rate > 0 else '하락'}**했습니다."
            if cvr_rate is not None
            else
            f"CVR은 **{cvr_base:.2f}%**입니다."
        )

        comment = (
            f"**{campaign_name}**은 기준 기간에 "
            f"광고비 **{spend_base:,.0f}원**을 집행해 "
            f"{conversion_part} "
            f"{cpa_part} "
            f"{cvr_part} "
            f"따라서 광고비 변화와 전환 변화가 함께 움직였는지 확인하고, "
            f"CPA와 CVR 중 어느 지표가 성과 변화를 주도했는지를 기준으로 "
            f"후속 최적화 방향을 판단하는 것이 좋습니다."
        )
    st.markdown(
        f'<div class="comment-box">{comment}</div>',
        unsafe_allow_html=True
    )


# ============================================================
# 22. 데이터 새로고침
# ============================================================

st.divider()

if st.button("🔄 데이터 새로고침"):

    st.cache_data.clear()

    st.rerun()
