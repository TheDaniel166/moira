"""Conditional serving-vector enclosure checks with explicit proof limits."""
from fractions import Fraction
from dataclasses import replace
import math
from types import SimpleNamespace

import pytest

from moira import _eclipse_serving_astro as serving
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_spk_bounds import EclipseSpkBoundsUnavailable
from moira.constants import C_KM_PER_DAY, Body
from moira.corrections import _apply_light_time_split
from moira.planets import _barycentric_at_tt_offset, _earth_barycentric_at_tt_offset


def _linear_provider(*, frame_id=1, mismatch=False):
    speed = Fraction.from_float(C_KM_PER_DAY)
    center_epoch = Fraction(2451545 * 4 + 3, 4)  # JD 2451545.75

    def route(reader, center, target, jd_tdb, offset_days, *, max_records):
        assert max_records >= 1
        zero = I.point(0)
        if (center, target) == (0, 10):
            elapsed = I.point(jd_tdb) + offset_days - center_epoch
            position = (speed * (I.point(Fraction(1, 4)) + elapsed / 16), zero, zero)
        elif (center, target) == (3, 301):
            position = (I.point(1), I.point(2), I.point(3))
        else:
            position = (zero, zero, zero)
        source = SimpleNamespace(
            frame_id=frame_id if target == 301 else 1,
            source_sha256_at_reader_open="other" if mismatch and target == 301 else "one",
        )
        return SimpleNamespace(position_km=position, source=source)

    return route


@pytest.mark.parametrize("tight_norm", [False, True])
def test_linear_sun_covers_actual_split_loop_and_all_intermediate_states(monkeypatch, tight_norm):
    monkeypatch.setattr(serving, "conditional_native_type2_bounds", _linear_provider())
    tt = 2451545.75
    result = serving.bound_conditional_lunar_serving_vectors(None, tt, I.point(0), tight_norm=tight_norm)
    assert result.tight_norm_assumptions_required is tight_norm
    assert result.route_calls == 14
    assert len(result.iterations) == 10
    assert result.split_tdb_enclosed_conditionally
    assert result.native_spk_enclosed_conditionally
    assert result.finite_light_time_enclosed_conditionally
    assert result.guarded_split_source_required
    assert result.immutable_reader_and_constants_required
    assert not result.arithmetic_environment_attested
    assert not result.native_build_attested
    assert not result.source_and_kernel_attested
    assert not result.ut1_enclosed
    assert not result.complete_search_certified
    assert not result.physical_accuracy_certified

    calls = []

    def body(body_name, epoch, offset, reader):
        value = (C_KM_PER_DAY * (0.25 + offset / 16.0), 0.0, 0.0)
        calls.append((offset, value))
        return value

    actual, final_delay = _apply_light_time_split(Body.SUN, tt, None, (0.0, 0.0, 0.0), body)
    assert len(calls) == 11  # initial body plus exhausted ten iterations
    for (offset, vector), step in zip(calls[1:], result.iterations):
        assert step.emission_tt_offset_days.contains(Fraction.from_float(offset))
        for box, value in zip(step.sun_geocentric_km, vector):
            assert box.contains(value)
        delay = abs(vector[0]) / C_KM_PER_DAY
        assert step.next_delay_days.contains(delay)
        input_delay = -offset
        assert step.input_delay_days.contains(input_delay)
        exact_difference = Fraction.from_float(delay) - Fraction.from_float(input_delay)
        assert step.emission_delay_residual_days.contains(exact_difference)
        assert step.rounded_emission_delay_residual_days.contains(delay - input_delay)
    for box, value in zip(result.sun_retarded_km, actual):
        assert box.contains(value)
    assert result.iterations[-1].next_delay_days.contains(final_delay)
    for box, value in zip(result.moon_geometric_km, (1.0, 2.0, 3.0)):
        assert box.contains(value)


@pytest.mark.parametrize("kwargs", [{"frame_id": 2}, {"mismatch": True}])
def test_incompatible_frame_or_source_never_combined(monkeypatch, kwargs):
    monkeypatch.setattr(serving, "conditional_native_type2_bounds", _linear_provider(**kwargs))
    with pytest.raises(serving.EclipseServingBoundsUnavailable):
        serving.bound_conditional_lunar_serving_vectors(None, 2451545.75, I.point(0))


def test_budget_and_spk_failure_are_not_empty_evidence(monkeypatch):
    monkeypatch.setattr(serving, "conditional_native_type2_bounds", _linear_provider())
    with pytest.raises(EnclosureUnavailable, match="budget"):
        serving.bound_conditional_lunar_serving_vectors(None, 2451545.75, I.point(0), max_route_calls=3)

    def fail(*args, **kwargs):
        raise EclipseSpkBoundsUnavailable("record priority transition")

    monkeypatch.setattr(serving, "conditional_native_type2_bounds", fail)
    with pytest.raises(EclipseSpkBoundsUnavailable, match="priority"):
        serving.bound_conditional_lunar_serving_vectors(None, 2451545.75, I.point(0))


def test_tdb_day_branch_refuses_unproved_ownership(monkeypatch):
    monkeypatch.setattr(serving, "conditional_native_type2_bounds", _linear_provider())
    with pytest.raises(EnclosureUnavailable, match="whole-day branch"):
        serving.bound_conditional_lunar_serving_vectors(None, 2451545.0, I.point(0))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
@pytest.mark.parametrize("tight_norm", [False, True])
def test_de441_serving_vectors_and_each_actual_iteration_are_enclosed(planetary_reader, tt, tight_norm):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, offsets, tight_norm=tight_norm)
    assert result.route_calls == 14
    assert all(state.source.frame_id == 1 for state in result.spk_usages)
    assert len({state.source.source_sha256_at_reader_open for state in result.spk_usages}) == 1
    for seconds in (-2.0, 0.0, 2.0):
        epoch = tt + seconds / 86400.0
        relative = Fraction.from_float(epoch) - Fraction.from_float(tt)
        assert offsets.contains(relative)
        earth = _earth_barycentric_at_tt_offset(epoch, 0.0, planetary_reader)
        seen = []

        def body(body_name, reception, emission_offset, reader):
            bary = _barycentric_at_tt_offset(body_name, reception, emission_offset, reader)
            seen.append((emission_offset, bary))
            return bary

        sun, final_delay = _apply_light_time_split(Body.SUN, epoch, planetary_reader, earth, body)
        assert 1 <= len(seen) - 1 < 10  # real samples terminate before exhausting the loop
        for (emission_offset, bary), step in zip(seen[1:], result.iterations):
            assert step.emission_tt_offset_days.contains(relative + Fraction.from_float(emission_offset))
            xyz = tuple(a - b for a, b in zip(bary, earth))
            for box, value in zip(step.sun_geocentric_km, xyz):
                assert box.contains(value)
            measured_delay = math.sqrt(xyz[0]**2 + xyz[1]**2 + xyz[2]**2) / C_KM_PER_DAY
            assert step.next_delay_days.contains(measured_delay)
            input_delay = -emission_offset
            assert step.input_delay_days.contains(input_delay)
            exact_difference = Fraction.from_float(measured_delay) - Fraction.from_float(input_delay)
            assert step.emission_delay_residual_days.contains(exact_difference)
            assert step.rounded_emission_delay_residual_days.contains(measured_delay - input_delay)
        for box, value in zip(result.sun_retarded_km, sun):
            assert box.contains(value)
        last_step = result.iterations[len(seen) - 2]
        assert last_step.next_delay_days.contains(final_delay)
        assert last_step.rounded_emission_delay_residual_days.contains(final_delay + seen[-1][0])
        # Production geometric lunar route subtracts two EMB-centered legs,
        # avoiding one extra barycentric addition and its roundoff.
        emb = planetary_reader._position_tdb_offset
        from moira.julian import _tt_to_tdb_split
        first, second = _tt_to_tdb_split(epoch, 0.0)
        moon_direct = emb(3, 301, first, second)
        earth_direct = emb(3, 399, first, second)
        moon = tuple(a - b for a, b in zip(moon_direct, earth_direct))
        for box, value in zip(result.moon_geometric_km, moon):
            assert box.contains(value)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_guarded_lunar_evaluation_uses_the_bounded_record_snapshots(planetary_reader, monkeypatch, tt):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, offsets)

    def no_new_route(*args, **kwargs):
        raise AssertionError("snapshot sampling must not read a new route")

    monkeypatch.setattr(serving, "conditional_native_type2_bounds", no_new_route)
    for seconds in (-2, 0, 2):
        sample = serving.evaluate_guarded_lunar_snapshot(bounds, tt + seconds / 86400)
        assert 1 <= sample.iterations_used <= 10
        assert len(sample.snapshot_hashes) == 4 + sample.iterations_used
        assert sample.snapshot_hashes == tuple(
            state.record_snapshot_sha256 for state in bounds.spk_usages[:4 + sample.iterations_used]
        )
        assert all(box.contains(value) for box, value in zip(bounds.sun_retarded_km, sample.sun_retarded_km))
        assert all(box.contains(value) for box, value in zip(bounds.moon_geometric_km, sample.moon_geometric_km))
        assert not sample.independent_build_receipt_verified
        assert not sample.legacy_mapped_evaluator_certified
        assert not sample.source_and_kernel_attested
        assert not sample.python_arithmetic_environment_attested
        assert not sample.physical_accuracy_certified


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_production_body_pair_on_bounded_records_matches_serving_kernel(planetary_reader, tt):
    """The opt-in reader runs the production body-pair code on copied DE441 words."""
    from moira.eclipse import _eclipse_body_pair

    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, offsets)
    for seconds in (-2, 0, 2):
        epoch = tt + seconds / 86400
        result = serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, epoch)
        sun, moon = _eclipse_body_pair(epoch, planetary_reader, sun_retarded=True, moon_retarded=False)
        assert result.sun_retarded_km == tuple(sun)
        assert result.moon_geometric_km == tuple(moon)
        assert 6 <= len(result.route_snapshot_hashes) <= 15
        assert not result.legacy_mapped_evaluator_certified
        assert not result.source_and_kernel_attested
        assert not result.arithmetic_environment_attested
        assert not result.complete_search_certified
        assert not result.physical_accuracy_certified


@pytest.mark.requires_ephemeris
def test_frozen_serving_scope_evaluates_after_reader_close(planetary_reader, monkeypatch):
    """Once copied, sample evaluation does not reopen the mapped reader."""
    from moira.eclipse import _eclipse_body_pair
    from moira.spk_reader import SpkReader

    tt = 2459891.9582497696
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    with SpkReader(planetary_reader.path) as reader:
        expected = {
            second: _eclipse_body_pair(tt + second / 86400, reader, sun_retarded=True, moon_retarded=False)
            for second in (-4, 0, 4)
        }
        scope = serving.prepare_lunar_serving_snapshot(reader, tt, offsets)
        # A new live-reader preflight detects a changed source identity, but
        # the already-frozen scope retains its copied words and operations.
        monkeypatch.setattr(reader, "_source_identity", replace(reader._source_identity, sha256="0" * 64))
        with pytest.raises(EnclosureUnavailable, match="source identity"):
            serving.evaluate_lunar_snapshot_with_serving_kernel(reader, scope.bounds, tt)
        frozen_sample = serving.evaluate_lunar_frozen_snapshot(scope, tt)
        assert frozen_sample.sun_retarded_km == tuple(expected[0][0])
        assert frozen_sample.moon_geometric_km == tuple(expected[0][1])
    assert len(scope.operations) == len(scope.records) == len(scope.snapshot_hashes) == 14

    def no_reader_access(*args, **kwargs):
        raise AssertionError("frozen evaluation must not revisit live descriptors")

    monkeypatch.setattr(serving, "_selected_descriptor", no_reader_access)
    for second, (sun, moon) in expected.items():
        sample = serving.evaluate_lunar_frozen_snapshot(scope, tt + second / 86400)
        assert sample.sun_retarded_km == tuple(sun)
        assert sample.moon_geometric_km == tuple(moon)
        assert not sample.source_and_kernel_attested
        assert not sample.complete_search_certified
    with pytest.raises(ValueError, match="outside"):
        serving.evaluate_lunar_frozen_snapshot(scope, tt + 1.0)
    assert not scope.source_and_kernel_attested
    assert not scope.arithmetic_environment_attested
    assert not scope.totality_certified and not scope.complete_search_certified


@pytest.mark.requires_ephemeris
def test_frozen_scope_replacement_cannot_assert_certification(planetary_reader):
    """A replaceable diagnostic scope cannot be promoted into a certificate."""
    tt = 2459891.9582497696
    scope = serving.prepare_lunar_serving_snapshot(planetary_reader, tt, I.point(0))
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(scope, totality_certified=True)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(scope, source_and_kernel_attested=True)
    narrowed = replace(scope.bounds, sun_retarded_km=(I.point(0),) * 3)
    forged = replace(scope, bounds=narrowed)
    assert not forged.totality_certified and not forged.source_and_kernel_attested
    with pytest.raises(ArithmeticError, match="escaped"):
        serving.evaluate_lunar_frozen_snapshot(forged, tt)


@pytest.mark.requires_ephemeris
def test_serving_kernel_copied_record_validates_record_and_epoch(planetary_reader):
    from moira.julian import _tt_to_tdb_split

    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    state = bounds.spk_usages[3]
    jd, offset = _tt_to_tdb_split(tt, 0.0)
    evaluator = serving._selected_descriptor(planetary_reader, 0, 10, jd, I.point(offset))._load_native_evaluator()
    record = tuple(value for axis in state.record_snapshot for value in axis)
    copied = evaluator._eclipse_position_from_copied_record(jd, offset, state.record_index, record)
    assert copied == tuple(evaluator.position(jd, offset))
    with pytest.raises(ValueError, match="does not cover"):
        evaluator._eclipse_position_from_copied_record(jd, offset, state.record_index + 1, record)
    with pytest.raises(ValueError, match="invalid dimensions"):
        evaluator._eclipse_position_from_copied_record(jd, offset, state.record_index, record[:-1])
    with pytest.raises(ValueError, match="coefficients"):
        evaluator._eclipse_position_from_copied_record(jd, offset, state.record_index, (float("nan"), *record[1:]))
    with pytest.raises(ValueError):
        evaluator._eclipse_position_from_copied_record(jd, 100000000.0, state.record_index, record)


@pytest.mark.requires_ephemeris
def test_production_body_pair_snapshot_rejects_tampering_and_missing_native_capability(planetary_reader, monkeypatch):
    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    state = bounds.spk_usages[1]
    record = list(state.record_snapshot)
    record[0] = (record[0][0] + 1.0, *record[0][1:])
    bad_state = replace(state, record_snapshot=tuple(record))
    bad_bounds = replace(bounds, spk_usages=(bounds.spk_usages[0], bad_state, *bounds.spk_usages[2:]))
    with pytest.raises(EnclosureUnavailable, match="identity"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bad_bounds, tt)
    with pytest.raises(ValueError, match="outside"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, tt + 1.0)

    select_descriptor = serving._selected_descriptor

    def missing_capability(reader, center, target, jd, offset):
        selected = select_descriptor(reader, center, target, jd, offset)
        original = selected._load_native_evaluator()
        evaluator = SimpleNamespace(chebyshev_metadata=original.chebyshev_metadata,
                                    chebyshev_records=original.chebyshev_records)
        return SimpleNamespace(start_second=selected.start_second, end_second=selected.end_second,
                               frame=selected.frame, start_i=selected.start_i, end_i=selected.end_i,
                               _load_native_evaluator=lambda: evaluator)

    monkeypatch.setattr(serving, "_selected_descriptor", missing_capability)
    with pytest.raises(EnclosureUnavailable, match="unavailable"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, tt)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("field", ["frame", "start_i", "end_i"])
def test_production_body_pair_snapshot_rejects_descriptor_mismatch(planetary_reader, monkeypatch, field):
    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    select_descriptor = serving._selected_descriptor

    def altered_descriptor(reader, center, target, jd, offset):
        selected = select_descriptor(reader, center, target, jd, offset)
        values = {name: getattr(selected, name) for name in ("frame", "start_i", "end_i")}
        values[field] += 1
        return SimpleNamespace(start_second=selected.start_second, end_second=selected.end_second,
                               _load_native_evaluator=selected._load_native_evaluator, **values)

    monkeypatch.setattr(serving, "_selected_descriptor", altered_descriptor)
    with pytest.raises(EnclosureUnavailable, match="identity"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, tt)


@pytest.mark.requires_ephemeris
def test_production_body_pair_snapshot_rejects_changed_reader_identity(planetary_reader, monkeypatch):
    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    identity = planetary_reader._source_identity
    monkeypatch.setattr(planetary_reader, "_source_identity", replace(identity, sha256="0" * 64))
    with pytest.raises(EnclosureUnavailable, match="source identity"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, tt)


@pytest.mark.requires_ephemeris
def test_production_body_pair_snapshot_rejects_changed_live_record(planetary_reader, monkeypatch):
    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    select_descriptor = serving._selected_descriptor

    def altered_record(reader, center, target, jd, offset):
        selected = select_descriptor(reader, center, target, jd, offset)
        original = selected._load_native_evaluator()

        def records(first, count):
            stored = list(original.chebyshev_records(first, count))
            axes = list(stored[0])
            axes[0] = (axes[0][0] + 1.0, *axes[0][1:])
            stored[0] = tuple(axes)
            return tuple(stored)

        evaluator = SimpleNamespace(chebyshev_metadata=original.chebyshev_metadata, chebyshev_records=records)
        return SimpleNamespace(start_second=selected.start_second, end_second=selected.end_second,
                               frame=selected.frame, start_i=selected.start_i, end_i=selected.end_i,
                               _load_native_evaluator=lambda: evaluator)

    monkeypatch.setattr(serving, "_selected_descriptor", altered_record)
    with pytest.raises(EnclosureUnavailable, match="record identity changed"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, tt)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("evaluator", [None, SimpleNamespace(), SimpleNamespace(chebyshev_metadata=lambda: None)])
def test_production_body_pair_snapshot_reports_missing_native_metadata(planetary_reader, monkeypatch, evaluator):
    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    select_descriptor = serving._selected_descriptor

    def unavailable(reader, center, target, jd, offset):
        selected = select_descriptor(reader, center, target, jd, offset)
        return SimpleNamespace(start_second=selected.start_second, end_second=selected.end_second,
                               _load_native_evaluator=lambda: evaluator)

    monkeypatch.setattr(serving, "_selected_descriptor", unavailable)
    with pytest.raises(EnclosureUnavailable, match="metadata is unavailable"):
        serving.evaluate_lunar_snapshot_with_serving_kernel(planetary_reader, bounds, tt)


@pytest.mark.requires_ephemeris
def test_snapshot_rejects_tampered_coefficients_and_unbounded_inputs(planetary_reader):
    tt = 2459891.9582497696
    bounds = serving.bound_conditional_lunar_serving_vectors(planetary_reader, tt, I.point(0))
    state = bounds.spk_usages[0]
    first_axis = state.record_snapshot[0]
    changed = ((first_axis[0] + 1.0, *first_axis[1:]), *state.record_snapshot[1:])
    bad_state = replace(state, record_snapshot=changed)
    bad_bounds = replace(bounds, spk_usages=(bad_state, *bounds.spk_usages[1:]))
    with pytest.raises(ValueError, match="snapshot identity"):
        serving.evaluate_guarded_lunar_snapshot(bad_bounds, tt)
    with pytest.raises(ValueError, match="outside"):
        serving.evaluate_guarded_lunar_snapshot(bounds, tt + 1.0)
    with pytest.raises(ValueError, match="finite"):
        serving.evaluate_guarded_lunar_snapshot(bounds, float("nan"))
    wrong_source = replace(state.source, center=42)
    wrong_route = replace(state, source=wrong_source)
    wrong_bounds = replace(bounds, spk_usages=(wrong_route, *bounds.spk_usages[1:]))
    with pytest.raises(EnclosureUnavailable, match="route"):
        serving.evaluate_guarded_lunar_snapshot(wrong_bounds, tt)
