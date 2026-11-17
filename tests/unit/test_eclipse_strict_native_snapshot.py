"""Opt-in strict scalar snapshot: arithmetic guards and same-record evidence."""
from dataclasses import replace
import math
import subprocess
import sys

import pytest

from moira import _moira_native
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_spk_bounds import conditional_native_type2_bounds, guarded_scalar_snapshot_evaluate


CONTRACT = "moira_eclipse_scalar_snapshot_binary64_rn_gradual_v1"


def _native_capability():
    capability = getattr(_moira_native, "_eclipse_strict_snapshot_build_contract", None)
    evaluate = getattr(_moira_native, "_eclipse_strict_snapshot_evaluate", None)
    assert callable(capability) and callable(evaluate), "native snapshot extension must be rebuilt"
    return capability(), evaluate


def test_strict_snapshot_synthetic_record_and_terminal_endpoint():
    contract, evaluate = _native_capability()
    record = ((1., 2., 3.), (4., 5., 6.), (7., 8., 9.))
    if contract != CONTRACT:
        with pytest.raises(ValueError, match="eclipse_snapshot_"):
            evaluate(record, 2451545., .5, 0., 86400., 1, 0, 0., 86400.)
        return
    position, velocity, s, index = evaluate(record, 2451545., .5, 0., 86400., 1, 0, 0., 86400.)
    assert index == 0 and s == 0.0
    assert tuple(position) == (-2., -2., -2.)
    assert tuple(velocity) == (4., 10., 16.)
    position, velocity, s, index = evaluate(record, 2451545., 1., 0., 86400., 1, 0, 0., 86400.)
    assert index == 0 and s == 1.0
    assert tuple(position) == (6., 15., 24.)
    assert tuple(velocity) == (28., 58., 88.)


def test_snapshot_rejects_outside_descriptor_or_wrong_record():
    contract, evaluate = _native_capability()
    if contract != CONTRACT:
        pytest.skip("strict snapshot is explicitly unavailable on this build/architecture")
    record = ((1., 2.), (3., 4.), (5., 6.))
    with pytest.raises(ValueError, match="descriptor_coverage_failure"):
        evaluate(record, 2451545., -0.1, 0., 86400., 1, 0, 0., 86400.)
    with pytest.raises(ValueError, match="record_mismatch"):
        evaluate(record, 2451545., 0.75, 0., 43200., 2, 0, 0., 86400.)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_tdb", [1026285.7107341307, 2451545.0, 2460409.262])
@pytest.mark.parametrize("center,target", [(0, 3), (0, 10), (3, 301), (3, 399)])
@pytest.mark.parametrize("offset", [-0.0001, 0.0001])
def test_guarded_snapshot_is_contained_and_tracks_legacy_sample(
    planetary_reader, jd_tdb, center, target, offset,
):
    contract, _ = _native_capability()
    if contract != CONTRACT:
        pytest.skip("strict snapshot is explicitly unavailable on this build/architecture")
    bounds = conditional_native_type2_bounds(planetary_reader, center, target, jd_tdb, I.point(offset))
    result = guarded_scalar_snapshot_evaluate(bounds, offset)
    legacy_position, legacy_velocity = planetary_reader._position_and_velocity_tdb_offset(center, target, jd_tdb, offset)
    assert not result.independent_build_receipt_verified
    assert not result.legacy_mapped_evaluator_certified
    assert result.record_snapshot_sha256 == bounds.record_snapshot_sha256
    for calculated, legacy in zip(result.position_km, legacy_position):
        assert abs(calculated - legacy) < 1e-6  # 1 mm, same-DE441 numerical comparison only.
    for calculated, legacy in zip(result.velocity_km_per_day, legacy_velocity):
        assert abs(calculated - legacy) < 1e-3  # 1 mm/day numerical comparison, not a physical bound.


@pytest.mark.requires_ephemeris
def test_guarded_snapshot_detects_tampered_record(planetary_reader):
    contract, _ = _native_capability()
    if contract != CONTRACT:
        pytest.skip("strict snapshot is explicitly unavailable on this build/architecture")
    bounds = conditional_native_type2_bounds(planetary_reader, 0, 3, 2451545.0, I.point(0.0001))
    changed = list(bounds.record_snapshot[0])
    changed[-1] = math.nextafter(changed[-1], math.inf)
    forged = replace(bounds, record_snapshot=(tuple(changed), *bounds.record_snapshot[1:]))
    with pytest.raises(ValueError, match="snapshot identity"):
        guarded_scalar_snapshot_evaluate(forged, 0.0001)
    forged_domain = replace(bounds, offset_days=I(0, 1))
    with pytest.raises(ValueError, match="snapshot identity"):
        guarded_scalar_snapshot_evaluate(forged_domain, 0.0001)


def test_unavailable_build_never_reports_guarded_scalar_success():
    contract, evaluate = _native_capability()
    if contract == CONTRACT:
        return
    with pytest.raises(ValueError, match="eclipse_snapshot_"):
        evaluate(((1.,), (2.,), (3.,)), 2451545., .5, 0., 86400., 1, 0, 0., 86400.)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows CRT rounding-mode probe")
def test_guard_rejects_changed_thread_rounding_and_restores_test_state():
    # The test itself always restores its thread's original CRT environment.
    import ctypes

    contract, evaluate = _native_capability()
    if contract != CONTRACT:
        pytest.skip("strict snapshot is explicitly unavailable on this build/architecture")
    try:
        control = ctypes.CDLL("ucrtbase")._controlfp_s
    except (OSError, AttributeError):
        pytest.skip("UCRT control function unavailable")
    control.argtypes = (ctypes.POINTER(ctypes.c_uint), ctypes.c_uint, ctypes.c_uint)
    control.restype = ctypes.c_int
    saved = ctypes.c_uint()
    assert control(ctypes.byref(saved), 0, 0) == 0
    current = ctypes.c_uint()
    mask_rounding, toward_negative = 0x00000300, 0x00000100
    record = ((1.,), (2.,), (3.,))
    try:
        assert control(ctypes.byref(current), toward_negative, mask_rounding) == 0
        with pytest.raises(ValueError, match="eclipse_snapshot_requires_"):
            evaluate(record, 2451545., .5, 0., 86400., 1, 0, 0., 86400.)
    finally:
        assert control(ctypes.byref(current), saved.value, mask_rounding) == 0
    evaluate(record, 2451545., .5, 0., 86400., 1, 0, 0., 86400.)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows UCRT denormal-mode probe")
def test_guard_rejects_ftz_daz_in_isolated_process():
    contract, _ = _native_capability()
    if contract != CONTRACT:
        pytest.skip("strict snapshot is explicitly unavailable on this build/architecture")
    script = r'''
import ctypes, sys
from moira import _moira_native as native
try:
    control = ctypes.CDLL("ucrtbase")._controlfp_s
except (OSError, AttributeError):
    sys.exit(77)
control.argtypes = (ctypes.POINTER(ctypes.c_uint), ctypes.c_uint, ctypes.c_uint)
control.restype = ctypes.c_int
saved, current = ctypes.c_uint(), ctypes.c_uint()
if control(ctypes.byref(saved), 0, 0) != 0:
    sys.exit(77)
mask_denormals, flush_denormals = 0x03000000, 0x01000000
try:
    if control(ctypes.byref(current), flush_denormals, mask_denormals) != 0:
        sys.exit(77)
    if (current.value & mask_denormals) != flush_denormals:
        sys.exit(77)
    try:
        native._eclipse_strict_snapshot_evaluate(
            ((1.,), (2.,), (3.,)), 2451545., .5, 0., 86400., 1, 0, 0., 86400.
        )
    except ValueError as exc:
        if "eclipse_snapshot_requires_nearest_and_gradual_underflow" not in str(exc):
            raise
    else:
        raise AssertionError("FTZ/DAZ mode was accepted")
finally:
    if control(ctypes.byref(current), saved.value, mask_denormals) != 0:
        raise RuntimeError("could not restore UCRT denormal mode")
'''
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script], capture_output=True, text=True, timeout=30, check=False,
    )
    if completed.returncode == 77:
        pytest.skip("UCRT cannot expose or change denormal mode on this platform")
    assert completed.returncode == 0, completed.stdout + completed.stderr
