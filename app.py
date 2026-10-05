'''앱 설정, 제목 아래 페이지 메뉴와 페이지별 독립 필터를 연결한다.'''

import streamlit as st

from data.snapshot import load_dashboard_snapshot
from data.table_contract import DataValidationError
from ui.components import apply_styles, render_filters
from ui.loading import loading_html
from utils.state import init_session_state

st.set_page_config(
  page_title='해외 언론 보도 기반 국가간 분쟁의 방산 무기·기술 사용 동향 분석 대시보드',  # 브라우저 탭명 설정
  page_icon='🌐',  # 브라우저 탭 파비콘 설정
  layout='wide',  # 본문 배치 레이아웃 설정 centered 보다 넓게 배치
  initial_sidebar_state='collapsed',  # 왼쪽 사이드바 상태 설정 (접힌 상태로 시작)
)

# assets/styles.css 및 ui/frontend/loading.css 스타일 적용
apply_styles()

# 로딩 표시 여부와 관계없이 매 실행마다 같은 위치에 빈 자리 할당
initial_loading = st.empty()

# 세션에 대시보드 데이터가 없으면 로딩 문구를 표시
if '_dashboard' not in st.session_state:
  initial_loading.html(loading_html('대시보드를 불러오는 중…', initial=True))

# 데이터 로딩 에러 예외처리 (데이터 로드에 실패해도 로딩 표기는 비가시화)
load_error = None
try:
  snapshot = load_dashboard_snapshot()
except DataValidationError as exc:
  load_error = exc
finally:
  initial_loading.empty()

# 데이터 로딩 실패시 streamlit 코드 실행 중단
if load_error is not None:
  st.error(f'데이터를 불러올 수 없습니다. {load_error}')
  st.stop()

previous_snapshot = st.session_state.get('_dashboard')
if (
  previous_snapshot is not None
  and previous_snapshot['revision'] != snapshot['revision']
):
  for key in list(st.session_state):
    if (
      key.startswith(('_monthly_ui_', 'interactive_'))
      or key == '_overview_selected_category'
    ):
      st.session_state.pop(key, None)
st.session_state['_dashboard'] = snapshot
settings = snapshot['settings']
if settings['start'] is None:
  st.info('등록된 기사가 없습니다. 기사 데이터를 추가하면 조회할 수 있습니다.')
  st.stop()

# 첫 자동 탐색에서도 충돌하지 않도록 숫자 접두사를 제외한 파일명도 구분한다.
# 각 페이지의 URL을 지정하며 보도 동향을 첫 화면으로 사용한다.
pages = [
  st.Page(
    'pages/01_overview.py',
    title='종합 분석',
    url_path='overview',
    default=True,
  ),
  st.Page(
    'pages/02_annual.py',
    title='연간 분석',
    url_path='annual',
  ),
  st.Page(
    'pages/03_monthly.py',
    title='월간 분석',
    url_path='monthly',
  ),
  st.Page(
    'pages/04_weekly.py',
    title='주간 분석',
    url_path='weekly',
  ),
]
page = st.navigation(pages, position='hidden')
initial_page = st.session_state.pop('_initial_page', None)
if initial_page:
  target = next((item for item in pages if item.url_path == initial_page), None)
  if target is not None and page.url_path != initial_page:
    st.switch_page(target)
with st.container(key='dashboard_header'):
  st.subheader(
    '해외 언론 보도 기반 국가간 분쟁의 방산 무기·기술 사용 동향 분석', anchor=False
  )

  # 네비게이션 메뉴
  with st.container(key='dashboard_navigation', horizontal=True, gap='small'):
    for target in pages:
      st.page_link(target, label=target.title, width='content')

# 필터는 같은 위치에 표시하되, 선택값과 위젯 키는 페이지마다 따로 관리한다.
# 기본 페이지의 url_path는 Streamlit에서 빈 문자열로 제공한다.
is_overview = page.url_path in ('', 'overview')
page_key = 'overview' if is_overview else page.url_path
init_session_state(settings, page_key=page_key)
if is_overview:
  page.run()
else:
  render_filters(settings, page_key)
  page.run()
