"""Failure contracts for absent kernels and retarded record crossings."""

from fractions import Fraction
from math import hypot

import pytest

from moira._eclipse_continuous_lunar import build_continuous_lunar_reference
from moira._eclipse_interval import RationalInterval
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.constants import C_KM_PER_DAY
from moira.julian import tdb_to_tt, tt_to_tdb
from moira.spk_reader import SpkReader


def test_missing_kernel_cannot_become_bounded_no_event(tmp_path):
    """An absent input raises a resource error before any model exists."""
    path = tmp_path / "absent-de441.bsp"
    with pytest.raises(FileNotFoundError, match="Planetary kernel not found"):
        build_continuous_lunar_reference(SpkReader(path), 2451545.0, RationalInterval.point(0))
    assert not path.exists()


@pytest.mark.requires_ephemeris
def test_real_sun_emission_crosses_record_and_reference_fails_closed(planetary_reader):
    """A real same-kernel crossing is unknown, not an absent eclipse."""
    reader = planetary_reader
    segment = reader._segment_for_tdb(0, 10, 2459891.96)
    init, length, count, _, _ = segment._load_native_evaluator().chebyshev_metadata()
    index = int(((2459891.96 - 2451545.0) * 86400 - init) // length) + 1
    assert 0 < index < count
    seam = 2451545.0 + (init + index * length) / 86400.0
    tt = tdb_to_tt(seam + 0.002)
    reception = tt_to_tdb(tt)

    # Independent ordinary point sample establishes the geometry of this
    # particular test: reception is after the join while the ten-iteration
    # retarded solar emission is before it. It is not an interval certificate.
    emb = reader.position_tdb(0, 3, reception)
    earth_leg = reader.position_tdb(3, 399, reception)
    earth = tuple(a + b for a, b in zip(emb, earth_leg))
    delay = 0.0
    for _ in range(11):
        sun = reader.position_tdb(0, 10, reception - delay)
        delay = hypot(*(a - b for a, b in zip(sun, earth))) / C_KM_PER_DAY
    assert reception > seam > reception - delay
    assert Fraction.from_float(delay) < Fraction(1, 100)

    # This model freezes a single record per route over its emission horizon.
    # It must explicitly refuse a horizon crossing a join.
    with pytest.raises(EnclosureUnavailable):
        build_continuous_lunar_reference(reader, tt, RationalInterval.point(0))
