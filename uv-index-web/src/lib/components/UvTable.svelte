<script lang="ts">
	import { uvColor, uvLabel, formatHour, type UvCurveResult } from '$lib/uv';

	interface Props {
		data: UvCurveResult;
	}

	let { data }: Props = $props();
	let expanded = $state(false);

	interface HourlyRow {
		hour: number;
		uv: number;
		label: string;
		color: string;
	}

	let rows = $derived.by(() => {
		const result: HourlyRow[] = [];
		for (let h = 0; h < 24; h++) {
			const idx = h * 60;
			const uv = data.uvValues[idx];
			result.push({
				hour: h,
				uv,
				label: uvLabel(uv),
				color: uvColor(uv)
			});
		}
		return result;
	});

	let visibleRows = $derived(expanded ? rows : rows.filter((r) => r.uv > 0.1));
</script>

<div class="table-card">
	<div class="table-header">
		<h3>Valeurs horaires</h3>
		<button class="toggle-btn" onclick={() => (expanded = !expanded)}>
			{expanded ? 'Heures actives' : 'Toutes les heures'}
		</button>
	</div>
	<div class="table-wrapper">
		<table>
			<thead>
				<tr>
					<th>Heure</th>
					<th>Indice UV</th>
					<th>Niveau</th>
					<th class="bar-col"></th>
				</tr>
			</thead>
			<tbody>
				{#each visibleRows as row}
					<tr class:peak={Math.abs(row.hour - data.peakHour) < 0.5 && data.uvMax > 0}>
						<td class="hour">{row.hour}h00</td>
						<td class="uv-val">{row.uv.toFixed(1)}</td>
						<td>
							<span class="level-badge" style="background: {row.color}20; color: {row.color}">
								{row.uv >= 0.1 ? row.label : '—'}
							</span>
						</td>
						<td class="bar-col">
							{#if row.uv >= 0.1}
								<div class="bar-track">
									<div
										class="bar-fill"
										style="width: {Math.min(100, (row.uv / Math.max(data.uvMax, 1)) * 100)}%; background: {row.color}"
									></div>
								</div>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<style>
	.table-card {
		background: white;
		border-radius: 12px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
		overflow: hidden;
	}

	.table-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px 12px;
	}

	h3 {
		font-size: 15px;
		font-weight: 600;
		color: #333;
		margin: 0;
	}

	.toggle-btn {
		font-size: 12px;
		padding: 5px 12px;
		border: 1px solid #ddd;
		border-radius: 6px;
		background: #fafafa;
		color: #666;
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s;
	}

	.toggle-btn:hover {
		border-color: #6b49c8;
		color: #6b49c8;
		background: #f8f6ff;
	}

	.table-wrapper {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 14px;
	}

	thead {
		border-top: 1px solid #eee;
	}

	th {
		text-align: left;
		padding: 8px 16px;
		font-size: 11px;
		font-weight: 600;
		color: #999;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		border-bottom: 1px solid #eee;
	}

	td {
		padding: 7px 16px;
		border-bottom: 1px solid #f5f5f5;
	}

	tr:last-child td {
		border-bottom: none;
	}

	tr.peak {
		background: #fffbeb;
	}

	tr.peak td {
		border-bottom-color: #fef3c7;
	}

	.hour {
		font-weight: 500;
		color: #555;
		font-variant-numeric: tabular-nums;
	}

	.uv-val {
		font-weight: 600;
		color: #333;
		font-variant-numeric: tabular-nums;
	}

	.level-badge {
		display: inline-block;
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
	}

	.bar-col {
		width: 30%;
		min-width: 80px;
	}

	.bar-track {
		height: 6px;
		background: #f0f0f0;
		border-radius: 3px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}

	@media (max-width: 520px) {
		.table-card {
			border-radius: 0;
			box-shadow: none;
			border-bottom: 1px solid #f0f0f0;
		}

		.bar-col {
			display: none;
		}

		th, td {
			padding: 7px 12px;
		}
	}
</style>
