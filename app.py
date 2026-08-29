import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import StringIO
import requests
from datetime import timedelta

# ============================================================
# 1. 기본 설정
# ============================================================
st.set_page_config(
    page_title="Performance Marketing Dashboard",
    page_icon="📊",
    layout="wide",
)

SHEET_ID = "1M_NGYvpXgY721bV-B0dgXOj5LmITfKoVTIoIJgmv6gk"
GID = "519342112"

SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    f"?format=csv&gid={GID}"
)

# ============================================================
# 2. 데이터 로드
# ============================================================
@st.cache_data(ttl=300)
def load_data():
    r = requests.get(SHEET_URL, timeout=30)
    r.raise_for_status()

    # utf-8-sig 우선, 실패 시 cp949
    try:
        text = r.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = r.content.decode("cp949", errors="replace")

    df = pd.read_csv(StringIO(text))

    # 컬럼명 정리
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
        .str.lower()
    )

    # 실제 데이터 컬럼명 기준
    rename_map = {}
    candidates = {
        "date": ["date"],
        "media": ["media"],
        "campaign": ["campaign"],
        "impress": ["impress"],
        "click": ["click"],
        "spend": ["spend"],
        "conversion": ["conversion", "db"],
    }

    for target, names in candidates.items():
        for name in names:
            if name in df.columns:
                rename_map[name] = target
                break

    df = df.rename(columns=rename_map)

    required = [
        "date", "media", "campaign",
        "impress", "click", "spend", "conversion"
    ]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"필수 컬럼을 찾지 못했습니다: {missing}\n"
            f"현재 컬럼: {list(df.columns)}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for c in ["impress", "click", "spend", "conversion"]:
        df[c] = (
            df[c].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("-", "0", regex=False)
            .str.strip()
        )
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # 문자열 깨짐/공백 최소화
    for c in ["media", "campaign"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    df = df.dropna(subset=["date"]).copy()

    # 빈 매체/캠페인 제외
    df = df[df["media"] != ""]
    df["campaign"] = df["campaign"].replace("", "미지정")

    return df


try:
    df = load_data()
except Exception as e:
    st.error("Google Sheets 데이터를 불러오지 못했습니다.")
    st.exception(e)
    st.stop()

# ============================================================
# 3. 유틸
# ============================================================
def safe_cpa(spend, conversion):
    if conversion and conversion > 0:
        return spend / conversion
    return np.nan


def safe_cvr(click, conversion):
    if click and click > 0:
        return conversion / click * 100
    return np.nan


def pct_change(current, previous):
    if pd.isna(previous) or previous == 0:
        return np.nan
    return (current - previous) / previous * 100


def fmt_num(x):
    if pd.isna(x):
        return "-"
    return f"{x:,.0f}"


def fmt_won(x):
    if pd.isna(x):
        return "-"
    return f"{x:,.0f}원"


def fmt_pct(x):
    if pd.isna(x):
        return "-"
    return f"{x:+.1f}%"


def arrow_pct(x, reverse=False):
    """
    기본:
    + 변화 = 빨간 ▲
    - 변화 = 파란 ▼

    reverse=True:
    CPA처럼 감소가 좋은 지표를 판단할 때도
    표시 자체는 사용자가 요청한 +/− 색상 규칙을 유지.
    """
    if pd.isna(x):
        return "-"
    if x > 0:
        return f'<span class="up">▲ +{x:.1f}%</span>'
    if x < 0:
        return f'<span class="down">▼ {x:.1f}%</span>'
    return "0.0%"


def aggregate_period(data, start_date, end_date):
    d = data[
        (data["date"].dt.normalize() >= pd.Timestamp(start_date))
        & (data["date"].dt.normalize() <= pd.Timestamp(end_date))
    ].copy()

    if d.empty:
        return pd.DataFrame(
            columns=[
                "media", "impress", "click", "spend",
                "conversion", "CPA", "CVR"
            ]
        )

    g = (
        d.groupby("media", dropna=False)[
            ["impress", "click", "spend", "conversion"]
        ]
        .sum()
        .reset_index()
    )

    g["CPA"] = g.apply(
        lambda r: safe_cpa(r["spend"], r["conversion"]), axis=1
    )
    g["CVR"] = g.apply(
        lambda r: safe_cvr(r["click"], r["conversion"]), axis=1
    )
    return g


def get_comparison_dates(base_date, mode):
    """
    동일 진행일수 비교.

    기준일이 8/26이면:
    전일: 8/26 1일 vs 8/25 1일
    전주: 8/20~8/26 7일 vs 8/13~8/19 7일
    전월: 8/1~8/26 26일 vs 7/1~7/26 26일

    단, 데이터에 존재하는 날짜 범위를 고려해
    실제 기준기간의 시작일을 계산한다.
    """
    base = pd.Timestamp(base_date).normalize()

    if mode == "전일":
        current_start = base
        current_end = base
        previous_start = base - timedelta(days=1)
        previous_end = base - timedelta(days=1)

    elif mode == "전주":
        current_start = base - timedelta(days=6)
        current_end = base
        previous_start = current_start - timedelta(days=7)
        previous_end = current_end - timedelta(days=7)

    elif mode == "전월":
        current_start = base.replace(day=1)
        current_end = base
        previous_end = current_end - pd.DateOffset(months=1)
        previous_start = previous_end.replace(day=1)

    else:
        raise ValueError("잘못된 비교기간입니다.")

    return (
        current_start.normalize(),
        current_end.normalize(),
        pd.Timestamp(previous_start).normalize(),
        pd.Timestamp(previous_end).normalize(),
    )


def build_comparison(data, base_date, mode, selected_media, selected_campaigns):
    current_start, current_end, previous_start, previous_end = \
        get_comparison_dates(base_date, mode)

    work = data.copy()

    if selected_media:
        work = work[work["media"].isin(selected_media)]

    if selected_campaigns:
        work = work[work["campaign"].isin(selected_campaigns)]

    current = aggregate_period(work, current_start, current_end)
    previous = aggregate_period(work, previous_start, previous_end)

    current = current.rename(
        columns={
            "impress": "기준 노출",
            "click": "기준 클릭",
            "spend": "기준 광고비",
            "conversion": "기준 전환수",
            "CPA": "기준 CPA",
            "CVR": "기준 CVR",
        }
    )

    previous = previous.rename(
        columns={
            "impress": "비교 노출",
            "click": "비교 클릭",
            "spend": "비교 광고비",
            "conversion": "비교 전환수",
            "CPA": "비교 CPA",
            "CVR": "비교 CVR",
        }
    )

    result = pd.merge(current, previous, on="media", how="outer")

    numeric_cols = [
        "기준 노출", "기준 클릭", "기준 광고비", "기준 전환수",
        "기준 CPA", "기준 CVR",
        "비교 노출", "비교 클릭", "비교 광고비", "비교 전환수",
        "비교 CPA", "비교 CVR",
    ]

    for c in numeric_cols:
        if c in result.columns:
            result[c] = pd.to_numeric(result[c], errors="coerce").fillna(0)

    result["광고비 변화"] = result.apply(
        lambda r: pct_change(r["기준 광고비"], r["비교 광고비"]), axis=1
    )
    result["전환수 변화"] = result.apply(
        lambda r: pct_change(r["기준 전환수"], r["비교 전환수"]), axis=1
    )
    result["CPA 변화"] = result.apply(
        lambda r: pct_change(r["기준 CPA"], r["비교 CPA"]), axis=1
    )
    result["CVR 변화"] = result.apply(
        lambda r: pct_change(r["기준 CVR"], r["비교 CVR"]), axis=1
    )

    return result, (
        current_start, current_end,
        previous_start, previous_end
    )


# ============================================================
# 4. 자동 코멘트
# ============================================================
def media_comment(row):
    spend_chg = row["광고비 변화"]
    conv_chg = row["전환수 변화"]
    cpa_chg = row["CPA 변화"]
    cvr_chg = row["CVR 변화"]

    if pd.isna(conv_chg) and pd.isna(cpa_chg):
        return "데이터가 부족해 성과 판단이 어렵습니다."

    if (
        not pd.isna(conv_chg)
        and not pd.isna(cpa_chg)
        and conv_chg >= 10
        and cpa_chg <= -10
    ):
        return (
            "🟢 확대 후보 — 전환수가 증가하면서 CPA가 개선되었습니다. "
            "추가 예산 확대를 검토할 수 있습니다."
        )

    if (
        not pd.isna(spend_chg)
        and not pd.isna(conv_chg)
        and spend_chg >= 10
        and conv_chg < 0
        and not pd.isna(cpa_chg)
        and cpa_chg > 0
    ):
        return (
            "🚨 긴급 점검 — 광고비는 증가했지만 전환수는 감소하고 "
            "CPA는 상승했습니다. 캠페인·타겟·소재 점검이 필요합니다."
        )

    if (
        not pd.isna(conv_chg)
        and not pd.isna(cpa_chg)
        and conv_chg < -10
        and cpa_chg > 10
    ):
        return (
            "🔴 개선 필요 — 전환수가 감소하고 CPA가 상승했습니다. "
            "저성과 캠페인 또는 소재를 우선 확인하세요."
        )

    if (
        not pd.isna(conv_chg)
        and conv_chg >= 0
        and not pd.isna(cpa_chg)
        and cpa_chg < 0
    ):
        return (
            "🟢 효율 개선 — 전환 규모를 유지/확대하면서 CPA가 개선되었습니다."
        )

    if (
        not pd.isna(cpa_chg)
        and cpa_chg > 10
    ):
        return (
            "🟡 효율 주의 — CPA가 상승했습니다. "
            "예산 확대보다 원인별 세부 분석을 권장합니다."
        )

    return (
        "🟡 관찰 — 주요 지표의 방향성이 혼재되어 있습니다. "
        "캠페인·상품별 세부 성과를 확인하세요."
    )


def overall_comment(result):
    if result.empty:
        return "선택한 조건에 해당하는 데이터가 없습니다."

    r = result.copy()

    # CPA 개선은 낮을수록 좋으므로 가장 큰 음수
    valid_cpa = r.dropna(subset=["CPA 변화"])
    valid_conv = r.dropna(subset=["전환수 변화"])

    messages = []

    if not valid_cpa.empty:
        best_cpa = valid_cpa.loc[valid_cpa["CPA 변화"].idxmin()]
        messages.append(
            f"**CPA 개선:** {best_cpa['media']} "
            f"({fmt_pct(best_cpa['CPA 변화'])})"
        )

    if not valid_conv.empty:
        best_conv = valid_conv.loc[valid_conv["전환수 변화"].idxmax()]
        messages.append(
            f"**전환수 증가:** {best_conv['media']} "
            f"({fmt_pct(best_conv['전환수 변화'])})"
        )

    danger = r[
        (r["CPA 변화"].notna()) & (r["CPA 변화"] > 10)
        & (r["전환수 변화"].notna()) & (r["전환수 변화"] < -10)
    ]

    if not danger.empty:
        names = ", ".join(danger["media"].astype(str).tolist())
        messages.append(f"**개선 우선:** {names}")

    if not messages:
        return "현재 선택 조건에서 뚜렷한 우수/저성과 매체가 확인되지 않습니다."

    return " · ".join(messages)


# ============================================================
# 5. CSS
# ============================================================
st.markdown(
    """
    <style>
    .up {
        color: #d93025;
        font-weight: 700;
    }

    .down {
        color: #1967d2;
        font-weight: 700;
    }

    .metric-card {
        padding: 14px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        text-align: center;
    }

    .metric-title {
        font-size: 13px;
        color: #6b7280;
    }

    .metric-value {
        font-size: 23px;
        font-weight: 700;
    }

    .comment-box {
        padding: 15px 18px;
        border-radius: 10px;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        line-height: 1.7;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 6. 제목
# ============================================================
st.title("📊 Performance Marketing Dashboard")
st.caption(
    f"Google Sheets RAW 데이터 · "
    f"{df['date'].min().date()} ~ {df['date'].max().date()} · "
    f"{len(df):,} rows"
)

# ============================================================
# 7. 필터
# ============================================================
min_date = df["date"].min().date()
max_date = df["date"].max().date()

col1, col2, col3 = st.columns([1.2, 1.5, 2.2])

with col1:
    base_date = st.date_input(
        "기준일",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

with col2:
    mode = st.radio(
        "비교기간",
        ["전일", "전주", "전월"],
        horizontal=True,
    )

with col3:
    media_options = sorted(df["media"].dropna().unique().tolist())
    selected_media = st.multiselect(
        "매체 · 다중선택",
        options=media_options,
        default=media_options,
        placeholder="전체 매체",
    )

campaign_options = sorted(df["campaign"].dropna().unique().tolist())
selected_campaigns = st.multiselect(
    "캠페인 · 다중선택",
    options=campaign_options,
    default=campaign_options,
    placeholder="전체 캠페인",
)

# ============================================================
# 8. 비교 계산
# ============================================================
result, dates = build_comparison(
    df,
    base_date,
    mode,
    selected_media,
    selected_campaigns,
)

current_start, current_end, previous_start, previous_end = dates

st.info(
    f"**기준기간:** {current_start:%Y-%m-%d} ~ {current_end:%Y-%m-%d}  "
    f"  ↔  **비교기간:** {previous_start:%Y-%m-%d} ~ {previous_end:%Y-%m-%d}"
)

# ============================================================
# 9. KPI
# ============================================================
if not result.empty:
    total_spend = result["기준 광고비"].sum()
    total_conv = result["기준 전환수"].sum()
    total_prev_spend = result["비교 광고비"].sum()
    total_prev_conv = result["비교 전환수"].sum()

    total_cpa = safe_cpa(total_spend, total_conv)
    prev_cpa = safe_cpa(total_prev_spend, total_prev_conv)

    st.markdown("### 📌 기준기간 전체 성과")

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "광고비",
        fmt_won(total_spend),
        fmt_pct(pct_change(total_spend, total_prev_spend)),
    )

    k2.metric(
        "전환수",
        fmt_num(total_conv),
        fmt_pct(pct_change(total_conv, total_prev_conv)),
    )

    k3.metric(
        "CPA",
        fmt_won(total_cpa),
        fmt_pct(pct_change(total_cpa, prev_cpa)),
    )

    total_click = df[
        (df["date"].dt.normalize() >= pd.Timestamp(current_start))
        & (df["date"].dt.normalize() <= pd.Timestamp(current_end))
    ]["click"].sum()

    prev_click = df[
        (df["date"].dt.normalize() >= pd.Timestamp(previous_start))
        & (df["date"].dt.normalize() <= pd.Timestamp(previous_end))
    ]["click"].sum()

    current_cvr = safe_cvr(total_click, total_conv)
    previous_cvr = safe_cvr(prev_click, total_prev_conv)

    k4.metric(
        "CVR",
        "-" if pd.isna(current_cvr) else f"{current_cvr:.2f}%",
        fmt_pct(pct_change(current_cvr, previous_cvr)),
    )

# ============================================================
# 10. 차트
# ============================================================
st.markdown("### 📈 성과 비교")

if not result.empty:
    chart_df = result.copy()

    # Plotly JSON 직렬화 문제 방지
    for c in [
        "기준 광고비", "비교 광고비",
        "기준 전환수", "비교 전환수",
        "기준 CPA", "비교 CPA",
    ]:
        chart_df[c] = pd.to_numeric(chart_df[c], errors="coerce").fillna(0)

    chart_df = chart_df.sort_values(
        "기준 전환수", ascending=False
    )

    c1, c2 = st.columns(2)

    with c1:
        fig1 = go.Figure()

        fig1.add_trace(
            go.Bar(
                x=chart_df["media"],
                y=chart_df["기준 CPA"],
                name="CPA",
                hovertemplate="%{x}<br>CPA: %{y:,.0f}원<extra></extra>",
            )
        )

        fig1.add_trace(
            go.Scatter(
                x=chart_df["media"],
                y=chart_df["기준 전환수"],
                name="전환수",
                mode="lines+markers",
                yaxis="y2",
                hovertemplate="%{x}<br>전환수: %{y:,.0f}건<extra></extra>",
            )
        )

        fig1.update_layout(
            title="CPA + 전환수",
            height=300,
            margin=dict(l=20, r=20, t=50, b=20),
            yaxis=dict(title="CPA"),
            yaxis2=dict(
                title="전환수",
                overlaying="y",
                side="right",
            ),
            legend=dict(orientation="h"),
        )

        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = go.Figure()

        fig2.add_trace(
            go.Bar(
                x=chart_df["media"],
                y=chart_df["기준 광고비"],
                name="광고비",
                hovertemplate="%{x}<br>광고비: %{y:,.0f}원<extra></extra>",
            )
        )

        fig2.add_trace(
            go.Scatter(
                x=chart_df["media"],
                y=chart_df["기준 전환수"],
                name="전환수",
                mode="lines+markers",
                yaxis="y2",
                hovertemplate="%{x}<br>전환수: %{y:,.0f}건<extra></extra>",
            )
        )

        fig2.update_layout(
            title="광고비 + 전환수",
            height=300,
            margin=dict(l=20, r=20, t=50, b=20),
            yaxis=dict(title="광고비"),
            yaxis2=dict(
                title="전환수",
                overlaying="y",
                side="right",
            ),
            legend=dict(orientation="h"),
        )

        st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# 11. 상세 비교표
# ============================================================
st.markdown("### 📋 상세 성과 비교")

if result.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    # 사용자가 요청한 형태:
    # 매체 = 가로
    # 지표 = 세로
    metrics = [
        ("기준 광고비", "광고비"),
        ("비교 광고비", "비교 광고비"),
        ("광고비 변화", "광고비 변화"),
        ("기준 전환수", "전환수"),
        ("비교 전환수", "비교 전환수"),
        ("전환수 변화", "전환수 변화"),
        ("기준 CPA", "CPA"),
        ("비교 CPA", "비교 CPA"),
        ("CPA 변화", "CPA 변화"),
        ("기준 CVR", "CVR"),
        ("비교 CVR", "비교 CVR"),
        ("CVR 변화", "CVR 변화"),
    ]

    table_rows = []

    for source_col, label in metrics:
        row = {"지표": label}

        for _, r in result.iterrows():
            media = r["media"]

            if source_col in [
                "기준 광고비", "비교 광고비"
            ]:
                row[media] = fmt_won(r[source_col])

            elif source_col in [
                "기준 전환수", "비교 전환수"
            ]:
                row[media] = fmt_num(r[source_col])

            elif source_col in [
                "기준 CPA", "비교 CPA"
            ]:
                row[media] = fmt_won(r[source_col])

            elif source_col in [
                "기준 CVR", "비교 CVR"
            ]:
                row[media] = (
                    "-"
                    if pd.isna(r[source_col])
                    else f"{r[source_col]:.2f}%"
                )

            else:
                row[media] = arrow_pct(r[source_col])

        table_rows.append(row)

    display_df = pd.DataFrame(table_rows)

    # HTML로 빨강/파랑 화살표 표시
    html = display_df.to_html(
        index=False,
        escape=False,
        classes="comparison-table",
    )

    st.markdown(
        """
        <style>
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .comparison-table th {
            background: #f3f4f6;
            font-weight: 700;
            padding: 10px;
            border-bottom: 1px solid #d1d5db;
            text-align: center;
        }

        .comparison-table td {
            padding: 9px 10px;
            border-bottom: 1px solid #e5e7eb;
            text-align: right;
            white-space: nowrap;
        }

        .comparison-table td:first-child {
            text-align: left;
            font-weight: 700;
            background: #fafafa;
            position: sticky;
            left: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# 12. 자동 성과 코멘트
# ============================================================
st.markdown("### 🎯 성과 분석 코멘트")

if not result.empty:
    comment_result = result.copy()
    comment_result["코멘트"] = comment_result.apply(
        media_comment, axis=1
    )

    for _, r in comment_result.iterrows():
        st.markdown(
            f"""
            <div class="comment-box">
                <b>{r['media']}</b><br>
                {r['코멘트']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### 📌 종합 판단")
    st.markdown(
        f'<div class="comment-box">{overall_comment(result)}</div>',
        unsafe_allow_html=True,
    )

# ============================================================
# 13. 캠페인 드릴다운
# ============================================================
st.markdown("### 🔎 캠페인 드릴다운")

if selected_media:
    drill_media = selected_media
else:
    drill_media = media_options

drill_df = df[df["media"].isin(drill_media)].copy()

if selected_campaigns:
    drill_df = drill_df[drill_df["campaign"].isin(selected_campaigns)]

drill_current = drill_df[
    (drill_df["date"].dt.normalize() >= pd.Timestamp(current_start))
    & (drill_df["date"].dt.normalize() <= pd.Timestamp(current_end))
]

drill_previous = drill_df[
    (drill_df["date"].dt.normalize() >= pd.Timestamp(previous_start))
    & (drill_df["date"].dt.normalize() <= pd.Timestamp(previous_end))
]


def campaign_aggregate(d):
    if d.empty:
        return pd.DataFrame(
            columns=["campaign", "spend", "conversion", "click", "CPA", "CVR"]
        )

    x = (
        d.groupby("campaign")[
            ["spend", "conversion", "click"]
        ].sum().reset_index()
    )

    x["CPA"] = x.apply(
        lambda r: safe_cpa(r["spend"], r["conversion"]), axis=1
    )
    x["CVR"] = x.apply(
        lambda r: safe_cvr(r["click"], r["conversion"]), axis=1
    )
    return x


cc = campaign_aggregate(drill_current).rename(
    columns={
        "spend": "기준 광고비",
        "conversion": "기준 전환수",
        "CPA": "기준 CPA",
        "CVR": "기준 CVR",
    }
)

pp = campaign_aggregate(drill_previous).rename(
    columns={
        "spend": "비교 광고비",
        "conversion": "비교 전환수",
        "CPA": "비교 CPA",
        "CVR": "비교 CVR",
    }
)

if not cc.empty or not pp.empty:
    drill = pd.merge(cc, pp, on="campaign", how="outer")

    for c in [
        "기준 광고비", "기준 전환수", "기준 CPA", "기준 CVR",
        "비교 광고비", "비교 전환수", "비교 CPA", "비교 CVR",
    ]:
        if c in drill.columns:
            drill[c] = pd.to_numeric(drill[c], errors="coerce")

    drill["광고비 변화"] = drill.apply(
        lambda r: pct_change(r["기준 광고비"], r["비교 광고비"]), axis=1
    )
    drill["전환수 변화"] = drill.apply(
        lambda r: pct_change(r["기준 전환수"], r["비교 전환수"]), axis=1
    )
    drill["CPA 변화"] = drill.apply(
        lambda r: pct_change(r["기준 CPA"], r["비교 CPA"]), axis=1
    )
    drill["CVR 변화"] = drill.apply(
        lambda r: pct_change(r["기준 CVR"], r["비교 CVR"]), axis=1
    )

    drill = drill.sort_values(
        "기준 전환수", ascending=False, na_position="last"
    )

    # ========================================================
    # 캠페인을 가로 / 지표를 세로로 배치
    # ========================================================
    metrics = [
        ("기준 광고비", "기준 광고비", "won"),
        ("비교 광고비", "비교 광고비", "won"),
        ("광고비 변화", "광고비 변화", "change"),
        ("기준 전환수", "기준 전환수", "num"),
        ("비교 전환수", "비교 전환수", "num"),
        ("전환수 변화", "전환수 변화", "change"),
        ("기준 CPA", "기준 CPA", "won"),
        ("비교 CPA", "비교 CPA", "won"),
        ("CPA 변화", "CPA 변화", "change"),
        ("기준 CVR", "기준 CVR", "pct"),
        ("비교 CVR", "비교 CVR", "pct"),
        ("CVR 변화", "CVR 변화", "change"),
    ]

    table_rows = []

    for source_col, label, value_type in metrics:
        row = {"지표": label}

        for _, r in drill.iterrows():
            campaign = str(r["campaign"])
            value = r.get(source_col, np.nan)

            if value_type == "won":
                row[campaign] = fmt_won(value)
            elif value_type == "num":
                row[campaign] = fmt_num(value)
            elif value_type == "pct":
                row[campaign] = (
                    "-" if pd.isna(value) else f"{value:.2f}%"
                )
            else:
                row[campaign] = arrow_pct(value)

        table_rows.append(row)

    drill_display = pd.DataFrame(table_rows)

    # HTML 표를 사용해 변화율 색상과 화살표 유지
    html = drill_display.to_html(
        index=False,
        escape=False,
        classes="comparison-table campaign-table",
    )

    st.markdown(
        """
        <style>
        .campaign-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            min-width: max-content;
        }

        .campaign-table th {
            background: #f3f4f6;
            font-weight: 700;
            padding: 9px 10px;
            border-bottom: 1px solid #d1d5db;
            text-align: center;
            white-space: nowrap;
        }

        .campaign-table td {
            padding: 8px 10px;
            border-bottom: 1px solid #e5e7eb;
            text-align: right;
            white-space: nowrap;
        }

        .campaign-table th:first-child,
        .campaign-table td:first-child {
            text-align: left;
            font-weight: 700;
            background: #fafafa;
            position: sticky;
            left: 0;
            z-index: 2;
        }

        .campaign-table th:first-child {
            z-index: 3;
        }

        .campaign-table .up {
            color: #dc2626;
            font-weight: 700;
        }

        .campaign-table .down {
            color: #2563eb;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 캠페인이 많아도 가로 스크롤로 확인할 수 있도록 컨테이너 구성
    st.markdown(
        f"""
        <div style="overflow-x:auto; width:100%;">
            {html}
        </div>
        """,
        unsafe_allow_html=True,
    )

else:
    st.info("선택된 조건에서 캠페인 데이터가 없습니다.")

# ============================================================
# 14. 새로고침
# ============================================================
st.divider()

if st.button("🔄 Google Sheets 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.caption(
    "데이터는 Google Sheets에서 최대 5분마다 자동 갱신됩니다. "
    "RAW 데이터가 변경되면 새로고침 버튼으로 즉시 반영할 수 있습니다."
)
