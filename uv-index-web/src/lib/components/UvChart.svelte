<script lang="ts">
	import * as d3 from 'd3';
	import { uvColor, uvLabel, formatHour, type UvCurveResult } from '$lib/uv';

	interface Props {
		data: UvCurveResult;
		timezone: string;
	}

	let { data, timezone }: Props = $props();

	let svgEl: SVGSVGElement | undefined = $state();

	const margin = { top: 20, right: 20, bottom: 45, left: 45 };
	const bands = [
		{ lo: 0, hi: 3, color: '#4eb400', label: 'Faible' },
		{ lo: 3, hi: 6, color: '#f7e400', label: 'Modéré' },
		{ lo: 6, hi: 8, color: '#f85900', label: 'Élevé' },
		{ lo: 8, hi: 11, color: '#d8001d', label: 'Très élevé' },
		{ lo: 11, hi: 20, color: '#6b49c8', label: 'Extrême' }
	];

	$effect(() => {
		if (!svgEl || !data) return;
		drawChart();
	});

	function drawChart() {
		if (!svgEl) return;

		const svg = d3.select(svgEl);
		svg.selectAll('*').remove();

		const rect = svgEl.getBoundingClientRect();
		const isMobile = rect.width < 520;
		const width = rect.width || 700;
		const aspectRatio = isMobile ? 0.72 : 0.55;
		const height = Math.min(420, width * aspectRatio);

		svgEl.setAttribute('viewBox', `0 0 ${width} ${height}`);

		const w = width - margin.left - margin.right;
		const h = height - margin.top - margin.bottom;

		const yMax = Math.max(14, Math.ceil(data.uvMax) + 1);

		// Sur mobile : zoom sur la plage lever/coucher
		let xDomainMin = 0;
		let xDomainMax = 24;
		if (isMobile && data.sunTimes) {
			xDomainMin = Math.max(0, data.sunTimes.sunrise - 0.75);
			xDomainMax = Math.min(24, data.sunTimes.sunset + 0.75);
		}

		const x = d3.scaleLinear().domain([xDomainMin, xDomainMax]).range([0, w]);
		const y = d3.scaleLinear().domain([0, yMax]).range([h, 0]);

		const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

		// Background bands
		for (const band of bands) {
			if (band.lo < yMax) {
				g.append('rect')
					.attr('x', 0)
					.attr('y', y(Math.min(band.hi, yMax)))
					.attr('width', w)
					.attr('height', y(band.lo) - y(Math.min(band.hi, yMax)))
					.attr('fill', band.color)
					.attr('opacity', 0.08);
			}
		}

		// Sunrise / sunset shaded zones + dashed lines
		if (data.sunTimes) {
			const { sunrise, sunset } = data.sunTimes;

			// Night zones (semi-transparent overlay)
			if (sunrise > xDomainMin) {
				g.append('rect')
					.attr('x', 0)
					.attr('y', 0)
					.attr('width', x(sunrise))
					.attr('height', h)
					.attr('fill', '#1a1a2e')
					.attr('opacity', 0.06);
			}

			if (sunset < xDomainMax) {
				g.append('rect')
					.attr('x', x(sunset))
					.attr('y', 0)
					.attr('width', w - x(sunset))
					.attr('height', h)
					.attr('fill', '#1a1a2e')
					.attr('opacity', 0.06);
			}

			// Sunrise line
			if (sunrise >= xDomainMin && sunrise <= xDomainMax) {
				g.append('line')
					.attr('x1', x(sunrise)).attr('x2', x(sunrise))
					.attr('y1', 0).attr('y2', h)
					.attr('stroke', '#f59e0b').attr('stroke-width', 1.5)
					.attr('stroke-dasharray', '6,4').attr('opacity', 0.7);

				g.append('text')
					.attr('x', x(sunrise) + 5).attr('y', 14)
					.attr('fill', '#d97706').attr('font-size', '11px').attr('font-weight', 500)
					.text(`\u2600 ${formatHour(sunrise)}`);
			}

			// Sunset line
			if (sunset >= xDomainMin && sunset <= xDomainMax) {
				g.append('line')
					.attr('x1', x(sunset)).attr('x2', x(sunset))
					.attr('y1', 0).attr('y2', h)
					.attr('stroke', '#f59e0b').attr('stroke-width', 1.5)
					.attr('stroke-dasharray', '6,4').attr('opacity', 0.7);

				g.append('text')
					.attr('x', x(sunset) - 5).attr('y', 14)
					.attr('text-anchor', 'end')
					.attr('fill', '#d97706').attr('font-size', '11px').attr('font-weight', 500)
					.text(`${formatHour(sunset)} \u263D`);
			}
		}

		// Downsample for performance: every 10 minutes
		const step = 10;
		const points: [number, number][] = [];
		for (let i = 0; i < data.localHours.length; i += step) {
			points.push([data.localHours[i], data.uvValues[i]]);
		}

		const mainColor = uvColor(data.uvMax);

		// Area fill
		const area = d3.area<[number, number]>()
			.x((d) => x(d[0]))
			.y0(h)
			.y1((d) => y(d[1]))
			.curve(d3.curveMonotoneX);

		g.append('path')
			.datum(points)
			.attr('d', area)
			.attr('fill', mainColor)
			.attr('opacity', 0.25);

		// Line
		const line = d3.line<[number, number]>()
			.x((d) => x(d[0]))
			.y((d) => y(d[1]))
			.curve(d3.curveMonotoneX);

		g.append('path')
			.datum(points)
			.attr('d', line)
			.attr('fill', 'none')
			.attr('stroke', mainColor)
			.attr('stroke-width', 2.5);

		// X axis
		const tickStep = isMobile ? 1 : 2;
		const tickStart = Math.ceil(xDomainMin);
		const tickEnd = Math.floor(xDomainMax);
		const tickValues = d3.range(tickStart, tickEnd + 1, tickStep);

		g.append('g')
			.attr('transform', `translate(0,${h})`)
			.call(
				d3.axisBottom(x)
					.tickValues(tickValues)
					.tickFormat((d) => `${d}h`)
			)
			.call((sel) => sel.select('.domain').attr('stroke', '#ccc'))
			.call((sel) => sel.selectAll('.tick line').attr('stroke', '#ccc'))
			.call((sel) => sel.selectAll('.tick text').attr('fill', '#666').attr('font-size', '12px'));

		// X label
		g.append('text')
			.attr('x', w / 2).attr('y', h + 38)
			.attr('text-anchor', 'middle').attr('fill', '#888').attr('font-size', '12px')
			.text(`Heure locale (${timezone})`);

		// Y axis
		g.append('g')
			.call(d3.axisLeft(y).ticks(yMax > 14 ? 10 : yMax))
			.call((sel) => sel.select('.domain').attr('stroke', '#ccc'))
			.call((sel) => sel.selectAll('.tick line').attr('stroke', '#ccc'))
			.call((sel) => sel.selectAll('.tick text').attr('fill', '#666').attr('font-size', '12px'));

		// Y label
		g.append('text')
			.attr('transform', 'rotate(-90)')
			.attr('x', -h / 2).attr('y', -35)
			.attr('text-anchor', 'middle').attr('fill', '#888').attr('font-size', '12px')
			.text('Indice UV');

		// Grid lines
		g.append('g')
			.attr('class', 'grid')
			.selectAll('line')
			.data(d3.range(0, yMax + 1))
			.join('line')
			.attr('x1', 0).attr('x2', w)
			.attr('y1', (d) => y(d)).attr('y2', (d) => y(d))
			.attr('stroke', '#eee').attr('stroke-dasharray', '2,3');

		// Peak annotation
		if (data.uvMax > 0 && data.peakHour >= xDomainMin && data.peakHour <= xDomainMax) {
			const px = x(data.peakHour);
			const py = y(data.uvMax);

			g.append('circle')
				.attr('cx', px).attr('cy', py).attr('r', 4)
				.attr('fill', mainColor).attr('stroke', 'white').attr('stroke-width', 2);

			const labelX = data.peakHour > (xDomainMin + xDomainMax) / 2 + 2 ? px - 10 : px + 10;
			const anchor = labelX < px ? 'end' : 'start';

			const label = g.append('g').attr('transform', `translate(${labelX},${py - 12})`);

			label.append('rect')
				.attr('x', anchor === 'end' ? -130 : -4).attr('y', -16)
				.attr('width', 134).attr('height', 22).attr('rx', 4)
				.attr('fill', 'white').attr('stroke', '#ddd').attr('stroke-width', 1);

			label.append('text')
				.attr('x', anchor === 'end' ? -63 : 63).attr('y', 0)
				.attr('text-anchor', 'middle').attr('fill', '#333')
				.attr('font-size', '12px').attr('font-weight', 600)
				.text(`UV max ${data.uvMax.toFixed(1)} \u00e0 ${formatHour(data.peakHour)}`);
		}

		// ---- Interactive tooltip ----
		const hoverLine = g.append('line')
			.attr('y1', 0).attr('y2', h)
			.attr('stroke', '#666').attr('stroke-width', 1)
			.attr('stroke-dasharray', '3,3').attr('opacity', 0);

		const hoverDot = g.append('circle')
			.attr('r', 5).attr('fill', mainColor)
			.attr('stroke', 'white').attr('stroke-width', 2).attr('opacity', 0);

		const tooltipG = g.append('g').attr('opacity', 0);
		const tooltipRect = tooltipG.append('rect')
			.attr('rx', 6).attr('fill', 'white').attr('stroke', '#ddd').attr('stroke-width', 1)
			.attr('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))');

		const tooltipTime = tooltipG.append('text')
			.attr('font-size', '12px').attr('font-weight', 600).attr('fill', '#333');
		const tooltipUv = tooltipG.append('text')
			.attr('font-size', '12px').attr('fill', '#555');
		const tooltipLevel = tooltipG.append('text')
			.attr('font-size', '11px').attr('font-weight', 500);
		const tooltipElev = tooltipG.append('text')
			.attr('font-size', '11px').attr('fill', '#888');

		function updateTooltip(mx: number) {
			const hour = x.invert(mx);
			if (hour < xDomainMin || hour > xDomainMax) return;

			const minuteIdx = Math.round(hour * 60);
			const clampedIdx = Math.max(0, Math.min(data.uvValues.length - 1, minuteIdx));
			const uvVal = data.uvValues[clampedIdx];
			const localH = data.localHours[clampedIdx];
			const elev = data.solarElevations[clampedIdx];

			const cx = x(localH);
			const cy = y(uvVal);

			hoverLine.attr('x1', cx).attr('x2', cx).attr('opacity', 0.5);
			hoverDot.attr('cx', cx).attr('cy', cy).attr('fill', uvColor(uvVal)).attr('opacity', 1);

			tooltipTime.text(formatHour(localH));
			tooltipUv.text(`UV : ${uvVal.toFixed(1)}`);
			tooltipLevel.text(uvLabel(uvVal)).attr('fill', uvColor(uvVal));
			tooltipElev.text(elev > 0.5 ? `Soleil : ${elev.toFixed(0)}°` : 'Sous l\'horizon');

			const tooltipW = 110;
			const tooltipH = 68;
			let tx = cx + 12;
			if (tx + tooltipW > w) tx = cx - tooltipW - 12;
			let ty = cy - tooltipH / 2;
			if (ty < 0) ty = 0;
			if (ty + tooltipH > h) ty = h - tooltipH;

			tooltipG.attr('transform', `translate(${tx},${ty})`).attr('opacity', 1);
			tooltipRect.attr('width', tooltipW).attr('height', tooltipH);
			tooltipTime.attr('x', 10).attr('y', 16);
			tooltipUv.attr('x', 10).attr('y', 32);
			tooltipLevel.attr('x', 10).attr('y', 47);
			tooltipElev.attr('x', 10).attr('y', 61);
		}

		function hideTooltip() {
			hoverLine.attr('opacity', 0);
			hoverDot.attr('opacity', 0);
			tooltipG.attr('opacity', 0);
		}

		// Invisible overlay for mouse + touch events
		const overlay = g.append('rect')
			.attr('width', w).attr('height', h)
			.attr('fill', 'none').attr('pointer-events', 'all');

		const overlayNode = overlay.node()!;

		overlay
			.on('mousemove', (event: MouseEvent) => {
				// d3.pointer uses event.currentTarget (the rect) → coords in g-space
				const [mx] = d3.pointer(event);
				updateTooltip(mx);
			})
			.on('mouseleave', hideTooltip)
			.on('touchstart', (event: TouchEvent) => {
				event.preventDefault();
				const touch = event.touches[0] ?? event.changedTouches[0];
				if (!touch) return;
				const [mx] = d3.pointer(touch as unknown as MouseEvent, overlayNode);
				updateTooltip(mx);
			}, { passive: false })
			.on('touchmove', (event: TouchEvent) => {
				event.preventDefault();
				const touch = event.touches[0] ?? event.changedTouches[0];
				if (!touch) return;
				const [mx] = d3.pointer(touch as unknown as MouseEvent, overlayNode);
				updateTooltip(mx);
			}, { passive: false })
			.on('touchend', hideTooltip);
	}
</script>

<div class="chart-container">
	<svg bind:this={svgEl} preserveAspectRatio="xMidYMid meet"></svg>
</div>

<style>
	.chart-container {
		width: 100%;
		background: white;
		border-radius: 12px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
		padding: 16px;
		box-sizing: border-box;
	}

	svg {
		width: 100%;
		height: auto;
		display: block;
		min-height: 250px;
		touch-action: none;
	}

	@media (max-width: 520px) {
		.chart-container {
			border-radius: 0;
			box-shadow: none;
			border-bottom: 1px solid #f0f0f0;
			padding: 12px 8px;
		}
	}
</style>
