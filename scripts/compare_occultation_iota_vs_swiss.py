from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
import swisseph as swe

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira.constants import KM_PER_AU, MOON_RADIUS_KM
from moira.eclipse_geometry import apparent_radius
from moira.julian import julian_day, ut_to_tt
from moira.occultations import _angular_separation_equatorial, lunar_star_graze_latitude
from moira.stars import star_at


_SWISS_EQ_FLAGS = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL | swe.FLG_TOPOCTR
_SWISS_STAR_PATH_CANDIDATES = (
    ROOT.parent / "Ananke",
    ROOT.parent / "IsopGem",
)


@dataclass(frozen=True, slots=True)
class IotaRow:
    jd: float
    lon: float
    lat: float
    observer_elev_m: float


def _parse_iota_rows_for_date(
    url: str,
    year: int,
    month: int,
    day: int,
) -> list[IotaRow]:
    raw_text = requests.get(url, timeout=30).text
    elev_match = re.search(r"Nominal site altitude\s+([\d.]+)\s*m", raw_text)
    nominal_elev_m = float(elev_match.group(1)) if elev_match else 0.0
    rows: list[IotaRow] = []
    for line in raw_text.splitlines():
        match = re.match(
            r"^\s*([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+([+-]?)\s*(\d+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)",
            line,
        )
        if match is None:
            continue

        lon_sign, lon_deg, lon_min, lon_sec, lat_sign, lat_deg, lat_min, lat_sec, hh, mm, ss = match.groups()
        lon = int(lon_deg) + int(lon_min) / 60.0 + int(lon_sec) / 3600.0
        if lon_sign == "-":
            lon = -lon
        lat = int(lat_deg) + int(lat_min) / 60.0 + float(lat_sec) / 3600.0
        if lat_sign == "-":
            lat = -lat
        jd = julian_day(year, month, day, int(hh) + int(mm) / 60.0 + int(ss) / 3600.0)
        rows.append(IotaRow(jd=jd, lon=lon, lat=lat, observer_elev_m=nominal_elev_m))
    return rows


def _parse_iota_annual_rows(
    url: str,
    star_label: str,
) -> list[IotaRow]:
    text = requests.get(url, timeout=30).text
    sections = [s for s in re.split(r"(?=^#\s*\d+:)", text, flags=re.M) if s.strip().startswith("#")]
    section = next(
        (s for s in sections if star_label.lower() in s.splitlines()[0].lower()),
        None,
    )
    if section is None:
        raise RuntimeError(f"Could not find annual IOTA section for {star_label!r}")

    header = section.splitlines()[0]
    date_match = re.search(r":\s*([A-Z]+)\.?\s+(\d{1,2}),\s+(\d{4})", header)
    if date_match is None:
        raise RuntimeError(f"Could not parse date for annual IOTA section {star_label!r}")
    month_token, day_text, year_text = date_match.groups()
    month_map = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "JULY": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }
    month = month_map[month_token.upper()]
    day = int(day_text)
    year = int(year_text)
    elev_match = re.search(r"Nominal site altitude\s+([\d.]+)\s*m", section)
    nominal_elev_m = float(elev_match.group(1)) if elev_match else 0.0

    rows: list[IotaRow] = []
    for line in section.splitlines():
        match = re.match(
            r"^\s*([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+([+-]?)\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)",
            line,
        )
        if match is None:
            continue
        lon_sign, lon_deg, lon_min, lon_sec, lat_sign, lat_deg, lat_min, lat_sec, hh, mm, ss = match.groups()
        lon = int(lon_deg) + int(lon_min) / 60.0 + int(lon_sec) / 3600.0
        if lon_sign == "-":
            lon = -lon
        lat = int(lat_deg) + int(lat_min) / 60.0 + int(lat_sec) / 3600.0
        if lat_sign == "-":
            lat = -lat
        jd = julian_day(year, month, day, int(hh) + int(mm) / 60.0 + float(ss) / 3600.0)
        rows.append(IotaRow(jd=jd, lon=lon, lat=lat, observer_elev_m=nominal_elev_m))
    return rows


def _configure_swiss_star_catalog() -> Path | None:
    for directory in _SWISS_STAR_PATH_CANDIDATES:
        if (directory / "sefstars.txt").exists():
            swe.set_ephe_path(str(directory))
            return directory
    return None


def _sample_rows(rows: list[IotaRow]) -> list[IotaRow]:
    return [rows[0], rows[len(rows) // 3], rows[(2 * len(rows)) // 3], rows[-1]]


def _solve_root(
    margin_fn,
    guess_lat: float,
    *,
    half_width: float = 3.0,
    expand_step: float = 2.0,
    max_expand: int = 20,
    iterations: int = 50,
) -> float | None:
    left = guess_lat - half_width
    right = guess_lat + half_width
    f_left = margin_fn(left)
    f_right = margin_fn(right)
    for _ in range(max_expand):
        if f_left * f_right <= 0.0:
            break
        left -= expand_step
        right += expand_step
        f_left = margin_fn(left)
        f_right = margin_fn(right)
    else:
        return None

    if f_left * f_right > 0.0:
        return None

    for _ in range(iterations):
        mid = (left + right) / 2.0
        f_mid = margin_fn(mid)
        if f_left * f_mid <= 0.0:
            right = mid
        else:
            left = mid
            f_left = f_mid
    return (left + right) / 2.0


def _swiss_margin(
    swiss_star_name: str,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float,
) -> float:
    swe.set_topo(lon, lat, observer_elev_m)
    moon_xx, _ = swe.calc_ut(jd, swe.MOON, _SWISS_EQ_FLAGS)
    star_xx, _, _ = swe.fixstar2_ut(swiss_star_name, jd, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    separation = _angular_separation_equatorial(moon_xx[0], moon_xx[1], star_xx[0], star_xx[1])
    moon_radius = apparent_radius(MOON_RADIUS_KM, moon_xx[2] * KM_PER_AU)
    return moon_radius - separation


def _summarize_case(
    *,
    label: str,
    rows: list[IotaRow],
    moira_star_name: str,
    swiss_star_name: str,
) -> tuple[float, float, float, float]:
    rows = _sample_rows(rows)
    star = star_at(moira_star_name, ut_to_tt(rows[0].jd))
    moira_errors: list[float] = []
    swiss_errors: list[float] = []

    print(label)
    for row in rows:
        moira_root = lunar_star_graze_latitude(
            star.longitude,
            star.latitude,
            row.jd,
            row.lon,
            row.lat,
            observer_elev_m=row.observer_elev_m,
        )
        swiss_root = _solve_root(
            lambda latitude: _swiss_margin(
                swiss_star_name,
                row.jd,
                latitude,
                row.lon,
                row.observer_elev_m,
            ),
            row.lat,
        )
        if swiss_root is None:
            raise RuntimeError(f"Could not solve one of the comparison roots for row at lon={row.lon}")

        moira_error = abs(moira_root - row.lat)
        swiss_error = abs(swiss_root - row.lat)
        moira_errors.append(moira_error)
        swiss_errors.append(swiss_error)
        winner = "Moira" if moira_error < swiss_error else "Swiss"
        print(
            f"  lon={row.lon:7.2f}  iota_lat={row.lat:9.6f}  "
            f"moira_err={moira_error:0.9f}  swiss_err={swiss_error:0.9f}  winner={winner}"
        )

    moira_mean = sum(moira_errors) / len(moira_errors)
    swiss_mean = sum(swiss_errors) / len(swiss_errors)
    print(
        f"  summary: moira_mean={moira_mean:0.9f}  swiss_mean={swiss_mean:0.9f}  "
        f"moira_worst={max(moira_errors):0.9f}  swiss_worst={max(swiss_errors):0.9f}"
    )
    print()
    return moira_mean, swiss_mean, max(moira_errors), max(swiss_errors)


def main() -> None:
    star_path = _configure_swiss_star_catalog()
    if star_path is None:
        raise RuntimeError("Could not find sefstars.txt for Swiss fixed-star comparisons")
    print(f"Swiss fixed-star catalog: {star_path / 'sefstars.txt'}")
    print()

    cases = [
        (
            "El Nath 2025 vs IOTA",
            _parse_iota_rows_for_date("https://occultations.org/publications/rasc/2025/20250307ElNath.txt", 2025, 3, 7),
            "Elnath",
            "Elnath",
        ),
        (
            "Spica north limit vs IOTA",
            _parse_iota_rows_for_date("https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt", 2024, 11, 27),
            "Spica",
            "Spica",
        ),
        (
            "Spica south limit vs IOTA",
            _parse_iota_rows_for_date("https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt", 2024, 11, 27),
            "Spica",
            "Spica",
        ),
        (
            "Alcyone 2025 vs IOTA",
            _parse_iota_annual_rows("https://occultations.org/publications/rasc/2025/nam25grz.txt", "Alcyone"),
            "Alcyone",
            "Alcyone",
        ),
        (
            "Merope 2025 vs IOTA",
            _parse_iota_annual_rows("https://occultations.org/publications/rasc/2025/nam25grz.txt", "Merope"),
            "Merope",
            "Merope",
        ),
        (
            "Asellus Borealis 2025 vs IOTA",
            _parse_iota_annual_rows("https://occultations.org/publications/rasc/2025/nam25grz.txt", "Asellus Borealis"),
            "Asellus Borealis",
            "Asellus Borealis",
        ),
        (
            "Regulus 2025 vs IOTA",
            _parse_iota_annual_rows("https://occultations.org/publications/rasc/2025/nam25grz.txt", "Regulus"),
            "Regulus",
            "Regulus",
        ),
    ]

    summaries = []
    for label, rows, moira_star_name, swiss_star_name in cases:
        summaries.append((label, *_summarize_case(
            label=label,
            rows=rows,
            moira_star_name=moira_star_name,
            swiss_star_name=swiss_star_name,
        )))

    print("Corpus summary")
    for label, moira_mean, swiss_mean, moira_worst, swiss_worst in summaries:
        winner = "Moira" if moira_mean < swiss_mean else "Swiss"
        print(
            f"  {label}: moira_mean={moira_mean:0.9f} swiss_mean={swiss_mean:0.9f} "
            f"moira_worst={moira_worst:0.9f} swiss_worst={swiss_worst:0.9f} winner={winner}"
        )


if __name__ == "__main__":
    main()
