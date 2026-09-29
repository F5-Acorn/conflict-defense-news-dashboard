'''선택 조건을 집계해 보도 동향 지표와 지도, 분쟁별 주요 범주를 표시한다.'''

import streamlit as st

from services.analysis_service import article_totals, filter_data, ranked_categories
from services.detail_service import classification_details
from ui.components import category_details_card, conflict_card
from ui.interactive import render_map
from ui.maps import build_conflict_map
from utils.state import apply_map_navigation, get_page_filters

# app.py에서 유효한 월 범위를 확인한 뒤 실행한다.
filters = get_page_filters()
start, end = filters['period']
conflict = filters['conflict']
kind = filters['overview_kind']

snapshot = st.session_state['_dashboard']
settings = snapshot['settings']
conflicts = settings['conflicts']
classification_counts = settings['classification_counts']
articles, categories = snapshot['article_daily'], snapshot['category_daily']
filtered_articles = filter_data(articles, conflict, start, end, kind)
analysis_count, usage_count = article_totals(filtered_articles)
kinds = ['무기', '기술'] if kind == '전체' else [kind]
kind_text = '방산 ' + '무기·기술' if kind == '전체' else kind
conflict_text = '분쟁별' if conflict == '전체' else f'{conflict} 분쟁'

# 분류 수는 기간·분쟁과 무관한 기준 정보이다.
classification_count = sum(classification_counts[item] for item in kinds)

# 지도 수치는 기사 지표에서, 주요 범주는 범주별 보도 수에서 각각 집계한다.
# 전체 선택 시 DB 로더의 분쟁 정렬 순서대로 지도와 오른쪽 카드를 표시한다.
selected_conflicts = list(conflicts) if conflict == '전체' else [conflict]
counts = filtered_articles.groupby('conflict')['usage_articles'].sum().to_dict()
visible_conflicts = [item for item in selected_conflicts if counts.get(item, 0) > 0]
visible_counts = {item: counts[item] for item in visible_conflicts}
top_categories = {}
for item in visible_conflicts:
  top_categories[item] = {}
  for category_kind in kinds:
    filtered_categories = filter_data(categories, item, start, end, category_kind)
    ranking = ranked_categories(filtered_categories)
    top_categories[item][category_kind] = ranking['category'].tolist()

empty_usage_message = '선택한 조건의 사용 보도가 없습니다.'

# 상단에는 기존 순서와 디자인으로 기사 지표 카드 3개를 표시한다.
analysis_column, usage_column, classification_column = st.columns(3)

analysis_column.metric(
  '전체 분석 기사 수',
  f'{analysis_count:,}건',
  border=True,
  help=f'분쟁·기간별 {kind_text} 언급이 확인된 기사',
)
with usage_column.container(key='usage_count'):
  st.metric(
    f'{kind_text} 사용 사례 보도 수',
    f'{usage_count:,}건',
    border=True,
    help=f'분쟁·기간별 {kind_text}의 사용 사례가 확인된 기사',
  )
with classification_column.container():
  st.metric(
    f'{kind_text} 분류 수',
    f'{classification_count:,}개',
    border=True,
    help=f'{kind_text} 기준이 된 범주의 개수로, 분쟁·기간 필터에 따라 바뀌지 않습니다.',
  )

# 지도와 주요 범주를 2:1로 나눈다. 좁은 화면에서는 기본 반응형 배치로 위아래에 놓인다.
# 열 자체에 테두리를 적용해 두 섹션의 위·아래 경계를 같은 높이로 맞춘다.
map_column, details_column = st.columns([2, 1], gap='medium')
with map_column.container(height=740):
  st.subheader(f'{conflict_text} {kind_text} 사용 보도 현황 지도')
  if not visible_conflicts:
    st.info(empty_usage_message)
  scale_articles = filter_data(articles, '전체', start, end, kind)
  scale_counts = scale_articles.groupby('conflict')['usage_articles'].sum()
  scale_max = int(scale_counts.max()) if not scale_counts.empty else 0
  conflict_ids = {name: cid for cid, name in settings['conflict_names_by_id'].items()}
  world = build_conflict_map(
    visible_counts,
    top_categories,
    conflicts,
    scale_max=scale_max,
    conflict_ids=conflict_ids,
  )
  map_html = world.get_root().render()
  map_context = f'{snapshot["revision"]}:{conflict}:{start}:{end}:{kind}'
  event = render_map(map_html, map_context)
  action = event.action
  if (
    isinstance(action, dict)
    and action.get('context') == map_context
    and settings['conflict_names_by_id'].get(action.get('conflict_id'))
    in visible_conflicts
  ):
    page_key = apply_map_navigation(
      settings, action.get('conflict_id'), action.get('kind')
    )
    if page_key:
      path = (
        'pages/02_weapons_monthly.py'
        if page_key == 'weapons-monthly'
        else 'pages/03_technology_monthly.py'
      )
      st.switch_page(path)

with details_column.container(height=740):
  st.subheader(f'{conflict_text} 주요 {kind_text}')
  if not visible_conflicts:
    st.info(empty_usage_message)
  # DB 로더의 정렬 순서로 분쟁 카드를 표시한다.
  for item in visible_conflicts:
    st.html(conflict_card(item, counts[item], top_categories[item], conflicts))

st.subheader('주요 범주별 상세 목록')
with st.container(key='conflict_details', border=False):
  for category_kind in kinds:
    # 왼쪽 카드의 분쟁별 Top 3를 합치되, 처음 등장한 순서로 범주를 한 번씩만 표시한다.
    major_categories = list(
      dict.fromkeys(
        name
        for item in visible_conflicts
        for name in top_categories[item][category_kind]
      )
    )
    all_details = classification_details(snapshot['tables'], category_kind)
    details = {name: all_details[name] for name in major_categories}
    st.html(category_details_card(category_kind, details))
