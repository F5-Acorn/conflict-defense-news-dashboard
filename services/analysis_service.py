'''Streamlit에 의존하지 않는 기간 필터 및 집계 함수.'''

import pandas as pd

from data.constants import KIND_LABELS, UsageCode


def build_overview_article_counts(tables):
  '''분쟁별 전체 기사 행 수와 사용 판정 고유 기사 수, 전체 사용 기사 수를 반환한다.'''
  conflicts = tables['conflicts'][['conflict_id', 'conflict_name_ko']].rename(
    columns={'conflict_name_ko': 'conflict'}
  )
  # A: 판정 유무와 관계없이 분쟁에 연결된 모든 기사를 포함한다.
  mentions = tables['articles'][['article_id', 'conflict_id']].merge(
    conflicts, on='conflict_id', validate='many_to_one'
  )
  # B: 사용 판정만 A에 연결한다. 같은 기사의 여러 범주는 중복 집계하지 않는다.
  usage = (
    tables['result']
    .loc[tables['result']['usage_code'].eq(UsageCode.USED), ['article_id']]
    .merge(mentions, on='article_id', validate='many_to_one')
  )
  analysis_counts = mentions.groupby('conflict_id').size()
  usage_counts = usage.groupby('conflict_id')['article_id'].nunique()
  overview = conflicts.assign(
    analysis_articles=conflicts['conflict_id'].map(analysis_counts).fillna(0),
    usage_articles=conflicts['conflict_id'].map(usage_counts).fillna(0),
  ).astype({'analysis_articles': 'int64', 'usage_articles': 'int64'})
  return overview, int(usage['article_id'].nunique())


def build_dashboard_data(tables, reports):
  '''조인된 판정에서 article_id를 중복 제거해 화면용 일별 지표를 만든다.

  결과가 없는 수집 기사는 분석 지표에서 제외한다. 사용 건수는 usage_code=0만 센다.
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


def article_totals(frame):
  '''필터링된 기사 지표에서 (전체 분석 기사 수, 사용 관련 보도 수)를 반환한다.'''
  analysis_count = int(frame['analysis_articles'].sum())
  usage_count = int(frame['usage_articles'].sum())
  return analysis_count, usage_count


def ranked_categories(frame, limit=3):
  '''범주별 합계를 구해 보도 수 상위 limit개를 category·count 컬럼으로 반환한다.'''
  summary = frame.groupby('category', as_index=False)['count'].sum()
  summary = summary[summary['count'] > 0]
  # 보도가 없는 범주는 제외하고, 같은 건수라면 이름순으로 순위를 정한다.
  summary = summary.sort_values(['count', 'category'], ascending=[False, True])
  return summary.head(limit).reset_index(drop=True)


def period_reports(reports, conflict, start, end, kind):
  '''기간·분쟁·유형에 해당하는 기사·범주 판정 행을 반환한다.'''
  selected = reports['date'].between(pd.Timestamp(start), pd.Timestamp(end))
  if conflict != '전체':
    selected &= reports['conflict'].eq(conflict)
  if kind != '전체':
    selected &= reports['kind'].eq(kind)
  return reports.loc[selected].copy()


STATUS_COLUMNS = {
  UsageCode.USED: 'used_count',
  UsageCode.UNCERTAIN: 'uncertain_count',
  UsageCode.NOT_USED: 'not_used_count',
}


def build_status_daily(reports):
  '''기사·범주 쌍을 한 번만 집계해 판정별 일별 수치를 준비한다.'''
  keys = ['date', 'conflict_id', 'conflict', 'category_id', 'kind', 'category']
  rows = reports.drop_duplicates(['article_id', 'category_id'])
  counts = (
    rows.groupby(keys + ['usage_code'], observed=True).size().unstack('usage_code')
  )
  counts = counts.reindex(columns=list(STATUS_COLUMNS), fill_value=0).fillna(0)
  result = counts.rename(columns=STATUS_COLUMNS).astype('int64').reset_index()
  result['total_count'] = result[list(STATUS_COLUMNS.values())].sum(axis=1)
  return result


def category_summary(snapshot, conflict, start, end, kind):
  '''공통 일별 집계에서 범주 전체 요약을 생성하고 동일 조건을 재사용한다.'''
  key = ('categories', conflict, start, end, kind)

  def build():
    rows = period_reports(snapshot['category_status_daily'], conflict, start, end, kind)
    columns = [*STATUS_COLUMNS.values(), 'total_count']
    counts = rows.groupby('category_id', observed=True)[columns].sum()
    meta = snapshot['category_meta']
    if kind != '전체':
      meta = meta.loc[meta['kind'].eq(kind)]
    result = meta.merge(counts, on='category_id', how='left').fillna(
      {c: 0 for c in columns}
    )
    result[columns] = result[columns].astype('int64')
    return result.sort_values(
      ['used_count', 'kind', 'category'], ascending=[False, True, True]
    ).reset_index(drop=True)

  return snapshot['view_cache'].get(key, build)


def summary_word_counts(summary):
  '''동명 범주의 표시 단어는 합산하되 범주 ID별 집계는 보존한다.'''
  counts = summary.groupby('category', observed=True)['used_count'].sum()
  return {name: int(count) for name, count in counts.items() if count > 0}


def summary_judgements(summary, category_id):
  row = summary.loc[summary['category_id'].eq(category_id)]
  return pd.Series(
    {code: int(row[column].sum()) for code, column in STATUS_COLUMNS.items()}
  )


def summary_trend(snapshot, conflict, start, end, kind, selected_ids, granularity):
  key = ('trend', conflict, start, end, kind, tuple(selected_ids), granularity)

  def build():
    full_months = (
      start.day == 1 and end == (pd.Timestamp(end) + pd.offsets.MonthEnd(0)).date()
    )
    monthly = granularity == 'month' and full_months
    frame = snapshot['category_status_monthly' if monthly else 'category_status_daily']
    chosen = period_reports(frame, conflict, start, end, kind)
    chosen = chosen.loc[chosen['category_id'].isin(selected_ids)].copy()
    chosen['bucket'] = (
      chosen['date'].dt.to_period('M').dt.to_timestamp()
      if granularity == 'month'
      else chosen['date']
    )
    counts = chosen.groupby(['bucket', 'category_id'], observed=True)[
      'used_count'
    ].sum()
    dates = pd.date_range(
      start.replace(day=1) if granularity == 'month' else start,
      end,
      freq='MS' if granularity == 'month' else 'D',
    )
    index = pd.MultiIndex.from_product(
      [dates, selected_ids], names=['bucket', 'category_id']
    )
    return counts.reindex(index, fill_value=0).rename('count').reset_index()

  return snapshot['view_cache'].get(key, build)
