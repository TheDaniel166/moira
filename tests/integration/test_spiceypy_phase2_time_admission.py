"""Parity checks for the admitted native NAIF LSK time-admission path."""

from __future__ import annotations

import pytest
import spiceypy as sp

from moira.lunar_limb import _default_cache_root, _ensure_kernels_loaded, _jd_ut_to_et

try:
    from moira import _moira_native as moira_native
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False


_CURATED_EPOCHS_JD = (
    2441317.5,   # 1972-01-01 leap-second baseline
    2451545.0,   # J2000
    2457754.5,   # 2017-01-01 leap-second boundary
    2460800.5,   # modern post-2017 epoch
)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.serial
@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native backend not available")
def test_native_jd_time_admission_matches_spice_str2et():
    cache_root = _default_cache_root()
    _ensure_kernels_loaded(cache_root)

    lsk_path = cache_root / "kernels" / "naif0012.tls"
    assert lsk_path.exists(), f"Expected cached NAIF LSK at {lsk_path}"

    sp.kclear()
    sp.furnsh(str(lsk_path))

    for jd_utc in _CURATED_EPOCHS_JD:
        expected = sp.str2et(f"JD {jd_utc}")
        actual = moira_native.jd_utc_to_et_seconds_past_j2000(jd_utc)
        assert actual == pytest.approx(expected, abs=1e-10), f"Parity failure at JD {jd_utc}"
        assert _jd_ut_to_et(jd_utc) == pytest.approx(expected, abs=1e-10)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.serial
@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native backend not available")
def test_pre1972_epochs_remain_on_spice_fallback():
    cache_root = _default_cache_root()
    _ensure_kernels_loaded(cache_root)
    lsk_path = cache_root / "kernels" / "naif0012.tls"

    sp.kclear()
    sp.furnsh(str(lsk_path))

    historical_jd_utc = 2415020.0
    with pytest.raises(RuntimeError, match="pre-1972 UTC epochs"):
        moira_native.jd_utc_to_et_seconds_past_j2000(historical_jd_utc)

    expected = sp.str2et(f"JD {historical_jd_utc}")
    assert _jd_ut_to_et(historical_jd_utc) == pytest.approx(expected, abs=1e-10)
