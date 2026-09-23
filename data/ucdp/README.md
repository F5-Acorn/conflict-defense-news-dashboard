# UCDP 데이터 파일 안내

UCDP 데이터는 원본(`raw`), 참조 자료(`references`), 가공 결과(`processed`)로
구분한다. 가공 결과는 처리 단계와 관계없이 `processed` 바로 아래에 저장한다.

CSV에는 표준 주석 문법이 없어 설명 행을 넣으면 Pandas·Excel 등의 도구가
헤더나 데이터로 해석할 수 있다. 원본과 기존 CSV 형식·인코딩을 유지하고,
파일별 한글 설명은 이 문서와 생성 스크립트의 주석으로 제공한다.

## 원본 다운로드 및 배치

UCDP 원본 CSV는 용량 때문에 GitHub에 포함하지 않는다. 저장소를 복제하거나
ZIP으로 내려받은 뒤, [UCDP 공식 다운로드 센터](https://ucdp.uu.se/downloads/index.html)에서
아래 두 자료의 **26.1 버전 CSV**를 직접 다운로드한다.
현재 처리 코드와 국가코드 매핑은 26.1을 기준으로 하므로 같은 버전을 사용한다.

| 자료 | 다운로드 | 압축 해제 후 저장할 경로 (프로젝트 루트 기준) |
| --- | --- | --- |
| UCDP GED Global 26.1 | [GED CSV ZIP](https://ucdp.uu.se/downloads/ged/ged261-csv.zip) | `data/ucdp/raw/GEDEvent_v26_1.csv` |
| UCDP Actor Dataset 26.1 | [Actor CSV ZIP](https://ucdp.uu.se/downloads/actor/ucdp-actor-261-csv.zip) | `data/ucdp/raw/Actor_v26_1.csv` |

프로젝트 루트에서 저장 폴더를 준비한다.

```bash
mkdir -p data/ucdp/raw
```

다운로드한 ZIP의 압축을 풀고 CSV 두 개를 위 경로에 복사한다. 압축 해제 시 별도
폴더가 생겼더라도 CSV는 `raw` 바로 아래에 넣고, 파일명과 원본 내용·인코딩을 유지한다.

```text
data/ucdp/raw/
├── README.md
├── GEDEvent_v26_1.csv
└── Actor_v26_1.csv
```

`.gitignore`에서 `data/ucdp/raw/`의 원본 파일과 하위 폴더를 제외하며,
안내 문서인 `README.md`만 Git으로 관리한다.
배치가 끝나면 아래 [실행 순서](#실행-순서)에 따라 두 가공 스크립트를 실행한다.

## CSV별 역할

| 파일 | 역할 | 사용 단계 |
| --- | --- | --- |
| [`raw/GEDEvent_v26_1.csv`](raw/GEDEvent_v26_1.csv) | 분쟁 사건의 날짜·위치·분쟁·교전 당사자 등을 담은 GED 26.1 원본. 기간·폭력 유형 필터링의 기준 | `prepare_ucdp.py` 입력 |
| [`raw/Actor_v26_1.csv`](raw/Actor_v26_1.csv) | 행위자 ID별 정식 명칭·원어명·영문명·변경명을 담은 Actor 26.1 원본 | `build_ucdp_search_inputs.py`에서 행위자 검색어 생성 |
| [`references/country_code_mapping.csv`](references/country_code_mapping.csv) | UCDP 발생 국가 ID를 GDELT 위치 검색용 FIPS 국가코드에 연결하는 프로젝트 매핑 | 사건별 국가 검색 조건 생성 |
| [`processed/ucdp_state_events_2016_2025.csv`](processed/ucdp_state_events_2016_2025.csv) | 2016~2025년 국가 기반 분쟁(`type_of_violence=1`) 사건만 선택한 20개 컬럼의 추출 결과. 사건별 한 행 | 분쟁 목록·행위자 검색어·사건별 검색 조건 생성의 공통 입력 |
| [`processed/conflicts.csv`](processed/conflicts.csv) | 분쟁별 ID·원문명·사건 수·첫/마지막 관측일·지도 대표 좌표. 분쟁별 한 행 | 분쟁 목록 확인과 지도용 대표 정보 준비 |
| [`processed/actor_aliases.csv`](processed/actor_aliases.csv) | 추출 사건에 등장한 행위자의 기본 명칭·검색용 다른 이름·출처·검토 필요 여부·Actor 연결 여부 | GDELT 기사 후보의 행위자 명칭 검색과 검토 |
| [`processed/event_search_conditions.csv`](processed/event_search_conditions.csv) | 추출 사건에 검색 기간·GDELT 국가코드·공간 검색 방식·반경을 추가한 검색 조건. 사건별 한 행 | 기사 후보 수집 조건 구성과 국가·월별 조회 계획 생성 |

`conflicts.csv`의 관측 기간은 이번 추출 범위의 첫·마지막 사건 날짜이며,
분쟁 자체의 시작·종료일을 의미하지 않는다. 가공 CSV는 후속 분석용 중간 자료이며
현재 앱의 샘플 테이블이나 DB에 자동으로 적재되지 않는다.

## 함께 사용하는 파일

| 파일 | 역할 |
| --- | --- |
| [`references/gdelt_fips_countries.tsv`](references/gdelt_fips_countries.tsv) | GDELT 공식 위치 국가코드 확인본. 매핑 CSV의 FIPS 코드 유효성 검증 |
| [`processed/ucdp_state_events_2016_2025.metadata.json`](processed/ucdp_state_events_2016_2025.metadata.json) | GED 원본·추출 CSV의 경로·해시, 필터·컬럼·건수·처리 시각 기록. 추출 CSV는 이 JSON과 같은 폴더에서 조회 |
| [`processed/gdelt_search_plan.json`](processed/gdelt_search_plan.json) | 입력 파일의 경로·해시, 결과 CSV의 파일명·해시·건수, 국가·월별 GDELT 조회 계획. 결과 CSV는 이 JSON과 같은 폴더에 보관 |

## 실행 순서

프로젝트 루트에서 실행한다.

```bash
conda activate streamlit
python scripts/prepare_ucdp.py
python scripts/build_ucdp_search_inputs.py
```

두 스크립트의 기본 출력 폴더는 모두 `data/ucdp/processed/`다.
자세한 옵션과 검증 방법은 [원본·가공 안내](raw/README.md),
국가코드의 의미는 [국가코드 연결 안내](references/README.md)를 참고한다.

## UCDP 데이터를 활용한 GDELT 기사 수집

이 프로젝트에서는 UCDP 사건의 **기간·발생 국가·위치·교전 당사자**를 이용해
GDELT에서 관련 기사 후보를 찾는다. UCDP 사건 ID와 GDELT의 `GLOBALEVENTID`는
서로 다른 식별자이므로 직접 조인하지 않고, 검색 조건과 기사 내용으로 연결한다.

아래는 2016~2025년 자료를 GDELT 2.0 BigQuery 공개 테이블에서 수집하는 절차다.
현재 스크립트는 검색 입력 파일 생성까지 수행하며, BigQuery 조회·기사 본문 수집·DB
적재는 아직 구현되지 않았다. 아래 SQL은 사용자가 BigQuery에서 실행할 예시다.

### 1. 검색 입력과 GDELT 테이블 연결

| UCDP 가공 파일 | 수집 시 사용하는 값과 역할 |
| --- | --- |
| `processed/gdelt_search_plan.json` | `batches`의 국가·월별 조회 범위로 BigQuery 작업을 나누고, `batch_id`로 실행·재시도·저장 결과를 관리 |
| `processed/event_search_conditions.csv` | 배치 조회 후 각 UCDP 사건의 실제 검색 기간·공간 조건·교전 당사자를 대조 |
| `processed/actor_aliases.csv` | `side_a_new_id`, `side_b_new_id`를 `actor_id`에 연결해 기사에서 확인할 행위자 명칭 후보 구성 |
| `processed/conflicts.csv` | 일치 후보 사건의 `conflict_id`를 분쟁명에 연결. 대표 좌표는 개별 사건의 검색 좌표로 사용하지 않음 |

GDELT에서는 다음 테이블을 사용한다.

| BigQuery 테이블 | 역할과 연결 키 |
| --- | --- |
| `gdelt-bq.gdeltv2.events_partitioned` | 사건 날짜(`SQLDATE`), 발생 위치(`ActionGeo_*`), 행위자(`Actor1Name`, `Actor2Name`), 행동 코드(`EventCode`)로 후보 사건 조회 |
| `gdelt-bq.gdeltv2.eventmentions_partitioned` | `GLOBALEVENTID`로 Events와 연결하고, `MentionType=1`인 웹 기사의 `MentionIdentifier` URL 수집 |
| `gdelt-bq.gdeltv2.gkg_partitioned` | 필요하면 `DocumentIdentifier`를 기사 URL에 연결해 주제·인물·기관 등의 메타데이터 보강 |

Events의 `SOURCEURL`은 최초 발견 보도에 해당하므로, 같은 사건을 다룬 여러 매체의
기사를 모을 때는 EventMentions를 함께 조회한다.
테이블 연결 방식은 [GDELT 공식 조인 예시](https://blog.gdeltproject.org/complex-queries-combining-events-eventmentions-and-gkg/),
필드 의미는 [GDELT 2.0 Event 코드북](https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf)을 참고한다.

### 2. 국가·월별 배치 선택

프로젝트 루트에서 다음 코드를 실행하면 첫 번째 배치의 조회 조건을 확인할 수 있다.
전체 수집을 구현할 때는 `plan['batches']`를 순회하되, 먼저 한 배치로 결과를 확인한다.

```python
import json
from pathlib import Path

plan = json.loads(
    Path('data/ucdp/processed/gdelt_search_plan.json').read_text(encoding='utf-8')
)
batch = plan['batches'][0]
keys = [
    'batch_id', 'country_name', 'gdelt_geo_country_codes',
    'event_date_start', 'event_date_end_exclusive',
    'partition_start', 'partition_end_exclusive',
]
print(json.dumps({key: batch[key] for key in keys}, ensure_ascii=False, indent=2))
```

| 배치 값 | SQL에 적용하는 방법 |
| --- | --- |
| `gdelt_geo_country_codes` | `ActionGeo_CountryCode IN (...)`에 모든 코드 적용. 배열의 코드 중 하나라도 일치하면 포함 |
| `event_date_start` | `YYYYMMDD` 정수로 바꿔 `SQLDATE >= 시작일`에 사용 |
| `event_date_end_exclusive` | `YYYYMMDD` 정수로 바꿔 `SQLDATE < 종료일`에 사용 |
| `partition_start` | 조회할 두 테이블의 `_PARTITIONTIME >= TIMESTAMP(시작일)`에 사용 |
| `partition_end_exclusive` | 조회할 두 테이블의 `_PARTITIONTIME < TIMESTAMP(종료일)`에 사용 |
| `ucdp_event_ids` | 조회 후 사건별 대조에 사용할 `event_search_conditions.csv`의 `id` 목록 |

`*_end_exclusive`는 해당 날짜를 포함하지 않는다. 사건별 CSV의
`search_end_date`는 포함 상한이므로 적용 방식이 다르다.
현재 생성기는 보도 지연을 일부 고려해 파티션 종료일을 다음 달 1일에서 14일
뒤로 잡는다. 이 기간 이후에 수록된 기사나 뒤늦은 회고 보도까지 포함하는 설정은 아니다.
GDELT 위치 국가코드는 FIPS 코드이며, ISO 코드나 `Actor1CountryCode`의 국가코드로
대체하지 않는다.

### 3. BigQuery에서 기사 후보 조회

Google Cloud 프로젝트의 BigQuery SQL 편집기에서 GoogleSQL을 사용한다.
공개 프로젝트 `gdelt-bq`의 `gdeltv2` 데이터셋을 찾아 테이블 스키마와 데이터 위치를
확인하고, 쿼리 실행 위치와 결과를 저장할 데이터셋 위치를 맞춘다.

아래는 현재 검색 계획의 첫 배치인 **`41_202402` — Haiti, 2024년 2월** 예시다.
다른 배치를 조회할 때는 배치 ID, 국가코드, 사건 날짜 범위, 두 테이블의 파티션 범위,
`MentionTimeDate` 범위를 함께 교체한다. 날짜·시간은 UTC 기준으로 취급한다.

```sql
-- GoogleSQL: 국가·월 단위의 기사 후보 조회
WITH candidate_events AS (
  SELECT
    GLOBALEVENTID, SQLDATE, DATEADDED,
    Actor1Name, Actor2Name, EventCode,
    ActionGeo_CountryCode, ActionGeo_FullName, ActionGeo_Type,
    ActionGeo_Lat, ActionGeo_Long
  FROM `gdelt-bq.gdeltv2.events_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP('2024-02-01')
    AND _PARTITIONTIME < TIMESTAMP('2024-03-15')
    AND SQLDATE >= 20240201
    AND SQLDATE < 20240301
    AND ActionGeo_CountryCode IN ('HA')
), candidate_mentions AS (
  SELECT
    GLOBALEVENTID, MentionIdentifier, MentionSourceName,
    MentionTimeDate, Confidence, MentionDocTranslationInfo
  FROM `gdelt-bq.gdeltv2.eventmentions_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP('2024-02-01')
    AND _PARTITIONTIME < TIMESTAMP('2024-03-15')
    AND MentionTimeDate >= 20240201000000
    AND MentionTimeDate < 20240315000000
    AND MentionType = 1
    AND MentionIdentifier IS NOT NULL
    AND MentionIdentifier != ''
)
SELECT DISTINCT
  '41_202402' AS batch_id,
  e.GLOBALEVENTID AS gdelt_event_id,
  e.SQLDATE AS gdelt_event_date,
  e.DATEADDED AS gdelt_added_at,
  e.Actor1Name, e.Actor2Name, e.EventCode,
  e.ActionGeo_CountryCode, e.ActionGeo_FullName, e.ActionGeo_Type,
  e.ActionGeo_Lat, e.ActionGeo_Long,
  m.MentionIdentifier AS source_url,
  m.MentionSourceName AS source_name,
  m.MentionTimeDate AS gdelt_mention_time,
  m.Confidence AS extraction_confidence,
  m.MentionDocTranslationInfo AS translation_info
FROM candidate_events AS e
JOIN candidate_mentions AS m USING (GLOBALEVENTID);
```

이 SQL의 결과는 GDELT 사건과 기사의 조합이며, UCDP 사건과의 일치는 아직 확정되지 않는다.
`SELECT DISTINCT`를 적용해도 같은 URL의 다른 사건·시각 행은 남으므로,
결과 행 수를 기사 수로 바로 집계하지 않는다.

각 테이블에 `_PARTITIONTIME` 조건을 적용해 읽는 날짜 범위를 제한한다.
실행 전 편집기의 예상 처리량 또는 dry run으로 조회량을 확인하고,
쿼리 설정의 `Maximum bytes billed`로 허용 조회량을 지정한다.
`LIMIT`만 추가하는 방식은 스캔 비용 제한을 보장하지 않는다.
[GDELT 파티션 테이블 안내](https://blog.gdeltproject.org/announcing-partitioned-gdelt-bigquery-tables/)와
[BigQuery 조회량·비용 제어](https://docs.cloud.google.com/bigquery/docs/best-practices-costs)를 참고한다.

### 4. UCDP 사건별로 관련성 대조

배치의 `ucdp_event_ids`에 포함된 사건만 `event_search_conditions.csv`에서 선택한 뒤,
조회 결과를 다음 순서로 대조한다. 배치의 `conflict_ids` 전체를 모든 기사에 일괄
부여하지 않고, 일치 후보인 개별 UCDP 사건을 거쳐 분쟁에 연결한다.

1. **날짜**: `gdelt_event_date`를 날짜로 변환해 사건의
   `search_start_date <= 날짜 <= search_end_date` 범위와 비교한다.
2. **국가**: 사건의 `gdelt_geo_country_codes`를 `|`로 분리하고
   `ActionGeo_CountryCode`가 그중 하나인지 확인한다.
3. **위치**: `spatial_match_mode=radius`이면 사건 좌표와 GDELT 좌표의 거리를
   `radius_km`와 비교한다. 좌표가 비어 있거나 GDELT 위치가 국가·행정구역 중심점인
   경우에는 정밀 좌표로 간주하지 않고 검토 대상으로 남긴다.
   `administrative_area`는 `adm_1`, `adm_2`와 기사 지명을 확인하며,
   `country`는 국가 단위의 넓은 후보로 관리한다. 행정구역명·코드는 별도 정규화 없이
   같은 값이라고 가정하지 않는다.
4. **행위자**: 사건 양측 ID에 해당하는 `actor_aliases.csv`의 검색 명칭을
   `Actor1Name`, `Actor2Name`과 기사 제목·본문에서 확인한다.
   UCDP의 A/B와 GDELT의 Actor1/Actor2 순서는 같다고 가정하지 않는다.
   `needs_review=True`인 약칭·변경명과 한쪽 행위자가 누락된 기사는 검토 대상으로 남긴다.
5. **내용**: 실제 같은 사건·분쟁을 다루는지 확인한 뒤 무기·방산기술과 사용 근거
   문장을 추출한다. 특정 `EventCode`나 높은 `extraction_confidence`만으로
   무기 사용을 확정하지 않는다.

현재 검색 기간은 사건 시작 하루 전부터 종료 3일 후까지이며, 반경 25·50km는
프로젝트의 초기 검색값이다. 표본 기사를 검토해 조건을 조정한다.
행위자 이름의 완전 일치를 최초 SQL의 필수 조건으로 걸면 표기 차이·생략으로
후보가 빠질 수 있으므로, 예시 SQL은 국가·기간으로 먼저 수집하고 후속 검토에 사용한다.

### 5. 결과 저장·기사 중복 제거·본문 수집

수집 결과는 UCDP 원본과 구분해 별도의 `data/gdelt/` 아래에 저장한다.
아래는 향후 수집기를 구현할 때 사용할 권장 경로이며, 현재 생성된 파일은 아니다.

| 권장 경로 | 저장 내용 |
| --- | --- |
| `data/gdelt/raw/{batch_id}_mentions.csv` | BigQuery에서 받은 배치별 사건·기사 후보 결과 |
| `data/gdelt/references/{batch_id}.sql` | 실행한 SQL과 적용 조건 |
| `data/gdelt/references/{batch_id}.metadata.json` | 배치 ID, UCDP 검색 계획의 SHA-256, 실행 시각, BigQuery 작업 ID, 처리 바이트, 행 수, 결과 해시 |
| `data/gdelt/processed/articles.csv` | 정규화한 URL별 기사 ID·원래 URL·매체·제목·본문·발행일·언어·수집 상태 |
| `data/gdelt/processed/article_event_links.csv` | 기사 ID·GDELT 사건 ID·UCDP 사건 ID·분쟁 ID·관련성 판정·판정 근거 연결 |

BigQuery 결과는 CSV로 내려받거나 결과 테이블에 저장해 내보낸다. 배치별 CSV를
합친 뒤 URL을 정규화해 기사 단위 중복을 제거하되, 같은 기사가 여러 사건·분쟁에
연결된 관계는 `article_event_links.csv`에 별도로 유지한다. 본문이 같은 재게시
기사의 대표본 선정은 URL 중복 제거 다음 단계에서 처리한다.

위 SQL은 기사 URL과 사건 메타데이터를 반환한다. 제목·본문·실제 발행일은 해당
URL의 기사에서 별도로 수집하고, 원문을 확보하지 못하면 실패 상태와 원인을 기록한다.
`gdelt_event_date`는 사건 날짜이고 `gdelt_mention_time`은 GDELT 처리 시각이므로,
둘 중 하나를 실제 기사 발행일로 대신 저장하지 않는다.

영문 기사만 분석할 때도 원문 언어를 확인한다. `translation_info`가 비어 있는 것은
원래 영문이거나 사람이 영어로 번역해 제공한 경우 등을 포함하므로, 빈 값만으로
원문 언어를 확정하지 않는다. 날짜·번역 정보의 의미는
[GDELT 2.0 Event 코드북](https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf)에 정의되어 있다.

### 6. 수집 범위 보완과 완료 확인

현재 계획은 UCDP에 기록된 국가 기반 분쟁 사건 주변을 찾는 방식이다.
UCDP 사건이 없는 기간의 방공·전자전·기술 운용 보도와 GDELT Events에 잡히지 않은
기사를 보완하려면, 별도의 분쟁별 기간·지역·행위자·무기/기술 명칭 조건으로 GKG의
`DocumentIdentifier` 후보를 조회하고 원문을 검토한다. 이 보완 수집은 현재 배치
생성기에 포함되지 않으므로 조건과 수집 출처를 따로 기록한다.

수집 완료 시 배치별 성공·실패·0건을 구분하고, 실패 배치만 재실행할 수 있게 한다.
최종적으로 후보 URL 수, 중복 제거 기사 수, 본문 확보 수, 분쟁 연결 수를 확인한다.
대시보드의 사용 보도 수는 관련성·무기 사용 판정을 통과한 기사 ID를 중복 없이
집계하며, GDELT 조회 행 수나 UCDP 사건 수를 기사 수로 사용하지 않는다.
