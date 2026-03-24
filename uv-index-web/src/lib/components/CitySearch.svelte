<script lang="ts">
	import { searchCities, reverseGeocode, countryFlag, type CityResult } from '$lib/api';

	interface Props {
		onselect: (city: CityResult) => void;
		initialQuery?: string;
	}

	let { onselect, initialQuery = '' }: Props = $props();

	let query = $state('');
	let suggestions = $state<CityResult[]>([]);

	$effect(() => {
		if (initialQuery && !query) {
			query = initialQuery;
		}
	});
	let showDropdown = $state(false);
	let loading = $state(false);
	let geolocating = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | undefined;
	let inputEl: HTMLInputElement | undefined = $state();

	function handleInput() {
		const q = query.trim();
		if (debounceTimer) clearTimeout(debounceTimer);

		if (q.length < 2) {
			suggestions = [];
			showDropdown = false;
			return;
		}

		loading = true;
		debounceTimer = setTimeout(async () => {
			suggestions = await searchCities(q);
			showDropdown = suggestions.length > 0;
			loading = false;
		}, 500);
	}

	function selectCity(city: CityResult) {
		query = city.name;
		showDropdown = false;
		suggestions = [];
		onselect(city);
	}

	async function geolocate() {
		if (!navigator.geolocation) return;
		geolocating = true;

		navigator.geolocation.getCurrentPosition(
			async (pos) => {
				const city = await reverseGeocode(pos.coords.latitude, pos.coords.longitude);
				if (city) {
					query = city.name;
					onselect(city);
				}
				geolocating = false;
			},
			() => {
				geolocating = false;
			},
			{ timeout: 10000 }
		);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			showDropdown = false;
		}
	}

	function handleBlur() {
		setTimeout(() => {
			showDropdown = false;
		}, 200);
	}
</script>

<div class="city-search">
	<div class="input-row">
		<div class="input-wrapper">
			<svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
			</svg>
			<input
				bind:this={inputEl}
				bind:value={query}
				oninput={handleInput}
				onkeydown={handleKeydown}
				onblur={handleBlur}
				onfocus={() => { if (suggestions.length > 0) showDropdown = true; }}
				type="text"
				placeholder="Rechercher une ville..."
				autocomplete="off"
			/>
			{#if loading}
				<span class="spinner"></span>
			{/if}
		</div>
		<button class="geo-btn" onclick={geolocate} disabled={geolocating} title="Ma position">
			{#if geolocating}
				<span class="spinner"></span>
			{:else}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="3" />
					<path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
				</svg>
			{/if}
		</button>
	</div>

	{#if showDropdown}
		<ul class="dropdown">
			{#each suggestions as city}
				<li>
					<button onclick={() => selectCity(city)}>
						<span class="flag">{countryFlag(city.countryCode)}</span>
						<span class="city-info">
							<strong>{city.name}</strong>
							<small>{city.displayName}</small>
						</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.city-search {
		position: relative;
	}

	.input-row {
		display: flex;
		gap: 8px;
	}

	.input-wrapper {
		flex: 1;
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-icon {
		position: absolute;
		left: 12px;
		width: 18px;
		height: 18px;
		color: #999;
		pointer-events: none;
	}

	input {
		width: 100%;
		padding: 12px 12px 12px 40px;
		border: 1.5px solid #ddd;
		border-radius: 10px;
		font-size: 16px;
		background: white;
		transition: border-color 0.2s;
	}

	input:focus {
		outline: none;
		border-color: #6b49c8;
		box-shadow: 0 0 0 3px rgba(107, 73, 200, 0.1);
	}

	.geo-btn {
		width: 48px;
		height: 48px;
		border: 1.5px solid #ddd;
		border-radius: 10px;
		background: white;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: border-color 0.2s, background 0.2s;
		flex-shrink: 0;
	}

	.geo-btn:hover:not(:disabled) {
		border-color: #6b49c8;
		background: #f8f6ff;
	}

	.geo-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.geo-btn svg {
		width: 20px;
		height: 20px;
		color: #555;
	}

	.dropdown {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		margin-top: 4px;
		background: white;
		border: 1px solid #ddd;
		border-radius: 10px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
		list-style: none;
		padding: 4px;
		z-index: 100;
		max-height: 280px;
		overflow-y: auto;
	}

	.dropdown li button {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 12px;
		border: none;
		background: none;
		border-radius: 8px;
		cursor: pointer;
		text-align: left;
		transition: background 0.15s;
	}

	.dropdown li button:hover {
		background: #f5f3ff;
	}

	.flag {
		font-size: 20px;
		flex-shrink: 0;
	}

	.city-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.city-info strong {
		font-size: 14px;
		color: #333;
	}

	.city-info small {
		font-size: 12px;
		color: #888;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.spinner {
		width: 18px;
		height: 18px;
		border: 2px solid #ddd;
		border-top-color: #6b49c8;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.input-wrapper .spinner {
		position: absolute;
		right: 12px;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
