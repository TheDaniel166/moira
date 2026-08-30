"""Deterministic validation receipt for Moira's admitted Delta-T surface.

This script validates source routing, declared arithmetic, public vessels, and
failure behavior.  It performs no network access and makes no external-oracle
claim.  A failed invariant produces a non-zero process exit status.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import math
import sys


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import moira.delta_t_physical as dtp
from moira.constants import JULIAN_YEAR
from moira.julian import _delta_t_observation_boundary, delta_t as canonical_delta_t


def _future_expected(year: float) -> float:
    boundary = _delta_t_observation_boundary()
    horizon = year - boundary.year
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    return boundary.total + curvature * (horizon / 100.0) ** 2


def _run_checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append((name, passed, detail))

    boundary = _delta_t_observation_boundary()
    source_years = (-2000.0, -720.0, 0.0, 1000.0, 1840.0, 1962.5, 2000.0, boundary.year)
    source_differences = [
        abs(dtp.delta_t_hybrid(year) - canonical_delta_t(year)) for year in source_years
    ]
    record(
        f"source priority through {boundary.year:g}",
        max(source_differences) == 0.0,
        f"max internal routing difference={max(source_differences):.3e} s",
    )

    candidate_values = []
    for year in (-2000.0, 1840.0, 1962.5, boundary.year, 2100.0):
        candidate_values.extend(
            (
                dtp.core_delta_t(year),
                dtp.cryo_delta_t(year),
                dtp.fluid_lowfreq(year),
                dtp.historical_core_delta_t(year),
            )
        )
    record(
        "candidate attributions quarantined",
        all(value == 0.0 for value in candidate_values),
        f"max absolute candidate field={max(map(abs, candidate_values)):.3e} s",
    )

    future_years = (boundary.year + 1.0, 2030.0, 2050.0, 2100.0, 2150.0)
    future_differences = [
        abs(dtp.delta_t_hybrid(year) - _future_expected(year)) for year in future_years
    ]
    record(
        "future boundary-conditioned formula",
        max(future_differences) < 1e-11,
        f"max formula difference={max(future_differences):.3e} s; Delta-T(2100)={dtp.delta_t_hybrid(2100.0):.6f} s",
    )

    step = 1e-3
    reference = dtp.delta_t_hybrid(boundary.year)
    left_slope = (reference - dtp.delta_t_hybrid(boundary.year - step)) / step
    right_slope = (dtp.delta_t_hybrid(boundary.year + step) - reference) / step
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    parabola_slope = 2.0 * curvature * step / 10_000.0
    record(
        f"{boundary.year:g} C0 handoff",
        reference == boundary.total and abs(right_slope - parabola_slope) < 3e-6,
        (
            f"value={reference:.9f} s; left slope={left_slope:.9f}; "
            f"right slope={right_slope:.9f} s/year"
        ),
    )

    largest_component_seam = 0.0
    for seam in (1840.0, 1962.5, boundary.year):
        left = dtp.delta_t_breakdown(seam - 1e-7)
        right = dtp.delta_t_breakdown(seam + 1e-7)
        for name in ("total", "secular", "core", "cryo", "fluid", "bridge", "residual"):
            largest_component_seam = max(
                largest_component_seam,
                abs(getattr(right, name) - getattr(left, name)),
            )
    record(
        "component seam continuity",
        largest_component_seam < 1e-5,
        f"largest two-sided epsilon difference={largest_component_seam:.3e} s",
    )

    source_errors = {
        -2000.0: 2520.0,
        0.0: 90.0,
        2016.0: 0.06,
    }
    errors_match = all(
        dtp.delta_t_hybrid_uncertainty(year) == expected
        for year, expected in source_errors.items()
    )
    record(
        "source error and modern-floor scales",
        errors_match,
        ", ".join(
            f"{year:g}={dtp.delta_t_hybrid_uncertainty(year):g} s"
            for year in source_errors
        ),
    )

    uncertainty_years = (boundary.year, 2030.0, 2050.0, 2100.0, 2150.0)
    uncertainty_values = [dtp.delta_t_hybrid_uncertainty(year) for year in uncertainty_years]
    record(
        "future uncalibrated policy scale",
        uncertainty_values == sorted(uncertainty_values)
        and all(math.isfinite(value) and value > 0.0 for value in uncertainty_values),
        ", ".join(
            f"{year:g}={value:.6f} s"
            for year, value in zip(uncertainty_years, uncertainty_values)
        ),
    )

    horizon = 1e-6
    actual_horizon = (boundary.year + horizon) - boundary.year
    ou_value = dtp._future_stochastic_delta_t_sigma(boundary.year + horizon)
    brownian_limit = (
        JULIAN_YEAR
        / 1000.0
        * dtp._LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR
        * math.sqrt(actual_horizon**3 / 3.0)
    )
    relative_error = abs(ou_value - brownian_limit) / brownian_limit
    record(
        "stable short-horizon O-U evaluation",
        relative_error < 5e-4,
        f"relative Brownian-limit difference={relative_error:.3e}",
    )

    rejected = 0
    for bad_year in (math.nan, math.inf, -math.inf, -2000.0001):
        try:
            dtp.delta_t_hybrid(bad_year)
        except ValueError:
            rejected += 1
    record(
        "finite and admitted-domain rejection",
        rejected == 4,
        f"rejected {rejected}/4 non-finite or pre-source years",
    )

    extrapolation_years = (2150.0, 2150.0001, 2200.0)
    extrapolation_differences = [
        abs(dtp.delta_t_hybrid(year) - _future_expected(year))
        for year in extrapolation_years
    ]
    record(
        "post-2150 scenario continuation",
        max(extrapolation_differences) < 1e-11,
        "continuous mathematical extrapolation; external validation not claimed",
    )

    residual_failed_closed = False
    try:
        dtp._fitted_residual_spline()
    except RuntimeError:
        residual_failed_closed = True
    record(
        "residual validation fail-closed",
        residual_failed_closed,
        "quarantined residual fit raised RuntimeError",
    )

    breakdown_fields = tuple(field.name for field in fields(dtp.DeltaTBreakdown))
    distribution_fields = tuple(field.name for field in fields(dtp.DeltaTDistribution))
    record(
        "public vessels preserved",
        breakdown_fields
        == ("year", "total", "secular", "core", "cryo", "fluid", "bridge", "residual", "era")
        and distribution_fields == ("year", "mean", "sigma"),
        f"breakdown={breakdown_fields}; distribution={distribution_fields}",
    )

    return checks


def main() -> int:
    checks = _run_checks()
    print("Moira Delta-T source-bounded validation")
    print("Evidence class: internal routing, invariant, and packaged-source regression")
    print("External oracle: not exercised")
    print()
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")

    failures = [name for name, passed, _ in checks if not passed]
    print()
    print(f"Result: {len(checks) - len(failures)}/{len(checks)} checks passed")
    if failures:
        print("Failed: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
