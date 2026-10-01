'''연간·월간·주간 무기·기술 통합 분석 화면.'''

import hashlib
import json
from html import escape

import streamlit as st

from config import TREND_PALETTE
from data.constants import STATUS_LABELS
from services.analysis_service import (
  category_summary,
  summary_judgements,
  summary_trend,
  summary_word_counts,
)
from services.detail_service import article_details, valid_article_request
from ui.charts import (
  DONUT_WIDTH,
  PERIOD_STATUS_COLORS,
  judgement_donut,
  period_trend_chart,
)
from ui.interactive import render_interactive_trend, render_judgement_donut
from ui.wordcloud_view import render_wordcloud_panel
from utils.state import (
  MAX_CATEGORIES,
  ensure_dashboard,
  filter_widget_key,
  get_page_filters,
  remember_filter,
  remember_period_category,
)


def _categories(settings, kind):
  kinds = ('무기', '기술') if kind == '전체' else (kind,)
  return {
    category_id: (item, name)
    for item in kinds
    for name, category_id in settings['category_ids'][item].items()
  }


def _category_picker(page_key, filters, categories, counts, kind_text):
  ordered = sorted(
    categories,
    key=lambda cid: (-counts.get(cid, 0), categories[cid][0], categories[cid][1]),
  )
  if not filters['categories_initialized']:
    filters['selected_category_ids'] = ordered[:3]
    filters['categories_initialized'] = True
  with st.container(height='stretch', border=True, key=f'period_picker_{page_key}'):
    with st.container(
      horizontal=True,
      horizontal_alignment='left',
      vertical_alignment='bottom',
      width='content',
      gap='small',
    ):
      st.subheader(f'방산 {kind_text} 범주', width='content', anchor=False)
      st.caption(f'({len(filters["selected_category_ids"])}/{MAX_CATEGORIES} 선택됨)')
    query = (
      st.text_input(
        '범주명 검색',
        key=filter_widget_key(page_key, 'category_search'),
        placeholder='범주명 검색',
        label_visibility='collapsed',
        on_change=remember_filter,
        args=(page_key, 'category_search'),
      )
      .strip()
      .casefold()
    )
    visible = [
      cid
      for cid in ordered
      if query in f'{categories[cid][0]} · {categories[cid][1]}'.casefold()
    ]
    with st.container(height=300, border=False, key=f'period_category_list_{page_key}'):
      if not visible:
        st.info('검색 결과가 없습니다.')
      for category_id in visible:
        kind, name = categories[category_id]
        widget_key = filter_widget_key(page_key, f'category_{category_id}')
        st.session_state[widget_key] = category_id in filters['selected_category_ids']
        st.checkbox(
          f'{name} ({counts.get(category_id, 0):,}건)',
          key=widget_key,
          disabled=len(filters['selected_category_ids']) >= MAX_CATEGORIES
          and category_id not in filters['selected_category_ids'],
          on_change=remember_period_category,
          args=(page_key, category_id, widget_key),
        )
  return filters['selected_category_ids']


def _donut_item(page_key, summary, category_id, categories):
  _, name = categories[category_id]
  counts = summary_judgements(summary, category_id)
  with st.container(
    width=DONUT_WIDTH, key=f'period_donut_item_{page_key}_{category_id}'
  ):
    html_text = f'''<div class="period-donut-label" title="{escape(name, quote=True)}">{escape(name)}</div>'''
    st.html(html_text)
    figure = judgement_donut(counts)
    render_judgement_donut(figure, key=f'period_donut_chart_{page_key}_{category_id}')


def _donut_panel(page_key, summary, selected, categories, kind_text):
  with st.container(height='stretch', border=True, key=f'period_donut_{page_key}'):
    legend_items = []
    for code, label in STATUS_LABELS.items():
      html_text = f'''<span>
                        <i style="background:{PERIOD_STATUS_COLORS[code]}"></i>
                        {escape(label)}
                      </span>'''
      legend_items.append(html_text)
    legend = '\n'.join(legend_items)
    with st.container(
      horizontal=True,
      wrap=False,
      horizontal_alignment='distribute',
      vertical_alignment='center',
      gap='small',
      key=f'period_donut_header_{page_key}',
    ):
      st.subheader(f'방산 {kind_text} 사용 판단 분포', anchor=False)
      with st.container(width='content'):
        html_text = f'''<div class="period-donut-legend" aria-label="판정 상태 범례">
                          {legend}
                        </div>'''
        st.html(html_text)
    with st.container(vertical_alignment='center', key=f'period_donut_body_{page_key}'):
      if not selected:
        st.info('판정 상태를 확인할 범주를 하나 이상 선택해주세요.')
        return
      rows = (
        [selected]
        if len(selected) <= 3
        else (
          [selected[:2], selected[2:]]
          if len(selected) == 4
          else [selected[:3], selected[3:]]
        )
      )
      for index, row in enumerate(rows):
        with st.container(
          horizontal=True,
          wrap=False,
          horizontal_alignment='center',
          vertical_alignment='bottom',
          key=f'period_donut_row_{page_key}_{index}',
        ):
          for category_id in row:
            _donut_item(page_key, summary, category_id, categories)


def _interactive_trend(page_key, filters, snapshot, selected, categories):
  start, end = filters['period']
  granularity = 'month' if page_key == 'annual' else 'day'
  settings = snapshot['settings']
  conflict_id = next(
    (
      cid
      for cid, name in settings['conflict_names_by_id'].items()
      if name == filters['conflict']
    ),
    None,
  )
  context = hashlib.sha256(
    json.dumps(
      [
        snapshot['revision'],
        page_key,
        filters['conflict'],
        filters['kind'],
        start.isoformat(),
        end.isoformat(),
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
    category_id = request['category_id']
    drawer = article_details(
      snapshot['reports'],
      category_id,
      request['month'],
      request['page'],
      granularity=granularity,
      conflict=filters['conflict'],
    )
    _, name = categories[category_id]
    drawer.update(
      category=name,
      category_id=category_id,
      month=request['month'],
      conflict=filters['conflict'],
    )
  trend = summary_trend(
    snapshot, filters['conflict'], start, end, filters['kind'], selected, granularity
  )
  labels = {cid: categories[cid][1] for cid in selected}
  colors = {
    cid: TREND_PALETTE[index % len(TREND_PALETTE)] for index, cid in enumerate(selected)
  }
  comparison = '전월' if granularity == 'month' else '전일'
  st.caption(f'점을 선택하면 {comparison} 대비 증감과 관련 기사를 확인할 수 있습니다.')
  if not trend['count'].any():
    st.info('선택한 범주의 사용 보도가 없어 0건으로 표시합니다.')
  render_interactive_trend(
    period_trend_chart(trend, labels, colors, granularity),
    context,
    filters['kind'],
    drawer,
    page_key,
    conflict_id,
    granularity=granularity,
    on_action=lambda: handle_article_action(
      f'interactive_{page_key}',
      state_key,
      context,
      filters['kind'],
      conflict_id,
      selected,
      start,
      end,
      granularity,
    ),
  )


def handle_article_action(
  widget_key,
  state_key,
  context,
  kind,
  conflict_id,
  allowed_ids,
  start,
  end,
  granularity='month',
):
  """컴포넌트 콜백에서 먼저 상태를 갱신해 추가 rerun 없이 최신 목록을 그린다."""
  action = st.session_state.get(widget_key, {}).get('action')
  ui_state = st.session_state.get(state_key)
  if not ui_state or ui_state['context'] != context:
    return
  if (
    not isinstance(action, dict)
    or action.get('context') != context
    or action.get('kind') != kind
    or action.get('conflict_id') != conflict_id
    or action.get('granularity', 'month') != granularity
  ):
    return
  if action.get('type') == 'close_articles':
    ui_state['request'] = None
  elif valid_article_request(
    action, context, allowed_ids, start, end, kind, granularity
  ):
    page = action.get('page', 1)
    if isinstance(page, int) and not isinstance(page, bool) and page > 0:
      ui_state['request'] = {
        'category_id': action['category_id'],
        'month': action['month'],
        'page': page,
      }


def render_period_view(page_key):
  ensure_dashboard(page_key)
  filters = get_page_filters(page_key)
  snapshot = st.session_state['_dashboard']
  settings = snapshot['settings']
  start, end = filters['period']
  summary = category_summary(snapshot, filters['conflict'], start, end, filters['kind'])
  categories = _categories(settings, filters['kind'])
  counts = dict(zip(summary['category_id'], summary['used_count'].astype(int)))
  word_counts = summary_word_counts(summary)
  kind = filters['kind']
  kind_text = '무기·기술' if kind == '전체' else kind

  with st.container(height=420, border=False, key=f'period_analysis_{page_key}'):
    word_cloud_column, selected_column, donut_column = st.columns([2.8, 2, 5.2])
    # 워드 클라우드
    with (
      word_cloud_column,
      st.container(height='stretch', border=True, key=f'period_words_{page_key}'),
    ):
      st.subheader(f'방산 {kind_text} 현황', anchor=False)
      st.caption(
        f'선택한 국가간 분쟁과 기간을 기준으로 방산 {kind_text}별 사용 여부가 보도된 빈도 확인'
      )
      render_wordcloud_panel(
        word_counts,
        images=snapshot['wordcloud_images'],
        key=f'period_wordcloud_{page_key}',
      )

    # 범주 선택
    with selected_column:
      selected = _category_picker(page_key, filters, categories, counts, kind_text)

    # 도넛 플롯
    with donut_column:
      _donut_panel(page_key, summary, selected, categories, kind_text)

  with st.container(border=True, key=f'period_trend_{page_key}'):
    st.subheader(f'방산 {kind_text} 사용 보도 추이', anchor=False)
    if not selected:
      st.info('추이를 확인할 범주를 하나 이상 선택해주세요.')
    else:
      _interactive_trend(page_key, filters, snapshot, selected, categories)
