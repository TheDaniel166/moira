from __future__ import annotations

from pathlib import Path

from moira.constants import Body
from moira.gauquelin import gauquelin_sector
from moira.julian import local_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity
from moira.planets import sky_position_at
from scripts.compare_swetest import PASS_THRESHOLD, _parse_gauquelin_iterations


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "swe_t.exp"


def _sector_oracle_value(sector: int, degree_in_sector: float, sectors: int) -> float:
    """Return Swiss-style sector plus fractional-sector position."""
    value = sector + degree_in_sector / (360.0 / sectors)
    return value - sectors if value >= sectors + 1 else value


def _sector_diff(a: float, b: float, sectors: int = 36) -> float:
    diff = abs(a - b) % sectors
    return diff if diff <= sectors / 2 else sectors - diff


def test_gauquelin_sun_matches_offline_swiss_method_zero_reference(moira_engine) -> None:
    """
    Secondary oracle audit against cached Swiss ``swe_gauquelin_sector()`` rows.

    The fixture block's method-0 rows encode the Sun's Gauquelin sector as
    ``sector + fractional_sector``.  The comparison uses Moira's apparent
    topocentric RA/Dec for the Sun, geometric horizon DSA, and the same
    observer latitude/longitude and JD_UT carried by the fixture.

    This is a corroborating oracle.  The primary proof remains the local
    diurnal-sector boundary doctrine in the unit tests.
    """
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")
    iterations = _parse_gauquelin_iterations(fixture_text, imeth=0)

    failures: list[str] = []
    for it in iterations:
        jd_ut = it["jd_ut"]
        jd_tt = ut_to_tt(jd_ut)
        dpsi, _ = nutation(jd_tt)
        obliquity = true_obliquity(jd_tt)
        lst = local_sidereal_time(jd_ut, it["lon"], dpsi, obliquity)
        sky = sky_position_at(
            Body.SUN,
            jd_ut,
            observer_lat=it["lat"],
            observer_lon=it["lon"],
            reader=moira_engine._reader,
            refraction=False,
        )
        position = gauquelin_sector(
            sky.right_ascension,
            sky.declination,
            it["lat"],
            lst,
            horizon_altitude=0.0,
        )
        moira_gp = _sector_oracle_value(
            position.sector,
            position.degree_in_sector,
            position.sectors,
        )
        diff = _sector_diff(moira_gp, it["gp"])
        if diff > PASS_THRESHOLD:
            failures.append(
                f"jd={jd_ut:.6f} lat={it['lat']:.2f} lon={it['lon']:.2f} "
                f"swiss_gp={it['gp']:.9f} moira_gp={moira_gp:.9f} diff={diff:.9f}"
            )

    assert iterations, "No Swiss Gauquelin method-0 oracle rows parsed"
    assert not failures, "Gauquelin oracle mismatches:\n" + "\n".join(failures)
