/**
 * Moteur de calcul UV — porté du Python uv_index.py
 * Modèle LUT Beer-Lambert (Rayleigh + ozone, masses d'air séparées)
 */

import { getOzone } from './ozone';

const DEG2RAD = Math.PI / 180;

// ---------------------------------------------------------------------------
// Look-up Table UV — Beer-Lambert avec masses d'air séparées
//
// UVI pré-calculé au niveau de la mer (alt=0), facteur d=1.
// Formule : F0 × cos(SZA) × exp(-τ_R × M_R) × exp(-σ_eff × O3 × M_O3)
//   F0    = 23.767  (calibration : UVI(SZA=0°, O3=300 DU) = 12.0)
//   τ_R   = 0.0834  (épaisseur optique Rayleigh effective)
//   σ_eff = 0.002   (section efficace ozone effective /DU)
//   M_R   : Kasten & Young (1989)
//   M_O3  : couche sphérique à H=22 km → RAF dépendant du SZA
//
// RAF effectif ≈ 0.6 à SZA=0°, ≈ 1.2 à SZA=60°, ≈ 2.2 à SZA=75°
// ---------------------------------------------------------------------------

const LUT_SZA = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 73, 76, 79, 82, 85, 88, 90];
const LUT_O3  = [200, 225, 250, 275, 300, 325, 350, 375, 400, 425, 450];
const LUT_UVI = [
//   O3→  200      225      250      275      300      325      350      375      400      425      450
    [14.6572, 13.9423, 13.2624, 12.6156, 12.0003, 11.415,  10.8583, 10.3287,  9.825,   9.3458,  8.89  ],  //  0°
    [14.5747, 13.8612, 13.1827, 12.5374, 11.9237, 11.34,   10.7849, 10.257,   9.7549,  9.2774,  8.8232],  //  5°
    [14.328,  13.6188, 12.9446, 12.3039, 11.6949, 11.116,  10.5658, 10.0428,  9.5457,  9.0732,  8.624 ],  // 10°
    [13.9199, 13.2179, 12.5512, 11.9182, 11.3171, 10.7464, 10.2044,  9.6897,  9.201,   8.737,   8.2963],  // 15°
    [13.3553, 12.6636, 12.0077, 11.3857, 10.796,  10.2368,  9.7066,  9.2038,  8.7271,  8.2751,  7.8465],  // 20°
    [12.6409, 11.9629, 11.3212, 10.714,  10.1393,  9.5955,  9.0809,  8.5938,  8.1329,  7.6967,  7.2838],  // 25°
    [11.7855, 11.1251, 10.5017,  9.9132,  9.3577,  8.8333,  8.3383,  7.871,   7.4299,  7.0136,  6.6206],  // 30°
    [10.8005, 10.162,   9.5613,  8.9961,  8.4642,  7.9639,  7.4931,  7.0501,  6.6333,  6.2412,  5.8722],  // 35°
    [ 9.6999,  9.0884,  8.5155,  7.9787,  7.4757,  7.0045,  6.5629,  6.1492,  5.7616,  5.3984,  5.0581],  // 40°
    [ 8.5009,  7.9225,  7.3834,  6.881,   6.4128,  5.9764,  5.5698,  5.1908,  4.8376,  4.5084,  4.2017],  // 45°
    [ 7.2249,  6.6867,  6.1887,  5.7277,  5.301,   4.9062,  4.5407,  4.2025,  3.8894,  3.5997,  3.3316],  // 50°
    [ 5.899,   5.4099,  4.9612,  4.5498,  4.1725,  3.8265,  3.5092,  3.2182,  2.9513,  2.7066,  2.4821],  // 55°
    [ 4.5583,  4.1287,  3.7396,  3.3872,  3.068,   2.7788,  2.5169,  2.2797,  2.0649,  1.8703,  1.694 ],  // 60°
    [ 3.25,    2.8927,  2.5746,  2.2915,  2.0395,  1.8153,  1.6157,  1.438,   1.2799,  1.1392,  1.0139],  // 65°
    [ 2.0401,  1.769,   1.534,   1.3302,  1.1535,  1.0003,  0.8674,  0.7522,  0.6522,  0.5656,  0.4905],  // 70°
    [ 1.399,   1.1861,  1.0057,  0.8526,  0.7229,  0.6129,  0.5197,  0.4406,  0.3736,  0.3167,  0.2685],  // 73°
    [ 0.8527,  0.7009,  0.5761,  0.4735,  0.3891,  0.3198,  0.2629,  0.2161,  0.1776,  0.146,   0.12  ],  // 76°
    [ 0.4305,  0.3383,  0.2659,  0.2089,  0.1642,  0.129,   0.1014,  0.0797,  0.0626,  0.0492,  0.0387],  // 79°
    [ 0.1571,  0.1153,  0.0846,  0.0621,  0.0456,  0.0334,  0.0245,  0.018,   0.0132,  0.0097,  0.0071],  // 82°
    [ 0.0313,  0.0207,  0.0136,  0.009,   0.0059,  0.0039,  0.0026,  0.0017,  0.0011,  0.0007,  0.0005],  // 85°
    [ 0.0019,  0.0011,  0.0006,  0.0004,  0.0002,  0.0001,  0.0001,  0.0,     0.0,     0.0,     0.0   ],  // 88°
    [ 0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0   ],  // 90°
];

function interpLut(szaDeg: number, o3DU: number): number {
    szaDeg = Math.max(0, Math.min(90, szaDeg));
    o3DU   = Math.max(LUT_O3[0], Math.min(LUT_O3[LUT_O3.length - 1], o3DU));

    let i1 = LUT_SZA.length - 2;
    for (let i = 0; i < LUT_SZA.length - 1; i++) {
        if (LUT_SZA[i + 1] > szaDeg) { i1 = i; break; }
    }
    const i2 = i1 + 1;
    const tSza = LUT_SZA[i2] !== LUT_SZA[i1]
        ? (szaDeg - LUT_SZA[i1]) / (LUT_SZA[i2] - LUT_SZA[i1])
        : 0;

    let j1 = LUT_O3.length - 2;
    for (let j = 0; j < LUT_O3.length - 1; j++) {
        if (LUT_O3[j + 1] > o3DU) { j1 = j; break; }
    }
    const j2 = j1 + 1;
    const tO3 = LUT_O3[j2] !== LUT_O3[j1]
        ? (o3DU - LUT_O3[j1]) / (LUT_O3[j2] - LUT_O3[j1])
        : 0;

    return (
        LUT_UVI[i1][j1] * (1 - tSza) * (1 - tO3) +
        LUT_UVI[i1][j2] * (1 - tSza) *      tO3  +
        LUT_UVI[i2][j1] *      tSza  * (1 - tO3) +
        LUT_UVI[i2][j2] *      tSza  *      tO3
    );
}

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
	const szaDeg = sza / DEG2RAD;
	if (szaDeg >= 90) return 0;
	const uviBase = interpLut(szaDeg, ozoneDU);
	return uviBase * distanceFactor * (1 + 0.06 * altitudeKm);
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
