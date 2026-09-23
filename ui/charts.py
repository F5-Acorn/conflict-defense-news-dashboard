'''집계된 데이터를 현재 디자인의 Plotly 선 그래프와 누적 막대그래프로 만든다.'''

import pandas as pd
import plotly.graph_objects as go

from config import CHART_BACKGROUND, GRID_COLOR, TEXT_COLOR
from services.analysis_service import is_partial_month


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


def trend_chart(trend, kind, start, end, category_colors):
  '''월·범주·건수 집계와 유형·조회 기간을 받아 월별 추이 차트를 반환한다.'''
  figure = go.Figure()
  months = pd.date_range(start.replace(day=1), end.replace(day=1), freq='MS')
  # 축에는 선택 기간의 모든 월을 표시하고 일부 날짜만 포함된 월을 구분한다.
  month_keys = []
  month_labels = []
  for month in months:
    month_keys.append(month.strftime('%Y-%m'))
    label = f'{month:%Y.%m}' if start.year != end.year else f'{month.month}월'
    if is_partial_month(month.date(), start, end):
      label += '<br>(부분 기간)'
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
        hovertemplate=f'{category}<br>%{{x}} · %{{y:,}}건<extra></extra>',
      )
    )
  _base_layout(figure, 340)
  figure.update_layout(hovermode='x unified')
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
    fixedrange=True,
  )
  return figure


def distribution_chart(ranking, distribution, conflicts):
  '''Top 3 순위와 범주·분쟁별 건수를 받아 분쟁별 누적 가로 막대그래프를 반환한다.'''
  figure = go.Figure()
  ordered = ranking['category'].tolist()
  for conflict, config in conflicts.items():
    conflict_rows = distribution.loc[distribution['conflict'] == conflict]
    category_counts = conflict_rows.set_index('category')['count']
    values = category_counts.reindex(ordered, fill_value=0)
    if not values.any():
      continue
    figure.add_trace(
      go.Bar(
        name=conflict,
        y=ordered,
        x=values.tolist(),
        orientation='h',
        marker_color=config['color'],
        text=[f'{value:,}건' if value else '' for value in values],
        textposition='inside',
        insidetextanchor='middle',
        textfont={'color': 'white', 'size': 14},
        hovertemplate=f'{conflict}<br>%{{y}} · %{{x:,}}건<extra></extra>',
      )
    )
  _base_layout(figure, 330)
  # 같은 범주의 분쟁별 보도를 한 막대에 쌓고, 순위가 높은 범주부터 위에 놓는다.
  figure.update_layout(
    barmode='stack',
    bargap=0.42,
    margin={'l': 10, 'r': 35, 't': 20, 'b': 110},
    legend={'yanchor': 'top', 'y': -0.15, 'xanchor': 'left', 'x': 0},
  )
  maximum = max(1, int(ranking['count'].max())) if not ranking.empty else 1
  figure.update_xaxes(visible=False, range=[0, maximum * 1.16], fixedrange=True)
  figure.update_yaxes(
    categoryorder='array', categoryarray=ordered, autorange='reversed', fixedrange=True
  )
  # 각 막대의 오른쪽에 분쟁을 합친 범주별 총 보도 수를 표시한다.
  for row in ranking.itertuples():
    figure.add_annotation(
      x=row.count,
      y=row.category,
      text=f'<b>{row.count:,}건</b>',
      showarrow=False,
      xanchor='left',
      xshift=12,
      font={'color': '#edf4fc', 'size': 14},
    )
  return figure
