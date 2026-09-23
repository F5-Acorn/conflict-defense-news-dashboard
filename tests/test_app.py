'''실제 진입점의 최초 실행과 네 페이지 이동을 검증한다.'''

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from config import build_settings
from data.excel_loader import DataValidationError
from data.sample_data import load_dashboard_snapshot
from services.analysis_service import article_totals, filter_data
from utils.state import init_session_state


class DashboardAppTest(unittest.TestCase):
  def test_startup_navigation_and_shared_filters(self):
    # AppTest는 페이지 자동 탐색 상태를 초기화하므로 최초 실행의 URL 충돌도 검출한다.
    entrypoint = Path(__file__).resolve().parents[1] / 'app.py'
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    self.assertFalse(app.exception)
    self.assertEqual(len(app.metric), 3)
    snapshot = load_dashboard_snapshot()
    self.assertEqual(app.metric[2].value, '65개')
    self.assertEqual(len(app.selectbox(key='conflict').options), 13)
    self.assertEqual(
      app.date_input(key='period').value, (date(2016, 1, 1), date(2025, 12, 31))
    )
    # 전체 및 12개 분쟁 모두 실제 엑셀 결과에서 계산한 지표를 표시한다.
    for conflict in ['전체', *snapshot['settings']['conflicts']]:
      app.selectbox(key='conflict').select(conflict).run()
      self.assertFalse(app.exception)
      expected = article_totals(
        filter_data(
          snapshot['article_daily'],
          conflict,
          date(2016, 1, 1),
          date(2025, 12, 31),
          '전체',
        )
      )
      self.assertEqual(
        [item.value for item in app.metric[:2]], [f'{value:,}건' for value in expected]
      )
    self.assertIn('주요 범주별 상세 목록', [item.value for item in app.subheader])

    app.selectbox(key='conflict').select('이란·이스라엘').run()
    app.selectbox(key='_overview_kind').select('기술').run()
    period = (date(2025, 4, 15), date(2025, 5, 31))
    app.date_input(key='period').set_value(period).run()
    self.assertFalse(app.exception)
    expected_metrics = [item.value for item in app.metric]

    for page in [
      'pages/01_overview_map.py',
      'pages/02_weapons_monthly.py',
      'pages/03_technology_monthly.py',
      'pages/00_overview.py',
    ]:
      with self.subTest(page=page):
        app.switch_page(page).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='conflict').value, '이란·이스라엘')
        self.assertEqual(app.date_input(key='period').value, period)
        if page in ('pages/00_overview.py', 'pages/01_overview_map.py'):
          self.assertEqual(app.selectbox(key='_overview_kind').value, '기술')
          self.assertEqual([item.value for item in app.metric], expected_metrics)
        else:
          self.assertEqual(len(app.get('plotly_chart')), 2)

    app.button[0].click().run()
    self.assertFalse(app.exception)
    self.assertEqual(app.selectbox(key='conflict').value, '전체')
    self.assertEqual(app.selectbox(key='_overview_kind').value, '전체')
    self.assertEqual(
      app.date_input(key='period').value, (date(2016, 1, 1), date(2025, 12, 31))
    )

  def test_unselected_categories_do_not_hide_top_three(self):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(
      timeout=30
    )
    app.switch_page('pages/02_weapons_monthly.py').run()
    for category in list(app.session_state['selected_무기']):
      app.checkbox(key=f'_category_무기_{category}').uncheck().run()
    self.assertFalse(app.exception)
    self.assertEqual(len(app.get('plotly_chart')), 1)
    self.assertTrue(any('하나 이상' in item.value for item in app.info))

  def test_missing_files_and_empty_articles_have_clear_messages(self):
    entrypoint = str(Path(__file__).resolve().parents[1] / 'app.py')
    with patch(
      'data.sample_data.load_dashboard_snapshot',
      side_effect=DataValidationError('article_example.xlsx: 파일 없음'),
    ):
      app = AppTest.from_file(entrypoint).run(timeout=30)
      self.assertFalse(app.exception)
      self.assertIn('article_example.xlsx', app.error[0].value)
      self.assertEqual(len(app.metric), 0)
    snapshot = load_dashboard_snapshot()
    snapshot['tables']['articles'] = snapshot['tables']['articles'].iloc[:0]
    snapshot['settings'] = build_settings(snapshot['tables'])
    with patch('data.sample_data.load_dashboard_snapshot', return_value=snapshot):
      app = AppTest.from_file(entrypoint).run(timeout=30)
      self.assertFalse(app.exception)
      self.assertIn('등록된 기사가 없습니다', app.info[0].value)

  def test_invalid_selections_are_repaired_after_data_changes(self):
    settings = load_dashboard_snapshot()['settings']
    state = {
      'conflict': '삭제된 분쟁',
      'period': (date(2026, 1, 1), date(2026, 2, 1)),
      'overview_kind': '기술',
      'selected_무기': ['삭제된 범주'],
      'selected_기술': [],
    }
    with patch('utils.state.st.session_state', state):
      init_session_state(settings)
    self.assertEqual(state['conflict'], '전체')
    self.assertEqual(state['period'], (settings['start'], settings['end']))
    self.assertEqual(state['selected_무기'], settings['default_categories']['무기'])
    self.assertEqual(state['selected_기술'], [])


if __name__ == '__main__':
  unittest.main()
