'''Streamlit에 의존하지 않는 기간 필터 및 집계 함수.'''

import pandas as pd

from data.constants import KIND_LABELS, UsageCode


def build_dashboard_data(tables, reports):
  '''조인된 판정에서 article_id를 중복 제거해 화면용 일별 지표를 만든다.

  결과가 없는 수집 기사는 분석 지표에서 제외한다. 사용 건수는 내부 코드 0만 센다.
  전체는 무기·기술의 합이 아닌 기사 집합의 합집합이며, 범주별 건수는 중복될 수 있다.
  '''
  articles = tables['articles']
  categories = tables['categories']
  conflicts = tables['conflicts']
  reports = reports.copy()
  reports['is_usage'] = reports['usage_code'].eq(UsageCode.USED)

  # 한 기사에 여러 범주가 있어도 유형별·전체 기사 지표에서는 한 번만 센다.
  by_kind = reports.groupby(['date', 'conflict', 'kind', 'article_id'], as_index=False)[
    'is_usage'
  ].max()
  overall = reports.groupby(['date', 'conflict', 'article_id'], as_index=False)[
    'is_usage'
  ].max()
  overall['kind'] = '전체'
  article_counts = (
    pd.concat([by_kind, overall], ignore_index=True)
    .groupby(['date', 'conflict', 'kind'])
    .agg(
      analysis_articles=('article_id', 'nunique'), usage_articles=('is_usage', 'sum')
    )
  )

  # 기사 지표의 빈 날짜는 0으로 채우되, 큰 범주별 격자는 만들지 않는다.
  dates = pd.DatetimeIndex([])
  if not articles.empty:
    published_dates = pd.to_datetime(articles['published_date'])
    dates = pd.date_range(published_dates.min(), published_dates.max())
  conflict_names = conflicts['conflict_name_ko'].tolist()
  article_index = pd.MultiIndex.from_product(
    [dates, conflict_names, ['전체', *KIND_LABELS.values()]],
    names=['date', 'conflict', 'kind'],
  )
  article_daily = article_counts.reindex(article_index, fill_value=0).reset_index()
  article_daily = article_daily.astype(
    {'analysis_articles': 'int64', 'usage_articles': 'int64'}
  )

  category_counts = (
    reports.loc[reports['is_usage']]
    .groupby(['date', 'conflict', 'category_id'])['article_id']
    .nunique()
    .rename('count')
  )
  category_daily = (
    category_counts.reset_index()
    .merge(categories, on='category_id', validate='many_to_one')
    .rename(columns={'category_name': 'category'})
  )
  category_daily['kind'] = category_daily['kind'].map(KIND_LABELS)
  category_daily['count'] = category_daily['count'].astype('int64')
  return article_daily, category_daily[
    ['date', 'conflict', 'kind', 'category', 'count']
  ]


def filter_data(frame, conflict, start, end, kind):
  '''일별 DataFrame에서 선택한 기간·분쟁·유형에 해당하는 행의 복사본을 반환한다.'''
  selected = frame['date'].between(pd.Timestamp(start), pd.Timestamp(end)) & frame[
    'kind'
  ].eq(kind)
  if conflict != '전체':
    selected &= frame['conflict'].eq(conflict)
  return frame.loc[selected].copy()


def article_totals(frame):
  '''필터링된 기사 지표에서 (전체 분석 기사 수, 사용 관련 보도 수)를 반환한다.'''
  analysis_count = int(frame['analysis_articles'].sum())
  usage_count = int(frame['usage_articles'].sum())
  return analysis_count, usage_count


def ordered_category_names(categories, category_counts=None):
  '''0건 범주도 포함해 기사 수 내림차순·이름 오름차순으로 정렬한다.'''
  counts = category_counts if category_counts is not None else {}
  return sorted(categories, key=lambda category: (-counts.get(category, 0), category))


def ranked_categories(frame, limit=3):
  '''범주별 합계를 구해 보도 수 상위 limit개를 category·count 컬럼으로 반환한다.'''
  summary = frame.groupby('category', as_index=False)['count'].sum()
  summary = summary[summary['count'] > 0]
  # 보도가 없는 범주는 제외하고, 같은 건수라면 이름순으로 순위를 정한다.
  summary = summary.sort_values(['count', 'category'], ascending=[False, True])
  return summary.head(limit).reset_index(drop=True)


def monthly_trend(frame, selected, start, end):
  '''선택한 범주의 월별 합계를 month·category·count 컬럼으로 반환한다.'''
  chosen = frame.loc[frame['category'].isin(selected)].copy()
  # 같은 월의 날짜를 월초로 맞춰 그룹화한다. 일별 필터를 먼저 적용하므로 부분 월도 반영된다.
  months = chosen['date'].dt.to_period('M')
  chosen['month'] = months.dt.to_timestamp()
  summary = chosen.groupby(['month', 'category'])['count'].sum()
  months = pd.date_range(start.replace(day=1), end.replace(day=1), freq='MS')
  index = pd.MultiIndex.from_product(
    [months, sorted(set(selected))], names=['month', 'category']
  )
  # 조회한 월과 선택한 범주만 확장해 10년치 일별 전체 격자를 피한다.
  return summary.reindex(index, fill_value=0).reset_index()
