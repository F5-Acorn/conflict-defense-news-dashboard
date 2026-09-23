# 수집 범위와 국가코드 참조 자료

- `collection_scope.json`: 모든 국가 간 분쟁, 기사 발행일 2016~2026년, Candidate 공개분 목록과 GDELT 지연 조회 일수.
- `country_code_mapping.csv`: UCDP 국가 ID를 GDELT 발생 위치 FIPS 코드에 연결한다. 교전국의 지리 검색 범위와 사건 발생 지역을 모두 지원한다.
- `gdelt_fips_countries.tsv`: [GDELT 공식 Geo 국가코드](https://gdeltproject.org/data/lookups/FIPS.country.txt)의 2026-09-22 확인본.
- `gdelt_candidates.sql`: 검색 계획 한 배치를 실행할 파라미터 기반 GoogleSQL 예시. 실제 조회는 자동 실행하지 않는다.
- `conflicts_table.json`: 최종 DB 적재 대상 12개 분쟁의 고정 ID 목록, 한국어명·색상·국기와 지도 대표 좌표의 근거 사건. `python scripts/build_conflicts_table.py`가 이 설정과 가공 데이터를 결합해 `data/final/conflicts.csv`를 만든다. 검색용 15개 목록과 구분한다.

UCDP `country_id`와 ACD `gwno_a/gwno_b`는 Gleditsch–Ward 국가 코드이다.
행위자 ID인 `side_a_id/side_b_id`와 다르다. Actor `GWNOLoc`는 활동 국가 목록이므로
행위자의 국적을 추정하는 데 쓰지 않는다.

GDELT `ActionGeo_CountryCode`는 두 글자 FIPS 코드다. ISO 코드나
`Actor1CountryCode/Actor2CountryCode`의 코드와 혼용하지 않는다.
Israel 묶음에는 `IS/GZ/WE`, Morocco 묶음에는 `MO/WI`를 연결하여 후보 누락을 줄인다.
이처럼 넓게 얻은 지역 후보가 실제 해당 국가 간 분쟁 기사인지는 본문으로 확인한다.
매핑에 없는 교전국·발생국이 추가되면 생성기는 해당 ID를 알려주고 중단한다.

2026-09-23부터 미국(국가 ID `2`, FIPS `US`)을 교전국 조회용 매핑에 포함한다.
국가코드·행위자 검색어만으로 직접 교전 관계를 확정하지 않는다.

수집 범위 변경 후에는 `prepare_ucdp.py`와 `build_ucdp_search_inputs.py`를 순서대로
다시 실행한다. 출력 파일을 손으로 수정하면 해시 검증에서 거부된다.

공식 정의: [ACD](https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-261.pdf),
[GED](https://ucdp.uu.se/downloads/ged/ged261.pdf),
[Actor](https://ucdp.uu.se/downloads/actor/ucdp-actor-codebook-261.pdf).
