export default function({parentElement, data, setTriggerValue}) {
  const frame = parentElement.querySelector('iframe');
  frame.dashboardCleanup?.();
  let mapDocument;
  const preserveScroll = (event) => {
    const marker = event.target;
    if (event.button === 0 && marker.matches?.('path.leaflet-interactive')) {
      // SVG 마커의 기본 포커스가 부모 스크롤을 이동시키면 mouseup 대상이 달라진다.
      // 포커스 접근성은 유지하면서 첫 클릭의 위치를 고정한다.
      event.preventDefault();
      marker.closest('.leaflet-container')?.focus({preventScroll:true});
    }
  };
  const loaded = () => {
    mapDocument = frame.contentDocument;
    mapDocument?.addEventListener('mousedown',preserveScroll,true);
  };
  frame.addEventListener('load',loaded);
  frame.srcdoc = data.html;
  const receive = (event) => {
    if (event.source !== frame.contentWindow || event.data?.channel !== 'dashboard-map') return;
    const {kind, conflict_id} = event.data;
    setTriggerValue('action', {kind, conflict_id, context: data.context});
  };
  window.addEventListener('message', receive);
  const cleanup = () => {
    window.removeEventListener('message', receive);
    frame.removeEventListener('load',loaded);
    mapDocument?.removeEventListener('mousedown',preserveScroll,true);
  };
  frame.dashboardCleanup = cleanup;
  return cleanup;
}
