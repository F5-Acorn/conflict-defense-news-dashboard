'''DB 경계의 코드·정밀도·검증·캐시와 화면 입력 계약 회귀 검사.'''

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest

from data.db_loader import database_url, normalize_tables, read_tables_from_db
from data.snapshot import _build_snapshot, dataset_revision
from data.table_contract import COLUMNS, DataValidationError
from services.detail_service import article_details, category_frequencies


def database_tables():
  rows = {
    'conflicts': [
      ['c1', 'A', '분쟁 A', '#123456', '🇰🇷', Decimal('37.1'), Decimal('127.1')],
      ['c2', 'B', '분쟁 B', '#654321', None, 1, 2],
    ],
    'categories': [['w1', 'weapon', '무기 범주'], ['t1', 'technology', '기술 범주']],
    'sipri_dictionary': [['s1', 'w1', 'tank']],
    'nato_dictionary': [['n1', 't1', 'radar']],
    'articles': [
      [2**63 - 1, 'c1', date(2026, 9, 1), 'https://example.org/a', None],
      [2, 'c2', date(2026, 9, 1), 'https://example.org/a', 'NA'],
      [3, 'c1', date(2026, 9, 2), 'https://example.org/b', '기사'],
    ],
    'result': [
      [2**63 - 1, 'w1', 1, 'tank used'],
      [2, 'w1', 2, ''],
      [3, 't1', 3, None],
    ],
  }
  return {
    name: pd.DataFrame(rows[name], columns=cols) for name, cols in COLUMNS.items()
  }


class ContractTests(unittest.TestCase):
  def test_db_codes_kinds_and_bigint(self):
    tables = normalize_tables(database_tables())
    self.assertEqual(tables['result'].usage_code.tolist(), [0, 1, 2])
    self.assertEqual(tables['categories'].kind.tolist(), ['wp', 'tech'])
    self.assertEqual(tables['articles'].article_id.iloc[0], 2**63 - 1)
    self.assertEqual(str(tables['articles'].published_date.dtype), 'datetime64[ns]')

  def test_invalid_data_is_rejected(self):
    cases = [
      ('result', 'usage_code', 0),
      ('result', 'usage_code', 4),
      ('result', 'evidence_sentence', ''),
      ('result', 'article_id', 100),
      ('articles', 'article_id', 2**63),
      ('articles', 'published_date', '2026-09-01 12:00:00'),
      ('articles', 'published_date', '2026-09-01T00:00:00Z'),
      ('articles', 'published_date', 'invalid'),
      ('categories', 'kind', 'unknown'),
      ('conflicts', 'latitude', 91),
      ('conflicts', 'color', 'red'),
      ('sipri_dictionary', 'category_id', 't1'),
    ]
    for name, column, value in cases:
      with self.subTest(name=name, column=column, value=value):
        tables = database_tables()
        tables[name][column] = tables[name][column].astype(object)
        tables[name].at[0, column] = value
        with self.assertRaises(DataValidationError):
          normalize_tables(tables)

  def test_duplicate_url_is_scoped_to_conflict(self):
    normalize_tables(database_tables())
    tables = database_tables()
    tables['articles'].at[1, 'conflict_id'] = 'c1'
    with self.assertRaisesRegex(DataValidationError, 'article_url'):
      normalize_tables(tables)

  def test_missing_column_and_duplicate_result(self):
    tables = database_tables()
    tables['articles'] = tables['articles'].drop(columns='title')
    with self.assertRaisesRegex(DataValidationError, 'title'):
      normalize_tables(tables)
    tables = database_tables()
    tables['result'] = pd.concat([tables['result'], tables['result'].iloc[:1]])
    with self.assertRaisesRegex(DataValidationError, '중복'):
      normalize_tables(tables)


class LoaderTests(unittest.TestCase):
  def test_six_explicit_queries_one_read_only_connection(self):
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    tables = database_tables()
    with (
      patch('data.db_loader.get_db_engine', return_value=engine),
      patch(
        'data.db_loader.pd.read_sql_query', side_effect=list(tables.values())
      ) as read,
    ):
      result = read_tables_from_db('test')
    self.assertEqual(set(result), set(COLUMNS))
    engine.connect.assert_called_once()
    connection.exec_driver_sql.assert_called_once_with(
      'START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY'
    )
    self.assertEqual(read.call_count, 6)
    for call in read.call_args_list:
      sql = str(call.args[0])
      self.assertNotIn('*', sql)
      self.assertNotIn('usage_patterns', sql)
      self.assertIs(call.args[1], connection)

  def test_connection_error_is_sanitized(self):
    engine = MagicMock()
    engine.connect.side_effect = OperationalError(None, None, Exception('secret-value'))
    with patch('data.db_loader.get_db_engine', return_value=engine):
      with self.assertRaises(DataValidationError) as error:
        read_tables_from_db('test')
    self.assertNotIn('secret-value', str(error.exception))

  def test_missing_secrets(self):
    with patch('data.db_loader.st.secrets', {}):
      with self.assertRaisesRegex(DataValidationError, 'secrets.toml'):
        database_url()


class SnapshotTests(unittest.TestCase):
  def tearDown(self):
    _build_snapshot.clear()

  def test_cache_copy_and_revision_content(self):
    tables = normalize_tables(database_tables())
    with patch('data.snapshot.read_tables_from_db', return_value=tables) as read:
      first = _build_snapshot('test')
      first['tables']['articles'].at[0, 'title'] = '수정'
      second = _build_snapshot('test')
      self.assertEqual(read.call_count, 1)
      self.assertTrue(pd.isna(second['tables']['articles'].at[0, 'title']))
      self.assertEqual(first['revision'], second['revision'])
      _build_snapshot.clear()
      tables['articles'].at[0, 'title'] = '갱신'
      third = _build_snapshot('test')
      self.assertNotEqual(second['revision'], third['revision'])
    self.assertEqual(
      set(third),
      {'tables', 'revision', 'reports', 'settings', 'article_daily', 'category_daily'},
    )
    self.assertEqual(third['settings']['category_ids']['무기'], {'무기 범주': 'w1'})

  def test_title_fallback_usage_counts_and_wordcloud(self):
    with patch(
      'data.snapshot.read_tables_from_db',
      return_value=normalize_tables(database_tables()),
    ):
      snapshot = _build_snapshot('test')
    details = article_details(snapshot['reports'], 'w1', '2026-09')
    self.assertEqual(details['total'], 1)
    self.assertEqual(details['items'][0]['title'], '제목 없음')
    self.assertEqual(category_frequencies(snapshot['reports']), {'무기 범주': 1})
    self.assertEqual(snapshot['category_daily']['count'].sum(), 1)

  def test_empty_articles_and_results(self):
    tables = database_tables()
    tables['articles'] = tables['articles'].iloc[:0]
    tables['result'] = tables['result'].iloc[:0]
    with patch(
      'data.snapshot.read_tables_from_db', return_value=normalize_tables(tables)
    ):
      snapshot = _build_snapshot('test')
    self.assertIsNone(snapshot['settings']['start'])
    self.assertTrue(snapshot['reports'].empty)

  def test_revision_changes_for_reference_and_evidence(self):
    tables = normalize_tables(database_tables())
    first = dataset_revision(tables)
    tables['result'].at[0, 'evidence_sentence'] = 'new evidence'
    second = dataset_revision(tables)
    tables['conflicts'].at[0, 'color'] = '#ffffff'
    self.assertNotEqual(first, second)
    self.assertNotEqual(second, dataset_revision(tables))


class AppErrorTests(unittest.TestCase):
  def test_db_failure_shows_message(self):
    with patch(
      'data.snapshot.load_dashboard_snapshot',
      side_effect=DataValidationError('DB 조회 실패'),
    ):
      app = AppTest.from_file('../app.py').run()
    self.assertFalse(app.exception)
    self.assertIn('DB 조회 실패', app.error[0].value)


if __name__ == '__main__':
  unittest.main()
