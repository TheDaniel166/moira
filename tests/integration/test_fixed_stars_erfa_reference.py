from __future__ import annotations

import math
from pathlib import Path

import pytest

from moira.coordinates import equatorial_to_ecliptic
from moira.fixed_stars import fixed_star_at

erfa = pytest.importorskip("erfa")


_TARGETS = [
    "Sirius",
    "Canopus",
    "Arcturus",
    "Vega",
    "Capella",
    "Rigel",
    "Procyon",
    "Betelgeuse",
    "Aldebaran",
    "Spica",
    "Regulus",
    "Antares",
    "Fomalhaut",
    "Algol",
    "Polaris",
]

_EPOCH_MAP = {
    "ICRS": 2448349.0625,
    "2000": 2451545.0,
    "1950": 2433282.4235,
}

_TEST_EPOCHS = [
    2451545.0,   # J2000.0
    2457389.0,   # J2016.0 (Gaia DR3 epoch)
    2415020.5,   # 1900-01-01 TT-ish reference
    2488070.5,   # 2100-01-01 TT-ish reference
]

_MAX_COMPONENT_ERROR_ARCSEC = 0.3


def _parse_ra(hours: str, minutes: str, seconds: str) -> float:
    return (float(hours) + float(minutes) / 60.0 + float(seconds) / 3600.0) * 15.0


def _parse_dec(degrees: str, minutes: str, seconds: str) -> float:
    deg = float(degrees)
    arc = float(minutes) / 60.0 + float(seconds) / 3600.0
    return deg - arc if deg < 0 or degrees.strip().startswith("-") else deg + arc


def _load_target_rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    path = Path(__file__).resolve().parents[2] / "sefstars.txt"

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 16:
                continue
            if parts[0] in _TARGETS:
                rows[parts[0]] = parts

    missing = sorted(set(_TARGETS) - set(rows))
    if missing:
        raise AssertionError(f"Missing fixed-star catalog rows for: {missing}")

    return rows


_CATALOG_ROWS = _load_target_rows()


def _erfa_reference_ecliptic(parts: list[str], jd_tt: float) -> tuple[float, float]:
    equinox = parts[2].upper()
    epoch_jd = _EPOCH_MAP[equinox]

    ra_deg = _parse_ra(parts[3], parts[4], parts[5])
    dec_deg = _parse_dec(parts[6], parts[7], parts[8])
    pm_ra_star = float(parts[9])          # 0.001 arcsec/year * cos(dec)
    pm_dec = float(parts[10])             # 0.001 arcsec/year
    radial_velocity = float(parts[11]) if parts[11] else 0.0
    parallax_mas = float(parts[12]) if parts[12] else 0.0

    cos_dec = max(abs(math.cos(math.radians(dec_deg))), 1e-12)
    pm_ra_arcsec_per_year = (pm_ra_star * 0.001) / cos_dec
    pm_dec_arcsec_per_year = pm_dec * 0.001

    ra_rad, dec_rad, *_ = erfa.starpm(
        math.radians(ra_deg),
        math.radians(dec_deg),
        math.radians(pm_ra_arcsec_per_year / 3600.0),
        math.radians(pm_dec_arcsec_per_year / 3600.0),
        parallax_mas / 1000.0,
        radial_velocity,
        epoch_jd,
        0.0,
        jd_tt,
        0.0,
    )

    true_equatorial = erfa.rxp(erfa.pnm06a(jd_tt, 0.0), erfa.s2c(ra_rad, dec_rad))
    ra_true, dec_true = erfa.c2s(true_equatorial)
    eps_true = erfa.obl06(jd_tt, 0.0) + erfa.nut06a(jd_tt, 0.0)[1]

    return equatorial_to_ecliptic(
        math.degrees(ra_true) % 360.0,
        math.degrees(dec_true),
        math.degrees(eps_true),
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("star_name", _TARGETS)
@pytest.mark.parametrize("jd_tt", _TEST_EPOCHS)
def test_fixed_star_positions_match_erfa_reference(star_name: str, jd_tt: float) -> None:
    """
    Validate Moira's named fixed-star positions against an independent ERFA path.

    This checks the full ICRS/J2000 -> true-equator-of-date -> true-ecliptic-of-date
    pipeline, not just stored goldens. The representative corpus is biased toward
    bright stars and stars with meaningful proper motion/parallax.
    """
    reference_lon, reference_lat = _erfa_reference_ecliptic(_CATALOG_ROWS[star_name], jd_tt)
    result = fixed_star_at(star_name, jd_tt)

    lon_error = abs((result.longitude - reference_lon + 180.0) % 360.0 - 180.0) * 3600.0
    lat_error = abs(result.latitude - reference_lat) * 3600.0

    assert lon_error <= _MAX_COMPONENT_ERROR_ARCSEC
    assert lat_error <= _MAX_COMPONENT_ERROR_ARCSEC
