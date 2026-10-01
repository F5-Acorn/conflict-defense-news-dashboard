export default function ({ parentElement, data, key }) {
	const registry = (window.__dashboardDonutRenderers ||= new Map());
	registry.get(key)?.();
	const plot = parentElement.querySelector('.judgement-donut');
	const svgNS = 'http://www.w3.org/2000/svg';
	let disposed = false;

	function svg(tag, attributes, parent) {
		const element = document.createElementNS(svgNS, tag);
		for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
		parent.appendChild(element);
		return element;
	}

	function fits(point, fraction, radius, hole, position, box) {
		const middle = Math.atan2(point.pxmid[1], point.pxmid[0]);
		const cos = Math.cos(position.angle), sin = Math.sin(position.angle);
		// 실제 글자 사각형의 모서리와 변 중앙이 모두 현재 조각 안에 있어야 한다.
		for (const x of [-box.width / 2 - 1, 0, box.width / 2 + 1]) {
			for (const y of [-box.height / 2 - 1, 0, box.height / 2 + 1]) {
				const dx = position.x - point.cxFinal + x * cos - y * sin;
				const dy = position.y - point.cyFinal + x * sin + y * cos;
				const distance = Math.hypot(dx, dy);
				const delta = Math.atan2(Math.sin(Math.atan2(dy, dx) - middle), Math.cos(Math.atan2(dy, dx) - middle));
				if (distance < radius * hole + 1 || distance > radius - 1 || Math.abs(delta) > fraction * Math.PI) return false;
			}
		}
		return true;
	}

	function insidePosition(point, fraction, radius, hole, box) {
		const middle = Math.atan2(point.pxmid[1], point.pxmid[0]);
		const offsets = [0, -.25, .25, -.5, .5, -.75, .75];
		for (const tangent of [false, true]) {
			for (const offset of offsets) {
				const angle = middle + offset * fraction * Math.PI;
				let textAngle = tangent ? angle + Math.PI / 2 : 0;
				textAngle = Math.atan2(Math.sin(textAngle), Math.cos(textAngle));
				if (textAngle > Math.PI / 2) textAngle -= Math.PI;
				if (textAngle < -Math.PI / 2) textAngle += Math.PI;
				for (const shift of [0, -2, 2]) {
					const distance = radius * (1 + hole) / 2 + shift;
					const position = {
						x: point.cxFinal + distance * Math.cos(angle),
						y: point.cyFinal + distance * Math.sin(angle),
						angle: textAngle,
					};
					if (fits(point, fraction, radius, hole, position, box)) return position;
				}
			}
		}
		return null;
	}

	function positionText(text, box, x, y, angle = 0) {
		text.setAttribute('transform', `translate(${x},${y}) rotate(${angle * 180 / Math.PI}) translate(${-box.x - box.width / 2},${-box.y - box.height / 2})`);
	}

	function fitLabelWidth(text, box, available) {
		if (box.width <= available) return box;
		text.setAttribute('font-size', 12 * available / box.width);
		return text.getBBox();
	}

	function placeRatios() {
		const trace = data.data[0];
		const total = trace.values.reduce((sum, value) => sum + value, 0);
		for (const slice of plot.querySelectorAll('.pielayer .slice')) {
			const point = slice.__data__;
			if (!point?.pxmid || !total) continue;
			slice.querySelectorAll('text.slicetext, path.textline').forEach(element => element.remove());
			const index = point.i;
			const code = trace.customdata[index];
			const fraction = trace.values[index] / total;
			const radius = data.layout.meta.donut_diameter / 2;
			const text = svg('text', {
				class: 'donut-ratio-label', fill: '#ffffff',
				'font-family': data.layout.font.family, 'font-size': 12,
				'pointer-events': 'none', 'data-status': code,
				'aria-label': `${trace.labels[index]} ${(fraction * 100).toFixed(1)}%`,
			}, slice);
			text.textContent = `${(fraction * 100).toFixed(1)}%`;
			const box = text.getBBox();
			const position = insidePosition(point, fraction, radius, trace.hole, box);
			if (position) {
				text.dataset.placement = 'inside';
				positionText(text, box, position.x, position.y, position.angle);
			} else if (code === 1) {
				// 비사용만 왼쪽에 연결선을 표시한다. 차트별 왼쪽 여백을 공유하지 않는다.
				const edge = point.cxFinal - radius;
				const outsideBox = fitLabelWidth(text, box, edge - 10);
				const x = edge - 8 - outsideBox.width / 2;
				text.dataset.placement = 'outside';
				positionText(text, outsideBox, x, point.cyFinal);
				svg('path', {
					class: 'textline', d: `M${edge},${point.cyFinal} H${edge - 6}`,
					fill: 'none', stroke: data.layout.font.color, 'stroke-width': 1,
					'pointer-events': 'none',
				}, slice);
			} else {
				// 작은 사용·불확실은 차트 오른쪽 빈 공간에 색상 표시와 함께 놓는다.
				const x = point.cxFinal + radius + 4;
				const y = point.cyFinal + (code === 0 ? -22 : 22);
				const fallbackBox = fitLabelWidth(text, box, data.layout.width - x - 10);
				text.dataset.placement = 'fallback';
				positionText(text, fallbackBox, x + 8 + fallbackBox.width / 2, y);
				svg('circle', {cx: x + 2, cy: y, r: 2.5, fill: trace.marker.colors[index], 'pointer-events': 'none'}, slice);
			}
		}
	}

	async function draw() {
		if (disposed) return;
		const context = document.createElement('canvas').getContext('2d');
		const annotations = data.layout.annotations.map(item => {
			const lines = item.text.split(/<br\s*\/?\s*>/i).map(line => line.replace(/<[^>]*>/g, ''));
			context.font = `700 ${item.font.size}px ${data.layout.font.family}`;
			const longest = Math.max(...lines.map(line => context.measureText(line).width));
			const available = data.layout.meta.donut_diameter * data.data[0].hole - 10;
			return {...item, x: .5, y: .5, xanchor: 'center', yanchor: 'middle',
				font: {...item.font, size: Math.min(item.font.size, item.font.size * available / longest)}};
		});
		await window.Plotly.react(plot, data.data, {...data.layout, annotations}, {displayModeBar: false, responsive: false});
		if (!disposed) placeRatios();
	}

	document.fonts.ready.then(draw);
	const cleanup = () => {
		disposed = true;
		window.Plotly.purge(plot);
		if (registry.get(key) === cleanup) registry.delete(key);
	};
	registry.set(key, cleanup);
	return cleanup;
}
