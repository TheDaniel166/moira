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


def test_add_during_evaluation_does_not_mutate_active_snapshot() -> None:
    primary = _StrictReader(0, 10, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="primary")
    added = _StrictReader(0, 10, (2.0, 0.0, 0.0), (0.0, 0.0, 0.0), label="added")
    pool = KernelPool((primary,))
    primary.on_evaluate = lambda: pool.add(added)

    state = pool.position_and_velocity_tdb_with_receipt(0, 10, 1500.0)

    assert state.pool_generation == 0
    assert state.position_km == (1.0, 0.0, 0.0)
    with pool._read_lease() as snapshot:
        assert snapshot.generation == 1
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

