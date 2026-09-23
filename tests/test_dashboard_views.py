'''장기간 조회, 빈 월·범주 및 지도·차트의 데이터 반영 검증.'''

import unittest
from datetime import date

import folium
import pandas as pd

from data.sample_data import load_dashboard_snapshot
from services.analysis_service import (
  latest_distribution,
  monthly_trend,
  ranked_categories,
)
from ui.charts import distribution_chart, trend_chart
from ui.maps import build_conflict_map


class DashboardViewsTest(unittest.TestCase):
  def test_sparse_months_and_missing_categories_are_zero_filled(self):
    frame = pd.DataFrame(
      {
        'date': pd.to_datetime(['2020-02-29', '2020-04-01']),
        'category': ['무인기', '무인기'],
        'count': [2, 3],
        'conflict': ['분쟁', '분쟁'],
      }
    )
    trend = monthly_trend(
      frame, ['무인기', '전차'], date(2020, 2, 29), date(2020, 4, 1)
    )
    self.assertEqual(len(trend), 6)
    self.assertEqual(
      trend.loc[trend['category'].eq('무인기'), 'count'].tolist(), [2, 0, 3]
    )
    self.assertTrue(trend.loc[trend['category'].eq('전차'), 'count'].eq(0).all())
    ranking, distribution = latest_distribution(frame, date(2020, 3, 31))
    self.assertTrue(ranking.empty)
    self.assertTrue(distribution.empty)
    self.assertTrue(monthly_trend(frame, [], date(2020, 2, 29), date(2020, 4, 1)).empty)

  def test_top_three_uses_name_order_for_ties(self):
    frame = pd.DataFrame(
      {'category': ['라', '다', '나', '가', '영'], 'count': [2, 2, 2, 2, 0]}
    )
    self.assertEqual(ranked_categories(frame)['category'].tolist(), ['가', '나', '다'])

  def test_ten_year_trend_and_twelve_conflict_map(self):
    snapshot = load_dashboard_snapshot()
    settings = snapshot['settings']
    selected = settings['default_categories']['무기']
    frame = snapshot['category_daily'].query('kind == "무기"')
    trend = monthly_trend(frame, selected, settings['start'], settings['end'])
    figure = trend_chart(
      trend, '무기', settings['start'], settings['end'], settings['category_colors']
    )
    self.assertEqual(len(figure.data[0].x), 120)
    self.assertLessEqual(len(figure.layout.xaxis.tickvals), 13)
    self.assertTrue(all('.' in value for value in figure.layout.xaxis.ticktext))
    self.assertNotIn('text', figure.data[0].mode)
    conflicts = settings['conflicts']
    counts = {name: index for index, name in enumerate(conflicts)}
    top = {name: {'무기': []} for name in conflicts}
    world = build_conflict_map(counts, top, conflicts)
    circles = [
      child
      for child in world._children.values()
      if isinstance(child, folium.CircleMarker)
    ]
    self.assertEqual(len(circles), 24)
    for point in conflicts.values():
      self.assertIn(list(point['location']), [marker.location for marker in circles])
    html = world.get_root().render()
    self.assertIn('fitBounds', html)
    for name in conflicts:
      self.assertIn(name, html)
    ranking, distribution = latest_distribution(frame, settings['end'])
    chart = distribution_chart(ranking, distribution, conflicts)
    self.assertEqual(sum(sum(trace.x) for trace in chart.data), ranking['count'].sum())
    self.assertEqual(chart.layout.legend.yanchor, 'top')


if __name__ == '__main__':
  unittest.main()
