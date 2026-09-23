# 전출항지 분석 대시보드

`dashboard.ipynb`의 분석을 Streamlit 화면으로 옮긴 `dashboard.py`입니다. 프로젝트의
`data/data1.csv`와 `data/data2.csv`를 읽습니다.

## 실행

프로젝트 폴더에서 다음 명령을 실행하세요.

```powershell
uv sync
uv run streamlit run dashboard.py
```

브라우저에 표시되는 로컬 주소(기본값 `http://localhost:8501`)로 접속합니다.

사이드바에서 전출항지 상위 개수와 평균 체류시간의 상한을 조절할 수 있습니다.
기본값은 전출항지 10개, 체류시간 48시간 이하입니다. 전출항지 순위는 외항 기록의
출현 건수로 정하고, 총톤수 비율의 분모는 선정된 전출항지의 총톤수 합계입니다.
총톤수는 선박 크기 지표이며 실제 화물량이 아닙니다.
