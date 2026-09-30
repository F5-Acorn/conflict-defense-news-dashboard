# 지도 경계 데이터

`world_countries.geojson`은 Natural Earth의 1:110m 국가 경계 데이터를 화면용으로 가공한 파일입니다.

- 원본: [Natural Earth Vector — ne_110m_admin_0_countries.geojson](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson)
- 이용 조건: [Natural Earth Terms of Use](https://www.naturalearthdata.com/about/terms-of-use/) — Public Domain
- 가공: 국가명과 geometry만 유지, 좌표 소수 셋째 자리로 반올림, 지도 표시 범위 밖 남극 제외
- 수집일: 2026-09-21

지도 타일 API 키는 필요하지 않습니다. Folium의 Leaflet JS/CSS는 CDN에서 불러오므로 최초 지도 렌더링에는 인터넷 연결이 필요합니다.

## 한글 워드클라우드 글꼴

- 기본 파일: `fonts/Pretendard.ttf` (Pretendard v1.3.9 Regular, 굵기 400)
- 출처: [공식 v1.3.9 배포본](https://github.com/orioncactus/pretendard/releases/tag/v1.3.9), `Pretendard-1.3.9.zip` 안의 `public/static/alternative/Pretendard-Regular.ttf`
- 배포본의 TTF 내용은 그대로 유지하고 파일명만 `Pretendard.ttf`로 저장했습니다.
- 라이선스: SIL Open Font License 1.1. 원문은 `fonts/OFL-Pretendard.txt`에 포함합니다.
- 버전·출처·파일 크기·SHA-256: `fonts/pretendard-manifest.json`
- 용도: 무기·기술 워드클라우드를 서버에서 PNG로 생성합니다. AWS 배포에 파일을 함께 포함하면 서버와 접속 기기의 시스템 글꼴에 의존하지 않습니다.

## 공통 국기 이모지

- 자산: `flags/*.svg`, Twemoji v17.0.3 국기 23종 (원본 그대로 포함)
- 출처: [Twemoji](https://github.com/jdecked/twemoji/tree/v17.0.3)
- 그래픽 저작자: Twitter, Inc 및 Twemoji 기여자
- 라이선스: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), 원문은 `flags/LICENSE-GRAPHICS`
- 파일별 원본 URL과 SHA-256: `flags/manifest.json`
- SVG를 데이터 URI로 삽입하므로 국기 표시에 외부 연결과 OS 국기 글꼴이 필요하지 않습니다.
