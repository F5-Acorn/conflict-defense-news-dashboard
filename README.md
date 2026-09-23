# 해외 언론보도 데이터 기반 주요 분쟁의 무기·방산기술 사용 동향 분석 대시보드

## 프로젝트 구조

```text
conflict-defense-news-dashboard/
├── README.md                    # 프로젝트 안내와 실행 방법
├── requirements.txt             # 필요한 Python 패키지
├── requirements-dev.txt         # 개발용 Ruff 버전
├── pyproject.toml               # Python 포맷·코드 검사 규칙
├── schema.dbml                  # 실제 데이터 연결용 테이블·관계·제약 명세
├── .editorconfig                # 편집기의 Python 들여쓰기·줄바꿈
├── app.py                       # 앱 설정, 상단 메뉴, 공통 필터 연결
├── config.py                    # 기본 기간, 분쟁 정보, 색상, 분류 수
├── .vscode/
│   ├── settings.json           # Python 저장 시 Ruff 포맷 적용
│   └── extensions.json         # 팀 공통 Ruff 확장 추천
├── .streamlit/
│   └── config.toml              # Streamlit 기본 테마
├── pages/
│   ├── 00_overview.py           # 분쟁 요약과 범주별 상세 명칭
│   ├── 01_overview_map.py       # 지도와 분쟁별 주요 범주
│   ├── 02_weapons_monthly.py    # 무기 월간 화면 호출
│   └── 03_technology_monthly.py # 기술 월간 화면 호출
├── data/
│   ├── reference_data.py        # ERD 기준 테이블의 가상 예시
│   ├── sample_data.py           # 가상 기사·판정 결과 생성과 화면용 집계
│   └── ucdp/
│       ├── README.md            # UCDP 파일별 한글 설명과 데이터 처리 흐름
│       ├── raw/                 # GED·Actor 원본 CSV와 추출 안내
│       ├── references/          # 국가코드 매핑과 GDELT FIPS 기준표
│       └── processed/           # 모든 가공 CSV·JSON을 하위 폴더 없이 보관
├── services/
│   └── analysis_service.py      # 조건별 필터링, 월별 집계, Top 3
├── ui/
│   ├── maps.py                  # 국가 경계 로딩과 Folium 지도 생성
│   ├── monthly_view.py          # 무기·기술 월간 화면의 공통 구성
│   ├── components.py            # 공통 필터, 범주 선택, 공통 표시 요소
│   └── charts.py                # 현재 디자인의 Plotly 차트
├── tests/
│   ├── test_app.py              # 최초 실행·페이지 이동·공통 필터 검사
│   └── test_sample_data.py      # ERD 제약·중복 제거·SQL 집계 대조 검사
├── utils/
│   └── state.py                 # 선택값 초기화·저장·초기화 버튼 처리
└── assets/
    ├── README.md                # 지도 데이터 출처와 가공 내역
    ├── style.css                # 화면 스타일
    └── world_countries.geojson  # 지도 경계 데이터
```

`app.py`가 공통 설정과 필터를 준비합니다. 보도 동향은 `pages/00_overview.py`에서 분쟁별 요약과 범주별 상세 명칭을 표시하고, 지도 화면은 `pages/01_overview_map.py`에서 구성합니다. 무기·기술 월간 페이지는 `ui/monthly_view.py`의 공통 화면 함수를 호출합니다. 데이터는 `data`, 집계 함수는 `services`, 페이지 이동 후에도 유지할 선택값과 선택 변경 콜백은 `utils/state.py`에서 관리합니다.

`schema.dbml`은 실제 데이터 연결을 위한 7개 테이블의 설계 명세입니다. 파일 전체를 dbdiagram.io에 붙여 넣으면 관계와 제약조건을 확인할 수 있습니다. `kind`는 `wp`·`tech`, `usage_code`는 `0`(사용 외 언급)·`1`(사용 확인)·`2`(확인 필요)로 정의하며, DB의 `kind`를 화면에 전달할 때는 `무기`·`기술`로 변환합니다. URL 중복 제거와 사전별 범주 유형 검증은 적재 단계에서 처리합니다. 현재 앱은 계속 샘플 데이터를 사용합니다.

## UCDP 데이터 추출

UCDP GED 26.1에서 **2016~2025년 국가 기반 분쟁(`type_of_violence=1`)**을
추출하는 코드는 `scripts/prepare_ucdp.py`에 있다. 원본 두 파일은
`data/ucdp/raw/`에 보관하며, 실행하면 필요한 20개 컬럼의 사건 CSV와
버전·필터·건수를 기록한 JSON을 `data/ucdp/processed/`에 생성한다.

```bash
conda activate streamlit
python scripts/prepare_ucdp.py
```

원본 위치, 실행 옵션과 검증 방법은 [UCDP 추출 안내](data/ucdp/raw/README.md)를
참고한다. 이 추출 결과는 이후 분쟁 목록과 GDELT 검색 조건을 만드는 입력이다.

2단계 추출 후 다음 명령으로 **분쟁 목록·행위자 검색어·사건별 검색 조건·국가별
월간 조회 계획**을 생성한다. 2단계 JSON에서 추출 CSV 경로와 해시를 확인하고
Actor 자료를 연결하며, 결과는 추출 CSV와 같은 `data/ucdp/processed/`에 저장한다.

```bash
python scripts/build_ucdp_search_inputs.py
```

기본값, 입력 경로 지정과 결과 파일 설명은 위 UCDP 추출 안내의 3단계를 참고한다.
전체 파일의 역할은 [UCDP 파일별 한글 설명](data/ucdp/README.md)에 정리했다.

## 대시보드 실행

현재 화면은 **ERD의 7개 테이블에 맞춘 가상 기사와 판정 결과**를 사용합니다. 분쟁·일 단위 기간·유형·범주 필터를 조작하면 원본에서 계산한 지표를 조회합니다. 기사 제목·URL·근거 문장은 모두 예시이며 실제 보도나 SIPRI/NATO 공식 사전이 아닙니다.

프로젝트 루트에서 실행합니다.

```bash
conda activate streamlit
python -m streamlit run app.py
```

새 Python 환경에서는 먼저 `python -m pip install -r requirements.txt`로 의존성을 설치합니다. 화면에서 사용하는 주요 패키지는 Streamlit, Pandas, Plotly, Folium입니다.

### 팀 개발 환경과 코드 규칙

개발 환경은 Python 3.13을 기준으로 합니다. Python 코드는 **Ruff 0.16.8**, **스페이스 2칸**, **작성한 따옴표 유지**, **줄 길이 기준 88자**, **LF 줄바꿈**으로 정리합니다. `pyproject.toml`에는 Python 버전, 들여쓰기, 따옴표 유지, 줄바꿈과 검사할 규칙만 설정합니다. 줄 길이 88자와 스페이스 들여쓰기 방식은 Ruff 기본값을 사용합니다.

파일 첫 줄의 `'''내용'''`은 Python에서 주석이 아닌 모듈 docstring입니다. Ruff는 `quote-style = "single"`이어도 docstring을 `"""내용"""`으로 정리하므로, 작은따옴표 세 개를 유지하려면 `"preserve"`가 필요합니다. 이 설정은 편집기 저장과 터미널에 공통으로 적용됩니다. 자세한 동작은 [Ruff의 quote-style 문서](https://docs.astral.sh/ruff/settings/#format_quote-style)를 참고하세요.

프로젝트 루트에서 개발 도구를 설치합니다. `requirements.txt`는 앱 실행 패키지, `requirements-dev.txt`는 개발용 Ruff만 관리합니다. 개발 환경에서는 두 파일을 함께 설치할 수 있습니다.

```bash
conda activate streamlit
python -m pip install -r requirements.txt -r requirements-dev.txt
```

- `pyproject.toml`이 팀 공통 규칙입니다. 기본 오류·미사용 변수 및 import를 검사하고 import 순서를 정리합니다. 프로젝트 내부 모듈은 Ruff가 자동으로 인식합니다.
- VS Code에서는 Ruff 확장을 설치하고 위 도구를 설치한 Python 환경을 선택합니다. 프로젝트 설정이 Python 기본 포맷터를 Ruff로 지정하며, 저장 시 포맷과 수정 가능한 오류·import 순서 정리를 실행합니다.
- 확장은 선택한 환경의 Ruff를 우선 사용하고 프로젝트 설정 파일을 우선 적용합니다. Ruff 버전은 `requirements-dev.txt`에서 관리합니다.
- `.editorconfig`를 지원하는 편집기는 Python 입력 시에도 2칸 들여쓰기를 사용합니다. 다른 편집기를 사용해도 아래 터미널 명령으로 동일하게 검사할 수 있습니다.

자동 정리와 수정 없는 검사는 다음 명령을 사용합니다.

```bash
# 자동 정리: 코드 오류와 import 순서를 먼저 수정한 뒤 포맷을 적용한다.
python -m ruff check --fix .
python -m ruff format .

# 검사만 실행: 원본 파일을 수정하지 않는다.
python -m ruff check .
python -m ruff format --check .
```

Ruff 버전을 올릴 때는 `requirements-dev.txt`를 변경하고 전체 검사를 실행합니다.

### 페이지 구성

| 파일                             | 화면                                 |
| -------------------------------- | ------------------------------------ |
| `pages/00_overview.py` | 분쟁별 요약과 주요 범주별 상세 명칭 |
| `pages/01_overview_map.py` | 지도와 분쟁별 주요 무기/기술 |
| `pages/02_weapons_monthly.py`    | 방산 무기 월간 분석                  |
| `pages/03_technology_monthly.py` | 방산 기술 월간 분석                  |

`app.py`에서 위 네 페이지를 상단 메뉴에 등록하고 공통 필터를 연결합니다. 첫 화면은 상세 목록이 있는 보도 동향이며, 무기·기술 월간 화면은 같은 `render_monthly()` 함수를 사용합니다.

Streamlit은 최초 실행 시 `pages` 폴더를 자동 탐색하며 숫자 접두사를 제외한 파일명으로 URL을 추론합니다. `00_overview.py`와 `01_overview.py`처럼 나머지 이름이 같으면 앱의 `st.navigation()` 설정이 실행되기 전에 충돌하므로, 지도 페이지는 `01_overview_map.py`로 구분합니다.

- 기본 조건: 분쟁 전체, 2026-03-01~2026-08-31, 유형 전체.
- 보도 동향의 지표 아래에는 분쟁별 요약과 통합 상세 목록을 1:2로 배치합니다. 상세 목록은 범주를 중복 제거하고 사전 명칭을 쉼표로 연결합니다. 지도 화면에서는 지도와 주요 무기·기술 영역을 2:1로 배치합니다. 오른쪽 카드는 러시아·우크라이나, 이란·이스라엘 순서로 세로 표시하며, 좁은 화면에서는 지도 아래로 이어집니다.
- 좌우로 배치된 두 영역의 테두리는 같은 높이를 유지합니다. 오른쪽 제목은 유형 선택에 따라 `분쟁별 주요 무기/기술`, `분쟁별 주요 무기`, `분쟁별 주요 기술`로 바뀝니다.
- 지도 초기 중심은 위도 41·경도 39, 줌은 3.4로 고정합니다. 여러 화면 크기에서 마커와 말풍선이 잘리지 않는지 직접 확인한 값이며, 선택한 분쟁에 따라 자동으로 범위를 계산하지 않습니다.
- 분쟁·기간은 페이지 이동 시 유지됩니다. 범주 선택은 무기·기술 페이지별로 유지되며 검색으로 숨겨져도 해제되지 않습니다.
- 월별 추이는 선택한 범주만 표시합니다. 최신 Top 3는 선택 기간 마지막 월의 보도 수로 선정하며 추이 범주 선택과 독립적입니다. 동률이면 이름 오름차순입니다.
- 시작일·종료일을 모두 포함합니다. 월 일부만 선택하면 그 기간만 집계하고 `부분 기간`으로 표시합니다.
- 초기화는 분쟁·기간·유형·범주 선택·범주 검색을 기본값으로 되돌립니다.
- 보도 건수는 실제 사용 횟수나 성능을 의미하지 않습니다.

### 샘플 값 수정 및 실제 데이터 교체

`data/reference_data.py`에서 기준 테이블을 정의하고, `data/sample_data.py`에서 고정된 난수 시드로 기사와 판정 결과를 생성합니다. `load_sample_tables()`는 다음 7개 Pandas DataFrame을 테이블명으로 조회할 수 있는 사전으로 반환합니다.

| 테이블 | 기본 샘플 행 수 | 내용 |
| --- | ---: | --- |
| `conflicts` | 2 | 분쟁 ID, 한국어 이름, 색상, 국기, 표시 순서 |
| `articles` | 5,708 | 기사 ID, 분쟁 ID, 발행일, 가상 URL, 제목 |
| `categories` | 13 | 무기(`wp`) 7개·기술(`tech`) 6개 범주와 한·영 이름 |
| `sipri_dictionary` | 15 | 무기 범주에 연결된 예시 명칭·유의어 |
| `nato_dictionary` | 12 | 기술 범주에 연결된 예시 명칭·유의어 |
| `usage_patterns` | 6 | 사용 표현의 원형·활용형. 다른 테이블과 FK로 연결하지 않음 |
| `result` | 9,849 | 기사 × 범주 복합키, 사용 여부 코드, 근거 문장 |

```python
from data.sample_data import load_sample_tables

tables = load_sample_tables()
print(tables['articles'].head())
print(tables['result'].head())
```

- 기사는 2026-03-01~2026-08-31에 걸쳐 생성하며, URL은 `https://example.invalid/` 아래의 가상 주소입니다.
- 한 기사에 여러 무기·기술 범주가 함께 등장할 수 있습니다. 같은 기사·범주의 결과는 한 행만 생성합니다.
- `usage_code`는 `0`(사용 외 언급), `1`(사용 확인), `2`(확인 필요)를 모두 포함합니다. 사용 확인 결과에는 근거 문장이 반드시 있습니다.
- 결과가 없는 기사 335건도 포함합니다. 이는 무기·기술 언급이 없는 수집 기사 예시이며 분석 기사 수에서 제외합니다.
- 사용 판정은 완료된 상태를 가정한 가상 값입니다. `usage_patterns`의 단어가 문장에 있다는 이유만으로 사용 보도로 판정하는 분석기는 구현하지 않습니다.
- 같은 기준 데이터·기간으로 다시 실행하면 같은 결과가 나옵니다. 캐시 입력에 기준 테이블과 기간을 전달하며, 호출자가 반환값을 수정해도 캐시 원본에는 영향을 주지 않습니다.

`services/analysis_service.py`의 `build_dashboard_data()`가 원본 테이블을 조인하여 집계합니다.

| 지표 | 집계 기준 |
| --- | --- |
| 분석 기사 수 | 선택한 유형의 `result`에 등장하는 고유 `article_id` 수. 코드 0·1·2 포함 |
| 사용 보도 수 | 선택한 유형에서 `usage_code=1`인 고유 `article_id` 수 |
| 전체 기사 수 | 무기·기술 기사 집합의 합집합. 유형별 숫자를 단순 합산하지 않음 |
| 범주별 추이·Top 3 | 사용이 확인된 기사만 범주별로 중복 제거. 한 기사가 여러 범주에 기여할 수 있음 |
| 샘플 분류 수 | `categories`의 범주 수. 사전의 명칭·유의어 수와 구분하며 기간·분쟁에 무관 |

기본 전체 기간의 분석 기사는 **5,373건**, 사용 보도는 **3,700건**, 샘플 범주는 **13개**입니다. 이 숫자는 별도로 입력한 합계가 아니라 원본 기사·판정 결과에서 계산됩니다. 보도가 없는 날짜·범주도 0으로 채워 월별 그래프에서 선택한 범주가 누락되지 않게 합니다.

| 파일 | 수정 대상 |
| --- | --- |
| `data/reference_data.py` | 분쟁·범주·명칭·사용 표현, 샘플 시작일과 종료일 |
| `data/sample_data.py` | 일별 기사 수, 기사별 범주 조합, 사용 코드 분포와 가상 근거 문장 |
| `services/analysis_service.py` | 원본 조인·중복 제거 집계, 기간 필터, 월별 추이와 순위 |
| `config.py` | 지도 대표 좌표, 지도 초기 위치와 배율, 차트 색상 |

분쟁 이름·색상·국기·표시 순서와 범주 목록·개수는 기준 테이블에서 읽습니다. 범주 기본 선택은 한국어 이름순 첫 3개입니다. 지도 대표 좌표는 ERD에 없으므로 `config.py`의 `CONFLICT_LOCATIONS`에서 별도로 관리합니다.

`load_dashboard_data()`의 화면용 반환 형식은 유지합니다.

- 기사 지표: `date`, `conflict`, `kind`(전체/무기/기술), `analysis_articles`, `usage_articles`.
- 범주별 사용 보도 수: `date`, `conflict`, `kind`(무기/기술), `category`, `count`.

실제 DB를 연결할 때는 `load_sample_tables()`의 기사·결과 공급부와 `load_reference_tables()`의 기준 정보 공급부를 함께 교체합니다. ERD 컬럼, PK/FK, 사용 코드와 근거 문장 제약을 지키면 같은 집계 함수를 사용할 수 있습니다. DB 연결과 뉴스 수집은 아직 구현하지 않았습니다.

### 코드 수정 위치

| 파일                           | 주요 함수와 역할                                                                                                                                                                             |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/analysis_service.py` | `filter_data()`는 기간·분쟁·유형 필터, `article_totals()`는 기사 지표 합계, `monthly_trend()`는 월별 합계, `ranked_categories()`·`latest_distribution()`는 Top 3와 분쟁별 분포를 계산합니다. |
| `utils/state.py`               | `init_session_state()`는 없는 선택값만 기본값으로 채우고, `remember_kind()`·`remember_category()`는 변경한 선택을 저장합니다. `reset_filters()`는 선택과 검색을 초기화합니다.                |
| `ui/components.py`             | `render_filters()`는 공통 필터, `render_category_picker()`는 검색 가능한 범주 목록, `conflict_card()`는 분쟁별 카드 HTML을 만듭니다.                                                         |
| `pages/00_overview.py` | 분쟁별 요약과 무기·기술별 상세 명칭 목록을 표시합니다. |
| `pages/01_overview_map.py` | 선택 조건에 맞게 집계하고 기사 지표, 왼쪽 지도, 오른쪽 분쟁별 카드를 직접 배치합니다.                                                                                                        |
| `ui/maps.py`                   | `build_conflict_map()`은 분쟁별 보도 수와 주요 범주를 받아 Folium 지도를 만듭니다.                                                                                                           |
| `ui/monthly_view.py`           | `render_monthly(kind)`는 유형을 받아 무기·기술 월간 화면을 구성합니다.                                                                                                                       |
| `ui/charts.py`                 | `trend_chart()`는 선 그래프, `distribution_chart()`는 누적 가로 막대그래프를 만듭니다.                                                                                                       |
| `assets/style.css`             | 공통 배경, 제목, 카드, 필터, 범주 태그, 좁은 화면의 여백을 수정합니다.                                                                                                                       |

`ui/components.py`의 `apply_styles()`가 CSS 파일을 읽어 적용합니다. 지도는 별도 iframe 안에 표시되므로 지도 전용 스타일은 `ui/maps.py`에 있습니다. 이번 구현에는 DB 연결과 뉴스 수집을 포함하지 않습니다.

지도는 API 키가 필요 없는 로컬 Natural Earth 경계 데이터와 Folium을 사용합니다. Leaflet JS/CSS를 CDN에서 불러오므로 최초 표시에는 인터넷 연결이 필요합니다. 지도 출처와 가공 내역은 [assets/README.md](assets/README.md)를 참고하세요.

### 검증

프로젝트 루트에서 문법 오류를 확인합니다. 이 명령은 화면 동작까지 검사하지는 않습니다.

```bash
python -m compileall -q app.py config.py pages data services ui utils
```

ERD 컬럼·기본키·외래키, 사전 유형, 사용 근거, 중복 제거, 빈 데이터와 월별 집계를 검사합니다. 실제 샘플 집계는 별도 SQLite 쿼리의 `COUNT(DISTINCT article_id)` 결과와 대조합니다.

```bash
python -m unittest discover -s tests -v
```

Streamlit AppTest로 기본 지표와 네 페이지의 실행 오류를 확인할 수 있습니다.

```bash
python - <<'PY'
from streamlit.testing.v1 import AppTest

app = AppTest.from_file("app.py").run(timeout=20)
assert not app.exception
values = [int(metric.value.replace(",", "").rstrip("건개")) for metric in app.metric]
assert values == [5373, 3700, 13]
for page in [
  "pages/02_weapons_monthly.py",
  "pages/03_technology_monthly.py",
  "pages/01_overview_map.py",
  "pages/00_overview.py",
]:
  app.switch_page(page).run()
  assert not app.exception
print("기본 지표와 페이지 진입 확인 완료")
PY
```

화면을 변경한 뒤에는 앱을 실행해 하루 선택, 월 경계를 넘는 부분 기간, 종료일 미선택, 범주 전체 해제, 검색 후 선택 유지, 페이지 왕복 이동과 초기화를 확인합니다. Top 3는 범주를 모두 해제해도 유지되어야 하며, 지도·차트·한글 표시와 카드 겹침 여부는 브라우저에서 확인합니다.

지도 화면은 넓은 화면에서 지도 오른쪽에 카드가 세로로 놓이고 두 영역의 테두리 높이가 같은지, 분쟁·유형 선택에 따라 제목과 카드·범주가 바뀌는지 확인합니다. 좁은 화면에서는 카드가 지도 아래로 이어지고 고정 초기 줌에서도 마커·말풍선·태그가 잘리지 않는지 확인합니다.

---

## 프로젝트 개요

### 배경

- 러시아·우크라이나 전쟁의 드론 활용·대응기술과 이란 전쟁의 미사일·드론 공격 등이 최근 NATO·UN 자료에서도 다뤄지고 있어, 주요 분쟁에서 어떤 무기와 방산기술의 사용이 보도되는지 전쟁별·시기별로 비교할 필요
  - NATO NCIA (2026.09.09) : 우크라이나에서의 소형 드론 활용과 다중센서 기반 대드론 탐지·식별 기술 소개
  - UN (2026.03.03) : 미국·이스라엘의 대이란 공격 및 이란의 미사일·드론 반격 보도
- GDELT를 통해 다양한 해외 언론보도를 수집하고 주제별 기사량의 시간적 변화를 확인할 수 있어, 대상 분쟁의 관련 기사를 선별하고 무기·방산기술의 사용 보도 동향을 분석할 수 있는 데이터 기반 확보 가능
  - GDELT DOC 2.0 : 글로벌 온라인 뉴스의 검색 및 주제별 기사 건수·보도량의 시계열 분석 기능 제공
- 수집된 기사에 등장하는 무기·기술의 명칭과 분류를 통일하여, 사용이 보도된 무기·기술의 종류, 보도 빈도 및 기간별 변화를 일관된 기준으로 비교할 수 있는 분석 환경 마련 필요
  - SIPRI, _Arms Transfers Database – Sources and Methods_
  - 기술 분류는 NATO STO, Science & Technology Trends(2020)를 기본 자료로 하고, NATO, _Electromagnetic Warfare_(2023), NATO, _Summary of NATO’s Autonomy Implementation Plan_(2022), NATO, Summary of NATO’s Quantum Technologies Strategy(2024), NATO, Summary of NATO’s Revised Artificial Intelligence (AI) Strategy(2024) 의 관련 용어를 보완하여 구축한 프로젝트용 분석 분류체계

### 목적

- 러시아·우크라이나 전쟁과 이란 전쟁에 관한 해외 언론보도 데이터를 수집하여, 전쟁별·시기별 무기·방산기술 사용 관련 보도 빈도와 변화 추이를 시각화하는 대시보드 구축
- 단순한 무기·기술 언급이나 개발·도입 계획과 구분하여 사용이 보도된 기사를 선별하고, SIPRI 자료 기반 무기 분류와 NATO 자료 기반 기술 분류를 공통 기준으로 적용하여 무기·기술별 보도 건수, 비중, 상위 항목 및 월별 추이 분석
  - https://www.sipri.org/databases/armstransfers
  - https://www.nato.int/content/dam/nato/legacy-wcm/media_pdf/2020/4/pdf/190422-ST_Tech_Trends_Report_2020-2040.pdf
  - https://www.nato.int/en/what-we-do/deterrence-and-defence/electromagnetic-warfare
  - https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2022/10/13/summary-of-natos-autonomy-implementation-plan
  - https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2024/01/16/summary-of-natos-quantum-technologies-strategy
  - https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2024/07/10/summary-of-natos-revised-artificial-intelligence-ai-strategy
- 각 전쟁에서 반복적으로 사용이 보도되는 무기·기술과 기간별 보도 빈도의 증가·감소를 직관적으로 비교·확인할 수 있도록 지원
- 국방·방산 분야의 동향을 조사하는 실무자·연구자와 일반 관심자가 여러 기사를 직접 찾아 정리하는 부담을 줄이고, 관심 무기·기술의 사용 보도 현황을 확인할 수 있는 기초 자료 제공

### 타겟

- 방산기업·국방 관련 연구기관의 동향 조사 담당자
- 국방·방산 분야 연구자와 학습자
- 전쟁 관련 뉴스와 무기·방산 기술에 관심 있는 일반 이용자

### 기대효과

- 글로벌 기사에 분산된 무기·기술 사용 보도 정보의 통합을 통한 자료 탐색 시간과 정리 부담 감소
- 무기·기술별 사용 보도 빈도와 순위 시각화를 통한 주요 보도 항목의 신속한 파악
- 분쟁별 비교를 통한 공통으로 사용이 보도된 무기·기술과 전쟁별 보도 특징의 파악
- 기간별 빈도 및 비중 분석을 통한 무기·기술 사용 보도 변화 추이의 체계적 확인
- 직관적인 시각화를 통한 일반 이용자의 국방·방산 정보 접근성 및 보도 동향 이해도 향상
- 관련 기사와 출처 연결을 통한 관심 무기·기술의 추가 탐색 및 원문 근거 확인 지원
- 국방·방산 분야의 학습, 기초 자료조사 및 정기 동향 보고를 위한 참고 자료 제공

---

## 프로젝트 수행 방향 및 내용

### 데이터 수집

1. SIPRI Arms Transfers Database – 무기 명칭·분류 데이터
   - 선정 사유 : 검증된 주요 재래식 무기의 명칭과 설명을 구조화하여 제공하므로 일관된 무기 분류 기준으로 활용하기에 적합
   - 수집 목적: 기사에 등장하는 무기 명칭을 표준 무기명과 분류에 연결하기 위한 무기 분류 Dictionary 구축
   - 수집 방법
     1. SIPRI Transfer Register 데이터를 CSV 형태로 수집
     2. `Weapon designation`과 `Weapon description`의 연결 관계를 추출하고 표기 차이·약어를 정리하여 `표준 무기명–무기 분류–검색용 명칭` 형태로 구성
2. NATO STO Science & Technology Trends 2020–2040 – 방산기술 기본 분류 데이터
   - 선정 사유: NATO 국방 과학기술 전문가 네트워크의 분석을 기반으로 주요 방산기술 범주를 체계적으로 제시하여 기술 분류 기준으로 활용하기에 적합
   - 수집 목적: 기사에 등장하는 방산기술 명칭을 공통 기술명과 상위 분류에 연결하기 위한 기술 분류 Dictionary 구축
   - 수집 방법
     1. NATO STO 기술전망 보고서의 8개 핵심 기술 분야를 대상으로 `Keywords`, `Technology Focus Areas`, 기술 정의 및 약어표에서 기술 용어 후보 추출
     2. 독립적인 기술 개념으로 사용할 수 있는 표현만 선정하고 기관명·정책명·국가명·연구 프로그램명 및 의미가 지나치게 넓은 일반 용어 제외
     3. NATO의 전자기전·자율체계·AI·양자기술 관련 공개자료에서 세부 기술과 운용 용어를 추가 추출
     4. 대소문자·하이픈·단수·복수 표기를 정규화하고 정식 명칭을 표준 기술명으로 지정하여 약어·표기 변형·한국어 번역명을 유의어로 연결
     5. 기존 용어와 추가 용어를 병합하여 `표준 기술명–상위 기술 분류–동의어·약어–한국어 번역명–출처` 형태의 기술 분류 Dictionary 구성
3. CAMEO Event Coding Dictionary 및 NATO 군사행동 정의 – 무기·기술 사용 여부 판별 데이터
   - 선정 사유: 위협·군사태세와 실제 공격·교전을 구분하는 정의와 사례를 제공하여 무기·기술의 사용 여부 판정 기준으로 활용하기에 적합
   - 수집 목적: 단순 언급·위협·계획과 실제 전투·방어·군사작전에서의 사용을 구분하기 위한 판별 Dictionary 구축
   - 수집 방법
     1. CAMEO에서 실제 군사행동과 사용 이전 단계에 해당하는 이벤트 코드 및 정의 수집
     2. 공개 Verb Pattern Dictionary에서 코드별 동사·구문을 추출하여 사용 포함·제외 표현 구성
     3. NATO 공개자료에서 전자전 등 방산기술의 운용 표현을 추가하여 `행동 유형–판별 표현–포함 여부–출처` 형태로 구성
4. GDELT 2.0 BigQuery – 해외 뉴스 기사 후보 데이터
   - 선정 사유: 다양한 해외 온라인 뉴스와 출처·발행일·원문 URL 등의 메타데이터를 제공하여 수집 결과의 추적성과 일관성 확보에 적합
   - 수집 목적: 분쟁별·기간별 무기·방산기술 사용 보도 빈도와 변화 추이 분석을 위한 원천 기사 데이터 확보
   - 수집 방법
     1. Google BigQuery의 GDELT 공개 데이터셋에서 기간·매체·행위자·언어·이벤트 코드에 대한 분쟁별 조건을 적용하여 SQL 조회
     2. 러시아·우크라이나 전쟁과 이란·이스라엘·미국 간 직접 교전의 후보 레코드를 1차 분류하여 CSV 형태로 추출
     3. 기사 식별정보와 원문 URL을 보존하고 적용 SQL·조회 기간·수집 일시를 함께 기록하여 수집 과정의 재현성 확보

### 데이터 전처리

#### 데이터 정제

- 수집된 원문은 별도로 보존하고 분석용 제목·본문 생성
- HTML 태그, 광고, 메뉴, 불필요한 공백·특수문자 제거
- 기사 URL 정규화 및 발행일·수정일·수집일 형식 통일
- 원문 미확보·필수값 누락·형식 오류 데이터에 처리 상태 부여

#### 데이터 통합

- 기사 식별정보 또는 정규화된 URL을 기준으로 GDELT CSV 메타데이터와 원문 기사 결합
- 분쟁 판별 Dictionary, 무기 분류 Dictionary, 기술 분류 Dictionary 및 사용 여부 판별 Dictionary 연결
- 무기와 기술을 독립적으로 매핑하고 한 기사에 여러 항목이 등장하는 경우 각각의 연결 관계 유지
- 기사 원문과 분쟁·무기·기술·사용 여부 판정 결과를 구분하여 저장

#### 데이터 축소

- 정규화된 URL이 동일한 중복 레코드 제거
- 정제된 본문이 동일한 재게시 기사 중 대표 기사만 유지
- 동일 기사의 수정본이 여러 건인 경우 최종 수정일이 가장 최근인 기사 유지
- 분석에 사용하지 않는 중간 컬럼과 원문 미확보 등 분석 불가능 데이터 제외

#### 데이터 변환

- 국가·기관·무기·기술의 대소문자, 하이픈, 단수·복수, 약어 및 표기 변형 정규화
- 기사에서 발견된 무기·기술 명칭을 표준 ID와 상위 분류에 매핑하고 근거 문장 저장
- 사용 표현과 행위 주체의 연결 관계를 기준으로 `사용 보도`, `사용 외 언급`, `확인 필요`로 분류
- 기사 전체가 아닌 `기사–무기·기술 항목` 단위로 사용 여부 판정
- 개발·지원·계획·시험·위협 등 실제 사용 이전 단계는 `사용 외 언급`으로 변환

#### 데이터 필터링 및 정렬

- 영문 기사, 대상 기간 및 수집 대상 매체 조건 적용
- 러시아·우크라이나 전쟁의 교전·무기 사용·군사 활동 관련 기사만 포함하고 국내 정치와 다른 지역 군사 활동 제외
- 이란·이스라엘 또는 이란·미국 간 직접 공격·방어 기사만 포함하고 무기 공급·지원 또는 대리세력 활동만 다룬 기사 제외
- 대상 분쟁과의 관련성이 불명확한 기사는 `확인 필요`로 분리
- 분쟁 관련 기사 중 무기 또는 방산기술이 확인된 기사만 분석 대상으로 선정
- 분쟁·발행일·매체·표준 무기·기술 ID 순으로 정렬하여 분석 데이터 생성

### 분석(EDA)

### 시각화

### 대시보드 화면

1. 분쟁별 방산 무기/기술 사용 보도 동향
   - 분쟁 종류별, 기간별, 무기/기술별 필터
   - 전체 분석 기사 수(중복 제거 완료 기사 기준)
     : 분쟁관련 기사 중 방산 무기/기술이 언급된 기사
   - 사용 관련 보도 수(방산 무기/기술의 사용이 원문에 명시된 기사 수)
     : 분쟁관련 기사 중 방산 무기/기술의 사용 사례가 언급된 기사
   - 분석용 방산 무기/기술 분류 수
     - 샘플에 등록된 방산 무기 범주 수 (현재 7개)
     - 샘플에 등록된 방산 기술 범주 수 (현재 6개)
   - 분쟁별 방산 무기/기술 사용 보도 현황 지도
     - 분쟁별 사용 관련 보도 수
     - 분쟁별 주요 방산 무기/기술 Top 3
2. 방산 무기 월간 분석
   - 분쟁/기간별 방산 무기 월간 사용 보도 추이
     - 방산 무기 범주 리스트 및 다중 선택
   - 분쟁별 사용 방산 무기 최신 Top 3 보도 사례 분포
3. 방산 기술 월간 분석
   - 분쟁/기간별 방산 기술 월간 사용 보도 추이
     - 방산 기술 범주 리스트 및 다중 선택
   - 분쟁별 사용 방산 기술 최신 Top 3 보도 사례 분포

### 데이터 출처

### 수행 도구

- **Python·Pandas·NumPy·Jupyter Notebook**
  : 데이터 수집·정제·변환, 지표 계산 및 EDA 수행
- **MySQL·MySQL Workbench**
  : 테이블·ERD·키·인덱스 설계, 정제 데이터 저장 및 집계
- **Matplotlib·Seaborn·SciPy**
  : 데이터 시각화, 기초 통계 분석
- **Streamlit·Folium**
  : 대시보드 화면 및 지도 시각화 구현, DB·지도 연동 패키지 검증 및 버전 고정
- **Git·GitHub**
  : 코드 공동 작업 및 버전 관리, 의존성 목록과 실행 방법 관리

## 프로젝트 조직 (구성원 및 역할)

### 역할 분담

- **정종규(조장)**
  : 팀 일정·진행 상황 관리 및 회의 주관, 교수님 소통 및 요구사항 공유, 무기 Dictionary 구축 기준 수립 및 결과 검수, 무기·기술 사용 여부 판별 Dictionary 구축, GDELT 기사 수집 방법 및 절차 설계
- **강민주**
  : 무기·기술 분류 Dictionary의 DB 적재, 정제된 뉴스 기사 데이터의 DB 적재
- **박서준**
  : SIPRI 기반 무기 Dictionary 데이터 구축, GDELT 기사 수집 기준 수립 및 선정 근거 정리, GDELT 후보 기사 원천 데이터 수집 및 1차 정제
- **이다은**
  : 프로젝트 기획서 최종 정리, 중간 발표자료 제작, GitHub 기반 프로젝트 산출물 관리, NATO 기반 기술 Dictionary 구축
- **오휘준**
  : GDELT 수집 기사의 무기·기술 식별 및 분류 코드 개발

## 프로젝트 추진 일정

### 일정

- **09/11(금) ~ 09/16(수)** : 프로젝트 주제 선정 및 기획안 초안 작성
- **09/17(목) ~ 09/22(화)** : 데이터 수집 기준 수립 및 Dictionary 구축, GDELT 후보 기사 수집, 무기·기술 분류 및 사용 여부 판별 Dictionary DB 적재, 기획안 마무리 및 중간 발표
- **09/23(수), 09/28(월)** : 기사 데이터 전처리·분류 완료, 최종 정제 데이터 DB 적재, 데이터 품질 확인 및 EDA 수행, 시각화 설계 확정
- **09/29(화) ~ 09/30(수)** : 시각화 구현, 대시보드 개발 및 DB 연동
- **10/01(목)** : 대시보드 통합 테스트, 집계 결과 검증 및 오류 수정
- **10/02(금)** : 발표자료 제작, 시연 점검 및 발표 준비
- **10/06(화)** : 최종 발표 및 프로젝트 마무리
