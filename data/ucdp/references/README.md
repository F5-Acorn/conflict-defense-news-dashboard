# UCDP와 GDELT의 발생 위치 코드 연결

- `gdelt_fips_countries.tsv`: [GDELT 공식 Geo 국가코드](https://gdeltproject.org/data/lookups/FIPS.country.txt)의 2026-09-22 확인본.
- `country_code_mapping.csv`: GED 26.1의 2016~2025년 국가 기반 분쟁에 등장하는 68개 발생 국가를 위 코드표에 연결한 프로젝트 매핑.

UCDP `country_id`는 Gleditsch–Ward 숫자 코드이고, GDELT의
`ActionGeo_CountryCode`는 두 글자 FIPS 코드다. 이 매핑은 발생 위치 검색용이며
세 글자 `Actor1CountryCode`·`Actor2CountryCode`에 넣으면 안 된다.
Actor 자료의 `GWNOLoc` 역시 활동 국가 목록이므로 행위자의 국적으로 사용하지 않는다.

UCDP의 Israel 묶음에는 Gaza Strip·West Bank 사건이 있고, Morocco 묶음에는
서사하라 지역 사건이 있다. 후보 누락을 줄이도록 각각 `IS/GZ/WE`, `MO/WI`를
검색 코드로 등록했다. 이후 개별 사건의 날짜·행정구역·좌표·행위자로 관련성을 확인한다.
매핑되지 않은 국가가 추가되면 스크립트는 해당 ID를 알려주고 중단한다.

관련 문서:

- [GDELT 코드 체계 안내](https://gdeltproject.org/data.html)
- [UCDP GED 코드북](https://ucdp.uu.se/downloads/ged/ged261.pdf)
- [UCDP Actor 코드북](https://ucdp.uu.se/downloads/actor/ucdp-actor-codebook-261.pdf)
