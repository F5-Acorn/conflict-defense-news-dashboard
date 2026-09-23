# 지도 경계 데이터

`world_countries.geojson`은 Natural Earth의 1:110m 국가 경계 데이터를 화면용으로 가공한 파일입니다.

- 원본: [Natural Earth Vector — ne_110m_admin_0_countries.geojson](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson)
- 이용 조건: [Natural Earth Terms of Use](https://www.naturalearthdata.com/about/terms-of-use/) — Public Domain
- 가공: 국가명과 geometry만 유지, 좌표 소수 셋째 자리로 반올림, 지도 표시 범위 밖 남극 제외
- 수집일: 2026-09-21

지도 타일 API 키는 필요하지 않습니다. Folium의 Leaflet JS/CSS는 CDN에서 불러오므로 최초 지도 렌더링에는 인터넷 연결이 필요합니다.
