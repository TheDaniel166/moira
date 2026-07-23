"""
Moira's source-bounded Delta-T attribution and forecast surface.

The public vessel and function names in this module are stable, but the model
is deliberately narrow about what it claims to identify:

* From year -2000 through the reference epoch, the total is the canonical
  source-priority Delta-T value from :mod:`moira.julian`.
* Candidate GRACE, total-LOD, AAM, and OAM artifacts are retained only for
  provenance and research.  They are not admitted as separately identified
  cryosphere, core, or fluid contributions.
* After the reference epoch, the mean is a boundary-conditioned scenario:
  the admitted value and provisional aggregate-epoch slope at the hand-off plus
  the declared tidal/GIA curvature.  It is not described as a geophysical
  component inversion.
  Values after 2150 are mathematical continuation of that scenario, not a
  validated forecast.
* HPIERS-owned historical uncertainty comes from that source table's error
  column. The source bridge and aggregate era use the modern policy floor. The
  future ``sigma`` field is an uncalibrated policy scale: it has no stated
  coverage probability and omits unquantified handoff-value and handoff-slope
  uncertainty.

This module owns decimal-year model policy.  JD-aware UTC/UT1/TT conversion
and daily EOP authority remain in :mod:`moira.julian`.
"""

import math
import statistics
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from .constants import JULIAN_YEAR
from .julian import (
    _HPIERS_EXPECTED_DATA_ROWS,
    _HPIERS_LATER_ROW_CONFLICT_EPOCHS,
    _HPIERS_MODERN_HALF_YEAR_EPOCHS,
    _MAX_ABS_DELTA_T_YEAR,
    _delta_t_hpiers_annual_bridge,
    _delta_t_observation_boundary,
    julian_day,
)

__all__ = [
    "TIDAL_COEFF",
    "GIA_COEFF",
    "REFERENCE_LOD",
    "REFERENCE_YEAR",
    "secular_trend",
    "fluid_lowfreq",
    "historical_core_delta_t",
    "core_delta_t",
    "cryo_delta_t",
    "delta_t_hybrid",
    "delta_t_hybrid_uncertainty",
    "DeltaTDistribution",
    "delta_t_distribution",
    "DeltaTBreakdown",
    "delta_t_breakdown",
]


_DATA_DIR = Path(__file__).resolve().parent / "data"
_PACKAGED_DATA_DIR = _DATA_DIR

TIDAL_COEFF: float = 31.0
GIA_COEFF: float = -3.0

# Compatibility name: this value is a Delta-T baseline in seconds, not a
# length-of-day measurement.  Renaming the exported symbol would break the
# established Python surface, so the truthful meaning is documented here.
REFERENCE_LOD: float = 69.11474233219883
# Compatibility snapshot of the source-owned aggregate boundary at import time.
# Runtime routing reads the same boundary vessel dynamically, so refreshing
# the annual table cannot leave the model anchored to an independent literal.
REFERENCE_YEAR: float = _delta_t_observation_boundary().year

_PHYSICAL_SOURCE_START: float = -2000.0
_FORECAST_VALID_THROUGH: float = 2150.0
_SMH_FINAL_YEAR: float = 2016.0
# Uncalibrated bridge/aggregate policy scale.  The 0.06-second value covers
# the measured 0.052808-second maximum daily residual of the representative-
# epoch aggregate interpolation against the bundled EOP snapshot.
_MODERN_SOURCE_ERROR_FLOOR: float = 0.06

# Legacy scenario-spread coefficients retained for stable numerical behavior.
# They do not have a complete, traceable calibration record in this module and
# are not probability-standard-deviation claims.  In particular, no sourced
# uncertainty for the boundary value or its local slope is propagated.
_TIDAL_COEFF_SIGMA: float = abs(TIDAL_COEFF) * (0.003 / 25.858)
_GIA_COEFF_SIGMA: float = 0.5
_LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR: float = 0.2379
_LOD_OU_REVERSION_RATE: float = 0.1


def _coerce_model_year(year: float) -> float:
    """Return a finite admitted model year or raise ``ValueError``."""
    try:
        value = float(year)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Delta-T year must be a finite real number, got {year!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Delta-T year must be finite, got {year!r}")
    if value < _PHYSICAL_SOURCE_START:
        raise ValueError(
            "The physical Delta-T surface is source-bounded at year "
            f"{_PHYSICAL_SOURCE_START:g}; got {value:g}. "
            "Use moira.julian.delta_t for the canonical earlier-era extrapolation."
        )
    if value > _MAX_ABS_DELTA_T_YEAR:
        raise ValueError(
            "The physical Delta-T surface exceeds Moira's representable "
            f"year domain at {_MAX_ABS_DELTA_T_YEAR:g}; got {value:g}."
        )
    return value


def _finite_result(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{label} is not representable for the requested year")
    return value


def _canonical_delta_t(year: float) -> float:
    """Deferred import avoids the julian -> physical future-routing cycle."""
    from .julian import delta_t

    return delta_t(year)


def _reference_year() -> float:
    """Return the single source-owned observation boundary dynamically."""

    return _delta_t_observation_boundary().year


def _reference_total() -> float:
    return _delta_t_observation_boundary().total


def _reference_slope() -> float:
    """Return the provisional aggregate-epoch boundary slope in seconds/year.

    Aggregate values are materialized at their representative sample epochs;
    the final product is a Jan-Apr 2026 partial mean.  The resulting quotient
    is explicit scenario policy, not a measured instantaneous derivative.
    """
    return _delta_t_observation_boundary().slope


@dataclass(frozen=True, slots=True)
class _SMHPoint:
    """Vessel: One Stephenson-Morrison-Hohenkerk data point."""
    year: float
    delta_t: float
    error: float


@cache
def _load_smh2016_points() -> tuple[_SMHPoint, ...]:
    """Load the HPIERS/SMH table strictly, retaining its published error."""
    path = _DATA_DIR / "delta_t_hpiers_2016.txt"
    if not path.exists():
        raise FileNotFoundError(f"Required Delta-T authority table is missing: {path}")

    means: dict[float, float] = {}
    errors: dict[float, float] = {}
    previous_source_year: float | None = None
    data_rows = 0

    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 3:
            raise ValueError(f"{path}:{line_number}: expected year, Delta-T, and error")
        try:
            year = float(parts[0])
            delta_t_seconds = float(parts[1])
            error_seconds = float(parts[2])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: non-numeric Delta-T row") from exc
        if not all(math.isfinite(v) for v in (year, delta_t_seconds, error_seconds)):
            raise ValueError(f"{path}:{line_number}: non-finite Delta-T row")
        if error_seconds < 0.0:
            raise ValueError(f"{path}:{line_number}: negative source error")
        if previous_source_year is not None and year < previous_source_year:
            raise ValueError(f"{path}:{line_number}: source epochs are not non-decreasing")
        previous_source_year = year
        data_rows += 1

        previous_mean = means.get(year)
        previous_error = errors.get(year)
        if (
            previous_mean is not None
            and (previous_mean, previous_error) != (delta_t_seconds, error_seconds)
            and year not in _HPIERS_LATER_ROW_CONFLICT_EPOCHS
        ):
            raise ValueError(
                f"{path}:{line_number}: conflicting duplicate Delta-T epoch {year:g}"
            )
        # Exact duplicates are inert.  At the two declared source-regime joins,
        # the later row owns the shared epoch and the largest quoted error is
        # retained.
        means[year] = delta_t_seconds
        errors[year] = max(errors.get(year, 0.0), error_seconds)

    if data_rows == 0:
        raise ValueError(f"Required Delta-T authority table is empty: {path}")
    packaged_source = path.resolve() == (
        _PACKAGED_DATA_DIR / "delta_t_hpiers_2016.txt"
    ).resolve()
    if packaged_source and data_rows != _HPIERS_EXPECTED_DATA_ROWS:
        raise ValueError(
            f"Unexpected HPIERS row count {data_rows}; "
            f"expected {_HPIERS_EXPECTED_DATA_ROWS}"
        )
    points = tuple(_SMHPoint(year, means[year], errors[year]) for year in sorted(means))
    modern_epochs = tuple(
        point.year for point in points if 1950.0 <= point.year <= 2016.0
    )
    if packaged_source and modern_epochs != _HPIERS_MODERN_HALF_YEAR_EPOCHS:
        raise ValueError(
            "HPIERS 1950--2016 epochs do not preserve the declared "
            "half-year cadence"
        )
    if points[0].year != _PHYSICAL_SOURCE_START or points[-1].year != _SMH_FINAL_YEAR:
        raise ValueError(
            f"Unexpected HPIERS coverage {points[0].year:g}..{points[-1].year:g}; "
            f"expected {_PHYSICAL_SOURCE_START:g}..{_SMH_FINAL_YEAR:g}"
        )
    return points


@cache
def _load_smh2016_table() -> tuple[tuple[float, float], ...]:
    """Compatibility view of the strict HPIERS loader: ``(year, Delta-T)``."""
    return tuple((point.year, point.delta_t) for point in _load_smh2016_points())


@cache
def _load_smh2016_uncertainty_table() -> tuple[tuple[float, float], ...]:
    return tuple((point.year, point.error) for point in _load_smh2016_points())


def _interpolate_bounded(
    table: tuple[tuple[float, float], ...],
    year: float,
    *,
    product: str,
) -> float:
    if not table:
        raise RuntimeError(f"{product} table is empty")
    if year < table[0][0] or year > table[-1][0]:
        raise ValueError(
            f"{product} is defined on {table[0][0]:g}..{table[-1][0]:g}; got {year:g}"
        )
    if year == table[-1][0]:
        return table[-1][1]
    for (year0, value0), (year1, value1) in zip(table, table[1:]):
        if year0 <= year <= year1:
            fraction = (year - year0) / (year1 - year0)
            return value0 + fraction * (value1 - value0)
    raise RuntimeError(f"{product} interpolation failed inside declared coverage")


def _smh2016_lookup(year: float) -> float:
    """Interpolate the source Delta-T table without out-of-domain clamping."""
    value = _coerce_model_year(year)
    return _interpolate_bounded(_load_smh2016_table(), value, product="HPIERS Delta-T")


def _smh2016_uncertainty(year: float) -> float:
    value = _coerce_model_year(year)
    return _interpolate_bounded(
        _load_smh2016_uncertainty_table(), value, product="HPIERS Delta-T error"
    )


def secular_trend(year: float) -> float:
    """Boundary-conditioned tidal/GIA curvature in Delta-T seconds."""
    value = _coerce_model_year(year)
    centuries = (value - _reference_year()) / 100.0
    result = REFERENCE_LOD + (TIDAL_COEFF + GIA_COEFF) * centuries * centuries
    return _finite_result(result, "secular_trend")


def _future_secular_baseline(year: float) -> float:
    """Compatibility helper for the admitted curvature-only future baseline."""
    return secular_trend(year)


def fluid_lowfreq(year: float) -> float:
    """Reserved compatibility field; candidate AAM/OAM attribution is quarantined."""
    _coerce_model_year(year)
    return 0.0


def historical_core_delta_t(year: float) -> float:
    """Reserved compatibility field; no historical core inversion is admitted."""
    _coerce_model_year(year)
    return 0.0


def core_delta_t(year: float) -> float:
    """Reserved compatibility field; bundled C04 total LOD is not a core inversion."""
    _coerce_model_year(year)
    return 0.0


def cryo_delta_t(year: float) -> float:
    """Reserved compatibility field; the GRACE-derived candidate is quarantined."""
    _coerce_model_year(year)
    return 0.0


def _modern_bridge_coefficients() -> tuple[float, float]:
    """Legacy private diagnostic; no fitted polynomial bridge is admitted."""
    return (0.0, 0.0)


def _fit_fluid_lowfreq_coefficients() -> tuple[float, float]:
    """Legacy private diagnostic; no AAM/OAM regression is admitted."""
    return (0.0, 0.0)


def _historical_bridge_delta_t(year: float) -> float:
    value = _coerce_model_year(year)
    if not 1840.0 <= value < 1962.5:
        return 0.0
    return _canonical_delta_t(value) - secular_trend(value)


def _modern_bridge_delta_t(year: float) -> float:
    value = _coerce_model_year(year)
    if not 1962.5 <= value <= _reference_year():
        return 0.0
    return _canonical_delta_t(value) - secular_trend(value)


def _future_bridge_delta_t(year: float) -> float:
    value = _coerce_model_year(year)
    reference_year = _reference_year()
    if value <= reference_year:
        return 0.0
    horizon = value - reference_year
    return (_reference_total() - REFERENCE_LOD) + _reference_slope() * horizon


def _parse_strict_series(
    path: Path,
    *,
    value_name: str,
) -> tuple[tuple[float, float], ...]:
    if not path.exists():
        return ()
    rows: list[tuple[float, float]] = []
    previous_year: float | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            raise ValueError(f"{path}:{line_number}: expected year and {value_name}")
        try:
            year = float(parts[0])
            value = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: non-numeric research row") from exc
        if not math.isfinite(year) or not math.isfinite(value):
            raise ValueError(f"{path}:{line_number}: non-finite research row")
        if previous_year is not None and year <= previous_year:
            raise ValueError(f"{path}:{line_number}: epochs must be strictly increasing")
        previous_year = year
        rows.append((year, value))
    return tuple(rows)


@cache
def _load_grace_series() -> tuple[tuple[float, float, int], ...]:
    """Load the quarantined GRACE artifact strictly for provenance diagnostics."""
    path = _DATA_DIR / "grace_lod_contribution.txt"
    if not path.exists():
        return ()
    rows: list[tuple[float, float, int]] = []
    previous_year: float | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 3:
            raise ValueError(f"{path}:{line_number}: expected year, value, and gap flag")
        try:
            year = float(parts[0])
            value = float(parts[1])
            flag = int(parts[2])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: malformed GRACE research row") from exc
        if not math.isfinite(year) or not math.isfinite(value):
            raise ValueError(f"{path}:{line_number}: non-finite GRACE research row")
        if flag not in (0, 1):
            raise ValueError(f"{path}:{line_number}: gap flag must be 0 or 1")
        if previous_year is not None and year <= previous_year:
            raise ValueError(f"{path}:{line_number}: epochs must be strictly increasing")
        previous_year = year
        rows.append((year, value, flag))
    return tuple(rows)


@cache
def _load_core_series() -> tuple[tuple[float, float], ...]:
    """Load quarantined IERS total-LOD proxy rows for provenance diagnostics."""
    return _parse_strict_series(
        _DATA_DIR / "core_angular_momentum.txt", value_name="total LOD anomaly"
    )


@cache
def _load_historical_core_series() -> tuple[tuple[float, float], ...]:
    """Load optional research rows; absence never changes admitted runtime behavior."""
    return _parse_strict_series(
        _DATA_DIR / "historical_core_angular_momentum.txt",
        value_name="candidate historical LOD anomaly",
    )


def _annual_mean_midyear_jd(year: float) -> float | None:
    if not math.isfinite(year):
        raise ValueError("series epoch must be finite")
    whole_year = math.floor(year)
    if abs((year - whole_year) - 0.5) > 1e-9:
        return None
    start = julian_day(int(whole_year), 1, 1, 0.0)
    end = julian_day(int(whole_year) + 1, 1, 1, 0.0)
    return (start + end) / 2.0


def _series_epoch_delta_days(year0: float, year1: float) -> float:
    if not math.isfinite(year0) or not math.isfinite(year1) or year1 <= year0:
        raise ValueError("series epochs must be finite and strictly increasing")
    midpoint0 = _annual_mean_midyear_jd(year0)
    midpoint1 = _annual_mean_midyear_jd(year1)
    if midpoint0 is not None and midpoint1 is not None:
        return midpoint1 - midpoint0
    return (year1 - year0) * JULIAN_YEAR


def _lod_series_to_delta_t(
    series: tuple[tuple[float, float], ...]
) -> tuple[tuple[float, float], ...]:
    """Research helper: detrend and integrate an identified ms/day LOD series."""
    if not series:
        return ()
    for index, (year, lod) in enumerate(series):
        if not math.isfinite(year) or not math.isfinite(lod):
            raise ValueError("LOD research series contains a non-finite value")
        if index and year <= series[index - 1][0]:
            raise ValueError("LOD research series epochs must be strictly increasing")
    if len(series) == 1:
        return ((series[0][0], 0.0),)

    mean_year = sum(year for year, _ in series) / len(series)
    mean_lod = sum(lod for _, lod in series) / len(series)
    denominator = sum((year - mean_year) ** 2 for year, _ in series)
    slope = (
        sum((year - mean_year) * (lod - mean_lod) for year, lod in series) / denominator
        if denominator > 0.0
        else 0.0
    )
    intercept = mean_lod - slope * mean_year

    result: list[tuple[float, float]] = [(series[0][0], 0.0)]
    cumulative = 0.0
    for (year0, lod0), (year1, lod1) in zip(series, series[1:]):
        trend0 = intercept + slope * year0
        trend1 = intercept + slope * year1
        average_anomaly_ms = ((lod0 - trend0) + (lod1 - trend1)) / 2.0
        cumulative += average_anomaly_ms * _series_epoch_delta_days(year0, year1) / 1000.0
        result.append((year1, cumulative))
    return tuple(result)


@cache
def _get_core_dt_series() -> tuple[tuple[float, float], ...]:
    """Quarantined research diagnostic; never consumed by the admitted model."""
    return _lod_series_to_delta_t(_load_core_series())


@cache
def _core_recent_stats() -> tuple[float, float]:
    series = _get_core_dt_series()
    if len(series) < 2:
        return (0.0, 0.0)
    cutoff = series[-1][0] - 10.0
    window = [value for year, value in series if year >= cutoff]
    return (sum(window) / len(window), statistics.stdev(window) if len(window) > 1 else 0.0)


def _core_terminal_value() -> float:
    series = _get_core_dt_series()
    return series[-1][1] if series else 0.0


def _three_year_smooth(
    years: list[float], values: list[float]
) -> tuple[list[float], list[float]]:
    if len(years) != len(values):
        raise ValueError("years and values must have equal length")
    smoothed: list[float] = []
    for index in range(len(values)):
        low = max(0, index - 1)
        high = min(len(values), index + 2)
        smoothed.append(sum(values[low:high]) / (high - low))
    return years, smoothed


def _cosine_taper(year: float) -> float:
    """Retained numerical utility; no taper is used by the admitted model."""
    if year <= 2021.5:
        return 1.0
    if year >= 2024.5:
        return 0.0
    phase = (year - 2021.5) / 3.0
    return 0.5 * (1.0 + math.cos(math.pi * phase))


@dataclass(frozen=True, slots=True)
class _ResidualSplineFit:
    """Vessel: Structured residual spline fit data."""
    spline: None
    cv_rms: float
    in_sample_rms: float
    knot_count: int


def _fitted_residual_spline() -> _ResidualSplineFit:
    """Fail closed: the unvalidated residual fit is quarantined from runtime."""
    raise RuntimeError(
        "The residual spline is quarantined: its former cross-validation was "
        "not an independent, fail-closed authority validation."
    )


def _future_stochastic_delta_t_sigma(year: float) -> float:
    """Uncalibrated integrated O-U policy scale, evaluated without cancellation."""
    value = _coerce_model_year(year)
    horizon = max(0.0, value - _reference_year())
    if horizon == 0.0:
        return 0.0
    theta = _LOD_OU_REVERSION_RATE
    if not math.isfinite(theta) or theta <= 0.0:
        raise ValueError("O-U mean-reversion rate must be finite and positive")

    z = theta * horizon
    if z < 1e-3:
        bracket = z ** 3 * (
            2.0 / 3.0
            - z / 2.0
            + 7.0 * z * z / 30.0
            - z * z * z / 12.0
        )
    else:
        one_minus_exp = -math.expm1(-z)
        bracket = 2.0 * z - 2.0 * one_minus_exp - one_minus_exp * one_minus_exp
    if bracket < 0.0:
        raise ArithmeticError("Integrated O-U variance became negative")

    variance_years = bracket / (2.0 * theta ** 3)
    sigma = (
        JULIAN_YEAR
        / 1000.0
        * _LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR
        * math.sqrt(variance_years)
    )
    return _finite_result(sigma, "future stochastic Delta-T scale")


@dataclass(frozen=True, slots=True)
class DeltaTDistribution:
    """
    Normal-shaped mathematical convenience around a Delta-T policy scale.

    ``sigma`` is not claimed as calibrated 68-percent coverage or as complete
    structural model uncertainty. Historical HPIERS values carry the published
    source-error scale. Post-HPIERS modern values use a policy floor; future
    values use an uncalibrated scenario scale which omits unquantified boundary
    value and slope uncertainty. ``pdf`` and ``interval`` therefore express a
    caller-selected normal approximation, not a validated probability law.
    """

    year: float
    mean: float
    sigma: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.year, self.mean, self.sigma)):
            raise ValueError("DeltaTDistribution values must be finite")
        if self.sigma < 0.0:
            raise ValueError("DeltaTDistribution sigma must be non-negative")

    @property
    def variance(self) -> float:
        return self.sigma * self.sigma

    def pdf(self, delta_t_seconds: float) -> float:
        value = float(delta_t_seconds)
        if math.isnan(value):
            raise ValueError("Delta-T PDF input must not be NaN")
        if self.sigma == 0.0:
            return math.inf if value == self.mean else 0.0
        z = (value - self.mean) / self.sigma
        return math.exp(-0.5 * z * z) / (self.sigma * math.sqrt(2.0 * math.pi))

    def interval(self, sigma: float = 1.0) -> tuple[float, float]:
        scale = float(sigma)
        if not math.isfinite(scale):
            raise ValueError("Interval scale must be finite")
        width = abs(scale) * self.sigma
        return (self.mean - width, self.mean + width)


def delta_t_hybrid_uncertainty(year: float) -> float:
    """Return a source error or explicitly uncalibrated policy scale.

    HPIERS-era values use the table's published error. Later source-bridge and
    aggregate rows use a 0.06-second policy scale that covers the verified
    first-of-month residuals against the bundled EOP snapshot; the aggregate
    table carries no row-level errors. Future values add legacy curvature and stochastic
    policy terms arithmetically. The result has no calibrated coverage
    interpretation and does not propagate uncertainty in the boundary value or
    provisional aggregate-epoch boundary slope.
    """
    value = _coerce_model_year(year)
    hpiers_mean_final_year = _delta_t_hpiers_annual_bridge()[0][0]
    if value <= hpiers_mean_final_year:
        return _smh2016_uncertainty(value)
    reference_year = _reference_year()
    if value <= reference_year:
        return _MODERN_SOURCE_ERROR_FLOOR

    horizon = value - reference_year
    centuries_squared = (horizon / 100.0) ** 2
    result = math.fsum((
        _MODERN_SOURCE_ERROR_FLOOR,
        _TIDAL_COEFF_SIGMA * centuries_squared,
        _GIA_COEFF_SIGMA * centuries_squared,
        _future_stochastic_delta_t_sigma(value),
    ))
    return _finite_result(result, "Delta-T uncertainty scale")


@dataclass(frozen=True, slots=True)
class DeltaTBreakdown:
    """Additive, source-honest breakdown of Delta-T in seconds.

    ``era`` preserves legacy compatibility categories; it is not source-row
    provenance.  The actual total-source routing is described by
    :func:`delta_t_hybrid` and the module doctrine above.
    """

    year: float
    total: float
    secular: float
    core: float
    cryo: float
    fluid: float
    bridge: float
    residual: float
    era: str


def delta_t_breakdown(year: float) -> DeltaTBreakdown:
    """
    Return the stable public breakdown without unsupported attribution.

    ``bridge`` is the explicit empirical/source reconciliation between the
    curvature baseline and the admitted total.  Candidate component fields are
    retained as zero-valued compatibility surfaces until authoritative,
    independently identified products exist.  ``era`` retains its historical
    category strings and must not be interpreted as the active source branch.
    """
    value = _coerce_model_year(year)
    secular = secular_trend(value)

    if value <= _reference_year():
        total = _canonical_delta_t(value)
        bridge = total - secular
        if value < 1840.0:
            era = "pre-1840"
        elif value < 1962.5:
            era = "historical"
        else:
            era = "measured"
    else:
        bridge = _future_bridge_delta_t(value)
        total = _finite_result(secular + bridge, "future Delta-T mean")
        era = "future"

    return DeltaTBreakdown(
        year=value,
        total=total,
        secular=secular,
        core=0.0,
        cryo=0.0,
        fluid=0.0,
        bridge=bridge,
        residual=0.0,
        era=era,
    )


def delta_t_hybrid(year: float) -> float:
    """Return the source-bounded total or boundary-conditioned future scenario.

    The scenario is declared through 2150.  Later values are the same
    deterministic mathematical extrapolation, not authority-validated
    forecasts of Earth rotation.
    """
    return delta_t_breakdown(year).total


def delta_t_distribution(year: float) -> DeltaTDistribution:
    value = _coerce_model_year(year)
    return DeltaTDistribution(
        year=value,
        mean=delta_t_hybrid(value),
        sigma=delta_t_hybrid_uncertainty(value),
    )
