export default function({parentElement, data, setTriggerValue}) {
  const frame = parentElement.querySelector('iframe');
  const loading = parentElement.querySelector('.dashboard-loading');
  frame.dashboardCleanup?.();
  let mapDocument, map, observer, disposed = false, activeId = null;
  const cards = data.cards || {};
  function clearFocus() {
    if (activeId !== null) {
      document.querySelector(`.${CSS.escape('st-key-' + cards[activeId])}`)?.classList.remove('overview-conflict-focused');
    }
    activeId = null;
  }
  function focusCard(id) {
    if (!Object.hasOwn(cards, id)) return;
    const card = document.querySelector(`.${CSS.escape('st-key-' + cards[id])}`);
    const list = document.querySelector('.st-key-overview_conflicts');
    if (!card || !list) return;
    const changed = activeId !== id;
    clearFocus();
    activeId = id;
    card.style.setProperty('--conflict-focus-color', data.colors[id]);
    card.classList.add('overview-conflict-focused');
    const box = card.getBoundingClientRect(), bounds = list.getBoundingClientRect();
    if (changed || box.top < bounds.top || box.bottom > bounds.bottom) {
      list.scrollTo({top:list.scrollTop + box.top - bounds.top - 16,
        behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    }
  }
  const save = () => {
    if (!map || map.dashboardLocked) return;
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
    if (event.button === 0 && event.target.matches?.('path.leaflet-interactive')) {
      event.preventDefault();
      event.target.closest('.leaflet-container')?.focus({preventScroll:true});
    }
  };
  function failed() {
    if (disposed) return;
    loading.querySelector('.dashboard-spinner').hidden = true;
    loading.querySelector('.dashboard-loading-message').textContent = '지도를 표시할 수 없습니다.';
    loading.hidden = false;
  }
  const loaded = () => {
    if (disposed) return;
    mapDocument = frame.contentDocument;
    map = frame.contentWindow?.dashboardMap;
    if (!map) { failed(); return; }
    map.whenReady(() => {
      if (disposed) return;
      mapDocument.addEventListener('mousedown', preserveScroll, true);
      const saved = read();
      if (!map.dashboardLocked && map.dashboardFocusToken !== data.focus_token &&
          saved?.focus_token === data.focus_token && Array.isArray(saved.center) &&
          saved.center.length === 2 && saved.center.every(Number.isFinite) &&
          Number.isFinite(saved.zoom) && saved.zoom >= map.getMinZoom() && saved.zoom <= map.getMaxZoom()) {
        map.setView(saved.center, saved.zoom, {animate:false, reset:true});
      }
      map.dashboardFocusToken = data.focus_token;
      map.on('moveend zoomend', save);
      save();
      let width, height;
      observer = new ResizeObserver(entries => {
        const size = entries[0].contentRect;
        if (size.width === width && size.height === height) return;
        width = size.width; height = size.height;
        map.invalidateSize({pan:false, animate:false});
        map._popup?.update();
        save();
      });
      observer.observe(frame);
      if (map.dashboardActiveConflictId !== null) focusCard(map.dashboardActiveConflictId);
      frame.style.visibility = 'visible';
      loading.hidden = true;
    });
  };
  const receive = (event) => {
    if (disposed || event.source !== frame.contentWindow || event.data?.channel !== 'dashboard-map') return;
    if (event.data.context !== data.context) return;
    const {type, target_page, conflict_id} = event.data;
    if (typeof conflict_id !== 'string' || !Object.hasOwn(cards, conflict_id)) return;
    if (type === 'focus_conflict') { focusCard(conflict_id); return; }
    if (type === 'clear_focus') {
      if (activeId === conflict_id && !map?.dashboardLocked) clearFocus();
      return;
    }
    if (!['annual', 'monthly', 'weekly'].includes(target_page)) return;
    setTriggerValue('action', {target_page, conflict_id, context:data.context});
  };
  window.addEventListener('message', receive);
  frame.addEventListener('load', loaded);
  frame.addEventListener('error', failed);
  if (frame.dashboardHtml !== data.html) {
    loading.hidden = false;
    loading.querySelector('.dashboard-spinner').hidden = false;
    loading.querySelector('.dashboard-loading-message').textContent = '지도를 준비하는 중…';
    frame.style.visibility = 'hidden';
    frame.dashboardHtml = data.html;
    frame.srcdoc = data.html;
  } else loaded();
  const cleanup = () => {
    disposed = true;
    save();
    clearFocus();
    observer?.disconnect();
    map?.off('moveend zoomend', save);
    window.removeEventListener('message', receive);
    frame.removeEventListener('load', loaded);
    frame.removeEventListener('error', failed);
    mapDocument?.removeEventListener('mousedown', preserveScroll, true);
  };
  frame.dashboardCleanup = cleanup;
  return cleanup;
}
