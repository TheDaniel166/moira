from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import math
from types import SimpleNamespace

import pytest

import moira.lunar_occultation_contacts as contacts_module
from moira.julian import calendar_datetime_from_jd, datetime_from_jd
from moira.lunar_limb import (
    LunarLimbAssetIdentity,
    LunarLimbEventProfile,
    LunarLimbProfileSlice,
    LunarLimbProfileSource,
)
from moira.lunar_occultation_contacts import (
    ContactGeometry,
    ContactSearchPolicy,
    LunarContactGeometryMode,
    LunarContactProfilePolicy,
    LunarContactStar,
    LunarContactKind,
    LunarOccultationContact,
    LunarOccultationContactSequence,
    LunarVisibilityState,
    _contact_klioner_deflected_unit_direction,
    _observer_star_icrf_direction,
    _reader_bound_deflected_star_icrf_direction,
    _refine_crossing,
    _solve_signed_clearance_contacts,
    _validate_star_reference_epoch,
    lunar_contact_star_at,
    lunar_star_topographic_contacts,
    prepare_lola_rdr_lunar_star_contact_profile,
)


J2000 = 2_451_545.0


def _star(*, epoch: float = J2000, parallax_mas: float | None = 10.0) -> LunarContactStar:
    barycentric_distance_km = (
        None
        if parallax_mas is None
        else (1000.0 / parallax_mas) * 206_264.80624709636 * 149_597_870.7
    )
    return LunarContactStar(
        name="Synthetic",
        nomenclature="HIP 1",
        catalog_source="synthetic unit-test catalog",
        catalog_identifier="HIP 1",
        lookup_kind="exact",
        reference_epoch_jd_tt=epoch,
        barycentric_icrf_unit=(1.0, 0.0, 0.0),
        parallax_mas=parallax_mas,
        barycentric_distance_km=barycentric_distance_km,
    )


class PreparedProfile:
    model_name = "TEST_VALLEY_PRESERVING_PROFILE"
    provenance = "synthetic unit-test profile"

    def adjustment_deg(
        self,
        jd_ut1: float,
        observer_latitude_deg: float,
        observer_longitude_deg: float,
        observer_elevation_m: float,
        position_angle_deg: float,
        moon_distance_km: float,
    ) -> float:
        return 0.0


def _seconds(jd_ut1: float) -> float:
    return (jd_ut1 - J2000) * 86_400.0


def _policy(**overrides: object) -> ContactSearchPolicy:
    values: dict[str, object] = {
        "scan_step_seconds": 0.05,
        "time_tolerance_seconds": 0.0005,
        "clearance_tolerance_deg": 1.0e-7,
        "tangency_tolerance_deg": 2.0e-7,
        "plateau_tolerance_deg": 1.0e-12,
        "chronology_tolerance_seconds": 0.001,
    }
    values.update(overrides)
    return ContactSearchPolicy(**values)  # type: ignore[arg-type]


def _contact(
    *,
    jd_ut1: float = J2000 + 1.0 / 86_400.0,
    kind: LunarContactKind = LunarContactKind.DISAPPEARANCE,
    before: LunarVisibilityState = LunarVisibilityState.VISIBLE,
    after: LunarVisibilityState = LunarVisibilityState.OCCULTED,
    signed_clearance_deg: float = 0.0,
    bracket_half_width_seconds: float = 0.0001,
) -> LunarOccultationContact:
    return LunarOccultationContact(
        jd_ut1=jd_ut1,
        kind=kind,
        visibility_before=before,
        visibility_after=after,
        position_angle_deg=123.0,
        signed_clearance_deg=signed_clearance_deg,
        bracket_start_jd_ut1=(
            jd_ut1 - bracket_half_width_seconds / 86_400.0
        ),
        bracket_end_jd_ut1=(
            jd_ut1 + bracket_half_width_seconds / 86_400.0
        ),
    )


def _sequence(
    contact_values: tuple[LunarOccultationContact, ...],
    *,
    initial: LunarVisibilityState = LunarVisibilityState.VISIBLE,
    final: LunarVisibilityState = LunarVisibilityState.OCCULTED,
    policy: ContactSearchPolicy | None = None,
) -> LunarOccultationContactSequence:
    return LunarOccultationContactSequence(
        star=_star(),
        observer_latitude_deg=31.5,
        observer_longitude_deg=-99.9,
        observer_elevation_m=500.0,
        jd_start_ut1=J2000,
        jd_end_ut1=J2000 + 4.0 / 86_400.0,
        initial_visibility=initial,
        final_visibility=final,
        contacts=contact_values,
        profile_model="TEST_VALLEY_PRESERVING_PROFILE",
        profile_provenance="synthetic unit-test profile",
        policy=_policy() if policy is None else policy,
        geometry_mode=LunarContactGeometryMode.CALLER_INJECTED,
        geometry_provenance="synthetic unit-test geometry",
    )


def _structured_event_profile() -> tuple[
    LunarLimbEventProfile,
    LunarLimbProfileSource,
]:
    asset_url = "https://example.invalid/official-lola-tile.laz"
    source = LunarLimbProfileSource(
        authority="USGS Astrogeology LOLA STAC",
        collection="lunar_orbiter_laser_altimeter",
        coordinate_frame="IAU_2015 Moon ME",
        translation_model="fixture DE441/LE441",
        orientation_model="NAIF moon_pa_de440_200625",
        surface_frame_model="fixture DE421 ME",
        orientation_alignment_max_m=0.5,
        orientation_alignment_interval="fixture interval",
        reference_radius_km=1737.4,
        spatial_query_half_width_km=10.0,
        spatial_query_bounds_moon_xyz_km=(
            (-10.0, -8.0, -6.0),
            (10.0, 8.0, 6.0),
        ),
        relief_observation_sources=("fixture relief authority",),
        relief_observed_highest_km=9.0,
        relief_observed_approximate_absolute_km=9.5,
        relief_acquisition_policy="fixture complete bounded relief shell",
        max_absolute_relief_km=10.0,
        assets=(LunarLimbAssetIdentity(asset_url, 1, "0" * 64),),
    )

    def profile_slice(jd_ut1: float) -> LunarLimbProfileSlice:
        return LunarLimbProfileSlice(
            jd_ut1=jd_ut1,
            position_angles_unwrapped_deg=(100.0, 101.0),
            radii_km=(1737.3, 1737.5),
            bin_width_deg=1.0,
            max_interpolation_gap_deg=1.0,
            source_point_count=2,
            asset_urls=(asset_url,),
        )

    return (
        LunarLimbEventProfile(
            source=source,
            slices=(
                profile_slice(J2000),
                profile_slice(J2000 + 4.0 / 86_400.0),
            ),
            max_time_interpolation_gap_days=4.0 / 86_400.0,
            observer_latitude_deg=31.5,
            observer_longitude_deg=-99.9,
            observer_elevation_m=0.0,
        ),
        source,
    )


def test_solver_preserves_a_narrow_disappearance_reappearance_pair() -> None:
    def clearance(jd_ut1: float) -> float:
        seconds = _seconds(jd_ut1)
        return 1.0e-4 * (seconds - 2.0) * (seconds - 2.25)

    initial, final, solved = _solve_signed_clearance_contacts(
        J2000,
        J2000 + 4.0 / 86_400.0,
        clearance,
        _policy(),
    )

    assert initial is LunarVisibilityState.VISIBLE
    assert final is LunarVisibilityState.VISIBLE
    assert [item.kind for item in solved] == [
        LunarContactKind.DISAPPEARANCE,
        LunarContactKind.REAPPEARANCE,
    ]
    solved_seconds = [_seconds(item.jd_ut1) for item in solved]
    assert solved_seconds == pytest.approx([2.0, 2.25], abs=0.001)
    assert solved_seconds[1] - solved_seconds[0] > 0.24


def test_solver_fails_closed_when_exact_sample_hides_a_subscan_pair() -> None:
    policy = _policy(
        scan_step_seconds=0.005,
        time_tolerance_seconds=0.0005,
    )
    exact_sample_jd = J2000 + 2.0 * policy.scan_step_seconds / 86_400.0

    def clearance(jd_ut1: float) -> float:
        seconds_from_sample = (jd_ut1 - exact_sample_jd) * 86_400.0
        return seconds_from_sample * (seconds_from_sample - 0.001)

    with pytest.raises(
        ValueError,
        match="exact sampled zero contains an unresolved sub-scan",
    ):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 0.025 / 86_400.0,
            clearance,
            policy,
        )


@pytest.mark.parametrize(
    ("shape", "expected_kind", "initial", "final"),
    [
        (
            "crossing",
            LunarContactKind.REAPPEARANCE,
            LunarVisibilityState.OCCULTED,
            LunarVisibilityState.VISIBLE,
        ),
        (
            "tangency",
            LunarContactKind.TANGENCY,
            LunarVisibilityState.VISIBLE,
            LunarVisibilityState.VISIBLE,
        ),
    ],
)
def test_solver_preserves_lawful_exact_sampled_zero(
    shape: str,
    expected_kind: LunarContactKind,
    initial: LunarVisibilityState,
    final: LunarVisibilityState,
) -> None:
    policy = _policy(
        scan_step_seconds=0.005,
        time_tolerance_seconds=0.0005,
    )
    exact_sample_jd = J2000 + 2.0 * policy.scan_step_seconds / 86_400.0

    def clearance(jd_ut1: float) -> float:
        seconds_from_sample = (jd_ut1 - exact_sample_jd) * 86_400.0
        if shape == "crossing":
            return seconds_from_sample
        return seconds_from_sample * seconds_from_sample

    actual_initial, actual_final, solved = _solve_signed_clearance_contacts(
        J2000,
        J2000 + 0.025 / 86_400.0,
        clearance,
        policy,
    )

    assert actual_initial is initial
    assert actual_final is final
    assert len(solved) == 1
    assert solved[0].kind is expected_kind
    assert solved[0].jd_ut1 == exact_sample_jd


def test_solver_refines_a_shallow_crossing_to_the_time_tolerance() -> None:
    """A small clearance residual cannot substitute for a tight time bracket."""

    crossing_second = 10.037

    def clearance(jd_ut1: float) -> float:
        return 3.0e-8 * (_seconds(jd_ut1) - crossing_second)

    policy = _policy(clearance_tolerance_deg=1.0e-9)
    _initial, _final, solved = _solve_signed_clearance_contacts(
        J2000,
        J2000 + 20.0 / 86_400.0,
        clearance,
        policy,
    )

    assert len(solved) == 1
    assert solved[0].kind is LunarContactKind.REAPPEARANCE
    assert _seconds(solved[0].jd_ut1) == pytest.approx(
        crossing_second,
        abs=0.001,
    )
    assert (
        solved[0].bracket_end_jd_ut1 - solved[0].bracket_start_jd_ut1
    ) * 86_400.0 <= policy.time_tolerance_seconds
    assert abs(clearance(solved[0].jd_ut1)) <= policy.clearance_tolerance_deg


def test_crossing_refinement_meets_time_and_achievable_steep_residual() -> None:
    root_second = 10.23883
    slope_deg_per_second = 1.0e-3

    def clearance(jd_ut1: float) -> float:
        return slope_deg_per_second * (_seconds(jd_ut1) - root_second)

    left = J2000 + 10.2 / 86_400.0
    right = J2000 + 10.3 / 86_400.0
    policy = _policy(clearance_tolerance_deg=1.0e-7)
    jd_ut1, residual, refined_left, refined_right = _refine_crossing(
        clearance,
        left,
        right,
        clearance(left),
        clearance(right),
        policy,
    )

    assert refined_left <= jd_ut1 <= refined_right
    assert (refined_right - refined_left) * 86_400.0 <= (
        policy.time_tolerance_seconds
    )
    assert residual == clearance(jd_ut1)
    assert abs(residual) <= policy.clearance_tolerance_deg


def test_crossing_refinement_fails_when_binary64_cannot_meet_residual() -> None:
    left = J2000
    right = math.nextafter(left, math.inf)

    def discontinuous_clearance(jd_ut1: float) -> float:
        return -1.0 if jd_ut1 == left else 1.0

    policy = _policy(clearance_tolerance_deg=1.0e-7)
    with pytest.raises(
        RuntimeError,
        match="binary64 Julian-Day resolution",
    ):
        _refine_crossing(
            discontinuous_clearance,
            left,
            right,
            -1.0,
            1.0,
            policy,
        )


def test_crossing_refinement_fails_when_iteration_budget_cannot_meet_both() -> None:
    root_second = 0.314159

    def clearance(jd_ut1: float) -> float:
        return 1.0e-6 * (_seconds(jd_ut1) - root_second)

    left = J2000
    right = J2000 + 1.0 / 86_400.0
    policy = _policy(
        time_tolerance_seconds=0.0001,
        max_refine_iterations=8,
    )
    with pytest.raises(RuntimeError, match="max_refine_iterations"):
        _refine_crossing(
            clearance,
            left,
            right,
            clearance(left),
            clearance(right),
            policy,
        )


@pytest.mark.parametrize(
    ("sign", "state"),
    [
        (1.0, LunarVisibilityState.VISIBLE),
        (-1.0, LunarVisibilityState.OCCULTED),
    ],
)
def test_solver_detects_off_grid_same_sign_tangency_without_flipping_state(
    sign: float,
    state: LunarVisibilityState,
) -> None:
    tangent_second = 2.013

    def clearance(jd_ut1: float) -> float:
        return sign * (_seconds(jd_ut1) - tangent_second) ** 2

    initial, final, solved = _solve_signed_clearance_contacts(
        J2000,
        J2000 + 4.0 / 86_400.0,
        clearance,
        _policy(),
    )

    assert initial is state
    assert final is state
    assert len(solved) == 1
    assert solved[0].kind is LunarContactKind.TANGENCY
    assert solved[0].visibility_before is state
    assert solved[0].visibility_after is state
    assert _seconds(solved[0].jd_ut1) == pytest.approx(tangent_second, abs=0.001)
    assert (
        solved[0].bracket_end_jd_ut1 - solved[0].bracket_start_jd_ut1
    ) * 86_400.0 <= _policy().time_tolerance_seconds


@pytest.mark.parametrize(
    ("sign", "state", "curvature_deg_per_second_squared"),
    [
        (1.0, LunarVisibilityState.VISIBLE, 5.0e-8),
        (-1.0, LunarVisibilityState.OCCULTED, 5.0e-8),
        (1.0, LunarVisibilityState.VISIBLE, 2.0e-8),
        (-1.0, LunarVisibilityState.OCCULTED, 2.0e-8),
    ],
)
def test_solver_admits_a_physical_scale_shallow_unique_tangency(
    sign: float,
    state: LunarVisibilityState,
    curvature_deg_per_second_squared: float,
) -> None:
    """Millisecond closeness to zero is not evidence of a flat minimum."""

    tangent_second = 4.0013

    def clearance(jd_ut1: float) -> float:
        offset_seconds = _seconds(jd_ut1) - tangent_second
        return sign * curvature_deg_per_second_squared * offset_seconds**2

    policy = _policy(
        scan_step_seconds=0.005,
        time_tolerance_seconds=0.001,
    )
    initial, final, solved = _solve_signed_clearance_contacts(
        J2000,
        J2000 + 8.0 / 86_400.0,
        clearance,
        policy,
    )

    assert initial is state
    assert final is state
    assert len(solved) == 1
    assert solved[0].kind is LunarContactKind.TANGENCY
    assert solved[0].visibility_before is state
    assert solved[0].visibility_after is state
    assert _seconds(solved[0].jd_ut1) == pytest.approx(
        tangent_second,
        abs=policy.time_tolerance_seconds,
    )


@pytest.mark.parametrize("tangent_second", (0.0052, 0.0098))
def test_solver_keeps_near_boundary_tangency_probes_inside_search_window(
    tangent_second: float,
) -> None:
    """A large lawful time tolerance must not widen probes past the window."""

    jd_start = J2000
    jd_end = J2000 + 0.015 / 86_400.0
    evaluated_epochs: list[float] = []

    def clearance(jd_ut1: float) -> float:
        assert jd_start <= jd_ut1 <= jd_end
        evaluated_epochs.append(jd_ut1)
        seconds = (jd_ut1 - jd_start) * 86_400.0
        return 0.01 * (seconds - tangent_second) ** 2

    initial, final, solved = _solve_signed_clearance_contacts(
        jd_start,
        jd_end,
        clearance,
        _policy(
            scan_step_seconds=0.005,
            time_tolerance_seconds=0.004,
            chronology_tolerance_seconds=0.001,
        ),
    )

    assert initial is LunarVisibilityState.VISIBLE
    assert final is LunarVisibilityState.VISIBLE
    assert len(solved) == 1
    assert solved[0].kind is LunarContactKind.TANGENCY
    assert solved[0].visibility_before is LunarVisibilityState.VISIBLE
    assert solved[0].visibility_after is LunarVisibilityState.VISIBLE
    assert min(evaluated_epochs) >= jd_start
    assert max(evaluated_epochs) <= jd_end


@pytest.mark.parametrize("collapsed_side", ("left", "right"))
def test_solver_fails_closed_without_representable_two_sided_tangency_probes(
    monkeypatch: pytest.MonkeyPatch,
    collapsed_side: str,
) -> None:
    def clearance(jd_ut1: float) -> float:
        return (_seconds(jd_ut1) - 0.503) ** 2

    def collapsed_refinement(
        _objective: object,
        left_jd: float,
        right_jd: float,
        _policy_value: ContactSearchPolicy,
    ) -> tuple[float, float, float, float]:
        collapsed_jd = left_jd if collapsed_side == "left" else right_jd
        return collapsed_jd, 0.0, collapsed_jd, collapsed_jd

    monkeypatch.setattr(
        contacts_module,
        "_refine_tangency",
        collapsed_refinement,
    )

    with pytest.raises(ValueError, match="no two-sided local search bracket"):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 1.0 / 86_400.0,
            clearance,
            _policy(),
        )


@pytest.mark.parametrize("sign", (1.0, -1.0))
def test_solver_fails_closed_on_subscan_opposite_state_excursion(sign: float) -> None:
    """A real unresolved crossing pair must never be emitted as tangency."""

    def clearance(jd_ut1: float) -> float:
        seconds = _seconds(jd_ut1)
        return sign * (seconds - 0.503) * (seconds - 0.505)

    with pytest.raises(
        ValueError,
        match="unresolved sub-scan opposite-state excursion",
    ):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 1.0 / 86_400.0,
            clearance,
            ContactSearchPolicy(),
        )


def test_solver_rejects_distinct_close_tangencies_with_disjoint_brackets() -> None:
    first_tangent_second = 1.013
    second_tangent_second = 1.213

    def clearance(jd_ut1: float) -> float:
        seconds = _seconds(jd_ut1)
        return (
            (seconds - first_tangent_second)
            * (seconds - second_tangent_second)
        ) ** 2

    with pytest.raises(
        ValueError,
        match="distinct contacts are closer than chronology_tolerance_seconds",
    ):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 3.0 / 86_400.0,
            clearance,
            _policy(chronology_tolerance_seconds=0.25),
        )


def test_solver_does_not_promote_an_off_limb_local_minimum_to_tangency() -> None:
    def clearance(jd_ut1: float) -> float:
        return (_seconds(jd_ut1) - 2.013) ** 2 + 1.0e-5

    initial, final, solved = _solve_signed_clearance_contacts(
        J2000,
        J2000 + 4.0 / 86_400.0,
        clearance,
        _policy(),
    )

    assert initial is LunarVisibilityState.VISIBLE
    assert final is LunarVisibilityState.VISIBLE
    assert solved == ()


def test_solver_rejects_nonfinite_objective_values() -> None:
    def clearance(jd_ut1: float) -> float:
        return math.nan if _seconds(jd_ut1) > 1.0 else 1.0

    with pytest.raises(ValueError, match="signed clearance objective must be finite"):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 4.0 / 86_400.0,
            clearance,
            _policy(),
        )


@pytest.mark.parametrize("plateau_clearance_deg", (0.0, 1.0e-8))
def test_solver_rejects_a_flat_clearance_plateau(
    plateau_clearance_deg: float,
) -> None:
    def clearance(jd_ut1: float) -> float:
        seconds = _seconds(jd_ut1)
        if 1.9 <= seconds <= 2.1:
            return plateau_clearance_deg
        distance_from_plateau = min(abs(seconds - 1.9), abs(seconds - 2.1))
        return plateau_clearance_deg + distance_from_plateau**2

    with pytest.raises(ValueError, match="no unique"):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 4.0 / 86_400.0,
            clearance,
            _policy(),
        )


def test_solver_rejects_contact_at_open_window_endpoint() -> None:
    with pytest.raises(ValueError, match="endpoint-ambiguous"):
        _solve_signed_clearance_contacts(
            J2000,
            J2000 + 4.0 / 86_400.0,
            lambda jd_ut1: _seconds(jd_ut1),
            _policy(),
        )


def test_solver_rejects_a_scan_step_that_cannot_advance_at_large_jd() -> None:
    policy = _policy(
        scan_step_seconds=0.0001,
        time_tolerance_seconds=0.00001,
        chronology_tolerance_seconds=0.00002,
        max_scan_samples=1_000,
    )
    start = 40_000_000.0
    end = start + 0.01 / 86_400.0
    with pytest.raises(RuntimeError, match="scan cannot advance"):
        _solve_signed_clearance_contacts(start, end, lambda _jd: 1.0, policy)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("scan_step_seconds", 0.0, "greater than zero"),
        ("time_tolerance_seconds", 0.1, "smaller than"),
        ("tangency_tolerance_deg", math.inf, "finite"),
        ("max_refine_iterations", 7, "at least 8"),
        ("max_scan_samples", True, "must be int"),
    ],
)
def test_contact_search_policy_rejects_ambiguous_values(
    field: str,
    value: object,
    expected: str,
) -> None:
    values: dict[str, object] = {
        "scan_step_seconds": 0.1,
        "time_tolerance_seconds": 0.001,
        "tangency_tolerance_deg": 2.0e-7,
        "max_refine_iterations": 96,
        "max_scan_samples": 250_000,
    }
    values[field] = value
    with pytest.raises((TypeError, ValueError), match=expected):
        ContactSearchPolicy(**values)  # type: ignore[arg-type]


def test_default_contact_profile_policy_owns_resolution_bounds() -> None:
    search = ContactSearchPolicy()
    profile = LunarContactProfilePolicy()

    assert search.scan_step_seconds == 0.01
    assert search.time_tolerance_seconds == 0.001
    assert search.clearance_tolerance_deg == 1.0e-7
    assert profile.profile_time_step_seconds == 15.0
    assert profile.pa_bin_width_deg == 0.002
    assert profile.max_pa_interpolation_gap_deg == 0.002


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("profile_time_step_seconds", 0.0, "greater than zero"),
        ("pa_bin_width_deg", 1.0, "less than 1 degree"),
        ("max_pa_interpolation_gap_deg", 0.001, "at least one PA bin"),
    ],
)
def test_contact_profile_policy_rejects_unbounded_resolution(
    field: str,
    value: float,
    expected: str,
) -> None:
    values = {
        "profile_time_step_seconds": 15.0,
        "pa_bin_width_deg": 0.002,
        "max_pa_interpolation_gap_deg": 0.002,
    }
    values[field] = value
    with pytest.raises(ValueError, match=expected):
        LunarContactProfilePolicy(**values)


def test_named_contact_star_is_registry_propagated_and_content_identified() -> None:
    at_catalog_epoch = lunar_contact_star_at("Spica", J2000)
    propagated = lunar_contact_star_at("Spica", J2000 + 10.0 * 365.25)

    assert propagated.name == "Spica"
    assert propagated.nomenclature == "alf Vir"
    assert "star_registry.csv" in propagated.catalog_source
    assert "HIP 65474" in propagated.catalog_identifier
    assert "Gaia DR3 0" not in propagated.catalog_identifier
    assert propagated.coordinate_frame == "ICRS"
    assert propagated.origin == "SOLAR_SYSTEM_BARYCENTER"
    assert propagated.reference_time_scale == "TT"
    assert propagated.parallax_mas == pytest.approx(13.06)
    assert propagated.barycentric_distance_km is not None
    assert propagated.barycentric_distance_km != pytest.approx(
        at_catalog_epoch.barycentric_distance_km,
        abs=1.0,
    )
    assert math.sqrt(
        sum(value * value for value in propagated.barycentric_icrf_unit)
    ) == pytest.approx(1.0, abs=1.0e-15)
    assert propagated.barycentric_icrf_unit != pytest.approx(
        at_catalog_epoch.barycentric_icrf_unit,
        abs=1.0e-9,
    )


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"coordinate_frame": "TRUE_ECLIPTIC_OF_DATE"}, "coordinate_frame"),
        ({"origin": "EARTH_CENTER"}, "origin"),
        ({"reference_time_scale": "UT1"}, "reference_time_scale"),
        ({"reference_epoch_jd_tt": math.nan}, "reference_epoch_jd_tt"),
        ({"barycentric_icrf_unit": (2.0, 0.0, 0.0)}, "normalized"),
        ({"parallax_mas": 0.0}, "positive"),
        ({"barycentric_distance_km": 0.0}, "positive"),
        (
            {"parallax_mas": None, "barycentric_distance_km": 1.0},
            "must be None",
        ),
    ],
)
def test_contact_star_rejects_ambiguous_frame_epoch_and_distance_contracts(
    changes: dict[str, object],
    expected: str,
) -> None:
    with pytest.raises(ValueError, match=expected):
        replace(_star(), **changes)


def test_contact_star_is_frozen() -> None:
    star = _star()
    with pytest.raises(FrozenInstanceError):
        star.reference_epoch_jd_tt = J2000 + 1.0  # type: ignore[misc]


def test_topographic_contact_surface_remains_direct_import_only() -> None:
    import moira
    import moira.facade as facade_module

    direct_only_names = {
        "LunarContactGeometryMode",
        "LunarContactStar",
        "LunarOccultationContact",
        "LunarOccultationContactSequence",
        "lunar_contact_star_at",
        "lunar_star_topographic_contacts",
        "prepare_lola_rdr_lunar_star_contact_profile",
    }

    assert direct_only_names.isdisjoint(moira.__all__)
    assert direct_only_names.isdisjoint(facade_module.__all__)
    assert all(not hasattr(moira, name) for name in direct_only_names)
    assert all(not hasattr(facade_module.Moira, name) for name in direct_only_names)


def test_catalog_parallax_uses_complete_observer_ssb_translation() -> None:
    star = _star(parallax_mas=1000.0)  # one parsec
    observer = (0.0, _AU_KM := 149_597_870.7, 6_378.0)

    direction = _observer_star_icrf_direction(star, observer)
    expected_y = -1.0 / 206_264.80624709636

    assert direction[0] == pytest.approx(1.0, abs=2.0e-11)
    assert direction[1] == pytest.approx(expected_y, rel=2.0e-10)
    assert direction[2] == pytest.approx(
        -6_378.0 / (_AU_KM * 206_264.80624709636),
        rel=2.0e-10,
    )
    assert _observer_star_icrf_direction(
        _star(parallax_mas=None), observer
    ) == (1.0, 0.0, 0.0)


def test_contact_klioner_helper_matches_erfa_ld_with_exact_finite_q() -> None:
    erfa = pytest.importorskip("erfa")
    from moira.corrections import SCHWARZSCHILD_RADII

    observer_to_source = (0.3, 0.4, math.sqrt(0.75))
    raw_deflector_to_source = (0.2, -0.5, math.sqrt(0.71))
    q_norm = math.sqrt(
        sum(component * component for component in raw_deflector_to_source)
    )
    deflector_to_source = tuple(
        component / q_norm for component in raw_deflector_to_source
    )
    deflector_to_observer = (-0.8, 0.6, 0.0)
    distance_au = 4.2
    distance_km = distance_au * (erfa.DAU / 1000.0)
    radius_km = SCHWARZSCHILD_RADII["Sun"]
    equivalent_solar_masses = radius_km / (
        erfa.SRS * (erfa.DAU / 1000.0)
    )

    actual = _contact_klioner_deflected_unit_direction(
        observer_to_source,
        deflector_to_source,
        deflector_to_observer,
        radius_km,
        distance_km,
        3.0e-9,
    )
    raw_expected = erfa.ld(
        equivalent_solar_masses,
        observer_to_source,
        deflector_to_source,
        deflector_to_observer,
        distance_au,
        3.0e-9,
    )
    expected_norm = math.sqrt(
        sum(float(component) ** 2 for component in raw_expected)
    )
    expected = tuple(float(component) / expected_norm for component in raw_expected)

    assert actual == pytest.approx(expected, abs=3.0e-16)


@pytest.mark.parametrize("separation_deg", [40.0, 0.27])
def test_contact_solar_deflection_matches_erfa_ldsun(
    separation_deg: float,
) -> None:
    erfa = pytest.importorskip("erfa")
    from moira.corrections import SCHWARZSCHILD_RADII

    angle = math.radians(separation_deg)
    observer_to_source = (math.cos(angle), math.sin(angle), 0.0)
    deflector_to_observer = (-1.0, 0.0, 0.0)
    distance_km = erfa.DAU / 1000.0

    actual = _contact_klioner_deflected_unit_direction(
        observer_to_source,
        observer_to_source,
        deflector_to_observer,
        SCHWARZSCHILD_RADII["Sun"],
        distance_km,
        6.0e-6,
    )
    raw_expected = erfa.ldsun(
        observer_to_source,
        deflector_to_observer,
        1.0,
    )
    expected_norm = math.sqrt(
        sum(float(component) ** 2 for component in raw_expected)
    )
    expected = tuple(float(component) / expected_norm for component in raw_expected)

    # At 0.27 degrees the ray is just outside the mean solar limb and both
    # SOFA's solar limiter and the Ldn terrestrial-observer limiter are idle.
    assert actual == pytest.approx(expected, abs=1.0e-14)


def test_reader_bound_deflection_uses_de441_velocities_and_exact_finite_q(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.planets as planets_module

    speed_km_per_day = 299_792.458 * 86_400.0
    states = {
        "Sun": ((1.0e8, 0.0, 0.0), (0.0, 1.0e5, 0.0)),
        "Jupiter": ((5.0e8, 0.0, 0.0), (0.0, 2.0e5, 0.0)),
        "Saturn": ((9.0e8, 0.0, 0.0), (0.0, 3.0e5, 0.0)),
    }
    monkeypatch.setattr(
        planets_module,
        "_barycentric_state",
        lambda body, _jd_tt, _reader: states[body],
    )
    calls: list[tuple[object, ...]] = []

    def capture(
        p: tuple[float, float, float],
        q: tuple[float, float, float],
        e: tuple[float, float, float],
        radius_km: float,
        distance_km: float,
        limiter: float,
    ) -> tuple[float, float, float]:
        calls.append((p, q, e, radius_km, distance_km, limiter))
        return p

    monkeypatch.setattr(
        contacts_module,
        "_contact_klioner_deflected_unit_direction",
        capture,
    )
    star = _star(parallax_mas=1000.0)
    observer = (0.0, 0.0, 0.0)

    actual = _reader_bound_deflected_star_icrf_direction(
        star,
        observer,
        J2000,
        object(),
    )

    assert actual == (1.0, 0.0, 0.0)
    # The incoming light encounters Saturn, Jupiter, then the Sun.  This is
    # passage order, not a fixed decreasing-mass order.
    assert [call[5] for call in calls] == [3.0e-10, 3.0e-9, 6.0e-6]
    source_ssb = (
        star.barycentric_distance_km,
        0.0,
        0.0,
    )
    for call, body in zip(calls, ("Saturn", "Jupiter", "Sun")):
        position, velocity = states[body]
        offset_days = -position[0] / speed_km_per_day
        body_at_passage = tuple(
            position[index] + offset_days * velocity[index]
            for index in range(3)
        )
        body_to_source = tuple(
            source_ssb[index] - body_at_passage[index]
            for index in range(3)
        )
        source_distance = math.sqrt(
            sum(component * component for component in body_to_source)
        )
        expected_q = tuple(
            component / source_distance for component in body_to_source
        )
        body_to_observer = tuple(-component for component in body_at_passage)
        observer_distance = math.sqrt(
            sum(component * component for component in body_to_observer)
        )
        expected_e = tuple(
            component / observer_distance for component in body_to_observer
        )

        assert call[1] == pytest.approx(expected_q, abs=2.0e-15)
        assert call[2] == pytest.approx(expected_e, abs=2.0e-15)
        assert call[4] == pytest.approx(observer_distance, rel=2.0e-15)


def test_finite_star_distance_propagates_with_radial_and_tangential_motion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.stars as stars_module

    record = SimpleNamespace(
        name="Fast Nearby",
        nomenclature="HIP synthetic",
        ra_deg=0.0,
        dec_deg=0.0,
        pmra_mas_yr=5_000.0,
        pmdec_mas_yr=-2_000.0,
        parallax_mas=1_000.0,
        radial_velocity_km_s=100.0,
        gaia_dr3_id=None,
        provenance={"matching_status": "synthetic"},
    )
    monkeypatch.setattr(
        stars_module,
        "_resolve_star_record",
        lambda _name, _policy: (record, "exact"),
    )
    years = 100.0
    star = lunar_contact_star_at("Fast Nearby", J2000 + years * 365.25)

    parsec_au = 206_264.80624709636
    au_km = 149_597_870.7
    mas_to_rad = math.radians(1.0 / 3_600_000.0)
    radial_pc_per_year = 100.0 * 31_557_600.0 / (au_km * parsec_au)
    expected_position_pc = (
        1.0 + radial_pc_per_year * years,
        5_000.0 * mas_to_rad * years,
        -2_000.0 * mas_to_rad * years,
    )
    expected_distance_pc = math.sqrt(
        sum(component * component for component in expected_position_pc)
    )
    expected_unit = tuple(
        component / expected_distance_pc for component in expected_position_pc
    )

    assert star.barycentric_distance_km == pytest.approx(
        expected_distance_pc * parsec_au * au_km,
        rel=2.0e-15,
    )
    assert star.barycentric_icrf_unit == pytest.approx(expected_unit, abs=2.0e-15)
    observer = (0.0, au_km, 6_378.0)
    expected_relative = (
        expected_position_pc[0] * parsec_au * au_km - observer[0],
        expected_position_pc[1] * parsec_au * au_km - observer[1],
        expected_position_pc[2] * parsec_au * au_km - observer[2],
    )
    expected_relative_norm = math.sqrt(
        sum(component * component for component in expected_relative)
    )
    assert _observer_star_icrf_direction(star, observer) == pytest.approx(
        tuple(component / expected_relative_norm for component in expected_relative),
        abs=2.0e-15,
    )


def test_star_reference_epoch_must_lie_inside_tt_event_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira._ephemeris_time as ephemeris_time

    monkeypatch.setattr(
        ephemeris_time,
        "_ut1_to_ephemeris_tt",
        lambda jd_ut1, _reader: jd_ut1 + 0.25,
    )
    inside = _star(epoch=J2000 + 0.25 + 2.0 / 86_400.0)
    _validate_star_reference_epoch(
        inside,
        J2000,
        J2000 + 4.0 / 86_400.0,
        object(),
    )
    with pytest.raises(ValueError, match="inside the contact window in TT"):
        _validate_star_reference_epoch(
            _star(epoch=J2000),
            J2000,
            J2000 + 4.0 / 86_400.0,
            object(),
        )


def test_contact_and_sequence_are_frozen_and_validate_state_machine() -> None:
    disappearance = _contact()
    sequence = _sequence((disappearance,))
    assert sequence.contacts == (disappearance,)
    with pytest.raises(FrozenInstanceError):
        disappearance.jd_ut1 = J2000  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        sequence.contacts = ()  # type: ignore[misc]

    invalid_reappearance = _contact(
        kind=LunarContactKind.REAPPEARANCE,
        before=LunarVisibilityState.OCCULTED,
        after=LunarVisibilityState.VISIBLE,
    )
    with pytest.raises(ValueError, match="state machine"):
        _sequence(
            (invalid_reappearance,),
            initial=LunarVisibilityState.VISIBLE,
            final=LunarVisibilityState.VISIBLE,
        )


def test_sequence_rejects_false_observer_and_target_semantics() -> None:
    sequence = _sequence((_contact(),))
    with pytest.raises(ValueError, match="WGS84 geodetic"):
        replace(sequence, observer_geometry="SPHERICAL_EARTH")
    with pytest.raises(ValueError, match="point-source catalog star"):
        replace(sequence, target_model="FINITE_STELLAR_DISK")
    with pytest.raises(ValueError, match="airless product"):
        replace(sequence, atmospheric_refraction=True)


def test_contact_kind_must_agree_with_visibility_transition() -> None:
    with pytest.raises(ValueError, match="visibility transition"):
        _contact(
            kind=LunarContactKind.DISAPPEARANCE,
            before=LunarVisibilityState.OCCULTED,
            after=LunarVisibilityState.VISIBLE,
        )
    with pytest.raises(ValueError, match="tangency must preserve"):
        _contact(
            kind=LunarContactKind.TANGENCY,
            before=LunarVisibilityState.VISIBLE,
            after=LunarVisibilityState.OCCULTED,
        )


def test_sequence_enforces_kind_specific_contact_residual_policy() -> None:
    with pytest.raises(ValueError, match="policy clearance_tolerance_deg"):
        _sequence((_contact(signed_clearance_deg=1.1e-7),))

    admitted_tangency = _contact(
        kind=LunarContactKind.TANGENCY,
        before=LunarVisibilityState.VISIBLE,
        after=LunarVisibilityState.VISIBLE,
        signed_clearance_deg=1.5e-7,
    )
    assert _sequence(
        (admitted_tangency,),
        initial=LunarVisibilityState.VISIBLE,
        final=LunarVisibilityState.VISIBLE,
    ).contacts == (admitted_tangency,)

    rejected_tangency = replace(
        admitted_tangency,
        signed_clearance_deg=2.1e-7,
    )
    with pytest.raises(ValueError, match="policy tangency_tolerance_deg"):
        _sequence(
            (rejected_tangency,),
            initial=LunarVisibilityState.VISIBLE,
            final=LunarVisibilityState.VISIBLE,
        )


def test_sequence_enforces_contact_bracket_time_policy() -> None:
    wide_bracket = _contact(bracket_half_width_seconds=0.001)
    with pytest.raises(ValueError, match="bracket width.*time_tolerance_seconds"):
        _sequence((wide_bracket,))


def test_sequence_enforces_contact_chronology_resolution_policy() -> None:
    disappearance = _contact()
    reappearance = _contact(
        jd_ut1=disappearance.jd_ut1 + 0.0008 / 86_400.0,
        kind=LunarContactKind.REAPPEARANCE,
        before=LunarVisibilityState.OCCULTED,
        after=LunarVisibilityState.VISIBLE,
    )

    with pytest.raises(
        ValueError,
        match="closer than policy chronology_tolerance_seconds",
    ):
        _sequence(
            (disappearance, reappearance),
            initial=LunarVisibilityState.VISIBLE,
            final=LunarVisibilityState.VISIBLE,
            policy=_policy(chronology_tolerance_seconds=0.001),
        )


def test_sequence_admits_coalesced_and_search_boundary_bracket_witnesses() -> None:
    exact_tangency = _contact(
        kind=LunarContactKind.TANGENCY,
        before=LunarVisibilityState.VISIBLE,
        after=LunarVisibilityState.VISIBLE,
    )
    exact_tangency = replace(
        exact_tangency,
        bracket_start_jd_ut1=exact_tangency.jd_ut1,
        bracket_end_jd_ut1=exact_tangency.jd_ut1,
    )
    assert _sequence(
        (exact_tangency,),
        initial=LunarVisibilityState.VISIBLE,
        final=LunarVisibilityState.VISIBLE,
    ).contacts == (exact_tangency,)

    end = J2000 + 4.0 / 86_400.0
    boundary_witnesses = (
        replace(
            _contact(jd_ut1=math.nextafter(J2000, math.inf)),
            bracket_start_jd_ut1=J2000,
        ),
        replace(
            _contact(jd_ut1=math.nextafter(end, -math.inf)),
            bracket_end_jd_ut1=end,
        ),
    )
    for witness in boundary_witnesses:
        assert _sequence((witness,)).contacts == (witness,)


@pytest.mark.parametrize("boundary", ["start", "end"])
def test_sequence_rejects_contact_bracket_outside_search_window(
    boundary: str,
) -> None:
    contact = _contact()
    if boundary == "start":
        contact = replace(
            contact,
            bracket_start_jd_ut1=J2000 - 0.1 / 86_400.0,
        )
    else:
        contact = replace(
            contact,
            bracket_end_jd_ut1=J2000 + 4.1 / 86_400.0,
        )
    with pytest.raises(ValueError, match="brackets must lie inside"):
        _sequence((contact,))


def test_ut1_contact_and_window_properties_invert_to_utc_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    utc_offset_days = 2.0 / 86_400.0
    monkeypatch.setattr(
        contacts_module,
        "_ut1_to_utc",
        lambda jd_ut1: jd_ut1 - utc_offset_days,
    )
    disappearance = _contact()
    sequence = _sequence((disappearance,))

    assert disappearance.jd_utc == pytest.approx(
        disappearance.jd_ut1 - utc_offset_days
    )
    assert disappearance.datetime_utc == datetime_from_jd(disappearance.jd_utc)
    assert disappearance.calendar_utc == calendar_datetime_from_jd(
        disappearance.jd_utc
    )
    assert sequence.start_datetime_utc == datetime_from_jd(sequence.jd_start_utc)
    assert sequence.end_calendar_utc == calendar_datetime_from_jd(
        sequence.jd_end_utc
    )


def test_public_assembly_uses_injected_geometry_and_preserves_profile_truth() -> None:
    profile = PreparedProfile()

    def geometry(jd_ut1: float, supplied_profile: PreparedProfile) -> ContactGeometry:
        assert supplied_profile is profile
        seconds = _seconds(jd_ut1)
        return ContactGeometry(
            signed_clearance_deg=(
                1.0e-4 * (seconds - 2.0) * (seconds - 2.25)
            ),
            position_angle_deg=(120.0 + seconds) % 360.0,
        )

    result = lunar_star_topographic_contacts(
        _star(),
        J2000,
        J2000 + 4.0 / 86_400.0,
        31.5,
        -99.9,
        profile=profile,
        observer_elevation_m=500.0,
        policy=_policy(),
        geometry_evaluator=geometry,
    )

    assert result.time_scale == "UT1"
    assert result.profile_model == profile.model_name
    assert result.profile_provenance == profile.provenance
    assert result.geometry_mode is LunarContactGeometryMode.CALLER_INJECTED
    assert "no reader-bound astronomical geometry claim" in (
        result.geometry_provenance
    )
    assert result.initial_visibility is LunarVisibilityState.VISIBLE
    assert result.final_visibility is LunarVisibilityState.VISIBLE
    assert [contact.kind for contact in result.contacts] == [
        LunarContactKind.DISAPPEARANCE,
        LunarContactKind.REAPPEARANCE,
    ]
    assert [contact.position_angle_deg for contact in result.contacts] == pytest.approx(
        [122.0, 122.25],
        abs=0.002,
    )


def test_default_evaluator_wires_reader_profile_site_and_airless_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.eclipse_geometry as eclipse_geometry
    reader = object()
    geometry_calls: list[tuple[object, ...]] = []

    def physical_geometry(*args: object) -> tuple[float, float, float]:
        geometry_calls.append(args)
        return (
            0.25 + (0.1 - _seconds(float(args[1]))) * 1.0e-4,
            42.0,
            384_400.0,
        )

    monkeypatch.setattr(
        contacts_module,
        "_physical_star_moon_geometry",
        physical_geometry,
    )
    monkeypatch.setattr(eclipse_geometry, "apparent_radius", lambda *_args: 0.25)
    monkeypatch.setattr(
        contacts_module,
        "_validate_star_reference_epoch",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        contacts_module,
        "_reader_bound_geometry_label",
        lambda *_args: "DE-0441LE-0441",
    )

    result = lunar_star_topographic_contacts(
        _star(),
        J2000,
        J2000 + 0.2 / 86_400.0,
        31.5,
        -99.9,
        profile=PreparedProfile(),
        observer_elevation_m=500.0,
        reader=reader,
        policy=_policy(),
    )

    assert len(result.contacts) == 1
    assert result.contacts[0].kind is LunarContactKind.DISAPPEARANCE
    assert _seconds(result.contacts[0].jd_ut1) == pytest.approx(0.1, abs=0.001)
    assert result.contacts[0].position_angle_deg == 42.0
    assert result.initial_visibility is LunarVisibilityState.VISIBLE
    assert result.final_visibility is LunarVisibilityState.OCCULTED
    assert result.geometry_mode is LunarContactGeometryMode.READER_BOUND_DE441
    assert "ephemeris=DE-0441LE-0441" in result.geometry_provenance
    assert "Klioner (2003) Eq.70 / IAU SOFA Ld-Ldn" in result.geometry_provenance
    assert "limiters 6e-6/3e-9/3e-10" in result.geometry_provenance
    assert "exact finite-star deflector-to-source direction" in (
        result.geometry_provenance
    )
    assert geometry_calls
    assert all(call[2:5] == (31.5, -99.9, 500.0) for call in geometry_calls)
    assert all(call[5] is reader for call in geometry_calls)


def test_injected_geometry_rejects_an_ambiguous_unused_reader() -> None:
    with pytest.raises(ValueError, match="reader must be omitted"):
        lunar_star_topographic_contacts(
            _star(),
            J2000,
            J2000 + 4.0 / 86_400.0,
            31.5,
            -99.9,
            profile=PreparedProfile(),
            reader=object(),
            policy=_policy(),
            geometry_evaluator=lambda _jd, _profile: ContactGeometry(1.0, 0.0),
        )


def test_physical_reader_must_match_structured_profile_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile, _source = _structured_event_profile()
    monkeypatch.setattr(
        contacts_module,
        "_validate_star_reference_epoch",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        contacts_module,
        "_reader_bound_geometry_label",
        lambda *_args: "DE-0441LE-0441",
    )

    with pytest.raises(ValueError, match="does not match"):
        lunar_star_topographic_contacts(
            _star(),
            J2000,
            J2000 + 4.0 / 86_400.0,
            31.5,
            -99.9,
            profile=profile,
            reader=object(),
            policy=_policy(),
        )


def test_public_assembly_rejects_missing_profile_provenance() -> None:
    class UnattributedProfile:
        model_name = "unknown"

        def adjustment_deg(self, *_args: object) -> float:
            return 0.0

    with pytest.raises(TypeError, match="profile provenance must be str"):
        lunar_star_topographic_contacts(
            _star(),
            J2000,
            J2000 + 4.0 / 86_400.0,
            31.5,
            -99.9,
            profile=UnattributedProfile(),  # type: ignore[arg-type]
            policy=_policy(),
            geometry_evaluator=lambda _jd, _profile: ContactGeometry(1.0, 0.0),
        )


def test_public_assembly_admits_structured_event_profile_and_source_identity() -> None:
    profile, source = _structured_event_profile()
    result = lunar_star_topographic_contacts(
        _star(),
        J2000,
        J2000 + 4.0 / 86_400.0,
        31.5,
        -99.9,
        profile=profile,
        policy=_policy(),
        geometry_evaluator=lambda _jd, _profile: ContactGeometry(1.0, 100.5),
    )

    assert result.contacts == ()
    assert result.profile_model == source.silhouette_model
    assert source.authority in result.profile_provenance
    assert "query_bounds_moon_xyz_km=-10,-8,-6,10,8,6" in (
        result.profile_provenance
    )
    assert "relief_bound=+/-10.0km" in result.profile_provenance
    assert "relief_policy=fixture complete bounded relief shell" in (
        result.profile_provenance
    )
    assert "relief_sources=fixture relief authority" in result.profile_provenance
    assert "content_identified_assets=1" in result.profile_provenance
    expected_asset_set_sha256 = hashlib.sha256(
        f"{source.assets[0].url}\0{source.assets[0].byte_length}\0"
        f"{source.assets[0].sha256}".encode("utf-8")
    ).hexdigest()
    assert f"asset_set_sha256={expected_asset_set_sha256}" in (
        result.profile_provenance
    )
    assert "realized_profile_sha256=" in result.profile_provenance
    assert result.observer_geometry == "WGS84_GEODETIC"
    assert result.target_model == "POINT_SOURCE_CATALOG_STAR"
    assert result.star.parallax_model == "FINITE_DISTANCE_FROM_CATALOG_PARALLAX"
    assert result.atmospheric_refraction is False


def test_structured_profile_identity_changes_with_every_scientific_input() -> None:
    profile, source = _structured_event_profile()
    base_identity = contacts_module._profile_identity(profile)[1]
    first_slice = profile.slices[0]

    variants = (
        replace(
            profile,
            source=replace(
                source,
                assets=(
                    replace(source.assets[0], sha256="1" * 64),
                ),
            ),
        ),
        replace(profile, source=replace(source, max_absolute_relief_km=10.5)),
        replace(
            profile,
            source=replace(source, relief_observed_highest_km=9.1),
        ),
        replace(
            profile,
            slices=(
                replace(first_slice, bin_width_deg=0.5),
                profile.slices[1],
            ),
        ),
        replace(
            profile,
            max_time_interpolation_gap_days=3.0 / 86_400.0,
        ),
        replace(
            profile,
            slices=(
                replace(first_slice, radii_km=(1737.3, 1737.6)),
                profile.slices[1],
            ),
        ),
    )

    variant_identities = {
        contacts_module._profile_identity(variant)[1] for variant in variants
    }
    assert len(variant_identities) == len(variants)
    assert base_identity not in variant_identities


@pytest.mark.parametrize(
    ("observer_latitude_deg", "observer_longitude_deg", "observer_elevation_m"),
    [
        (31.5001, -99.9, 0.0),
        (31.5, -99.9001, 0.0),
        (31.5, -99.9, 1.0),
    ],
)
def test_site_bound_profile_cannot_be_reused_for_another_observer(
    observer_latitude_deg: float,
    observer_longitude_deg: float,
    observer_elevation_m: float,
) -> None:
    profile, _source = _structured_event_profile()
    evaluator_called = False

    def geometry(_jd: float, _profile: object) -> ContactGeometry:
        nonlocal evaluator_called
        evaluator_called = True
        return ContactGeometry(1.0, 100.5)

    with pytest.raises(ValueError, match="does not match the prepared profile site"):
        lunar_star_topographic_contacts(
            _star(),
            J2000,
            J2000 + 4.0 / 86_400.0,
            observer_latitude_deg,
            observer_longitude_deg,
            profile=profile,
            observer_elevation_m=observer_elevation_m,
            policy=_policy(),
            geometry_evaluator=geometry,
        )
    assert evaluator_called is False


def test_public_assembly_rejects_non_geometry_evaluator_result() -> None:
    with pytest.raises(TypeError, match="must return ContactGeometry"):
        lunar_star_topographic_contacts(
            _star(),
            J2000,
            J2000 + 4.0 / 86_400.0,
            31.5,
            -99.9,
            profile=PreparedProfile(),
            policy=_policy(),
            geometry_evaluator=lambda _jd, _profile: (1.0, 0.0),  # type: ignore[return-value]
        )


def test_profile_preparer_derives_wrapped_pa_envelope_and_proves_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.lunar_limb as lunar_limb

    geometry_pas = iter((359.8, 0.0, 0.2))
    geometry_calls: list[float] = []

    def geometry(*args: object) -> tuple[float, float, float]:
        geometry_calls.append(float(args[1]))
        return (0.25, next(geometry_pas), 384_400.0)

    radius_calls: list[tuple[float, float]] = []
    profile = SimpleNamespace(
        radius_km_at=lambda epoch, pa: radius_calls.append((epoch, pa)) or 1737.4
    )
    build_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def build(*args: object, **kwargs: object) -> object:
        build_calls.append((args, kwargs))
        return profile

    monkeypatch.setattr(contacts_module, "_physical_star_moon_geometry", geometry)
    monkeypatch.setattr(
        contacts_module,
        "_validate_star_reference_epoch",
        lambda *_args: None,
    )
    monkeypatch.setattr(lunar_limb, "build_lola_rdr_lunar_limb_event_profile", build)
    expected_asset = LunarLimbAssetIdentity(
        "https://example.invalid/pinned.copc.laz",
        123,
        "a" * 64,
    )

    result = prepare_lola_rdr_lunar_star_contact_profile(
        _star(epoch=J2000 + 1.0 / 86_400.0),
        J2000,
        J2000 + 2.0 / 86_400.0,
        31.5,
        -99.9,
        reader=object(),
        observer_elevation_m=500.0,
        policy=LunarContactProfilePolicy(
            trajectory_step_seconds=1.0,
            position_angle_guard_deg=0.1,
            profile_time_step_seconds=1.0,
            pa_bin_width_deg=0.1,
            max_pa_interpolation_gap_deg=0.2,
        ),
        expected_lola_assets=(expected_asset,),
    )

    assert result is profile
    assert len(geometry_calls) == 3
    args, kwargs = build_calls[0]
    assert tuple(args[0]) == pytest.approx(
        (J2000, J2000 + 1.0 / 86_400.0, J2000 + 2.0 / 86_400.0)
    )
    assert float(args[4]) == pytest.approx(360.0)
    assert kwargs["position_angle_half_width_deg"] == pytest.approx(0.3)
    assert kwargs["max_time_interpolation_gap_days"] == pytest.approx(
        1.0 / 86_400.0
    )
    assert kwargs["expected_lola_assets"] == (expected_asset,)
    assert radius_calls == pytest.approx(
        [
            (J2000, 359.8),
            (J2000 + 1.0 / 86_400.0, 0.0),
            (J2000 + 2.0 / 86_400.0, 0.2),
        ]
    )


def test_profile_preparer_rejects_excessive_slice_count_before_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.lunar_limb as lunar_limb

    monkeypatch.setattr(
        contacts_module,
        "_validate_star_reference_epoch",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("reader-bound epoch validation must not run")
        ),
    )
    monkeypatch.setattr(
        contacts_module,
        "_physical_star_moon_geometry",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("geometry must not run for an excessive profile")
        ),
    )
    monkeypatch.setattr(
        lunar_limb,
        "build_lola_rdr_lunar_limb_event_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("profile builder must not run")
        ),
    )

    with pytest.raises(
        ValueError,
        match="MAX_LUNAR_CONTACT_PROFILE_SLICES=4096",
    ):
        prepare_lola_rdr_lunar_star_contact_profile(
            _star(epoch=J2000 + 1.0 / 86_400.0),
            J2000,
            J2000 + 2.0 / 86_400.0,
            31.5,
            -99.9,
            reader=object(),
            policy=LunarContactProfilePolicy(
                profile_time_step_seconds=1.0e-4,
            ),
        )


@pytest.mark.parametrize(
    ("argument", "value", "expected"),
    [
        ("observer_latitude_deg", -91.0, r"must be in \[-90, 90\]"),
        ("observer_longitude_deg", 181.0, r"must be in \[-180, 180\]"),
        ("observer_elevation_m", math.inf, "must be finite"),
    ],
)
def test_public_assembly_validates_all_site_coordinates(
    argument: str,
    value: float,
    expected: str,
) -> None:
    values = {
        "observer_latitude_deg": 31.5,
        "observer_longitude_deg": -99.9,
        "observer_elevation_m": 500.0,
    }
    values[argument] = value
    with pytest.raises(ValueError, match=expected):
        lunar_star_topographic_contacts(
            _star(),
            J2000,
            J2000 + 4.0 / 86_400.0,
            values["observer_latitude_deg"],
            values["observer_longitude_deg"],
            profile=PreparedProfile(),
            observer_elevation_m=values["observer_elevation_m"],
            policy=_policy(),
            geometry_evaluator=lambda _jd, _profile: ContactGeometry(1.0, 0.0),
        )
