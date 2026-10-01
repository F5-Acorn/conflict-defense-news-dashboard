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
  counts,
  conflicts,
  *,
  scale_max=None,
  conflict_ids=None,
  context=None,
  locked_conflict_id=None,
):
  '''분쟁별 보도 수와 선택 모드로 지도·중심점에 연결된 팝업을 만든다.'''
  locked = locked_conflict_id is not None
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
    zoom_control=not locked,
    dragging=not locked,
    double_click_zoom=not locked,
    touch_zoom=not locked,
    box_zoom=not locked,
    keyboard=not locked,
    tap_hold=not locked,
    fade_animation=False,
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
                    .leaflet-popup.conflict-popup {{margin-bottom:0;}}
                    .conflict-popup .leaflet-popup-content-wrapper {{
                      background:rgba(7,20,30,.94);color:#f4f8ff;border-radius:9px;
                      border:2px solid var(--conflict-color);box-shadow:0 3px 16px #0008;
                      font:14px/1.4 Arial,sans-serif;
                    }}
                    .conflict-map-title {{display:flex;flex-wrap:wrap;align-items:center;gap:0.5rem;}}
                    .conflict-map-name {{font-size:14px;font-weight:600;overflow-wrap:anywhere;}}
                    .conflict-map-count {{font-size:16px;font-weight:750;color:var(--conflict-color);line-height:1.15;}}
                    .conflict-popup .leaflet-popup-content {{margin:12px 15px;width:min(280px,calc(100vw - 66px)) !important;}}
                    .conflict-popup .leaflet-popup-tip-container {{
                      left:calc(50% + var(--popup-center-offset,0px));margin-left:-12px;margin-top:0;width:24px;height:20px;overflow:visible;
                    }}
                    .conflict-popup .leaflet-popup-tip {{
                      background:var(--conflict-color);width:24px;height:20px;
                      margin:0;padding:0;transform:none;box-shadow:none;
                      clip-path:polygon(0 0,100% 0,50% 100%);
                    }}
                    .conflict-popup .leaflet-popup-content {{max-height:calc(100vh - 64px);overflow-y:auto;}}
                    .conflict-popup .leaflet-popup-close-button {{color:#eef6ff;right:4px;top:4px;}}
                    .conflict-popup button {{font-size:12px;margin:9px 5px 0 0;padding:4px 8px;cursor:pointer;
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
  markers = []
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
    halo = folium.CircleMarker(
      location,
      radius=radius + 8,
      color=color,
      weight=0,
      fill=True,
      fill_color=color,
      fill_opacity=0.16,
    )
    # Folium의 경로 옵션 변환은 interactive를 생략하므로 직접 전달한다.
    halo.options['interactive'] = False
    halo.add_to(world)
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
    html_text += f'<div class="conflict-map-actions">{buttons}</div>'
    marker = folium.CircleMarker(
      location,
      radius=radius,
      color=color,
      weight=3,
      fill=True,
      fill_color='#f4f8ff',
      fill_opacity=1,
      popup=folium.Popup(
        html_text,
        max_width=340,
        class_name=f'conflict-popup {style_class}',
        offset=(0, -20),
        auto_pan=True,
        auto_pan_padding=(12, 12),
        close_button=not locked,
        close_on_click=not locked,
        close_on_escape_key=not locked,
        auto_close=not locked,
      ),
    ).add_to(world)
    marker.options['interactive'] = not locked
    if conflict_ids and conflict in conflict_ids:
      markers.append({'id': conflict_ids[conflict], 'name': marker.get_name()})
  if len(locations) > 1:
    bounds = [
      [min(point[i] for point in locations) for i in (0, 1)],
      [max(point[i] for point in locations) for i in (0, 1)],
    ]
    world.fit_bounds(bounds, padding=(40, 40), max_zoom=4)
  bridge = MacroElement()
  bridge._template = Template('''{% macro script(this, kwargs) %}
    (function() {
      const map = {{this.map_name}};
      const context = {{this.context | tojson}};
      const markers = {
        {% for marker in this.markers %}
        {{marker.id | tojson}}: {{marker.name}}{% if not loop.last %},{% endif %}
        {% endfor %}
      };
      window.dashboardMap = map;
      map.dashboardMarkers = markers;
      map.dashboardLocked = {{this.locked | tojson}};
      map.dashboardActiveConflictId = null;
      for (const [id, marker] of Object.entries(markers)) {
        marker.getPopup().dashboardConflictId = id;
      }
      function notify(type, conflictId) {
        window.parent.postMessage({channel:'dashboard-map', type,
          conflict_id:conflictId, context}, '*');
      }
      function alignTail(popup) {
        const node = popup.getElement();
        // Leaflet은 팝업 너비의 절반을 반올림하므로 홀수 너비의 0.5px도 보정한다.
        const halfWidth = node.offsetWidth / 2;
        node.style.setProperty('--popup-center-offset', (Math.round(halfWidth) - halfWidth) + 'px');
      }
      map.on('popupopen', event => {
        alignTail(event.popup);
        const id = event.popup.dashboardConflictId;
        map.dashboardActiveConflictId = id;
        notify('focus_conflict', id);
      });
      map.on('popupclose', event => {
        const id = event.popup.dashboardConflictId;
        if (map.dashboardActiveConflictId === id) map.dashboardActiveConflictId = null;
        notify('clear_focus', id);
      });
      map.on('resize', () => {
        if (map._popup && map.hasLayer(map._popup)) {
          map._popup.update();
          alignTail(map._popup);
        }
      });
      const selected = markers[{{this.locked_conflict_id | tojson}}];
      if (selected) map.whenReady(() => selected.openPopup());
    })();
  {% endmacro %}''')
  bridge.map_name = world.get_name()
  bridge.context = context
  bridge.markers = markers
  bridge.locked = locked
  bridge.locked_conflict_id = locked_conflict_id
  world.add_child(bridge)
  return world
