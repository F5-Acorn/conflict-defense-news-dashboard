'''공통 스타일 적용, 필터, 범주 선택 목록과 분쟁 카드를 표시한다.'''

from html import escape
from pathlib import Path

import streamlit as st

from services.analysis_service import ordered_category_names
from services.detail_service import classification_csv
from ui.flags import render_flags
from utils.state import (
  MAX_CATEGORIES,
  filter_widget_key,
  get_page_filters,
  initialize_category_selection,
  month_options,
  month_period,
  remember_category,
  remember_filter,
  reset_filters,
)

BUBBLE_TEMPLATE = '''<template class="monthly-bubble-template">
<section class="monthly-bubble" role="dialog">
  <button type="button" class="monthly-close" aria-label="말풍선 닫기">×</button>
  <h4></h4><div class="monthly-bubble-month"></div><strong></strong><p></p>
  <button type="button" class="monthly-open-articles">관련 기사 보기</button>
</section></template>'''


def article_panel_html(panel):
  '''기사 내용은 텍스트로 이스케이프하며, 링크는 브라우저에서 HTTP(S)만 활성화한다.'''
  cards = []
  for item in panel['items']:
    cards.append(
      '<article class="monthly-article">'
      f'<h4>{escape(item["title"])}</h4>'
      f'<div class="monthly-article-meta">{escape(item["date"])} · {escape(item["conflict"])}</div>'
      f'<p>{escape(item["evidence_sentence"])}</p>'
      f'<a data-article-url="{escape(item["article_url"], quote=True)}" '
      'target="_blank" rel="noopener noreferrer">원문 보기 ↗</a></article>'
    )
  articles = ''.join(cards) or '<p>해당 조건의 사용 확인 기사가 없습니다.</p>'
  conflict = '분쟁 전체' if panel['conflict'] == '전체' else panel['conflict']
  page, pages = panel['page'], panel['pages']
  previous_disabled = ' disabled' if page <= 1 else ''
  next_disabled = ' disabled' if page >= pages else ''
  return (
    '<div class="monthly-backdrop"></div>'
    '<section class="monthly-drawer" role="dialog" aria-modal="true" aria-label="관련 기사 목록">'
    '<header class="monthly-drawer-header">'
    '<button type="button" class="monthly-close" aria-label="기사 목록 닫기">×</button>'
    f'<h3>{escape(panel["category"])} 관련 기사</h3>'
    f'<div>{escape(conflict)} · {escape(panel["month"].replace("-", "."))} · {panel["total"]:,}건</div>'
    f'</header><div class="monthly-articles">{articles}</div>'
    '<nav class="monthly-pagination" aria-label="기사 목록 페이지">'
    f'<button type="button" data-page="{page - 1}"{previous_disabled}>이전</button>'
    f'<span>{page} / {pages}</span>'
    f'<button type="button" data-page="{page + 1}"{next_disabled}>다음</button>'
    '</nav></section>'
  )


def apply_styles():
  '''assets/style.css를 읽어 모든 페이지에 같은 디자인을 적용한다.'''
  style_path = Path(__file__).resolve().parents[1] / 'assets' / 'style.css'
  styles = style_path.read_text(encoding='utf-8')
  st.html(f'<style>{styles}</style>')


def render_filters(settings, page_key):
  '''페이지별 월 필터를 표시하고 유효한 집계 기간을 반환한다.'''
  is_overview = page_key == 'overview'
  filters = get_page_filters(page_key)
  with st.container(key='filters'):
    # overview는 오른쪽 끝에 다운로드 영역을 두고, 월간 화면은 필터만 표시한다.
    columns = st.columns(
      [2.1, 2.1, 2.1, 2.1, 1.1, 3.4] if is_overview else 4,
      width='stretch' if is_overview else 1000,
      gap='small',
      vertical_alignment='center',
    )
    conflict_col, start_col, end_col = columns[:3]
    reset_col = columns[4] if is_overview else columns[-1]
    conflict_options = ['전체'] + list(settings['conflicts'])
    conflict_col.selectbox(
      '분쟁',
      conflict_options,
      key=filter_widget_key(page_key, 'conflict'),
      on_change=remember_filter,
      args=(page_key, 'conflict'),
    )
    options = month_options(settings)
    start_month = start_col.selectbox(
      '시작월',
      options,
      key=filter_widget_key(page_key, 'start_month'),
      format_func=lambda value: value.replace('-', '.'),
      on_change=remember_filter,
      args=(page_key, 'start_month'),
    )
    end_month = end_col.selectbox(
      '종료월',
      options,
      key=filter_widget_key(page_key, 'end_month'),
      format_func=lambda value: value.replace('-', '.'),
      on_change=remember_filter,
      args=(page_key, 'end_month'),
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
    if is_overview:
      kind = filters['overview_kind']
      kinds = ['무기', '기술'] if kind == '전체' else [kind]
      with (
        columns[5],
        st.container(
          horizontal=True,
          horizontal_alignment='right',
          vertical_alignment='center',
          key='classification_downloads',
        ),
      ):
        for item in kinds:
          st.download_button(
            f'{item} CSV 다운로드',
            classification_csv(st.session_state['_dashboard']['tables'], item),
            file_name=f'{"weapons" if item == "무기" else "technology"}_classifications.csv',
            mime='text/csv',
            key=f'classification_csv_{item}',
            on_click='ignore',
          )
  if start_month > end_month:
    st.info('종료월은 시작월과 같거나 이후로 선택해주세요.')
    return None
  filters['period'] = month_period(start_month, end_month)
  return filters['period']


def render_category_picker(kind, settings, *, category_counts=None):
  '''무기 또는 기술 범주를 검색·선택하는 목록을 표시하고 선택한 이름 목록을 반환한다.'''
  page_key = st.session_state['_filter_page']
  filters = get_page_filters(page_key)
  ordered = ordered_category_names(settings['categories'][kind], category_counts)
  initialize_category_selection(page_key, ordered)
  with st.container(border=True, height=428, key=f'picker_{kind}'):
    with st.container(
      horizontal=True,
      horizontal_alignment='left',
      vertical_alignment='bottom',
    ):
      st.subheader(f'방산 {kind} 범주 선택', width='content')
      st.caption(
        f'({len(filters["selected_categories"])} / {MAX_CATEGORIES}개 선택됨)',
        width='content',
      )
    query = st.text_input(
      '범주 이름 검색',
      key=filter_widget_key(page_key, 'category_search'),
      placeholder='이름 검색',
      label_visibility='collapsed',
      on_change=remember_filter,
      args=(page_key, 'category_search'),
    )
    query = query.strip().casefold()
    visible = [category for category in ordered if query in category.casefold()]
    if not visible:
      st.info('검색 결과가 없습니다.')
    for category in visible:
      widget_key = filter_widget_key(page_key, f'category_{category}')
      # 검색으로 숨겨진 위젯은 삭제될 수 있으므로 별도 저장한 선택 목록에서 복원한다.
      st.session_state[widget_key] = category in filters['selected_categories']
      st.checkbox(
        category,
        key=widget_key,
        disabled=len(filters['selected_categories']) >= MAX_CATEGORIES
        and category not in filters['selected_categories'],
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
    f'<div class="conflict-card"><div class="card-heading">{render_flags(config["flag"])} '
    f'<span>{escape(conflict)}</span></div>'
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
