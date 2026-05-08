from __future__ import annotations

import pytest

import moira.nutation_2000a as nut


@pytest.mark.parametrize(
    "jd_tt",
    [
        2451545.0,
        2415020.5,
        2460310.5,
        2488069.5,
    ],
)
def test_native_nutation_2000a_matches_scalar_reference(jd_tt: float) -> None:
    if nut._moira_native is None:
        pytest.skip("native module unavailable")

    ls_terms, pl_terms = nut._ensure_tables_loaded()
    T = nut.centuries_from_j2000(jd_tt)
    fa = nut._fundamental_args(T)
    expected_dpsi, expected_deps = nut._nutation_python(T, fa)
    actual_dpsi, actual_deps = nut.nutation_2000a(jd_tt)

    assert actual_dpsi == pytest.approx(expected_dpsi, abs=1e-13)
    assert actual_deps == pytest.approx(expected_deps, abs=1e-13)

    assert ls_terms
    assert pl_terms
