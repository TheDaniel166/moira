from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import swisseph as swe

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira.planets import sky_position_at
from tests.integration.test_eclipse_occultation_where_reference import (
    _parse_iota_annual_graze_section,
    _parse_iota_graze_rows_for_date,
)
from tests.tools.horizons import observer_sky_position

_SWISS_EQ_FLAGS = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL | swe.FLG_TOPOCTR
_SWISS_STAR_PATH_CANDIDATES = (
    ROOT.parent / "Ananke",
    ROOT.parent / "IsopGem",
)


@dataclass(frozen=True, slots=True)
class Row:
    label: str
    jd: float
    lon: float
    lat: float
    observer_elev_m: float


def _configure_swiss() -> Path:
    for directory in _SWISS_STAR_PATH_CANDIDATES:
        if (directory / "sefstars.txt").exists():
            swe.set_ephe_path(str(directory))
            return directory
    raise RuntimeError("Could not find Swiss ephemeris path")


def _signed_arcsec(a_deg: float, b_deg: float) -> float:
    return ((a_deg - b_deg + 180.0) % 360.0 - 180.0) * 3600.0


def _build_cases() -> list[Row]:
    def first(rows):
        return rows[0]

    def last(rows):
        return rows[-1]

    return [
        Row("El Nath worst row", **last(_parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2025/20250307ElNath.txt", 2025, 3, 7
        ))),
        Row("Spica north worst row", **last(_parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt", 2024, 11, 27
        ))),
        Row("Spica south worst row", **last(_parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt", 2024, 11, 27
        ))),
        Row("Alcyone leading row", **first(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Alcyone"
        ))),
        Row("Merope leading row", **first(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Merope"
        ))),
        Row("Asellus Borealis control row", **_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Asellus Borealis"
        )[(2 * len(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Asellus Borealis"
        ))) // 3]),
        Row("Regulus control row", **last(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Regulus"
        ))),
    ]


def main() -> None:
    swiss_path = _configure_swiss()
    print(f"Swiss ephemeris path: {swiss_path}")
    print()

    for row in _build_cases():
        moira = sky_position_at(
            "Moon",
            row.jd,
            observer_lat=row.lat,
            observer_lon=row.lon,
            observer_elev_m=row.observer_elev_m,
        )
        ref = observer_sky_position(
            "301",
            row.jd,
            longitude_deg=row.lon,
            latitude_deg=row.lat,
            elevation_km=row.observer_elev_m / 1000.0,
        )

        swe.set_topo(row.lon, row.lat, row.observer_elev_m)
        moon_xx, _ = swe.calc_ut(row.jd, swe.MOON, _SWISS_EQ_FLAGS)

        moira_ra_err = _signed_arcsec(moira.right_ascension, ref.right_ascension)
        moira_dec_err = (moira.declination - ref.declination) * 3600.0
        swiss_ra_err = _signed_arcsec(moon_xx[0], ref.right_ascension)
        swiss_dec_err = (moon_xx[1] - ref.declination) * 3600.0

        moira_total = max(abs(moira_ra_err), abs(moira_dec_err))
        swiss_total = max(abs(swiss_ra_err), abs(swiss_dec_err))

        winner = "Moira" if moira_total < swiss_total else "Swiss"
        print(row.label)
        print(f"  site lon={row.lon:.6f} lat={row.lat:.6f} elev_m={row.observer_elev_m:.1f} jd={row.jd:.9f}")
        print(f"  HORIZONS Moon RA/Dec=({ref.right_ascension:.9f}, {ref.declination:.9f})")
        print(f"  Moira RA/Dec=({moira.right_ascension:.9f}, {moira.declination:.9f})")
        print(f"  Swiss RA/Dec=({moon_xx[0]:.9f}, {moon_xx[1]:.9f})")
        print(f"  Moira errors: RA={moira_ra_err:+.3f}\" DEC={moira_dec_err:+.3f}\"")
        print(f"  Swiss errors: RA={swiss_ra_err:+.3f}\" DEC={swiss_dec_err:+.3f}\"")
        print(f"  winner={winner}")
        print()


if __name__ == "__main__":
    main()
