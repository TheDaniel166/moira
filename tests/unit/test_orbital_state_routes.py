"""Deterministic, receipted TDB route planning for Stage 1 orbital state."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import pytest

from moira.spk_reader import (
    KernelPool,
    OutOfRangeError,
    _KernelSourceIdentity,
    _RoutedState,
    _SpkSegmentReceipt,
)


@dataclass
class _StrictReader:
    center: int
    target: int
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    intervals: tuple[tuple[float, float], ...] = ((1000.0, 2000.0),)
    label: str = "synthetic"

    def __post_init__(self) -> None:
        self._source_identity = _KernelSourceIdentity(
            label=self.label,
            sha256=(self.label.encode().hex() + "0" * 64)[:64],
            byte_length=1,
        )
        self.closed = 0
        self.on_evaluate = None

    def _coverage_pairs_tdb(self):
        return ((self.center, self.target),)

    def coverage_intervals_tdb(self, center: int, target: int):
        if (center, target) != (self.center, self.target):
            return ()
        return self.intervals

    def has_segment_at_tdb(self, center: int, target: int, epoch_tdb: float):
        return (center, target) == (self.center, self.target) and any(
            start <= epoch_tdb <= end for start, end in self.intervals
        )

    def position_and_velocity_tdb_with_receipt(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
        *,
        pool_index: int = 0,
    ):
        if self.on_evaluate is not None:
            self.on_evaluate()
        if not self.has_segment_at_tdb(center, target, epoch_tdb):
            raise OutOfRangeError("outside synthetic coverage", True)
        interval = next(
            pair for pair in self.intervals if pair[0] <= epoch_tdb <= pair[1]
        )
        receipt = _SpkSegmentReceipt(
            center=center,
            target=target,
            data_type=2,
            coverage_start_tdb=interval[0],
            coverage_end_tdb=interval[1],
            source=self._source_identity,
            pool_index=pool_index,
        )
        return _RoutedState(
            position_km=self.position,
            velocity_km_per_day=self.velocity,
            epoch_tdb=epoch_tdb,
            legs=(receipt,),
            covered_intervals_tdb=self.intervals,
        )

    def close(self) -> None:
        self.closed += 1


def test_direct_route_binds_exact_source_and_generation() -> None:
    reader = _StrictReader(0, 10, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    state = KernelPool((reader,)).position_and_velocity_tdb_with_receipt(
        0, 10, 1500.0
    )

    assert state.position_km == (1.0, 2.0, 3.0)
    assert state.velocity_km_per_day == (4.0, 5.0, 6.0)
    assert state.pool_generation == 0
    assert [(leg.center, leg.target, leg.pool_index) for leg in state.legs] == [
        (0, 10, 0)
    ]
    assert state.legs[0].source.label == "synthetic"


def test_reverse_route_negates_position_and_velocity_but_receipts_source() -> None:
    reader = _StrictReader(0, 10, (1.0, -2.0, 3.0), (4.0, -5.0, 6.0))
    state = KernelPool((reader,)).position_and_velocity_tdb_with_receipt(
        10, 0, 1500.0
    )

    assert state.position_km == (-1.0, 2.0, -3.0)
    assert state.velocity_km_per_day == (-4.0, 5.0, -6.0)
    assert (state.legs[0].center, state.legs[0].target) == (0, 10)


def test_multi_hop_route_adds_state_and_intersects_exact_coverage() -> None:
    first = _StrictReader(
        0,
        3,
        (1.0, 2.0, 3.0),
        (0.1, 0.2, 0.3),
        ((1000.0, 1600.0), (1700.0, 2200.0)),
        "first",
    )
    second = _StrictReader(
        3,
        10,
        (10.0, 20.0, 30.0),
        (1.0, 2.0, 3.0),
        ((1200.0, 1800.0), (1900.0, 2300.0)),
        "second",
    )
    state = KernelPool((first, second)).position_and_velocity_tdb_with_receipt(
        0, 10, 1500.0
    )

    assert state.position_km == (11.0, 22.0, 33.0)
    assert state.velocity_km_per_day == pytest.approx((1.1, 2.2, 3.3))
    assert state.covered_intervals_tdb == (
        (1200.0, 1600.0),
        (1700.0, 1800.0),
        (1900.0, 2200.0),
    )
    assert [leg.source.label for leg in state.legs] == ["first", "second"]


def test_direct_route_wins_over_chain_and_pool_order_breaks_ties() -> None:
    first_direct = _StrictReader(0, 10, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="first")
    bridge = _StrictReader(0, 3, (20.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="bridge")
    tail = _StrictReader(3, 10, (30.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="tail")
    second_direct = _StrictReader(0, 10, (2.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="second")

    state = KernelPool(
        (bridge, tail, first_direct, second_direct)
    ).position_and_velocity_tdb_with_receipt(0, 10, 1500.0)

    assert state.position_km == (1.0, 0.0, 0.0)
    assert state.legs[0].source.label == "first"


@pytest.mark.parametrize("reader_count", (0, 1, 4))
def test_initial_pool_builds_once_and_preserves_receipted_state(
    monkeypatch: pytest.MonkeyPatch, reader_count: int,
) -> None:
    readers = tuple(
        _StrictReader(0, 10, (float(i), 0.0, 0.0), (0.0, 0.0, 0.0), label=f"reader-{i}")
        for i in range(reader_count)
    )
    sequential = KernelPool()
    for reader in readers:
        sequential.add(reader)
    rebuilds = []
    original_rebuild = KernelPool._rebuild_indices_locked

    def counted_rebuild(pool):
        rebuilds.append(pool._readers)
        original_rebuild(pool)

    monkeypatch.setattr(KernelPool, "_rebuild_indices_locked", counted_rebuild)
    pool = KernelPool._from_initial_readers(iter(readers))
    assert rebuilds == [readers]
    with pool._read_lease() as actual, sequential._read_lease() as expected:
        assert actual == expected
    if readers:
        assert pool.position_and_velocity_tdb_with_receipt(0, 10, 1500.0) == (
            sequential.position_and_velocity_tdb_with_receipt(0, 10, 1500.0)
        )

    added = _StrictReader(0, 99, (9.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="added")
    pool.add(added)
    sequential.add(added)
    assert pool.position_and_velocity_tdb_with_receipt(0, 99, 1500.0) == (
        sequential.position_and_velocity_tdb_with_receipt(0, 99, 1500.0)
    )
    assert KernelPool(readers)._generation == 0


@pytest.mark.parametrize("entry_point", ("facade", "legacy"))
@pytest.mark.parametrize("discovery_fails", (False, True))
def test_initial_discovery_preserves_order_and_optional_failure_policy(
    monkeypatch: pytest.MonkeyPatch, entry_point: str, discovery_fails: bool,
) -> None:
    from moira import _facade_kernel, _kernel_paths, _spk_body_kernel, spk_reader

    primary = _StrictReader(0, 10, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="primary")
    first = _StrictReader(0, 10, (2.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="first")
    second = _StrictReader(0, 10, (3.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="second")
    error = ValueError("unavailable optional manifest")
    manifests = ("first.json", "second.json")
    loaded = []
    rebuilds = []
    original_rebuild = KernelPool._rebuild_indices_locked

    def load_manifest(path):
        loaded.append(path)
        if path == manifests[1] and discovery_fails:
            raise error
        return [first if path == manifests[0] else second]

    def counted_rebuild(pool):
        rebuilds.append(pool._readers)
        original_rebuild(pool)

    monkeypatch.setattr(_kernel_paths, "find_all_small_body_manifests", lambda: manifests)
    monkeypatch.setattr(_spk_body_kernel, "small_body_readers_from_manifest", load_manifest)
    monkeypatch.setattr(_facade_kernel, "small_body_readers_from_manifest", load_manifest)
    monkeypatch.setattr(KernelPool, "_rebuild_indices_locked", counted_rebuild)
    if entry_point == "facade":
        monkeypatch.setattr(_facade_kernel, "SpkReader", lambda path: primary)
        engine = _facade_kernel.KernelFacadeMixin("primary.bsp")
        pool = engine._reader_obj
        assert engine._kernel_init_error is None
        assert engine._supplemental_kernel_init_error is (error if discovery_fails else None)
    else:
        monkeypatch.setattr(spk_reader, "_reader", None)
        monkeypatch.setattr(spk_reader, "_reader_path", None)
        monkeypatch.setattr(spk_reader, "SpkReader", lambda path: primary)
        monkeypatch.setattr(spk_reader, "_OriginalSpkReader", _StrictReader)
        spk_reader.set_kernel_path("primary.bsp")
        pool = spk_reader._reader
    expected_readers = (primary, first) if discovery_fails else (primary, first, second)
    assert loaded == list(manifests)
    assert rebuilds == [expected_readers]
    state = pool.position_and_velocity_tdb_with_receipt(0, 10, 1500.0)
    assert state.position_km == primary.position
    assert state.pool_generation == len(expected_readers)
    assert state.legs[0].pool_index == 0


@pytest.mark.parametrize("initial_discovery", (False, True))
def test_add_during_evaluation_does_not_mutate_active_snapshot(initial_discovery: bool) -> None:
    primary = _StrictReader(0, 10, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="primary")
    added = _StrictReader(0, 10, (2.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="added")
    pool = (KernelPool._from_initial_readers((primary,)) if initial_discovery
            else KernelPool((primary,)))
    generation = 1 if initial_discovery else 0
    primary.on_evaluate = lambda: pool.add(added)

    state = pool.position_and_velocity_tdb_with_receipt(0, 10, 1500.0)

    assert state.pool_generation == generation
    assert state.position_km == (1.0, 0.0, 0.0)
    with pool._read_lease() as snapshot:
        assert snapshot.generation == generation + 1
        assert snapshot.readers == (primary, added)


def test_exception_releases_lease_and_close_closes_each_reader_once() -> None:
    reader = _StrictReader(0, 10, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    pool = KernelPool((reader,))

    with pytest.raises(RuntimeError):
        with pool._read_lease():
            raise RuntimeError("synthetic")

    pool.close()
    pool.close()
    assert reader.closed == 1


def test_close_waits_for_active_snapshot_before_closing_reader() -> None:
    reader = _StrictReader(0, 10, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    pool = KernelPool((reader,))
    leased = threading.Event()
    release = threading.Event()
    closed = threading.Event()

    def hold_lease() -> None:
        with pool._read_lease():
            leased.set()
            release.wait(timeout=2.0)

    def close_pool() -> None:
        pool.close()
        closed.set()

    holder = threading.Thread(target=hold_lease)
    closer = threading.Thread(target=close_pool)
    holder.start()
    assert leased.wait(timeout=1.0)
    closer.start()
    assert not closed.wait(timeout=0.05)
    assert reader.closed == 0

    release.set()
    holder.join(timeout=1.0)
    closer.join(timeout=1.0)
    assert closed.is_set()
    assert reader.closed == 1

