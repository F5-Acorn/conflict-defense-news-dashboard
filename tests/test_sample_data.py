'''ERD 제약과 기사 중복 제거·사용 판정 집계의 회귀 검사.'''

import sqlite3
import unittest
from datetime import date

import pandas as pd

from config import build_settings
from data.excel_loader import DUMMY_DIR
from data.reference_data import KIND_LABELS
from data.sample_data import load_sample_tables
from scripts.build_dummy_examples import build_examples
from services.analysis_service import (
  article_totals,
  build_dashboard_data,
  filter_data,
  latest_distribution,
  monthly_trend,
)


class SampleTablesTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tables = load_sample_tables()
    cls.daily, cls.category_daily = build_dashboard_data(cls.tables)
    cls.settings = build_settings(cls.tables)

  def test_erd_columns_and_primary_keys(self):
    columns = {
      'conflicts': [
        'conflict_id',
        'conflict_name_en',
        'conflict_name_ko',
        'color',
        'flag',
        'latitude',
        'longitude',
      ],
      'articles': [
        'article_id',
        'conflict_id',
        'published_date',
        'article_url',
        'title',
      ],
      'categories': ['category_id', 'kind', 'category_name'],
      'sipri_dictionary': ['wp_id', 'category_id', 'wp_name'],
      'nato_dictionary': ['tech_id', 'category_id', 'tech_name'],
      'usage_patterns': ['pattern_id', 'base_form', 'trans_form'],
      'result': ['article_id', 'category_id', 'usage_code', 'evidence_sentence'],
    }
    self.assertEqual(set(self.tables), set(columns))
    for name, expected in columns.items():
      with self.subTest(table=name):
        frame = self.tables[name]
        self.assertEqual(frame.columns.tolist(), expected)
        primary_key = (
          ['article_id', 'category_id'] if name == 'result' else [expected[0]]
        )
        self.assertFalse(frame.duplicated(primary_key).any())
        nullable = {'flag', 'evidence_sentence', 'trans_form'}
        required = [column for column in expected if column not in nullable]
        self.assertFalse(frame[required].isna().any().any())

  def test_foreign_keys_and_dictionary_kinds(self):
    for child, column, parent in [
      ('articles', 'conflict_id', 'conflicts'),
      ('result', 'article_id', 'articles'),
      ('result', 'category_id', 'categories'),
      ('sipri_dictionary', 'category_id', 'categories'),
      ('nato_dictionary', 'category_id', 'categories'),
    ]:
      with self.subTest(table=child, column=column):
        self.assertTrue(
          self.tables[child][column].isin(self.tables[parent][column]).all()
        )
    categories = self.tables['categories'].set_index('category_id')
    for name, kind in [('sipri_dictionary', 'wp'), ('nato_dictionary', 'tech')]:
      frame = self.tables[name]
      self.assertTrue(frame['category_id'].map(categories['kind']).eq(kind).all())

  def test_unique_names_domains_and_evidence(self):
    unique_columns = {
      'conflicts': ['conflict_name_ko'],
      'articles': ['article_url'],
      'categories': ['kind', 'category_name'],
      'nato_dictionary': ['tech_name'],
    }
    for name, columns in unique_columns.items():
      self.assertFalse(self.tables[name].duplicated(columns).any())
    for frame in self.tables.values():
      for column in frame.columns:
        if column.endswith('_id') and column != 'article_id':
          self.assertTrue(frame[column].str.len().le(20).all())
    self.assertTrue(
      self.tables['conflicts']['color'].str.fullmatch(r'#[0-9a-fA-F]{6}').all()
    )
    self.assertTrue(self.tables['conflicts']['latitude'].between(-90, 90).all())
    self.assertEqual(set(self.tables['categories']['kind']), {'wp', 'tech'})
    results = self.tables['result']
    self.assertEqual(set(results['usage_code']), {0, 1, 2})
    evidence = results.loc[results['usage_code'].eq(1), 'evidence_sentence']
    self.assertTrue(evidence.notna().all())
    self.assertTrue(evidence.str.strip().str.len().gt(0).all())
    articles = self.tables['articles']
    self.assertTrue(
      articles['article_url'].str.startswith('https://example.invalid/').all()
    )
    self.assertTrue(articles['title'].str.startswith('[가상 기사]').all())
    self.assertTrue(
      articles['published_date'].between('2016-01-01', '2025-12-31').all()
    )
    self.assertEqual(articles['published_date'].dt.to_period('M').nunique(), 120)
    self.assertIn(pd.Timestamp('2020-02-29'), set(articles['published_date']))
    monthly = articles.groupby(
      ['conflict_id', articles['published_date'].dt.to_period('M')]
    ).size()
    self.assertEqual(len(monthly), 12 * 120)
    self.assertTrue(monthly.between(12, 24).all())
    self.assertEqual(len(self.tables['conflicts']), 12)
    self.assertEqual(self.settings['classification_counts'], {'무기': 23, '기술': 42})

  def test_metadata_matches_reference_tables(self):
    categories = self.tables['categories']
    for code, label in KIND_LABELS.items():
      expected = categories.loc[categories['kind'].eq(code), 'category_name']
      self.assertEqual(self.settings['categories'][label], sorted(expected))
      self.assertEqual(self.settings['classification_counts'][label], len(expected))
    self.assertEqual(
      list(self.settings['conflicts']),
      self.tables['conflicts']['conflict_name_ko'].tolist(),
    )

  def test_reproducible_generation_and_cache_isolation(self):
    first = build_examples(DUMMY_DIR, '2016-01-01', '2016-01-02')
    second = build_examples(DUMMY_DIR, '2016-01-01', '2016-01-02')
    self.assertEqual(first, second)
    modified = load_sample_tables()
    modified['articles'].loc[0, 'title'] = 'changed'
    self.assertNotEqual(load_sample_tables()['articles'].loc[0, 'title'], 'changed')

  def test_aggregates_match_independent_sql_counts(self):
    connection = sqlite3.connect(':memory:')
    self.addCleanup(connection.close)
    for name, frame in self.tables.items():
      frame.to_sql(name, connection, index=False)
    periods = [
      (date(2016, 1, 1), date(2025, 12, 31)),
      (date(2020, 2, 29), date(2020, 3, 1)),
      (date(2025, 12, 31), date(2025, 12, 31)),
    ]
    for start, end in periods:
      for conflict in ['전체', *self.settings['conflicts']]:
        for kind in ['전체', *KIND_LABELS.values()]:
          with self.subTest(start=start, end=end, conflict=conflict, kind=kind):
            conditions = ['date(a.published_date) BETWEEN ? AND ?']
            parameters = [str(start), str(end)]
            if conflict != '전체':
              conditions.append('f.conflict_name_ko = ?')
              parameters.append(conflict)
            if kind != '전체':
              conditions.append('c.kind = ?')
              parameters.append(
                next(code for code, label in KIND_LABELS.items() if label == kind)
              )
            query = '''
              SELECT COUNT(DISTINCT r.article_id),
                     COUNT(DISTINCT CASE WHEN r.usage_code = 1 THEN r.article_id END)
              FROM result r
              JOIN articles a USING (article_id)
              JOIN categories c USING (category_id)
              JOIN conflicts f USING (conflict_id)
              WHERE ''' + ' AND '.join(conditions)
            expected = connection.execute(query, parameters).fetchone()
            filtered = filter_data(self.daily, conflict, start, end, kind)
            self.assertEqual(article_totals(filtered), expected)
    expected = pd.read_sql_query(
      '''
      SELECT date(a.published_date) AS date, f.conflict_name_ko AS conflict,
             c.category_name AS category, COUNT(DISTINCT r.article_id) AS count
      FROM result r
      JOIN articles a USING (article_id)
      JOIN categories c USING (category_id)
      JOIN conflicts f USING (conflict_id)
      WHERE r.usage_code = 1
      GROUP BY date(a.published_date), f.conflict_name_ko, c.category_id
    ''',
      connection,
    )
    expected['date'] = pd.to_datetime(expected['date'])
    keys = ['date', 'conflict', 'category']
    actual = self.category_daily.loc[
      self.category_daily['count'].gt(0), keys + ['count']
    ]
    pd.testing.assert_frame_equal(
      actual.sort_values(keys).reset_index(drop=True),
      expected.sort_values(keys).reset_index(drop=True),
      check_dtype=False,
    )


class ArticleCountingTest(unittest.TestCase):
  def setUp(self):
    self.tables = {
      'conflicts': pd.DataFrame(
        [
          ('ru_ua', 'Russia - Ukraine', '러시아·우크라이나', '#3296ff', '', 48, 37),
          ('ir_il', 'Iran - Israel', '이란·이스라엘', '#ff7953', '', 32, 46),
        ],
        columns=[
          'conflict_id',
          'conflict_name_en',
          'conflict_name_ko',
          'color',
          'flag',
          'latitude',
          'longitude',
        ],
      ),
      'categories': pd.DataFrame(
        [
          ('wp_missile', 'wp', '미사일'),
          ('wp_drone', 'wp', '무인기'),
          ('wp_tank', 'wp', '전차'),
          ('tech_ew', 'tech', '전자전'),
          ('tech_isr', 'tech', '감시·정찰'),
          ('tech_autonomy', 'tech', '자율 제어'),
        ],
        columns=['category_id', 'kind', 'category_name'],
      ),
    }
    self.tables['articles'] = pd.DataFrame(
      [
        (1, 'ru_ua', '2026-03-01'),
        (2, 'ru_ua', '2026-03-01'),
        (3, 'ru_ua', '2026-03-01'),
        (4, 'ir_il', '2026-03-01'),
        (5, 'ir_il', '2026-03-02'),
        (6, 'ru_ua', '2026-03-02'),  # 무기·기술 언급이 없는 수집 기사
      ],
      columns=['article_id', 'conflict_id', 'published_date'],
    )
    self.tables['articles']['article_url'] = [
      f'https://example.invalid/{i}' for i in range(6)
    ]
    self.tables['articles']['title'] = '[가상 기사] 집계 검증'
    self.tables['result'] = pd.DataFrame(
      [
        (1, 'wp_missile', 1),
        (1, 'wp_drone', 1),
        (1, 'tech_ew', 1),
        (2, 'wp_tank', 0),
        (2, 'tech_isr', 2),
        (3, 'tech_autonomy', 1),
        (4, 'wp_drone', 2),
        (5, 'wp_drone', 1),
      ],
      columns=['article_id', 'category_id', 'usage_code'],
    )
    self.tables['result']['evidence_sentence'] = '[Synthetic] Counting fixture.'

  def test_cross_category_and_cross_kind_articles_count_once(self):
    daily, categories = build_dashboard_data(self.tables)
    for kind, expected in [('전체', (5, 3)), ('무기', (4, 2)), ('기술', (3, 2))]:
      self.assertEqual(article_totals(daily.loc[daily['kind'].eq(kind)]), expected)
    self.assertEqual(categories['count'].sum(), 5)
    self.assertEqual(
      categories.loc[categories['category'].isin(['전차', '감시·정찰']), 'count'].sum(),
      0,
    )

  def test_inclusive_dates_zero_days_monthly_counts_and_top_three(self):
    daily, categories = build_dashboard_data(self.tables)
    day = date(2026, 3, 2)
    self.assertEqual(
      article_totals(filter_data(daily, '러시아·우크라이나', day, day, '전체')), (0, 0)
    )
    self.assertEqual(
      article_totals(filter_data(daily, '이란·이스라엘', day, day, '무기')), (1, 1)
    )
    weapons = filter_data(categories, '전체', date(2026, 3, 1), day, '무기')
    trend = monthly_trend(weapons, ['무인기', '전차'], date(2026, 3, 1), day)
    self.assertEqual(
      dict(zip(trend['category'], trend['count'])), {'무인기': 2, '전차': 0}
    )
    ranking, distribution = latest_distribution(weapons, day)
    self.assertEqual(ranking['category'].tolist(), ['무인기', '미사일'])
    self.assertEqual(ranking['count'].tolist(), [2, 1])
    self.assertEqual(
      distribution.groupby('category')['count'].sum().to_dict(),
      {'무인기': 2, '미사일': 1},
    )

  def test_empty_results_and_no_confirmed_usage(self):
    self.tables['result']['usage_code'] = 2
    daily, categories = build_dashboard_data(self.tables)
    self.assertEqual(article_totals(daily.loc[daily['kind'].eq('전체')]), (5, 0))
    self.assertTrue(categories['count'].eq(0).all())
    self.tables['result'] = self.tables['result'].iloc[:0]
    daily, categories = build_dashboard_data(self.tables)
    self.assertEqual(article_totals(daily), (0, 0))
    self.assertTrue(categories['count'].eq(0).all())
    ranking, distribution = latest_distribution(categories, date(2026, 3, 2))
    self.assertTrue(ranking.empty)
    self.assertTrue(distribution.empty)
    self.tables['articles'] = self.tables['articles'].iloc[:0]
    daily, categories = build_dashboard_data(self.tables)
    self.assertTrue(daily.empty)
    self.assertTrue(categories.empty)
    self.assertTrue(pd.api.types.is_datetime64_any_dtype(daily['date']))


if __name__ == '__main__':
  unittest.main()
