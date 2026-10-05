# 국가 간 분쟁의 방산 무기·기술 사용 보도 분석 대시보드

해외 언론보도에 나타난 무기·방산기술의 사용 보도를 분쟁별·기간별로 살펴보는 Streamlit 대시보드입니다. 지도와 차트로 주요 범주와 변화 추이를 확인하고, 관련 기사의 근거 문장과 원문으로 이어서 탐색할 수 있습니다.

**이 대시보드의 숫자는 보도 건수입니다. 실제 무기·기술의 사용 횟수나 성능을 의미하지 않습니다.**

## 프로젝트 소개

### 배경과 목적

일부 무기·기술 키워드에 집중된 분쟁 보도에서 벗어나, 주요 국가간 분쟁에 등장하는 무기·방산기술의 종류와 사용 보도 변화를 공통 기준으로 비교하는 것이 프로젝트의 목적입니다. 단순한 명칭 언급이나 개발·도입 계획과 사용 보도를 구분하고, 사용·비사용·불확실의 판정 구성을 함께 제시하여 보도의 확실성도 살펴봅니다.

여러 기사에 흩어진 정보를 같은 분류와 집계 기준으로 정리하여 다음 질문을 살펴봅니다.

- 분쟁별로 어떤 무기·기술의 사용이 많이 보도되었는가?
- 관심 범주의 사용 보도가 월별·일별로 어떻게 달라졌는가?
- 해당 수치에 포함된 기사와 사용 판정의 근거는 무엇인가?

### 주요 타겟층

주요 타겟층은 **방산기업·국방 관련 연구기관의 동향 조사 담당자**입니다.  
기사 탐색과 정리의 부담을 줄이고, 분쟁별·시기별 무기·기술 사용 보도를 기초 조사와 정기 동향 보고에 활용하도록 지원합니다.

### 데이터 출처와 판별 기준

주요 데이터 출처와 활용 목적은 다음과 같습니다.

| 출처·기준                                           | 기획상 활용 목적                                               |
| --------------------------------------------------- | -------------------------------------------------------------- |
| UCDP                                                | 주요 국가간 분쟁의 분석 범위 설정과 분쟁 사건 추이 대조        |
| SIPRI Arms Transfers Database                       | 무기 명칭을 표준 무기명과 분류에 연결하는 사전 구성            |
| NATO STO 기술전망 보고서 및 NATO 공개자료           | 방산기술 분류와 세부 기술·운용 용어 사전 구성                  |
| CAMEO Event Coding Dictionary 및 NATO 군사행동 정의 | 실제 사용과 단순 언급·위협·계획을 구분하는 표현·패턴 사전 구성 |
| GDELT 2.0 BigQuery                                  | 분쟁별 조건으로 해외 뉴스 기사 후보와 원문 URL 확보            |

기술 분류는 NATO STO의 *Science & Technology Trends 2020–2040*을 기본 자료로 하며, 전자전·자율체계·양자기술·개정 AI 전략 관련 NATO 공개자료를 보완하여 구성하는 프로젝트용 분석 분류체계입니다.

영문 기사에서 대상 국가간 직접 공격·방어와 무기·기술을 선별하고, 기사–무기·기술 항목 단위로 사용 표현과 행위 주체의 연결 관계를 판별합니다.  
개발·지원·계획·시험·위협 등 사용 이전 단계는 ‘사용 외 언급’, 판별이 어려운 내용은 ‘확인 필요’로 구분합니다.  
화면은 DB에 적재된 ‘사용·비사용·불확실’ 판정을 표시합니다.

## 주요 기능

| 화면      | 조회 범위                   | 제공 내용                                                     |
| --------- | --------------------------- | ------------------------------------------------------------- |
| 종합 분석 | 등록된 전체 데이터 기간     | 분쟁별 주요 무기·기술, 기사 지표, 분쟁 지도, 분류별 세부 명칭 |
| 연간 분석 | 선택한 한 해                | 범주별 사용 판단 분포, 월별 사용 보도 추이, 관련 기사         |
| 월간 분석 | 선택한 한 달                | 범주별 사용 판단 분포, 일별 사용 보도 추이, 관련 기사         |
| 주간 분석 | 선택한 한 주, 월요일~일요일 | 범주별 사용 판단 분포, 일별 사용 보도 추이, 관련 기사         |

### 탐색 흐름

1. 종합 분석에서 분쟁별 사용 보도와 주요 범주를 확인합니다.
2. 지도 팝업에서 연간·월간·주간 분석으로 이동하거나 상단 메뉴에서 화면을 선택합니다.
3. 분쟁·기간·무기/기술을 고르고, 최대 5개 범주를 비교합니다.
4. 도넛 차트의 사용 조각 또는 추이 점의 관련 기사 버튼으로 기사를 조회합니다.
5. 근거 문장과 원문을 확인하거나 기사 CSV를 내려받습니다.

종합 분석의 카드와 지도에는 사용 보도가 1건 이상인 분쟁만 표시됩니다.  
범주 태그를 선택하면 분류 사전에 등록된 세부 명칭이 나타납니다.

기간별 화면은 가장 최근 기사가 속한 기간을 기본값으로 사용합니다.  
처음에는 사용 보도 수 기준 상위 범주를 최대 3개 선택하며, 검색과 선택을 통해 최대 5개까지 비교할 수 있습니다.  
추이에 빈 날짜·월이 있으면 0건으로 표시합니다.

분쟁·기간·유형·범주·검색어는 페이지별로 저장됩니다.  
지도에서 다른 분석 화면으로 이동할 때는 목적 화면의 분쟁만 변경하고 기존 기간·유형·범주 선택은 유지합니다.

관련 기사 목록은 사용 판정 기사를 기사 ID 기준으로 중복 제거하여 최신순으로 20건씩 표시합니다.  
도넛의 사용 조각은 선택 기간 전체를, 추이 점의 관련 기사 버튼은 해당 월 또는 날짜를 조회합니다.

## 데이터와 집계 기준

### 읽는 테이블

앱은 여섯 테이블의 필요한 컬럼만 하나의 읽기 전용 트랜잭션에서 조회합니다. DB 스키마와 데이터를 수정하지 않습니다.

| 테이블             | 역할                  | 필수 컬럼                                                                                       |
| ------------------ | --------------------- | ----------------------------------------------------------------------------------------------- |
| `conflicts`        | 분쟁 이름·표시 정보   | `conflict_id`, `conflict_name_en`, `conflict_name_ko`, `color`, `flag`, `latitude`, `longitude` |
| `categories`       | 무기·기술 범주        | `category_id`, `kind`, `category_name`                                                          |
| `sipri_dictionary` | 무기 범주별 세부 명칭 | `wp_id`, `category_id`, `wp_name`                                                               |
| `nato_dictionary`  | 기술 범주별 세부 명칭 | `tech_id`, `category_id`, `tech_name`                                                           |
| `articles`         | 분쟁에 연결된 기사    | `article_id`, `conflict_id`, `published_date`, `article_url`, `title`                           |
| `result`           | 기사·범주별 사용 판정 | `article_id`, `category_id`, `usage_code`, `evidence_sentence`                                  |

`result`는 기사 ID와 범주 ID의 쌍이 고유해야 합니다. 한 기사가 여러 범주에 속하면 여러 판정 행을 가질 수 있습니다. `articles`에서는 같은 분쟁 안의 URL 중복을 허용하지 않습니다.

검증 규칙의 기준은 `data/table_contract.py`입니다. 필수값, 자료형, 키 중복, 참조 관계, 날짜·좌표·색상 형식을 확인합니다. 사용 판정에는 비어 있지 않은 근거 문장이 필요합니다.

### 판정 코드

현재 소스는 DB의 `usage_code` 원값을 그대로 사용합니다. `data/constants.py`의 `UsageCode`와 `data/table_contract.py`의 검증 기준은 다음과 같습니다.

| 의미   | DB `usage_code` | 내부 `UsageCode` |
| ------ | --------------- | ---------------- |
| 사용   | `0`             | `USED = 0`       |
| 비사용 | `1`             | `NOT_USED = 1`   |
| 불확실 | `2`             | `UNCERTAIN = 2`  |

로더는 사용·비사용 코드를 서로 바꾸지 않으며 코드 체계를 자동으로 추측하지 않습니다. 다른 DB를 연결할 때도 `0=사용, 1=비사용, 2=불확실`의 의미가 일치해야 합니다. 사용 판정 `0`에는 근거 문장이 필요합니다.

무기·기술 유형은 내부에서 `wp`, `tech`를 사용합니다. 로더는 외부 값 `weapon`, `technology`도 각각 `wp`, `tech`로 변환합니다.

### 기사 수와 판정 수의 차이

| 지표·집계                          | 기준                                                                |
| ---------------------------------- | ------------------------------------------------------------------- |
| 종합 분석의 언급 기준 분석 기사 수 | 선택한 분쟁에 연결된 `articles` 행 수. 판정 결과가 없는 기사도 포함 |
| 기간별 기사 집계의 분석 기사 수    | 판정 결과에 등장하는 고유 기사 ID 수. 사용·불확실·비사용 포함       |
| 사용 보도 기사 수                  | 사용 판정이 있는 고유 기사 ID 수                                    |
| 범주별 사용 보도 추이              | 해당 범주의 사용 판정 기사 ID를 중복 제거한 수                      |
| 범주별 사용 판단 분포              | 기사 × 범주의 판정 행 수                                            |

유형을 `전체`로 조회할 때 기사 수는 무기·기술 기사 ID 집합의 합집합으로 계산합니다. 무기 기사 수와 기술 기사 수를 단순히 더하지 않습니다. 같은 URL이라도 서로 다른 분쟁에 별도 기사 ID로 등록되면 각각 집계합니다.

예를 들어 같은 분쟁·기간에 아래 두 기사가 있다고 가정합니다.

| 기사   | 판정 결과              |
| ------ | ---------------------- |
| 기사 A | 미사일 사용, 드론 사용 |
| 기사 B | 레이더 불확실          |

종합 분석 기사 수는 **2건**, 기간별 기사 집계의 분석 기사 수는 **2건**, 사용 보도 기사 수는 **1건**, 전체 범주 판정 수는 **3건**입니다. 미사일·드론의 사용 보도 수를 합하면 2건이지만, 두 범주가 같은 기사 A에 있으므로 사용 보도 기사는 1건입니다.

기사 B의 판정 결과가 없으면 종합 분석 기사 수는 2건을 유지하고, 기간별 기사 집계의 분석 기사 수는 1건이 됩니다.

종합 분석의 ‘언급 기준 분석 기사 수’는 DB에 등록된 분쟁별 기사 행 수입니다. 이 지표만으로 모든 기사에 대한 범주 판정이 완료되었다고 해석할 수는 없습니다.

## CSV 다운로드

| 다운로드                | 적용 조건                              | 행 단위                 |
| ----------------------- | -------------------------------------- | ----------------------- |
| 무기·기술 분류 기준 CSV | 분쟁·기간과 관계없이 전체 분류         | 범주별 분류명·세부 명칭 |
| 기사 CSV                | 기간별 화면의 분쟁·기간·무기/기술 필터 | 기사 × 범주별 판정      |

기사 CSV에는 사용·불확실·비사용을 모두 포함합니다. 화면에서 선택한 범주와 범주 검색어는 기사 CSV의 필터에 포함하지 않습니다.

기사 CSV 컬럼은 다음과 같습니다.

```text
기사 ID, 보도일, 제목, 국가간 분쟁, 무기/기술, 범주 ID,
범주명, 사용 판정, 근거 문장, 원문 URL
```

보도일 내림차순, 기사 ID·범주 ID 오름차순으로 정렬하며 보도일은 `YYYY-MM-DD` 형식입니다. CSV는 UTF-8 BOM을 포함하고, 결과가 없어도 헤더를 제공합니다. 분류 기준 CSV에서는 사전에 등록된 명칭이 없는 범주의 세부 명칭을 빈 값으로 유지합니다.

다운로드는 현재 화면의 스냅샷과 필터에서 생성합니다. 다운로드를 위해 DB를 다시 조회하지 않습니다.

## 데이터 갱신과 캐시

서버 프로세스는 최초 조회 시 기사 연결, 일별·월별 집계, 분류 사전·CSV 등 공통 데이터를 준비하여 하나의 `SnapshotStore`에서 공유합니다. 페이지 이동과 필터 변경은 준비된 스냅샷을 사용합니다.

백그라운드 작업은 **1시간 간격**으로 DB를 다시 조회합니다.

1. 여섯 테이블의 내용을 읽고 데이터 버전 해시를 계산합니다.
2. 이전 버전과 같으면 기존 스냅샷을 재사용합니다.
3. 변경되면 새 집계가 완성된 뒤 스냅샷 참조를 교체합니다.
4. 조회·갱신에 실패하면 마지막 정상 스냅샷을 유지하고 다음 주기에 다시 시도합니다.

**새 데이터는 사용자의 다음 페이지 이동·필터 조작 등 앱 재실행 시 화면에 반영됩니다.** 화면을 자동으로 새로고침하는 타이머는 없습니다.

조건별 요약·추이·지도·CSV 등은 스냅샷별 `ViewCache`에서 최대 128개 결과를 재사용합니다. DB 엔진도 재사용하지만 캐시 만료 시간은 지정되어 있지 않습니다. `pool_recycle=1800`은 오래된 DB 연결을 다시 빌릴 때 교체하는 설정이며, 30분마다 엔진 캐시나 화면 데이터를 갱신하는 설정은 아닙니다.

## 프로젝트 구조

실제 작업 폴더를 기준으로 **폴더를 먼저 표시하고, 같은 단계에서는 이름순(대소문자 구분 없이)**으로 정렬했습니다. `.git/`, `.ruff_cache/`, `__pycache__/` 등 관리·캐시 폴더는 생략했습니다. `secrets.toml`과 `NEWREADME.md`는 현재 로컬에 존재하는 파일이며, 공통 소스와 구분해 표시했습니다.

```text
conflict-defense-news-dashboard/
├── .streamlit/
│   ├── config.toml                   # Streamlit 테마
│   └── secrets.toml                  # 로컬 DB 접속 정보, Git 제외
├── .vscode/
│   ├── extensions.json               # 추천 확장
│   └── settings.json                 # Python·Ruff 편집기 설정
├── assets/
│   ├── flags/
│   │   ├── *.svg                     # 국가별 국기 SVG 파일 (축약)
│   │   ├── LICENSE-GRAPHICS          # Twemoji 그래픽 라이선스
│   │   └── manifest.json             # 국기 자산 출처·버전·해시
│   ├── fonts/
│   │   ├── OFL-Pretendard.txt        # 글꼴 라이선스
│   │   ├── Pretendard-Bold.ttf       # 워드클라우드용 Bold 글꼴
│   │   ├── pretendard-manifest.json  # 글꼴 자산 출처·버전·해시
│   │   └── Pretendard.ttf            # Regular 글꼴
│   ├── README.md                     # 자산 출처와 가공 내역
│   ├── style.css                     # 공통 화면 스타일
│   └── world_countries.geojson       # 국가 경계 데이터
├── data/
│   ├── constants.py                  # 유형·DB 판정 원값 정의
│   ├── db_loader.py                  # 읽기 전용 조회·유형 이름 정규화
│   ├── snapshot.py                   # 공유 집계·버전·백그라운드 갱신·캐시
│   └── table_contract.py             # 테이블 규격·참조 관계 검증
├── pages/
│   ├── 01_overview.py                # 종합 분석
│   ├── 02_annual.py                  # 연간 분석 진입점
│   ├── 03_monthly.py                 # 월간 분석 진입점
│   └── 04_weekly.py                  # 주간 분석 진입점
├── services/
│   ├── analysis_service.py           # 기사·범주 집계·순위·추이
│   ├── detail_service.py             # 판정 조인·기사 상세·사전 명칭
│   └── export_service.py             # 기사 CSV 생성
├── ui/
│   ├── frontend/                     # 컴포넌트 JavaScript·CSS
│   │   ├── classification.css        # 분류 세부 명칭 스타일
│   │   ├── classification.js         # 분류 세부 명칭 표시
│   │   ├── donut.js                  # 도넛 차트·기사 조회 이벤트
│   │   ├── loading.css               # 로딩 표시 스타일
│   │   ├── map.js                    # 지도 이벤트·카드 강조·시점 저장
│   │   ├── monthly.css               # 추이 차트·말풍선 스타일
│   │   ├── monthly.js                # 추이 차트·말풍선·기사 조회 이벤트
│   │   └── wordcloud.js              # 워드클라우드 크기 측정·이미지 표시
│   ├── charts.py                     # Plotly 차트
│   ├── components.py                 # 필터·지표·다운로드·기사 카드
│   ├── flags.py                      # 로컬 국기 SVG 표시
│   ├── interactive.py                # Python과 브라우저 이벤트 연결
│   ├── loading.py                    # 로딩 표시
│   ├── maps.py                       # Folium 지도
│   ├── period_view.py                # 연간·월간·주간 공통 화면
│   └── wordcloud_view.py             # 워드클라우드 이미지 생성·표시 코드
├── utils/
│   └── state.py                      # 페이지별 선택값·초기화·이동 상태
├── .editorconfig                     # 들여쓰기·줄바꿈 편집 규칙
├── .gitignore                        # Git 제외 규칙
├── app.py                            # 앱 진입점·메뉴·공통 필터·오류 안내
├── config.py                         # 화면 상수와 DB 기반 조회 설정
├── NEWREADME.md                      # 로컬 README 초안, 미추적
├── pyproject.toml                    # Python 코드 검사·포맷 규칙
├── README.md                         # 프로젝트 안내·실행 방법
├── requirements-dev.txt              # 개발 도구 Ruff
└── requirements.txt                  aa# 앱 실행 의존성
```

`data`는 입력 데이터와 갱신을, `services`는 집계·상세 조회를, `ui`는 화면과 상호작용을 담당합니다. 연간·월간·주간 페이지는 `ui/period_view.py`의 `render_period_view()`를 재사용합니다.

화면의 사용자 선택은 `utils/state.py`에서 관리합니다. `ui/frontend`는 지도·Plotly 클릭 전달과 브라우저에서 필요한 동작을 처리하며, 별도의 Node 패키지 설치나 빌드 과정은 없습니다.

## 개발과 검증

개발 도구를 함께 설치하려면 다음 명령을 사용합니다.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

코드 규칙은 `pyproject.toml`을 기준으로 합니다. Python 3.13, Ruff 0.16.8, 스페이스 2칸 들여쓰기, 작성한 따옴표 유지, LF 줄바꿈을 사용합니다. 줄 길이 기준은 Ruff 기본값인 88자입니다.

수정 없이 검사하려면 다음 명령을 실행합니다.

```bash
python -m compileall -q app.py config.py pages data services ui utils
python -m ruff check .
python -m ruff format --check .
```

문법·코드 규칙 검사는 실제 DB 연결과 브라우저 동작까지 확인하지 않습니다. 실행 환경에서는 필터 변경, 도넛·추이에서 기사 조회, 원문 연결, CSV 내용과 데이터 갱신을 확인해야 합니다.

## 실행 방법

### 준비 사항

- Python **3.13.x**, MySQL Community Server **8.4.x**
- 본인 PC의 MySQL 관리자 계정 root 비밀번호
- 별도로 공유받은 개발 DB 덤프 파일 dashboarddb-dev-v1.sql
- 별도로 공유받은 secrets.toml 파일

- DB 복원·Python 환경·압축 해제 공간을 위해 여유 디스크 3GB 이상, 메모리 8GB 이상을 권장
- 기본 MySQL 포트 `3306`, 기본 앱 포트 `8501` 사용

### 1. 저장소 clone 및 main 브랜치 접근

터미널에서 저장소를 내려받을 위치로 이동한 뒤, 다음 명령을 한 줄씩 실행합니다.

```bash
git clone https://github.com/F5-Acorn/conflict-defense-news-dashboard.git
cd conflict-defense-news-dashboard
git switch main
```

VSCode를 사용하는 경우 내려받은 `conflict-defense-news-dashboard` 폴더를 엽니다.

이후 Python 환경 준비와 앱 실행은 **`app.py`와 `requirements.txt`가 있는 프로젝트 루트 폴더**에서 진행합니다.

### 2. Python 환경과 의존성 준비

프로젝트 루트에서 다음 명령을 한 줄씩 실행합니다.

```bash
conda create -n streamlit python=3.13
conda activate streamlit
python -m pip install -r requirements.txt
```

이미 Python 3.13으로 만든 `streamlit` 환경이 있다면 첫 번째 환경 생성 명령은 생략합니다.

Windows에서 `conda` 명령을 찾을 수 없다면 **Anaconda Prompt**를 열고 프로젝트 루트로 이동하여 실행합니다.

MySQL의 `caching_sha2_password` 인증에 필요한 추가 의존성도 설치합니다. 아래 명령은 레포에서 사용하는 PyMySQL 버전을 유지하면서 RSA 인증 의존성을 추가합니다. [PyMySQL 공식 설치 안내](https://pymysql.readthedocs.io/en/latest/user/installation.html)

```bash
python -m pip install "PyMySQL[rsa]==1.2.0"
```

### 3. 전달받은 secrets.toml 추가

전달받은 `secrets.toml` 파일을 프로젝트 루트의 **`.streamlit` 폴더 안에 복사**합니다.

```text
conflict-defense-news-dashboard/
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml
├── app.py
└── requirements.txt
```

secrets.toml 파일의 내용은 하기와 같이 작성되어 있습니다.

```toml
[connections.dashboarddb]
url = "mysql+pymysql://dashboard_reader:PASSWORD@127.0.0.1:3306/dashboarddb_dev_v1?charset=utf8mb4"
```

- 실제 전달받은 파일에는 `PASSWORD` 대신 실제 비밀번호가 기입되어 있고, 다음 단계의 계정 생성 SQL에도 같은 비밀번호를 적용합니다.

`secrets.toml`은 현재 레포의 `.gitignore`에 등록되어 있어 Git 추적 대상에서 제외됩니다.

### 4. 로컬 DB 복원

#### 4-1. SQL 파일과 MySQL 준비

팀에서 공유한 **`dashboarddb-dev-v1.sql`**을 다운로드합니다. 아래 명령은 파일이 본인 계정의 `Downloads` 폴더에 있다고 가정합니다.

MySQL 서버를 시작하고 터미널에서 다음 명령을 확인합니다.

```bash
mysql --version
```

`mysql` 명령을 찾을 수 없다면 MySQL 설치 폴더의 `bin` 경로가 PATH에 등록되어 있는지 확인합니다.

#### 4-2. DB 생성 및 조회 계정 준비 — 공통

macOS는 터미널, Windows는 **명령 프롬프트(cmd)**에서 다음 명령으로 MySQL에 접속합니다.

```bash
mysql --host=127.0.0.1 --port=3306 --user=root -p
```

`Enter password:`가 나오면 **본인 PC에 MySQL을 설치할 때 설정한 root 비밀번호**를 입력합니다. 앱 조회 계정의 비밀번호를 입력하는 단계가 아닙니다.

```sql
CREATE DATABASE dashboarddb_dev_v1
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

다음으로 앱 조회 계정을 준비하고 권한을 부여합니다.

```sql
CREATE USER IF NOT EXISTS 'dashboard_reader'@'localhost'
  IDENTIFIED BY PASSWORD;

GRANT SELECT ON dashboarddb_dev_v1.*
  TO 'dashboard_reader'@'localhost';

FLUSH PRIVILEGES;

exit;
```

3번과 마찬가지로 `PASSWORD`에는 secrets.toml 파일에서 확인한 실제 비밀번호를 기입합니다.

#### 4-3. SQL 파일 복원 — macOS

일반 터미널에서 다음 명령을 실행하여 DB를 복제합니다.

```bash
mysql --host=127.0.0.1 --port=3306 --user=root -p --default-character-set=utf8mb4 dashboarddb_dev_v1 < "$HOME/Downloads/dashboarddb-dev-v1.sql"
```

root 비밀번호를 입력한 뒤 명령이 끝날 때까지 기다립니다.

파일 위치가 다르면 `"$HOME/Downloads/dashboarddb-dev-v1.sql"`을 실제 경로로 변경합니다. 공백이 있는 경로도 사용할 수 있도록 따옴표를 유지합니다.

### 4-4. SQL 파일 복원 — Windows

**명령 프롬프트(cmd)**에서 다음 명령을 실행합니다.

```bat
mysql --host=127.0.0.1 --port=3306 --user=root -p --default-character-set=utf8mb4 dashboarddb_dev_v1 < "%USERPROFILE%\Downloads\dashboarddb-dev-v1.sql"
```

root 비밀번호를 입력한 뒤 명령이 끝날 때까지 기다립니다.

파일 위치가 다르면 `"%USERPROFILE%\Downloads\dashboarddb-dev-v1.sql"`을 실제 경로로 변경하고 따옴표를 유지합니다.

VSCode 터미널을 사용하는 경우 터미널 프로필에서 **Command Prompt**를 선택합니다. 위 명령은 cmd 기준이므로 PowerShell 창에 그대로 입력하지 않습니다.

두 운영체제의 명령은 `<`로 SQL 파일을 MySQL에 전달하여 복원하는 방식입니다. 복원 중 오류가 나오면 오류를 해결한 뒤 다음 단계로 진행합니다. [MySQL 공식 SQL 파일 실행 안내](https://dev.mysql.com/doc/refman/8.4/en/mysql-batch-commands.html)

#### 4-5. 복원 결과와 조회 권한 확인 — 공통

앱에서 사용하는 **`dashboard_reader` 계정**으로 테이블 목록을 확인합니다.

```bash
mysql --host=127.0.0.1 --port=3306 --user=dashboard_reader -p dashboarddb_dev_v1 -e "SHOW TABLES;"
```

이번 비밀번호 요청에는 **조회 계정의 비밀번호**를 입력합니다.

다음 여섯 테이블이 표시되는지 확인합니다.

```text
articles
categories
conflicts
nato_dictionary
result
sipri_dictionary
```

테이블 목록 확인은 조회 계정의 접속과 테이블 접근을 확인하는 단계입니다. 데이터 복원 상태는 다음 단계에서 대시보드 화면까지 확인합니다.

### 5. 프로젝트 루트에서 대시보드 실행

`app.py`가 있는 프로젝트 루트에서 실행합니다.

```bash
conda activate streamlit
streamlit run app.py
```

## 자산과 라이선스

국가 경계 데이터는 Natural Earth 자료를 가공하여 로컬 GeoJSON으로 사용합니다. 지도 타일 API 키는 필요하지 않지만 지도 표시용 Leaflet JS/CSS는 CDN에서 불러옵니다.

한글 이미지용 Pretendard 글꼴과 국기용 Twemoji SVG를 포함합니다.  
글꼴·국기 자산의 출처·버전·해시는 `assets/fonts/pretendard-manifest.json`과 `assets/flags/manifest.json`, 라이선스 원문은 `assets/fonts/OFL-Pretendard.txt`와 `assets/flags/LICENSE-GRAPHICS`에서 확인할 수 있습니다.  
자산의 가공 내역은 `assets/README.md`를 참고하세요.
