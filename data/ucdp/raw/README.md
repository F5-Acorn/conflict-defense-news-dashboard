# 원본과 전처리 실행 안내

원본 CSV 6개와 다운로드 링크는 [전체 안내](../README.md#원본-다운로드-및-배치)에 있다.
GED·ACD·Actor의 연간 버전은 모두 26.1로 맞춘다. Candidate는
[수집 설정](../references/collection_scope.json)에 지정한 공개분을 사용한다.
원본은 Git 제외 대상이며 덮어쓰거나 정규화하지 않는다.

## 1. 원본 배치

```text
data/ucdp/raw/
  GEDEvent_v26_1.csv
  UcdpPrioConflict_v26_1.csv
  Actor_v26_1.csv
  GEDEvent_v26_01_26_06.csv
  GEDEvent_v26_0_7.csv
  GEDEvent_v26_0_8.csv
```

Candidate 월간 자료는 누적 자료가 아니므로 8월 파일 하나로 1~8월을 대체하지 않는다.
상반기 누적본과 7·8월 자료를 함께 사용한다. 파일 내부 사건 ID 중복은 오류로 처리하고,
서로 다른 공개분에 반복된 ID는 최신 수록 종료일의 자료로 갱신한다.

## 2. 국가 간 분쟁 사건 추출

```bash
python scripts/prepare_ucdp.py --as-of 2026-09-23
```

- `--input`: GED 경로. 기본 `data/ucdp/raw/GEDEvent_v26_1.csv`.
- `--acd`: 연간 분쟁 분류 CSV 경로.
- `--actors`: 국가 정부 판별용 Actor CSV 경로.
- `--scope`: 요청 기간·Candidate 목록 JSON 경로.
- `--candidate-dir`: Candidate 원본 폴더. 기본 GED와 같은 폴더.
- `--output-dir`: 결과 폴더. 기본 `data/ucdp/processed`.
- `--as-of`: UTC 기준일. 생략하면 실행일. 요청 종료일 이후로 확장하지 않는다.
- `--chunksize`: GED를 읽을 행 단위. 기본 50,000.
- `--download-date`: 실제 원본 다운로드 날짜를 알고 있을 때만 지정. 기본 미상.

추출 컬럼에는 사건·분쟁·행위자 ID, 날짜·위치·정확도, `active_year`, `code_status`,
`gwnoa/gwnob`, 출처 파일·버전, 분류 상태·근거·검토 여부를 보존한다.
사망자 통계를 계산하는 단계가 아니므로 사망자 수는 필수 컬럼에 포함하지 않는다.

`interstate_confirmed`는 같은 연도 ACD 분류와 당사자를 확인한 사건이다.
`interstate_reference`와 `state_pair_candidate`는 검토 표시를 유지한다.
알 수 없는 행위자·연합 ID 등은 `ucdp_event_review_queue.csv`로 분리하며 조용히 삭제하지 않는다.
상세 선별 기준과 공개분 공백 처리는 [전체 안내](../README.md#국가-간-분쟁-선별-기준)에 있다.

## 3. 분쟁별 전체 기간 기사 검색 계획

```bash
python scripts/build_ucdp_search_inputs.py
```

```bash
python scripts/build_ucdp_search_inputs.py \
  --metadata /absolute/path/ucdp_interstate_events.metadata.json \
  --actors /absolute/path/Actor_v26_1.csv \
  --country-codes /absolute/path/country_code_mapping.csv \
  --output-dir /absolute/path/processed
```

추출 CSV 및 Actor의 SHA-256을 확인한 후 분쟁 목록·명칭·사건 참고값·전체 기간 배치를 만든다.
Actor 인코딩은 UTF-8 검사 후 CP1252를 사용하며 `--actor-encoding`으로 지정할 수 있다.
입력·출력 경로 충돌이나 필수값 누락은 기존 결과 교체 전에 실패한다.

분쟁마다 분석 시작일부터 종료일까지 한 번에 조회한다. 사건 날짜 ±며칠·25/50km 반경은
`event_match_hints.csv`의 참고값이며 GDELT 기사 제외 기준이 아니다.
기사의 실제 발행일은 원문 수집 후 확인한다.

## 기존 결과에서 전환

이전 전체 국가 기반 분쟁 추출 파일과 사건 필수 대조 파일은 새 파이프라인에서 읽지 않는다.
새 메타데이터는 `schema_version=2`이며 이전 스키마는 검색 계획 생성기에서 거부한다.
두 단계가 성공한 뒤 이전 `ucdp_state_events_2016_2025.csv`, 같은 이름의 metadata JSON,
`event_search_conditions.csv`는 결과 폴더에서 제거한다. 원본 CSV는 그대로 보존한다.

```bash
python -m unittest tests.test_prepare_ucdp tests.test_build_ucdp_search_inputs -v
```
