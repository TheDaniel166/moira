from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from moira import moira_native
from moira._lunar_orientation_resources import _resolve_resource


def _pck_path() -> Path:
    try:
        return _resolve_resource("moon_pa_de440_200625.bpc")
    except Exception as exc:
        pytest.skip(f"pinned lunar binary PCK is unavailable: {exc}")


def _determinant(matrix) -> float:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def test_real_pck_catalog_preserves_nd2_ni5_descriptor_truth() -> None:
    catalog = moira_native.read_daf_catalog(str(_pck_path()))
    assert catalog["locidw"] == "DAF/PCK"
    assert catalog["nd"] == 2
    assert catalog["ni"] == 5
    assert [len(tuple(item["descriptor"])) for item in catalog["summaries"]] == [7, 7]
    assert [tuple(item["descriptor"])[2:5] for item in catalog["summaries"]] == [
        (31008, 1, 2),
        (31008, 1, 2),
    ]


def test_real_pck_rotation_is_proper_and_accepts_segment_boundary() -> None:
    handle = moira_native.open_pck_kernel(str(_pck_path()))
    try:
        catalog = handle.catalog()
        boundary_second = float(catalog["summaries"][1]["descriptor"][0])
        boundary_jd = boundary_second / 86400.0 + 2451545.0
        matrix = handle.rotation_matrix(boundary_jd)
        for left in range(3):
            for right in range(3):
                dot = sum(matrix[left][axis] * matrix[right][axis] for axis in range(3))
                assert dot == pytest.approx(1.0 if left == right else 0.0, abs=3e-15)
        assert _determinant(matrix) == pytest.approx(1.0, abs=3e-15)
    finally:
        handle.close()


def test_real_pck_fails_outside_descriptor_coverage() -> None:
    handle = moira_native.open_pck_kernel(str(_pck_path()))
    try:
        start, end = handle.coverage()
        with pytest.raises((IndexError, ValueError, OverflowError), match="outside descriptor coverage"):
            handle.rotation_matrix(start - 1.0 / 86400.0)
        with pytest.raises((IndexError, ValueError, OverflowError), match="outside descriptor coverage"):
            handle.rotation_matrix(end + 1.0 / 86400.0)
    finally:
        handle.close()


def test_real_pck_handle_supports_concurrent_cached_evaluation() -> None:
    handle = moira_native.open_pck_kernel(str(_pck_path()))
    epochs = [2451545.0 + index * 913.25 for index in range(16)]
    try:
        expected = [handle.rotation_matrix(epoch) for epoch in epochs]
        with ThreadPoolExecutor(max_workers=8) as executor:
            actual = list(executor.map(handle.rotation_matrix, epochs * 4))
        assert actual == expected * 4
        assert 1 <= handle.segment_cache_size() <= 2
    finally:
        handle.close()
