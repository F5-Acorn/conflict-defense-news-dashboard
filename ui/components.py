'''공통 스타일, 분석 필터, Overview 지표와 기사 패널을 표시한다.'''

from html import escape
from pathlib import Path

import streamlit as st

from services.export_service import article_csv
from utils.state import (
  filter_widget_key,
  get_page_filters,
  period_bounds,
  period_label,
  period_options,
  remember_filter,
  reset_filters,
)

BUBBLE_TEMPLATE = f'''<template class="monthly-bubble-template">
                        <section class="monthly-bubble" role="dialog">
                          <button type="button" class="monthly-close" aria-label="말풍선 닫기">×</button>
                          <h4></h4>
                          <div class="monthly-bubble-month"></div>
                          <strong></strong>
                          <p></p>
                          <button type="button" class="monthly-open-articles">관련 기사 보기</button>
                        </section>
                      </template>'''  # noqa: F541


def article_panel_html(panel):
  '''기사 내용은 텍스트로 이스케이프하며, 링크는 브라우저에서 HTTP(S)만 활성화한다.'''
  cards = []
  for item in panel['items']:
    html_text = f'''<article class="monthly-article">
                      <h4>{escape(item["title"])}</h4>
                      <div class="monthly-article-meta">{escape(item["date"])} · {escape(item["conflict"])}</div>
                      <p>{escape(item["evidence_sentence"])}</p>
                      <a data-article-url="{escape(item["article_url"], quote=True)}" target="_blank" rel="noopener noreferrer">원문 보기 ↗</a>
                    </article>'''
    cards.append(html_text)
  articles = '\n'.join(cards)
  if not articles:
    html_text = f'''<p>해당 조건의 사용 확인 기사가 없습니다.</p>'''  # noqa: F541
    articles = html_text
  conflict = '분쟁 전체' if panel['conflict'] == '전체' else panel['conflict']
  page, pages = panel['page'], panel['pages']
  previous_disabled = ' disabled' if page <= 1 else ''
  next_disabled = ' disabled' if page >= pages else ''
  html_text = f'''<div class="monthly-backdrop"></div>
                  <section class="monthly-drawer" role="dialog" aria-modal="true" aria-label="관련 기사 목록">
                    <header class="monthly-drawer-header">
                      <button type="button" class="monthly-close" aria-label="기사 목록 닫기">×</button>
                      <h3>{escape(panel["category"])} 관련 기사</h3>
                      <div>{escape(conflict)} · {escape(panel["month"].replace("-", "."))} · {panel["total"]:,}건</div>
                    </header>
                    <div class="monthly-articles">{articles}</div>
                    <nav class="monthly-pagination" aria-label="기사 목록 페이지">
                      <button type="button" data-page="{page - 1}"{previous_disabled}>이전</button>
                      <span>{page} / {pages}</span>
                      <button type="button" data-page="{page + 1}"{next_disabled}>다음</button>
                    </nav>
                  </section>'''
  return html_text


def apply_styles():
  '''assets/style.css를 읽어 모든 페이지에 같은 디자인을 적용한다.'''
  style_path = Path(__file__).resolve().parents[1] / 'assets' / 'style.css'
  styles = style_path.read_text(encoding='utf-8')
  html_text = f'''<style>{styles}</style>'''
  st.html(html_text)


def render_analysis_indicators(kind_text, analysis_count, usage_count):
  rows = []
  for label, description, count, kind in (
    (
      '언급 기준 분석 기사 수',
      f'{kind_text}의 언급이 확인된 기사',
      analysis_count,
      'mention',
    ),
    (
      '사용 사례 포함 보도 수',
      f'{kind_text}의 사용 사례가 확인된 기사',
      usage_count,
      'usage',
    ),
  ):
    html_text = f'''<div class="overview-indicator {kind}">
                      <div class="overview-indicator-caption">
                        <div class="overview-indicator-label">
                          {label}
                        </div>
                        <p>{escape(description)}</p>
                      </div>
                      <div class="overview-indicator-number">{count:,}<small>건</small></div>
                    </div>'''
    rows.append(html_text)
  indicators = '\n'.join(rows)
  html_text = f'''<section class="overview-indicators" aria-label="분석 지표">
                    {indicators}
                  </section>'''
  st.html(html_text)


def render_classification_downloads(settings):
  with st.container(border=False):
    st.subheader('방산 무기·기술 분류 기준', anchor=False)
    for kind, standard, filename in (
      ('무기', '무기(SIPRI)', 'weapons'),
      ('기술', '기술(NATO)', 'technology'),
    ):
      count = settings['classification_counts'][kind]
      st.download_button(
        f'{standard} CSV 다운로드 ({count}개)',
        st.session_state['_dashboard']['classification_csv'][kind],
        file_name=f'{filename}_classifications.csv',
        mime='text/csv',
        key=f'classification_csv_{kind}',
        on_click='ignore',
      )


def render_filters(settings, page_key):
  '''분석 페이지의 기간·분쟁·유형과 초기화 필터를 표시한다.'''
  filters = get_page_filters(page_key)
  with st.container(
    horizontal=True,
    horizontal_alignment='distribute',
    vertical_alignment='center',
    key='filter_bar',
  ):
    with st.container(key='filters', width=900):
      columns = st.columns(
        [1.2, 1, 0.8, 1],
        width=900,
        gap='small',
        vertical_alignment='center',
      )
      columns[0].selectbox(
        '국가간 분쟁',
        ['전체', *settings['conflicts']],
        key=filter_widget_key(page_key, 'conflict'),
        on_change=remember_filter,
        args=(page_key, 'conflict'),
      )
      selected = columns[1].selectbox(
        '기간',
        period_options(settings, page_key),
        key=filter_widget_key(page_key, 'selected_period'),
        format_func=lambda value: period_label(page_key, value),
        on_change=remember_filter,
        args=(page_key, 'selected_period'),
      )
      columns[2].selectbox(
        '무기/기술',
        ['전체', '무기', '기술'],
        key=filter_widget_key(page_key, 'kind'),
        on_change=remember_filter,
        args=(page_key, 'kind'),
      )
      columns[3].button(
        '초기화',
        key=filter_widget_key(page_key, 'reset'),
        on_click=reset_filters,
        args=(page_key,),
        width=100,
      )
    filters['period'] = period_bounds(page_key, selected)
    snapshot = st.session_state['_dashboard']
    conflict, kind = filters['conflict'], filters['kind']
    start, end = filters['period']
    with st.container(width='content', key='article_download'):
      st.download_button(
        '기사 CSV 다운로드',
        data=lambda: article_csv(snapshot, conflict, start, end, kind),
        file_name=f'articles_{page_key}_{start.isoformat()}_{end.isoformat()}.csv',
        mime='text/csv',
        key=f'article_csv_{page_key}',
        on_click='ignore',
      )
  return filters['period']
