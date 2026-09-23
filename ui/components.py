'''공통 스타일 적용, 필터, 범주 선택 목록과 분쟁 카드를 표시한다.'''

from html import escape
from pathlib import Path

import streamlit as st

from utils.state import remember_category, remember_kind, reset_filters


def apply_styles():
  '''assets/style.css를 읽어 모든 페이지에 같은 디자인을 적용한다.'''
  style_path = Path(__file__).resolve().parents[1] / 'assets' / 'style.css'
  styles = style_path.read_text(encoding='utf-8')
  st.html(f'<style>{styles}</style>')


def render_footer():
  '''보도 건수의 해석 범위를 화면 아래에 표시한다.'''
  st.html(
    '<div class="dashboard-footer">현재 화면은 가상 기사와 판정 결과를 집계한 샘플입니다. '
    '보도 건수는 실제 사용 횟수나 성능을 의미하지 않습니다.</div>'
  )


def format_conflict_name(value):
  '''분쟁 선택값은 그대로 두고 '전체'의 표시 이름만 바꾼다.'''
  if value == '전체':
    return '분쟁 전체'
  return value


def render_filters(settings, is_overview):
  '''공통 필터를 표시하고 완성된 날짜 쌍을 반환한다. 미완성이면 None을 반환한다.'''
  with st.container(key='filters'):
    conflict_col, date_col, kind_col, reset_col = st.columns(
      [2.1, 3.1, 2.1, 1], vertical_alignment='bottom'
    )
    conflict_options = ['전체'] + list(settings['conflicts'])
    conflict_col.selectbox(
      '분쟁', conflict_options, key='conflict', format_func=format_conflict_name
    )
    period = date_col.date_input(
      '기간',
      key='period',
      min_value=settings['start'],
      max_value=settings['end'],
      format='YYYY.MM.DD',
    )
    if is_overview:
      # 유형 위젯이 없는 월간 화면을 거쳐도 이전 선택을 복원한다.
      st.session_state['_overview_kind'] = st.session_state['overview_kind']
      kind_col.selectbox(
        '무기/기술 유형',
        ['전체', '무기', '기술'],
        key='_overview_kind',
        on_change=remember_kind,
      )
    reset_col.button('초기화', on_click=reset_filters, width='stretch')
  # 종료일을 고르는 중에는 페이지 집계를 실행하지 않도록 진입점에 알린다.
  if len(period) != 2:
    st.info('조회할 시작일과 종료일을 모두 선택해주세요.')
    return None
  if period[0] > period[1]:
    st.info('종료일은 시작일 이후로 선택해주세요.')
    return None
  return period


def render_category_picker(kind, settings):
  '''무기 또는 기술 범주를 검색·선택하는 목록을 표시하고 선택한 이름 목록을 반환한다.'''
  selection_key = f'selected_{kind}'
  with st.container(border=True, height=428, key=f'picker_{kind}'):
    st.subheader(f'방산 {kind} 범주 선택')
    st.caption(f'{len(st.session_state[selection_key])}개 선택 · 선택 개수 제한 없음')
    query = st.text_input(
      '범주 이름 검색',
      key=f'_search_{kind}',
      placeholder='이름 검색',
      label_visibility='collapsed',
    )
    query = query.strip().casefold()
    visible = []
    for category in settings['categories'][kind]:
      if query in category.casefold():
        visible.append(category)
    if not visible:
      st.info('검색 결과가 없습니다.')
    for category in visible:
      widget_key = f'_category_{kind}_{category}'
      # 검색으로 숨겨진 위젯은 삭제될 수 있으므로 별도 저장한 선택 목록에서 복원한다.
      st.session_state[widget_key] = category in st.session_state[selection_key]
      st.checkbox(
        category,
        key=widget_key,
        on_change=remember_category,
        args=(kind, category, widget_key),
      )
    st.caption('이름 오름차순 · 기본값: 첫 3개')
  return st.session_state[selection_key]


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
