'''판정 원본 조인, 기사 상세·증감 계산과 분류 내보내기. UI와 분리한다.'''

import re
from datetime import date

import pandas as pd

from data.constants import KIND_LABELS, UsageCode

DICTIONARIES = {
  '무기': ('wp', 'sipri_dictionary', 'wp_name'),
  '기술': ('tech', 'nato_dictionary', 'tech_name'),
}


def build_reports(tables):
  reports = (
    tables['result']
    .merge(tables['articles'], on='article_id', validate='many_to_one')
    .merge(tables['categories'], on='category_id', validate='many_to_one')
    .merge(
      tables['conflicts'][['conflict_id', 'conflict_name_ko']],
      on='conflict_id',
      validate='many_to_one',
    )
    .rename(
      columns={
        'published_date': 'date',
        'conflict_name_ko': 'conflict',
        'category_name': 'category',
      }
    )
  )
  reports['date'] = pd.to_datetime(reports['date'])
  reports['kind'] = reports['kind'].map(KIND_LABELS)
  return reports


def classification_details(tables, kind):
  '''모든 범주에 사전 명칭을 연결한다. 미등록 범주도 빈 목록으로 남긴다.'''
  code, table, column = DICTIONARIES[kind]
  names = (
    tables[table]
    .groupby('category_id', sort=False)[column]
    .agg(lambda values: values.dropna().drop_duplicates().tolist())
  )
  categories = tables['categories'].loc[tables['categories']['kind'].eq(code)]
  return {
    row.category_name: names.get(row.category_id, [])
    for row in categories.itertuples(index=False)
  }


def classification_csv(tables, kind, *, details=None):
  if details is None:
    details = classification_details(tables, kind)
  result = pd.DataFrame(
    [(category, ', '.join(names)) for category, names in details.items()],
    columns=['분류', '세부명칭'],
  )
  return result.to_csv(index=False).encode('utf-8-sig')


def with_period_changes(trend, category_column='category_id', period_column='bucket'):
  '''조회 범위 내 앞 구간과 비교한다. 월별·일별 모두 빈 구간을 포함한다.'''
  result = trend.sort_values([category_column, period_column]).copy()
  result['previous'] = result.groupby(category_column)['count'].shift(1)
  result['delta'] = result['count'] - result['previous']
  result['change_text'] = result.apply(_change_text, axis=1)
  return result


def _change_text(row):
  if pd.isna(row['previous']):
    return '비교 대상 없음'
  delta = int(row['delta'])
  if row['previous'] == 0:
    return f'+{delta:,}건 · 신규' if delta else '0건 · 변동 없음'
  rate = delta / row['previous'] * 100
  return f'{delta:+,}건 ({rate:+.1f}%)'


def article_details(
  reports,
  category_id,
  start,
  end,
  page=1,
  page_size=20,
  conflict='전체',
):
  '''양 끝 날짜를 포함한 기간의 범주·분쟁별 사용 확인 기사를 조회한다.'''
  selected = (
    reports['usage_code'].eq(UsageCode.USED)
    & reports['category_id'].eq(category_id)
    & reports['date'].ge(pd.Timestamp(start))
    & reports['date'].lt(pd.Timestamp(end) + pd.Timedelta(days=1))
  )
  if conflict != '전체':
    selected &= reports['conflict'].eq(conflict)
  rows = (
    reports.loc[selected]
    .drop_duplicates('article_id')
    .sort_values(['date', 'article_id'], ascending=False)
  )
  total = len(rows)
  pages = max(1, (total + page_size - 1) // page_size)
  page = max(1, min(page, pages))
  items = rows.iloc[(page - 1) * page_size : page * page_size].copy()
  titles = items['title'].fillna('')
  items['title'] = titles.where(titles.str.strip().ne(''), '제목 없음')
  items['date'] = items['date'].dt.strftime('%Y.%m.%d')
  columns = [
    'article_id',
    'title',
    'date',
    'conflict',
    'evidence_sentence',
    'article_url',
  ]
  return {
    'total': total,
    'page': page,
    'pages': pages,
    'items': items[columns].fillna('').to_dict('records'),
  }


def valid_article_request(
  action, context, allowed_ids, start, end, kind, granularity='month'
):
  '''브라우저 요청이 현재 페이지의 범주·월 또는 날짜에 해당하는지 확인한다.'''
  if (
    not isinstance(action, dict)
    or granularity not in ('month', 'day')
    or action.get('context') != context
    or action.get('kind') != kind
    or action.get('granularity', 'month') != granularity
  ):
    return False
  if action.get('type') != 'open_articles':
    return False
  month = action.get('month')
  pattern = r'\d{4}-\d{2}' if granularity == 'month' else r'\d{4}-\d{2}-\d{2}'
  if not isinstance(month, str) or not re.fullmatch(pattern, month):
    return False
  try:
    date.fromisoformat(f'{month}-01' if granularity == 'month' else month)
  except ValueError:
    return False
  date_format = '%Y-%m' if granularity == 'month' else '%Y-%m-%d'
  if not start.strftime(date_format) <= month <= end.strftime(date_format):
    return False
  return action.get('category_id') in allowed_ids
