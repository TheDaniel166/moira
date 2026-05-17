"""
Tests for native C++ harmogram_trace_batch kernel — hotspot 3.

The batch function fuses ZA-parts computation, Fourier decomposition, and
intensity projection for N time samples in one C++ call, optionally in
parallel via OpenMP.

Return shape: (total_strengths[N], sample_components[N][H])
  - total_strengths[i]       : float  — same as HarmogramTraceSample.total_strength
  - sample_components[i][k]  : (harmonic: int, amplitude: float, phase_deg: float)

All tests skip gracefully when the native extension is unavailable.
"""
from __future__ import annotations

import math

import pytest

moira_native = pytest.importorskip(
    "moira.moira_native", reason="native extension not available"
)


# ---------------------------------------------------------------------------
# Pure-Python reference — mirrors the trace inner loop exactly
# ---------------------------------------------------------------------------

def _py_za_parts(
    source_lons: list[float],
    target_lons: list[float],
    same_source_target: bool,
    ordered: bool,
    include_self: bool,
) -> list[float]:
    parts: list[float] = []
    if same_source_target and not ordered:
        n = len(source_lons)
        for i in range(n):
            j_start = i if include_self else i + 1
            for j in range(j_start, n):
                raw = (source_lons[i] - source_lons[j]) % 360.0
                parts.append(raw)
    else:
        for idx_s, s in enumerate(source_lons):
            for idx_t, t in enumerate(target_lons):
                if same_source_target and not include_self and idx_s == idx_t:
                    continue
                raw = (s - t) % 360.0
                parts.append(raw)
    return parts


def _py_strength_from_parts(
    parts: list[float],
    harmonics: list[int],
    raw_sum: bool,
    h0_contribution: float,
    intensity_components: list[tuple[int, float, float]],
) -> tuple[float, list[tuple[int, float, float]]]:
    n = len(parts)
    inv_n = 1.0 if raw_sum else (1.0 / n if n else 1.0)
    int_z = {
        h: (a * math.cos(math.radians(p)), a * math.sin(math.radians(p)))
        for h, a, p in intensity_components
    }

    total = h0_contribution
    src_components: list[tuple[int, float, float]] = []
    for h in harmonics:
        re_sum = im_sum = 0.0
        for lon in parts:
            angle = math.radians(h * lon)
            re_sum += math.cos(angle)
            im_sum += math.sin(angle)
        re_sum *= inv_n
        im_sum *= inv_n
        amp = math.sqrt(re_sum * re_sum + im_sum * im_sum)
        phase = 0.0
        if amp >= 1.0e-12:
            phase = math.degrees(math.atan2(im_sum, re_sum)) % 360.0
            if abs(phase - 360.0) < 1.0e-12:
                phase = 0.0
        src_components.append((h, amp, phase))

        iz_re, iz_im = int_z[h]
        term = 2.0 * (re_sum * iz_re + im_sum * iz_im)
        total += term

    return total, src_components


def _py_trace_batch(
    samples_source_lons: list[list[float]],
    samples_target_lons: list[list[float]],
    same_source_target: bool,
    ordered: bool,
    include_self: bool,
    raw_sum: bool,
    h0_contribution: float,
    harmonics: list[int],
    intensity_components: list[tuple[int, float, float]],
) -> tuple[list[float], list[list[tuple[int, float, float]]]]:
    strengths: list[float] = []
    all_comps: list[list[tuple[int, float, float]]] = []
    for i, src_lons in enumerate(samples_source_lons):
        tgt_lons = src_lons if same_source_target else samples_target_lons[i]
        parts = _py_za_parts(src_lons, tgt_lons, same_source_target, ordered, include_self)
        strength, comps = _py_strength_from_parts(
            parts, harmonics, raw_sum, h0_contribution, intensity_components
        )
        strengths.append(strength)
        all_comps.append(comps)
    return strengths, all_comps


# Shared small intensity spectrum (precomputed via Python reference)
HARMONICS = [1, 2, 3, 4]
SAMPLE_COUNT = 256

def _make_intensity_components() -> tuple[float, list[tuple[int, float, float]], float]:
    """Returns (h0_contribution, intensity_components, h0_source) for a simple policy."""
    from moira.harmograms import intensity_function_spectrum, HarmogramIntensityPolicy
    from moira.harmograms.models import HarmonicDomain
    policy = HarmogramIntensityPolicy(
        harmonic_domain=HarmonicDomain(1, 4),
        sample_count=SAMPLE_COUNT,
    )
    spec = intensity_function_spectrum(1, policy=policy)
    h0_source = 1.0  # MEAN_RESULTANT
    h0_contribution = h0_source * spec.harmonic_zero_amplitude
    comps = [(c.harmonic, c.amplitude, c.phase_deg) for c in spec.components]
    return h0_contribution, comps, h0_source


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_native_trace_batch_function_exists() -> None:
    assert hasattr(moira_native, "harmogram_trace_batch"), (
        "moira_native must export harmogram_trace_batch"
    )


def test_native_trace_batch_returns_pair() -> None:
    h0_contrib, int_comps, _ = _make_intensity_components()
    result = moira_native.harmogram_trace_batch(
        [[0.0, 120.0, 240.0]],  # 1 sample, 3 positions
        [],                      # empty → same_source_target
        True,                    # same_source_target
        True,                    # ordered (full cross-product)
        True,                    # include_self
        False,                   # mean-resultant
        h0_contrib,
        HARMONICS,
        int_comps,
    )
    strengths, all_comps = result
    assert len(strengths) == 1
    assert len(all_comps) == 1
    assert len(all_comps[0]) == len(HARMONICS)


def test_native_trace_batch_component_harmonics_match() -> None:
    h0_contrib, int_comps, _ = _make_intensity_components()
    _, all_comps = moira_native.harmogram_trace_batch(
        [[10.0, 130.0, 250.0]],
        [], True, True, True, False,
        h0_contrib, HARMONICS, int_comps,
    )
    returned_harmonics = [c[0] for c in all_comps[0]]
    assert returned_harmonics == HARMONICS


# ---------------------------------------------------------------------------
# Correctness — single sample
# ---------------------------------------------------------------------------

def test_native_trace_batch_single_sample_matches_python() -> None:
    h0_contrib, int_comps, _ = _make_intensity_components()
    src = [15.0, 135.0, 255.0]
    exp_strengths, exp_comps = _py_trace_batch(
        [src], [], True, True, True, False, h0_contrib, HARMONICS, int_comps
    )
    nat_strengths, nat_comps = moira_native.harmogram_trace_batch(
        [src], [], True, True, True, False, h0_contrib, HARMONICS, int_comps
    )
    assert nat_strengths[0] == pytest.approx(exp_strengths[0], abs=1.0e-11)
    for (eh, ea, ep), (rh, ra, rp) in zip(exp_comps[0], nat_comps[0]):
        assert eh == rh
        assert ra == pytest.approx(ea, abs=1.0e-12)
        if ea > 1.0e-9:
            assert rp == pytest.approx(ep, abs=1.0e-10)


# ---------------------------------------------------------------------------
# Correctness — multiple samples
# ---------------------------------------------------------------------------

def test_native_trace_batch_multiple_samples_matches_python() -> None:
    h0_contrib, int_comps, _ = _make_intensity_components()
    import random
    rng = random.Random(7)
    samples = [[rng.uniform(0, 360) for _ in range(5)] for _ in range(12)]

    exp_s, exp_c = _py_trace_batch(
        samples, [], True, True, True, False, h0_contrib, HARMONICS, int_comps
    )
    nat_s, nat_c = moira_native.harmogram_trace_batch(
        samples, [], True, True, True, False, h0_contrib, HARMONICS, int_comps
    )
    for i in range(len(samples)):
        assert nat_s[i] == pytest.approx(exp_s[i], abs=1.0e-11)
        for (eh, ea, ep), (rh, ra, rp) in zip(exp_c[i], nat_c[i]):
            assert ra == pytest.approx(ea, abs=1.0e-12)
            if ea > 1.0e-9:
                assert rp == pytest.approx(ep, abs=1.0e-10)


def test_native_trace_batch_unordered_mode_matches_python() -> None:
    h0_contrib, int_comps, _ = _make_intensity_components()
    import random
    rng = random.Random(13)
    samples = [[rng.uniform(0, 360) for _ in range(6)] for _ in range(8)]

    exp_s, exp_c = _py_trace_batch(
        samples, [], True, False, True, False, h0_contrib, HARMONICS, int_comps
    )
    nat_s, nat_c = moira_native.harmogram_trace_batch(
        samples, [], True, False, True, False, h0_contrib, HARMONICS, int_comps
    )
    for i in range(len(samples)):
        assert nat_s[i] == pytest.approx(exp_s[i], abs=1.0e-11)


def test_native_trace_batch_exclude_self_pairs_matches_python() -> None:
    h0_contrib, int_comps, _ = _make_intensity_components()
    import random
    rng = random.Random(21)
    samples = [[rng.uniform(0, 360) for _ in range(5)] for _ in range(6)]

    exp_s, _ = _py_trace_batch(
        samples, [], True, True, False, False, h0_contrib, HARMONICS, int_comps
    )
    nat_s, _ = moira_native.harmogram_trace_batch(
        samples, [], True, True, False, False, h0_contrib, HARMONICS, int_comps
    )
    for i in range(len(samples)):
        assert nat_s[i] == pytest.approx(exp_s[i], abs=1.0e-11)


def test_native_trace_batch_relational_different_source_target_matches_python() -> None:
    """TRANSIT_TO_NATAL style: separate source and target lists per sample."""
    h0_contrib, int_comps, _ = _make_intensity_components()
    import random
    rng = random.Random(99)
    natal = [rng.uniform(0, 360) for _ in range(5)]
    transit_samples = [[rng.uniform(0, 360) for _ in range(4)] for _ in range(10)]
    target_samples = [natal] * 10

    exp_s, _ = _py_trace_batch(
        transit_samples, target_samples, False, True, True, False,
        h0_contrib, HARMONICS, int_comps
    )
    nat_s, _ = moira_native.harmogram_trace_batch(
        transit_samples, target_samples, False, True, True, False,
        h0_contrib, HARMONICS, int_comps
    )
    for i in range(10):
        assert nat_s[i] == pytest.approx(exp_s[i], abs=1.0e-11)


def test_native_trace_batch_raw_sum_mode_matches_python() -> None:
    h0_contrib, int_comps, h0_source = _make_intensity_components()
    # RAW_SUM: h0_source = parts_count (3×3=9), h0_contribution = parts_count * h0_int
    from moira.harmograms import intensity_function_spectrum, HarmogramIntensityPolicy
    from moira.harmograms.models import HarmonicDomain
    spec = intensity_function_spectrum(
        1, policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 4), sample_count=SAMPLE_COUNT
        )
    )
    parts_count = 9.0  # 3×3 ordered with self-pairs
    h0_contribution_raw = parts_count * spec.harmonic_zero_amplitude

    import random
    rng = random.Random(55)
    samples = [[rng.uniform(0, 360) for _ in range(3)] for _ in range(5)]

    exp_s, _ = _py_trace_batch(
        samples, [], True, True, True, True, h0_contribution_raw,
        HARMONICS, [(c.harmonic, c.amplitude, c.phase_deg) for c in spec.components]
    )
    nat_s, _ = moira_native.harmogram_trace_batch(
        samples, [], True, True, True, True, h0_contribution_raw,
        HARMONICS, [(c.harmonic, c.amplitude, c.phase_deg) for c in spec.components]
    )
    for i in range(len(samples)):
        assert nat_s[i] == pytest.approx(exp_s[i], abs=1.0e-11)


# ---------------------------------------------------------------------------
# Public API parity — harmogram_trace with MOIRA_ACCELERATE=1
# ---------------------------------------------------------------------------

def test_public_trace_parity_dynamic(monkeypatch) -> None:
    """Full harmogram_trace output is numerically identical via Python and native."""
    from moira.harmograms import (
        harmogram_trace,
        HarmogramPolicy,
        HarmogramTraceFamily,
        HarmogramIntensityPolicy,
        HarmonicDomain,
        PointSetHarmonicVectorPolicy,
    )
    from moira import dispatch

    policy = HarmogramPolicy(
        trace_family=HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS,
        intensity_policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 4),
            sample_count=SAMPLE_COUNT,
        ),
        point_set_policy=PointSetHarmonicVectorPolicy(
            harmonic_domain=HarmonicDomain(1, 4),
        ),
    )
    import random
    rng = random.Random(42)
    samples = [
        {
            "time": float(t),
            "positions": [
                {"name": "Sun", "degree": rng.uniform(0, 360)},
                {"name": "Moon", "degree": rng.uniform(0, 360)},
                {"name": "Mars", "degree": rng.uniform(0, 360)},
            ],
        }
        for t in range(10)
    ]

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.PYTHON)
    py_trace = harmogram_trace(samples, harmonic_numbers=[1], policy=policy)

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.NATIVE)
    nat_trace = harmogram_trace(samples, harmonic_numbers=[1], policy=policy)

    py_strengths = [s.total_strength for s in py_trace.series[0].samples]
    nat_strengths = [s.total_strength for s in nat_trace.series[0].samples]
    assert nat_strengths == pytest.approx(py_strengths, abs=1.0e-11)


def test_public_trace_parity_transit_to_natal(monkeypatch) -> None:
    """Transit-to-natal trace is numerically identical via Python and native."""
    from moira.harmograms import (
        harmogram_trace,
        HarmogramPolicy,
        HarmogramTraceFamily,
        HarmogramChartDomain,
        HarmogramIntensityPolicy,
        HarmonicDomain,
        PointSetHarmonicVectorPolicy,
    )
    from moira import dispatch

    policy = HarmogramPolicy(
        trace_family=HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS,
        chart_domain=HarmogramChartDomain.TRANSIT_TO_NATAL_TRACE,
        intensity_policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 4),
            sample_count=SAMPLE_COUNT,
        ),
        point_set_policy=PointSetHarmonicVectorPolicy(
            harmonic_domain=HarmonicDomain(1, 4),
        ),
    )
    import random
    rng = random.Random(77)
    natal = [
        {"name": "Sun", "degree": 10.0},
        {"name": "Moon", "degree": 130.0},
        {"name": "Mercury", "degree": 250.0},
    ]
    samples = [
        {
            "time": float(t),
            "transit_positions": [
                {"name": "Mars", "degree": rng.uniform(0, 360)},
                {"name": "Jupiter", "degree": rng.uniform(0, 360)},
            ],
            "natal_positions": natal,
        }
        for t in range(8)
    ]

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.PYTHON)
    py_trace = harmogram_trace(samples, harmonic_numbers=[1], policy=policy)

    monkeypatch.setattr(dispatch.settings, "_default_backend", dispatch.MoiraBackend.NATIVE)
    nat_trace = harmogram_trace(samples, harmonic_numbers=[1], policy=policy)

    py_s = [s.total_strength for s in py_trace.series[0].samples]
    nat_s = [s.total_strength for s in nat_trace.series[0].samples]
    assert nat_s == pytest.approx(py_s, abs=1.0e-11)
