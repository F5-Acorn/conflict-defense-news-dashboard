'''앱 설정, 상단 페이지 메뉴와 페이지별 독립 필터를 연결한다.'''

import streamlit as st

from data.excel_loader import DataValidationError
from data.sample_data import load_dashboard_snapshot
from ui.components import apply_styles, render_filters
from utils.state import init_session_state

st.set_page_config(
  page_title='해외 언론보도 데이터 기반 주요 분쟁의 무기·방산기술 사용 동향 분석 대시보드',
  page_icon='🌐',
  layout='wide',
  initial_sidebar_state='collapsed',
)

apply_styles()
try:
  snapshot = load_dashboard_snapshot()
except DataValidationError as exc:
  st.error(f'데이터를 불러올 수 없습니다. {exc}')
  st.stop()
st.session_state['_dashboard'] = snapshot
settings = snapshot['settings']
if settings['start'] is None:
  st.info('등록된 기사가 없습니다. 기사 데이터를 추가하면 조회할 수 있습니다.')
  st.stop()

# 첫 자동 탐색에서도 충돌하지 않도록 숫자 접두사를 제외한 파일명도 구분한다.
# 각 페이지의 URL을 지정하며 보도 동향을 첫 화면으로 사용한다.
page = st.navigation(
  [
    st.Page(
      'pages/01_overview.py',
      title='분쟁별 방산 무기/기술 사용 보도 동향',
      url_path='overview',
      default=True,
    ),
    st.Page(
      'pages/02_weapons_monthly.py',
      title='방산 무기 월간 분석',
      url_path='weapons-monthly',
    ),
    st.Page(
      'pages/03_technology_monthly.py',
      title='방산 기술 월간 분석',
      url_path='technology-monthly',
    ),
  ],
  position='top',
)

# st.title(page.title)
# 필터는 같은 위치에 표시하되, 선택값과 위젯 키는 페이지마다 따로 관리한다.
# 기본 페이지의 url_path는 Streamlit에서 빈 문자열로 제공한다.
is_overview = page.url_path in ('', 'overview')
page_key = 'overview' if is_overview else page.url_path
init_session_state(settings, page_key=page_key)
period = render_filters(settings, page_key)
if period is not None:
  # 시작일과 종료일을 모두 선택한 경우에만 화면의 집계를 실행한다.
  page.run()
