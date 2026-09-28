'''공통 스타일 적용, 필터, 범주 선택 목록과 분쟁 카드를 표시한다.'''

from html import escape
from pathlib import Path

import streamlit as st

from utils.state import (
  filter_widget_key,
  get_page_filters,
  remember_category,
  remember_filter,
  reset_filters,
)


def apply_styles():
  '''assets/style.css를 읽어 모든 페이지에 같은 디자인을 적용한다.'''
  style_path = Path(__file__).resolve().parents[1] / 'assets' / 'style.css'
  styles = style_path.read_text(encoding='utf-8')
  st.html(f'<style>{styles}</style>')


def render_filters(settings, page_key):
  '''공통 필터를 표시하고 완성된 날짜 쌍을 반환한다. 미완성이면 None을 반환한다.'''
  is_overview = page_key == 'overview'
  filters = get_page_filters(page_key)
  with st.container(key='filters'):
    # 월간 화면은 유형 열을 제외하고 전체 폭도 줄여 초기화를 종료일 옆에 둔다.
    columns = st.columns(
      5 if is_overview else 4,
      width=1250 if is_overview else 1000,
      gap='small',
      vertical_alignment='center',
    )
    conflict_col, start_col, end_col = columns[:3]
    reset_col = columns[-1]
    conflict_options = ['전체'] + list(settings['conflicts'])
    conflict_col.selectbox(
      '분쟁',
      conflict_options,
      key=filter_widget_key(page_key, 'conflict'),
      on_change=remember_filter,
      args=(page_key, 'conflict'),
    )
    # 범위 달력은 월·연도 이동 후 종료일 선택이 새 시작일 선택으로 바뀔 수 있다.
    # 두 날짜를 독립적으로 입력받고, 유효한 쌍만 집계용 기간에 반영한다.
    start = start_col.date_input(
      '시작일',
      key=filter_widget_key(page_key, 'start'),
      min_value=settings['start'],
      max_value=settings['end'],
      format='YYYY.MM.DD',
      on_change=remember_filter,
      args=(page_key, 'start'),
    )
    end = end_col.date_input(
      '종료일',
      key=filter_widget_key(page_key, 'end'),
      min_value=settings['start'],
      max_value=settings['end'],
      format='YYYY.MM.DD',
      on_change=remember_filter,
      args=(page_key, 'end'),
    )
    if is_overview:
      kind_col = columns[3]
      kind_col.selectbox(
        '무기/기술 유형',
        ['전체', '무기', '기술'],
        key=filter_widget_key(page_key, 'overview_kind'),
        on_change=remember_filter,
        args=(page_key, 'overview_kind'),
      )
    reset_col.button(
      '초기화',
      key=filter_widget_key(page_key, 'reset'),
      on_click=reset_filters,
      args=(page_key,),
      width=100,
    )
  # 종료일을 고르는 중에는 페이지 집계를 실행하지 않도록 진입점에 알린다.
  if start is None or end is None:
    st.info('조회할 시작일과 종료일을 모두 선택해주세요.')
    return None
  if start > end:
    st.info('종료일은 시작일 이후로 선택해주세요.')
    return None
  filters['period'] = (start, end)
  return start, end


def render_category_picker(kind, settings):
  '''무기 또는 기술 범주를 검색·선택하는 목록을 표시하고 선택한 이름 목록을 반환한다.'''
  page_key = st.session_state['_filter_page']
  filters = get_page_filters(page_key)
  with st.container(border=True, height=428, key=f'picker_{kind}'):
    with st.container(
      horizontal=True,
      horizontal_alignment='left',
      vertical_alignment='bottom',
    ):
      st.subheader(f'방산 {kind} 범주 선택', width='content')
      st.caption(f'({len(filters["selected_categories"])}개 선택됨)', width='content')
    query = st.text_input(
      '범주 이름 검색',
      key=filter_widget_key(page_key, 'category_search'),
      placeholder='이름 검색',
      label_visibility='collapsed',
      on_change=remember_filter,
      args=(page_key, 'category_search'),
    )
    query = query.strip().casefold()
    visible = []
    for category in settings['categories'][kind]:
      if query in category.casefold():
        visible.append(category)
    if not visible:
      st.info('검색 결과가 없습니다.')
    for category in visible:
      widget_key = filter_widget_key(page_key, f'category_{category}')
      # 검색으로 숨겨진 위젯은 삭제될 수 있으므로 별도 저장한 선택 목록에서 복원한다.
      st.session_state[widget_key] = category in filters['selected_categories']
      st.checkbox(
        category,
        key=widget_key,
        on_change=remember_category,
        args=(page_key, category, widget_key),
      )
  return filters['selected_categories']


def conflict_card(conflict, count, top_categories, conflicts):
  '''분쟁 이름·보도 수(건)·유형별 Top 3 이름을 받아 카드 HTML을 반환한다.'''
  config = conflicts[conflict]
  rows = []
  for kind, categories in top_categories.items():
    tag_class = 'category-tag technology-tag' if kind == '기술' else 'category-tag'
    tags = []
    for category in categories:
      # 실제 데이터로 교체해도 범주명이 HTML로 해석되지 않도록 처리한다.
      tags.append(f'<span class="{tag_class}">{escape(category)}</span>')
    tags = "".join(tags)
    rows.append(
      f'<div class="tag-row"><span class="tag-label">주요 {kind}</span>{tags or "보도 없음"}</div>'
    )
  return (
    f'<div class="conflict-card"><div class="card-heading">{escape(config["flag"])} {escape(conflict)}</div>'
    f'<div class="report-count" style="color:{config["color"]}">{count:,}건</div>{"".join(rows)}</div>'
  )


def category_details_card(kind, details):
  '''범주는 세로로, 해당 사전의 명칭은 쉼표로 연결해 표시하는 유형별 카드 HTML.'''
  card_class = 'category-details-card'
  if kind == '기술':
    card_class += ' technology-details-card'
  name_count = sum(len(names) for names in details.values())
  rows = []
  for category, names in details.items():
    name_text = ', '.join(names) if names else '등록된 명칭이 없습니다.'
    rows.append(
      f'<tr><th scope="row">{escape(category)}</th>'
      f'<td><div class="dictionary-names">{escape(name_text)}</div></td></tr>'
    )
  if rows:
    body = (
      '<table class="category-details-table">'
      '<colgroup><col class="category-name-column"><col></colgroup>'
      '<thead><tr><th scope="col">분류</th><th scope="col">세부 명칭</th></tr></thead>'
      f'<tbody>{"".join(rows)}</tbody></table>'
    )
  else:
    body = '<p class="category-details-empty">선택한 조건의 주요 범주가 없습니다.</p>'
  return (
    f'<section class="{card_class}" aria-label="{escape(kind)} 상세 목록">'
    '<div class="category-details-heading">'
    f'<h4>{escape(kind)}</h4>'
    f'<span class="category-details-count">{len(details)}개 범주 · {name_count}개 명칭</span>'
    f'</div>{body}</section>'
  )
