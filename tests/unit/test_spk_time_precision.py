"""SPK record-local time against exact rational polynomial arithmetic.

The synthetic type-2/3 segments reproduce a long DE440s segment's time
geometry without requiring a downloaded kernel. Positions are km, native
type-2 velocities km/day, type-3 stored velocities km/s; ET uses the same
binary64 JD-to-seconds contract as CSPICE.
"""

import math
import struct
from fractions import Fraction as F

import pytest

from moira import moira_native
from moira import _spk_body_kernel as small
from moira import spk_reader as planetary


INIT = -4734072000.0
INTLEN = 691200.0
COUNT = 12740
WORST_JD = 2498657.0966907064
SPEED = (58.0, -17.0, 11.0)
CURVE = (3.0, -4.0, 5.0)


def _write_spk(path, data_type):
    components = 3 if data_type == 2 else 6
    rsize = 2 + 3 * components
    words = []
    for index in range(COUNT):
        words.extend((INIT + (index + 0.5) * INTLEN, INTLEN / 2))
        for axis in range(3):
            words.extend((float(index * (axis + 1)), SPEED[axis] * INTLEN / 2, CURVE[axis]))
        if data_type == 3:
            for axis in range(3):
                words.extend((SPEED[axis], 4 * CURVE[axis] / (INTLEN / 2), 0.0))
    words.extend((INIT, INTLEN, float(rsize), float(COUNT)))
    start_i = 641
    end_i = start_i + len(words) - 1
    header = bytearray(5 * 1024)
    header[0:8] = b"DAF/SPK "
    struct.pack_into("<ii", header, 8, 2, 6)
    header[16:76] = b"MOIRA RECORD TIME PRECISION".ljust(60)
    struct.pack_into("<iii", header, 76, 4, 4, end_i + 1)
    header[88:96] = b"LTL-IEEE"
    struct.pack_into("<ddd", header, 3 * 1024, 0.0, 0.0, 1.0)
    descriptor = (INIT, INIT + COUNT * INTLEN, 1, 0, 1, data_type, start_i, end_i)
    struct.pack_into("<ddiiiiii", header, 3 * 1024 + 24, *descriptor)
    header[4 * 1024:4 * 1024 + 40] = b"SYNTHETIC LONG CHEBYSHEV SEGMENT".ljust(40)
    payload = header + struct.pack(f"<{len(words)}d", *words)
    payload.extend(bytes(-len(payload) % 1024))
    path.write_bytes(payload)
    return descriptor


@pytest.fixture(scope="module", params=[2, 3])
def synthetic(request, tmp_path_factory):
    path = tmp_path_factory.mktemp("record_time") / f"type{request.param}.bsp"
    descriptor = _write_spk(path, request.param)
    return path, descriptor


def _oracle(jd, jd2=0.0):
    # Exact rational record selection and evaluation, independent of the
    # implementation's segment-wide subtraction and Clenshaw recurrence.
    seconds = F.from_float((jd - 2451545.0) * 86400.0) + F.from_float(jd2 * 86400.0)
    index = min(int((seconds - F(INIT)) // F(INTLEN)), COUNT - 1)
    midpoint = F(INIT) + (F(index) + F(1, 2)) * F(INTLEN)
    s = (seconds - midpoint) / F(INTLEN / 2)
    position = tuple(float(index * (axis + 1) + F(SPEED[axis]) * F(INTLEN / 2) * s
                           + F(CURVE[axis]) * (2 * s * s - 1)) for axis in range(3))
    velocity = tuple(float((F(SPEED[axis]) + 4 * F(CURVE[axis]) * s / F(INTLEN / 2))
                           * 86400) for axis in range(3))
    return position, velocity


def _segment(synthetic, owner, monkeypatch):
    path, descriptor = synthetic
    if owner == "native_standalone":
        return moira_native.load_spk_segment_evaluator(str(path), *descriptor[-2:], True, descriptor[5])
    if owner == "native_handle":
        handle = moira_native.open_spk_kernel(str(path))
        try:
            return handle.load_segment_evaluator(*descriptor[-2:], descriptor[5])
        finally:
            handle.close()
    module = planetary if owner == "planetary_fallback" else small
    segment = module._NativeChebyshevSegment(path, b"SYNTHETIC", descriptor, True)
    # Supply the canonical native-decoded tensor to isolate time arithmetic
    # from each wrapper's payload-admission and coefficient-order policy.
    payload = moira_native.read_spk_chebyshev_segment_payload(
        str(path), *descriptor[-2:], True, descriptor[5]
    )
    segment._data = (payload["init"], payload["intlen"], payload["coefficients"])
    monkeypatch.setattr(segment, "_load_native_evaluator", lambda: None)
    if module is planetary:
        segment._native_evaluator = None
    return segment


@pytest.mark.parametrize("owner", ["native_standalone", "native_handle", "planetary_fallback", "small_body_fallback"])
@pytest.mark.parametrize("split", [False, True])
def test_long_segment_time_preserves_record_local_precision(synthetic, monkeypatch, owner, split):
    if synthetic[1][5] == 3 and "fallback" in owner:
        pytest.skip("Python type-3 velocity policy is outside this type-2/3 native time repair")
    segment = _segment(synthetic, owner, monkeypatch)
    jd, jd2 = (2451545.0, WORST_JD - 2451545.0) if split else (WORST_JD, 0.0)
    expected_position, expected_velocity = _oracle(jd, jd2)
    if owner.startswith("native"):
        position, velocity = segment.position_and_velocity(jd, jd2)
        if synthetic[1][5] == 3:
            expected_velocity = tuple(value / 86400 for value in expected_velocity)
    else:
        position, velocity = segment.compute_and_differentiate(jd, jd2)
    # 50 micrometres allows Clenshaw/output rounding for ~10^7 km components;
    # the original lost microsecond produces several centimetres of error.
    assert position == pytest.approx(expected_position, rel=0.0, abs=5e-8)
    assert velocity == pytest.approx(expected_velocity, rel=0.0, abs=2e-9)
    if owner == "planetary_fallback" and not split:
        assert planetary._native_position(segment, jd) == pytest.approx(expected_position, rel=0.0, abs=5e-8)


@pytest.mark.parametrize("owner", ["native_standalone", "native_handle", "planetary_fallback", "small_body_fallback"])
def test_record_boundary_ownership_split_epochs_and_closed_end(synthetic, monkeypatch, owner):
    if synthetic[1][5] == 3 and "fallback" in owner:
        pytest.skip("Only native type-3 policy is in scope")
    segment = _segment(synthetic, owner, monkeypatch)
    evaluate = segment.position if owner.startswith("native") else segment.compute
    boundary = 2451545.0 + (INIT + 12738 * INTLEN) / 86400.0
    start = 2451545.0 + INIT / 86400.0
    end = 2451545.0 + (INIT + COUNT * INTLEN) / 86400.0
    for jd, jd2 in [(start, 0.0), (end, 0.0), (boundary, 0.0),
                    (math.nextafter(boundary, -math.inf), 0.0),
                    (math.nextafter(boundary, math.inf), 0.0),
                    (boundary, -1e-9), (boundary, 1e-9)]:
        assert evaluate(jd, jd2) == pytest.approx(_oracle(jd, jd2)[0], rel=0.0, abs=5e-8)
    for outside in [math.nextafter(start, -math.inf), math.nextafter(end, math.inf)]:
        with pytest.raises((ValueError, planetary.OutOfRangeError, small.OutOfRangeError)):
            evaluate(outside)


def test_legacy_native_chebyshev_evaluator_preserves_record_time(synthetic):
    path, descriptor = synthetic
    payload = moira_native.read_spk_chebyshev_segment_payload(
        str(path), *descriptor[-2:], True, descriptor[5]
    )
    coefficients = payload["coefficients"]
    evaluator = moira_native.ChebyshevEvaluator(
        INIT, INTLEN, COUNT, len(coefficients[0]), len(coefficients[0][0]),
        [value for record in coefficients for component in record for value in component],
    )
    assert evaluator.evaluate(WORST_JD)[:3] == pytest.approx(_oracle(WORST_JD)[0], rel=0.0, abs=5e-8)


def test_event_enclosures_contain_exact_record_local_time():
    from moira._event_search.astronomy import record_arguments
    from moira._event_search.frames import Differential

    boundary = 2451545.0 + (INIT + 12738 * INTLEN) / 86400.0
    cases = [(INIT, COUNT, jd) for jd in (
        WORST_JD, boundary, math.nextafter(boundary, -math.inf),
        math.nextafter(boundary, math.inf), 2451545.0 + INIT / 86400.0,
        2451545.0 + (INIT + COUNT * INTLEN) / 86400.0,
    )]
    # A much longer segment exercises the larger segment-offset rounding
    # scale without allocating a correspondingly large synthetic SPK file.
    cases.append((-473407200000.0, 2000000, WORST_JD))
    for init, count, jd in cases:
        seconds = F.from_float((jd - 2451545.0) * 86400.0)
        index = min(int((seconds - F(init)) // F(INTLEN)), count - 1)
        midpoint = F(init) + (F(index) + F(1, 2)) * F(INTLEN)
        expected = float((seconds - midpoint) / F(INTLEN / 2))
        branches = record_arguments(Differential.point(jd), init, INTLEN, count)
        assert any(
            record_index == index and argument.value.lo <= expected <= argument.value.hi
            for record_index, argument in branches
        )
