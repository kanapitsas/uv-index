<script lang="ts">
	import CitySearch from '$lib/components/CitySearch.svelte';
	import DatePicker from '$lib/components/DatePicker.svelte';
	import UvChart from '$lib/components/UvChart.svelte';
	import UvResult from '$lib/components/UvResult.svelte';
	import UvTable from '$lib/components/UvTable.svelte';
	import { onMount } from 'svelte';
	import { getElevationAndTimezone, type CityResult } from '$lib/api';
	import { computeUvForLocation, uvColor, uvLabel, formatHour, type UvCurveResult } from '$lib/uv';

	const STORAGE_KEY = 'uv-index-last-city';

	let selectedCity = $state<CityResult | null>(null);
	let selectedDate = $state(new Date().toISOString().split('T')[0]);
	let uvData = $state<UvCurveResult | null>(null);
	let altitude = $state(0);
	let timezone = $state('');
	let utcOffsetHours = $state(0);
	let loading = $state(false);
	let cityName = $state('');
	let initialQuery = $state('');

	let isToday = $derived(selectedDate === new Date().toISOString().split('T')[0]);

	let currentUvInfo = $derived.by(() => {
		if (!uvData || !isToday) return null;
		const nowUtcH = (Date.now() / 3600000) % 24;
		const nowLocalH = ((nowUtcH + utcOffsetHours) % 24 + 24) % 24;
		const idx = Math.max(0, Math.min(uvData.uvValues.length - 1, Math.round(nowLocalH * 60)));
		return { uv: uvData.uvValues[idx], hour: nowLocalH };
	});

	onMount(() => {
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			if (saved) {
				const city: CityResult = JSON.parse(saved);
				selectedCity = city;
				cityName = city.name;
				initialQuery = city.name;
				compute();
			}
		} catch {}
	});

	function saveCity(city: CityResult) {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(city));
		} catch {}
	}

	async function onCitySelect(city: CityResult) {
		selectedCity = city;
		cityName = city.name;
		saveCity(city);
		await compute();
	}

	function onDateChange(date: string) {
		selectedDate = date;
		if (selectedCity) compute();
	}

	function utcOffsetForDate(tz: string, date: Date): number {
		const tzPart = new Intl.DateTimeFormat('en', {
			timeZone: tz,
			timeZoneName: 'shortOffset'
		}).formatToParts(date).find(p => p.type === 'timeZoneName')?.value ?? 'GMT';

		const match = tzPart.match(/^GMT([+-]\d+(?::\d+)?)?$/);
		if (!match || !match[1]) return 0;

		const [h, m = '0'] = match[1].split(':');
		return (h.startsWith('-') ? -1 : 1) * (Math.abs(parseInt(h)) + parseInt(m) / 60);
	}

	async function compute() {
		if (!selectedCity || !selectedDate) return;
		loading = true;

		try {
			const info = await getElevationAndTimezone(selectedCity.lat, selectedCity.lon);
			altitude = info.elevation;
			timezone = info.timezone;

			// Use UTC noon to determine DST for the selected date, then local noon for UV calc
			utcOffsetHours = utcOffsetForDate(info.timezone, new Date(selectedDate + 'T12:00:00Z'));
			const dateObj = new Date(selectedDate + 'T12:00:00');

			uvData = computeUvForLocation(
				selectedCity.lat,
				selectedCity.lon,
				dateObj,
				utcOffsetHours,
				info.elevation
			);

		} catch (e) {
			console.error('Erreur de calcul:', e);
		} finally {
			loading = false;
		}
	}
</script>

<div class="page">
	<section class="card">
		<span class="section-label">Lieu</span>
		<CitySearch onselect={onCitySelect} {initialQuery} />
	</section>

	<section class="card">
		<span class="section-label">Date</span>
		<DatePicker value={selectedDate} onchange={onDateChange} />
	</section>

	{#if loading}
		<div class="loading">
			<span class="spinner"></span>
			<span>Calcul en cours...</span>
		</div>
	{/if}

	{#if uvData && !loading}
		<div class="results" class:visible={true}>
			{#if cityName}
				<h2 class="results-title">{cityName} — {formatDisplayDate(selectedDate)}</h2>
			{/if}

			{#if currentUvInfo}
				<div class="now-card" style="--now-color: {uvColor(currentUvInfo.uv)}">
					<div class="now-current">
						<span class="now-label">Maintenant ({formatHour(currentUvInfo.hour)})</span>
						<span class="now-value">{currentUvInfo.uv.toFixed(1)}</span>
						<span class="now-level">{uvLabel(currentUvInfo.uv)}</span>
					</div>
					<div class="now-divider"></div>
					<div class="now-max">
						<span class="now-label">Max aujourd'hui</span>
						<span class="now-value now-value--max">{uvData.uvMax.toFixed(1)}</span>
						<span class="now-sub">à {formatHour(uvData.peakHour)}</span>
					</div>
				</div>
			{/if}

			<UvResult data={uvData} {altitude} {timezone} />
			<UvChart data={uvData} {timezone} />
			<UvTable data={uvData} />

			<aside class="info-box">
				<details>
					<summary>Comment lire ces valeurs ?</summary>
					<div class="info-content">
						<p>
							Les valeurs affichées sont des <strong>indices UV par ciel clair</strong> (clear sky),
							c'est-à-dire le maximum théorique en l'absence de nuages.
							En conditions réelles, la couverture nuageuse réduit l'indice UV,
							parfois de plus de 50&nbsp;%.
						</p>
						<h4>Ce que le modèle prend en compte</h4>
						<ul>
							<li>Position du soleil (angle zénithal) selon le lieu, la date et l'heure</li>
							<li>Climatologie d'ozone par latitude et mois (données TOMS/OMI)</li>
							<li>Correction d'altitude (+6&nbsp;% par 1000&nbsp;m)</li>
							<li>Distance Terre-Soleil variable au cours de l'année</li>
						</ul>
						<h4>Ce que le modèle ne prend pas en compte</h4>
						<ul>
							<li>Nébulosité (nuages) — les valeurs affichées sont un maximum</li>
							<li>Réflexion au sol (neige, sable, eau)</li>
							<li>Aérosols et pollution atmosphérique</li>
							<li>Variations d'ozone en temps réel</li>
						</ul>
						<p class="info-ref">
							Modèle basé sur la formulation erythemal de Madronich (1993) / WMO (2002).
						</p>
					</div>
				</details>
			</aside>
		</div>
	{/if}
</div>

<script lang="ts" module>
	function formatDisplayDate(dateStr: string): string {
		const d = new Date(dateStr + 'T12:00:00');
		return d.toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'long',
			year: 'numeric'
		});
	}
</script>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.card {
		background: white;
		border-radius: 12px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
		padding: 20px;
	}

	@media (max-width: 520px) {
		.card,
		.now-card,
		.info-box {
			border-radius: 0;
			box-shadow: none;
			border-bottom: 1px solid #f0f0f0;
		}
	}

	.section-label {
		display: block;
		font-size: 13px;
		font-weight: 600;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 10px;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		padding: 24px;
		color: #888;
		font-size: 14px;
	}

	.spinner {
		width: 20px;
		height: 20px;
		border: 2px solid #ddd;
		border-top-color: #6b49c8;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.results {
		display: flex;
		flex-direction: column;
		gap: 16px;
		animation: fadeIn 0.3s ease-out;
	}

	.results-title {
		font-size: 18px;
		font-weight: 600;
		color: #333;
		margin: 8px 0 0;
	}

	.now-card {
		background: white;
		border-radius: 12px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
		border-left: 4px solid var(--now-color);
		padding: 16px 20px;
		display: flex;
		align-items: center;
		gap: 20px;
	}

	.now-current,
	.now-max {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		flex: 1;
	}

	.now-label {
		font-size: 11px;
		font-weight: 600;
		color: #999;
		text-transform: uppercase;
		letter-spacing: 0.4px;
	}

	.now-value {
		font-size: 36px;
		font-weight: 700;
		color: var(--now-color);
		line-height: 1.1;
	}

	.now-value--max {
		font-size: 28px;
		color: #555;
	}

	.now-level {
		font-size: 12px;
		font-weight: 600;
		color: var(--now-color);
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.now-sub {
		font-size: 12px;
		color: #888;
	}

	.now-divider {
		width: 1px;
		height: 48px;
		background: #eee;
		flex-shrink: 0;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.info-box {
		background: white;
		border-radius: 12px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
		overflow: hidden;
	}

	.info-box summary {
		padding: 16px 20px;
		font-size: 14px;
		font-weight: 500;
		color: #666;
		cursor: pointer;
		list-style: none;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.info-box summary::-webkit-details-marker {
		display: none;
	}

	.info-box summary::before {
		content: '\25B6';
		font-size: 10px;
		color: #aaa;
		transition: transform 0.2s;
	}

	.info-box details[open] summary::before {
		transform: rotate(90deg);
	}

	.info-content {
		padding: 0 20px 20px;
		font-size: 13px;
		line-height: 1.7;
		color: #555;
	}

	.info-content p {
		margin: 0 0 12px;
	}

	.info-content h4 {
		font-size: 13px;
		font-weight: 600;
		color: #444;
		margin: 14px 0 6px;
	}

	.info-content ul {
		margin: 0 0 8px;
		padding-left: 20px;
	}

	.info-content li {
		margin-bottom: 3px;
	}

	.info-ref {
		font-size: 12px;
		color: #999;
		font-style: italic;
		margin-top: 14px;
		margin-bottom: 0;
	}
</style>
