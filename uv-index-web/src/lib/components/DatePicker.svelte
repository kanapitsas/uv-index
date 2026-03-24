<script lang="ts">
	interface Props {
		value: string;
		onchange: (date: string) => void;
	}

	let { value, onchange }: Props = $props();

	function setToday() {
		const today = new Date().toISOString().split('T')[0];
		onchange(today);
	}

	function handleChange(e: Event) {
		const input = e.target as HTMLInputElement;
		onchange(input.value);
	}
</script>

<div class="date-picker">
	<div class="input-row">
		<div class="input-wrapper">
			<svg class="cal-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="3" y="4" width="18" height="18" rx="2" />
				<path d="M16 2v4M8 2v4M3 10h18" />
			</svg>
			<input
				type="date"
				{value}
				onchange={handleChange}
			/>
		</div>
		<button class="today-btn" onclick={setToday}>Aujourd'hui</button>
	</div>
</div>

<style>
	.date-picker {
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

	.cal-icon {
		position: absolute;
		left: 12px;
		width: 18px;
		height: 18px;
		color: #999;
		pointer-events: none;
	}

	input[type='date'] {
		width: 100%;
		padding: 12px 12px 12px 40px;
		border: 1.5px solid #ddd;
		border-radius: 10px;
		font-size: 16px;
		background: white;
		color: #333;
		transition: border-color 0.2s;
	}

	input[type='date']:focus {
		outline: none;
		border-color: #6b49c8;
		box-shadow: 0 0 0 3px rgba(107, 73, 200, 0.1);
	}

	.today-btn {
		padding: 12px 18px;
		border: 1.5px solid #ddd;
		border-radius: 10px;
		background: white;
		font-size: 14px;
		font-weight: 500;
		color: #555;
		cursor: pointer;
		white-space: nowrap;
		transition: border-color 0.2s, background 0.2s;
	}

	.today-btn:hover {
		border-color: #6b49c8;
		background: #f8f6ff;
		color: #6b49c8;
	}
</style>
