'''페이지별 필터 선택값과 위젯 변경 콜백을 관리한다.'''

from datetime import date

import streamlit as st

PAGE_KINDS = {'weapons-monthly': '무기', 'technology-monthly': '기술'}


def filter_widget_key(page_key, field):
  '''같은 필터라도 페이지마다 독립된 위젯 키를 반환한다.'''
  return f'_filter_{page_key}_{field}'


def get_page_filters(page_key=None):
  '''지정 페이지 또는 현재 페이지의 보관용 필터 값을 반환한다.'''
  if page_key is None:
    page_key = st.session_state['_filter_page']
  return st.session_state['page_filters'][page_key]


def default_filters(settings, page_key):
  '''페이지별 기본값을 만들고 시작일을 실제 데이터 범위 안으로 보정한다.'''
  start = date(2016 if page_key == 'overview' else 2025, 1, 1)
  start = min(max(start, settings['start']), settings['end'])
  filters = {
    'conflict': '전체',
    'period': (start, settings['end']),
    'start': start,
    'end': settings['end'],
  }
  if page_key == 'overview':
    filters['overview_kind'] = '전체'
  else:
    kind = PAGE_KINDS[page_key]
    filters['selected_categories'] = list(settings['default_categories'][kind])
    filters['category_search'] = ''
  return filters


def init_session_state(settings, *, page_key='overview'):
  '''현재 페이지의 필터를 초기화·보정하고 화면 위젯에 복원한다.'''
  defaults = default_filters(settings, page_key)
  pages = st.session_state.setdefault('page_filters', {})
  filters = pages.setdefault(page_key, {})
  for key, value in defaults.items():
    filters.setdefault(key, value)

  # 다른 페이지의 보관 값은 건드리지 않고, 방문한 페이지만 최신 데이터에 맞춘다.
  if filters['conflict'] not in ['전체', *settings['conflicts']]:
    filters['conflict'] = '전체'
  period = filters['period']
  if (
    len(period) != 2
    or any(
      day is None or day < settings['start'] or day > settings['end'] for day in period
    )
    or period[0] > period[1]
  ):
    period = filters['period'] = defaults['period']
    filters['start'], filters['end'] = period
  for field, day in zip(('start', 'end'), period):
    # 입력 중인 빈 날짜·역전된 날짜 쌍도 해당 페이지에 보관한다.
    value = filters[field]
    if value is not None and not settings['start'] <= value <= settings['end']:
      filters[field] = day

  if page_key == 'overview':
    if filters['overview_kind'] not in ['전체', '무기', '기술']:
      filters['overview_kind'] = '전체'
  else:
    available = settings['categories'][PAGE_KINDS[page_key]]
    selected = filters['selected_categories']
    valid = [name for name in selected if name in available]
    filters['selected_categories'] = (
      valid if valid or not selected else defaults['selected_categories']
    )

  st.session_state['_filter_page'] = page_key
  # 페이지 이동으로 Streamlit이 정리한 위젯도 보관용 값으로 다시 만든다.
  for field in ('conflict', 'start', 'end', 'overview_kind', 'category_search'):
    if field in filters:
      st.session_state[filter_widget_key(page_key, field)] = filters[field]


def reset_filters(page_key):
  '''현재 페이지의 필터·범주·검색어만 기본값으로 되돌린다.'''
  settings = st.session_state['_dashboard']['settings']
  st.session_state['page_filters'][page_key] = default_filters(settings, page_key)
  prefix = filter_widget_key(page_key, '')
  for key in list(st.session_state):
    if key.startswith(prefix):
      del st.session_state[key]


def remember_filter(page_key, field):
  '''위젯 선택을 해당 페이지에 보관해 다른 페이지의 선택과 분리한다.'''
  get_page_filters(page_key)[field] = st.session_state[
    filter_widget_key(page_key, field)
  ]


def remember_category(page_key, category, widget_key):
  '''검색으로 숨겨져도 유지할 범주 목록을 해당 페이지에 보관한다.'''
  filters = get_page_filters(page_key)
  selected = list(filters['selected_categories'])
  is_checked = st.session_state[widget_key]
  if is_checked and category not in selected:
    selected.append(category)
  elif not is_checked and category in selected:
    selected.remove(category)
  filters['selected_categories'] = sorted(selected)
