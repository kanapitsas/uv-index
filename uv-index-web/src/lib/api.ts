/**
 * API calls: Nominatim geocoding + Open-Meteo elevation/timezone
 */

export interface CityResult {
	lat: number;
	lon: number;
	name: string;
	displayName: string;
	country: string;
	countryCode: string;
}

export interface LocationInfo {
	elevation: number;
	timezone: string;
	utcOffsetSeconds: number;
}

export async function searchCities(query: string): Promise<CityResult[]> {
	if (query.length < 2) return [];

	const url = `https://nominatim.openstreetmap.org/search?` +
		new URLSearchParams({
			q: query,
			format: 'json',
			limit: '5',
			addressdetails: '1',
			'accept-language': 'fr'
		});

	const res = await fetch(url, {
		headers: { 'User-Agent': 'uv-index-calculator/1.0' }
	});

	if (!res.ok) return [];

	const data = await res.json();
	return data.map((item: any) => ({
		lat: parseFloat(item.lat),
		lon: parseFloat(item.lon),
		name: item.address?.city || item.address?.town || item.address?.village || item.name || item.display_name.split(',')[0],
		displayName: item.display_name,
		country: item.address?.country || '',
		countryCode: (item.address?.country_code || '').toUpperCase()
	}));
}

export async function reverseGeocode(lat: number, lon: number): Promise<CityResult | null> {
	const url = `https://nominatim.openstreetmap.org/reverse?` +
		new URLSearchParams({
			lat: lat.toString(),
			lon: lon.toString(),
			format: 'json',
			addressdetails: '1',
			'accept-language': 'fr'
		});

	const res = await fetch(url, {
		headers: { 'User-Agent': 'uv-index-calculator/1.0' }
	});

	if (!res.ok) return null;

	const item = await res.json();
	return {
		lat,
		lon,
		name: item.address?.city || item.address?.town || item.address?.village || item.name || item.display_name.split(',')[0],
		displayName: item.display_name,
		country: item.address?.country || '',
		countryCode: (item.address?.country_code || '').toUpperCase()
	};
}

export async function getElevationAndTimezone(lat: number, lon: number): Promise<LocationInfo> {
	const url = `https://api.open-meteo.com/v1/forecast?` +
		new URLSearchParams({
			latitude: lat.toFixed(4),
			longitude: lon.toFixed(4),
			daily: 'temperature_2m_max',
			timezone: 'auto',
			forecast_days: '1'
		});

	try {
		const res = await fetch(url);
		if (!res.ok) throw new Error('Open-Meteo error');

		const data = await res.json();
		return {
			elevation: Math.max(0, data.elevation ?? 0),
			timezone: data.timezone ?? 'UTC',
			utcOffsetSeconds: data.utc_offset_seconds ?? 0
		};
	} catch {
		return { elevation: 0, timezone: 'UTC', utcOffsetSeconds: 0 };
	}
}

const FLAG_OFFSET = 0x1F1E6 - 65;

export function countryFlag(countryCode: string): string {
	if (!countryCode || countryCode.length !== 2) return '';
	const cp1 = countryCode.codePointAt(0)! + FLAG_OFFSET;
	const cp2 = countryCode.codePointAt(1)! + FLAG_OFFSET;
	return String.fromCodePoint(cp1, cp2);
}
