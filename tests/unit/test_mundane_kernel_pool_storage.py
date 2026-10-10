"""Mundane provenance accepts only canonical, immutable KernelPool storage."""

import pytest

from moira.mundane import build_mundane_event_clock
from moira.spk_reader import KernelPool


@pytest.mark.requires_ephemeris
def test_mundane_clock_accepts_the_canonical_pool_and_preserves_clock_truth(planetary_reader):
    pool = KernelPool((planetary_reader,))
    assert type(pool._readers) is tuple
    direct = build_mundane_event_clock(2460000.0, reader=planetary_reader)
    pooled = build_mundane_event_clock(2460000.0, reader=pool)
    assert pooled == direct


@pytest.mark.requires_ephemeris
def test_mundane_clock_rejects_replaced_mutable_pool_storage(planetary_reader):
    pool = KernelPool((planetary_reader,))
    pool._readers = [planetary_reader]
    with pytest.raises(TypeError, match="reader storage is not the admitted concrete vessel"):
        build_mundane_event_clock(2460000.0, reader=pool)
