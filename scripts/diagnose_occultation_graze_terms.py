from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import swisseph as swe

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira.constants import KM_PER_AU, MOON_RADIUS_KM
from moira.eclipse_geometry import apparent_radius
from moira.occultations import (
    _angular_separation_equatorial,
    _star_topocentric_equatorial,
    _star_topocentric_target_geometry,
    lunar_star_graze_latitude,
)
from moira.planets import sky_position_at
from moira.stars import star_at
from tests.integration.test_eclipse_occultation_where_reference import (
    _parse_iota_annual_graze_section,
    _parse_iota_graze_rows_for_date,
)

_SWISS_EQ_FLAGS = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL | swe.FLG_TOPOCTR
_SWISS_STAR_PATH_CANDIDATES = (
    ROOT.parent / "Ananke",
    ROOT.parent / "IsopGem",
)


@dataclass(frozen=True, slots=True)
class Row:
    label: str
    star_name: str
    swiss_star_name: str
    jd: float
    lon: float
    lat: float
    observer_elev_m: float


def _configure_swiss_star_catalog() -> Path:
    for directory in _SWISS_STAR_PATH_CANDIDATES:
        if (directory / "sefstars.txt").exists():
            swe.set_ephe_path(str(directory))
            return directory
    raise RuntimeError("Could not find sefstars.txt for Swiss fixed-star comparisons")


def _sample_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [rows[0], rows[len(rows) // 3], rows[(2 * len(rows)) // 3], rows[-1]]


def _swiss_margin(
    swiss_star_name: str,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float,
) -> tuple[float, float, float, float, float]:
    swe.set_topo(lon, lat, observer_elev_m)
    moon_xx, _ = swe.calc_ut(jd, swe.MOON, _SWISS_EQ_FLAGS)
    star_xx, _, _ = swe.fixstar2_ut(swiss_star_name, jd, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    separation = _angular_separation_equatorial(moon_xx[0], moon_xx[1], star_xx[0], star_xx[1])
    moon_radius = apparent_radius(MOON_RADIUS_KM, moon_xx[2] * KM_PER_AU)
    margin = moon_radius - separation
    return moon_xx[0], moon_xx[1], star_xx[0], star_xx[1], separation, moon_radius, margin


def _moira_margin(
    star_name: str,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float,
) -> tuple[float, float, float, float, float, float, float]:
    star = star_at(star_name, jd)
    moon = sky_position_at("Moon", jd, lat, lon, observer_elev_m)
    star_ra, star_dec, _ = _star_topocentric_equatorial(
        star.longitude,
        star.latitude,
        jd,
        lat,
        lon,
        observer_elev_m,
    )
    separation, margin, _, _ = _star_topocentric_target_geometry(
        star.longitude,
        star.latitude,
        jd,
        lat,
        lon,
        reader=None,
        observer_elev_m=observer_elev_m,
    )
    moon_radius = apparent_radius(MOON_RADIUS_KM, moon.distance)
    return moon.right_ascension, moon.declination, star_ra, star_dec, separation, moon_radius, margin


def _margin_sensitivity_deg_per_deg(
    margin_fn,
    lat: float,
    step_deg: float = 1.0 / 120.0,
) -> float:
    return (margin_fn(lat + step_deg) - margin_fn(lat - step_deg)) / (2.0 * step_deg)


def _build_cases() -> list[Row]:
    spica_north_rows = _sample_rows(
        _parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt",
            2024,
            11,
            27,
        )
    )
    asellus_rows = _sample_rows(
        _parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt",
            "Asellus Borealis",
        )
    )
    elnath_rows = _sample_rows(
        _parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2025/20250307ElNath.txt",
            2025,
            3,
            7,
        )
    )
    spica_south_rows = _sample_rows(
        _parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt",
            2024,
            11,
            27,
        )
    )
    alcyone_rows = _sample_rows(
        _parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt",
            "Alcyone",
        )
    )
    merope_rows = _sample_rows(
        _parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt",
            "Merope",
        )
    )
    regulus_rows = _sample_rows(
        _parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt",
            "Regulus",
        )
    )

    spica_worst = spica_north_rows[-1]
    asellus_best = asellus_rows[(2 * len(asellus_rows)) // 3]
    elnath_worst = elnath_rows[-1]
    spica_south_worst = spica_south_rows[-1]
    alcyone_worst = alcyone_rows[0]
    merope_worst = merope_rows[0]
    regulus_best = regulus_rows[-1]
    return [
        Row(
            label="Swiss-winning case: El Nath",
            star_name="Elnath",
            swiss_star_name="Elnath",
            jd=float(elnath_worst["jd"]),
            lon=float(elnath_worst["lon"]),
            lat=float(elnath_worst["lat"]),
            observer_elev_m=float(elnath_worst["observer_elev_m"]),
        ),
        Row(
            label="Swiss-winning outlier: Spica north",
            star_name="Spica",
            swiss_star_name="Spica",
            jd=float(spica_worst["jd"]),
            lon=float(spica_worst["lon"]),
            lat=float(spica_worst["lat"]),
            observer_elev_m=float(spica_worst["observer_elev_m"]),
        ),
        Row(
            label="Swiss-winning case: Spica south",
            star_name="Spica",
            swiss_star_name="Spica",
            jd=float(spica_south_worst["jd"]),
            lon=float(spica_south_worst["lon"]),
            lat=float(spica_south_worst["lat"]),
            observer_elev_m=float(spica_south_worst["observer_elev_m"]),
        ),
        Row(
            label="Swiss-winning case: Alcyone",
            star_name="Alcyone",
            swiss_star_name="Alcyone",
            jd=float(alcyone_worst["jd"]),
            lon=float(alcyone_worst["lon"]),
            lat=float(alcyone_worst["lat"]),
            observer_elev_m=float(alcyone_worst["observer_elev_m"]),
        ),
        Row(
            label="Swiss-winning case: Merope",
            star_name="Merope",
            swiss_star_name="Merope",
            jd=float(merope_worst["jd"]),
            lon=float(merope_worst["lon"]),
            lat=float(merope_worst["lat"]),
            observer_elev_m=float(merope_worst["observer_elev_m"]),
        ),
        Row(
            label="Moira-winning case: Asellus Borealis",
            star_name="Asellus Borealis",
            swiss_star_name="Asellus Borealis",
            jd=float(asellus_best["jd"]),
            lon=float(asellus_best["lon"]),
            lat=float(asellus_best["lat"]),
            observer_elev_m=float(asellus_best["observer_elev_m"]),
        ),
        Row(
            label="Moira-winning case: Regulus",
            star_name="Regulus",
            swiss_star_name="Regulus",
            jd=float(regulus_best["jd"]),
            lon=float(regulus_best["lon"]),
            lat=float(regulus_best["lat"]),
            observer_elev_m=float(regulus_best["observer_elev_m"]),
        ),
    ]


def main() -> None:
    catalog = _configure_swiss_star_catalog()
    print(f"Swiss fixed-star catalog: {catalog / 'sefstars.txt'}")
    print()

    for row in _build_cases():
        moira_root = lunar_star_graze_latitude(
            star_at(row.star_name, row.jd).longitude,
            star_at(row.star_name, row.jd).latitude,
            row.jd,
            row.lon,
            row.lat,
            observer_elev_m=row.observer_elev_m,
        )

        (
            moira_moon_ra,
            moira_moon_dec,
            moira_star_ra,
            moira_star_dec,
            moira_sep,
            moira_radius,
            moira_margin,
        ) = _moira_margin(
            row.star_name,
            row.jd,
            row.lat,
            row.lon,
            row.observer_elev_m,
        )
        (
            swiss_moon_ra,
            swiss_moon_dec,
            swiss_star_ra,
            swiss_star_dec,
            swiss_sep,
            swiss_radius,
            swiss_margin,
        ) = _swiss_margin(
            row.swiss_star_name,
            row.jd,
            row.lat,
            row.lon,
            row.observer_elev_m,
        )

        moira_star = star_at(row.star_name, row.jd)
        moira_margin_deriv = _margin_sensitivity_deg_per_deg(
            lambda latitude: _star_topocentric_target_geometry(
                moira_star.longitude,
                moira_star.latitude,
                row.jd,
                latitude,
                row.lon,
                reader=None,
                observer_elev_m=row.observer_elev_m,
            )[1],
            row.lat,
        )
        swiss_margin_deriv = _margin_sensitivity_deg_per_deg(
            lambda latitude: _swiss_margin(
                row.swiss_star_name,
                row.jd,
                latitude,
                row.lon,
                row.observer_elev_m,
            )[-1],
            row.lat,
        )

        print(row.label)
        print(f"  jd={row.jd:.9f} lon={row.lon:.6f} lat={row.lat:.6f} elev_m={row.observer_elev_m:.1f}")
        print(f"  moira_root_delta_deg={moira_root - row.lat:+0.9f}")
        print(f"  moira_moon_ra_dec=({moira_moon_ra:0.9f}, {moira_moon_dec:0.9f})")
        print(f"  swiss_moon_ra_dec=({swiss_moon_ra:0.9f}, {swiss_moon_dec:0.9f})")
        print(f"  moon_ra_diff_deg={moira_moon_ra - swiss_moon_ra:+0.9f}")
        print(f"  moon_dec_diff_deg={moira_moon_dec - swiss_moon_dec:+0.9f}")
        print(f"  moira_star_ra_dec=({moira_star_ra:0.9f}, {moira_star_dec:0.9f})")
        print(f"  swiss_star_ra_dec=({swiss_star_ra:0.9f}, {swiss_star_dec:0.9f})")
        print(f"  star_ra_diff_deg={moira_star_ra - swiss_star_ra:+0.9f}")
        print(f"  star_dec_diff_deg={moira_star_dec - swiss_star_dec:+0.9f}")
        print(f"  moira_sep={moira_sep:0.9f} swiss_sep={swiss_sep:0.9f} sep_diff={moira_sep - swiss_sep:+0.9f}")
        print(f"  moira_radius={moira_radius:0.9f} swiss_radius={swiss_radius:0.9f} radius_diff={moira_radius - swiss_radius:+0.9f}")
        print(f"  moira_margin={moira_margin:+0.9f} swiss_margin={swiss_margin:+0.9f} margin_diff={moira_margin - swiss_margin:+0.9f}")
        print(f"  moira_dmargin_dlat={moira_margin_deriv:+0.9f} swiss_dmargin_dlat={swiss_margin_deriv:+0.9f}")
        if abs(moira_margin_deriv) > 1e-12:
            implied_lat_shift = -(moira_margin - swiss_margin) / moira_margin_deriv
            print(f"  implied_lat_shift_from_margin_diff_deg={implied_lat_shift:+0.9f}")
        print()


if __name__ == "__main__":
    main()
