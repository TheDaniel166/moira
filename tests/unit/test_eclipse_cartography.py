from __future__ import annotations

import pytest

from moira.eclipse_cartography import _solar_site_maximum
from moira.julian import julian_day


@pytest.mark.slow
def test_scalar_site_solver_reproduces_global_site_product(
    eclipse_calculator,
) -> None:
    global_result = eclipse_calculator.solar_global_circumstances(
        julian_day(2027, 7, 20),
        kind="total",
    )
    sample = _solar_site_maximum(
        eclipse_calculator,
        global_result,
        global_result.greatest.latitude_deg,
        global_result.greatest.longitude_deg,
        time_samples=17,
    )
    assert sample.visible is True
    assert sample.local_class == "total"
    assert sample.magnitude >= global_result.greatest.magnitude
    assert sample.magnitude == pytest.approx(
        global_result.greatest.magnitude,
        abs=2.0e-5,
    )
    assert sample.obscuration == 1.0
    assert sample.magnitude_jd_ut1 == pytest.approx(
        global_result.event.jd_ut,
        abs=4.0e-3,
    )


@pytest.mark.slow
def test_cartography_emits_separate_magnitude_and_obscuration_components(
    eclipse_calculator,
) -> None:
    result = eclipse_calculator.solar_eclipse_cartography(
        julian_day(2027, 7, 20),
        kind="total",
        magnitude_levels=(0.2, 0.8),
        obscuration_levels=(0.2, 0.8),
        mesh_depth=0,
        time_samples=9,
    )
    assert len(result.samples) == 12
    assert 0 < sum(sample.visible for sample in result.samples) < len(result.samples)
    assert [level.threshold for level in result.magnitude_levels] == [0.2, 0.8]
    assert [level.threshold for level in result.obscuration_levels] == [0.2, 0.8]
    assert all(level.quantity == "magnitude" for level in result.magnitude_levels)
    assert all(
        level.quantity == "obscuration"
        for level in result.obscuration_levels
    )
    assert all(
        component.closed
        for level in (*result.magnitude_levels, *result.obscuration_levels)
        for component in level.components
    )
    assert result.duration_contours_available is False
    assert result.projection == "SPHERICAL_GEOGRAPHIC"
    assert result.achieved_mesh_depth == 0
    assert result.mesh_triangle_count == 20
    assert result.converged is (result.unresolved_edge_count == 0)


@pytest.mark.slow
def test_cartography_refines_only_edges_that_fail_declared_criteria(
    eclipse_calculator,
) -> None:
    result = eclipse_calculator.solar_eclipse_cartography(
        julian_day(2027, 7, 20),
        kind="total",
        magnitude_levels=(0.2, 0.8),
        obscuration_levels=(0.2, 0.8),
        mesh_depth=1,
        time_samples=9,
        angular_tolerance_deg=40.0,
        field_tolerance=0.05,
    )
    assert result.achieved_mesh_depth == 1
    assert 12 < len(result.samples) < 42
    assert 20 < result.mesh_triangle_count < 80
    assert result.unresolved_edge_count > 0
    assert result.converged is False
    assert all(
        abs(right[1] - left[1]) <= 180.0
        for level in (*result.magnitude_levels, *result.obscuration_levels)
        for component in level.components
        for left, right in zip(component.points, component.points[1:])
    )


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"magnitude_levels": ()}, ValueError),
        ({"magnitude_levels": (0.8, 0.2)}, ValueError),
        ({"obscuration_levels": (0.0,)}, ValueError),
        ({"mesh_depth": True}, TypeError),
        ({"mesh_depth": 4}, ValueError),
        ({"time_samples": 10}, ValueError),
        ({"angular_tolerance_deg": 0.0}, ValueError),
        ({"field_tolerance": 0.5}, ValueError),
    ],
)
def test_cartography_rejects_ambiguous_or_unbounded_policy_inputs(
    eclipse_calculator,
    kwargs: dict[str, object],
    error: type[Exception],
) -> None:
    options = {
        "mesh_depth": 0,
        "time_samples": 9,
        "magnitude_levels": (0.2,),
        "obscuration_levels": (0.2,),
        "angular_tolerance_deg": 8.0,
        "field_tolerance": 0.01,
    }
    options.update(kwargs)
    with pytest.raises(error):
        eclipse_calculator.solar_eclipse_cartography(
            julian_day(2027, 7, 20),
            kind="total",
            **options,
        )
