"""
Calculateur d'indice UV maximum (ciel clair) en fonction du lieu et du jour.
Affiche un graphique de l'indice UV au cours de la journée choisie en heure locale.

Modèle LUT Beer-Lambert (Rayleigh + ozone, masses d'air séparées) :
  - Masse d'air Rayleigh  : Kasten & Young (1989)
  - Masse d'air ozone     : géométrie sphérique (couche à 22 km)
  - Climatologie d'ozone  : TOMS/OMI par latitude et mois
  - Correction d'altitude : empirique +6 %/km (WMO)
  - Facteur Terre-Soleil  : ±3.3 % sur l'année
"""

import json
import math
import sys
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder


# ---------------------------------------------------------------------------
# Climatologie d'ozone (Dobson Units) — moyennes mensuelles par bande de latitude
# Source : données TOMS/OMI simplifiées
# Lignes  : latitudes de -90 à +90 par pas de 15°
# Colonnes : mois de janvier (0) à décembre (11)
# ---------------------------------------------------------------------------
OZONE_LATS = np.array([-90, -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75, 90])
OZONE_MONTHLY = np.array([
    # Jan  Fev  Mar  Avr  Mai  Jun  Jul  Aou  Sep  Oct  Nov  Dec
    [310, 295, 275, 260, 250, 245, 240, 235, 200, 180, 230, 290],  # -90 (trou d'ozone austral)
    [315, 300, 285, 270, 260, 255, 250, 245, 210, 195, 250, 300],  # -75
    [320, 310, 300, 290, 280, 275, 270, 265, 250, 260, 290, 310],  # -60
    [295, 290, 285, 280, 275, 270, 265, 265, 265, 270, 280, 290],  # -45
    [270, 270, 275, 275, 275, 270, 268, 265, 262, 260, 262, 268],  # -30
    [260, 260, 262, 262, 260, 258, 258, 255, 255, 255, 257, 258],  # -15
    [255, 258, 260, 260, 258, 255, 255, 255, 255, 255, 255, 255],  #   0
    [258, 260, 265, 268, 268, 265, 262, 260, 258, 256, 255, 256],  #  15
    [275, 280, 290, 295, 295, 290, 285, 280, 275, 270, 268, 270],  #  30
    [310, 320, 335, 345, 340, 330, 315, 305, 295, 290, 295, 300],  #  45
    [340, 360, 385, 400, 390, 370, 345, 330, 310, 305, 315, 330],  #  60
    [350, 375, 410, 430, 415, 385, 355, 340, 315, 310, 325, 340],  #  75
    [350, 380, 420, 440, 420, 390, 360, 345, 320, 315, 330, 345],  #  90
], dtype=float)


def get_ozone(latitude: float, month: int) -> float:
    """
    Interpole la colonne d'ozone (DU) pour une latitude et un mois donnés.
    month : 1-12
    """
    month_idx = month - 1
    return float(np.interp(latitude, OZONE_LATS, OZONE_MONTHLY[:, month_idx]))


# ---------------------------------------------------------------------------
# Géocodage et altitude
# ---------------------------------------------------------------------------

def geocode_city(city_name: str) -> tuple[float, float, str]:
    """Géocode une ville et retourne (latitude, longitude, nom affiché)."""
    geolocator = Nominatim(user_agent="uv-index-calculator")
    location = geolocator.geocode(city_name)
    if location is None:
        print(f"Impossible de trouver la ville « {city_name} ».")
        sys.exit(1)
    return location.latitude, location.longitude, location.address


def get_timezone(latitude: float, longitude: float) -> ZoneInfo:
    """Trouve le fuseau horaire à partir des coordonnées."""
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=latitude, lng=longitude)
    if tz_name is None:
        print("Impossible de déterminer le fuseau horaire. Utilisation UTC.")
        return ZoneInfo("UTC")
    return ZoneInfo(tz_name)


def get_elevation(latitude: float, longitude: float) -> float:
    """Récupère l'altitude (m) via l'API Open-Meteo."""
    url = (
        f"https://api.open-meteo.com/v1/elevation"
        f"?latitude={latitude:.4f}&longitude={longitude:.4f}"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            elev = data["elevation"][0]
            return max(0.0, float(elev))
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Look-up Table UV — Beer-Lambert avec masses d'air séparées
#
# UVI pré-calculé au niveau de la mer (alt=0), facteur d=1.
# Formule : F0 × cos(SZA) × exp(-τ_R × M_R) × exp(-σ_eff × O3 × M_O3)
#   F0      = 23.767  (calibration : UVI(SZA=0, O3=300) = 12.0)
#   τ_R     = 0.0834  (épaisseur optique Rayleigh effective pour l'UV erythemal)
#   σ_eff   = 0.002   (section efficace ozone effective /DU)
#   M_R     : Kasten & Young (1989)
#   M_O3    : couche sphérique à H=22 km → RAF dépendant du SZA
#
# RAF effectif ≈ 0.6 à SZA=0°, ≈ 1.2 à SZA=60°, ≈ 2.2 à SZA=75°
# (RAF augmente avec le SZA car le chemin dans la couche d'ozone s'allonge)
# ---------------------------------------------------------------------------

_LUT_SZA = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 73, 76, 79, 82, 85, 88, 90]
_LUT_O3  = [200, 225, 250, 275, 300, 325, 350, 375, 400, 425, 450]
_LUT_UVI = [
    # O3→ 200      225      250      275      300      325      350      375      400      425      450
    [14.6572, 13.9423, 13.2624, 12.6156, 12.0003, 11.415,  10.8583, 10.3287,  9.825,   9.3458,  8.89  ],  #  0°
    [14.5747, 13.8612, 13.1827, 12.5374, 11.9237, 11.34,   10.7849, 10.257,   9.7549,  9.2774,  8.8232],  #  5°
    [14.328,  13.6188, 12.9446, 12.3039, 11.6949, 11.116,  10.5658, 10.0428,  9.5457,  9.0732,  8.624 ],  # 10°
    [13.9199, 13.2179, 12.5512, 11.9182, 11.3171, 10.7464, 10.2044,  9.6897,  9.201,   8.737,   8.2963],  # 15°
    [13.3553, 12.6636, 12.0077, 11.3857, 10.796,  10.2368,  9.7066,  9.2038,  8.7271,  8.2751,  7.8465],  # 20°
    [12.6409, 11.9629, 11.3212, 10.714,  10.1393,  9.5955,  9.0809,  8.5938,  8.1329,  7.6967,  7.2838],  # 25°
    [11.7855, 11.1251, 10.5017,  9.9132,  9.3577,  8.8333,  8.3383,  7.871,   7.4299,  7.0136,  6.6206],  # 30°
    [10.8005, 10.162,   9.5613,  8.9961,  8.4642,  7.9639,  7.4931,  7.0501,  6.6333,  6.2412,  5.8722],  # 35°
    [ 9.6999,  9.0884,  8.5155,  7.9787,  7.4757,  7.0045,  6.5629,  6.1492,  5.7616,  5.3984,  5.0581],  # 40°
    [ 8.5009,  7.9225,  7.3834,  6.881,   6.4128,  5.9764,  5.5698,  5.1908,  4.8376,  4.5084,  4.2017],  # 45°
    [ 7.2249,  6.6867,  6.1887,  5.7277,  5.301,   4.9062,  4.5407,  4.2025,  3.8894,  3.5997,  3.3316],  # 50°
    [ 5.899,   5.4099,  4.9612,  4.5498,  4.1725,  3.8265,  3.5092,  3.2182,  2.9513,  2.7066,  2.4821],  # 55°
    [ 4.5583,  4.1287,  3.7396,  3.3872,  3.068,   2.7788,  2.5169,  2.2797,  2.0649,  1.8703,  1.694 ],  # 60°
    [ 3.25,    2.8927,  2.5746,  2.2915,  2.0395,  1.8153,  1.6157,  1.438,   1.2799,  1.1392,  1.0139],  # 65°
    [ 2.0401,  1.769,   1.534,   1.3302,  1.1535,  1.0003,  0.8674,  0.7522,  0.6522,  0.5656,  0.4905],  # 70°
    [ 1.399,   1.1861,  1.0057,  0.8526,  0.7229,  0.6129,  0.5197,  0.4406,  0.3736,  0.3167,  0.2685],  # 73°
    [ 0.8527,  0.7009,  0.5761,  0.4735,  0.3891,  0.3198,  0.2629,  0.2161,  0.1776,  0.146,   0.12  ],  # 76°
    [ 0.4305,  0.3383,  0.2659,  0.2089,  0.1642,  0.129,   0.1014,  0.0797,  0.0626,  0.0492,  0.0387],  # 79°
    [ 0.1571,  0.1153,  0.0846,  0.0621,  0.0456,  0.0334,  0.0245,  0.018,   0.0132,  0.0097,  0.0071],  # 82°
    [ 0.0313,  0.0207,  0.0136,  0.009,   0.0059,  0.0039,  0.0026,  0.0017,  0.0011,  0.0007,  0.0005],  # 85°
    [ 0.0019,  0.0011,  0.0006,  0.0004,  0.0002,  0.0001,  0.0001,  0.0,     0.0,     0.0,     0.0   ],  # 88°
    [ 0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0   ],  # 90°
]


def _interp_lut(sza_deg: float, o3_du: float) -> float:
    """Interpolation bilinéaire dans la LUT (SZA, O3)."""
    sza_deg = max(0.0, min(90.0, sza_deg))
    o3_du   = max(float(_LUT_O3[0]), min(float(_LUT_O3[-1]), o3_du))

    i1 = next((i for i in range(len(_LUT_SZA) - 1) if _LUT_SZA[i + 1] > sza_deg), len(_LUT_SZA) - 2)
    i2 = i1 + 1
    t_sza = (sza_deg - _LUT_SZA[i1]) / (_LUT_SZA[i2] - _LUT_SZA[i1]) if _LUT_SZA[i2] != _LUT_SZA[i1] else 0.0

    j1 = next((j for j in range(len(_LUT_O3) - 1) if _LUT_O3[j + 1] > o3_du), len(_LUT_O3) - 2)
    j2 = j1 + 1
    t_o3 = (o3_du - _LUT_O3[j1]) / (_LUT_O3[j2] - _LUT_O3[j1]) if _LUT_O3[j2] != _LUT_O3[j1] else 0.0

    v11, v12 = _LUT_UVI[i1][j1], _LUT_UVI[i1][j2]
    v21, v22 = _LUT_UVI[i2][j1], _LUT_UVI[i2][j2]
    return (
        v11 * (1 - t_sza) * (1 - t_o3)
        + v12 * (1 - t_sza) * t_o3
        + v21 * t_sza       * (1 - t_o3)
        + v22 * t_sza       * t_o3
    )


# ---------------------------------------------------------------------------
# Modèle solaire
# ---------------------------------------------------------------------------

def solar_declination(day_of_year: int) -> float:
    """Déclinaison solaire en radians."""
    return math.radians(23.45) * math.sin(math.radians(360 / 365 * (day_of_year - 81)))


def equation_of_time(day_of_year: int) -> float:
    """Equation du temps en minutes."""
    b = math.radians(360 / 365 * (day_of_year - 81))
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def earth_sun_distance_factor(day_of_year: int) -> float:
    """Facteur de correction distance Terre-Soleil (inverse carré)."""
    return 1 + 0.033 * math.cos(math.radians(360 * day_of_year / 365))


def solar_zenith_angle(latitude_rad: float, declination: float, hour_angle: float) -> float:
    """Angle zénithal solaire en radians."""
    cos_sza = (
        math.sin(latitude_rad) * math.sin(declination)
        + math.cos(latitude_rad) * math.cos(declination) * math.cos(hour_angle)
    )
    cos_sza = max(-1.0, min(1.0, cos_sza))
    return math.acos(cos_sza)


# ---------------------------------------------------------------------------
# Calcul de l'indice UV — modèle LUT Beer-Lambert
# ---------------------------------------------------------------------------

def clear_sky_uv_index(
    sza: float, distance_factor: float, ozone_du: float, altitude_km: float
) -> float:
    """
    Indice UV par ciel clair via interpolation bilinéaire dans la LUT.

    Améliorations vs. cos(θ)^1.3 :
      - Masses d'air séparées pour Rayleigh et ozone (géométrie sphérique)
      - RAF dépendant du SZA (≈0.6 à 0°, ≈1.2 à 60°, ≈2.2 à 75°)
      - Comportement réaliste à l'aube/crépuscule

    Paramètres post-LUT appliqués analytiquement :
      - distance_factor : facteur Terre-Soleil (±3.3%)
      - altitude_km     : +6 %/km niveau de la mer (WMO)
    """
    sza_deg = math.degrees(sza)
    if sza_deg >= 90.0:
        return 0.0
    uvi_base = _interp_lut(sza_deg, ozone_du)
    return uvi_base * distance_factor * (1.0 + 0.06 * altitude_km)


# ---------------------------------------------------------------------------
# Conversion heure locale → heure solaire
# ---------------------------------------------------------------------------

def local_hour_to_solar_hour(
    local_hour: float, longitude: float, day_of_year: int, utc_offset_hours: float
) -> float:
    """Convertit une heure locale en heure solaire."""
    eot = equation_of_time(day_of_year)
    solar_hour = local_hour + (eot / 60) + (longitude / 15) - utc_offset_hours
    return solar_hour


# ---------------------------------------------------------------------------
# Courbe UV journalière
# ---------------------------------------------------------------------------

def compute_uv_curve(
    latitude: float,
    longitude: float,
    chosen_date: date,
    tz: ZoneInfo,
    ozone_du: float,
    altitude_km: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Calcule l'indice UV pour chaque minute de la journée en heure locale."""
    day_of_year = chosen_date.timetuple().tm_yday
    lat_rad = math.radians(latitude)
    decl = solar_declination(day_of_year)
    dist_factor = earth_sun_distance_factor(day_of_year)

    dt_local = datetime(chosen_date.year, chosen_date.month, chosen_date.day, 12, tzinfo=tz)
    utc_offset_hours = dt_local.utcoffset().total_seconds() / 3600

    minutes = np.arange(0, 24 * 60)
    local_hours = minutes / 60.0
    uv_values = np.zeros_like(local_hours)

    for i, lh in enumerate(local_hours):
        solar_h = local_hour_to_solar_hour(lh, longitude, day_of_year, utc_offset_hours)
        hour_angle = math.radians(15 * (solar_h - 12))
        sza = solar_zenith_angle(lat_rad, decl, hour_angle)
        uv_values[i] = clear_sky_uv_index(sza, dist_factor, ozone_du, altitude_km)

    return local_hours, uv_values


# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

def uv_color(uv_max: float) -> str:
    if uv_max < 3:
        return "#4eb400"
    if uv_max < 6:
        return "#f7e400"
    if uv_max < 8:
        return "#f85900"
    if uv_max < 11:
        return "#d8001d"
    return "#6b49c8"


def uv_label(uv_max: float) -> str:
    if uv_max < 3:
        return "Faible"
    if uv_max < 6:
        return "Modéré"
    if uv_max < 8:
        return "Élevé"
    if uv_max < 11:
        return "Très élevé"
    return "Extrême"


def format_hour(h: float) -> str:
    return f"{int(h)}h{int((h % 1) * 60):02d}"


def plot_uv(
    latitude: float,
    longitude: float,
    chosen_date: date,
    tz: ZoneInfo,
    city_name: str,
    ozone_du: float,
    altitude_m: float,
) -> None:
    altitude_km = altitude_m / 1000
    local_hours, uv = compute_uv_curve(
        latitude, longitude, chosen_date, tz, ozone_du, altitude_km
    )
    uv_max = float(np.max(uv))
    peak_hour = local_hours[np.argmax(uv)]
    color = uv_color(uv_max)

    fig, ax = plt.subplots(figsize=(10, 5))

    bands = [
        (0, 3, "#4eb400", "Faible"),
        (3, 6, "#f7e400", "Modéré"),
        (6, 8, "#f85900", "Élevé"),
        (8, 11, "#d8001d", "Très élevé"),
        (11, max(14, uv_max + 1), "#6b49c8", "Extrême"),
    ]
    y_max = max(14, math.ceil(uv_max) + 1)
    for lo, hi, c, label in bands:
        if lo < y_max:
            ax.axhspan(lo, min(hi, y_max), alpha=0.10, color=c)

    ax.fill_between(local_hours, uv, alpha=0.3, color=color)
    ax.plot(local_hours, uv, color=color, linewidth=2.5)

    ax.set_xlim(0, 24)
    ax.set_ylim(0, y_max)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.set_xlabel(f"Heure locale ({tz})")
    ax.set_ylabel("Indice UV")

    date_str = chosen_date.strftime("%d/%m/%Y")
    ax.set_title(f"Indice UV ciel clair — {city_name} — {date_str}")

    # Annotation du pic
    info_lines = [
        f"UV max = {uv_max:.1f} ({uv_label(uv_max)})",
        f"à {format_hour(peak_hour)}",
        f"O₃ = {ozone_du:.0f} DU · alt. {altitude_m:.0f} m",
    ]
    ax.annotate(
        "\n".join(info_lines),
        xy=(peak_hour, uv_max),
        xytext=(peak_hour + 2, uv_max - 1.5),
        fontsize=9,
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="grey"),
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="grey", alpha=0.9),
    )

    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Calculateur d'indice UV (ciel clair) ===\n")

    city_input = input("Ville (ex: Paris, Tokyo, La Paz) : ").strip()
    if not city_input:
        print("Veuillez entrer un nom de ville.")
        sys.exit(1)

    print(f"Recherche de « {city_input} »...")
    latitude, longitude, display_name = geocode_city(city_input)
    tz = get_timezone(latitude, longitude)
    altitude_m = get_elevation(latitude, longitude)
    city_short = display_name.split(",")[0].strip()

    print(f"  → {display_name}")
    print(f"  → Coordonnées : {latitude:.2f}°, {longitude:.2f}°")
    print(f"  → Altitude : {altitude_m:.0f} m")
    print(f"  → Fuseau horaire : {tz}")

    date_str = input("\nDate (JJ/MM/AAAA, ou Entrée pour aujourd'hui) : ").strip()
    if date_str:
        try:
            chosen_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            print("Format de date invalide. Utilisez JJ/MM/AAAA.")
            sys.exit(1)
    else:
        chosen_date = date.today()

    ozone_du = get_ozone(latitude, chosen_date.month)
    print(f"  → Ozone climatologique : {ozone_du:.0f} DU")

    altitude_km = altitude_m / 1000
    local_hours, uv = compute_uv_curve(
        latitude, longitude, chosen_date, tz, ozone_du, altitude_km
    )
    uv_max = float(np.max(uv))
    peak_hour = local_hours[np.argmax(uv)]

    print(f"\n{'─' * 40}")
    print(f"  Lieu        : {city_short}")
    print(f"  Date        : {chosen_date.strftime('%d/%m/%Y')}")
    print(f"  Altitude    : {altitude_m:.0f} m")
    print(f"  Ozone       : {ozone_du:.0f} DU")
    print(f"  UV max      : {uv_max:.1f} ({uv_label(uv_max)}) à {format_hour(peak_hour)}")
    print(f"{'─' * 40}")

    plot_uv(latitude, longitude, chosen_date, tz, city_short, ozone_du, altitude_m)


if __name__ == "__main__":
    main()
