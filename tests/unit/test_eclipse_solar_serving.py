"""Conditional solar vector bounds versus the split production route.

The DE441 samples are regression evidence for the represented production
model, not independent ephemeris accuracy or a whole-interval proof.
"""
from fractions import Fraction
from types import SimpleNamespace

import pytest

from moira import _eclipse_solar_serving as serving
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.constants import Body, C_KM_PER_DAY
from moira.coordinates import vec_norm
from moira.corrections import _apply_light_time_split
from moira.eclipse import _eclipse_body_pair
from moira.planets import _barycentric_at_tt_offset, _earth_barycentric_at_tt_offset


def _synthetic_route(*, bad_frame=False, bad_source=False):
    def route(_reader, center, target, _anchor, _offset):
        source = SimpleNamespace(
            frame_id=2 if bad_frame and target == 301 else 1,
            source_sha256_at_reader_open="second" if bad_source and target == 301 else "first",
        )
        vector = (I.point(100000000 if target == 10 else 100), I.point(0), I.point(0))
        return SimpleNamespace(source=source, position_km=vector)
    return route


@pytest.mark.parametrize("kwargs", [{"bad_frame": True}, {"bad_source": True}])
def test_incompatible_route_evidence_is_rejected(monkeypatch, kwargs):
    monkeypatch.setattr(serving, "conditional_native_type2_bounds", _synthetic_route(**kwargs))
    with pytest.raises(serving.EclipseSolarServingUnavailable):
        serving.bound_conditional_solar_serving_vectors(None, 2451545.75, I.point(0))


def test_budget_and_tdb_day_seam_fail_closed(monkeypatch):
    monkeypatch.setattr(serving, "conditional_native_type2_bounds", _synthetic_route())
    with pytest.raises(EnclosureUnavailable, match="budget"):
        serving.bound_conditional_solar_serving_vectors(None, 2451545.75, I.point(0), max_route_calls=3)
    with pytest.raises(EnclosureUnavailable, match="whole-day"):
        serving.bound_conditional_solar_serving_vectors(None, 2451545.0, I.point(0))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2460409.263, 2688456.25])
def test_de441_retarded_pair_and_each_emission_step(planetary_reader, tt):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = serving.bound_conditional_solar_serving_vectors(planetary_reader, tt, offsets)
    assert len(result.spk_usages) == 34
    assert len(result.sun_iterations) == len(result.moon_iterations) == 10
    assert all(usage.source.frame_id == 1 for usage in result.spk_usages)
    assert len({usage.source.source_sha256_at_reader_open for usage in result.spk_usages}) == 1
    assert result.split_serving_route_required
    assert not result.legacy_fallback_enclosed
    assert not result.arithmetic_environment_attested
    assert not result.native_build_attested
    assert not result.source_and_kernel_attested
    assert not result.earth_orientation_enclosed
    assert not result.rounded_shadow_axis_enclosed
    assert not result.physical_accuracy_certified

    for seconds in (-4, 0, 4):
        epoch = tt + seconds / 86400
        relative = Fraction.from_float(epoch) - Fraction.from_float(tt)
        assert offsets.contains(relative)
        actual_pair = _eclipse_body_pair(epoch, planetary_reader, sun_retarded=True, moon_retarded=True)
        earth = _earth_barycentric_at_tt_offset(epoch, 0.0, planetary_reader)
        for body_name, steps, vector_box, actual in (
            (Body.SUN, result.sun_iterations, result.sun_retarded_km, actual_pair[0]),
            (Body.MOON, result.moon_iterations, result.moon_retarded_km, actual_pair[1]),
        ):
            seen = []

            def body(name, reception, emission_offset, reader):
                bary = _barycentric_at_tt_offset(name, reception, emission_offset, reader)
                seen.append((emission_offset, bary))
                return bary

            value, delay = _apply_light_time_split(body_name, epoch, planetary_reader, earth, body)
            assert value == actual
            assert 1 <= len(seen) - 1 < 10
            assert all(box.contains(component) for box, component in zip(vector_box, value))
            for (emission_offset, bary), step in zip(seen[1:], steps):
                assert step.emission_tt_offset_days.contains(relative + Fraction.from_float(emission_offset))
                vector = tuple(component - observer for component, observer in zip(bary, earth))
                assert all(box.contains(component) for box, component in zip(step.geocentric_km, vector))
                next_delay = vec_norm(vector) / C_KM_PER_DAY
                assert step.next_delay_days.contains(next_delay)
                input_delay = -emission_offset
                assert step.input_delay_days.contains(input_delay)
                exact_difference = Fraction.from_float(next_delay) - Fraction.from_float(input_delay)
                assert step.emission_delay_residual_days.contains(exact_difference)
                assert step.rounded_emission_delay_residual_days.contains(next_delay - input_delay)
            last_step = steps[len(seen) - 2]
            assert last_step.next_delay_days.contains(delay)
            assert last_step.rounded_emission_delay_residual_days.contains(delay + seen[-1][0])
