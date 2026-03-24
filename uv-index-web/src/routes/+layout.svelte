<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();
</script>

<header>
	<div class="header-content">
		<svg class="logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<circle cx="12" cy="12" r="4" />
			<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
		</svg>
		<h1>Indice UV</h1>
	</div>
</header>

<main>
	{@render children()}
</main>

<style>
	header {
		background: white;
		border-bottom: 1px solid #eee;
		padding: 12px 20px;
	}

	.header-content {
		max-width: 700px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.logo {
		width: 26px;
		height: 26px;
		color: #f85900;
	}

	h1 {
		font-size: 18px;
		font-weight: 600;
		color: #333;
		margin: 0;
	}

	main {
		max-width: 700px;
		margin: 0 auto;
		padding: 24px 20px 60px;
	}

	@media (max-width: 520px) {
		main {
			padding: 12px 0 60px;
		}
	}
</style>
