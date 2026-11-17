"""Conditional native type-2 rounding-model and snapshot regressions."""
from dataclasses import replace
from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_spk_bounds import (
    _record_component,
    _require_matching_native_descriptor,
    conditional_native_type2_bounds,
    guarded_scalar_snapshot_evaluate,
)
from moira._eclipse_spk_bounds import EclipseSpkBoundsUnavailable


def test_native_duplicate_payload_coverage_is_checked_against_handle_catalog():
    segment = SimpleNamespace(start_i=100, end_i=200, data_type=2,
                              start_second=0.0, end_second=1000.0)
    selected = {"descriptor": (0.0, 1000.0, 301, 3, 1, 2, 100, 200)}
    conflicting = {"descriptor": (10.0, 900.0, 10, 0, 1, 2, 100, 200)}
    handle = SimpleNamespace(catalog=lambda: {"summaries": [conflicting, selected]})
    segment._handle = handle
    # The Python-side catalog is intentionally stale; production resolves
    # descriptor coverage from the native handle's own catalog.
    reader = SimpleNamespace(_kernel=SimpleNamespace(
        _handle=handle, catalog={"summaries": [selected]},
    ))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="conflicting coverage"):
        _require_matching_native_descriptor(reader, segment)

    handle.catalog = lambda: {"summaries": [selected, dict(selected)]}
    _require_matching_native_descriptor(reader, segment)
    segment._handle = object()
    with pytest.raises(EclipseSpkBoundsUnavailable, match="handle does not match"):
        _require_matching_native_descriptor(reader, segment)
    segment._handle = handle
    handle.catalog = lambda: {"summaries": []}
    with pytest.raises(EclipseSpkBoundsUnavailable, match="not present"):
        _require_matching_native_descriptor(reader, segment)
    reader._kernel._handle = None
    segment._handle = None
    _require_matching_native_descriptor(reader, segment)
    del reader._kernel.catalog
    with pytest.raises(EclipseSpkBoundsUnavailable, match="catalog unavailable"):
        _require_matching_native_descriptor(reader, segment)


@pytest.mark.requires_ephemeris
def test_de441_native_descriptor_identity_for_each_lunar_route(planetary_reader):
    for pair in ((0, 3), (3, 399), (3, 301), (0, 10)):
        segment = planetary_reader._segments_for_pair(*pair)[0]
        _require_matching_native_descriptor(planetary_reader, segment)


@pytest.mark.requires_ephemeris
def test_descriptor_selection_rejects_conflicting_native_catalog(planetary_reader, monkeypatch):
    segment = planetary_reader._segments_for_pair(0, 3)[0]
    catalog = planetary_reader._kernel._handle.catalog()
    duplicate = (segment.start_second + 1.0, segment.end_second - 1.0,
                 10, 0, 1, segment.data_type, segment.start_i, segment.end_i)
    simulated = {"summaries": [{"descriptor": duplicate}, *catalog["summaries"]]}
    fake_handle = SimpleNamespace(catalog=lambda: simulated)
    monkeypatch.setattr(planetary_reader._kernel, "_handle", fake_handle)
    monkeypatch.setattr(segment, "_handle", fake_handle)
    with pytest.raises(EclipseSpkBoundsUnavailable, match="conflicting coverage"):
        conditional_native_type2_bounds(planetary_reader, 0, 3, 2451545.0, I.point(0.0001))


def _independent_recurrence(coefficients, s, length, form):
    """Scalar, vector and fused operation orders, independent of interval code."""
    w1 = w2 = d1 = d2 = 0.0
    twice_s = 2.0 * s
    for coefficient in reversed(coefficients[1:]):
        old_d1 = d1
        if form == "fused":
            d1 = math.fma(twice_s, d1, 2.0*w1) - d2
        else:
            d1 = (2.0*w1) + (twice_s*d1 - d2)
        d2 = old_d1
        old_w1 = w1
        if form == "scalar":
            w1 = (coefficient + twice_s*w1) - w2
        elif form == "vector":
            w1 = coefficient + (twice_s*w1 - w2)
        else:
            w1 = math.fma(twice_s, w1, coefficient) - w2
        w2 = old_w1
    if form == "scalar":
        position = (coefficients[0] + s*w1) - w2
        derivative = (w1 + s*d1) - d2
    elif form == "vector":
        position = coefficients[0] + (s*w1 - w2)
        derivative = w1 + (s*d1 - d2)
    else:
        position = math.fma(s, w1, coefficients[0]) - w2
        derivative = math.fma(s, d1, w1) - d2
    return position, derivative * (172800.0 / length)


@pytest.mark.parametrize("coefficients", [
    (1e12, -1e12, 3.0, 0.25, -1.0),
    (1e-300, -2e-300, 3e-301, -5e-302),
    (0.0, math.ulp(0.0), -math.ulp(0.0), 0.0),
])
@pytest.mark.parametrize("s", [-1.0, -0.25, 0.0, 0.125, 1.0])
def test_conditional_bounds_cover_scalar_simd_and_fma_schedules(coefficients, s):
    position, velocity = _record_component(coefficients, I.point(s), 16.0)
    forms = ("scalar", "vector", "fused") if hasattr(math, "fma") else ("scalar", "vector")
    for form in forms:
        value, rate = _independent_recurrence(coefficients, s, 16.0, form)
        assert position.contains(value)
        assert velocity.contains(rate)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_tdb", [1026285.7107341307, 2451545.0, 2460409.262])
@pytest.mark.parametrize("center,target", [(0, 3), (0, 10), (3, 301), (3, 399)])
@pytest.mark.parametrize("start,end", [(-20, -10), (10, 20)])
def test_conditional_bounds_cover_actual_native_samples(
    planetary_reader, jd_tdb, center, target, start, end,
):
    offsets = I(Fraction(start, 86400), Fraction(end, 86400))
    try:
        result = conditional_native_type2_bounds(planetary_reader, center, target, jd_tdb, offsets)
    except EclipseSpkBoundsUnavailable as exc:
        # Any multiple native index/descriptor branch is intentionally
        # unsupported, but these ordinary controls are expected to resolve.
        pytest.fail(f"unexpected unresolved ordinary DE441 interval: {exc}")
    assert not result.arithmetic_environment_attested
    assert not result.source.native_routing_enclosed
    for seconds in (start, (start + end)//2, end):
        offset = float(Fraction(seconds, 86400))
        position, velocity = planetary_reader._position_and_velocity_tdb_offset(center, target, jd_tdb, offset)
        assert all(box.contains(value) for box, value in zip(result.position_km, position))
        assert all(box.contains(value) for box, value in zip(result.velocity_km_per_day, velocity))


@pytest.mark.requires_ephemeris
def test_guarded_wrapper_rejects_mutated_snapshot_before_native_call(planetary_reader):
    result = conditional_native_type2_bounds(planetary_reader, 0, 3, 2451545.0, I.point(0.0001))
    altered = list(result.record_snapshot[0])
    altered[0] = math.nextafter(altered[0], math.inf)
    forged = replace(result, record_snapshot=(tuple(altered), *result.record_snapshot[1:]))
    with pytest.raises(ValueError, match="snapshot identity"):
        guarded_scalar_snapshot_evaluate(forged, 0.0001)


@pytest.mark.requires_ephemeris
def test_guarded_wrapper_rejects_unbounded_offset_before_native_call(planetary_reader):
    result = conditional_native_type2_bounds(planetary_reader, 0, 3, 2451545.0, I.point(0.0001))
    with pytest.raises(ValueError, match="outside the bounded"):
        guarded_scalar_snapshot_evaluate(result, 0.1)
