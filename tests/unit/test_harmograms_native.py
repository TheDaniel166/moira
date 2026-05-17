"""
Tests for native C++ harmogram acceleration kernels.

Tests verify two things:
1. The raw native functions exist and return numerically correct results.
2. The full public API (point_set_harmonic_vector, intensity_function_spectrum)
   is numerically identical to the Python reference when MOIRA_ACCELERATE=1.

All tests skip gracefully when the native extension is unavailable.
"""
from __future__ import annotations

import math

import pytest

moira_native = pytest.importorskip(
    "moira.moira_native", reason="native extension not available"
)


# ---------------------------------------------------------------------------
# Helpers — pure-Python reference implementations for comparison
# ---------------------------------------------------------------------------

def _py_compute_components(
    longitudes_deg: list[float],
    harmonics: list[int],
    raw_sum: bool,
) -> list[tuple[int, float, float]]:
    """Mirror of compute.py _compute_components, but returns plain tuples."""
    n = len(longitudes_deg)
    results: list[tuple[int, float, float]] = []
    for h in harmonics:
        total = complex(0.0, 0.0)
        for lon in longitudes_deg:
            angle = math.radians(h * lon)
            total += complex(math.cos(angle), math.sin(angle))
        if not raw_sum:
            total /= n
        amp = abs(total)
        phase = (
            0.0
            if amp < 1.0e-12
            else math.degrees(math.atan2(total.imag, total.real)) % 360.0
        )
        results.append((h, amp, phase))
    return results


def _py_intensity_components(
    harmonic_number: int,
    harmonic_start: int,
    harmonic_stop: int,
    sample_count: int,
    orb_mode: str,
    orb_width_deg: float,
    include_conjunction: bool,
    gaussian_width_deg: float,
    gaussian_fwhm_mode: bool,
) -> tuple[float, list[tuple[int, float, float]]]:
    """Pure-Python reference for _compute_intensity_components."""
    step = 360.0 / harmonic_number
    if include_conjunction:
        centers = [i * step for i in range(harmonic_number)]
    else:
        centers = [i * step for i in range(1, harmonic_number)]

    half_width = orb_width_deg / harmonic_number

    if orb_mode == "gaussian":
        if gaussian_fwhm_mode:
            sigma = (gaussian_width_deg / harmonic_number) / (
                2.0 * math.sqrt(2.0 * math.log(2.0))
            )
        else:
            sigma = gaussian_width_deg / harmonic_number

    def intensity_at(angle_deg: float) -> float:
        if not centers:
            return 0.0
        best = 0.0
        for center in centers:
            delta_raw = (angle_deg - center) % 360.0
            if delta_raw >= 180.0:
                delta_raw -= 360.0
            delta = abs(delta_raw)
            if delta > half_width:
                continue
            if orb_mode == "cosine_bell":
                v = 0.5 * (1.0 + math.cos(math.pi * delta / half_width))
            elif orb_mode == "top_hat":
                v = 1.0
            elif orb_mode == "triangular":
                v = 1.0 - delta / half_width
            elif orb_mode == "gaussian":
                v = math.exp(-0.5 * (delta / sigma) ** 2)
            else:
                raise ValueError(f"unknown orb_mode {orb_mode}")
            if v > best:
                best = v
        return best

    samples = [intensity_at(360.0 * i / sample_count) for i in range(sample_count)]
    h0_amp = sum(samples) / sample_count

    harmonics = list(range(harmonic_start, harmonic_stop + 1))
    components: list[tuple[int, float, float]] = []
    for h in harmonics:
        total = complex(0.0, 0.0)
        for idx, s in enumerate(samples):
            angle = math.radians((360.0 * idx) / sample_count)
            total += s * complex(math.cos(-h * angle), math.sin(-h * angle))
        total /= sample_count
        amp = abs(total)
        phase = (
            0.0
            if amp < 1.0e-12
            else math.degrees(math.atan2(total.imag, total.real)) % 360.0
        )
        components.append((h, amp, phase))

    return h0_amp, components


# ---------------------------------------------------------------------------
# harmogram_compute_components — structure and correctness
# ---------------------------------------------------------------------------

def test_native_compute_components_function_exists() -> None:
    assert hasattr(moira_native, "harmogram_compute_components"), (
        "moira_native must export harmogram_compute_components"
    )


def test_native_compute_components_returns_one_entry_per_harmonic() -> None:
    result = moira_native.harmogram_compute_components([45.0], [1, 2, 3, 4], False)
    assert len(result) == 4


def test_native_compute_components_entry_harmonics_match_input_order() -> None:
    result = moira_native.harmogram_compute_components([45.0], [1, 2, 3, 4], False)
    assert [r[0] for r in result] == [1, 2, 3, 4]


def test_native_compute_components_single_point_amplitude_is_one() -> None:
    result = moira_native.harmogram_compute_components([45.0], [1, 2, 3, 4], False)
    amplitudes = [r[1] for r in result]
    assert amplitudes == pytest.approx([1.0, 1.0, 1.0, 1.0], abs=1.0e-12)


def test_native_compute_components_single_point_phase_tracks_harmonic() -> None:
    result = moira_native.harmogram_compute_components([45.0], [1, 2, 3, 4], False)
    phases = [r[2] for r in result]
    assert phases == pytest.approx([45.0, 90.0, 135.0, 180.0], abs=1.0e-10)


def test_native_compute_components_third_harmonic_max_at_trine() -> None:
    # Three points 120° apart: h=1 sums to zero (destructive), h=3 maps all
    # points to 0° so mean-resultant amplitude is 1.0 (constructive).
    result = moira_native.harmogram_compute_components(
        [0.0, 120.0, 240.0], [1, 2, 3], False
    )
    h1_amp = result[0][1]
    h3_amp = result[2][1]
    assert h1_amp == pytest.approx(0.0, abs=1.0e-12)
    assert h3_amp == pytest.approx(1.0, abs=1.0e-12)


def test_native_compute_components_matches_python_reference_mean_resultant() -> None:
    longitudes = [10.0, 130.0, 250.0]
    harmonics = [1, 2, 3, 4, 5]
    expected = _py_compute_components(longitudes, harmonics, False)
    result = moira_native.harmogram_compute_components(longitudes, harmonics, False)
    assert len(result) == len(expected)
    for (eh, ea, ep), (rh, ra, rp) in zip(expected, result):
        assert eh == rh
        assert ra == pytest.approx(ea, abs=1.0e-12)
        assert rp == pytest.approx(ep, abs=1.0e-10)


def test_native_compute_components_matches_python_reference_raw_sum() -> None:
    longitudes = [30.0, 90.0, 150.0, 210.0, 270.0, 330.0]
    harmonics = [1, 2, 3, 6]
    expected = _py_compute_components(longitudes, harmonics, True)
    result = moira_native.harmogram_compute_components(longitudes, harmonics, True)
    for (eh, ea, ep), (rh, ra, rp) in zip(expected, result):
        assert ra == pytest.approx(ea, abs=1.0e-12)


def test_native_compute_components_many_positions_matches_python() -> None:
    import random
    rng = random.Random(42)
    longitudes = [rng.uniform(0.0, 360.0) for _ in range(20)]
    harmonics = list(range(1, 13))
    expected = _py_compute_components(longitudes, harmonics, False)
    result = moira_native.harmogram_compute_components(longitudes, harmonics, False)
    for (eh, ea, ep), (rh, ra, rp) in zip(expected, result):
        assert ra == pytest.approx(ea, abs=1.0e-11)
        if ea > 1.0e-9:
            assert rp == pytest.approx(ep, abs=1.0e-9)


# ---------------------------------------------------------------------------
# harmogram_intensity_components — structure and correctness
# ---------------------------------------------------------------------------

def test_native_intensity_components_function_exists() -> None:
    assert hasattr(moira_native, "harmogram_intensity_components"), (
        "moira_native must export harmogram_intensity_components"
    )


def test_native_intensity_components_returns_pair() -> None:
    h0_amp, components = moira_native.harmogram_intensity_components(
        1, 1, 4, 128, "cosine_bell", 24.0, True, "equated_to_harmonic_one", 0.0, False
    )
    assert isinstance(h0_amp, float)
    assert isinstance(components, list)
    assert len(components) == 4


def test_native_intensity_components_h0_amplitude_nonnegative() -> None:
    h0_amp, _ = moira_native.harmogram_intensity_components(
        1, 1, 12, 256, "cosine_bell", 24.0, True, "equated_to_harmonic_one", 0.0, False
    )
    assert h0_amp >= 0.0


def test_native_intensity_components_component_harmonics_match_domain() -> None:
    _, components = moira_native.harmogram_intensity_components(
        2, 1, 6, 128, "top_hat", 24.0, True, "equated_to_harmonic_one", 0.0, False
    )
    harmonics = [c[0] for c in components]
    assert harmonics == list(range(1, 7))


def test_native_intensity_components_cosine_bell_matches_python() -> None:
    params = dict(
        harmonic_number=1,
        harmonic_start=1,
        harmonic_stop=8,
        sample_count=512,
        orb_mode="cosine_bell",
        orb_width_deg=24.0,
        include_conjunction=True,
        gaussian_width_deg=0.0,
        gaussian_fwhm_mode=False,
    )
    exp_h0, exp_comps = _py_intensity_components(**params)
    nat_h0, nat_comps = moira_native.harmogram_intensity_components(
        params["harmonic_number"],
        params["harmonic_start"],
        params["harmonic_stop"],
        params["sample_count"],
        params["orb_mode"],
        params["orb_width_deg"],
        params["include_conjunction"],
        "equated_to_harmonic_one",
        params["gaussian_width_deg"],
        params["gaussian_fwhm_mode"],
    )
    assert nat_h0 == pytest.approx(exp_h0, abs=1.0e-10)
    for (eh, ea, ep), (rh, ra, rp) in zip(exp_comps, nat_comps):
        assert eh == rh
        assert ra == pytest.approx(ea, abs=1.0e-10)
        if ea > 1.0e-9:
            assert rp == pytest.approx(ep, abs=1.0e-8)


def test_native_intensity_components_top_hat_matches_python() -> None:
    exp_h0, exp_comps = _py_intensity_components(
        harmonic_number=3,
        harmonic_start=1,
        harmonic_stop=6,
        sample_count=256,
        orb_mode="top_hat",
        orb_width_deg=18.0,
        include_conjunction=True,
        gaussian_width_deg=0.0,
        gaussian_fwhm_mode=False,
    )
    nat_h0, nat_comps = moira_native.harmogram_intensity_components(
        3, 1, 6, 256, "top_hat", 18.0, True, "equated_to_harmonic_one", 0.0, False
    )
    assert nat_h0 == pytest.approx(exp_h0, abs=1.0e-10)
    for (eh, ea, ep), (rh, ra, rp) in zip(exp_comps, nat_comps):
        assert ra == pytest.approx(ea, abs=1.0e-10)


def test_native_intensity_components_triangular_matches_python() -> None:
    exp_h0, exp_comps = _py_intensity_components(
        harmonic_number=4,
        harmonic_start=1,
        harmonic_stop=8,
        sample_count=256,
        orb_mode="triangular",
        orb_width_deg=12.0,
        include_conjunction=False,
        gaussian_width_deg=0.0,
        gaussian_fwhm_mode=False,
    )
    nat_h0, nat_comps = moira_native.harmogram_intensity_components(
        4, 1, 8, 256, "triangular", 12.0, False, "equated_to_harmonic_one", 0.0, False
    )
    assert nat_h0 == pytest.approx(exp_h0, abs=1.0e-10)
    for (eh, ea, ep), (rh, ra, rp) in zip(exp_comps, nat_comps):
        assert ra == pytest.approx(ea, abs=1.0e-10)


def test_native_intensity_components_gaussian_matches_python() -> None:
    exp_h0, exp_comps = _py_intensity_components(
        harmonic_number=2,
        harmonic_start=1,
        harmonic_stop=6,
        sample_count=512,
        orb_mode="gaussian",
        orb_width_deg=24.0,
        include_conjunction=True,
        gaussian_width_deg=10.0,
        gaussian_fwhm_mode=False,
    )
    nat_h0, nat_comps = moira_native.harmogram_intensity_components(
        2, 1, 6, 512, "gaussian", 24.0, True, "equated_to_harmonic_one", 10.0, False
    )
    assert nat_h0 == pytest.approx(exp_h0, abs=1.0e-10)
    for (eh, ea, ep), (rh, ra, rp) in zip(exp_comps, nat_comps):
        assert ra == pytest.approx(ea, abs=1.0e-10)


# ---------------------------------------------------------------------------
# Public API parity — when MOIRA_ACCELERATE=1 results must be identical
# ---------------------------------------------------------------------------

def test_public_api_parity_point_set_harmonic_vector(monkeypatch) -> None:
    """point_set_harmonic_vector gives identical results via Python and native paths."""
    from moira.harmograms import (
        HarmonicDomain,
        PointSetHarmonicVectorPolicy,
        point_set_harmonic_vector,
    )
    from moira import dispatch

    positions = [
        {"name": "Sun", "degree": 15.0},
        {"name": "Moon", "degree": 135.0},
        {"name": "Mercury", "degree": 275.0},
    ]
    policy = PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 8))

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.PYTHON)
    py_result = point_set_harmonic_vector(positions, policy=policy)

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.NATIVE)
    nat_result = point_set_harmonic_vector(positions, policy=policy)

    assert py_result.point_count == nat_result.point_count
    for py_c, nat_c in zip(py_result.components, nat_result.components):
        assert py_c.harmonic == nat_c.harmonic
        assert nat_c.amplitude == pytest.approx(py_c.amplitude, abs=1.0e-12)
        if py_c.amplitude > 1.0e-9:
            assert nat_c.phase_deg == pytest.approx(py_c.phase_deg, abs=1.0e-10)


def test_public_api_parity_intensity_function_spectrum(monkeypatch) -> None:
    """intensity_function_spectrum gives identical results via Python and native paths."""
    from moira.harmograms import intensity_function_spectrum, HarmogramIntensityPolicy
    from moira import dispatch

    policy = HarmogramIntensityPolicy(sample_count=256)

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.PYTHON)
    py_result = intensity_function_spectrum(3, policy=policy)

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.NATIVE)
    nat_result = intensity_function_spectrum(3, policy=policy)

    assert nat_result.harmonic_zero_amplitude == pytest.approx(
        py_result.harmonic_zero_amplitude, abs=1.0e-10
    )
    for py_c, nat_c in zip(py_result.components, nat_result.components):
        assert nat_c.amplitude == pytest.approx(py_c.amplitude, abs=1.0e-10)
