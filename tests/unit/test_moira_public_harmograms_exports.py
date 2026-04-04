from __future__ import annotations

import moira


_ROOT_HARMOGRAM_NAMES = [
    "HarmonicDomain",
    "PointSetHarmonicVectorPolicy",
    "HarmogramIntensityFamily",
    "HarmogramChartDomain",
    "HarmogramTraceFamily",
    "HarmogramIntensityPolicy",
    "HarmogramPolicy",
    "point_set_harmonic_vector",
    "parts_from_zero_aries",
    "zero_aries_parts_harmonic_vector",
    "intensity_function_spectrum",
    "project_harmogram_strength",
    "harmogram_trace",
]


def test_selected_harmogram_names_are_exported_from_moira_root() -> None:
    for name in _ROOT_HARMOGRAM_NAMES:
        assert hasattr(moira, name), f"moira.{name} not found"
        assert name in moira.__all__, f"{name!r} missing from moira.__all__"


def test_research_helpers_remain_out_of_root_public_surface() -> None:
    for name in (
        "dominant_harmonic_contributors",
        "compare_intensity_spectra",
        "compare_trace_series",
    ):
        assert name not in moira.__all__, f"{name!r} should not be exported from moira root"
