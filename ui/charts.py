'''집계된 데이터를 기간별 Plotly 선그래프와 판정 도넛으로 만든다.'''

from math import ceil

import pandas as pd
import plotly.graph_objects as go

from config import CHART_BACKGROUND, GRID_COLOR, TEXT_COLOR
from data.constants import STATUS_LABELS, UsageCode
from services.detail_service import with_period_changes


def _base_layout(figure, height):
  '''전달받은 차트에 공통 배경·글꼴·여백·범례와 높이(px)를 적용한다.'''
  # 범례를 차트 위쪽 오른편에 가로로 배치한다.
  figure.update_layout(
    template='plotly_dark',
    height=height,
    paper_bgcolor=CHART_BACKGROUND,
    plot_bgcolor=CHART_BACKGROUND,
    font={'family': 'Arial, Apple SD Gothic Neo, sans-serif', 'color': TEXT_COLOR},
    margin={'l': 20, 'r': 40, 't': 45, 'b': 20},
    legend={
      'orientation': 'h',
      'yanchor': 'bottom',
      'y': 1.05,
      'xanchor': 'right',
      'x': 1,
      'traceorder': 'normal',
    },
    hoverlabel={'font_size': 14},
  )


PERIOD_STATUS_COLORS = {
  UsageCode.USED: '#1E6BD6',
  UsageCode.UNCERTAIN: '#8995A5',
  UsageCode.NOT_USED: '#D8495B',
}
DONUT_DIAMETER = 130
DONUT_WIDTH = 224
DONUT_HEIGHT = 140


def judgement_donut(counts):
  '''기사·범주 판정 건수의 사용·불확실·비사용 비율을 표시한다.'''
  codes = [code for code in STATUS_LABELS if counts.get(code, 0) > 0]
  total = int(counts.sum())
  not_used = int(counts.get(UsageCode.NOT_USED, 0))
  rotation = (270 - 360 * (1 - not_used / (2 * total))) % 360 if not_used else 0
  html_text = f'''%{{percent:.1%}}'''  # noqa: F541
  hover_html_text = f'''%{{label}}: %{{value:,}}건 (%{{percent:.1%}})<extra></extra>'''  # noqa: F541
  figure = go.Figure(
    go.Pie(
      labels=[STATUS_LABELS[code] for code in codes],
      values=[int(counts.get(code, 0)) for code in codes],
      marker={'colors': [PERIOD_STATUS_COLORS[code] for code in codes]},
      hole=0.64,
      sort=False,
      direction='clockwise',
      rotation=rotation,
      domain={
        'x': [
          (DONUT_WIDTH - DONUT_DIAMETER) / (2 * DONUT_WIDTH),
          (DONUT_WIDTH + DONUT_DIAMETER) / (2 * DONUT_WIDTH),
        ]
      },
      customdata=[int(code) for code in codes],
      textposition='inside',
      texttemplate=html_text,
      insidetextfont={'size': 12, 'color': '#ffffff'},
      insidetextorientation='horizontal',
      automargin=False,
      hovertemplate=hover_html_text,
    )
  )
  if total:
    html_text = f'''<b>{total:,}건</b>'''
  else:
    html_text = f'''<b>보도 없음<br>(0건)</b>'''  # noqa: F541
  _base_layout(figure, DONUT_HEIGHT)
  figure.update_layout(
    width=DONUT_WIDTH,
    margin={'l': 0, 'r': 0, 't': 5, 'b': 5},
    meta={'donut_diameter': DONUT_DIAMETER},
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    showlegend=False,
    annotations=[
      {
        'text': html_text,
        'x': 0.5,
        'y': 0.5,
        'xanchor': 'center',
        'yanchor': 'middle',
        'xref': 'paper',
        'yref': 'paper',
        'showarrow': False,
        'font': {'size': 15, 'weight': 700},
      }
    ],
  )
  return figure


def period_trend_chart(trend, labels, colors, granularity):
  '''기간별 선택 범주 사용 보도 수를 Plotly 선그래프로 표시한다.'''
  figure = go.Figure()
  trend = with_period_changes(trend)
  date_format = '%Y-%m' if granularity == 'month' else '%Y-%m-%d'
  buckets = sorted(trend['bucket'].unique())
  bucket_keys = [pd.Timestamp(bucket).strftime(date_format) for bucket in buckets]
  for category_id, label in labels.items():
    rows = trend.loc[trend['category_id'].eq(category_id)]
    figure.add_trace(
      go.Scatter(
        x=rows['bucket'].dt.strftime(date_format).tolist(),
        y=rows['count'].tolist(),
        name=label,
        mode='lines+markers',
        line={'color': colors[category_id], 'width': 3},
        marker={'size': 7, 'color': colors[category_id]},
        customdata=[[category_id, row.change_text] for row in rows.itertuples()],
        cliponaxis=False,
        hoverinfo='none',
      )
    )
  _base_layout(figure, 410)
  figure.update_layout(hovermode='closest', clickmode='event', dragmode=False)
  step = 7 if granularity == 'day' and len(buckets) > 14 else 1
  ticks = sorted({*range(0, len(buckets), step), len(buckets) - 1}) if buckets else []
  figure.update_xaxes(
    type='category',
    categoryorder='array',
    categoryarray=bucket_keys,
    tickvals=[bucket_keys[index] for index in ticks],
    ticktext=[
      pd.Timestamp(buckets[index]).strftime(
        '%m월' if granularity == 'month' else '%m.%d'
      )
      for index in ticks
    ],
    gridcolor=GRID_COLOR,
    fixedrange=True,
  )
  maximum = max(1, int(trend['count'].max())) if not trend.empty else 1
  figure.update_yaxes(
    title_text='기사 수 (건)',
    range=[0, maximum * 1.22],
    tickmode='linear',
    dtick=max(1, ceil(maximum / 6)),
    tickformat=',d',
    gridcolor=GRID_COLOR,
    fixedrange=True,
  )
  return figure
