'''선택 조건을 집계해 보도 동향 지표와 지도, 분쟁별 주요 범주를 표시한다.'''

import streamlit as st

from services.analysis_service import article_totals, filter_data, ranked_categories
from ui.components import conflict_card
from ui.maps import build_conflict_map

# app.py에서 시작일과 종료일이 모두 선택된 것을 확인한 뒤 이 페이지를 실행한다.
start, end = st.session_state['period']
conflict = st.session_state['conflict']
kind = st.session_state['overview_kind']

snapshot = st.session_state['_dashboard']
settings = snapshot['settings']
conflicts = settings['conflicts']
classification_counts = settings['classification_counts']
articles, categories = snapshot['article_daily'], snapshot['category_daily']
filtered_articles = filter_data(articles, conflict, start, end, kind)
analysis_count, usage_count = article_totals(filtered_articles)
kinds = ['무기', '기술'] if kind == '전체' else [kind]

# 분류 수는 엑셀에 등록된 범주 수이므로 기간·분쟁에 따라 줄이지 않는다.
classification_count = 0
classification_labels = []
for item in kinds:
  classification_count += classification_counts[item]
  classification_labels.append(f'{item} 범주 {classification_counts[item]}개')

# 지도 수치는 기사 지표에서, 주요 범주는 범주별 보도 수에서 각각 집계한다.
# 전체 선택 시 엑셀의 분쟁 행 순서대로 지도와 오른쪽 카드를 표시한다.
visible_conflicts = list(conflicts) if conflict == '전체' else [conflict]
counts = {}
top_categories = {}
for item in visible_conflicts:
  conflict_articles = filtered_articles.loc[filtered_articles['conflict'] == item]
  counts[item] = int(conflict_articles['usage_articles'].sum())
  top_categories[item] = {}
  for category_kind in kinds:
    filtered_categories = filter_data(categories, item, start, end, category_kind)
    ranking = ranked_categories(filtered_categories)
    top_categories[item][category_kind] = ranking['category'].tolist()

# 상단에는 기존 순서와 디자인으로 기사 지표 카드 3개를 표시한다.
analysis_column, usage_column, classification_column = st.columns(3)
with analysis_column:
  st.metric(
    '전체 분석 기사 수',
    f'{analysis_count:,}건',
    border=True,
    help='선택한 유형의 범주가 언급된 기사를 중복 제거한 수입니다. 사용 외 언급과 확인 필요도 포함합니다.',
  )
with usage_column, st.container(key='usage_metric'):
  st.metric(
    f'{'무기/기술' if kind == '전체' else kind} 사용 사례 보도 수',
    f'{usage_count:,}건',
    border=True,
    help='선택한 유형에서 사용이 확인된 기사를 중복 제거한 수입니다. 사용 외 언급과 확인 필요는 제외합니다.',
  )
with classification_column:
  st.metric(
    f'방산 {'무기/기술' if kind == '전체' else kind} 분류 수',
    f'{classification_count:,}개',
    border=True,
    help='엑셀에 등록된 범주 수입니다. 사전의 명칭·유의어 수와 다르며, 분쟁·기간 필터에 따라 바뀌지 않습니다.',
    delta_description=' · '.join(classification_labels),
  )

# 지도와 주요 범주를 2:1로 나눈다. 좁은 화면에서는 기본 반응형 배치로 위아래에 놓인다.
# 열 자체에 테두리를 적용해 두 섹션의 위·아래 경계를 같은 높이로 맞춘다.
map_column, details_column = st.columns([2, 1], gap='medium', border=True)
with map_column, st.container(key='conflict_map', height=740):
  st.subheader('분쟁별 방산 무기/기술 사용 보도 현황 지도')
  world = build_conflict_map(counts, top_categories, conflicts)
  map_html = world.get_root().render()
  st.iframe(map_html, height=650)

with details_column, st.container(key='conflict_details', height=740):
  details_kind = '무기/기술' if kind == '전체' else kind
  st.subheader(f'분쟁별 주요 {details_kind}')
  # 엑셀에 등록된 순서로 분쟁 카드를 표시한다.
  for item in visible_conflicts:
    st.html(conflict_card(item, counts[item], top_categories[item], conflicts))
