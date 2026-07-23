from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.julian import julian_day


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "lunar_eclipse_global_parameters_reference.json"
)
NASA_CONTACT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_lunar_contact_instants_reference.json"
)


def _sexagesimal_degrees(value: str, *, hours: bool = False) -> float:
    sign = -1.0 if value.startswith("-") else 1.0
    major, minute, second = value.lstrip("+-").split(":")
    result = int(major) + int(minute) / 60.0 + float(second) / 3600.0
    return sign * result * (15.0 if hours else 1.0)


def _calendar_jd(value: str) -> float:
    date_text, time_text = value.split("T")
    year, month, day = (int(part) for part in date_text.split("-"))
    hour, minute, second = time_text.split(":")
    decimal_hour = int(hour) + int(minute) / 60.0 + float(second) / 3600.0
    return julian_day(year, month, day, decimal_hour)


def _circular_error_deg(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def test_fixture_declares_cross_model_semantics() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    source = payload["source"]
    assert source["evidence_class"] == "cross_model_corroboration"
    assert source["ephemerides"] == "JPL DE430"
    assert source["lunar_origin"] == "Moon center of mass"
    assert "Herald/Sinnott" in source["shadow_rule"]
    assert source["archived_sha256"] is None
    assert float(source["delta_t_seconds"]) == 72.3


@pytest.mark.slow
@pytest.mark.parametrize("mode", ["native", "nasa_compat"])
def test_lunar_global_circumstances_are_mode_pure_and_internally_consistent(
    eclipse_calculator,
    mode: str,
) -> None:
    result = eclipse_calculator.lunar_global_circumstances(
        julian_day(2026, 8, 20),
        kind="partial",
        mode=mode,
    )
    assert result.mode == mode == result.analysis.mode
    assert result.ephemeris == "DE-0441LE-0441"
    assert result.sun.frame == result.moon.frame
    assert result.sun.correction_policy == result.moon.correction_policy
    assert result.shadow.penumbral_magnitude >= result.shadow.umbral_magnitude
    assert result.penumbral_duration_seconds is not None
    assert result.partial_duration_seconds is not None
    assert result.total_duration_seconds is None
    assert result.greatest.delta_t_seconds == pytest.approx(
        (result.greatest.jd_tt - result.greatest.jd_ut1) * 86400.0,
        abs=5.0e-5,
    )
    if mode == "native":
        assert "native physical" in result.shadow.shadow_model
        assert result.analysis.gamma_earth_radii is None
    else:
        assert result.analysis.gamma_earth_radii == pytest.approx(
            result.shadow.gamma_earth_radii,
            abs=1.0e-12,
        )
        assert "lunar canon" in result.shadow.shadow_model


@pytest.mark.slow
def test_nasa_compat_lunar_global_fields_correlate_with_declared_eclipsewise_row(
    eclipse_calculator,
) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    source = payload["source"]
    row = payload["events"][0]
    tolerances = source["exploratory_tolerances"]
    result = eclipse_calculator.lunar_global_circumstances(
        julian_day(2026, 8, 20),
        kind=str(row["kind"]),
        mode="nasa_compat",
    )

    assert abs(
        result.greatest.jd_tt - _calendar_jd(str(row["greatest_td"]))
    ) * 86400.0 <= float(tolerances["greatest_tt_seconds"])
    assert result.shadow.gamma_earth_radii == pytest.approx(
        float(row["gamma_earth_radii"]),
        abs=float(tolerances["gamma_earth_radii"]),
    )
    assert result.shadow.penumbral_magnitude == pytest.approx(
        float(row["penumbral_magnitude"]),
        abs=float(tolerances["magnitude"]),
    )
    assert result.shadow.umbral_magnitude == pytest.approx(
        float(row["umbral_magnitude"]),
        abs=float(tolerances["magnitude"]),
    )

    for body_name in ("sun", "moon"):
        expected = row[body_name]
        actual = getattr(result, body_name)
        ra_tolerance = float(tolerances["right_ascension_arcsec"]) / 3600.0
        dec_tolerance = float(tolerances["declination_arcsec"]) / 3600.0
        assert _circular_error_deg(
            actual.right_ascension_deg,
            _sexagesimal_degrees(
                str(expected["right_ascension"]),
                hours=True,
            ),
        ) <= ra_tolerance
        assert actual.declination_deg == pytest.approx(
            _sexagesimal_degrees(str(expected["declination"])),
            abs=dec_tolerance,
        )
        assert actual.semidiameter_deg * 3600.0 == pytest.approx(
            _sexagesimal_degrees(str(expected["semidiameter"])) * 3600.0,
            abs=float(tolerances["semidiameter_arcsec"]),
        )
        assert actual.horizontal_parallax_deg * 3600.0 == pytest.approx(
            _sexagesimal_degrees(
                str(expected["horizontal_parallax"])
            ) * 3600.0,
            abs=float(tolerances["horizontal_parallax_arcsec"]),
        )

    assert result.greatest.delta_t_seconds != pytest.approx(
        float(source["delta_t_seconds"]),
        abs=0.1,
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    json.loads(
        NASA_CONTACT_FIXTURE_PATH.read_text(encoding="utf-8")
    )["events"],
    ids=lambda row: f"{row['label']} global vessel",
)
def test_lunar_global_vessel_tracks_nasa_contact_corpus_across_event_classes(
    eclipse_calculator,
    row: dict[str, object],
) -> None:
    """Bind the first-class global result to the hashed NASA figure corpus."""

    result = eclipse_calculator.lunar_global_circumstances(
        _calendar_jd(str(row["greatest_ut"])) - 10.0,
        kind=str(row["kind"]),
        mode="nasa_compat",
    )
    assert result.mode == "nasa_compat"
    assert result.ephemeris == "DE-0441LE-0441"
    eclipse_type = result.analysis.event.data.eclipse_type
    if row["kind"] == "penumbral":
        assert not any(
            (
                eclipse_type.is_partial,
                eclipse_type.is_annular,
                eclipse_type.is_total,
                eclipse_type.is_hybrid,
            )
        )
    else:
        assert getattr(eclipse_type, f"is_{row['kind']}") is True

    printed_geometry = row.get("printed_greatest_geometry")
    if isinstance(printed_geometry, dict) and "greatest_td" in printed_geometry:
        expected_greatest_tt = _calendar_jd(str(printed_geometry["greatest_td"]))
    else:
        expected_greatest_tt = _calendar_jd(str(row["greatest_ut"])) + (
            float(row["delta_t_s"]) / 86400.0
        )
    assert abs(result.greatest.jd_tt - expected_greatest_tt) * 86400.0 <= 10.0

    contacts = row["contacts_ut"]
    duration_tolerance_seconds = 2.0 * float(
        row["nasa_compat_tt_tolerance_s"]
    )
    expected_penumbral = (
        _calendar_jd(str(contacts["p4"]))
        - _calendar_jd(str(contacts["p1"]))
    ) * 86400.0
    assert result.penumbral_duration_seconds == pytest.approx(
        expected_penumbral,
        abs=duration_tolerance_seconds,
    )
    if "u1" in contacts:
        expected_partial = (
            _calendar_jd(str(contacts["u4"]))
            - _calendar_jd(str(contacts["u1"]))
        ) * 86400.0
        assert result.partial_duration_seconds == pytest.approx(
            expected_partial,
            abs=duration_tolerance_seconds,
        )
    else:
        assert result.partial_duration_seconds is None
    if "u2" in contacts:
        expected_total = (
            _calendar_jd(str(contacts["u3"]))
            - _calendar_jd(str(contacts["u2"]))
        ) * 86400.0
        assert result.total_duration_seconds == pytest.approx(
            expected_total,
            abs=duration_tolerance_seconds,
        )
    else:
        assert result.total_duration_seconds is None
