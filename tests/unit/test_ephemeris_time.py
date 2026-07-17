"""Source-aware Delta-T and private ephemeris-clock binding tests."""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from moira._ephemeris_time import (
    _EphemerisTimeBasisError,
    _ephemeris_delta_t,
    _ephemeris_tt_to_ut1,
    _ut1_to_ephemeris_tt,
)
from moira.julian import (
    DeltaTPolicy,
    EOPRegistry,
    _TIDAL_NDOT_DE441,
    _TIDAL_NDOT_HPIERS,
    _continuous_decimal_year_from_jd,
    _resolve_delta_t,
    _resolve_delta_t_for_ut1,
    _tidacc_correction,
    delta_t,
    julian_day,
    ut_to_tt,
)
from moira.constants import Body
from moira.planets import planet_at
from moira.spk_reader import _EphemerisKernelIdentity, KernelPool


def _identity(
    label: str,
    planetary: str,
    lunar: str,
    ndot: float | None,
) -> _EphemerisKernelIdentity:
    return _EphemerisKernelIdentity(label, planetary, lunar, ndot)


DE430_IDENTITY = _identity("DE-0430LE-0430", "DE430", "LE430", -25.85)
DE441_IDENTITY = _identity("DE-0441LE-0441", "DE441", "LE441", -25.936)
DE440_IDENTITY = _identity("DE-0440LE-0440", "DE440", "LE440", None)


@pytest.mark.parametrize(
    "year",
    (-2500.0, -2100.0, -2000.0, 0.0, 1955.0, 2015.2, 2020.0, 2030.0),
)
def test_source_resolver_preserves_public_delta_t_seconds(year: float) -> None:
    assert _resolve_delta_t(year).seconds == delta_t(year)


def test_hpiers_to_de441_correction_is_explicit_and_de430_is_zero() -> None:
    jd_ut1 = julian_day(-2000, 1, 1, 0.0)
    raw = _resolve_delta_t_for_ut1(jd_ut1)
    de430 = _ephemeris_delta_t(
        jd_ut1,
        SimpleNamespace(_kernel_identity=DE430_IDENTITY),
    )
    de441 = _ephemeris_delta_t(
        jd_ut1,
        SimpleNamespace(_kernel_identity=DE441_IDENTITY),
    )
    year = _continuous_decimal_year_from_jd(jd_ut1)
    expected = _tidacc_correction(
        year,
        _TIDAL_NDOT_HPIERS,
        _TIDAL_NDOT_DE441,
    )

    assert raw.source_product == "hpiers_de430_le430"
    assert de430.correction_seconds == pytest.approx(0.0, abs=1.0e-15)
    assert de430.seconds == raw.seconds
    assert de441.correction_seconds == pytest.approx(expected, abs=1.0e-12)
    assert de441.correction_seconds == pytest.approx(122.511, abs=0.002)
    assert de441.seconds == pytest.approx(raw.seconds + expected, abs=1.0e-12)


def test_unknown_tidal_basis_fails_only_for_basis_sensitive_source() -> None:
    ancient = julian_day(-1000, 1, 1, 0.0)
    with pytest.raises(_EphemerisTimeBasisError, match="unadmitted tidal basis"):
        _ephemeris_delta_t(
            ancient,
            SimpleNamespace(_kernel_identity=DE440_IDENTITY),
        )

    modern = julian_day(2000, 1, 1, 12.0)
    bound = _ephemeris_delta_t(
        modern,
        SimpleNamespace(_kernel_identity=DE440_IDENTITY),
    )
    assert bound.raw.source_product == "iers_eop_direct"
    assert bound.correction_seconds == 0.0
    assert bound.seconds == bound.raw.seconds


@pytest.mark.parametrize(
    "policy",
    (
        DeltaTPolicy(model="fixed", fixed_delta_t=123.0),
        DeltaTPolicy(model="nasa_canon"),
        DeltaTPolicy(model="physical"),
    ),
)
def test_explicit_nonhybrid_policies_are_locked_not_retargeted(
    policy: DeltaTPolicy,
) -> None:
    jd_ut1 = julian_day(-1000, 6, 1, 0.0)
    bound = _ephemeris_delta_t(
        jd_ut1,
        SimpleNamespace(),
        delta_t_policy=policy,
    )
    assert bound.raw.retarget_mode == "policy_locked"
    assert bound.correction_seconds == 0.0
    assert bound.seconds == policy.compute(
        _continuous_decimal_year_from_jd(jd_ut1)
        if policy.model != "fixed"
        else 0.0
    )


@pytest.mark.parametrize("boundary", (-2100.0, -2000.0))
def test_ancient_bridge_retargeting_is_c0_at_source_boundaries(
    boundary: float,
) -> None:
    left = _resolve_delta_t(math.nextafter(boundary, -math.inf))
    at = _resolve_delta_t(boundary)
    right = _resolve_delta_t(math.nextafter(boundary, math.inf))

    left_value = left.retargeted_seconds(_TIDAL_NDOT_DE441)
    at_value = at.retargeted_seconds(_TIDAL_NDOT_DE441)
    right_value = right.retargeted_seconds(_TIDAL_NDOT_DE441)
    assert left_value == pytest.approx(at_value, abs=1.0e-9)
    assert right_value == pytest.approx(at_value, abs=1.0e-9)


def test_direct_eop_and_public_modern_conversion_are_bit_identical() -> None:
    jd_ut1 = julian_day(2000, 1, 1, 12.0)
    resolved = _resolve_delta_t_for_ut1(jd_ut1)
    bound_tt = _ut1_to_ephemeris_tt(jd_ut1, SimpleNamespace())

    assert resolved.source_product == "iers_eop_direct"
    assert bound_tt == ut_to_tt(jd_ut1)


def test_ephemeris_clock_round_trip_uses_same_bound_surface() -> None:
    reader = SimpleNamespace(_kernel_identity=DE441_IDENTITY)
    jd_ut1 = julian_day(-1000, 7, 1, 0.0)
    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, reader)

    assert _ephemeris_tt_to_ut1(jd_tt, reader) == pytest.approx(
        jd_ut1,
        abs=1.0e-11,
    )


def test_eop_edge_retargeting_tapers_to_zero_without_a_clock_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(EOPRegistry, "_data", {60000: 0.1})
    segment = EOPRegistry._segment_bounds(60000, EOPRegistry._ensure_loaded())
    assert segment is not None
    first_ut1 = segment[0]
    epsilon = 1.0e-8

    before = _ephemeris_delta_t(
        first_ut1 - epsilon,
        SimpleNamespace(_kernel_identity=DE441_IDENTITY),
    )
    at = _ephemeris_delta_t(
        first_ut1,
        SimpleNamespace(_kernel_identity=DE441_IDENTITY),
    )
    assert before.seconds == pytest.approx(at.seconds, abs=1.0e-6)
    assert at.raw.source_product == "iers_eop_direct"
    assert at.correction_seconds == 0.0


def test_reader_identity_change_between_raw_and_corrected_tt_fails_closed() -> None:
    jd_ut1 = julian_day(-2000, 1, 1, 0.0)
    raw = _resolve_delta_t_for_ut1(jd_ut1)
    raw_tt = jd_ut1 + raw.seconds / 86400.0
    correction = raw.correction_to(_TIDAL_NDOT_DE441)
    threshold = raw_tt + correction / 172800.0

    class _ChangingReader:
        @staticmethod
        def _ephemeris_kernel_identity_at(jd_tt: float):
            return DE441_IDENTITY if jd_tt < threshold else DE430_IDENTITY

    with pytest.raises(_EphemerisTimeBasisError, match="identity boundary"):
        _ephemeris_delta_t(jd_ut1, _ChangingReader())


def test_kernel_pool_rejects_conflicting_clock_owners_at_one_epoch() -> None:
    def reader(identity: _EphemerisKernelIdentity):
        return SimpleNamespace(
            _kernel_identity=identity,
            has_segment_at=lambda _center, _target, _jd: True,
        )

    pool = KernelPool((reader(DE430_IDENTITY), reader(DE441_IDENTITY)))
    with pytest.raises(ValueError, match="conflicting planetary ephemeris"):
        pool._ephemeris_kernel_identity_at(2451545.0)


@pytest.mark.requires_ephemeris
def test_live_de441_planetary_default_uses_bound_ephemeris_clock(reader) -> None:
    """The default planetary path must consume its kernel-bound TT epoch."""

    identity = reader._kernel_identity
    if identity.planetary_ephemeris != "DE441":
        pytest.skip("live DE441 propagation check requires a DE441 kernel")

    jd_ut1 = julian_day(-2000, 1, 1, 0.0)
    raw_tt = ut_to_tt(jd_ut1)
    bound_tt = _ut1_to_ephemeris_tt(jd_ut1, reader)

    default = planet_at(Body.MOON, jd_ut1, reader=reader)
    explicit_bound = planet_at(
        Body.MOON,
        jd_ut1,
        reader=reader,
        jd_tt=bound_tt,
    )
    explicit_raw = planet_at(
        Body.MOON,
        jd_ut1,
        reader=reader,
        jd_tt=raw_tt,
    )

    assert default.longitude == explicit_bound.longitude
    assert default.latitude == explicit_bound.latitude
    assert default.distance == explicit_bound.distance

    longitude_shift = (
        (default.longitude - explicit_raw.longitude + 180.0) % 360.0
    ) - 180.0
    assert abs(longitude_shift) * 3600.0 > 30.0
