'''Components v2로 지도 이벤트와 클릭 가능한 차트·기사 패널을 연결한다.'''

import json
from pathlib import Path

import streamlit.components.v2 as components
from plotly.offline import get_plotlyjs

from data.constants import UsageCode
from ui.charts import DONUT_HEIGHT, DONUT_WIDTH
from ui.components import BUBBLE_TEMPLATE
from ui.loading import LOADING_CSS, loading_html

FRONTEND = Path(__file__).with_name('frontend')

html_text = f'''<div class="dashboard-map-shell">
  {loading_html("지도를 준비하는 중…")}
  <iframe class="dashboard-map" title="분쟁별 사용 보도 지도" style="visibility:hidden"></iframe>
</div>'''
map_component = components.component(
  'conflict_map',
  html=html_text,
  css=LOADING_CSS
  + '.dashboard-map-shell {position:relative;height:250px;} .dashboard-map {border:0;width:100%;height:250px;display:block;}',
  js=(FRONTEND / 'map.js').read_text(encoding='utf-8'),
)
html_text = f'''<section class="classification-details" aria-label="세부 명칭">
                </section>'''  # noqa: F541
classification_component = components.component(
  'classification_details',
  html=html_text,
  css=(FRONTEND / 'classification.css').read_text(encoding='utf-8'),
  js=(FRONTEND / 'classification.js').read_text(encoding='utf-8'),
  isolate_styles=False,
)
html_text = f'''<div class="monthly-interactive">
                  {loading_html("추이를 준비하는 중…")}
                  <div class="monthly-plot" style="visibility:hidden" tabindex="0" aria-label="월별 사용 확인 기사 추이"></div>
                </div>
                {BUBBLE_TEMPLATE}'''
trend_component = components.component(
  'monthly_trend',
  html=html_text,
  css=(FRONTEND / 'monthly.css').read_text(encoding='utf-8'),
  js=get_plotlyjs() + '\n' + (FRONTEND / 'monthly.js').read_text(encoding='utf-8'),
  isolate_styles=False,
)
html_text = f'''<div class="judgement-donut-shell">
                  {loading_html("차트를 준비하는 중…")}
                  <div class="judgement-donut" style="visibility:hidden" aria-label="범주별 사용 판단 분포"></div>
                </div>'''
donut_component = components.component(
  'judgement_donut',
  html=html_text,
  css=f'.judgement-donut-shell {{ position:relative; width:{DONUT_WIDTH}px; height:{DONUT_HEIGHT}px; margin-inline:auto; }} .judgement-donut {{width:100%;height:100%;}}',
  js=get_plotlyjs() + '\n' + (FRONTEND / 'donut.js').read_text(encoding='utf-8'),
  isolate_styles=False,
)


def render_judgement_donut(figure, key, *, context, category_id, on_action):
  return donut_component(
    data={
      'figure': json.loads(figure.to_json()),
      'context': context,
      'category_id': category_id,
      'used_code': int(UsageCode.USED),
    },
    key=key,
    on_action_change=on_action,
  )


def render_classification_details(category, names, context):
  return classification_component(
    data={'category': category, 'names': names, 'context': context},
    key='overview_classification_details',
  )


def render_map(html, context, view, *, cards, colors):
  return map_component(
    data={'html': html, 'context': context, 'cards': cards, 'colors': colors, **view},
    key='overview_map',
    on_action_change=lambda: None,
  )


def render_interactive_trend(
  figure,
  context,
  kind,
  page_key,
  conflict_id=None,
  on_action=None,
  granularity='month',
):
  return trend_component(
    data={
      'figure': json.loads(figure.to_json()),
      'context': context,
      'kind': kind,
      'granularity': granularity,
      'conflict_id': conflict_id,
    },
    key=f'interactive_{page_key}',
    on_action_change=on_action,
  )
