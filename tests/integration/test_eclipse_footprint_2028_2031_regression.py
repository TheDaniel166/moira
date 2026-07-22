"""Dated regressions for horizon-adjacent penumbral envelope seeds."""

from __future__ import annotations

import pytest

import moira.eclipse as eclipse_module
from moira.eclipse import (
    SolarEclipseFootprintBoundaryKind,
    SolarEclipseFootprintTopology,
)


@pytest.mark.slow
@pytest.mark.parametrize(
    ("seed_jd", "expected_topology", "expected_structure"),
    (
        (
            2_461_797.1,
            SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH: ((0, 0), (0, 1)),
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH: ((0, 0), (0, 1)),
            },
        ),
        (
            2_462_299.0,
            SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED,
            {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH: (
                    (0, 0),
                    (0, 1),
                    (0, 2),
                ),
            },
        ),
        (
            2_462_830.0,
            SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH: (
                    (0, 0),
                    (0, 1),
                    (0, 2),
                ),
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH: ((0, 0), (0, 1)),
            },
        ),
        (
            2_463_007.0,
            SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
            {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH: ((0, 0),),
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH: (
                    (0, 0),
                    (0, 1),
                    (0, 2),
                ),
            },
        ),
    ),
)
def test_horizon_adjacent_envelope_seeds_preserve_complete_components(
    eclipse_calculator,
    seed_jd: float,
    expected_topology: SolarEclipseFootprintTopology,
    expected_structure: dict[
        SolarEclipseFootprintBoundaryKind,
        tuple[tuple[int, int], ...],
    ],
) -> None:
    footprint = eclipse_calculator.solar_eclipse_footprint(
        seed_jd,
        sample_count=9,
    )

    assert footprint.topology is expected_topology
    actual_structure = {
        kind: tuple(
            (track.component_id, track.segment_id)
            for track in footprint.tracks
            if track.kind is kind
        )
        for kind in expected_structure
    }
    assert actual_structure == expected_structure


@pytest.mark.slow
def test_native_envelope_candidates_match_python_across_2028_event_slices(
    eclipse_calculator,
    monkeypatch,
) -> None:
    derivative_step = eclipse_module._SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS
    for epoch in (
        2_461_797.02,
        2_461_797.06,
        2_461_797.10,
        2_461_797.14,
        2_461_797.18,
    ):
        shadow, before, after = (
            eclipse_module._earth_fixed_solar_shadow(eclipse_calculator, sample_epoch)
            for sample_epoch in (
                epoch,
                epoch - derivative_step,
                epoch + derivative_step,
            )
        )
        assert shadow is not None
        assert before is not None
        assert after is not None
        native = eclipse_module._penumbral_envelope_points(shadow, before, after)
        with monkeypatch.context() as context:
            context.setattr(
                eclipse_module._moira_native,
                "penumbral_envelope_candidates",
                None,
            )
            python = eclipse_module._penumbral_envelope_points(
                shadow,
                before,
                after,
            )

        assert native.keys() == python.keys()
        for kind in native:
            assert len(native[kind]) == len(python[kind])
            for native_point, python_point in zip(native[kind], python[kind]):
                assert native_point.azimuth_rad == pytest.approx(
                    python_point.azimuth_rad,
                    abs=1.0e-14,
                )
                assert native_point.xyz_itrf_km == pytest.approx(
                    python_point.xyz_itrf_km,
                    abs=1.0e-12,
                )
                assert native_point.latitude_deg == pytest.approx(
                    python_point.latitude_deg,
                    abs=1.0e-12,
                )
                assert native_point.longitude_deg == pytest.approx(
                    python_point.longitude_deg,
                    abs=1.0e-12,
                )
                assert native_point.signed_half_chord_sq_km2 == pytest.approx(
                    python_point.signed_half_chord_sq_km2,
                    abs=1.0e-12,
                )


@pytest.mark.slow
def test_native_lawful_intervals_match_python_across_2028_event_slices(
    eclipse_calculator,
    monkeypatch,
) -> None:
    for epoch in (
        2_461_797.02,
        2_461_797.06,
        2_461_797.10,
        2_461_797.14,
        2_461_797.18,
    ):
        shadow = eclipse_module._earth_fixed_solar_shadow(
            eclipse_calculator,
            epoch,
        )
        assert shadow is not None
        native = eclipse_module._penumbral_lawful_azimuth_interval(shadow)
        with monkeypatch.context() as context:
            context.setattr(
                eclipse_module._moira_native,
                "penumbral_lawful_azimuth_interval",
                None,
            )
            python = eclipse_module._penumbral_lawful_azimuth_interval(shadow)

        assert native[:2] == pytest.approx(python[:2], abs=1.0e-14)
        assert native[2] is python[2]
