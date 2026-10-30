"""Native SPK evaluator against CSPICE at segment endpoints, record boundaries and outside the window.

A synthetic type-2 kernel with deliberately discontinuous records makes record-ownership
disagreements visible: any epoch assigned to the wrong record differs by hundreds of km.
"""
import math
import struct

import pytest

spice = pytest.importorskip("spiceypy")

from moira.spk_reader import SpkReader  # noqa: E402

J2000 = 2451545.0
INIT = 0.0                      # ET at J2000
INTLEN = 4 * 86400.0            # four-day records
COUNT = 8
CENTER, TARGET = 0, 1


def _write(path):
    rsize = 2 + 3 * 3
    words = []
    for k in range(COUNT):
        words += [INIT + (k + 0.5) * INTLEN, INTLEN / 2]
        for axis in range(3):
            words += [100.0 * (k + 1) * (axis + 1), 7.0 * (axis + 1) * (k + 1), -2.5 * (axis + 2)]
    words += [INIT, INTLEN, float(rsize), float(COUNT)]
    start_i, end_i = 641, 641 + len(words) - 1
    header = bytearray(5 * 1024)
    header[0:8] = b"DAF/SPK "
    struct.pack_into("<ii", header, 8, 2, 6)
    header[16:76] = b"MOIRA SPK BOUNDARY TEST".ljust(60)
    struct.pack_into("<iii", header, 76, 4, 4, end_i + 1)
    header[88:96] = b"LTL-IEEE"
    struct.pack_into("<ddd", header, 3 * 1024, 0.0, 0.0, 1.0)
    struct.pack_into("<ddiiiiii", header, 3 * 1024 + 24,
                     INIT, INIT + COUNT * INTLEN, TARGET, CENTER, 1, 2, start_i, end_i)
    header[4 * 1024:4 * 1024 + 24] = b"SYNTHETIC BOUNDARY SEG ".ljust(24)
    payload = header + struct.pack(f"<{len(words)}d", *words)
    payload.extend(bytes(-len(payload) % 1024))
    path.write_bytes(payload)


@pytest.fixture(scope="module")
def kernel(tmp_path_factory):
    path = tmp_path_factory.mktemp("spk_boundaries") / "boundaries.bsp"
    _write(path)
    spice.kclear()
    spice.furnsh(str(path))
    reader = SpkReader(path)
    yield reader
    reader.close()
    spice.kclear()


def _cspice(jd):
    state, _ = spice.spkez(TARGET, (jd - J2000) * 86400.0, "J2000", "NONE", CENTER)
    return state[:3], state[3:]


def _interior_boundaries():
    return [J2000 + k * INTLEN / 86400.0 for k in range(1, COUNT)]


def _check(reader, jd):
    pos, vel = reader.position_and_velocity_tdb(CENTER, TARGET, jd)
    ref_pos, ref_vel = _cspice(jd)
    for a, b in zip(pos, ref_pos):
        assert a == pytest.approx(b, abs=1e-7), f"position at JD {jd!r}"
    for a, b in zip(vel, ref_vel):
        assert a == pytest.approx(b * 86400.0, abs=1e-5), f"velocity at JD {jd!r}"


def test_segment_endpoints_match_cspice(kernel) -> None:
    _check(kernel, J2000)
    _check(kernel, J2000 + COUNT * INTLEN / 86400.0)  # closed end


@pytest.mark.parametrize("k", range(1, COUNT))
def test_record_boundaries_and_neighbours_match_cspice(kernel, k) -> None:
    boundary = J2000 + k * INTLEN / 86400.0
    _check(kernel, boundary)                          # ownership: later record
    _check(kernel, math.nextafter(boundary, math.inf))
    _check(kernel, boundary + 1e-3)
    _check(kernel, boundary - 1e-3)


def test_mid_record_epochs_match_cspice(kernel) -> None:
    for k in range(COUNT):
        _check(kernel, J2000 + (k + 0.5) * INTLEN / 86400.0)


@pytest.mark.parametrize("offset_days", [-1e-3, 1e-3])
def test_both_reject_epochs_outside_the_window(kernel, offset_days) -> None:
    jd = (J2000 if offset_days < 0 else J2000 + COUNT * INTLEN / 86400.0) + offset_days
    with pytest.raises(Exception):
        kernel.position_tdb(CENTER, TARGET, jd)
    with pytest.raises(Exception):
        _cspice(jd)
