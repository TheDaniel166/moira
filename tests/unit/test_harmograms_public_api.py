"""
tests/unit/test_harmograms_public_api.py

Validates that the curated harmograms public API is exposed from the owning
module while helper machinery remains internal.
"""

import moira.harmograms as _harmograms_module


_CURATED_PUBLIC_NAMES = [
    "HarmonicVectorNormalizationMode",
    "ZeroAriesPairConstructionMode",
    "SelfPairMode",
    "HarmonicDomain",
    "PointSetHarmonicVectorPolicy",
    "ZeroAriesPartsPolicy",
    "HarmonicVectorComponent",
    "PointSetHarmonicVector",
    "ZeroAriesPart",
    "ZeroAriesPartsSet",
    "ZeroAriesPartsHarmonicVector",
    "HarmogramIntensityFamily",
    "HarmogramOrbMode",
    "GaussianWidthParameterMode",
    "HarmogramOrbScalingMode",
    "HarmogramSymmetryMode",
    "IntensityNormalizationMode",
    "IntensitySpectrumRealizationMode",
    "HarmogramProjectionRealizationMode",
    "HarmogramSamplingMode",
    "HarmogramOutputMode",
    "HarmogramChartDomain",
    "HarmogramTraceFamily",
    "HarmogramIntensityPolicy",
    "HarmogramSamplingPolicy",
    "HarmogramPolicy",
    "IntensitySpectrumComponent",
    "IntensityFunctionSpectrum",
    "HarmogramProjectionTerm",
    "HarmogramProjection",
    "HarmogramDominantTerm",
    "IntensitySpectrumComparisonTerm",
    "IntensitySpectrumComparison",
    "HarmogramTraceSeriesComparisonSample",
    "HarmogramTraceSeriesComparison",
    "HarmogramTraceSample",
    "HarmogramTraceSeries",
    "HarmogramTrace",
    "point_set_harmonic_vector",
    "parts_from_zero_aries",
    "zero_aries_parts_harmonic_vector",
    "intensity_function_spectrum",
    "project_harmogram_strength",
    "harmogram_trace",
    "dominant_harmonic_contributors",
    "compare_intensity_spectra",
    "compare_trace_series",
    "harmonic_vector",
]

_INTERNAL_NAMES = [
    "_normalize_positions",
    "_validate_component_domain",
    "_compute_components",
    "_normalize_angle_deg",
]


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_harmograms(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_harmograms_module, name), f"moira.harmograms.{name} not found"

    def test_all_curated_names_in_module_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in _harmograms_module.__all__, f"{name!r} missing from moira.harmograms.__all__"

    def test_no_internal_names_in_module_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _harmograms_module.__all__, f"{name!r} leaked into moira.harmograms.__all__"

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_harmograms_module, name), (
                f"moira.harmograms.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_48(self):
        assert len(_CURATED_PUBLIC_NAMES) == 48
