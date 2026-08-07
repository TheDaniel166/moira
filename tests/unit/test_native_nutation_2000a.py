from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys

import pytest

from evidence.contracts import (
    NUTATION_DEPS_PARITY_COMPARISON,
    NUTATION_DPSI_PARITY_COMPARISON,
)
import moira.nutation_2000a as nut
from moira import moira_native


@pytest.mark.parametrize(
    "jd_tt",
    [
        2451545.0,
        2415020.5,
        2460310.5,
        2488069.5,
    ],
)
@pytest.mark.validation_contract(
    "MOIRA-NUTATION-2000A-PY-NATIVE-PARITY-V1"
)
@pytest.mark.parallel(reason="worker_isolated")
def test_native_nutation_2000a_matches_scalar_reference(jd_tt: float) -> None:
    if nut._moira_native is None:
        pytest.fail(
            "admitted native-parity evidence requires the project native module",
            pytrace=False,
        )

    ls_terms, pl_terms = nut._ensure_tables_loaded()
    T = nut.centuries_from_j2000(jd_tt)
    fa = nut._fundamental_args(T)
    expected_dpsi, expected_deps = nut._nutation_python(T, fa)
    actual_dpsi, actual_deps = nut.nutation_2000a(jd_tt)

    dpsi_residual = abs(actual_dpsi - expected_dpsi)
    deps_residual = abs(actual_deps - expected_deps)
    assert dpsi_residual <= NUTATION_DPSI_PARITY_COMPARISON.absolute, (
        f"delta psi residual {dpsi_residual!r} exceeds the absolute-only "
        f"contract bound {NUTATION_DPSI_PARITY_COMPARISON.absolute!r} degrees"
    )
    assert deps_residual <= NUTATION_DEPS_PARITY_COMPARISON.absolute, (
        f"delta epsilon residual {deps_residual!r} exceeds the absolute-only "
        f"contract bound {NUTATION_DEPS_PARITY_COMPARISON.absolute!r} degrees"
    )

    assert len(ls_terms) == 1358
    assert len(pl_terms) == 1056
    assert nut._LS_J0_COUNT == 1320
    assert nut._PL_J0_COUNT == 1037
    assert all(len(term) == 16 for term in ls_terms)
    assert all(len(term) == 16 for term in pl_terms)


def test_native_nutation_series_rejects_invalid_replacement() -> None:
    nut._ensure_tables_loaded()
    with pytest.raises(ValueError, match="longitude nutation table is empty"):
        moira_native.set_nutation_2000a_tables([], [(1.0, 2.0, 0)], 0, 1)

    # A rejected replacement must leave the published immutable snapshot live.
    assert moira_native.nutation_2000r06_series_ready() is True
    assert all(map(lambda value: value == value, moira_native.nutation_2000a(2451545.0)))


def test_native_nutation_series_is_safe_for_concurrent_readers() -> None:
    epochs = [2415020.5 + index * 3652.5 for index in range(20)]
    expected = [moira_native.nutation_2000a(jd) for jd in epochs]

    with ThreadPoolExecutor(max_workers=8) as pool:
        actual = list(pool.map(moira_native.nutation_2000a, epochs * 8))

    assert actual == pytest.approx(expected * 8, abs=1e-13)


def test_python_shim_initializes_cold_native_process_before_evaluation() -> None:
    script = """
import moira._moira_native as raw
assert raw.nutation_2000r06_series_ready() is False
try:
    raw.nutation_2000a(2451545.0)
except RuntimeError as error:
    assert 'not registered' in str(error)
else:
    raise AssertionError('raw native core must fail before table registration')
from moira import moira_native
result = moira_native.nutation_2000a(2451545.0)
assert len(result) == 2
assert raw.nutation_2000r06_series_ready() is True
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
