from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from moira.astrocartography import (
    fixed_star_astrocartography,
    fixed_star_astrocartography_from_chart,
    fixed_star_equatorial_subject,
)
from moira.obliquity import true_obliquity


def test_fixed_star_equatorial_subject_preserves_identity_and_true_of_date_frame() -> None:
    jd_tt = 2_451_545.0
    subject = fixed_star_equatorial_subject(
        "Sirius",
        jd_tt,
        true_obliquity(jd_tt),
    )

    assert subject.requested_name == "Sirius"
    assert subject.canonical_name == "Sirius"
    assert subject.nomenclature == "alf CMa"
    assert subject.source_kind == "sovereign"
    assert subject.source_mode == "sovereign_registry"
    assert subject.gaia_match_status == "native_registry"
    assert subject.merge_state == "native_registry"
    assert subject.observer_mode == "geocentric"
    assert subject.relation_kind == "catalog_merge"
    assert subject.relation_basis == "sovereign_registry"
    assert subject.true_position is True
    assert subject.is_topocentric is False
    assert subject.position_source == "moira.stars.star_at:ecliptic_to_equatorial"
    assert 0.0 <= subject.right_ascension < 360.0
    assert -90.0 <= subject.declination <= 90.0


def test_fixed_star_astrocartography_returns_full_line_and_point_parity() -> None:
    result = fixed_star_astrocartography(
        ("Sirius", "Regulus"),
        jd_ut=2_451_544.9992,
        jd_tt=2_451_545.0,
        lat_step=10.0,
    )

    assert result.computation_truth.requested_names == ("Sirius", "Regulus")
    assert result.computation_truth.canonical_names == ("Sirius", "Regulus")
    assert result.computation_truth.coordinate_frame == "true_equator_and_equinox_of_date"
    assert result.computation_truth.interpretation == "none_geometry_only"
    assert len(result.lines) == 8
    assert len(result.subplanetary_points) == 4
    for name in ("Sirius", "Regulus"):
        assert {line.line_type for line in result.lines if line.planet == name} == {
            "MC",
            "IC",
            "ASC",
            "DSC",
        }
        assert {
            point.point_type
            for point in result.subplanetary_points
            if point.planet == name
        } == {"Zenith", "Nadir"}

    with pytest.raises(ValueError, match="exactly one MC/IC/ASC/DSC"):
        replace(result, lines=(result.lines[0],) * len(result.lines))


def test_fixed_star_astrocartography_rejects_alias_identity_collisions() -> None:
    with pytest.raises(ValueError, match="duplicate canonical identities"):
        fixed_star_astrocartography(
            ("Mizar", "zet01 UMa"),
            jd_ut=2_451_544.9992,
            jd_tt=2_451_545.0,
        )


def test_fixed_star_astrocartography_chart_wrapper_requires_explicit_tt() -> None:
    with pytest.raises(TypeError, match="explicit jd_ut and jd_tt"):
        fixed_star_astrocartography_from_chart(
            SimpleNamespace(jd_ut=2_451_544.9992),
            ("Sirius",),
        )

    result = fixed_star_astrocartography_from_chart(
        SimpleNamespace(jd_ut=2_451_544.9992, jd_tt=2_451_545.0),
        ("Sirius",),
        lat_step=20.0,
    )
    assert result.subjects[0].canonical_name == "Sirius"


def test_fixed_star_astrocartography_rejects_boolean_numeric_inputs() -> None:
    with pytest.raises(ValueError, match="jd_ut and jd_tt must be finite"):
        fixed_star_astrocartography(
            ("Sirius",),
            jd_ut=True,
            jd_tt=2_451_545.0,
        )
    with pytest.raises(ValueError, match="sequence of names"):
        fixed_star_astrocartography(
            "Sirius",
            jd_ut=2_451_544.9992,
            jd_tt=2_451_545.0,
        )
