-- GoogleSQL. 검색 계획의 한 batch를 아래 이름의 쿼리 파라미터로 전달한다.
-- 각 batch는 한 분쟁의 전체 분석 기간을 월별 분할 없이 한 번에 조회한다.
-- DATE: mention_start, mention_end_exclusive, event_partition_start,
--       event_partition_end_exclusive
-- ARRAY<STRING>: gdelt_geo_country_codes, actor_terms
-- STRING: candidate_conflict_id, batch_id
-- 실행 전 dry run과 maximum_bytes_billed를 설정한다.
-- 여러 분쟁의 동일 기간은 조회 결과를 공유하고, 과거 Events 인덱스도 재사용한다.
WITH mentions AS (
  SELECT
    GLOBALEVENTID, MentionIdentifier, MentionSourceName, MentionTimeDate,
    Confidence, InRawText, SentenceID, MentionDocTranslationInfo
  FROM `gdelt-bq.gdeltv2.eventmentions_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP(@mention_start)
    AND _PARTITIONTIME < TIMESTAMP(@mention_end_exclusive)
    AND MentionTimeDate >= CAST(CONCAT(FORMAT_DATE('%Y%m%d', @mention_start), '000000') AS INT64)
    AND MentionTimeDate < CAST(CONCAT(FORMAT_DATE('%Y%m%d', @mention_end_exclusive), '000000') AS INT64)
    AND MentionType = 1
    AND REGEXP_CONTAINS(MentionIdentifier, r'^https?://')
), events AS (
  SELECT
    GLOBALEVENTID, SQLDATE, DATEADDED, Actor1Name, Actor2Name,
    Actor1CountryCode, Actor2CountryCode, EventCode, EventRootCode, QuadClass,
    ActionGeo_CountryCode, ActionGeo_FullName, ActionGeo_Type,
    ActionGeo_Lat, ActionGeo_Long
  FROM `gdelt-bq.gdeltv2.events_partitioned` AS e
  WHERE _PARTITIONTIME >= TIMESTAMP(@event_partition_start)
    AND _PARTITIONTIME < TIMESTAMP(@event_partition_end_exclusive)
    -- 지역은 후보 탐색 조건이다. 해당 국가의 내부 분쟁도 섞일 수 있다.
    -- 행위자 경로는 제3국·해역 또는 위치 누락 사건을 보완한다.
    AND (
      ActionGeo_CountryCode IN UNNEST(@gdelt_geo_country_codes)
      OR LOWER(Actor1Name) IN UNNEST(@actor_terms)
      OR LOWER(Actor2Name) IN UNNEST(@actor_terms)
    )
    -- SQLDATE를 기사 발행 기간으로 제한하지 않는다. 과거 사건의 새 보도도 후보이다.
)
SELECT DISTINCT
  @batch_id AS batch_id,
  @candidate_conflict_id AS candidate_conflict_id,
  e.*,
  m.MentionIdentifier AS source_url,
  m.MentionSourceName AS source_name,
  m.MentionTimeDate AS gdelt_mention_time,
  m.Confidence AS extraction_confidence,
  m.InRawText, m.SentenceID,
  m.MentionDocTranslationInfo AS translation_info
FROM events AS e
JOIN mentions AS m USING (GLOBALEVENTID);
-- 결과의 candidate_conflict_id는 확정 분쟁 분류가 아니다.
-- 원문에서 실제 발행일·분쟁 당사자·직접 군사행동·무기/기술 사용을 확인한다.
-- article_published_start <= 실제 발행일 < article_published_end_exclusive 적용.
-- 사건·기사 연결은 유지하고, 분쟁·발행월·범주별 고유 기사 ID를 집계한다.
