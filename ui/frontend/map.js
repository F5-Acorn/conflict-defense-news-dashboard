export default function({parentElement, data, setTriggerValue}) {
  const frame = parentElement.querySelector('iframe');
  frame.dashboardCleanup?.();
  let mapDocument, map, observer;
  const save = () => {
    if (!map) return;
    const {lat, lng} = map.getCenter();
    const viewport = {focus_token:data.focus_token, center:[lat, lng], zoom:map.getZoom()};
    frame.dashboardViewport = viewport;
    try { sessionStorage.setItem(data.storage_key, JSON.stringify(viewport)); } catch { /* 저장소 차단 시 현재 iframe의 상태는 유지한다. */ }
  };
  const read = () => {
    try { return JSON.parse(sessionStorage.getItem(data.storage_key)) || frame.dashboardViewport; }
    catch { return frame.dashboardViewport; }
  };
  const preserveScroll = (event) => {
    const marker = event.target;
    if (event.button === 0 && marker.matches?.('path.leaflet-interactive')) {
      event.preventDefault();
      marker.closest('.leaflet-container')?.focus({preventScroll:true});
    }
  };
  const loaded = () => {
    mapDocument = frame.contentDocument;
    map = frame.contentWindow?.dashboardMap;
    if (!map) return;
    mapDocument.addEventListener('mousedown', preserveScroll, true);
    const saved = read();
    if (map.dashboardFocusToken !== data.focus_token) {
      if (saved?.focus_token === data.focus_token && Array.isArray(saved.center) &&
          saved.center.length === 2 && saved.center.every(Number.isFinite) &&
          Number.isFinite(saved.zoom) && saved.zoom >= map.getMinZoom() && saved.zoom <= map.getMaxZoom()) {
        map.setView(saved.center, saved.zoom, {animate:false, reset:true});
      }
      map.dashboardFocusToken = data.focus_token;
    }
    map.on('moveend zoomend', save);
    save();
    let width, height;
    observer = new ResizeObserver(entries => {
      const size = entries[0].contentRect;
      if (size.width === width && size.height === height) return;
      width = size.width; height = size.height;
      const center = map.getCenter(), zoom = map.getZoom();
      map.invalidateSize({pan:false, animate:false});
      map.setView(center, zoom, {animate:false, reset:true});
      save();
    });
    observer.observe(frame);
  };
  frame.addEventListener('load', loaded);
  if (frame.dashboardHtml !== data.html) {
    frame.dashboardHtml = data.html;
    frame.srcdoc = data.html;
  } else {
    loaded();
  }
  const receive = (event) => {
    if (event.source !== frame.contentWindow || event.data?.channel !== 'dashboard-map') return;
    if (event.data.context !== data.context) return;
    const {target_page, conflict_id} = event.data;
    if (!['annual', 'monthly', 'weekly'].includes(target_page)) return;
    setTriggerValue('action', {target_page, conflict_id, context:data.context});
  };
  window.addEventListener('message', receive);
  const cleanup = () => {
    save();
    observer?.disconnect();
    map?.off('moveend zoomend', save);
    window.removeEventListener('message', receive);
    frame.removeEventListener('load', loaded);
    mapDocument?.removeEventListener('mousedown', preserveScroll, true);
  };
  frame.dashboardCleanup = cleanup;
  return cleanup;
}
