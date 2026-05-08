from __future__ import annotations

import re
from pathlib import Path

import pytest

from moira import moira_native
from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import SpkReader


_ROOT = Path(__file__).resolve().parents[2]
_NUMPY_PATTERNS = (
    r"\bimport numpy\b",
    r"\bfrom numpy\b",
    r"\b_np\.",
    r"\b_HAS_NUMPY\b",
)


def _numpy_markers(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    hits: list[str] = []
    for pattern in _NUMPY_PATTERNS:
        if re.search(pattern, text):
            hits.append(pattern)
    return hits


@pytest.mark.requires_ephemeris
def test_planetary_native_ownership_snapshot(snapshot) -> None:
    kernel_path = find_planetary_kernel()
    with SpkReader(kernel_path) as reader:
        segment = reader._segment_for(0, 10, 2451545.0)
        payload = moira_native.read_spk_chebyshev_segment_payload(
            str(kernel_path),
            int(segment.start_i),
            int(segment.end_i),
            True,
            int(segment.data_type),
        )

    value = {
        "planetary_numpy_markers": {
            "moira/planets.py": _numpy_markers(_ROOT / "moira" / "planets.py"),
            "moira/corrections.py": _numpy_markers(_ROOT / "moira" / "corrections.py"),
            "moira/nutation_2000a.py": _numpy_markers(_ROOT / "moira" / "nutation_2000a.py"),
        },
        "native_helpers": {
            "rotation_matrix_multiply": hasattr(moira_native, "rotation_matrix_multiply"),
            "rotation_matrix_apply": hasattr(moira_native, "rotation_matrix_apply"),
            "apply_aberration_velocity": hasattr(moira_native, "apply_aberration_velocity"),
            "apply_frame_bias": hasattr(moira_native, "apply_frame_bias"),
            "open_spk_kernel": hasattr(moira_native, "open_spk_kernel"),
        },
        "spk_payload_surface": {
            "coefficients_type": type(payload["coefficients"]).__name__,
            "record_type": type(payload["coefficients"][0]).__name__,
            "component_type": type(payload["coefficients"][0][0]).__name__,
            "record_count": int(payload["record_count"]),
            "component_count": int(payload["component_count"]),
            "coefficient_count": int(payload["coefficient_count"]),
        },
    }

    snapshot("planetary_native_ownership_state", value)
