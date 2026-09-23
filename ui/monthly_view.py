'''무기·기술 월간 페이지가 함께 사용하는 추이, 범주 선택과 Top 3 화면을 구성한다.'''

import streamlit as st

from services.analysis_service import (
  filter_data,
  is_partial_month,
  latest_distribution,
  monthly_trend,
)
from ui.charts import distribution_chart, trend_chart
from ui.components import render_category_picker


def render_monthly(kind):
  '''유형('무기' 또는 '기술')과 현재 분쟁·기간 선택으로 월간 분석 화면을 표시한다.'''
  start, end = st.session_state['period']
  conflict = st.session_state['conflict']
  # 월간 분석은 기사 전체 지표가 아닌 범주별 보도 수를 사용한다.
  snapshot = st.session_state['_dashboard']
  settings = snapshot['settings']
  categories = snapshot['category_daily']
  filtered_categories = filter_data(categories, conflict, start, end, kind)
  ranking, distribution = latest_distribution(filtered_categories, end)

  trend_column, picker_column = st.columns([3, 1.05], gap='medium')
  # 위젯부터 실행하되, 화면상의 위치는 오른쪽 열로 유지한다.
  with picker_column:
    selected = render_category_picker(kind, settings)
  trend = monthly_trend(filtered_categories, selected, start, end)
  with trend_column, st.container(border=True, key=f'trend_{kind}'):
    st.subheader(f'분쟁/기간별 방산 {kind} 월간 사용 보도 추이')
    st.caption('선택한 범주의 월별 기사 수')
    if not selected:
      st.info('추이를 확인할 범주를 하나 이상 선택해주세요.')
    else:
      if not trend['count'].any():
        st.info('선택한 범주의 사용 보도가 없어 0건으로 표시합니다.')
      figure = trend_chart(trend, kind, start, end, settings['category_colors'])
      st.plotly_chart(
        figure,
        theme=None,
        width='stretch',
        key=f'trend_chart_{kind}',
        config={'displayModeBar': False},
      )

  # Top 3는 위의 체크박스 선택과 무관하므로 범주를 모두 해제해도 계속 표시한다.
  with st.container(border=True, key=f'distribution_{kind}'):
    st.subheader(f'분쟁별 사용 방산 {kind} 최신 Top 3 보도 사례 분포')
    partial = ' · 부분 기간' if is_partial_month(end, start, end) else ''
    st.caption(
      f'최신 월: {end:%Y.%m}{partial} · 선택 기간의 마지막 월 보도 수 순 · 추이 범주 선택과 별도'
    )
    if ranking.empty:
      st.info('선택한 조건의 최신 월 보도가 없습니다.')
    else:
      figure = distribution_chart(ranking, distribution, settings['conflicts'])
      st.plotly_chart(
        figure,
        theme=None,
        width='stretch',
        key=f'distribution_chart_{kind}',
        config={'displayModeBar': False},
      )
