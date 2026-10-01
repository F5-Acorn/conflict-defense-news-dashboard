'''현재 스냅샷의 기사·범주 판정을 화면 필터에 맞춰 CSV로 내보낸다.'''

import pandas as pd

from data.constants import STATUS_LABELS

ARTICLE_CSV_COLUMNS = {
  'article_id': '기사 ID',
  'date': '보도일',
  'title': '제목',
  'conflict': '국가간 분쟁',
  'kind': '무기/기술',
  'category_id': '범주 ID',
  'category': '범주명',
  'usage_code': '사용 판정',
  'evidence_sentence': '근거 문장',
  'article_url': '원문 URL',
}


def article_csv(snapshot, conflict, start, end, kind):
  '''다운로드 클릭 시 전달받은 스냅샷과 필터만 사용하며 DB를 조회하지 않는다.'''
  key = ('article_csv', snapshot['revision'], conflict, start, end, kind)
  return snapshot['view_cache'].get(
    key, lambda: _article_csv(snapshot['reports'], conflict, start, end, kind)
  )


def _article_csv(reports, conflict, start, end, kind):
  selected = reports['date'].between(pd.Timestamp(start), pd.Timestamp(end))
  if conflict != '전체':
    selected &= reports['conflict'].eq(conflict)
  if kind != '전체':
    selected &= reports['kind'].eq(kind)
  rows = (
    reports.loc[selected, list(ARTICLE_CSV_COLUMNS)]
    .drop_duplicates(['article_id', 'category_id'])
    .sort_values(['date', 'article_id', 'category_id'], ascending=[False, True, True])
    .copy()
  )
  rows['article_id'] = rows['article_id'].astype(str)
  rows['date'] = rows['date'].dt.strftime('%Y-%m-%d')
  rows['usage_code'] = rows['usage_code'].map(STATUS_LABELS)
  return (
    rows.rename(columns=ARTICLE_CSV_COLUMNS)
    .fillna('')
    .to_csv(index=False)
    .encode('utf-8-sig')
  )
