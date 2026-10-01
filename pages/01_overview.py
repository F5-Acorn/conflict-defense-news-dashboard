'''선택 조건을 집계해 보도 동향 지표와 지도, 분쟁별 주요 범주를 표시한다.'''

from html import escape

import streamlit as st

from services.analysis_service import (
  article_totals,
)
from ui.components import render_analysis_indicators, render_classification_downloads
from ui.flags import render_flags
from ui.interactive import render_classification_details, render_map
from ui.maps import build_conflict_map
from utils.state import (
  apply_map_navigation,
  ensure_dashboard,
  filter_widget_key,
  get_page_filters,
  overview_map_view,
  remember_filter,
)


def toggle_category(identity):
  selected = st.session_state.get('_overview_selected_category')
  st.session_state['_overview_selected_category'] = (
    None if selected == identity else identity
  )


# app.py에서 유효한 월 범위를 확인한 뒤 실행한다.
ensure_dashboard('overview')
filters = get_page_filters()
conflict = filters['conflict']

snapshot = st.session_state['_dashboard']
settings = snapshot['settings']
conflicts = settings['conflicts']
articles = snapshot['overview_summary']['articles']
filtered_articles = (
  articles if conflict == '전체' else articles.loc[articles['conflict'].eq(conflict)]
)

analysis_count, usage_count = article_totals(filtered_articles)
if conflict == '전체':
  usage_count = snapshot['overview_summary']['usage_articles_total']
kinds = ['무기', '기술']
kind_text = '방산 무기·기술'
conflict_text = '국가간 분쟁 전체' if conflict == '전체' else f'{conflict} 분쟁'

# 지도 수치는 기사 지표에서, 주요 범주는 범주별 보도 수에서 각각 집계한다.
# 전체 선택 시 DB 로더의 분쟁 정렬 순서대로 지도와 왼쪽 카드를 표시한다.
selected_conflicts = list(conflicts) if conflict == '전체' else [conflict]
counts = filtered_articles.set_index('conflict')['usage_articles'].to_dict()
visible_conflicts = [item for item in selected_conflicts if counts.get(item, 0) > 0]
visible_counts = {item: counts[item] for item in visible_conflicts}
top_categories = {}
top_rankings = {}
for item in visible_conflicts:
  top_categories[item] = {}
  top_rankings[item] = {}
  for category_kind in kinds:
    ranking = snapshot['overview_summary']['rankings'][item][category_kind]
    top_rankings[item][category_kind] = ranking
    top_categories[item][category_kind] = ranking['category'].tolist()

empty_usage_message = '선택한 조건의 사용 보도가 없습니다.'

# 필터가 바뀌거나 더 이상 보이지 않는 태그를 선택한 경우 상세 명칭을 비운다.
selection_context = (snapshot['revision'], conflict)
if st.session_state.get('_overview_selection_context') != selection_context:
  st.session_state['_overview_selection_context'] = selection_context
  st.session_state['_overview_selected_category'] = None
selected_category = st.session_state.get('_overview_selected_category')
visible_category_ids = {
  (category_kind, settings['category_ids'][category_kind][row.category])
  for item in visible_conflicts
  for category_kind in kinds
  for row in top_rankings[item][category_kind].itertuples(index=False)
}
if selected_category not in visible_category_ids:
  selected_category = st.session_state['_overview_selected_category'] = None

# 본문 레이아웃
with st.container(key='overview_layout'):
  conflict_column, summary_column = st.columns([1, 1], gap='small')

# 본문 왼쪽
with conflict_column.container(height=650, border=True, key='overview_conflicts'):
  # 주요 방산 무기·기술 타이틀
  with st.container(
    horizontal=True, vertical_alignment='center', key='overview_heading'
  ):
    st.selectbox(
      '국가간 분쟁',
      ['전체', *conflicts],
      key=filter_widget_key('overview', 'conflict'),
      format_func=lambda value: '국가간 분쟁 전체' if value == '전체' else value,
      label_visibility='collapsed',
      width=200,
      on_change=remember_filter,
      args=('overview', 'conflict'),
    )
    st.subheader(
      ('주요 ' if conflict == '전체' else '분쟁 주요 ') + kind_text,
      width='content',
      anchor=False,
    )

  # 특정 분쟁 선택시 관련 보도 건수가 없는 경우
  if not visible_conflicts:
    st.info(empty_usage_message)

  for index, item in enumerate(visible_conflicts):
    config = conflicts[item]

    # 분쟁별 카드
    with st.container(border=False, key=f'overview_conflict_{index}'):
      html_text = f'''<div class="card-header">
                        <div class="card-title">
                          {render_flags(config["flag"])}
                          {escape(item)}
                          분쟁
                        </div>
                        <div class="report-summary">
                          <div class="report-label">방산 무기·기술 사용 보도 사례</div>
                          <div class="report-count" style="color:{config["color"]}">{counts[item]:,}건</div>
                        </div>
                      </div>'''
      st.html(html_text)

      for category_kind in kinds:
        ranking = top_rankings[item][category_kind]
        if ranking.empty:
          continue
        with st.container(key=f'overview_category_row_{index}_{category_kind}'):
          label_column, tags_column = st.columns([1, 9], gap='small')
          with label_column:
            st.caption(f'주요 {category_kind}')
          with (
            tags_column,
            st.container(horizontal=True, key=f'overview_tags_{index}_{category_kind}'),
          ):
            for row in ranking.itertuples(index=False):
              category_id = settings['category_ids'][category_kind][row.category]
              identity = (category_kind, category_id)
              st.button(
                f'{row.category} ({row.count:,}건)',
                key=f'overview_tag_{index}_{category_id}',
                type='primary' if selected_category == identity else 'secondary',
                on_click=toggle_category,
                args=(identity,),
              )

# 본문 오른쪽
with summary_column.container(height='content', border=False, key='overview_summary'):
  with st.container(
    horizontal=True, border=False, key='overview_metrics', gap='medium'
  ):
    with st.container(width='stretch', key='overview_indicators'):
      render_analysis_indicators(kind_text, analysis_count, usage_count)
    with st.container(width=250, key='overview_downloads'):
      render_classification_downloads(settings)

  # 국가간 분쟁 전체 방산 무기·기술 사용 보도 현황 지도
  with st.container(border=False, key='overview_map_half'):
    st.subheader(f'{conflict_text} {kind_text} 사용 보도 현황 지도', anchor=False)
    scale_max = max(counts.values(), default=0)
    conflict_ids = {name: cid for cid, name in settings['conflict_names_by_id'].items()}
    map_context = f'{snapshot["revision"]}:{conflict}'
    map_html = snapshot['view_cache'].get(
      ('map', conflict),
      lambda: (
        build_conflict_map(
          visible_counts,
          top_categories,
          conflicts,
          scale_max=scale_max,
          conflict_ids=conflict_ids,
          context=map_context,
        )
        .get_root()
        .render()
      ),
    )

    # 지도 영역
    event = render_map(map_html, map_context, overview_map_view(conflict))
    action = event.action
    if (
      isinstance(action, dict)
      and action.get('context') == map_context
      and isinstance(action.get('conflict_id'), str)
      and settings['conflict_names_by_id'].get(action.get('conflict_id'))
      in visible_conflicts
    ):
      page_key = apply_map_navigation(
        settings, action.get('conflict_id'), action.get('target_page')
      )
      if page_key:
        path = {
          'annual': 'pages/02_annual.py',
          'monthly': 'pages/03_monthly.py',
          'weekly': 'pages/04_weekly.py',
        }[page_key]
        st.switch_page(path)

  # 세부 명칭
  with st.container(border=False, key='overview_details_half'):
    if selected_category is not None:
      selected_kind, category_id = selected_category
      category_name = next(
        name
        for name, cid in settings['category_ids'][selected_kind].items()
        if cid == category_id
      )
      names = snapshot['classification_details'][selected_kind][category_name]
      render_classification_details(
        category_name, names, f'{map_context}:{selected_kind}:{category_id}'
      )
