'''페이지 이동·범주 검색 후에도 유지해야 하는 선택값과 콜백을 관리한다.'''

import streamlit as st


def init_session_state(settings):
  '''처음 접속한 사용자의 분쟁·기간·유형·범주 선택값을 초기화한다.'''
  defaults = {
    'conflict': '전체',
    'period': (settings['start'], settings['end']),
    'overview_kind': '전체',
  }
  for kind, categories in settings['default_categories'].items():
    defaults[f'selected_{kind}'] = list(categories)

  # 이미 사용자가 선택한 값은 유지하고, 아직 없는 항목만 기본값으로 채운다.
  for key, value in defaults.items():
    if key not in st.session_state:
      st.session_state[key] = value

  # 파일 갱신으로 사라진 선택값과 기간을 위젯 생성 전에 보정한다.
  if st.session_state['conflict'] not in ['전체', *settings['conflicts']]:
    st.session_state['conflict'] = '전체'
  period = st.session_state['period']
  if any(day < settings['start'] or day > settings['end'] for day in period):
    st.session_state['period'] = defaults['period']
  for kind, available in settings['categories'].items():
    key = f'selected_{kind}'
    selected = st.session_state[key]
    valid = [name for name in selected if name in available]
    st.session_state[key] = valid if valid or not selected else defaults[key]


def reset_filters():
  '''분쟁·기간·유형·범주를 기본값으로 돌리고 범주 검색어와 임시 위젯 값을 지운다.'''
  st.session_state['conflict'] = '전체'
  settings = st.session_state['_dashboard']['settings']
  st.session_state['period'] = (settings['start'], settings['end'])
  st.session_state['overview_kind'] = '전체'
  for kind, categories in settings['default_categories'].items():
    st.session_state[f'selected_{kind}'] = list(categories)

  # _로 시작하는 아래 키는 화면 위젯용 임시 값이다.
  # 제거 후 다음 렌더링에서 위의 기본 선택값으로 다시 채운다.
  for key in list(st.session_state):
    is_category_widget = key.startswith('_category_')
    is_search_widget = key.startswith('_search_')
    if is_category_widget or is_search_widget or key == '_overview_kind':
      del st.session_state[key]


def remember_kind():
  '''유형 선택 위젯의 값을 보관해 다른 페이지를 다녀와도 유지한다.'''
  st.session_state['overview_kind'] = st.session_state['_overview_kind']


def remember_category(kind, category, widget_key):
  '''체크박스 변경을 해당 유형의 보관용 범주 목록에 반영한다.'''
  # 검색으로 체크박스가 숨겨지면 Streamlit이 위젯 값을 정리할 수 있으므로 별도 목록에 보관한다.
  selection_key = f'selected_{kind}'
  selected = list(st.session_state[selection_key])
  is_checked = st.session_state[widget_key]
  if is_checked and category not in selected:
    selected.append(category)
  elif not is_checked and category in selected:
    selected.remove(category)
  st.session_state[selection_key] = sorted(selected)
