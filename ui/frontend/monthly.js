export default function ({ parentElement, data, setTriggerValue, key }) {
	// v2는 같은 인스턴스에 새 데이터를 전달할 때 렌더러를 다시 호출할 수 있다.
	// 기존 이벤트와 body 포털을 먼저 정리해 중복 말풍선·리스너를 방지한다.
	const registry = (window.__dashboardMonthlyRenderers ||= new Map());
	registry.get(key)?.();
	const plot = parentElement.querySelector(".monthly-plot");
	const loading = parentElement.querySelector(".dashboard-loading");
	loading.hidden = false;
	loading.querySelector('.dashboard-spinner').hidden = false;
	loading.querySelector('.dashboard-loading-message').textContent = '추이를 준비하는 중…';
	plot.style.visibility = 'hidden';
	const overlay = document.createElement("div");
	overlay.className = "monthly-overlay-root";
	document.body.appendChild(overlay);
	plot.setAttribute("aria-busy", "false");
	let disposed = false,
		bubble = null;
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
	// 목록만 바뀌면 차트 렌더러는 재실행되지 않으므로 요청 후 입력을 잠그지 않는다.
	function emit(type, values = {}) {
		if (disposed) return;
		setTriggerValue("action", {
			type,
			context: data.context,
			kind: data.kind,
			granularity: data.granularity || "month",
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
	function showBubble(point) {
		if (disposed) return;
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
		bubble = parentElement
			.querySelector(".monthly-bubble-template")
			.content.firstElementChild.cloneNode(true);
		bubble.setAttribute(
			"aria-label",
			`${point.data.name} ${point.x} 기사 정보`,
		);
		bubble.querySelector("h4").textContent = point.data.name;
		bubble.querySelector("strong").textContent =
			`${Number(point.y).toLocaleString()}건`;
		bubble.querySelector("p").textContent =
			`${String(point.x).replaceAll("-", ".")} · ${data.granularity === "day" ? "전일" : "전월"} 대비: ${point.customdata[1]}`;
		bubble.querySelector(".monthly-close").onclick = () => closeBubble(true);
		bubble.querySelector(".monthly-open-articles").onclick = () => {
			emit("open_articles", {
				category_id: point.customdata[0],
				month: point.x,
				page: 1,
			});
			closeBubble(true);
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
	const onKey = (event) => {
		if (event.key === "Escape" && bubble) {
			event.preventDefault();
			closeBubble(true);
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
		`${data.granularity === "day" ? "일별" : "월별"} 사용 확인 기사 추이. 점 클릭 또는 방향키와 Enter로 기사 정보를 확인합니다.`,
	);
	const resize = new ResizeObserver(() => {
		if (
			!disposed &&
			plot.isConnected &&
			plot._fullLayout &&
			plot.clientWidth &&
			plot.clientHeight
		)
			window.Plotly.Plots.resize(plot)
				.then(() => {
					if (!disposed) positionBubble();
				})
				.catch((error) => {
					// 크기 조정 도중 필터 변경으로 제거된 차트는 더 이상 갱신하지 않는다.
					if (
						!disposed &&
						plot.isConnected &&
						plot._fullLayout &&
						plot.clientWidth &&
						plot.clientHeight
					)
						throw error;
				});
	});
	resize.observe(plot);
	Promise.resolve().then(() => {
		if (disposed) return;
		return window.Plotly.newPlot(plot, data.figure.data, data.figure.layout, {
			displayModeBar: false,
			// 부모 크기 변경은 위 ResizeObserver가 처리한다.
			responsive: false,
		});
	}).then(() => {
		if (disposed) return;
		plot.style.visibility = "visible";
		loading.hidden = true;
		plot.on("plotly_click", (event) => {
			if (event.points?.length) showBubble(event.points[0]);
		});
	}).catch(() => {
		if (disposed) return;
		loading.querySelector('.dashboard-spinner').hidden = true;
		loading.querySelector('.dashboard-loading-message').textContent = '추이를 표시할 수 없습니다.';
	});
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
		window.Plotly.purge(plot);
		if (registry.get(key) === cleanup) registry.delete(key);
	};
	registry.set(key, cleanup);
	return cleanup;
}
