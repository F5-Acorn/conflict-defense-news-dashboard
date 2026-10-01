'''페이지별 기간 필터와 범주 선택, 위젯 변경 콜백을 관리한다.'''

from calendar import monthrange
from datetime import date, timedelta
from uuid import uuid4

import streamlit as st

PERIOD_PAGES = {'annual', 'monthly', 'weekly'}
MAX_CATEGORIES = 5


def ensure_dashboard(page_key):
  '''서버 첫 접속이 pages 파일로 향해도 공통 진입점에서 초기화한다.'''
  if '_dashboard' not in st.session_state:
    st.session_state['_initial_page'] = page_key
    st.switch_page('app.py')


def filter_widget_key(page_key, field):
  return f'_filter_{page_key}_{field}'


def get_page_filters(page_key=None):
  if page_key is None:
    page_key = st.session_state['_filter_page']
  return st.session_state['page_filters'][page_key]


def month_options(settings):
  first, last = settings['start'], settings['end']
  start = first.year * 12 + first.month - 1
  end = last.year * 12 + last.month - 1
  return [f'{value // 12:04d}-{value % 12 + 1:02d}' for value in range(start, end + 1)]


def period_options(settings, page_key):
  '''연·월·주 선택지를 데이터 기간과 겹치는 단위로 만든다.'''
  first, last = settings['start'], settings['end']
  if page_key == 'annual':
    return [str(year) for year in range(first.year, last.year + 1)]
  if page_key == 'monthly':
    return month_options(settings)
  if page_key == 'weekly':
    monday = first - timedelta(days=first.weekday())
    final_monday = last - timedelta(days=last.weekday())
    return [
      (monday + timedelta(days=7 * index)).isoformat()
      for index in range((final_monday - monday).days // 7 + 1)
    ]
  raise ValueError(f'지원하지 않는 기간 페이지: {page_key}')


def period_bounds(page_key, value):
  '''단일 연·월·주 선택값을 양 끝 날짜를 포함하는 기간으로 바꾼다.'''
  if page_key == 'annual':
    year = int(value)
    return date(year, 1, 1), date(year, 12, 31)
  if page_key == 'monthly':
    start = date.fromisoformat(f'{value}-01')
    return start, start.replace(day=monthrange(start.year, start.month)[1])
  if page_key == 'weekly':
    monday = date.fromisoformat(value)
    return monday, monday + timedelta(days=6)
  raise ValueError(f'지원하지 않는 기간 페이지: {page_key}')


def period_label(page_key, value):
  if page_key == 'annual':
    return f'{value}년'
  if page_key == 'monthly':
    return month_label(value)
  start, end = period_bounds(page_key, value)
  return f'{start:%Y.%m.%d}~{end:%m.%d}'


def month_label(value):
  year, month = value.split('-')
  return f'{year}년 {int(month)}월'


def default_filters(settings, page_key):
  if page_key == 'overview':
    return {
      'conflict': '전체',
      'period': (settings['start'], settings['end']),
      'overview_kind': '전체',
    }
  if page_key in PERIOD_PAGES:
    selected_period = period_options(settings, page_key)[-1]
    return {
      'conflict': '전체',
      'kind': '전체',
      'selected_period': selected_period,
      'period': period_bounds(page_key, selected_period),
      'selected_category_ids': [],
      'categories_initialized': False,
      'category_search': '',
      'article_category_id': None,
    }
  raise ValueError(f'지원하지 않는 페이지: {page_key}')


def init_session_state(settings, *, page_key='overview'):
  '''현재 페이지의 분쟁·기간·유형·범주 선택을 보정한다.'''
  defaults = default_filters(settings, page_key)
  pages = st.session_state.setdefault('page_filters', {})
  filters = pages.setdefault(page_key, {})
  for key, value in defaults.items():
    filters.setdefault(key, value)
  if filters['conflict'] not in ['전체', *settings['conflicts']]:
    filters['conflict'] = '전체'
  if page_key == 'overview':
    filters['period'] = defaults['period']
    filters['overview_kind'] = '전체'
    for field in ('start', 'end', 'start_month', 'end_month'):
      filters.pop(field, None)
      st.session_state.pop(filter_widget_key(page_key, field), None)
  elif page_key in PERIOD_PAGES:
    if filters['selected_period'] not in period_options(settings, page_key):
      filters['selected_period'] = defaults['selected_period']
    filters['period'] = period_bounds(page_key, filters['selected_period'])
    if filters['kind'] not in ('전체', '무기', '기술'):
      filters['kind'] = '전체'
    allowed_kinds = (
      ('무기', '기술') if filters['kind'] == '전체' else (filters['kind'],)
    )
    allowed = {
      cid for kind in allowed_kinds for cid in settings['category_ids'][kind].values()
    }
    filters['selected_category_ids'] = list(
      dict.fromkeys(cid for cid in filters['selected_category_ids'] if cid in allowed)
    )[:MAX_CATEGORIES]

  previous = st.session_state.get('_filter_page')
  if previous != page_key:
    clear_monthly_ui(previous)
    clear_monthly_ui(page_key)
  st.session_state['_filter_page'] = page_key
  for field in (
    'conflict',
    'overview_kind',
    'kind',
    'selected_period',
    'category_search',
  ):
    if field in filters:
      st.session_state[filter_widget_key(page_key, field)] = filters[field]


def clear_monthly_ui(page_key):
  '''필터와 별도로 관리하는 기사 패널 요청을 폐기한다.'''
  if page_key:
    st.session_state.pop(f'_monthly_ui_{page_key}', None)


def reset_filters(page_key):
  settings = st.session_state['_dashboard']['settings']
  defaults = default_filters(settings, page_key)
  filters = get_page_filters(page_key)
  # 조회 필터를 복원하고 분석 페이지의 범주 선택·검색어도 초기화한다.
  fields = (
    ('conflict', 'kind', 'selected_period', 'period')
    if page_key in PERIOD_PAGES
    else ('conflict', 'period', 'overview_kind')
  )
  for field in fields:
    if field in defaults:
      filters[field] = defaults[field]
      st.session_state.pop(filter_widget_key(page_key, field), None)
  if page_key in PERIOD_PAGES:
    filters['selected_category_ids'] = []
    filters['categories_initialized'] = False
    filters['category_search'] = ''
    filters['article_category_id'] = None
    st.session_state.pop(filter_widget_key(page_key, 'category_search'), None)
  clear_monthly_ui(page_key)


def remember_filter(page_key, field):
  widget_key = filter_widget_key(page_key, field)
  # 초기화·페이지 이동 직후에는 삭제된 위젯의 이전 이벤트가 도착할 수 있다.
  if widget_key not in st.session_state:
    return
  get_page_filters(page_key)[field] = st.session_state[widget_key]
  if page_key in PERIOD_PAGES and field == 'kind':
    filters = get_page_filters(page_key)
    filters['selected_category_ids'] = []
    filters['categories_initialized'] = False
  if field != 'category_search':
    clear_monthly_ui(page_key)


def remember_period_category(page_key, category_id, widget_key):
  if widget_key not in st.session_state:
    return
  filters = get_page_filters(page_key)
  selected = list(filters['selected_category_ids'])
  checked = st.session_state[widget_key]
  if checked and category_id not in selected:
    if len(selected) < MAX_CATEGORIES:
      selected.append(category_id)
    else:
      st.session_state[widget_key] = False
  elif not checked and category_id in selected:
    selected.remove(category_id)
  filters['selected_category_ids'] = selected
  clear_monthly_ui(page_key)


def overview_map_view(conflict):
  '''데이터 갱신과 페이지 이동에는 유지하고 분쟁 변경 때만 지도 시점을 새로 만든다.'''
  view = st.session_state.setdefault(
    '_overview_map_view',
    {'storage_key': f'dashboard-map:{uuid4().hex}', 'conflict': None},
  )
  if view['conflict'] != conflict:
    view['conflict'] = conflict
    view['focus_token'] = uuid4().hex
  return {key: view[key] for key in ('storage_key', 'focus_token')}


def apply_map_navigation(settings, conflict_id, target_page):
  '''유효한 지도 이동 요청의 분쟁만 목적 페이지에 적용한다.'''
  names = settings['conflict_names_by_id']
  if (
    not isinstance(target_page, str)
    or target_page not in PERIOD_PAGES
    or not isinstance(conflict_id, str)
    or conflict_id not in names
  ):
    return None
  page_key = target_page
  pages = st.session_state.setdefault('page_filters', {})
  filters = pages.setdefault(page_key, default_filters(settings, page_key))
  filters['conflict'] = names[conflict_id]
  clear_monthly_ui(page_key)
  return page_key
