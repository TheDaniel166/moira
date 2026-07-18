from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira.coordinates import (
    icrf_to_equatorial,
    mat_vec_mul,
    nutation_matrix_equatorial,
    precession_matrix_equatorial,
)
from moira.eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    _lunar_canon_axis_geometry_tt,
    _lunar_canon_vectors_tt,
    find_lunar_contacts_canon,
    lunar_canon_geometry,
)
from moira.eclipse_contacts import find_lunar_contacts
from moira.julian import julian_day


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"
CONTACT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_lunar_contact_instants_reference.json"
)
_CONTACT_FIELDS = ("p1", "u1", "u2", "u3", "u4", "p4")
_CONTACT_TOLERANCES_SECONDS = {
    "ordinary_cross_model": (120.0, 10.0),
    "limiting_robustness": (240.0, 30.0),
}
_FIGURE_PROVENANCE = {
    "2023-05-05 penumbral": (
        "https://eclipse.gsfc.nasa.gov/LEplot/LEplot2001/LE2023May05N.pdf",
        "DDD19DE28066B088EBF570B46EFF82FD0A5E5115746EDE2DEBA8DB22D1B15CE8"
    ),
    "2024-09-18 partial": (
        "https://eclipse.gsfc.nasa.gov/LEplot/LEplot2001/LE2024Sep18P.pdf",
        "78DB2A18CAB221CD2B64204E3502ABDA560115DF01DA189051AF86031100B032"
    ),
    "2025-03-14 total": (
        "https://eclipse.gsfc.nasa.gov/LEplot/LEplot2001/LE2025Mar14T.pdf",
        "4DF1EFA14457A1E925C2E63C0D8A7A428D30627532ABC11E5C15E3E219D2D166"
    ),
    "2027-07-18 limiting penumbral": (
        "https://eclipse.gsfc.nasa.gov/LEplot/LEplot2001/LE2027Jul18N.pdf",
        "70939615446926B117AF6C2457ACFF446CDDCFE3AFFE99A550DAE08E464DE01A"
    ),
}


def _contact_cases() -> tuple[dict[str, float | str], ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return tuple(payload["lunar_contact_products"])


def _contact_instant_cases() -> tuple[dict[str, object], ...]:
    payload = json.loads(CONTACT_FIXTURE_PATH.read_text(encoding="utf-8"))
    return tuple(payload["events"])


def _ut_jd(value: str) -> float:
    date_text, time_text = value.split("T")
    year, month, day = (int(part) for part in date_text.split("-"))
    hour_text, minute_text, second_text = time_text.split(":")
    hour = (
        int(hour_text)
        + int(minute_text) / 60.0
        + float(second_text) / 3600.0
    )
    return julian_day(year, month, day, hour)


def _sexagesimal_degrees(value: str, *, hours: bool = False) -> float:
    sign = -1.0 if value.startswith("-") else 1.0
    unsigned = value.lstrip("+-")
    major_text, minute_text, second_text = unsigned.split(":")
    degrees = (
        int(major_text)
        + int(minute_text) / 60.0
        + float(second_text) / 3600.0
    )
    return sign * degrees * (15.0 if hours else 1.0)


def _true_equatorial(
    jd_tt: float,
    xyz: tuple[float, float, float],
) -> tuple[float, float, float]:
    true_xyz = mat_vec_mul(
        nutation_matrix_equatorial(jd_tt),
        mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz),
    )
    return icrf_to_equatorial(true_xyz)


def _duration_minutes(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start) * 1440.0


def test_lunar_contact_fixture_names_its_catalog_semantics_and_sources() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert "Danjon" in payload["source"]["lunar_contact_validation_note"]
    rows = payload["lunar_contact_products"]
    assert len(rows) == 4
    assert {str(row["kind"]) for row in rows} == {"penumbral", "partial", "total"}
    assert all(
        row["source_url"]
        == "https://eclipse.gsfc.nasa.gov/LEcat5/LE2001-2100.html"
        for row in rows
    )
    for row in rows:
        derived_ut_jd = float(row["greatest_td_jd"]) - (
            float(row["delta_t_s"]) / 86400.0
        )
        assert float(row["greatest_ut_jd"]) == pytest.approx(
            derived_ut_jd,
            abs=1.0e-9,
        )


def test_lunar_contact_instant_fixture_names_its_figure_semantics_and_sources() -> None:
    payload = json.loads(CONTACT_FIXTURE_PATH.read_text(encoding="utf-8"))
    source = payload["source"]
    assert source["authority"] == "NASA/GSFC Eclipse Predictions by Fred Espenak"
    assert source["time_scale"] == "UT"
    assert source["comparison_time_scale"] == "TT"
    assert source["ephemerides"] == "VSOP87/ELP2000-85"
    assert source["shadow_rule"] == "CdT (Danjon)"
    assert float(source["contact_display_precision_s"]) == 1.0
    assert float(source["greatest_display_precision_s"]) == 0.1
    assert float(source["nasa_compat_greatest_tolerance_s"]) == 10.0
    assert DEFAULT_LUNAR_CANON_METHOD == "nasa_shadow_axis_apparent_sun_moon"
    assert source["contact_key_url"] == (
        "https://eclipse.gsfc.nasa.gov/LEplot/LEplotkey.html"
    )

    rows = payload["events"]
    duration_rows = _contact_cases()
    assert [row["label"] for row in rows] == [row["label"] for row in duration_rows]
    assert {str(row["kind"]) for row in rows} == {"penumbral", "partial", "total"}
    expected_fields = {
        "penumbral": {"p1", "p4"},
        "partial": {"p1", "u1", "u4", "p4"},
        "total": set(_CONTACT_FIELDS),
    }
    for row in rows:
        evidence_class = str(row["evidence_class"])
        expected_native, expected_compat = _CONTACT_TOLERANCES_SECONDS[
            evidence_class
        ]
        assert float(row["native_tt_tolerance_s"]) == expected_native
        assert float(row["nasa_compat_tt_tolerance_s"]) == expected_compat
        assert set(row["contacts_ut"]) == expected_fields[str(row["kind"])]
        expected_url, expected_sha256 = _FIGURE_PROVENANCE[str(row["label"])]
        assert str(row["figure_url"]) == expected_url
        assert str(row["figure_sha256"]) == expected_sha256

        contact_jds = [
            _ut_jd(str(row["contacts_ut"][field]))
            for field in _CONTACT_FIELDS
            if field in row["contacts_ut"]
        ]
        assert contact_jds == sorted(contact_jds)
        assert contact_jds[0] < _ut_jd(str(row["greatest_ut"])) < contact_jds[-1]


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    _contact_instant_cases(),
    ids=lambda row: f"{row['label']} NASA compatibility greatest",
)
def test_nasa_compat_lunar_greatest_instants_match_named_nasa_figures_on_tt(
    eclipse_calculator,
    row: dict[str, object],
) -> None:
    """Compare greatest TT with the strongest figure field retained per row."""

    payload = json.loads(CONTACT_FIXTURE_PATH.read_text(encoding="utf-8"))
    tolerance_seconds = float(
        payload["source"]["nasa_compat_greatest_tolerance_s"]
    )
    contacts = find_lunar_contacts_canon(
        eclipse_calculator,
        _ut_jd(str(row["greatest_ut"])),
    )
    printed_geometry = row.get("printed_greatest_geometry")
    if isinstance(printed_geometry, dict) and "greatest_td" in printed_geometry:
        expected_tt = _ut_jd(str(printed_geometry["greatest_td"]))
    else:
        expected_tt = _ut_jd(str(row["greatest_ut"])) + (
            float(row["delta_t_s"]) / 86400.0
        )
    residual_seconds = (contacts.greatest_tt - expected_tt) * 86400.0

    assert abs(residual_seconds) <= tolerance_seconds, (
        f"{row['label']} NASA compatibility greatest TT residual "
        f"{residual_seconds:+.3f} s exceeds {tolerance_seconds:.1f} s"
    )


@pytest.mark.slow
def test_default_nasa_compatibility_reproduces_printed_2025_figure_geometry(
    eclipse_calculator,
) -> None:
    """Validate the apparent-vector policy before fitting contact roots."""

    payload = json.loads(CONTACT_FIXTURE_PATH.read_text(encoding="utf-8"))
    row = next(
        item for item in payload["events"]
        if item["label"] == "2025-03-14 total"
    )
    printed = row["printed_greatest_geometry"]
    tolerances = payload["source"]["printed_geometry_tolerances"]
    jd_tt = _ut_jd(str(printed["greatest_td"]))

    sun_xyz, moon_xyz = _lunar_canon_vectors_tt(
        eclipse_calculator,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    sun_ra, sun_dec, sun_dist = _true_equatorial(jd_tt, sun_xyz)
    moon_ra, moon_dec, moon_dist = _true_equatorial(jd_tt, moon_xyz)
    ra_tolerance_deg = float(tolerances["right_ascension_arcsec"]) / 3600.0
    dec_tolerance_deg = float(tolerances["declination_arcsec"]) / 3600.0

    def circular_error(left: float, right: float) -> float:
        return abs((left - right + 180.0) % 360.0 - 180.0)

    assert circular_error(
        sun_ra,
        _sexagesimal_degrees(str(printed["sun_ra"]), hours=True),
    ) <= ra_tolerance_deg
    assert sun_dec == pytest.approx(
        _sexagesimal_degrees(str(printed["sun_dec"])),
        abs=dec_tolerance_deg,
    )
    assert circular_error(
        moon_ra,
        _sexagesimal_degrees(str(printed["moon_ra"]), hours=True),
    ) <= ra_tolerance_deg
    assert moon_dec == pytest.approx(
        _sexagesimal_degrees(str(printed["moon_dec"])),
        abs=dec_tolerance_deg,
    )

    semidiameter_tolerance = float(tolerances["semidiameter_arcsec"])
    parallax_tolerance = float(tolerances["horizontal_parallax_arcsec"])
    sun_semidiameter_arcsec = math.degrees(
        math.asin(SUN_RADIUS_KM / sun_dist)
    ) * 3600.0
    moon_semidiameter_arcsec = math.degrees(
        math.asin(MOON_RADIUS_KM / moon_dist)
    ) * 3600.0
    sun_parallax_arcsec = math.degrees(
        math.asin(EARTH_RADIUS_KM / sun_dist)
    ) * 3600.0
    moon_parallax_arcsec = math.degrees(
        math.asin(EARTH_RADIUS_KM / moon_dist)
    ) * 3600.0
    assert sun_semidiameter_arcsec == pytest.approx(
        _sexagesimal_degrees(str(printed["sun_semidiameter"])) * 3600.0,
        abs=semidiameter_tolerance,
    )
    assert moon_semidiameter_arcsec == pytest.approx(
        _sexagesimal_degrees(str(printed["moon_semidiameter"])) * 3600.0,
        abs=semidiameter_tolerance,
    )
    assert sun_parallax_arcsec == pytest.approx(
        _sexagesimal_degrees(str(printed["sun_horizontal_parallax"])) * 3600.0,
        abs=parallax_tolerance,
    )
    assert moon_parallax_arcsec == pytest.approx(
        _sexagesimal_degrees(str(printed["moon_horizontal_parallax"])) * 3600.0,
        abs=parallax_tolerance,
    )

    axis_km, _north, moon_dist, _moon_radius, umbra_radius, penumbra_radius = (
        _lunar_canon_axis_geometry_tt(
            eclipse_calculator,
            jd_tt,
            method=DEFAULT_LUNAR_CANON_METHOD,
        )
    )
    geometry = lunar_canon_geometry(
        eclipse_calculator,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    assert geometry.gamma_earth_radii == pytest.approx(
        float(printed["gamma_earth_radii"]),
        abs=float(tolerances["gamma_earth_radii"]),
    )
    assert math.degrees(math.asin(axis_km / moon_dist)) == pytest.approx(
        float(printed["axis_deg"]),
        abs=float(tolerances["axis_deg"]),
    )
    assert umbra_radius == pytest.approx(
        float(printed["umbra_radius_deg"]),
        abs=float(tolerances["shadow_radius_deg"]),
    )
    assert penumbra_radius == pytest.approx(
        float(printed["penumbra_radius_deg"]),
        abs=float(tolerances["shadow_radius_deg"]),
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    _contact_cases(),
    ids=lambda row: str(row["label"]),
)
def test_native_lunar_contact_durations_match_named_nasa_catalog_products(
    eclipse_calculator,
    row: dict[str, float | str],
) -> None:
    """Compare native mean-limb phase durations with named NASA rows.

    NASA's century catalog uses VSOP87/ELP2000-82, Danjon enlargement, and
    catalog Delta-T; Moira uses DE441 with its native TT/UT policy.  The
    fixture therefore owns explicit cross-model duration envelopes.  The
    limiting 2027 penumbral row is evidence that the short P1/P4 pair remains
    resolved, not a sub-minute parity claim.
    """

    greatest_ut = float(row["greatest_ut_jd"])
    contacts = find_lunar_contacts(eclipse_calculator, greatest_ut)
    data = eclipse_calculator.calculate_jd(contacts.greatest)

    assert str(data.eclipse_type).lower() == str(row["kind"])
    assert abs(contacts.greatest - greatest_ut) * 86400.0 <= float(
        row["greatest_tolerance_s"]
    )

    phase_pairs = {
        "penumbral_duration_min": (contacts.p1, contacts.p4),
        "partial_duration_min": (contacts.u1, contacts.u4),
        "total_duration_min": (contacts.u2, contacts.u3),
    }
    duration_tolerance = float(row["duration_tolerance_min"])
    for field, (start, end) in phase_pairs.items():
        actual_duration = _duration_minutes(start, end)
        if field not in row:
            assert actual_duration is None
            continue
        assert actual_duration is not None
        assert actual_duration == pytest.approx(
            float(row[field]),
            abs=duration_tolerance,
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    _contact_instant_cases(),
    ids=lambda row: f"{row['label']} native instants",
)
def test_native_lunar_contact_instants_match_named_nasa_figures_on_tt(
    eclipse_calculator,
    row: dict[str, object],
) -> None:
    """Bound every applicable native contact against its NASA figure instant."""

    contacts = find_lunar_contacts(
        eclipse_calculator,
        _ut_jd(str(row["greatest_ut"])),
    )
    expected_contacts = row["contacts_ut"]
    tolerance_seconds = float(row["native_tt_tolerance_s"])
    delta_t_days = float(row["delta_t_s"]) / 86400.0

    for field in _CONTACT_FIELDS:
        actual_ut = getattr(contacts, field)
        if field not in expected_contacts:
            assert actual_ut is None
            continue
        assert actual_ut is not None
        expected_tt = _ut_jd(str(expected_contacts[field])) + delta_t_days
        actual_tt = _ut1_to_ephemeris_tt(
            actual_ut,
            eclipse_calculator._reader,
        )
        residual_seconds = (actual_tt - expected_tt) * 86400.0
        assert abs(residual_seconds) <= tolerance_seconds, (
            f"{row['label']} native {field} TT residual "
            f"{residual_seconds:+.3f} s exceeds {tolerance_seconds:.1f} s"
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    _contact_instant_cases(),
    ids=lambda row: f"{row['label']} NASA compatibility instants",
)
def test_nasa_compat_lunar_contact_instants_match_named_nasa_figures_on_tt(
    eclipse_calculator,
    row: dict[str, object],
) -> None:
    """Compare the DE441 NASA-compatibility contacts in their stored TT scale."""

    contacts = find_lunar_contacts_canon(
        eclipse_calculator,
        _ut_jd(str(row["greatest_ut"])),
    )
    expected_contacts = row["contacts_ut"]
    tolerance_seconds = float(row["nasa_compat_tt_tolerance_s"])
    delta_t_days = float(row["delta_t_s"]) / 86400.0

    for field in _CONTACT_FIELDS:
        actual_tt = getattr(contacts, f"{field}_tt")
        if field not in expected_contacts:
            assert actual_tt is None
            continue
        assert actual_tt is not None
        expected_tt = _ut_jd(str(expected_contacts[field])) + delta_t_days
        residual_seconds = (actual_tt - expected_tt) * 86400.0
        assert abs(residual_seconds) <= tolerance_seconds, (
            f"{row['label']} NASA compatibility {field} TT residual "
            f"{residual_seconds:+.3f} s exceeds {tolerance_seconds:.1f} s"
        )
