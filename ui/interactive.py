'''Components v2로 지도 이벤트와 클릭 가능한 차트·기사 패널을 연결한다.'''

import json
from pathlib import Path

import streamlit.components.v2 as components
from plotly.offline import get_plotlyjs

from ui.components import BUBBLE_TEMPLATE, article_panel_html

FRONTEND = Path(__file__).with_name('frontend')

map_component = components.component(
  'conflict_map',
  html='<iframe class="dashboard-map" title="분쟁별 사용 보도 지도"></iframe>',
  css='.dashboard-map { border:0; width:100%; height:650px; display:block; }',
  js=(FRONTEND / 'map.js').read_text(encoding='utf-8'),
)
trend_component = components.component(
  'monthly_trend',
  html='<div class="monthly-interactive"><div class="monthly-plot" tabindex="0" aria-label="월별 사용 확인 기사 추이"></div></div>'
  + BUBBLE_TEMPLATE,
  css=(FRONTEND / 'monthly.css').read_text(encoding='utf-8'),
  js=get_plotlyjs() + '\n' + (FRONTEND / 'monthly.js').read_text(encoding='utf-8'),
  isolate_styles=False,
)


def render_map(html, context):
  return map_component(
    data={'html': html, 'context': context},
    key='overview_map',
    on_action_change=lambda: None,
  )


def render_interactive_trend(
  figure, context, kind, drawer, page_key, conflict_id=None, on_action=None
):
  if drawer is not None:
    # 기사 ID와 원본 행은 서버에 남기고 표시할 HTML과 페이지 이동 정보만 전달한다.
    drawer = {
      'html': article_panel_html(drawer),
      'category_id': drawer['category_id'],
      'month': drawer['month'],
    }
  return trend_component(
    data={
      'figure': json.loads(figure.to_json()),
      'context': context,
      'kind': kind,
      'drawer': drawer,
      'conflict_id': conflict_id,
    },
    key=f'interactive_{page_key}',
    on_action_change=on_action,
  )
