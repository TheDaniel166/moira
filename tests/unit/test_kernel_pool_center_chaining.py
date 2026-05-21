"""
Tests for KernelPool two-phase center-chain dispatch.

Phase 1: reader serves (center, target) directly — no chaining.
Phase 2: reader serves (X, target) where X != center — pool chains
         raw position + bridge position to yield the requested center.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from moira.spk_reader import KernelPool, OutOfRangeError


def _make_reader(center: int, target: int, pos: tuple, *, jd: float = 2451545.0):
    """Return a minimal KernelReader mock serving one (center, target) pair."""
    r = MagicMock()
    r.has_segment_at.side_effect = (
        lambda c, t, j: c == center and t == target and abs(j - jd) < 1e-3
    )
    r.has_segment.side_effect = lambda c, t: c == center and t == target
    r.position.side_effect = (
        lambda c, t, j: pos if (c == center and t == target) else (_ for _ in ()).throw(KeyError)
    )
    r.coverage.return_value = {(center, target): (jd - 1.0, jd + 1.0)}
    r.covered_bodies.return_value = frozenset([target])
    return r


def test_pool_phase1_direct_match_returns_without_chaining():
    """Phase 1: body served at requested center — one reader call, no recursion."""
    jd = 2451545.0
    ssb_reader = _make_reader(0, 10, (1.0, 2.0, 3.0), jd=jd)   # Sun at SSB
    pool = KernelPool([ssb_reader])

    result = pool.position(0, 10, jd)
    assert result == (1.0, 2.0, 3.0)
    ssb_reader.position.assert_called_once_with(0, 10, jd)


def test_pool_phase2_heliocentric_body_chains_through_sun():
    """
    Phase 2: asteroid served heliocentric (center=10), caller wants SSB (center=0).
    Pool must fetch asteroid from heliocentric reader, Sun from planetary reader,
    and return vec_add(asteroid_helio, sun_ssb).
    """
    jd = 2451545.0
    helio_asteroid = (100.0, 200.0, 300.0)
    sun_ssb        = (10.0,  20.0,  30.0)
    expected_ssb   = (110.0, 220.0, 330.0)

    asteroid_reader = _make_reader(10, 2002060, helio_asteroid, jd=jd)
    sun_reader      = _make_reader(0, 10, sun_ssb, jd=jd)

    pool = KernelPool([asteroid_reader, sun_reader])

    result = pool.position(0, 2002060, jd)
    assert result == pytest.approx(expected_ssb)


def test_pool_raises_out_of_range_when_no_reader_covers_target():
    """No reader covers the requested body — OutOfRangeError raised."""
    jd = 2451545.0
    reader = _make_reader(0, 10, (1.0, 2.0, 3.0), jd=jd)
    pool = KernelPool([reader])

    with pytest.raises(OutOfRangeError):
        pool.position(0, 9999999, jd)


def test_pool_covered_bodies_union_across_readers():
    """covered_bodies() returns union of all reader covered_bodies."""
    r1 = MagicMock()
    r1.covered_bodies.return_value = frozenset([1, 2])
    r1.coverage.return_value = {}
    r2 = MagicMock()
    r2.covered_bodies.return_value = frozenset([3, 4])
    r2.coverage.return_value = {}

    pool = KernelPool([r1, r2])
    assert pool.covered_bodies() == frozenset([1, 2, 3, 4])
