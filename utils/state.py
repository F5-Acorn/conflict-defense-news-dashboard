'''페이지별 월 필터와 범주 선택, 위젯 변경 콜백을 관리한다.'''

from calendar import monthrange
from datetime import date

import streamlit as st

PAGE_KINDS = {'weapons-monthly': '무기', 'technology-monthly': '기술'}
MAX_CATEGORIES = 5


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


def month_period(start_month, end_month):
  '''선택한 두 월을 양 끝 날짜를 포함하는 기간으로 바꾼다.'''
  start = date.fromisoformat(f'{start_month}-01')
  end = date.fromisoformat(f'{end_month}-01')
  return start, end.replace(day=monthrange(end.year, end.month)[1])


def default_filters(settings, page_key):
  options = month_options(settings)
  start = '2016-01' if page_key == 'overview' else '2025-09'
  start = min(max(start, options[0]), options[-1])
  filters = {
    'conflict': '전체',
    'start_month': start,
    'end_month': options[-1],
    'period': month_period(start, options[-1]),
  }
  if page_key == 'overview':
    filters['overview_kind'] = '전체'
  else:
    # 분쟁·기간이 확정된 첫 유효 렌더링에서 실제 보도 순위로 채운다.
    filters['selected_categories'] = []
    filters['categories_initialized'] = False
    filters['category_search'] = ''
  return filters


def init_session_state(settings, *, page_key='overview'):
  '''현재 페이지만 보정하며 기존 일 단위 저장값을 월 단위로 이행한다.'''
  defaults = default_filters(settings, page_key)
  pages = st.session_state.setdefault('page_filters', {})
  filters = pages.setdefault(page_key, {})
  if page_key in PAGE_KINDS and 'categories_initialized' not in filters:
    # 이전 버전의 저장값은 전체 선택 해제([])를 포함해 사용자 상태로 보존한다.
    filters['categories_initialized'] = 'selected_categories' in filters
  old_period = filters.get('period', ())
  for index, field in enumerate(('start_month', 'end_month')):
    old = filters.pop(('start', 'end')[index], None)
    if old is None and len(old_period) == 2:
      old = old_period[index]
    if field not in filters and isinstance(old, date):
      filters[field] = old.strftime('%Y-%m')
  for key, value in defaults.items():
    filters.setdefault(key, value)
  if filters['conflict'] not in ['전체', *settings['conflicts']]:
    filters['conflict'] = '전체'
  options = month_options(settings)
  for field in ('start_month', 'end_month'):
    if filters[field] not in options:
      filters[field] = defaults[field]
  if filters['start_month'] <= filters['end_month']:
    filters['period'] = month_period(filters['start_month'], filters['end_month'])
  elif len(filters['period']) != 2:
    filters['period'] = defaults['period']
  if page_key == 'overview':
    if filters['overview_kind'] not in ['전체', '무기', '기술']:
      filters['overview_kind'] = '전체'
  else:
    available = settings['categories'][PAGE_KINDS[page_key]]
    selected = filters['selected_categories']
    valid = list(dict.fromkeys(name for name in selected if name in available))
    filters['selected_categories'] = valid[:MAX_CATEGORIES]

  previous = st.session_state.get('_filter_page')
  if previous != page_key:
    clear_monthly_ui(previous)
    clear_monthly_ui(page_key)
  st.session_state['_filter_page'] = page_key
  for field in (
    'conflict',
    'start_month',
    'end_month',
    'overview_kind',
    'category_search',
  ):
    if field in filters:
      st.session_state[filter_widget_key(page_key, field)] = filters[field]


def initialize_category_selection(page_key, ordered_categories):
  '''페이지 첫 유효 렌더링에만 현재 정렬의 앞 3개를 선택한다.'''
  filters = get_page_filters(page_key)
  if not filters['categories_initialized']:
    filters['selected_categories'] = list(ordered_categories[:3])
    filters['categories_initialized'] = True


def clear_monthly_ui(page_key):
  '''필터와 별도로 관리하는 기사 패널 요청을 폐기한다.'''
  if page_key:
    st.session_state.pop(f'_monthly_ui_{page_key}', None)


def reset_filters(page_key):
  settings = st.session_state['_dashboard']['settings']
  defaults = default_filters(settings, page_key)
  filters = get_page_filters(page_key)
  # 범주 선택·검색어·최초 선택 완료 상태는 유지하고 조회 필터만 복원한다.
  for field in ('conflict', 'start_month', 'end_month', 'period', 'overview_kind'):
    if field in defaults:
      filters[field] = defaults[field]
      st.session_state.pop(filter_widget_key(page_key, field), None)
  clear_monthly_ui(page_key)


def remember_filter(page_key, field):
  get_page_filters(page_key)[field] = st.session_state[
    filter_widget_key(page_key, field)
  ]
  if field != 'category_search':
    clear_monthly_ui(page_key)


def remember_category(page_key, category, widget_key):
  filters = get_page_filters(page_key)
  selected = list(filters['selected_categories'])
  is_checked = st.session_state[widget_key]
  if is_checked and category not in selected:
    if len(selected) < MAX_CATEGORIES:
      selected.append(category)
    else:
      st.session_state[widget_key] = False
  elif not is_checked and category in selected:
    selected.remove(category)
  filters['selected_categories'] = sorted(selected)
  clear_monthly_ui(page_key)


def apply_map_navigation(settings, conflict_id, kind):
  '''유효한 지도 이동 요청의 분쟁만 목적 페이지에 적용한다.'''
  page_key = {'무기': 'weapons-monthly', '기술': 'technology-monthly'}.get(kind)
  names = settings['conflict_names_by_id']
  if page_key is None or conflict_id not in names:
    return None
  pages = st.session_state.setdefault('page_filters', {})
  filters = pages.setdefault(page_key, default_filters(settings, page_key))
  filters['conflict'] = names[conflict_id]
  clear_monthly_ui(page_key)
  return page_key
