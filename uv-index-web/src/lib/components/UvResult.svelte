<script lang="ts">
	import { uvColor, uvLabel, formatHour, type UvCurveResult } from '$lib/uv';

	interface Props {
		data: UvCurveResult;
		altitude: number;
		timezone: string;
	}

	let { data, altitude, timezone }: Props = $props();

	let color = $derived(uvColor(data.uvMax));
	let label = $derived(uvLabel(data.uvMax));
</script>

<div class="uv-result" style="--accent: {color}">
	<div class="uv-badge-wrap">
		<div class="uv-badge">
			<span class="uv-value">{data.uvMax.toFixed(1)}</span>
			<span class="uv-label">{label}</span>
		</div>
		<span class="clear-sky-tag">ciel clair</span>
	</div>
	<div class="uv-details">
		<div class="detail">
			<span class="detail-label">Pic à</span>
			<span class="detail-value">{formatHour(data.peakHour)}</span>
		</div>
		<div class="detail">
			<span class="detail-label">Ozone</span>
			<span class="detail-value">{data.ozoneDU.toFixed(0)} DU</span>
		</div>
		<div class="detail">
			<span class="detail-label">Altitude</span>
			<span class="detail-value">{altitude.toFixed(0)} m</span>
		</div>
		<div class="detail">
			<span class="detail-label">Fuseau</span>
			<span class="detail-value">{timezone}</span>
		</div>
		{#if data.sunTimes}
			<div class="detail">
				<span class="detail-label">Lever</span>
				<span class="detail-value">{formatHour(data.sunTimes.sunrise)}</span>
			</div>
			<div class="detail">
				<span class="detail-label">Coucher</span>
				<span class="detail-value">{formatHour(data.sunTimes.sunset)}</span>
			</div>
		{/if}
		{#if data.peakElevation > 0}
			<div class="detail">
				<span class="detail-label">Élévation au pic</span>
				<span class="detail-value">{data.peakElevation.toFixed(0)}°</span>
			</div>
		{/if}
	</div>
</div>

<style>
	.uv-result {
		background: white;
		border-radius: 12px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
		padding: 24px;
		display: flex;
		align-items: center;
		gap: 24px;
	}

	.uv-badge-wrap {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}

	.uv-badge {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 100px;
		height: 100px;
		border-radius: 50%;
		background: var(--accent);
		color: white;
	}

	.clear-sky-tag {
		font-size: 10px;
		font-weight: 500;
		color: #999;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		background: #f5f5f5;
		padding: 2px 8px;
		border-radius: 4px;
	}

	.uv-value {
		font-size: 32px;
		font-weight: 700;
		line-height: 1;
	}

	.uv-label {
		font-size: 12px;
		font-weight: 500;
		margin-top: 4px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.uv-details {
		flex: 1;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}

	.detail {
		display: flex;
		flex-direction: column;
	}

	.detail-label {
		font-size: 12px;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.detail-value {
		font-size: 16px;
		font-weight: 600;
		color: #333;
		margin-top: 2px;
	}

	@media (max-width: 520px) {
		.uv-result {
			flex-direction: column;
			text-align: center;
			border-radius: 0;
			box-shadow: none;
			border-bottom: 1px solid #f0f0f0;
		}

		.uv-details {
			width: 100%;
		}
	}
</style>
