/**
 * Moteur de calcul UV — porté du Python uv_index.py
 * Modèle erythemal Madronich (1993) / WMO (2002)
 */

import { getOzone } from './ozone';

const DEG2RAD = Math.PI / 180;

export function solarDeclination(dayOfYear: number): number {
	return 23.45 * DEG2RAD * Math.sin(DEG2RAD * (360 / 365) * (dayOfYear - 81));
}

export function equationOfTime(dayOfYear: number): number {
	const b = DEG2RAD * (360 / 365) * (dayOfYear - 81);
	return 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
}

export function earthSunDistanceFactor(dayOfYear: number): number {
	return 1 + 0.033 * Math.cos(DEG2RAD * (360 * dayOfYear) / 365);
}

export function solarZenithAngle(
	latitudeRad: number,
	declination: number,
	hourAngle: number
): number {
	let cosSza =
		Math.sin(latitudeRad) * Math.sin(declination) +
		Math.cos(latitudeRad) * Math.cos(declination) * Math.cos(hourAngle);
	cosSza = Math.max(-1, Math.min(1, cosSza));
	return Math.acos(cosSza);
}

export function clearSkyUvIndex(
	sza: number,
	distanceFactor: number,
	ozoneDU: number,
	altitudeKm: number
): number {
	const cosSza = Math.cos(sza);
	if (cosSza <= 0) return 0;

	const RAF = 1.2;
	const ozoneFactor = Math.pow(ozoneDU / 300, -RAF);
	const altitudeFactor = 1 + 0.06 * altitudeKm;

	return 12.5 * Math.pow(cosSza, 1.3) * distanceFactor * ozoneFactor * altitudeFactor;
}

function localHourToSolarHour(
	localHour: number,
	longitude: number,
	dayOfYear: number,
	utcOffsetHours: number
): number {
	const eot = equationOfTime(dayOfYear);
	return localHour + eot / 60 + longitude / 15 - utcOffsetHours;
}

export interface SunTimes {
	sunrise: number; // local hour (decimal)
	sunset: number;
}

/**
 * Calcule les heures de lever et coucher du soleil (heure locale décimale).
 * Retourne null si le soleil ne se lève/couche pas (nuit polaire / jour polaire).
 */
export function computeSunTimes(
	latitude: number,
	longitude: number,
	dayOfYear: number,
	utcOffsetHours: number
): SunTimes | null {
	const latRad = latitude * DEG2RAD;
	const decl = solarDeclination(dayOfYear);
	const eot = equationOfTime(dayOfYear);

	// cos(hour angle) at sunrise/sunset = -tan(lat)*tan(decl)
	const cosHa = -Math.tan(latRad) * Math.tan(decl);
	if (cosHa < -1 || cosHa > 1) return null; // midnight sun or polar night

	const ha = Math.acos(cosHa); // in radians
	const haDeg = ha / DEG2RAD; // in degrees

	// Solar noon in local hours
	const solarNoonLocal = 12 - eot / 60 - longitude / 15 + utcOffsetHours;

	const sunrise = solarNoonLocal - haDeg / 15;
	const sunset = solarNoonLocal + haDeg / 15;

	return { sunrise, sunset };
}

export interface UvCurveResult {
	localHours: number[];
	uvValues: number[];
	solarElevations: number[]; // degrés au-dessus de l'horizon (0 = horizon, 90 = zénith)
	uvMax: number;
	peakHour: number;
	peakElevation: number; // élévation solaire au moment du pic UV
	ozoneDU: number;
	sunTimes: SunTimes | null;
}

export function computeUvCurve(
	latitude: number,
	longitude: number,
	date: Date,
	utcOffsetHours: number,
	ozoneDU: number,
	altitudeKm: number
): UvCurveResult {
	const start = new Date(date.getFullYear(), 0, 1);
	const dayOfYear = Math.floor((date.getTime() - start.getTime()) / 86400000) + 1;

	const latRad = latitude * DEG2RAD;
	const decl = solarDeclination(dayOfYear);
	const distFactor = earthSunDistanceFactor(dayOfYear);

	const steps = 24 * 60; // one per minute
	const localHours: number[] = new Array(steps);
	const uvValues: number[] = new Array(steps);
	const solarElevations: number[] = new Array(steps);

	let uvMax = 0;
	let peakHour = 12;
	let peakElevation = 0;

	for (let i = 0; i < steps; i++) {
		const lh = i / 60;
		localHours[i] = lh;
		const solarH = localHourToSolarHour(lh, longitude, dayOfYear, utcOffsetHours);
		const hourAngle = DEG2RAD * 15 * (solarH - 12);
		const sza = solarZenithAngle(latRad, decl, hourAngle);
		const elevDeg = Math.max(0, 90 - sza / DEG2RAD);
		solarElevations[i] = elevDeg;
		const uv = clearSkyUvIndex(sza, distFactor, ozoneDU, altitudeKm);
		uvValues[i] = uv;
		if (uv > uvMax) {
			uvMax = uv;
			peakHour = lh;
			peakElevation = elevDeg;
		}
	}

	const sunTimes = computeSunTimes(latitude, longitude, dayOfYear, utcOffsetHours);

	return { localHours, uvValues, solarElevations, uvMax, peakHour, peakElevation, ozoneDU, sunTimes };
}

export function computeUvForLocation(
	latitude: number,
	longitude: number,
	date: Date,
	utcOffsetHours: number,
	altitudeM: number
): UvCurveResult {
	const month = date.getMonth() + 1;
	const ozoneDU = getOzone(latitude, month);
	const altitudeKm = altitudeM / 1000;
	return computeUvCurve(latitude, longitude, date, utcOffsetHours, ozoneDU, altitudeKm);
}

export function uvColor(uv: number): string {
	if (uv < 3) return '#4eb400';
	if (uv < 6) return '#f7e400';
	if (uv < 8) return '#f85900';
	if (uv < 11) return '#d8001d';
	return '#6b49c8';
}

export function uvLabel(uv: number): string {
	if (uv < 3) return 'Faible';
	if (uv < 6) return 'Modéré';
	if (uv < 8) return 'Élevé';
	if (uv < 11) return 'Très élevé';
	return 'Extrême';
}

export function formatHour(h: number): string {
	const hours = Math.floor(h);
	const mins = Math.round((h % 1) * 60);
	return `${hours}h${mins.toString().padStart(2, '0')}`;
}
