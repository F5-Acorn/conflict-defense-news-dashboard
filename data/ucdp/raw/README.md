# UCDP 원본과 2·3단계 가공

이 폴더에는 UCDP에서 다운로드한 두 파일을 원본 그대로 보관한다.

| 파일 | 용도 |
| --- | --- |
| `GEDEvent_v26_1.csv` | 2016~2025년 국가 기반 분쟁 사건 추출 |
| `Actor_v26_1.csv` | 다음 단계에서 행위자 ID와 정식 명칭·다른 이름 연결 |

출처는 [UCDP 데이터 다운로드 센터](https://ucdp.uu.se/downloads/index.html)이며,
두 파일의 버전은 26.1이다. 컬럼 정의는 해당 데이터의 Codebook을 참고한다.
원본 CSV는 용량 때문에 GitHub에 포함하지 않는다. 새로 저장소를 내려받은 환경에서는
두 자료의 26.1 버전 CSV를 직접 다운로드해 압축을 풀고, 프로젝트 루트 기준
`data/ucdp/raw/GEDEvent_v26_1.csv`와 `data/ucdp/raw/Actor_v26_1.csv`에 배치한다.
다운로드 링크와 폴더 생성 방법은 [원본 다운로드 안내](../README.md#원본-다운로드-및-배치)를
참고한다. 이 폴더에서는 안내 문서인 `README.md`만 Git으로 관리한다.

## 실행

프로젝트 루트에서 기존 `streamlit` 환경으로 실행한다. pandas가 필요하다.

```bash
conda activate streamlit
python scripts/prepare_ucdp.py
```

기본 경로는 스크립트 위치를 기준으로 계산하므로 다른 작업 폴더에서도
스크립트의 절대 경로로 실행할 수 있다.

실제 다운로드 날짜를 알고 있다면 `--download-date YYYY-MM-DD`를 덧붙인다.
생략하면 실행 기록의 `download_date`는 `null`이다. 파일 수정일이나 실행일을
다운로드 날짜로 대신 기록하지 않는다.

## 추출 기준

- `2016 <= year <= 2025`와 `type_of_violence == 1`을 동시에 적용한다.
- 국가 기반 분쟁에는 정부와 반군 사이의 내전도 포함된다.
- `year` 기준으로 선택하며 `active_year`, 사망자 수, 좌표 유무로 추가 제외하지 않는다.
- 분쟁 코드 3열, 사건 식별 3열, 날짜 3열, 장소 7열, 행위자 4열 등
  `SELECTED_COLUMNS`에 정의한 총 20개 컬럼을 순서대로 저장한다.
- 식별자, 날짜·좌표 표기, 빈 값, 원본 행 순서를 보존한다.
- 기본 50,000행씩 읽어 전체 GED 원본을 메모리에 한꺼번에 올리지 않는다.
- Actor 파일은 2단계에서 가공하지 않고 아래 3단계에서 읽는다.

## 결과

| 경로 | 내용 |
| --- | --- |
| `data/ucdp/processed/ucdp_state_events_2016_2025.csv` | 조건에 맞는 사건과 선택한 20개 컬럼. UTF-8 BOM 포함 |
| `data/ucdp/processed/ucdp_state_events_2016_2025.metadata.json` | 버전, 원본·결과 SHA-256, 다운로드 날짜, 실행 시각, 필터, 컬럼, 행 수, 연도별 건수 |

실행 완료 시 두 결과 파일을 갱신한다. CSV를 읽거나 필터링하는 도중 실패하면
기존 결과를 유지한다. 원본은 변경하지 않는다.

입력이나 결과 폴더를 바꿀 때는 `--input`, `--output-dir`을 사용한다.
메모리를 더 적게 사용하려면 `--chunksize 10000`처럼 행 수를 줄인다.

## 검증

```bash
python -m unittest discover -s tests -p 'test_prepare_ucdp.py' -v
python -m ruff check scripts/prepare_ucdp.py tests/test_prepare_ucdp.py
python -m ruff format --check scripts/prepare_ucdp.py tests/test_prepare_ucdp.py
```

## 3단계: 분쟁 목록과 GDELT 검색 조건 생성

2단계의 JSON은 사건 목록이 아닌 실행 기록이다. 다음 코드는 JSON의
`output_file`을 JSON 파일이 있는 폴더 기준으로 해석해 추출 CSV를 읽고,
`output_sha256`과 행 수를 검증한 뒤 Actor 원본과 국가코드 매핑을 연결한다.

```bash
conda activate streamlit
python scripts/build_ucdp_search_inputs.py
```

기본 입력은 다음 세 가지이며, 공식 GDELT FIPS 코드 확인본도 검증에 사용한다.

- `data/ucdp/processed/ucdp_state_events_2016_2025.metadata.json` 및 여기에 기록된 CSV
- `data/ucdp/raw/Actor_v26_1.csv`
- `data/ucdp/references/country_code_mapping.csv`

다른 위치의 실행 기록을 사용하려면 아래처럼 지정한다. JSON이 가리키는 CSV도
함께 준비해야 한다. 나머지 기본 입력 경로는 스크립트 위치를 기준으로 계산한다.

```bash
python scripts/build_ucdp_search_inputs.py \
  --metadata /absolute/path/ucdp_state_events_2016_2025.metadata.json \
  --output-dir /absolute/path/processed
```

| 결과 파일 (`data/ucdp/processed/`) | 내용 |
| --- | --- |
| `conflicts.csv` | 내부 ID `ucdp_<UCDP 코드>`, 원문 분쟁명, 사건 수, 관측 기간, 지도 대표 좌표 |
| `actor_aliases.csv` | 행위자 ID별 원문 이름·다른 이름·검색용 파생 명칭, 출처와 검토 여부 |
| `event_search_conditions.csv` | 사건별 날짜·지역·좌표·행위자 쌍과 GDELT 위치 코드·검색 기간·공간 조건 |
| `gdelt_search_plan.json` | 입력 출처·해시·건수·검토 대상, 결과 파일 참조, 국가·월별 조회 계획 |

### 처리 기준

- 현재 Actor 원본은 CP1252로 읽는다. UTF-8 여부를 먼저 검사하며, 필요하면
  `--actor-encoding`으로 인코딩을 명시할 수 있다. 결과는 UTF-8로 저장한다.
- Actor 파일의 빈 ID 행은 제외한다. Actor에 없는 ID는 GED의 이름으로 남기고
  JSON의 `missing_actor_ids`와 CSV의 `actor_dataset_matched=False`로 표시한다.
- 변경명 목록을 쉼표로 나눈 후보, 짧은 약칭, 정부명에서 추출한 국가 이름에는
  `needs_review=True`를 표시한다. 원문 이름도 함께 보존한다.
- 과거 이름의 정확한 유효 기간은 이 사전으로 확정하지 않는다. 이름이 일치해도
  기사 날짜와 실제 행위자를 확인해야 한다. 이전·분리·동맹 조직은 동의어로 합치지 않는다.
- 대표 좌표는 유효한 사건 좌표 중 위치 정밀도, 같은 좌표의 사건 빈도,
  사건 ID 순으로 선택한다. 실제 사건 검색에는 사건별 좌표를 사용한다.
- `first_observed_date`·`last_observed_date`는 이번 추출 범위의 첫·마지막 관측일이다.
  분쟁 자체의 시작·종료일을 의미하지 않는다. 한국어 분쟁명·색상 등 UI 필드는 후속 작업이다.
- 검색 기간은 사건 시작 하루 전부터 종료 3일 후까지이며 2016~2025년 안으로 제한한다.
  검색 기간이 월 경계를 넘으면 해당 사건을 양쪽 월의 조회 계획에 포함한다.
- 위치 정밀도 1·2인 유효 좌표에는 각각 반경 25·50km를 제안하고,
  나머지는 행정구역 또는 국가 조건으로 표시한다. 이 수치는 프로젝트의 초기 검색 설정이다.
- 각 월의 `event_date_end_exclusive`와 `partition_end_exclusive`는 미포함 상한이다.
  적재 파티션은 월 종료 후 14일을 추가해 보도 지연을 일부 고려한다.
- 국가코드는 `ActionGeo_CountryCode`용이며 `|`로 구분한 여러 코드가 있을 수 있다.
  [국가코드 연결 안내](../references/README.md)를 참고한다.
- 조회 계획은 UCDP 사건 주변의 기사 후보 검색용이다. 사건이 없는 기간의 방공·전자전 등
  배경 보도는 후속 GKG·키워드 검색으로 보완한다. BigQuery 실행과 기사 수집은 아직 수행하지 않는다.
- 기존 앱의 `conflicts` 테이블에 바로 적재하는 파일이 아닌 3단계 중간 데이터다.
  ERD 변경과 DB 적재는 별도 단계다. 실행을 완료하면 동일 이름의 결과를 갱신한다.

```bash
python -m unittest discover -s tests -p 'test_build_ucdp_search_inputs.py' -v
```
