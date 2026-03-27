# UV Index Calculator

Clear-sky UV index calculator based on solar physics (Madronich 1993 / WMO 2002 erythemal formulation). Available as a Python CLI and an interactive SvelteKit web app.

**Live demo:** https://uv.rkan.org

---

## Features

- Real-time UV index calculation from solar zenith angle, ozone column, altitude, and Earth-Sun distance
- City search via Nominatim (OpenStreetMap)
- Elevation and timezone auto-detected via Open-Meteo
- Interactive D3.js chart with sunrise/sunset markers and hover tooltips
- Hourly breakdown table
- Works for any date and location worldwide
- Handles polar day/night edge cases

## How it works

The UV index is calculated using:

```
UV = F₀ × d × cos(θ)^α × (O₃ / O₃_ref)^(-RAF) × (1 + β × alt)
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| F₀ | 12.5 | Calibration constant |
| d | variable | Earth-Sun distance factor |
| θ | variable | Solar zenith angle |
| α | 1.3 | Erythemal angular dependence |
| O₃_ref | 300 DU | Reference ozone column |
| RAF | 1.2 | Radiation Amplification Factor |
| β | 0.06 | Altitude factor (+6% per km) |

Ozone climatology uses TOMS/OMI monthly mean values interpolated by latitude band.

> **Note:** This is a clear-sky model — cloud cover is not factored in.

---

## Web App

Built with SvelteKit 2 + Svelte 5, D3.js, TypeScript. Deployed on Vercel.

### Run locally

```bash
cd uv-index-web
npm install
npm run dev
```

### Build & deploy

```bash
npm run build
```

The app uses the Vercel adapter. Push to your linked Vercel project to deploy.

---

## Python CLI

Interactive terminal tool with Matplotlib visualization.

### Setup

```bash
bash setup.sh
```

### Run

```bash
bash run.sh
```

You'll be prompted for a city name and date, then see the UV curve plotted.

**Dependencies:** `matplotlib`, `numpy`, `geopy`, `timezonefinder`

---

## UV Index Scale

| Index | Level | Color |
|-------|-------|-------|
| 0–2 | Low | Green |
| 3–5 | Moderate | Yellow |
| 6–7 | High | Orange |
| 8–10 | Very High | Red |
| 11+ | Extreme | Purple |

---

## External APIs

- **Nominatim** (OpenStreetMap) — city geocoding
- **Open-Meteo** — elevation and timezone lookup

No API keys required.

---

## Project Structure

```
uv-index/
├── uv_index.py          # Python CLI
├── setup.sh             # Python env setup
├── run.sh               # Run the CLI
└── uv-index-web/        # SvelteKit web app
    └── src/
        ├── lib/
        │   ├── uv.ts        # UV calculation engine
        │   ├── ozone.ts     # Ozone climatology data
        │   └── api.ts       # Nominatim & Open-Meteo calls
        └── routes/
            └── +page.svelte # Main app page
```

---

## References

- Madronich, S. (1993). *UV radiation in the natural and perturbed atmosphere.*
- WMO (2002). *Global Solar UV Index: A Practical Guide.*
