"""Conditional bounds for the actual phase planetary-vector ordering."""
from fractions import Fraction
from types import SimpleNamespace

import pytest

from moira import planets
from moira import _eclipse_phase_astro as phase_astro
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_phase_astro import bound_phase_planetary_vectors
from moira.constants import Body, C_KM_PER_DAY
from moira.coordinates import vec_add, vec_norm, vec_sub
from moira.corrections import _iterate_light_time
from moira.julian import tt_to_tdb


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_actual_phase_planetary_vectors_and_iterations_are_enclosed(planetary_reader, tt):
    bounds = bound_phase_planetary_vectors(planetary_reader, tt, I(Fraction(-5, 86400), Fraction(5, 86400)))
    assert len(bounds.spk_usages) == 34
    assert not bounds.source_and_kernel_attested
    assert not bounds.loaded_native_image_attested
    assert not bounds.arithmetic_environment_attested
    assert not bounds.ut1_enclosed
    assert not bounds.aberration_enclosed
    assert not bounds.ecliptic_frame_enclosed
    assert not bounds.phase_enclosed
    assert not bounds.search_certified
    for seconds in (-2, 0, 2):
        epoch = tt + seconds / 86400
        earth, earth_velocity = planets._earth_barycentric_state(epoch, planetary_reader)
        assert all(box.contains(value) for box, value in zip(bounds.earth_velocity_km_per_day, earth_velocity))
        epoch_tdb = tt_to_tdb(epoch)
        for body, steps, box in (
            (Body.SUN, bounds.sun_iterations, bounds.sun_retarded_km),
            (Body.MOON, bounds.moon_iterations, bounds.moon_retarded_km),
        ):
            seen = []

            def emission(delay):
                value = (0.0, 0.0, 0.0)
                for center, target in planets._NPE_BODY_ROUTE_PAIRS[body]:
                    value = vec_add(value, planetary_reader._position_tdb_offset(center, target, epoch_tdb, -delay))
                seen.append((delay, vec_sub(value, earth)))
                return value

            initial = planets._barycentric(body, epoch, planetary_reader)
            vector, delay = _iterate_light_time(earth, initial, emission, guard_norm=True)
            assert all(component.contains(value) for component, value in zip(box, vector))
            for (emission_delay, xyz), step in zip(seen, steps):
                assert step.emission_tdb_offset_days.contains(-emission_delay)
                assert all(component.contains(value) for component, value in zip(step.geocentric_km, xyz))
                assert step.next_delay_days.contains(vec_norm(xyz) / C_KM_PER_DAY)
            assert steps[len(seen) - 1].next_delay_days.contains(delay)


@pytest.mark.requires_ephemeris
def test_phase_vector_budget_failure_is_not_a_negative_eclipse_result(planetary_reader):
    with pytest.raises(EnclosureUnavailable, match="budget"):
        bound_phase_planetary_vectors(planetary_reader, 2459891.9582497696, I.point(0), max_route_calls=3)


def _synthetic_provider(*, frame=1, changing_source=False, ambiguous=False):
    calls = []

    def provider(reader, center, target, anchors, offset):
        calls.append((center, target, offset))
        zero = I.point(0)
        x = I(0, 1) if ambiguous and target == 10 else zero
        source = SimpleNamespace(
            frame_id=frame if target == 301 else 1,
            source_sha256_at_reader_open="other" if changing_source and target == 301 else "one",
        )
        return SimpleNamespace(position_km=(x, zero, zero), velocity_km_per_day=(zero, zero, zero), source=source,
                               record_routing_model="conditional_scalar_simd_fma_hull")

    return provider, calls


@pytest.mark.parametrize("kwargs", [{"frame": 2}, {"changing_source": True}])
def test_incompatible_phase_route_is_unavailable(monkeypatch, kwargs):
    provider, _ = _synthetic_provider(**kwargs)
    monkeypatch.setattr(phase_astro, "conditional_variable_anchor_type2_bounds", provider)
    with pytest.raises(EnclosureUnavailable):
        bound_phase_planetary_vectors(None, 2459891.9582497696, I.point(0))


def test_phase_zero_delay_and_negative_branches_remain_covered(monkeypatch):
    provider, calls = _synthetic_provider(ambiguous=True)
    monkeypatch.setattr(phase_astro, "conditional_variable_anchor_type2_bounds", provider)
    bounds = bound_phase_planetary_vectors(None, 2459891.9582497696, I.point(0))
    sun_emissions = [offset for center, target, offset in calls[4:] if (center, target) == (0, 10)]
    assert len(sun_emissions) == 20
    assert all(sun_emissions[i].hi < 0 and sun_emissions[i + 1] == I.point(0)
               for i in range(0, 20, 2))
    assert all(step.geocentric_km[0].contains(0) and step.geocentric_km[0].contains(1)
               for step in bounds.sun_iterations)


def test_phase_route_does_not_discard_record_seam(monkeypatch):
    def seam(*args):
        raise EnclosureUnavailable("record seam")

    monkeypatch.setattr(phase_astro, "conditional_variable_anchor_type2_bounds", seam)
    with pytest.raises(EnclosureUnavailable, match="record seam"):
        bound_phase_planetary_vectors(None, 2459891.9582497696, I.point(0))


def test_strict_snapshot_routing_never_certifies_legacy_phase(monkeypatch):
    provider, _ = _synthetic_provider()

    def strict_only(*args, **kwargs):
        state = provider(*args, **kwargs)
        state.record_routing_model = "strict_snapshot_scalar_binary64_rn"
        return state

    monkeypatch.setattr(phase_astro, "conditional_variable_anchor_type2_bounds", strict_only)
    with pytest.raises(EnclosureUnavailable, match="native routing hull"):
        bound_phase_planetary_vectors(None, 2459891.9582497696, I.point(0))


@pytest.mark.parametrize("speed", [0.0, -1.0, float("nan"), float("inf")])
def test_phase_route_rejects_invalid_light_speed(monkeypatch, speed):
    monkeypatch.setattr(phase_astro, "C_KM_PER_DAY", speed)
    with pytest.raises(EnclosureUnavailable, match="light speed"):
        bound_phase_planetary_vectors(None, 2459891.9582497696, I.point(0))
