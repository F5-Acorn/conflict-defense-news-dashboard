'''집계된 데이터를 현재 디자인의 Plotly 선 그래프와 누적 막대그래프로 만든다.'''

from math import ceil

import pandas as pd
import plotly.graph_objects as go

from config import CHART_BACKGROUND, GRID_COLOR, TEXT_COLOR
from data.constants import STATUS_LABELS, UsageCode
from services.detail_service import with_month_changes


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


def trend_chart(trend, kind, start, end, category_colors, category_ids=None):
  '''월·범주·건수 집계와 유형·조회 기간을 받아 월별 추이 차트를 반환한다.'''
  figure = go.Figure()
  trend = with_month_changes(trend)
  months = pd.date_range(start.replace(day=1), end.replace(day=1), freq='MS')
  # 축에는 선택 기간의 모든 월을 표시하고 일부 날짜만 포함된 월을 구분한다.
  month_keys = []
  month_labels = []
  for month in months:
    month_keys.append(month.strftime('%Y-%m'))
    label = f'{month:%Y.%m}' if start.year != end.year else f'{month.month}월'
    month_labels.append(label)
  selected_categories = sorted(trend['category'].unique())
  for category in selected_categories:
    category_rows = trend.loc[trend['category'] == category]
    monthly_counts = category_rows.set_index('month')['count']
    values = monthly_counts.reindex(months, fill_value=0)
    color = category_colors[kind][category]
    # 네 범주 이상 선택하면 숫자 라벨이 겹치지 않도록 선과 점만 표시한다.
    figure.add_trace(
      go.Scatter(
        x=month_keys,
        y=values.tolist(),
        name=category,
        mode=(
          'lines+markers+text'
          if len(selected_categories) <= 3 and len(months) <= 12
          else 'lines+markers'
        ),
        line={'color': color, 'width': 3},
        marker={'size': 9, 'color': '#edf4fc', 'line': {'color': color, 'width': 3}},
        text=[f'{value:,}' for value in values],
        textposition='top center',
        textfont={'color': color, 'size': 12},
        cliponaxis=False,
        customdata=[
          [
            category_ids.get(category, category) if category_ids else category,
            row.change_text,
          ]
          for row in category_rows.itertuples()
        ],
        hovertemplate=f'{category}<br>%{{x}} · %{{y:,}}건<extra></extra>',
      )
    )
  _base_layout(figure, 340)
  figure.update_layout(hovermode='closest', clickmode='event', dragmode=False)
  figure.update_traces(hovertemplate=None, hoverinfo='none')
  # 월 간격은 일정하게 두고 건수 축은 최대값보다 여유 있게 표시한다.
  step = max(1, (len(months) + 11) // 12)
  ticks = sorted({*range(0, len(months), step), len(months) - 1})
  figure.update_xaxes(
    type='category',
    categoryorder='array',
    categoryarray=month_keys,
    tickvals=[month_keys[index] for index in ticks],
    ticktext=[month_labels[index] for index in ticks],
    gridcolor=GRID_COLOR,
    showgrid=True,
    fixedrange=True,
  )
  maximum = max(1, int(trend['count'].max())) if not trend.empty else 1
  figure.update_yaxes(
    title_text='기사 수 (건)',
    range=[0, maximum * 1.22],
    gridcolor=GRID_COLOR,
    zerolinecolor=GRID_COLOR,
    tickformat=',d',
    tickmode='linear',
    tick0=0,
    dtick=max(1, ceil(maximum / 6)),
    fixedrange=True,
  )
  return figure


STATUS_COLORS = {
  UsageCode.USED: '#20bda6',
  UsageCode.UNCERTAIN: '#f1b94a',
  UsageCode.NOT_USED: '#8598b0',
}
MOSAIC_BAR_HEIGHT = 48
MOSAIC_ROW_GAP = 12


def mosaic_chart(distribution):
  """범주마다 고정 높이의 가로 막대로 판정 비율을 표시한다."""
  figure = go.Figure()
  row_height = MOSAIC_BAR_HEIGHT + MOSAIC_ROW_GAP
  ticks, labels = [], []
  for category, rows in distribution.groupby('category', sort=True):
    total = int(rows['count'].sum())
    if not total:
      continue
    center = len(labels)
    ticks.append(center)
    labels.append(category)
    for code, label in STATUS_LABELS.items():
      row = rows.loc[rows['usage_code'].eq(code)].iloc[0]
      figure.add_trace(
        go.Bar(
          x=[float(row['ratio'])],
          y=[center],
          width=[MOSAIC_BAR_HEIGHT / row_height],
          orientation='h',
          name=label,
          legendgroup=str(code),
          showlegend=center == 0,
          marker={
            'color': STATUS_COLORS[code],
            'line': {'color': CHART_BACKGROUND, 'width': 2},
          },
          customdata=[[category, int(row['count'])]],
          text=[
            f"{int(row['count']):,}건<br>{row['ratio']:.0%}"
            if row['ratio'] >= 0.12
            else ''
          ],
          textposition='inside',
          hovertemplate=f'%{{customdata[0]}}<br>{label}: %{{customdata[1]:,}}건 (%{{x:.1%}})<extra></extra>',
        )
      )
  row_count = max(1, len(labels))
  # 좁은 화면에서 범례가 최대 세 줄로 나뉘어도 막대 영역을 줄이지 않는다.
  margin = {'l': 10, 'r': 30, 't': 90, 'b': 60}
  _base_layout(figure, row_count * row_height + margin['t'] + margin['b'])
  figure.update_layout(
    barmode='stack',
    bargap=0,
    margin=margin,
    legend={
      'xref': 'container',
      'yref': 'container',
      'x': 0.98,
      'y': 1,
      'xanchor': 'right',
      'yanchor': 'top',
    },
  )
  figure.update_xaxes(
    range=[0, 1],
    tickformat='.0%',
    fixedrange=True,
    gridcolor=GRID_COLOR,
    title_text='판정 비율',
  )
  figure.update_yaxes(
    range=[row_count - 0.5, -0.5],
    tickvals=ticks,
    ticktext=labels,
    fixedrange=True,
    showgrid=False,
    automargin='left',
  )
  return figure
