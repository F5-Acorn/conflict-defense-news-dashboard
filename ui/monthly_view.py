'''월간 추이·범주 선택·기사 패널과 판정 분포·범주 워드클라우드를 구성한다.'''

import hashlib
import json

import streamlit as st

from services.analysis_service import filter_data, monthly_trend
from services.detail_service import (
  article_details,
  category_frequencies,
  judgement_distribution,
  valid_article_request,
)
from ui.charts import mosaic_chart, trend_chart
from ui.components import render_category_picker
from ui.interactive import render_interactive_trend
from ui.wordcloud_view import wordcloud_image
from utils.state import get_page_filters


def render_monthly(kind):
  filters = get_page_filters()
  page_key = st.session_state['_filter_page']
  start, end = filters['period']
  conflict = filters['conflict']
  snapshot = st.session_state['_dashboard']
  settings = snapshot['settings']
  category_ids = settings['category_ids'][kind]
  conflict_id = next(
    (cid for cid, name in settings['conflict_names_by_id'].items() if name == conflict),
    None,
  )
  filtered_categories = filter_data(
    snapshot['category_daily'], conflict, start, end, kind
  )
  reports = filter_data(snapshot['reports'], conflict, start, end, kind)
  frequencies = category_frequencies(reports)
  trend_column, picker_column = st.columns([3, 1.05], gap='medium')
  with picker_column:
    selected = render_category_picker(kind, settings, category_counts=frequencies)
  trend = monthly_trend(filtered_categories, selected, start, end)
  context = hashlib.sha256(
    json.dumps(
      [
        snapshot['revision'],
        page_key,
        conflict_id,
        filters['start_month'],
        filters['end_month'],
        selected,
      ],
      ensure_ascii=False,
    ).encode()
  ).hexdigest()
  state_key = f'_monthly_ui_{page_key}'
  ui_state = st.session_state.setdefault(
    state_key, {'context': context, 'request': None}
  )
  if ui_state['context'] != context:
    ui_state = st.session_state[state_key] = {'context': context, 'request': None}
  drawer = None
  request = ui_state['request']
  if request:
    drawer = article_details(
      reports, request['category_id'], request['month'], request['page']
    )
    drawer.update(
      category=next(
        name for name, cid in category_ids.items() if cid == request['category_id']
      ),
      category_id=request['category_id'],
      month=request['month'],
      conflict=conflict,
    )

  with trend_column, st.container(border=True, key=f'trend_{kind}'):
    conflict_text = '' if conflict == '전체' else f'{conflict} 분쟁 '
    st.subheader(
      f'{conflict_text}방산 {kind} 사용 보도 추이 ({start:%Y.%m}–{end:%Y.%m})'
    )
    st.caption('점을 선택하면 전월 대비 증감과 관련 기사를 확인할 수 있습니다.')
    if not selected:
      st.info('추이를 확인할 범주를 하나 이상 선택해주세요.')
    else:
      if not trend['count'].any():
        st.info('선택한 범주의 사용 보도가 없어 0건으로 표시합니다.')
      figure = trend_chart(
        trend, kind, start, end, settings['category_colors'], category_ids
      )
      render_interactive_trend(
        figure,
        context,
        kind,
        drawer,
        page_key,
        conflict_id,
        on_action=lambda: handle_article_action(
          f'interactive_{page_key}',
          state_key,
          context,
          kind,
          conflict_id,
          [category_ids[name] for name in selected],
          start,
          end,
        ),
      )

  mosaic_column, words_column = st.columns(2, gap='medium')
  with mosaic_column, st.container(border=True):
    st.subheader('범주별 판정 상태 분포')
    st.caption(
      '범주별 판정 비율 · 막대 높이는 동일하며, 같은 기사도 범주마다 각각 집계합니다.'
    )
    distribution = judgement_distribution(reports, selected)
    if not selected:
      st.info('판정 상태를 확인할 범주를 하나 이상 선택해주세요.')
    elif not distribution['count'].sum():
      st.info('선택한 조건의 판정 결과가 없습니다.')
    else:
      st.plotly_chart(
        mosaic_chart(distribution),
        key=f'mosaic_{page_key}',
        theme=None,
        width='stretch',
        config={'displayModeBar': False},
      )
  with words_column, st.container(border=True):
    st.subheader(f'{kind} 범주 워드클라우드')
    st.caption(f'분쟁·기간 내 모든 {kind} 범주 · 범주별 사용 확인 기사 수')
    content = wordcloud_image(frequencies)
    if content is None:
      st.info('선택한 조건에서 사용이 확인된 범주가 없습니다.')
    else:
      st.image(content, width='stretch')
      # 작은 이미지에 생략된 범주도 전체 집계에서 확인할 수 있다.
      with st.expander('전체 범주별 기사 수'):
        st.dataframe(
          [{'범주': name, '기사 수': count} for name, count in frequencies.items()],
          hide_index=True,
          width='stretch',
        )


def handle_article_action(
  widget_key, state_key, context, kind, conflict_id, allowed_ids, start, end
):
  """컴포넌트 콜백에서 먼저 상태를 갱신해 추가 rerun 없이 최신 목록을 그린다."""
  action = st.session_state[widget_key].get('action')
  ui_state = st.session_state.get(state_key)
  if not ui_state or ui_state['context'] != context:
    return
  if (
    not isinstance(action, dict)
    or action.get('context') != context
    or action.get('kind') != kind
    or action.get('conflict_id') != conflict_id
  ):
    return
  if action.get('type') == 'close_articles':
    ui_state['request'] = None
  elif valid_article_request(action, context, allowed_ids, start, end, kind):
    page = action.get('page', 1)
    if isinstance(page, int) and not isinstance(page, bool) and page > 0:
      ui_state['request'] = {
        'category_id': action['category_id'],
        'month': action['month'],
        'page': page,
      }
