'''국가 경계 데이터와 분쟁별 집계 결과로 Folium 지도를 만든다.'''

import json
from html import escape
from pathlib import Path

import folium
import streamlit as st


@st.cache_data(show_spinner=False)
def _world_boundaries():
  '''로컬 국가 경계 GeoJSON을 사전으로 읽고 캐시해 지도에서 재사용한다.'''
  path = Path(__file__).resolve().parents[1] / 'assets' / 'world_countries.geojson'
  return json.loads(path.read_text(encoding='utf-8'))


def _country_style(feature):
  '''Folium이 전달하는 국가 경계에 동일한 남색 채우기와 테두리를 적용한다.'''
  return {
    'fillColor': '#203448',
    'color': '#45627d',
    'weight': 0.65,
    'fillOpacity': 0.85,
  }


def build_conflict_map(counts, top_categories, conflicts):
  '''분쟁별 보도 수와 유형별 Top 3 이름을 받아 Folium 지도 객체를 반환한다.'''
  # 공개 경계 데이터를 번들해 타일 API 키 없이 어두운 세계 지도를 표시한다.
  locations = [conflicts[name]['location'] for name in counts]
  center = (
    [sum(point[i] for point in locations) / len(locations) for i in (0, 1)]
    if locations
    else [0, 0]
  )
  world = folium.Map(
    location=center,
    zoom_start=4 if len(locations) == 1 else 2,
    min_zoom=1,
    max_zoom=6,
    tiles=None,
    control_scale=False,
    scrollWheelZoom=False,
    crs='EPSG4326',
    max_bounds=True,
    prefer_canvas=False,
    zoom_snap=0.1,
    zoom_animation=False,
  )
  # 지도는 별도 iframe에 있으므로 지도 배경·출처 스타일은 지도 HTML에 넣는다.
  world.get_root().header.add_child(
    folium.Element(
      '<style>.leaflet-container { background: #0b1b26 !important; } '
      '.leaflet-control-attribution { background: #102331 !important; color: #adc5df; } '
      '.leaflet-control-attribution a { color: #adc5df; } '
      '.conflict-map-label { transform: translate(-50%, 24px); }</style>'
    )
  )
  folium.GeoJson(
    _world_boundaries(),
    name='Natural Earth',
    control=False,
    style_function=_country_style,
    zoom_on_click=False,
  ).add_to(world)
  world.get_root().html.add_child(
    folium.Element(
      '<div style="position:absolute;bottom:5px;left:8px;z-index:1000;font:10px sans-serif;'
      'color:#a6bfd7"><a href="https://www.naturalearthdata.com/" target="_blank" '
      'rel="noopener noreferrer" style="color:inherit">Made with Natural Earth</a></div>'
    )
  )
  for conflict, count in counts.items():
    config = conflicts[conflict]
    color = config['color']
    location = config['location']
    folium.CircleMarker(
      location,
      radius=18,
      color=color,
      weight=0,
      fill=True,
      fill_color=color,
      fill_opacity=0.16,
    ).add_to(world)
    popup_rows = []
    for kind, names in top_categories[conflict].items():
      category_names = escape(', '.join(names)) or '보도 없음'
      popup_rows.append(f'주요 {escape(kind)}: {category_names}')
    popup_rows = '<br>'.join(popup_rows)
    folium.CircleMarker(
      location,
      radius=7,
      color=color,
      weight=3,
      fill=True,
      fill_color='#f4f8ff',
      fill_opacity=1,
      tooltip=f'{escape(conflict)}: {count:,}건',
      popup=folium.Popup(
        f'<b>{escape(conflict)}</b><br>{count:,}건<br>{popup_rows}', max_width=300
      ),
    ).add_to(world)
    # 여러 분쟁은 툴팁과 팝업으로 확인하고, 단일 분쟁만 고정 라벨을 표시한다.
    if len(locations) != 1:
      continue
    label = (
      f'<div class="conflict-map-label" style="background:#0b1b26ed;border:1px solid {color};border-radius:5px;'
      f"padding:6px 10px;white-space:nowrap;color:#edf4fc;font:13px sans-serif;"
      f'">{escape(conflict)}<br>'
      f'<strong style="color:{color};font-size:21px">{count:,}건</strong></div>'
    )
    # 지도 좌표는 분쟁 지역을 표시하는 대표 위치이며 개별 사건 위치가 아니다.
    folium.Marker(
      location, icon=folium.DivIcon(html=label, icon_size=(160, 55), icon_anchor=(0, 0))
    ).add_to(world)
  if len(locations) > 1:
    bounds = [
      [min(point[i] for point in locations) for i in (0, 1)],
      [max(point[i] for point in locations) for i in (0, 1)],
    ]
    world.fit_bounds(bounds, padding=(40, 40), max_zoom=4)
  return world
