"""Stage 1 contracts for the SPK TT/TDB clock boundary."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import (
    _EphemerisTimeBasisError,
    _bind_ephemeris_time,
)
from moira.julian import (
    NAIF_LSK_TT_TDB_POLICY,
    NAIF_LSK_TT_TDB_SOURCE_BYTES,
    NAIF_LSK_TT_TDB_SOURCE_SHA256,
    NAIF_LSK_TT_TDB_SOURCE_URL,
    NAIF_LSK_TT_TDB_VERSION,
    _resolve_delta_t_for_ut1,
    _tt_to_tdb_with_receipt,
    julian_day,
    tdb_to_tt,
    tt_to_tdb,
)
from moira.spk_reader import _EphemerisKernelIdentity


DE430 = _EphemerisKernelIdentity("DE-0430LE-0430", "DE430", "LE430", -25.85)
DE441 = _EphemerisKernelIdentity("DE-0441LE-0441", "DE441", "LE441", -25.936)
TIME_AUTHORITY = json.loads(
    (
        Path(__file__).parents[1]
        / "fixtures"
        / "orbital_time_naif0012_reference.json"
    ).read_text(encoding="utf-8")
)


def test_naif0012_policy_metadata_is_frozen() -> None:
    assert NAIF_LSK_TT_TDB_POLICY == "NAIF_LSK_DELTET"
    assert NAIF_LSK_TT_TDB_VERSION == "naif0012"
    assert NAIF_LSK_TT_TDB_SOURCE_URL == (
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls"
    )
    assert NAIF_LSK_TT_TDB_SOURCE_BYTES == 5257
    assert NAIF_LSK_TT_TDB_SOURCE_SHA256 == (
        "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b"
    )


@pytest.mark.parametrize("case", TIME_AUTHORITY["time_cases"])
def test_frozen_naif0012_equation_values(case: dict[str, float]) -> None:
    receipt = _tt_to_tdb_with_receipt(case["jd_tt"])

    assert receipt.tdb_minus_tt_seconds == pytest.approx(
        case["tdb_minus_tt_seconds"], abs=2.0e-18
    )
    assert receipt.iterations == case["iterations"]
    assert receipt.epoch_tdb == case["jd_tdb"]
    assert receipt.epoch_tdb == math.fsum(
        (case["jd_tt"], receipt.tdb_minus_tt_seconds / 86400.0)
    )


@pytest.mark.parametrize(
    "jd_tt",
    (1000000.25, 2433282.5, 2451545.0, 2461298.5, 4000000.75),
)
def test_public_single_part_round_trip_is_within_one_binary64_ulp(
    jd_tt: float,
) -> None:
    recovered = tdb_to_tt(tt_to_tdb(jd_tt))
    assert abs(recovered - jd_tt) <= math.ulp(jd_tt)


@pytest.mark.parametrize("bad", (True, False, float("nan"), float("inf"), -float("inf")))
def test_tt_tdb_conversion_rejects_non_coordinates(bad: float) -> None:
    with pytest.raises(ValueError):
        tt_to_tdb(bad)
    with pytest.raises(ValueError):
        tdb_to_tt(bad)


def test_tt_tdb_conversion_rejects_unrepresentable_single_part_jd() -> None:
    with pytest.raises(ValueError, match="represent"):
        tt_to_tdb(1.0e20)
    with pytest.raises(ValueError, match="represent"):
        tdb_to_tt(1.0e20)


def test_native_and_python_naif_converters_agree() -> None:
    from moira import moira_native

    for jd_tt in (2433282.5, 2451545.0, 2461298.5, 2470171.5):
        assert moira_native.TtToTdbEvaluator.convert(jd_tt) == tt_to_tdb(jd_tt)


def test_ephemeris_time_binding_converges_on_one_tdb_identity() -> None:
    calls: list[float] = []

    class Reader:
        @staticmethod
        def _ephemeris_kernel_identity_at_tdb(epoch_tdb: float):
            calls.append(epoch_tdb)
            return DE441

    jd_ut1 = julian_day(-2000, 1, 1, 0.0)
    bound = _bind_ephemeris_time(jd_ut1, Reader())

    assert bound.identity is DE441
    assert bound.identity_iterations == 2
    assert bound.epoch_tdb == tt_to_tdb(bound.epoch_tt)
    assert calls == [calls[0], bound.epoch_tdb]
    assert calls[0] != calls[1]


def test_ephemeris_time_binding_fails_on_identity_oscillation() -> None:
    jd_ut1 = julian_day(-2000, 1, 1, 0.0)
    raw = _resolve_delta_t_for_ut1(jd_ut1)
    raw_tt = math.fsum((jd_ut1, raw.seconds / 86400.0))
    corrected_tt = math.fsum(
        (jd_ut1, raw.retargeted_seconds(-25.936) / 86400.0)
    )
    threshold = (tt_to_tdb(raw_tt) + tt_to_tdb(corrected_tt)) / 2.0

    class OscillatingReader:
        @staticmethod
        def _ephemeris_kernel_identity_at_tdb(epoch_tdb: float):
            return DE441 if epoch_tdb < threshold else DE430

    with pytest.raises(_EphemerisTimeBasisError) as caught:
        _bind_ephemeris_time(jd_ut1, OscillatingReader())

    assert caught.value.iterations == 6
    assert caught.value.provisional_identity_label == "DE-0441LE-0441"
    assert caught.value.direction == "UT1_TO_TDB"


def test_ephemeris_time_binding_requires_an_identified_source() -> None:
    class UnidentifiedReader:
        @staticmethod
        def _ephemeris_kernel_identity_at_tdb(_epoch_tdb: float):
            return None

    with pytest.raises(_EphemerisTimeBasisError, match="content-identified") as caught:
        _bind_ephemeris_time(julian_day(2000, 1, 1, 12.0), UnidentifiedReader())

    assert caught.value.final_identity_label is None
    assert caught.value.source_product == "iers_eop_direct"
