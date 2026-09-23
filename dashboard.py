from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILES = (DATA_DIR / "data1.csv", DATA_DIR / "data2.csv")
COLUMNS = {"외내", "전출항지", "차항지", "입항일시", "출항일시", "총톤수"}
COLORS = [
    "coral", "gold", "seagreen", "skyblue", "mediumpurple",
    "tomato", "turquoise", "deeppink", "slateblue", "pink",
]


@st.cache_data(show_spinner="CSV 데이터를 읽는 중입니다…")
def load_data(file_signatures: tuple[tuple[str, int, int], ...]) -> pd.DataFrame:
    frames = [
        pd.read_csv(
            path,
            encoding="utf-8-sig",
            usecols=lambda name: name.strip() in COLUMNS,
            low_memory=False,
        )
        for path, _, _ in file_signatures
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
    fig, ax = plt.subplots(figsize=(9, 5.5))
    if values.empty:
        ax.text(0.5, 0.5, "표시할 유효 데이터가 없습니다", ha="center", va="center", transform=ax.transAxes)
        ax.set_xlim(0, 1)
    else:
        colors = [COLORS[i % len(COLORS)] for i in range(len(values))]
        bars = ax.barh(values.index, values.to_numpy(), color=colors)
        label = "%.1f%%" if percent else "%.1f"
        ax.bar_label(bars, fmt=label, padding=4, fontsize=9)
        ax.set_xlim(0, max(values.max() * 1.2, 1))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def scatter_chart(summary: pd.DataFrame, max_hours: int):
    points = summary[["총톤수 비율 (%)", "평균 체류시간 (시간)"]].dropna()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, (port, row) in enumerate(points.iterrows()):
        x = row["총톤수 비율 (%)"]
        y = row["평균 체류시간 (시간)"]
        ax.scatter(x, y, color=COLORS[i % len(COLORS)], s=100)
        ax.annotate(port, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=9)
    ax.set_xlabel("선정된 전출항지의 총톤수 비율 (%)")
    ax.set_ylabel(f"평균 체류시간 (시간, {max_hours}시간 이하)")
    ax.set_title("총톤수 비율과 평균 체류시간")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def main() -> None:
    st.set_page_config(page_title="전출항지 분석 대시보드", layout="wide")
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    st.title("전출항지 분석 대시보드")
    st.caption("data1.csv + data2.csv · 외항 선박 기준")

    missing = [path.name for path in DATA_FILES if not path.is_file()]
    if missing:
        st.error(f"데이터 파일을 찾을 수 없습니다: {', '.join(missing)}")
        st.stop()
    signatures = tuple((str(path), path.stat().st_size, path.stat().st_mtime_ns) for path in DATA_FILES)
    data = load_data(signatures)
    if data.empty:
        st.warning("외항 데이터가 없습니다.")
        st.stop()

    with st.sidebar:
        st.header("분석 설정")
        top_n = st.slider("전출항지 상위 개수", min_value=3, max_value=20, value=10)
        max_hours = st.slider("체류시간 상한 (시간)", min_value=1, max_value=168, value=48)
        st.caption("체류시간은 0시간 이상, 설정한 상한 이하인 기록만 평균에 사용합니다.")

    summary = summarize(data, top_n, max_hours)
    valid_count = int(summary["유효 체류시간 건수"].sum())
    total_tonnage = summary["총톤수 합계"].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("외항 기록", f"{len(data):,}건")
    m2.metric("분석 전출항지", f"{len(summary)}개")
    m3.metric("유효 체류시간 기록", f"{valid_count:,}건")
    m4.metric("상위 전출항지 총톤수 합계", f"{total_tonnage:,.0f}")

    left, right = st.columns(2)
    with left:
        fig = bar_chart(summary["입출항 건수"], "전출항지 빈도", "건수")
        st.pyplot(fig)
        plt.close(fig)
    with right:
        fig = bar_chart(
            summary["평균 체류시간 (시간)"],
            f"평균 체류시간 ({max_hours}시간 이하)",
            "시간",
        )
        st.pyplot(fig)
        plt.close(fig)

    left, right = st.columns(2)
    with left:
        fig = bar_chart(
            summary["총톤수 비율 (%)"],
            "전출항지별 총톤수 비율",
            "상위 전출항지 총톤수 합계 대비 (%)",
            percent=True,
        )
        st.pyplot(fig)
        plt.close(fig)
    with right:
        fig = scatter_chart(summary, max_hours)
        st.pyplot(fig)
        plt.close(fig)

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
    st.download_button(
        "요약 CSV 다운로드",
        summary.to_csv(encoding="utf-8-sig").encode("utf-8-sig"),
        file_name="port_summary.csv",
        mime="text/csv",
    )

    with st.expander("분석 기준과 해석"):
        st.write(
            "전출항지 순위는 외항 기록의 출현 건수로 정합니다. 체류시간은 출항일시에서 "
            "입항일시를 뺀 값이며, 날짜 오류·음수·설정 상한 초과 기록을 평균에서 제외합니다. "
            "총톤수 합계와 비율은 선정된 전출항지의 모든 외항 기록으로 계산합니다. "
            "총톤수는 선박의 크기를 나타내며 실제 화물량은 아닙니다. "
            "전출항지는 항만명과 지역명 등이 섞여 있어 국가별 통계로 해석하지 않습니다."
        )


if __name__ == "__main__":
    main()
