"""Independent finite-iteration and DE441 reference-model enclosure tests."""
from decimal import Decimal, localcontext
from fractions import Fraction
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from moira import _eclipse_reference_astro as reference
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_spk_bounds import EclipseSpkBoundsUnavailable
from moira.constants import C_KM_PER_DAY


def _synthetic_provider(*, wrong_frame=False, mixed_sources=False):
    """Build a linear, exactly solvable SSB/Sun model and a fixed Moon."""
    light_speed = Fraction.from_float(C_KM_PER_DAY)

    def route(reader, center, target, anchor, offsets, *, max_records):
        assert max_records >= 1
        zero = I.point(0)
        if (center, target) == (0, 10):
            # x/c = 1/4 + t/16; all intervals are elapsed TDB days.
            position = (light_speed * (I.point(Fraction(1, 4)) + offsets / 16), zero, zero)
        elif (center, target) == (3, 301):
            position = (I.point(1), I.point(2), I.point(3))
        else:
            position = (zero, zero, zero)
        return SimpleNamespace(
            position_km=position,
            frame_id=2 if wrong_frame and target == 301 else 1,
            source_sha256_at_reader_open=("other" if mixed_sources and target == 301 else "one"),
        )

    return route


def test_linear_sun_encloses_every_possible_early_stop(monkeypatch):
    monkeypatch.setattr(reference, "bound_serving_type2_polynomial", _synthetic_provider())
    result = reference.bound_lunar_reference_vectors(None, 2451545.0, I.point(0))
    assert result.route_calls == 14
    assert len(result.iterations) == 10
    assert result.reference_model_only
    assert not result.native_routing_enclosed
    assert not result.native_evaluation_enclosed
    assert not result.native_tt_tdb_enclosed
    assert not result.native_light_time_enclosed
    assert not result.ut1_enclosed
    assert not result.physical_accuracy_certified
    for actual, expected in zip(result.moon_geometric_km, (1, 2, 3)):
        assert actual.contains(expected)

    # Independent exact recurrence for one admissible TDB-correction choice.
    # The reference envelope allows every correction in [-|K|,+|K|].
    delay = Fraction(1, 4)
    light_speed = Fraction.from_float(C_KM_PER_DAY)
    for step in result.iterations:
        assert step.emission_tt_offset_days.contains(-delay)
        delay = Fraction(1, 4) - delay / 16
        assert step.next_delay_days.contains(delay)
        assert step.sun_geocentric_km[0].contains(light_speed * delay)
        assert result.sun_retarded_km[0].contains(light_speed * delay)


def test_bounded_tdb_correction_and_closed_reception_interval(monkeypatch):
    monkeypatch.setattr(reference, "bound_serving_type2_polynomial", _synthetic_provider())
    offsets = I(Fraction(-1, 1000), Fraction(1, 1000))
    result = reference.bound_lunar_reference_vectors(None, 2451545.0, offsets)
    k = Fraction.from_float(abs(reference._NAIF_DELTET_K_SECONDS)) / 86400
    assert result.tdb_minus_tt_days.lo == -k
    assert result.tdb_minus_tt_days.hi == k
    assert result.reception_tt_offset_days.lo <= offsets.lo <= offsets.hi <= result.reception_tt_offset_days.hi
    for t in (offsets.lo, Fraction(0), offsets.hi):
        delay = Fraction(1, 4) + t / 16
        for step in result.iterations:
            assert step.emission_tt_offset_days.contains(t - delay)
            delay = Fraction(1, 4) + (t - delay) / 16
            assert step.next_delay_days.contains(delay)


@pytest.mark.parametrize("options", [{"wrong_frame": True}, {"mixed_sources": True}])
def test_different_frame_or_source_is_not_combined(monkeypatch, options):
    monkeypatch.setattr(reference, "bound_serving_type2_polynomial", _synthetic_provider(**options))
    with pytest.raises(EclipseReferenceUnavailable):
        reference.bound_lunar_reference_vectors(None, 2451545.0, I.point(0))


EclipseReferenceUnavailable = reference.EclipseReferenceUnavailable


def test_budget_and_underlying_coverage_remain_errors(monkeypatch):
    monkeypatch.setattr(reference, "bound_serving_type2_polynomial", _synthetic_provider())
    with pytest.raises(EnclosureUnavailable, match="budget"):
        reference.bound_lunar_reference_vectors(None, 2451545.0, I.point(0), max_route_calls=3)

    def fail(*args, **kwargs):
        raise EclipseSpkBoundsUnavailable("descriptor priority transition")

    monkeypatch.setattr(reference, "bound_serving_type2_polynomial", fail)
    with pytest.raises(EclipseSpkBoundsUnavailable, match="priority"):
        reference.bound_lunar_reference_vectors(None, 2451545.0, I.point(0))


@pytest.mark.parametrize("kwargs", [
    {"tt_anchor_jd": True, "tt_offset_days": I.point(0)},
    {"tt_anchor_jd": float("nan"), "tt_offset_days": I.point(0)},
    {"tt_anchor_jd": 2451545.0, "tt_offset_days": I.point(0), "max_route_calls": True},
    {"tt_anchor_jd": 2451545.0, "tt_offset_days": I.point(0), "sqrt_bits": 31},
    {"tt_anchor_jd": 2451545.0, "tt_offset_days": I.point(0), "quantize_bits": 257},
])
def test_invalid_requests_are_not_reported_as_empty_results(kwargs):
    with pytest.raises(ValueError):
        reference.bound_lunar_reference_vectors(None, **kwargs)


def test_unsupported_time_domain_fails_explicitly():
    with pytest.raises(EclipseReferenceUnavailable, match="time-transform"):
        reference.bound_lunar_reference_vectors(None, 40000000.0, I.point(1))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_de441_boxes_contain_independent_raw_record_states(planetary_reader, planetary_kernel_path, tt):
    # Independent 70-digit DAF record reader and forward Chebyshev recurrence.
    # Its TT/TDB periodic phase is binary64, so this is a numerical check of
    # the stated reference box, not a physical or serving-code certificate.
    path = Path(__file__).with_name("test_eclipse_split_epoch_precision.py")
    spec = importlib.util.spec_from_file_location("raw_eclipse_reference", path)
    raw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(raw)
    result = reference.bound_lunar_reference_vectors(planetary_reader, tt, I.point(0))
    with localcontext() as context, open(planetary_kernel_path, "rb") as stream:
        context.prec = 70
        sun, _ = raw._reference(planetary_reader, stream, Decimal.from_float(tt))
        moon = raw._sub(
            raw._state(planetary_reader, stream, (3, 301), Decimal.from_float(tt)),
            raw._state(planetary_reader, stream, (3, 399), Decimal.from_float(tt)),
        )
    for box, value in zip(result.sun_retarded_km, sun):
        assert box.contains(Fraction(value))
    for box, value in zip(result.moon_geometric_km, moon):
        assert box.contains(Fraction(value))
    assert all(state.frame_id == 1 for state in result.source_usages)
    assert len({state.source_sha256_at_reader_open for state in result.source_usages}) == 1
