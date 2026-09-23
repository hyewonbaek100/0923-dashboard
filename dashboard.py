from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILES = (DATA_DIR / "data1.csv", DATA_DIR / "data2.csv")
MAX_DWELL_HOURS = 48
COLUMNS = {"외내", "전출항지", "차항지", "입항일시", "출항일시", "총톤수"}
COLORS = [
    "coral", "gold", "seagreen", "skyblue", "mediumpurple",
    "tomato", "turquoise", "deeppink", "slateblue", "pink",
]


def load_data() -> pd.DataFrame:
    frames = [
        pd.read_csv(
            path,
            encoding="utf-8-sig",
            usecols=lambda name: name.strip() in COLUMNS,
            low_memory=False,
        )
        for path in DATA_FILES
    ]
    data = pd.concat(frames, ignore_index=True)
    data.columns = data.columns.str.strip()
    for column in ("외내", "전출항지", "차항지"):
        data[column] = data[column].astype("string").str.strip()
        data[column] = data[column].replace("", pd.NA)
    data["총톤수"] = pd.to_numeric(
        data["총톤수"].astype("string").str.replace(",", "", regex=False),
        errors="coerce",
    )
    data["입항일시"] = pd.to_datetime(data["입항일시"], errors="coerce")
    data["출항일시"] = pd.to_datetime(data["출항일시"], errors="coerce")
    data["체류시간_시간"] = (
        data["출항일시"] - data["입항일시"]
    ).dt.total_seconds() / 3600
    return data.loc[data["외내"] == "외항"].copy()


def summarize(data: pd.DataFrame, top_n: int, max_hours: int) -> pd.DataFrame:
    counts = data["전출항지"].value_counts().head(top_n)
    ports = counts.index
    selected = data.loc[data["전출항지"].isin(ports)]
    valid_time = selected.loc[selected["체류시간_시간"].between(0, max_hours)]

    tonnage = selected.groupby("전출항지")["총톤수"].sum(min_count=1).reindex(ports)
    tonnage_total = tonnage.sum()
    share = tonnage / tonnage_total * 100 if tonnage_total > 0 else tonnage * float("nan")

    return pd.DataFrame(
        {
            "입출항 건수": counts,
            "유효 체류시간 건수": valid_time.groupby("전출항지").size().reindex(ports, fill_value=0),
            "평균 체류시간 (시간)": valid_time.groupby("전출항지")["체류시간_시간"]
            .mean()
            .reindex(ports),
            "총톤수 합계": tonnage,
            "총톤수 비율 (%)": share,
        }
    ).rename_axis("전출항지")


def bar_chart(values: pd.Series, title: str, xlabel: str, *, percent: bool = False):
    values = values.dropna().sort_values()
    fig = go.Figure()
    if values.empty:
        fig.add_annotation(
            text="표시할 유효 데이터가 없습니다",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        )
    else:
        colors = [COLORS[i % len(COLORS)] for i in range(len(values))]
        value_format = ",.0f" if xlabel == "건수" else ".1f"
        suffix = "%" if percent else ("시간" if xlabel == "시간" else "")
        fig.add_trace(go.Bar(
            x=values.to_numpy(),
            y=values.index.tolist(),
            orientation="h",
            marker_color=colors,
            text=[f"{value:{value_format}}{suffix}" for value in values],
            textposition="outside",
            hovertemplate=f"<b>%{{y}}</b><br>{xlabel}: %{{x:{value_format}}}{suffix}<extra></extra>",
        ))
        fig.update_xaxes(range=[0, max(values.max() * 1.2, 1)])
    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        yaxis_title=None,
        height=max(440, len(values) * 32 + 140),
        margin=dict(l=20, r=60, t=60, b=50),
        showlegend=False,
    )
    return fig


def scatter_chart(summary: pd.DataFrame, max_hours: int):
    points = summary.dropna(subset=["총톤수 비율 (%)", "평균 체류시간 (시간)"])
    fig = go.Figure()
    for i, (port, row) in enumerate(points.iterrows()):
        x = row["총톤수 비율 (%)"]
        y = row["평균 체류시간 (시간)"]
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", name=port,
            text=[port], textposition="top center",
            marker=dict(color=COLORS[i % len(COLORS)], size=12),
            hovertemplate=(
                f"<b>{port}</b><br>"
                "총톤수 비율: %{x:.2f}%<br>"
                "평균 체류시간: %{y:.2f}시간<br>"
                f"입출항 건수: {int(row['입출항 건수']):,}건<br>"
                f"유효 체류시간 건수: {int(row['유효 체류시간 건수']):,}건"
                "<extra></extra>"
            ),
        ))
    if points.empty:
        fig.add_annotation(
            text="표시할 유효 데이터가 없습니다",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        )
    fig.update_layout(
        title="총톤수 비율과 평균 체류시간",
        xaxis_title="선정된 전출항지의 총톤수 비율 (%)",
        yaxis_title=f"평균 체류시간 (시간, {max_hours}시간 이하)",
        height=440,
        margin=dict(l=20, r=20, t=60, b=50),
        showlegend=False,
        hovermode="closest",
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="전출항지 분석 대시보드", layout="wide")

    st.title("전출항지별 분석 대시보드")
    st.caption('데이터 출처:해양수산부 portmis')

    st.link_button(
        "원본 데이터 사이트",
        "https://new.portmis.go.kr/portmis/websquare/websquare.jsp?w2xPath=/portmis/w2/main/index.xml&page=/portmis/w2/sp/vssl/vsch/UI-PM-SP-104-02.xml&menuId=1319&menuCd=M0182&menuNm=%EC%84%A0%EB%B0%95%EC%9E%85%EC%B6%9C%ED%95%AD%ED%98%84%ED%99%A9",
        type="primary",
    )

    missing = [path.name for path in DATA_FILES if not path.is_file()]
    if missing:
        st.error(f"데이터 파일을 찾을 수 없습니다: {', '.join(missing)}")
        st.stop()
    data = load_data()
    if data.empty:
        st.warning("외항 데이터가 없습니다.")
        st.stop()

    with st.sidebar:
        st.header("분석 설정")
        top_n = st.slider("전출항지 상위 개수", min_value=3, max_value=20, value=10)

    summary = summarize(data, top_n, MAX_DWELL_HOURS)
    valid_count = int(summary["유효 체류시간 건수"].sum())
    total_tonnage = summary["총톤수 합계"].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("외항 기록", f"{len(data):,}건")
    m2.metric("분석 전출항지", f"{len(summary)}개")
    m3.metric("유효 체류시간 기록", f"{valid_count:,}건")
    m4.metric("상위 전출항지 총톤수 합계", f"{total_tonnage:,.0f}")

    left, right = st.columns(2)
    with left:
        fig = bar_chart(summary["입출항 건수"], "전출항지 TOP10 항구", "건수")
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = bar_chart(
            summary["평균 체류시간 (시간)"],
            f"평균 체류시간 ({MAX_DWELL_HOURS}시간 이하) TOP10 항구",
            "시간",
        )
        st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        fig = bar_chart(
            summary["총톤수 비율 (%)"],
            "전출항지별 총톤수 비율",
            "상위 전출항지 총톤수 합계 대비 (%)",
            percent=True,
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = scatter_chart(summary, MAX_DWELL_HOURS)
        st.plotly_chart(fig, width="stretch")

    st.subheader("전출항지별 요약")
    st.dataframe(
        summary.style.format(
            {
                "입출항 건수": "{:,.0f}",
                "유효 체류시간 건수": "{:,.0f}",
                "평균 체류시간 (시간)": "{:,.2f}",
                "총톤수 합계": "{:,.0f}",
                "총톤수 비율 (%)": "{:.2f}%",
            },
            na_rep="—",
        ),
        width="stretch",
    )


    with st.expander("분석 기준과 해석"):
        st.write(
            "전출항지 순위는 외항 기록의 출현 건수로 정합니다. 체류시간은 출항일시에서 "
            "입항일시를 뺀 값이며, 날짜 오류·음수·설정 상한 초과 기록을 평균에서 제외합니다. "
            "총톤수는 선박의 크기를 나타내며 실제 화물량은 아닙니다. "
            "전출항지는 항만명과 지역명 등이 섞여 있어 국가별 통계로 해석하지 않습니다."
        )


    with st.expander("결론"):
        st.write(
        "부산항 데이터를 분석한 결과, 상하이·닝보·칭다오를 전출항지로 하는 화물 및 선박의 비중이 높게 나타났다."
        "동시에 해당 항로의 선박들은 부산항 입항부터 출항까지 평균 체류시간도 상대적으로 길게 나타났으며 총톤수도 높은 대형 선박 위주로 많은 화물이 들어오는 경향이 있다."
        "따라서 주요 중국 항로는 부산항 운영에서 물동량 측면의 중요도가 높으면서 체류시간 관리의 영향도 큰 구간으로 볼 수 있다."
        "다만 현재 분석만으로 전출항지가 부산항 체류시간 증가의 직접적인 원인이라고 판단할 수는 없으며, 실제화물량·접안 부두·시간대 등의 요인을 추가적으로 분석할 필요가 있다."
        "이에 따라 주요 항로의 평균 체류시간과 장시간 체류 비율을 핵심 KPI로 관리하고, 체류시간이 증가하는 조건을 파악하는 것을 운영 효율화 방향으로 제안한다."
    )


if __name__ == "__main__":
    main()
