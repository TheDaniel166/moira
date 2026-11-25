"""NAIF SPK Type 13 validity and legacy Moira compatibility."""

import math
import struct

import pytest

from moira import moira_native
from moira import _spk_body_kernel
from moira.daf_writer import write_spk_type13

_TARGET = 2000001
_J2000 = 2451545.0
_DAY = 86400.0
_DAYS = (0, 2, 3, 5, 8, 13, 21, 25, 30, 32, 33, 37, 41, 43, 44, 47)
_EPOCHS = [_J2000 + day for day in _DAYS]


def _states():
    rates = (0.25, 0.18, 0.31)
    return [
        *[[1000 * math.sin(rate * day) for day in _DAYS] for rate in rates],
        *[[1000 * rate * math.cos(rate * day) / _DAY for day in _DAYS] for rate in rates],
    ]


def _write(path, window):
    write_spk_type13(path, [{
        "naif_id": _TARGET, "epochs_jd": _EPOCHS, "states": _states(), "window_size": window,
    }], locifn="MOIRA UNIFIED ASTEROID CATALOG")
    return moira_native.read_daf_catalog(str(path))["summaries"][0]["descriptor"]


def _read_trailer(path, descriptor):
    with path.open("rb") as stream:
        stream.seek((descriptor[-1] - 2) * 8)
        return struct.unpack("<2d", stream.read(16))


def _state(reader, tdb, tdb2=0.0):
    position, velocity = reader._kernel.segments[0].compute_and_differentiate(tdb, tdb2)
    return [*position, *(value / _DAY for value in velocity)]


@pytest.mark.parametrize("window", [1, 7, 8, 14])
def test_type13_writer_trailer_and_naif_evaluation(tmp_path, monkeypatch, window):
    spice = pytest.importorskip("spiceypy")
    path = tmp_path / "standard.bsp"
    desc = _write(path, window)
    assert _read_trailer(path, desc) == (window - 1, len(_EPOCHS))

    # Exercise the split epoch route and NAIF centering on nonuniform data.
    time_pairs = [(tdb, 0.0) for tdb in _EPOCHS]
    time_pairs += [(_J2000, i / 8) for i in range(1, 47 * 8)]
    time_pairs += [(_J2000 + 21.0, 0.125 + 1e-11)]
    reader = _spk_body_kernel.SmallBodyKernel(path)
    try:
        with spice.KernelPool(str(path)):
            for force_python in (False, True):
                monkeypatch.setattr(_spk_body_kernel, "_FORCE_PYTHON_TYPE13_FALLBACK", force_python)
                for tdb, offset in time_pairs:
                    et = (tdb - _J2000) * _DAY + offset * _DAY
                    expected, _ = spice.spkgeo(_TARGET, et, "J2000", 10)
                    actual = _state(reader, tdb, offset)
                    assert actual[:3] == pytest.approx(expected[:3], abs=1e-8)
                    assert actual[3:] == pytest.approx(expected[3:], abs=1e-11)
    finally:
        reader.close()


def test_legacy_type13_opt_in_and_named_autodetection(tmp_path, monkeypatch):
    path = tmp_path / "legacy.bsp"
    desc = _write(path, 8)
    assert _read_trailer(path, desc)[0] == 7
    jd = _J2000 + 19.125
    expected = moira_native.spk_type13_record(_EPOCHS, _states(), 7, jd)
    expected = [*expected[:3], *(value / _DAY for value in expected[3:])]
    for label, selection in (
        (b"MOIRA UNIFIED ASTEROID CATALOG", None),
        (b"User-created legacy kernel", True),
    ):
        with path.open("r+b") as stream:
            stream.seek(16)
            stream.write(label.ljust(60, b"\0"))
        reader = _spk_body_kernel.SmallBodyKernel(path, legacy_type13=selection)
        try:
            for force_python in (False, True):
                monkeypatch.setattr(_spk_body_kernel, "_FORCE_PYTHON_TYPE13_FALLBACK", force_python)
                assert _state(reader, jd) == pytest.approx(expected, abs=1e-11)
        finally:
            reader.close()
    standard = _spk_body_kernel.SmallBodyKernel(path)
    try:
        assert max(abs(x - y) for x, y in zip(_state(standard, jd), expected, strict=True)) > 1e-5
    finally:
        standard.close()


def test_type13_reader_preserves_external_epoch_seconds(tmp_path):
    spice = pytest.importorskip("spiceypy")
    path = tmp_path / "naif-with-nonrounded-et.bsp"
    # Write raw ET tags deliberately between full-JD floating-point ticks.
    tags = [float(day) * _DAY + 0.01234567 for day in _DAYS]
    columns = _states()
    handle = spice.spkopn(str(path), "CSPICE created", 0)
    try:
        spice.spkw13(handle, _TARGET, 10, "J2000", tags[0], tags[-1], "fixture", 13,
                     len(tags), list(zip(*columns, strict=True)), tags)
    finally:
        spice.spkcls(handle)
    jd = _J2000 + 19
    offset = 0.125 + 0.00000023
    reader = _spk_body_kernel.SmallBodyKernel(path)
    try:
        with spice.KernelPool(str(path)):
            expected, _ = spice.spkgeo(_TARGET, (jd - _J2000) * _DAY + offset * _DAY, "J2000", 10)
        actual = _state(reader, jd, offset)
        assert actual[:3] == pytest.approx(expected[:3], abs=1e-8)
        assert actual[3:] == pytest.approx(expected[3:], abs=1e-11)
    finally:
        reader.close()
