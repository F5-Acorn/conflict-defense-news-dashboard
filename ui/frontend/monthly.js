export default function ({ parentElement, data, setTriggerValue, key }) {
	// v2는 같은 인스턴스에 새 데이터를 전달할 때 렌더러를 다시 호출할 수 있다.
	// 기존 이벤트와 body 포털을 먼저 정리해 중복 말풍선·리스너를 방지한다.
	const registry = (window.__dashboardMonthlyRenderers ||= new Map());
	registry.get(key)?.();
	const plot = parentElement.querySelector(".monthly-plot");
	const overlay = document.createElement("div");
	overlay.className = "monthly-overlay-root";
	document.body.appendChild(overlay);
	let pending = false;
	plot.setAttribute("aria-busy", "false");
	let disposed = false,
		bubble = null,
		drawer = null,
		previousFocus = null;
	const oldOverflow = document.body.style.overflow;
	let keyboardIndex = 0,
		activePoint = null;
	const points = data.figure.data.flatMap((trace, curveNumber) =>
		(trace.x || []).map((x, pointNumber) => ({
			x,
			y: trace.y[pointNumber],
			data: trace,
			curveNumber,
			pointNumber,
			customdata: trace.customdata[pointNumber],
		})),
	);
	function emit(type, values = {}) {
		if (pending) return;
		pending = true;
		plot.setAttribute("aria-busy", "true");
		setTriggerValue("action", {
			type,
			context: data.context,
			kind: data.kind,
			conflict_id: data.conflict_id,
			...values,
		});
	}
	function focusPlot() {
		if (plot.isConnected) plot.focus({ preventScroll: true });
	}
	function closeBubble(restore = false) {
		bubble?.remove();
		bubble = null;
		activePoint = null;
		if (restore) focusPlot();
	}
	function closeDrawer() {
		drawer?.remove();
		drawer = null;
		overlay.querySelector(".monthly-backdrop")?.remove();
		document.body.style.overflow = oldOverflow;
		if (previousFocus?.isConnected)
			previousFocus.focus({ preventScroll: true });
		else focusPlot();
		emit("close_articles");
	}
	function showBubble(point) {
		if (pending) return;
		closeBubble();
		keyboardIndex = Math.max(
			0,
			points.findIndex(
				(p) =>
					p.curveNumber === point.curveNumber &&
					p.pointNumber === point.pointNumber,
			),
		);
		activePoint = point;
		bubble = parentElement.querySelector('.monthly-bubble-template')
			.content.firstElementChild.cloneNode(true);
		bubble.setAttribute('aria-label', `${point.data.name} ${point.x} 기사 정보`);
		bubble.querySelector('h4').textContent = point.data.name;
		bubble.querySelector('.monthly-bubble-month').textContent = String(point.x).replace('-', '.');
		bubble.querySelector('strong').textContent = `${Number(point.y).toLocaleString()}건`;
		bubble.querySelector('p').textContent = `전월 대비: ${point.customdata[1]}`;
		bubble.querySelector('.monthly-close').onclick = () => closeBubble(true);
		bubble.querySelector('.monthly-open-articles').onclick = () => {
			previousFocus = plot;
			emit('open_articles', {category_id: point.customdata[0], month: point.x, page: 1});
			closeBubble();
		};
		overlay.appendChild(bubble);
		positionBubble();
		bubble.querySelector("button:last-child").focus({ preventScroll: true });
	}
	function positionBubble() {
		if (!bubble || !activePoint || !plot._fullLayout) return;
		const bounds = plot.getBoundingClientRect();
		const { xaxis, yaxis } = plot._fullLayout;
		const px = bounds.left + xaxis._offset + xaxis.d2p(activePoint.x);
		const py = bounds.top + yaxis._offset + yaxis.d2p(activePoint.y);
		const box = bubble.getBoundingClientRect();
		bubble.style.left = `${Math.max(12, Math.min(px + 12, window.innerWidth - box.width - 12))}px`;
		bubble.style.top = `${Math.max(12, Math.min(py + 12, window.innerHeight - box.height - 12))}px`;
	}
	function showDrawer(payload) {
		closeBubble();
		previousFocus = plot;
		// 내용과 페이지 버튼은 Python에서 생성한다. 브라우저에는 이벤트만 연결한다.
		overlay.insertAdjacentHTML('beforeend', payload.html);
		drawer = overlay.querySelector('.monthly-drawer');
		overlay.querySelector('.monthly-backdrop').onclick = closeDrawer;
		const close = drawer.querySelector('.monthly-close');
		close.onclick = closeDrawer;
		for (const link of drawer.querySelectorAll('[data-article-url]')) {
			try {
				const url = new URL(link.dataset.articleUrl);
				if (['http:', 'https:'].includes(url.protocol)) {
					link.href = url.href;
					continue;
				}
			} catch (_) { /* 유효하지 않은 URL은 링크로 표시하지 않는다. */ }
			link.remove();
		}
		for (const button of drawer.querySelectorAll('[data-page]')) {
			button.onclick = () => emit('article_page', {
				category_id: payload.category_id, month: payload.month,
				page: Number(button.dataset.page),
			});
		}
		document.body.style.overflow = "hidden";
		close.focus({ preventScroll: true });
	}
	const onKey = (event) => {
		if (event.key === "Escape") {
			if (drawer) {
				event.preventDefault();
				closeDrawer();
			} else if (bubble) {
				event.preventDefault();
				closeBubble(true);
			}
		}
		if (drawer && event.key === "Tab") {
			const focusable = [
				...drawer.querySelectorAll("button:not(:disabled),a[href]"),
			];
			const first = focusable[0],
				last = focusable.at(-1);
			if (event.shiftKey && document.activeElement === first) {
				event.preventDefault();
				last.focus();
			} else if (!event.shiftKey && document.activeElement === last) {
				event.preventDefault();
				first.focus();
			}
		}
	};
	const outside = (event) => {
		if (
			bubble &&
			!bubble.contains(event.target) &&
			!plot.contains(event.target)
		)
			closeBubble();
	};
	const plotKey = (event) => {
		if (
			!points.length ||
			![
				"ArrowLeft",
				"ArrowRight",
				"ArrowUp",
				"ArrowDown",
				"Enter",
				" ",
			].includes(event.key)
		)
			return;
		event.preventDefault();
		if (["ArrowLeft", "ArrowUp"].includes(event.key))
			keyboardIndex = (keyboardIndex + points.length - 1) % points.length;
		if (["ArrowRight", "ArrowDown"].includes(event.key))
			keyboardIndex = (keyboardIndex + 1) % points.length;
		showBubble(points[keyboardIndex]);
	};
	document.addEventListener("keydown", onKey);
	document.addEventListener("pointerdown", outside);
	window.addEventListener("resize", positionBubble);
	window.addEventListener("scroll", positionBubble, true);
	plot.addEventListener("keydown", plotKey);
	plot.setAttribute(
		"aria-label",
		"월별 사용 확인 기사 추이. 점 클릭 또는 방향키와 Enter로 기사 정보를 확인합니다.",
	);
	const resize = new ResizeObserver(() => {
		if (!disposed && plot._fullLayout)
			window.Plotly.Plots.resize(plot).then(() => {
				if (!disposed) positionBubble();
			});
	});
	resize.observe(plot);
	window.Plotly.newPlot(plot, data.figure.data, data.figure.layout, {
		displayModeBar: false,
		responsive: true,
	}).then(() => {
		if (disposed) return;
		plot.on("plotly_click", (event) => {
			if (event.points?.length) showBubble(event.points[0]);
		});
	});
	if (data.drawer) showDrawer(data.drawer);
	const cleanup = () => {
		if (disposed) return;
		disposed = true;
		resize.disconnect();
		document.removeEventListener("keydown", onKey);
		document.removeEventListener("pointerdown", outside);
		window.removeEventListener("resize", positionBubble);
		window.removeEventListener("scroll", positionBubble, true);
		plot.removeEventListener("keydown", plotKey);
		overlay.remove();
		document.body.style.overflow = oldOverflow;
		window.Plotly.purge(plot);
		if (registry.get(key) === cleanup) registry.delete(key);
	};
	registry.set(key, cleanup);
	return cleanup;
}
