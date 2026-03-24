/**
 * Climatologie d'ozone (Dobson Units) — moyennes mensuelles par bande de latitude
 * Source : données TOMS/OMI simplifiées
 * Lignes  : latitudes de -90 à +90 par pas de 15°
 * Colonnes : mois de janvier (0) à décembre (11)
 */

const OZONE_LATS = [-90, -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75, 90];

const OZONE_MONTHLY: number[][] = [
	//  Jan  Fev  Mar  Avr  Mai  Jun  Jul  Aou  Sep  Oct  Nov  Dec
	[310, 295, 275, 260, 250, 245, 240, 235, 200, 180, 230, 290], // -90
	[315, 300, 285, 270, 260, 255, 250, 245, 210, 195, 250, 300], // -75
	[320, 310, 300, 290, 280, 275, 270, 265, 250, 260, 290, 310], // -60
	[295, 290, 285, 280, 275, 270, 265, 265, 265, 270, 280, 290], // -45
	[270, 270, 275, 275, 275, 270, 268, 265, 262, 260, 262, 268], // -30
	[260, 260, 262, 262, 260, 258, 258, 255, 255, 255, 257, 258], // -15
	[255, 258, 260, 260, 258, 255, 255, 255, 255, 255, 255, 255], //   0
	[258, 260, 265, 268, 268, 265, 262, 260, 258, 256, 255, 256], //  15
	[275, 280, 290, 295, 295, 290, 285, 280, 275, 270, 268, 270], //  30
	[310, 320, 335, 345, 340, 330, 315, 305, 295, 290, 295, 300], //  45
	[340, 360, 385, 400, 390, 370, 345, 330, 310, 305, 315, 330], //  60
	[350, 375, 410, 430, 415, 385, 355, 340, 315, 310, 325, 340], //  75
	[350, 380, 420, 440, 420, 390, 360, 345, 320, 315, 330, 345]  //  90
];

/**
 * Interpolation linéaire de la colonne d'ozone (DU) pour une latitude et un mois donnés.
 * @param latitude - latitude en degrés (-90 à 90)
 * @param month - mois (1–12)
 */
export function getOzone(latitude: number, month: number): number {
	const monthIdx = month - 1;
	const column = OZONE_MONTHLY.map((row) => row[monthIdx]);
	return linearInterp(OZONE_LATS, column, latitude);
}

function linearInterp(xs: number[], ys: number[], x: number): number {
	if (x <= xs[0]) return ys[0];
	if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
	for (let i = 0; i < xs.length - 1; i++) {
		if (x >= xs[i] && x <= xs[i + 1]) {
			const t = (x - xs[i]) / (xs[i + 1] - xs[i]);
			return ys[i] + t * (ys[i + 1] - ys[i]);
		}
	}
	return ys[ys.length - 1];
}
