'''실제 진입점의 날짜 입력, 최초 실행과 페이지 이동을 검증한다.'''

import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from config import build_settings
from data.excel_loader import DataValidationError
from data.sample_data import load_dashboard_snapshot
from services.analysis_service import article_totals, filter_data
from utils.state import default_filters, filter_widget_key, init_session_state


class DashboardAppTest(unittest.TestCase):
  def filters(self, app):
    return app.session_state['page_filters'][app.session_state['_filter_page']]

  def widget_key(self, app, field):
    return filter_widget_key(app.session_state['_filter_page'], field)

  def switch_page(self, app, page_key):
    if page_key == 'overview':
      # AppTest가 pages 폴더의 기본 페이지를 직접 실행하지 않도록 진입점으로 복귀한다.
      app._page_hash = ''
    else:
      filename = {
        'weapons-monthly': 'pages/02_weapons_monthly.py',
        'technology-monthly': 'pages/03_technology_monthly.py',
      }[page_key]
      app.switch_page(filename)
    app.run(timeout=30)
    self.assertFalse(app.exception)

  def assert_period(self, app, period):
    self.assertEqual(self.filters(app)['period'], period)
    self.assertEqual(app.date_input(key=self.widget_key(app, 'start')).value, period[0])
    self.assertEqual(app.date_input(key=self.widget_key(app, 'end')).value, period[1])

  def test_startup_navigation_and_overview_filters(self):
    # AppTest는 페이지 자동 탐색 상태를 초기화하므로 최초 실행의 URL 충돌도 검출한다.
    entrypoint = Path(__file__).resolve().parents[1] / 'app.py'
    app = AppTest.from_file(str(entrypoint)).run(timeout=30)
    self.assertFalse(app.exception)
    self.assertEqual(len(app.metric), 3)
    snapshot = load_dashboard_snapshot()
    self.assertEqual(app.metric[2].value, '65개')
    self.assertEqual(
      len(app.selectbox(key=self.widget_key(app, 'conflict')).options), 13
    )
    self.assert_period(app, (date(2016, 1, 1), date(2025, 12, 31)))
    # 전체 및 12개 분쟁 모두 실제 엑셀 결과에서 계산한 지표를 표시한다.
    for conflict in ['전체', *snapshot['settings']['conflicts']]:
      app.selectbox(key=self.widget_key(app, 'conflict')).select(conflict).run()
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

    app.selectbox(key=self.widget_key(app, 'conflict')).select('이란·이스라엘').run()
    app.selectbox(key=self.widget_key(app, 'overview_kind')).select('기술').run()
    period = (date(2025, 4, 15), date(2025, 5, 31))
    app.date_input(key=self.widget_key(app, 'start')).set_value(period[0]).run()
    app.date_input(key=self.widget_key(app, 'end')).set_value(period[1]).run()
    self.assertFalse(app.exception)
    expected_metrics = [item.value for item in app.metric]

    for page in [
      'pages/02_weapons_monthly.py',
      'pages/03_technology_monthly.py',
      'pages/01_overview.py',
    ]:
      with self.subTest(page=page):
        if page == 'pages/01_overview.py':
          # AppTest의 자동 pages 탐색이 같은 이름의 기본 페이지를 직접 실행하지
          # 않도록 빈 경로로 복귀한다. 실제 브라우저의 기본 페이지 URL도 '/'이다.
          app._page_hash = ''
          app.run(timeout=30)
        else:
          app.switch_page(page).run(timeout=30)
        self.assertFalse(app.exception)
        if page == 'pages/01_overview.py':
          self.assertEqual(
            app.selectbox(key=self.widget_key(app, 'conflict')).value, '이란·이스라엘'
          )
          self.assert_period(app, period)
          self.assertEqual(
            app.selectbox(key=self.widget_key(app, 'overview_kind')).value, '기술'
          )
          self.assertEqual([item.value for item in app.metric], expected_metrics)
        else:
          self.assertEqual(
            app.selectbox(key=self.widget_key(app, 'conflict')).value, '전체'
          )
          self.assert_period(app, (date(2025, 1, 1), date(2025, 12, 31)))
          self.assertEqual(len(app.get('plotly_chart')), 2)

    app.button[0].click().run()
    self.assertFalse(app.exception)
    self.assertEqual(app.selectbox(key=self.widget_key(app, 'conflict')).value, '전체')
    self.assertEqual(
      app.selectbox(key=self.widget_key(app, 'overview_kind')).value, '전체'
    )
    self.assert_period(app, (date(2016, 1, 1), date(2025, 12, 31)))

  def test_page_filters_and_resets_are_independent(self):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(
      timeout=30
    )
    settings = load_dashboard_snapshot()['settings']
    saved = {}
    cases = [
      ('overview', '이란·이스라엘', date(2020, 1, 1), date(2021, 12, 31)),
      ('weapons-monthly', '러시아·우크라이나', date(2024, 4, 1), date(2025, 5, 31)),
      ('technology-monthly', '이란·이스라엘', date(2023, 5, 1), date(2024, 2, 29)),
    ]
    for page_key, conflict, start, end in cases:
      self.switch_page(app, page_key)
      default_start = date(2016 if page_key == 'overview' else 2025, 1, 1)
      self.assert_period(app, (default_start, date(2025, 12, 31)))
      self.assertEqual(
        app.selectbox(key=self.widget_key(app, 'conflict')).value, '전체'
      )
      app.selectbox(key=self.widget_key(app, 'conflict')).select(conflict).run()
      app.date_input(key=self.widget_key(app, 'start')).set_value(start).run()
      app.date_input(key=self.widget_key(app, 'end')).set_value(end).run()
      if page_key == 'overview':
        app.selectbox(key=self.widget_key(app, 'overview_kind')).select('기술').run()
      else:
        selected = list(self.filters(app)['selected_categories'])
        to_remove = selected[:1] if page_key == 'weapons-monthly' else selected
        for category in to_remove:
          app.checkbox(key=self.widget_key(app, f'category_{category}')).uncheck().run()
        app.text_input(key=self.widget_key(app, 'category_search')).set_value(
          selected[-1]
        ).run()
      self.assertFalse(app.exception)
      saved[page_key] = deepcopy(self.filters(app))

    for page_key, expected in saved.items():
      self.switch_page(app, page_key)
      self.assertEqual(self.filters(app), expected)
      self.assert_period(app, expected['period'])
      self.assertEqual(
        app.selectbox(key=self.widget_key(app, 'conflict')).value, expected['conflict']
      )
      if page_key == 'overview':
        self.assertEqual(
          app.selectbox(key=self.widget_key(app, 'overview_kind')).value, '기술'
        )
      else:
        self.assertEqual(
          app.text_input(key=self.widget_key(app, 'category_search')).value,
          expected['category_search'],
        )
        category = expected['category_search']
        self.assertEqual(
          app.checkbox(key=self.widget_key(app, f'category_{category}')).value,
          category in expected['selected_categories'],
        )

    # 어느 페이지에서 초기화해도 다른 두 페이지의 기간·선택·검색어는 보존한다.
    for page_key in saved:
      self.switch_page(app, page_key)
      before = deepcopy(app.session_state['page_filters'])
      app.button(key=self.widget_key(app, 'reset')).click().run()
      self.assertFalse(app.exception)
      self.assertEqual(self.filters(app), default_filters(settings, page_key))
      for other_page, expected in before.items():
        if other_page != page_key:
          self.assertEqual(app.session_state['page_filters'][other_page], expected)
      if page_key != 'overview':
        self.assertEqual(
          app.text_input(key=self.widget_key(app, 'category_search')).value, ''
        )
        self.assert_period(app, (date(2025, 1, 1), date(2025, 12, 31)))

  def test_separate_date_inputs_apply_cross_month_and_year_periods(self):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(
      timeout=30
    )
    snapshot = load_dashboard_snapshot()
    periods = [
      (date(2016, 1, 15), date(2016, 2, 20)),
      (date(2019, 12, 31), date(2020, 1, 1)),
      (date(2020, 2, 29), date(2020, 3, 1)),
      (date(2025, 5, 31), date(2025, 5, 31)),
    ]
    for period in periods:
      with self.subTest(period=period):
        previous_end = app.date_input(key=self.widget_key(app, 'end')).value
        app.date_input(key=self.widget_key(app, 'start')).set_value(period[0]).run()
        self.assertEqual(
          app.date_input(key=self.widget_key(app, 'start')).value, period[0]
        )
        self.assertEqual(
          app.date_input(key=self.widget_key(app, 'end')).value, previous_end
        )
        app.date_input(key=self.widget_key(app, 'end')).set_value(period[1]).run()
        self.assertFalse(app.exception)
        self.assert_period(app, period)
        expected = article_totals(
          filter_data(snapshot['article_daily'], '전체', *period, '전체')
        )
        self.assertEqual(
          [item.value for item in app.metric[:2]],
          [f'{value:,}건' for value in expected],
        )

  def test_invalid_period_can_be_corrected_or_reset(self):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(
      timeout=30
    )
    app.date_input(key=self.widget_key(app, 'end')).set_value(date(2019, 12, 31)).run()
    previous_period = self.filters(app)['period']
    app.date_input(key=self.widget_key(app, 'start')).set_value(date(2020, 1, 1)).run()
    self.assertFalse(app.exception)
    self.assertEqual(
      app.date_input(key=self.widget_key(app, 'start')).value, date(2020, 1, 1)
    )
    self.assertEqual(
      app.date_input(key=self.widget_key(app, 'end')).value, date(2019, 12, 31)
    )
    self.assertEqual(self.filters(app)['period'], previous_period)
    self.assertIn('종료일은 시작일 이후', app.info[0].value)
    self.assertEqual(len(app.metric), 0)

    # 다른 필터 변경이나 페이지 이동 중에도 수정 중인 날짜를 잃지 않는다.
    app.selectbox(key=self.widget_key(app, 'conflict')).select('이란·이스라엘').run()
    self.switch_page(app, 'weapons-monthly')
    self.assert_period(app, (date(2025, 1, 1), date(2025, 12, 31)))
    self.assertEqual(len(app.get('plotly_chart')), 2)
    self.switch_page(app, 'overview')
    self.assertEqual(
      app.date_input(key=self.widget_key(app, 'start')).value, date(2020, 1, 1)
    )
    self.assertEqual(
      app.date_input(key=self.widget_key(app, 'end')).value, date(2019, 12, 31)
    )
    self.assertEqual(len(app.metric), 0)
    app.date_input(key=self.widget_key(app, 'end')).set_value(date(2020, 2, 29)).run()
    self.assertFalse(app.exception)
    self.assert_period(app, (date(2020, 1, 1), date(2020, 2, 29)))

    self.switch_page(app, 'weapons-monthly')
    for key in ('start', 'end'):
      with self.subTest(cleared_date=key):
        previous_period = self.filters(app)['period']
        app.date_input(key=self.widget_key(app, key)).set_value(None).run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.date_input(key=self.widget_key(app, key)).value)
        self.assertEqual(self.filters(app)['period'], previous_period)
        self.assertIn('시작일과 종료일을 모두 선택', app.info[0].value)
        self.assertEqual(len(app.get('plotly_chart')), 0)
        self.switch_page(app, 'overview')
        self.assert_period(app, (date(2020, 1, 1), date(2020, 2, 29)))
        self.assertEqual(len(app.metric), 3)
        self.switch_page(app, 'weapons-monthly')
        self.assertIsNone(app.date_input(key=self.widget_key(app, key)).value)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assert_period(app, (date(2025, 1, 1), date(2025, 12, 31)))

  def test_unselected_categories_do_not_hide_top_three(self):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(
      timeout=30
    )
    app.switch_page('pages/02_weapons_monthly.py').run()
    for category in list(self.filters(app)['selected_categories']):
      app.checkbox(key=self.widget_key(app, f'category_{category}')).uncheck().run()
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
    pages = {
      key: default_filters(settings, key)
      for key in ('overview', 'weapons-monthly', 'technology-monthly')
    }
    pages['weapons-monthly'].update(
      conflict='삭제된 분쟁',
      period=(date(2026, 1, 1), date(2026, 2, 1)),
      start=date(2026, 1, 1),
      end=date(2026, 2, 1),
      selected_categories=['삭제된 범주'],
    )
    pages['technology-monthly']['selected_categories'] = []
    before = deepcopy(pages)
    state = {'page_filters': pages}
    with patch('utils.state.st.session_state', state):
      init_session_state(settings, page_key='weapons-monthly')
    self.assertEqual(
      pages['weapons-monthly'], default_filters(settings, 'weapons-monthly')
    )
    self.assertEqual(pages['overview'], before['overview'])
    self.assertEqual(pages['technology-monthly'], before['technology-monthly'])

  def test_incomplete_saved_period_is_repaired(self):
    settings = load_dashboard_snapshot()['settings']
    for period in [(), (date(2020, 2, 29),)]:
      with self.subTest(period=period):
        state = {'page_filters': {'overview': {'period': period}}}
        with patch('utils.state.st.session_state', state):
          init_session_state(settings)
        self.assertEqual(
          state['page_filters']['overview']['period'],
          (settings['start'], settings['end']),
        )
        self.assertEqual(
          state[filter_widget_key('overview', 'start')], settings['start']
        )
        self.assertEqual(state[filter_widget_key('overview', 'end')], settings['end'])

  def test_default_start_respects_available_data_dates(self):
    settings = load_dashboard_snapshot()['settings']
    cases = [
      (True, date(2015, 1, 1), date(2025, 12, 31), date(2016, 1, 1)),
      (False, date(2016, 1, 1), date(2025, 12, 31), date(2025, 1, 1)),
      (False, date(2025, 5, 1), date(2025, 12, 31), date(2025, 5, 1)),
      (False, date(2020, 1, 1), date(2020, 12, 31), date(2020, 12, 31)),
    ]
    for is_overview, start, end, expected_start in cases:
      with self.subTest(is_overview=is_overview, start=start, end=end):
        state = {}
        page_key = 'overview' if is_overview else 'weapons-monthly'
        current_settings = {**settings, 'start': start, 'end': end}
        with patch('utils.state.st.session_state', state):
          init_session_state(current_settings, page_key=page_key)
        self.assertEqual(
          state['page_filters'][page_key]['period'], (expected_start, end)
        )
        self.assertEqual(state[filter_widget_key(page_key, 'start')], expected_start)
        self.assertEqual(state[filter_widget_key(page_key, 'end')], end)


if __name__ == '__main__':
  unittest.main()
