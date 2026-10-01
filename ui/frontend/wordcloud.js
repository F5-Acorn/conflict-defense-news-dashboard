export default function ({ parentElement, data, setStateValue, key }) {
	const registry = (window.__dashboardWordcloudRenderers ||= new Map());
	registry.get(key)?.();
	const root = parentElement.querySelector('.period-wordcloud-image');
	const image = root.querySelector('img');
	const loading = root.querySelector('.period-wordcloud-loading');
	let timer, disposed = false;

	function measure() {
		if (disposed || !root.isConnected) return;
		const { width, height } = root.getBoundingClientRect();
		if (width < 16 || height < 16) return;
		// 서버 캔버스를 부모와 같은 비율의 2배 해상도로 생성한다.
		const scale = Math.min(2, 2048 / Math.max(width, height));
		const size = {
			width: Math.max(32, Math.round(width * scale)),
			height: Math.max(32, Math.round(height * scale)),
		};
		const matches = data.image && size.width === data.size.width && size.height === data.size.height;
		const ready = matches && image.complete && image.naturalWidth > 0;
		// 부모 크기와 일치하는 최종 배치가 로드된 뒤에만 표시한다.
		image.style.visibility = ready ? 'visible' : 'hidden';
		image.style.objectFit = 'fill';
		loading.style.display = ready ? 'none' : 'flex';
		clearTimeout(timer);
		if (!matches) {
			timer = setTimeout(() => {
				if (!disposed) setStateValue('size', size);
			}, data.image ? 200 : 0);
		}
	}

	const observer = new ResizeObserver(measure);
	image.onload = measure;
	if (data.image) image.src = data.image;
	observer.observe(root);
	measure();
	const cleanup = () => {
		disposed = true;
		clearTimeout(timer);
		observer.disconnect();
		image.onload = null;
		if (registry.get(key) === cleanup) registry.delete(key);
	};
	registry.set(key, cleanup);
	return cleanup;
}
