'''기사 상세, 판정 분포, 분류 내보내기와 범주별 기사 집계. UI와 분리한다.'''

import re

import pandas as pd

from data.constants import KIND_LABELS, STATUS_LABELS, UsageCode

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


def classification_csv(tables, kind):
  result = pd.DataFrame(
    [
      (category, ', '.join(names))
      for category, names in classification_details(tables, kind).items()
    ],
    columns=['분류', '세부명칭'],
  )
  return result.to_csv(index=False).encode('utf-8-sig')


def with_month_changes(trend):
  '''첫 달은 비교하지 않고, 조회 범위 내 앞 월과의 증감을 계산한다.'''
  result = trend.sort_values(['category', 'month']).copy()
  result['previous'] = result.groupby('category')['count'].shift(1)
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


def article_details(reports, category_id, month, page=1, page_size=20):
  '''이미 페이지 조건으로 제한한 판정에서 점 하나의 사용 확인 기사를 조회한다.'''
  selected_month = pd.Period(month, freq='M')
  rows = (
    reports.loc[
      reports['usage_code'].eq(UsageCode.USED)
      & reports['category_id'].eq(category_id)
      & reports['date'].between(selected_month.start_time, selected_month.end_time)
    ]
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


def judgement_distribution(reports, selected):
  rows = reports.loc[reports['category'].isin(selected)]
  summary = rows.groupby(['category', 'usage_code']).size().rename('count')
  index = pd.MultiIndex.from_product(
    [sorted(set(selected)), list(STATUS_LABELS)], names=['category', 'usage_code']
  )
  result = summary.reindex(index, fill_value=0).reset_index()
  result['total'] = result.groupby('category')['count'].transform('sum')
  result['ratio'] = (
    result['count'].div(result['total'].replace(0, float('nan'))).fillna(0)
  )
  return result


def category_frequencies(reports):
  '''분쟁·기간·유형으로 필터링한 전체 범주의 사용 확인 기사를 중복 없이 센다.'''
  summary = (
    reports.loc[reports['usage_code'].eq(UsageCode.USED)]
    .groupby('category')['article_id']
    .nunique()
    .rename('count')
    .reset_index()
  )
  summary = summary.sort_values(['count', 'category'], ascending=[False, True])
  return dict(zip(summary['category'], summary['count'].astype(int)))


def valid_article_request(action, context, allowed_ids, start, end, kind):
  '''브라우저 요청이 현재 페이지의 범주·월에 해당하는지 확인한다.'''
  if (
    not isinstance(action, dict)
    or action.get('context') != context
    or action.get('kind') != kind
  ):
    return False
  if action.get('type') not in ('open_articles', 'article_page'):
    return False
  month = action.get('month')
  if not isinstance(month, str) or not re.fullmatch(r'\d{4}-\d{2}', month):
    return False
  if not 1 <= int(month[-2:]) <= 12 or not start.strftime(
    '%Y-%m'
  ) <= month <= end.strftime('%Y-%m'):
    return False
  return action.get('category_id') in allowed_ids
