"""
Calculateur d'indice UV maximum (ciel clair) en fonction du lieu et du jour.
Affiche un graphique de l'indice UV au cours de la journée choisie en heure locale.

Modèle amélioré :
  - Climatologie d'ozone par latitude et mois (données TOMS/OMI)
  - Correction d'altitude (~6% par 1000m)
  - Formulation erythemal de Madronich (1993)
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
# Calcul de l'indice UV — modèle Madronich amélioré
# ---------------------------------------------------------------------------

def clear_sky_uv_index(
    sza: float, distance_factor: float, ozone_du: float, altitude_km: float
) -> float:
    """
    Indice UV par ciel clair — modèle erythemal amélioré.

    Basé sur Madronich (1993) / WMO (2002) :
      UV = F₀ × d × μ₀^α × (O₃/O₃_ref)^(-RAF) × (1 + β×alt)

    Paramètres :
      F₀       = 12.5  (calibration pour UV max tropical, 300 DU, alt. 0)
      α        = 1.3   (dépendance angulaire erythemal)
      RAF      = 1.2   (Radiation Amplification Factor, erythemal)
      O₃_ref   = 300 DU
      β        = 0.06  (+6% par km d'altitude)
    """
    cos_sza = math.cos(sza)
    if cos_sza <= 0:
        return 0.0

    RAF = 1.2
    ozone_factor = (ozone_du / 300.0) ** (-RAF)
    altitude_factor = 1 + 0.06 * altitude_km

    return 12.5 * (cos_sza ** 1.3) * distance_factor * ozone_factor * altitude_factor


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
