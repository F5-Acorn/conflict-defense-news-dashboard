'''국가 경계 데이터와 분쟁별 집계 결과로 Folium 지도를 만든다.'''

import json
from html import escape
from math import sqrt
from pathlib import Path

import folium
import streamlit as st
from branca.element import MacroElement, Template


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


def build_conflict_map(
  counts, top_categories, conflicts, *, scale_max=None, conflict_ids=None, context=None
):
  '''분쟁별 보도 수와 유형별 Top 3 이름을 받아 Folium 지도 객체를 반환한다.'''
  # 강조 원·라벨까지 포함해 0건인 분쟁은 지도에 생성하지 않는다.
  counts = {name: count for name, count in counts.items() if count > 0}
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
    track_resize=False,
  )
  # 지도는 별도 iframe에 있으므로 지도 배경·출처 스타일은 지도 HTML에 넣는다.
  html_text = f'''<style>
                    .leaflet-container {{ background: #0b1b26 !important; }}
                    .leaflet-control-attribution {{ background: #102331 !important; color: #adc5df; }}
                    .leaflet-control-attribution a {{ color: #adc5df; }}
                    .leaflet-tooltip.conflict-callout,.conflict-popup .leaflet-popup-content-wrapper {{
                      background:rgba(7,20,30,.94);color:#f4f8ff;border-radius:9px;
                      border:2px solid var(--conflict-color);box-shadow:0 3px 16px #0008;
                      font:14px/1.4 Arial,sans-serif;
                    }}
                    .leaflet-tooltip.conflict-callout {{padding:9px 14px;white-space:normal;width:190px;}}
                    .conflict-detail-open .conflict-callout {{display:none;}}
                    .leaflet-tooltip.conflict-callout:before {{border-right-color:var(--conflict-color);}}
                    .leaflet-tooltip.conflict-callout.leaflet-tooltip-left:before {{border-left-color:var(--conflict-color);border-right-color:transparent;}}
                    .leaflet-tooltip.conflict-callout.leaflet-tooltip-top:before {{border-top-color:var(--conflict-color);border-right-color:transparent;}}
                    .leaflet-tooltip.conflict-callout.leaflet-tooltip-bottom:before {{border-bottom-color:var(--conflict-color);border-right-color:transparent;}}
                    .conflict-map-title {{display:flex;flex-wrap:wrap;align-items:center;gap:0.5rem;}}
                    .conflict-map-name {{font-size:14px;font-weight:600;overflow-wrap:anywhere;}}
                    .conflict-map-count {{font-size:16px;font-weight:750;color:var(--conflict-color);line-height:1.15;}}
                    .conflict-popup .leaflet-popup-content {{margin:12px 15px;width:min(280px,calc(100vw - 66px)) !important;}}
                    .conflict-popup .leaflet-popup-tip {{background:var(--conflict-color);}}
                    .conflict-popup .leaflet-popup-tip-container {{left:calc(50% - var(--popup-shift-x, 0px));}}
                    .conflict-popup .leaflet-popup-content {{max-height:calc(100vh - 64px);overflow-y:auto;}}
                    .conflict-popup .leaflet-popup-close-button {{color:#eef6ff;right:4px;top:4px;}}
                    .conflict-map-details {{font-size:12px;line-height:1.5;margin-top:8px;}}
                    .conflict-map-details div {{margin-top:4px;}}
                    .conflict-popup button {{font-size:10px;margin:9px 5px 0 0;padding:4px 8px;cursor:pointer;
                      border:1px solid var(--conflict-color);border-radius:5px;background:#203448;color:#f4f8ff;}}
                  </style>'''  # noqa: F541
  world.get_root().header.add_child(folium.Element(html_text))
  folium.GeoJson(
    _world_boundaries(),
    name='Natural Earth',
    control=False,
    style_function=_country_style,
    zoom_on_click=False,
  ).add_to(world)
  html_text = f'''<div style="position:absolute;bottom:5px;left:8px;z-index:1000;font:10px sans-serif;color:#a6bfd7">
                    <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener noreferrer" style="color:inherit">Made with Natural Earth</a>
                  </div>'''  # noqa: F541
  world.get_root().html.add_child(folium.Element(html_text))
  maximum = max(counts.values(), default=0) if scale_max is None else scale_max
  for index, (conflict, count) in enumerate(counts.items()):
    config = conflicts[conflict]
    color = config['color']
    style_class = f'conflict-color-{index}'
    html_text = f'''<style>
                      .{style_class} {{--conflict-color:{color};}}
                    </style>'''
    world.get_root().header.add_child(folium.Element(html_text))
    location = config['location']
    radius = max(6, min(24, 24 * sqrt(count / maximum))) if maximum else 6
    folium.CircleMarker(
      location,
      radius=radius + 8,
      color=color,
      weight=0,
      fill=True,
      fill_color=color,
      fill_opacity=0.16,
      interactive=False,
    ).add_to(world)
    popup_rows = []
    for kind, names in top_categories[conflict].items():
      category_names = escape(', '.join(names)) or '보도 없음'
      html_text = f'''<div>주요 {escape(kind)}: {category_names}</div>'''
      popup_rows.append(html_text)
    popup_rows = '\n'.join(popup_rows)
    button_items = []
    if conflict_ids and conflict in conflict_ids:
      for target, label in (
        ('annual', '연간 분석'),
        ('monthly', '월간 분석'),
        ('weekly', '주간 분석'),
      ):
        payload = escape(
          json.dumps(
            {
              'channel': 'dashboard-map',
              'conflict_id': conflict_ids[conflict],
              'target_page': target,
              'context': context,
            },
            ensure_ascii=False,
          ),
          quote=True,
        )
        html_text = f'''<button type="button" onclick="window.parent.postMessage({payload}, '*')">{label}</button>'''
        button_items.append(html_text)
    buttons = '\n'.join(button_items)
    html_text = f'''<div class="conflict-map-title">
                      <div class="conflict-map-name">{escape(conflict)}</div>
                      <div class="conflict-map-count">{count:,}건</div>
                    </div>'''
    heading = html_text
    html_text = f'''{heading}
                    <div class="conflict-map-details">
                      {popup_rows}
                    </div>
                    {buttons}'''
    marker = folium.CircleMarker(
      location,
      radius=radius,
      color=color,
      weight=3,
      fill=True,
      fill_color='#f4f8ff',
      fill_opacity=1,
      tooltip=f'{escape(conflict)}: {count:,}건',
      popup=folium.Popup(
        html_text,
        max_width=340,
        class_name=f'conflict-popup {style_class}',
        auto_pan=False,
      ),
    ).add_to(world)
    # 여러 분쟁은 툴팁과 팝업으로 확인하고, 단일 분쟁만 고정 라벨을 표시한다.
    if len(locations) != 1:
      continue
    # 지도 좌표는 분쟁 지역을 표시하는 대표 위치이며 개별 사건 위치가 아니다.
    folium.Tooltip(
      heading,
      permanent=True,
      direction='right',
      offset=(radius + 12, -24),
      class_name=f'conflict-callout {style_class}',
      sticky=False,
    ).add_to(marker)
    behavior = MacroElement()
    behavior._template = Template('''{% macro script(this, kwargs) %}
      (function() {
        const map = {{this.map_name}}, marker = {{this.marker_name}};
        function placeCallout() {
          const tooltip = marker.getTooltip(), node = tooltip.getElement();
          if (!node || marker.isPopupOpen()) return;
          const point = map.latLngToContainerPoint(marker.getLatLng());
          const size = map.getSize(), box = node.getBoundingClientRect();
          let horizontal, vertical;
          if (point.x + box.width + {{this.offset}} + 12 < size.x || point.x > box.width + {{this.offset}} + 12) {
            tooltip.options.direction = point.x + box.width + {{this.offset}} + 12 < size.x ? 'right' : 'left';
            horizontal = tooltip.options.direction === 'right' ? {{this.offset}} : -{{this.offset}};
            vertical = Math.max(12 + box.height/2 - point.y, Math.min(-24, size.y - 12 - box.height/2 - point.y));
          } else {
            tooltip.options.direction = point.y > box.height + {{this.offset}} + 12 ? 'top' : 'bottom';
            horizontal = Math.max(12 + box.width/2 - point.x, Math.min(0, size.x - 12 - box.width/2 - point.x));
            vertical = tooltip.options.direction === 'top' ? -{{this.offset}} : {{this.offset}};
          }
          tooltip.options.offset = L.point(horizontal, vertical);
          tooltip.update();
        }
        marker.on('popupopen', () => {
          map.getContainer().classList.add('conflict-detail-open'); marker.closeTooltip();
        });
        marker.on('popupclose', () => {
          map.getContainer().classList.remove('conflict-detail-open');
          marker.openTooltip(); placeCallout();
        });
        map.on('moveend resize', placeCallout);
        setTimeout(placeCallout, 0);
      })();
    {% endmacro %}''')
    behavior.map_name = world.get_name()
    behavior.marker_name = marker.get_name()
    behavior.offset = radius + 12
    world.add_child(behavior)
  if len(locations) > 1:
    bounds = [
      [min(point[i] for point in locations) for i in (0, 1)],
      [max(point[i] for point in locations) for i in (0, 1)],
    ]
    world.fit_bounds(bounds, padding=(40, 40), max_zoom=4)
  # iframe 재생성 후에도 부모 컴포넌트가 준비된 지도에 저장한 시점을 복원한다.
  bridge = MacroElement()
  bridge._template = Template('''{% macro script(this, kwargs) %}
    (function() {
      const map = {{this.map_name}};
      window.dashboardMap = map;
      function placePopup() {
        const popup = map._popup;
        if (!popup || !map.hasLayer(popup)) return;
        popup.options.offset = L.point(0, 7);
        popup.update();
        const node = popup.getElement(), container = map.getContainer().getBoundingClientRect();
        const box = node.getBoundingClientRect();
        const dx = Math.max(container.left + 12 - box.left, Math.min(0, container.right - 12 - box.right));
        const dy = Math.max(container.top + 12 - box.top, Math.min(0, container.bottom - 12 - box.bottom));
        popup.options.offset = L.point(dx, 7 + dy);
        node.style.setProperty('--popup-shift-x', dx + 'px');
        popup.update();
      }
      map.on('popupopen moveend resize', placePopup);
    })();
  {% endmacro %}''')
  bridge.map_name = world.get_name()
  world.add_child(bridge)
  return world
