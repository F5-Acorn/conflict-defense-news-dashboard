# 국가 간 분쟁 보도 수집을 위한 UCDP 전처리

## 수집 목적과 범위

**모든 국가 간 분쟁에서 무기·기술이 사용되었다는 보도**를 2016~2026년
기사 발행일 기준으로 수집한다. 내부 분쟁, 비국가 분쟁, 일방적 폭력과
구매·개발·지원 계획만 다룬 보도는 최종 사용 보도 집계에서 제외한다.

UCDP는 대상 분쟁·교전 당사자와 참고 사건을 제공한다. GDELT 기사에 대응하는
개별 UCDP 사건이 있어야 한다는 조건은 적용하지 않는다. 무사망 요격·전자전 등도
해당 국가 간 분쟁의 사용 보도이면 포함할 수 있다.

수집 범위는 [`references/collection_scope.json`](references/collection_scope.json)에
둔다. 기본 요청 기간은 `2016-01-01`~`2026-12-31`이며, 실제 조회 상한은 실행 시
UTC 오늘 또는 `--as-of`와 요청 종료일 중 빠른 날이다. 미래 기사를 조회하지 않는다.
분쟁별 전체 기간을 검색하는 것은 모든 달에 그 분쟁이 진행됐다고 주장하는 것이 아니다.

현재 구현은 **UCDP 전처리·검색 계획 생성까지**이다. BigQuery 실행·본문 수집·기사
분쟁 판정·DB 적재는 후속 단계다. 앱은 기존 가상 데이터를 사용한다.

## 원본 다운로드 및 배치

[UCDP 공식 다운로드 센터](https://ucdp.uu.se/downloads/index.html)에서 다음 CSV를
다운로드한다. 원본은 Git에 포함하지 않으며 기존 파일을 가공 결과로 덮어쓰지 않는다.

| 자료 | 공식 다운로드 | `data/ucdp/raw/`의 파일명 |
| --- | --- | --- |
| GED Global 26.1 | [ZIP](https://ucdp.uu.se/downloads/ged/ged261-csv.zip) | `GEDEvent_v26_1.csv` |
| Armed Conflict Dataset 26.1 | [ZIP](https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-261-csv.zip) | `UcdpPrioConflict_v26_1.csv` |
| Actor 26.1 | [ZIP](https://ucdp.uu.se/downloads/actor/ucdp-actor-261-csv.zip) | `Actor_v26_1.csv` |
| Candidate 2026년 1~6월 | [CSV](https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_06.csv) | `GEDEvent_v26_01_26_06.csv` |
| Candidate 2026년 7월 | [CSV](https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_7.csv) | `GEDEvent_v26_0_7.csv` |
| Candidate 2026년 8월 | [CSV](https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_8.csv) | `GEDEvent_v26_0_8.csv` |

2026-09-23 확인 기준으로 연간 확정 자료는 2025년까지, Candidate 공개분은
2026년 8월까지다. 9월 이후의 신규 분쟁은 아직 UCDP 기반 목록에 없을 수 있다.
검색 기간을 연장하는 것만으로 신규 분쟁이 자동 발견되는 것은 아니다.
다음 공개분을 받으면 설정의 `candidate_sources`에 파일명·버전·실제 수록 기간을
추가하거나 누적 공개분으로 교체하고 두 스크립트를 다시 실행한다.

설정에 지정한 파일이 없으면 중단한다. 누락된 월을 0건으로 간주하지 않는다.
`candidate_coverage`에는 공개분의 기간, `candidate_missing_periods`에는 아직
확보하지 않은 기간을 기록한다. GED 사건 유무와 자료 수록 여부는 구분한다.

## 실행

```bash
conda activate streamlit
python scripts/prepare_ucdp.py
python scripts/build_ucdp_search_inputs.py
```

동일 시점으로 재현하려면 다음처럼 실행한다.

```bash
python scripts/prepare_ucdp.py --as-of 2026-09-23
python scripts/build_ucdp_search_inputs.py
```

[원본·명령 옵션 안내](raw/README.md)에 다른 입력·출력 경로 지정 방법을 정리했다.

## 국가 간 분쟁 선별 기준

`GED.type_of_violence=1`은 국가 기반 분쟁이며 내전도 포함한다.
`ACD.type_of_conflict=2`가 국가 간 분쟁이다. **GED 값을 2로 바꾸지 않는다.**

1. GED와 Candidate에서 분석 기간에 걸치는 사건을 읽는다.
2. 월 경계에서 중복된 Candidate 사건 ID는 수록 종료일이 늦은 공개분의 값을 채택한다.
   폭력 유형이 수정된 최신본도 반영하며, 원본 파일·버전·교체 건수를 기록한다.
3. `type_of_violence=1` 사건을 ACD의 **분쟁 ID + 사건 연도**로 확인한다.
4. 해당 연도 분쟁 유형이 2이고, GED 양측 행위자가 ACD 양측에 대응하면 확정 분류로 둔다.
   A/B 순서가 뒤바뀐 경우도 허용한다. 같은 국가 이름이 나온다는 이유로 연결하지 않는다.
5. 연간 행이 없지만 다른 연도의 같은 분쟁·당사자가 국가 간 분쟁이면 참고 사건으로 보존한다.
   `active_year=0`만으로 버리지 않는다. 해당 연도가 명시적으로 내전이면 제외한다.
6. 연간 분류가 없고 Actor의 양측 `Org=4`(국가 정부)인 새 쌍은 잠정 검색 후보로 둔다.
   이를 UCDP가 확정한 국가 간 분쟁으로 표시하지 않는다.
7. 행위자 미등록·동일 행위자 양측 등장·ACD 당사자 불일치는 별도 검토 목록에 남긴다.
   예를 들어 GED의 연합 행위자 ID와 ACD의 여러 개별 국가 ID가 다르면 자동으로 분해하지 않는다.

| 사건의 `classification_status` | 의미 | 검색 계획에서의 역할 |
| --- | --- | --- |
| `interstate_confirmed` | 같은 연도 ACD 분류와 양측 ID 확인 | 분쟁 검색의 근거 |
| `interstate_reference` | 다른 연도에서 분쟁과 당사자 확인 | 검토 표시를 유지한 참고 사건 |
| `state_pair_candidate` | 국가 행위자 쌍이나 연간 분류 없음 | 신규 분쟁 발견을 위한 잠정 검색 대상 |
| `review` | ID·당사자 대응을 확정하지 못함 | 별도 검토 CSV, 자동 검색 대상 추가에 사용하지 않음 |

분쟁 목록은 분석 기간의 ACD 국가 간 분쟁과 위 참고·잠정 사건에서 구성한다.
따라서 GED 사건이 0건인 ACD 국가 간 분쟁도 목록과 검색 배치를 갖는다.
검토 CSV의 항목을 확정하려면 원본·공식 당사자 자료를 확인하여 분류 규칙 또는
검증된 참조 자료를 보완한 후 재생성한다. 자동 판정 결과를 수동으로 덮어쓰지 않는다.

공식 정의: [GED](https://ucdp.uu.se/downloads/ged/ged261.pdf),
[ACD](https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-261.pdf),
[Actor](https://ucdp.uu.se/downloads/actor/ucdp-actor-codebook-261.pdf),
[Candidate](https://ucdp.uu.se/downloads/candidateged/ucdp-candidate-codebook1.5.pdf).

## 생성 파일과 역할

모든 결과는 `data/ucdp/processed/`에 저장한다.

| 파일 | 내용 |
| --- | --- |
| `ucdp_interstate_events.csv` | 대상·참고·잠정 사건. 기존 식별·날짜·위치·행위자 컬럼과 활동연도·원문 검토 상태·국가 행위자 코드·출처·분류·검토 필요 여부 |
| `ucdp_event_review_queue.csv` | 행위자 미등록 등 별도 검토가 필요한 사건. 제외 또는 확정 사건과 구분 |
| `ucdp_interstate_events.metadata.json` | 입력 해시·버전·수록 기간·설정 스냅샷·분류별 건수·대상 분쟁 목록·출력 해시 |
| `conflicts.csv` | 검색 대상 분쟁, 교전 당사자·교전국, 관측 발생 국가, 분석 기간, 분류 상태, 참고 사건 수 |
| `actor_aliases.csv` | 대상 분쟁 행위자의 정식 명칭·다른 이름·출처·검토 필요 여부. 사건이 없는 분쟁의 행위자도 포함 |
| `event_match_hints.csv` | 개별 사건의 날짜·반경·행정구역 참고값. 기사 채택의 필수 조건이 아님 |
| `gdelt_search_plan.json` | 분쟁별 전체 분석 기간을 한 번에 조회하는 검색 배치·입력 및 결과 해시 |

`conflicts.csv`의 `participant_country_ids`(교전국)와 `observed_country_ids`(발생국)는
분리한다. Actor의 `GWNOLoc`는 활동 국가 목록이므로 교전국 판정에 사용하지 않는다.
여러 교전국이 있는 분쟁은 행위자 쌍을 보존한다. 국가코드는
[참조 자료 안내](references/README.md)의 변환표로 연결한다.

## GDELT 조회와 기사 채택

### 공통 SQL에 분쟁별 조건 전달

수집 단위는 **분쟁 × 전체 분석 기간**이며, 분쟁마다 공통 SQL을 한 번 실행하도록
전체 기간의 시작일·종료일을 전달한다. 월 단위로 조회를 나누지 않는다.
분쟁별 SQL 파일을 따로 만들거나, SQL 결과를 해당 분쟁의 확정 기사로 취급하지 않는다.
각 분쟁의 조회 기간은 UCDP 사건의 최초·최종 날짜가 아닌 설정의 전체 분석 기간이다.
따라서 UCDP 최신 공개분 이후도 실행 시점까지 검색하되, 아직 목록에 없는 신규 분쟁의
누락 가능성은 별도로 관리한다.

1. `gdelt_search_plan.json`의 `batches`에서 분쟁별 배치를 선택한다. 각 배치는 UCDP 사건 없는 구간도 포함한 전체 분석 기간을 조회한다.
2. [`references/gdelt_candidates.sql`](references/gdelt_candidates.sql)의 GoogleSQL에
   아래 표의 이름·자료형으로 배치 값을 전달한다. 실행 전 dry run으로 조회 바이트를 확인하고
   `maximum_bytes_billed`를 설정한다. Events와 EventMentions는 `GLOBALEVENTID`로 연결한다.
3. 웹 기사(`MentionType=1`)의 URL과 사건·행위자·위치·품질 정보를 확보한다.
   `batch_id`와 `candidate_conflict_id`를 함께 저장하여 검색 시점의 후보 분쟁 연결을 보존한다.
4. URL 정규화로 본문 중복 수집을 줄이되, 기사–GDELT 사건–후보 분쟁 연결은 별도 보존한다.
5. 원문에서 실제 발행일·언어·제목·본문을 확보하고 해당 국가 간 분쟁의 직접 군사행동인지 검토한다.
6. 해당 행동에 연결되는 무기·기술, 사용 여부와 근거 문장을 추출한다.
7. 실제 발행일로 월을 정하고, **분쟁 × 발행월 × 무기·기술 분류별 고유 기사 ID**를 센다.

SQL에 전달하는 파라미터는 다음 8개이다. 이름은 `batches`의 필드명과 같다.

| 파라미터 이름 | BigQuery 자료형 |
| --- | --- |
| `mention_start`, `mention_end_exclusive` | 각각 `DATE` |
| `event_partition_start`, `event_partition_end_exclusive` | 각각 `DATE` |
| `gdelt_geo_country_codes`, `actor_terms` | 각각 `ARRAY<STRING>` |
| `candidate_conflict_id`, `batch_id` | 각각 `STRING` |

`bq` CLI나 BigQuery 클라이언트 라이브러리로 이름 있는 파라미터를 전달하고 GoogleSQL을
사용한다. BigQuery 콘솔의 쿼리 파라미터 설정은 배열 자료형을 지원하지 않으므로 이 SQL의
국가코드·행위자 배열을 해당 UI에 그대로 등록할 수는 없다.
[공식 파라미터 안내](https://docs.cloud.google.com/bigquery/docs/parameterized-queries)를 참고한다.

공통 SQL의 후보 조건은 다음과 같다. 기간 조건에 아래 조건을 `AND`로 결합한다.

```sql
AND (
  ActionGeo_CountryCode IN UNNEST(@gdelt_geo_country_codes)
  OR LOWER(Actor1Name) IN UNNEST(@actor_terms)
  OR LOWER(Actor2Name) IN UNNEST(@actor_terms)
)
```

이는 **기간 AND (관련 지역 OR 행위자 1 OR 행위자 2)**이며,
국가코드와 양쪽 행위자의 동시 일치를 요구하는 조건이 아니다.
국가코드는 발생 위치용 FIPS 코드, 행위자는 GDELT의 행위자 이름 필드에서 찾는 값이다.
기사 본문에 국가명이 있다는 사실만으로 SQL이 일치하는 것은 아니다.

전체 수집 시에는 모든 분쟁의 전체 기간 배치를 대상으로 하되, 같은 기간의 조회 결과와 과거 Events
인덱스는 재사용한다. 분쟁별 결과를 얻기 위해 같은 데이터를 매번 다시 스캔할 필요는 없다.
반환되는 후보가 줄어드는 것과 BigQuery 스캔 바이트가 줄어드는 것은 구분하여 확인한다.

### 후보 연결과 최종 판정

| 배치 값 | 용도 |
| --- | --- |
| `candidate_conflict_id` | 후보를 찾은 분쟁. 기사 본문 판정 전에는 확정 분쟁 ID가 아님 |
| `batch_id` | 분쟁 ID와 분석 시작일·종료일로 구성한 후보 조회 식별자 |
| `shared_period_query_id` | 여러 분쟁에서 공통 조회 결과를 재사용할 수 있는 전체 기간 식별자 |
| `article_published_start/end_exclusive` | 본문에서 확인한 실제 발행일에 적용할 전체 기간. 종료값은 분석 종료일 다음 날 |
| `mention_start/end_exclusive` | EventMentions 처리 시각·파티션 조회 범위. 보도 지연 14일을 고려하되 기준일 다음 날을 넘지 않음 |
| `event_partition_start/end_exclusive` | 과거 사건에 대한 새 보도를 연결할 Events 파티션 범위 |
| `gdelt_geo_country_codes` | 발생 위치 검색용 FIPS 코드 목록 |
| `actor_terms` | 행위자 정식 명칭·변형의 소문자 목록. 지리 범위 밖 후보를 보완 |
| `actor_pairs` | 본문에서 직접 교전 관계를 검토할 양측 행위자 쌍 |
| `ucdp_hint_event_count` | 전체 조회 기간에 참고할 사건 수. 0이어도 조회 배치 유지 |

최초 조회는 **관련 지역 또는 행위자** 조건으로 후보를 얻는다. 지역·국가명만으로는
국가 간 분쟁을 판별할 수 없으므로 내부 분쟁 등이 후보에 섞일 수 있다.
두 국가명이 함께 나온다는 이유만으로 채택하지 않으며, 무기 키워드·행동 코드·높은
추출 신뢰도만으로도 사용 보도를 확정하지 않는다. 잠정 후보는 분쟁 자체의 성격부터 검토한다.

예를 들어 A–B 분쟁을 조회할 때 A국 내전 기사도 지역 조건에 걸릴 수 있다. 또한 같은 기사가
A–B 분쟁과 A–C 분쟁의 검색 결과에 모두 나타날 수 있다. 검색 단계의 후보 연결을 출발점으로
본문의 당사자·직접 군사행동·무기 사용 근거를 확인하고, 각 후보를 채택·제외·확인 필요로
구분해야 한다. **후보 분쟁을 미리 연결하는 것이 후속 정제나 최종 분쟁 판정을 없애지는 않는다.**
사용 근거는 기사–분쟁–무기·기술 항목별로 보존하여 다른 분쟁의 문장을 잘못 집계하지 않는다.

사건 날짜 `SQLDATE`, GDELT 처리 시각 `MentionTimeDate`, 실제 기사 발행일은 서로 다르다.
SQLDATE를 기사 검색 기간으로 제한하면 과거 사건의 새 보도를 놓치므로 SQL 예시는 그런 제한을 두지 않는다.
원문 발행일을 확인하지 못한 기사는 확인 필요 상태로 남기고 월간 확정 지표에서 제외한다.
늦게 수집된 기사, GDELT Events에 없는 기사, 행위자·위치가 모두 누락된 기사는 이 경로에서
누락될 수 있다. GKG의 주제·기관·지명 후보나 분쟁별 원문 검색을 보완 경로로 관리한다.

### 비용과 저장

SQL은 수집 설계의 예시이며 자동 실행하지 않는다. 과거 Events를 매 배치마다 다시 읽으면
비용이 커지므로 필요한 Events 인덱스를 한 번 저장·갱신하고 재사용하는 구성이 적합하다.
같은 `shared_period_query_id`의 분쟁들은 전체 기간의 Mentions 조회 결과를 공유할 수 있다.
물리 조회를 합쳐도 각 후보 분쟁 연결과 적용 조건은 보존해야 한다.

실행 전 dry run으로 처리량을 확인하고 `maximum_bytes_billed`를 설정한다. `LIMIT`은
스캔 비용 상한이 아니다. 파티션·지연 기간과 원문 언어 범위를 기록한다.
관련 문서: [GDELT 조인](https://blog.gdeltproject.org/complex-queries-combining-events-eventmentions-and-gkg/),
[파티션 안내](https://blog.gdeltproject.org/announcing-partitioned-gdelt-bigquery-tables/).

후속 수집 결과는 `data/gdelt/`에 원본 후보, 실행 SQL·작업 ID·조회 바이트·실패 상태,
기사 목록, 사건–기사–분쟁 연결, 사용 판정과 근거를 나누어 저장한다.
기사 하나가 여러 사건·분쟁을 다룰 수 있으므로 연결을 삭제하지 않는다.
앱의 기존 단일 분쟁 기사 DB 명세에 실제 자료를 연결할 때에는 별도 연결 테이블 설계가 필요하다.

## 검증

```bash
python -m unittest tests.test_prepare_ucdp tests.test_build_ucdp_search_inputs -v
ruff check scripts tests
```

검증 항목은 내부 분쟁·다른 폭력 유형 제외, 연간 분류 누락 보존, 잠정 자료 중복·수정 반영,
사건 없는 분쟁과 월의 배치 생성, 미래 조회 제한, 교전국·발생국 구분, 원본·해시 보존이다.
