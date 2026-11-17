"""Binary64 seam ownership and unresolved-cell regressions."""
from fractions import Fraction
from dataclasses import replace
import math

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_spk_bounds import EclipseSpkBoundsUnavailable
from moira._eclipse_spk_partition import _binary64_domain, _split_float_domain, partition_variable_type2_snapshots
from moira._eclipse_variable_spk_bounds import (
    StrictScalarVariableAnchorBounds, conditional_variable_anchor_type2_bounds,
    guarded_variable_scalar_snapshot_evaluate, variable_snapshot_hash,
)
from moira.spk_reader import SpkReader
import moira._eclipse_spk_partition as partition


def test_binary64_input_domain_inward_and_empty():
    a, b = 1., math.nextafter(1., math.inf)
    midpoint = (Fraction.from_float(a) + Fraction.from_float(b)) / 2
    assert _binary64_domain(I(midpoint, b)) == I.point(b)
    with pytest.raises(EclipseSpkBoundsUnavailable, match="no finite"):
        _binary64_domain(I.point(Fraction(1, 3)))


def test_zero_boundary_split_does_not_require_thousand_bisections():
    negative, nonnegative = _split_float_domain(I(-.001, .001))
    assert negative.hi == Fraction.from_float(math.nextafter(0., -math.inf))
    assert nonnegative.lo == 0


def test_disjoint_ownership_across_priority_and_signed_zero(monkeypatch):
    reader = object.__new__(SpkReader)
    def synthetic(_reader, _center, _target, anchor, offset):
        if anchor.lo < 0 <= anchor.hi:
            raise EclipseSpkBoundsUnavailable("descriptor priority or coverage transition requires split")
        if offset.lo < 0 < offset.hi:
            raise EclipseSpkBoundsUnavailable("split day floor branch requires subdivision")
        return object()
    monkeypatch.setattr(partition, "strict_variable_anchor_type2_bounds", synthetic)
    step = math.ulp(0.)
    ledger = partition_variable_type2_snapshots(reader, 0, 3, I(-step, step), I(-step, step), max_cells=16)
    assert ledger.binary64_input_coverage_complete
    assert not ledger.same_live_source_certified and not ledger.legacy_evaluator_certified
    for anchor in (-step, -0., 0., step):
        for offset in (-step, -0., 0., step):
            assert ledger.owner(anchor, offset) in ledger.cells
    assert ledger.owner(-0., 0.) == ledger.owner(0., -0.)
    with pytest.raises(ValueError, match="outside"):
        ledger.owner(1., 0.)


def test_two_dimensional_priority_diagonal_is_covered_once(monkeypatch):
    reader = object.__new__(SpkReader)
    def synthetic(_reader, _center, _target, anchor, offset):
        if anchor.lo + offset.lo < 0 <= anchor.hi + offset.hi:
            raise EclipseSpkBoundsUnavailable("descriptor priority or coverage transition requires split")
        return object()
    monkeypatch.setattr(partition, "strict_variable_anchor_type2_bounds", synthetic)
    step = math.ulp(0.)
    ledger = partition_variable_type2_snapshots(reader, 0, 3, I(-2 * step, 2 * step), I(-2 * step, 2 * step), max_cells=64)
    assert ledger.all_resolved
    for anchor in (-2 * step, -step, 0., step, 2 * step):
        for offset in (-2 * step, -step, 0., step, 2 * step):
            cell = ledger.owner(anchor, offset)
            assert sum(c.anchor_days.contains(anchor) and c.offset_days.contains(offset) for c in ledger.cells) == 1
            assert cell.bounds is not None


@pytest.mark.parametrize("budget", ["cells", "evaluations", "depth"])
def test_budget_never_loses_unresolved_float_inputs(monkeypatch, budget):
    reader = object.__new__(SpkReader)
    def unavailable(*args):
        raise EclipseSpkBoundsUnavailable("record carry floor branch requires subdivision")
    monkeypatch.setattr(partition, "strict_variable_anchor_type2_bounds", unavailable)
    low, high = 2451545.25, math.nextafter(math.nextafter(2451545.25, math.inf), math.inf)
    kwargs = {"max_cells": 1} if budget == "cells" else {"max_evaluations": 1} if budget == "evaluations" else {"max_depth": 0}
    ledger = partition_variable_type2_snapshots(reader, 0, 3, I(low, high), I.point(0.), **kwargs)
    assert not ledger.all_resolved and ledger.binary64_input_coverage_complete
    for sample in (low, math.nextafter(low, math.inf), high):
        assert ledger.owner(sample, 0.).bounds is None
        assert "budget" in ledger.owner(sample, 0.).unresolved_reason


@pytest.mark.requires_ephemeris
def test_real_kernel_anchor_day_seam_and_snapshot_consistency(planetary_reader):
    center = 2451545.
    samples = (math.nextafter(center, -math.inf), center, math.nextafter(center, math.inf))
    ledger = partition_variable_type2_snapshots(
        planetary_reader, 0, 3, I(samples[0], samples[2]), I.point(-.0001), max_cells=16,
    )
    assert len(ledger.cells) >= 2
    assert ledger.all_resolved
    for anchor in samples:
        cell = ledger.owner(anchor, -.0001)
        assert cell.bounds.anchor_days == cell.anchor_days
        assert cell.bounds.offset_days == cell.offset_days
        assert variable_snapshot_hash(cell.bounds) == cell.bounds.record_snapshot_sha256
        result = guarded_variable_scalar_snapshot_evaluate(cell.bounds, anchor, -.0001)
        position, _ = planetary_reader._position_and_velocity_tdb_offset(0, 3, anchor, -.0001)
        assert all(abs(a-b) < 1e-6 for a, b in zip(result.position_km, position))


@pytest.mark.requires_ephemeris
def test_real_kernel_record_seam_owns_all_adjacent_inputs(planetary_reader):
    segment = planetary_reader._segments_for_pair(0, 3)[0]
    init, length, _, _, _ = segment._load_native_evaluator().chebyshev_metadata()
    anchor = 2451545.25
    anchor_seconds = (anchor - 2451545.) * 86400.
    record = math.ceil((anchor_seconds - init) / length)
    seam = (init + record * length - anchor_seconds) / 86400.
    below, above = math.nextafter(seam, -math.inf), math.nextafter(seam, math.inf)
    ledger = partition_variable_type2_snapshots(
        planetary_reader, 0, 3, I.point(anchor), I(below, above), max_cells=16, max_evaluations=31,
    )
    assert ledger.all_resolved
    for offset in (below, seam, above):
        cell = ledger.owner(anchor, offset)
        assert variable_snapshot_hash(cell.bounds) == cell.bounds.record_snapshot_sha256
        guarded_variable_scalar_snapshot_evaluate(cell.bounds, anchor, offset)
    lower = ledger.owner(anchor, below).bounds
    assert isinstance(lower, StrictScalarVariableAnchorBounds)
    assert not hasattr(lower, "position_km")
    assert lower.strict_bounds.record_routing_model == "strict_snapshot_scalar_binary64_rn"
    assert not lower.strict_bounds.source_record_matches_native
    with pytest.raises(EclipseSpkBoundsUnavailable, match="floor branch"):
        conditional_variable_anchor_type2_bounds(planetary_reader, 0, 3, I.point(anchor), I.point(below))
    forged = replace(lower, strict_bounds=replace(lower.strict_bounds, source_record_matches_native=True))
    with pytest.raises(ValueError, match="snapshot identity"):
        guarded_variable_scalar_snapshot_evaluate(forged, anchor, below)
