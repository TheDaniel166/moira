"""
Adversarial native DAF/SPK reader tests for Moira.

These tests target the native reader substrate directly rather than the higher
planetary facade. They force hostile summary metadata, exact coverage
boundaries, unsupported segment admission, split-segment coverage ownership,
and boundary-near record extraction.

The forbidden outcome is silent semantic drift.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

import moira._spk_body_kernel as body_kernel
import moira.spk_reader as spk_reader
from moira._spk_body_kernel import OutOfRangeError, SmallBodyKernel, _NativeChebyshevSegment
from moira.daf_writer import write_spk_type13


_ONE_SECOND_JD = 1.0 / 86400.0


def _synthetic_type13_kernel(path: Path) -> None:
    write_spk_type13(
        path,
        bodies=[
            {
                "naif_id": 2000433,
                "center": 10,
                "frame": 1,
                "name": "EROS SAMPLE",
                "window_size": 3,
                "epochs_jd": [2451545.0, 2451546.0, 2451547.0],
                "states": [
                    [1.0, 2.0, 3.0],
                    [4.0, 5.0, 6.0],
                    [7.0, 8.0, 9.0],
                    [0.01, 0.01, 0.01],
                    [0.02, 0.02, 0.02],
                    [0.03, 0.03, 0.03],
                ],
            }
        ],
        locifn="MOIRA ADVERSARIAL TYPE13",
    )


def test_adversarial_native_daf_catalog_preserves_descriptor_truth_on_synthetic_kernel(
    tmp_path: Path,
) -> None:
    if not spk_reader._HAS_NATIVE_DAF:
        pytest.skip("native DAF catalog reader is unavailable")

    path = tmp_path / "adversarial_type13.bsp"
    _synthetic_type13_kernel(path)

    catalog = spk_reader._moira_native.read_daf_catalog(str(path))
    assert catalog["locidw"] == "DAF/SPK"
    assert catalog["nd"] == 2
    assert catalog["ni"] == 6
    assert len(catalog["summaries"]) == 1

    descriptor = tuple(catalog["summaries"][0]["descriptor"])
    start_second, end_second, target, center, frame, data_type, start_i, end_i = descriptor

    # Governing boundaries:
    #   - summary descriptor ordering
    #   - native segment payload ownership
    #
    # Expected invariant:
    #   - summary metadata remains finite, ordered, and type-truthful
    assert math.isfinite(start_second)
    assert math.isfinite(end_second)
    assert start_second < end_second
    assert target == 2000433
    assert center == 10
    assert frame == 1
    assert data_type == 13
    assert start_i < end_i


def test_adversarial_small_body_kernel_accepts_exact_coverage_boundaries(
    tmp_path: Path,
) -> None:
    if not body_kernel._HAS_NATIVE_DAF:
        pytest.skip("native small-body DAF reader is unavailable")

    path = tmp_path / "coverage_edges.bsp"
    _synthetic_type13_kernel(path)

    kernel = SmallBodyKernel(path)
    try:
        coverage = kernel.coverage()[(10, 2000433)]
        start_jd, end_jd = coverage

        start_vec = kernel.position(2000433, start_jd)
        end_vec = kernel.position(2000433, end_jd)

        assert all(math.isfinite(value) for value in start_vec)
        assert all(math.isfinite(value) for value in end_vec)
    finally:
        kernel.close()


def test_adversarial_small_body_kernel_rejects_one_second_outside_coverage(
    tmp_path: Path,
) -> None:
    if not body_kernel._HAS_NATIVE_DAF:
        pytest.skip("native small-body DAF reader is unavailable")

    path = tmp_path / "outside_coverage.bsp"
    _synthetic_type13_kernel(path)

    kernel = SmallBodyKernel(path)
    try:
        start_jd, end_jd = kernel.coverage()[(10, 2000433)]

        with pytest.raises(KeyError, match="No segment covers NAIF"):
            kernel.position(2000433, start_jd - _ONE_SECOND_JD)
        with pytest.raises(KeyError, match="No segment covers NAIF"):
            kernel.position(2000433, end_jd + _ONE_SECOND_JD)
    finally:
        kernel.close()


def test_adversarial_small_body_kernel_rejects_unsupported_segment_type_before_partial_admission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "unsupported_type.bsp"
    path.write_bytes(b"placeholder")

    monkeypatch.setattr(body_kernel, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(
        body_kernel,
        "_moira_native",
        type(
            "_NativeStub",
            (),
            {
                "read_daf_catalog": staticmethod(
                    lambda _path: {
                        "little_endian": True,
                        "summaries": [
                            {
                                "name": b"UNSUPPORTED",
                                "descriptor": (0.0, 86400.0, 2000433, 10, 1, 9, 100, 200),
                            }
                        ],
                    }
                )
            },
        )(),
    )

    with pytest.raises(RuntimeError, match="supports native SPK segment types 2, 3, and 13"):
        SmallBodyKernel(path)


def test_adversarial_small_body_kernel_coverage_unions_split_segments_for_same_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "split_segments.bsp"
    path.write_bytes(b"placeholder")

    monkeypatch.setattr(body_kernel, "_HAS_NATIVE_DAF", True)
    monkeypatch.setattr(
        body_kernel,
        "_moira_native",
        type(
            "_NativeStub",
            (),
            {
                "read_daf_catalog": staticmethod(
                    lambda _path: {
                        "little_endian": True,
                        "summaries": [
                            {
                                "name": b"SEG_A",
                                "descriptor": (0.0, 86400.0, 2000433, 10, 1, 13, 100, 200),
                            },
                            {
                                "name": b"SEG_B",
                                "descriptor": (172800.0, 259200.0, 2000433, 10, 1, 13, 300, 400),
                            },
                        ],
                    }
                )
            },
        )(),
    )

    class _FakeSegment:
        def __init__(self, descriptor) -> None:
            self.target = int(descriptor[2])
            self.center = int(descriptor[3])
            self.start_jd = body_kernel._jd(float(descriptor[0]))
            self.end_jd = body_kernel._jd(float(descriptor[1]))

        def compute(self, jd):  # pragma: no cover - not used in this test
            return (jd, jd, jd)

    monkeypatch.setattr(
        body_kernel,
        "_native_segment_for",
        lambda _path, descriptor, _source, _little_endian: _FakeSegment(descriptor),
    )

    kernel = SmallBodyKernel(path)
    try:
        coverage = kernel.coverage()
        assert kernel.list_naif_ids() == [2000433]
        assert coverage[(10, 2000433)] == (
            body_kernel._jd(0.0),
            body_kernel._jd(259200.0),
        )
    finally:
        kernel.close()


def test_adversarial_native_catalog_support_predicate_rejects_mixed_supported_and_unsupported_types() -> None:
    catalog = {
        "little_endian": True,
        "summaries": [
            {"name": b"TYPE13", "descriptor": (0.0, 86400.0, 2000433, 10, 1, 13, 100, 200)},
            {"name": b"TYPE09", "descriptor": (0.0, 86400.0, 2000434, 10, 1, 9, 300, 400)},
        ],
    }

    assert body_kernel._small_body_kernel_native_supported(catalog) is False


def test_adversarial_native_chebyshev_exact_end_boundary_is_inclusive_and_next_tick_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "exact_end_boundary.bsp"
    path.write_bytes(b"placeholder")

    class _NativeStub:
        @staticmethod
        def read_spk_chebyshev_segment_payload(
            _path, _start_i, _end_i, _little_endian, _data_type, _reverse_coefficients=False
        ):
            return {
                "init": 0.0,
                "intlen": 86400.0,
                "coefficients": [
                    [
                        (1.0,),
                        (2.0,),
                        (3.0,),
                    ]
                ],
            }

    monkeypatch.setattr(body_kernel, "_moira_native", _NativeStub())
    monkeypatch.setattr(body_kernel, "_HAS_NATIVE_SEGMENTS", True)
    monkeypatch.setattr(_NativeChebyshevSegment, "_load_native_evaluator", lambda self: None)

    segment = _NativeChebyshevSegment(
        path,
        b"BOUNDARY",
        (0.0, 86400.0, 2000433, 10, 1, 2, 100, 200),
        True,
    )

    exact_end = segment.compute(body_kernel.T0 + 1.0)
    assert exact_end == (1.0, 2.0, 3.0)

    with pytest.raises(OutOfRangeError, match="segment only covers dates"):
        segment.compute(body_kernel.T0 + 1.0 + _ONE_SECOND_JD)
