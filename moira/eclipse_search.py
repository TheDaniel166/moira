"""
Moira — eclipse_search.py
The Eclipse Search Engine: governs numerical search and refinement of eclipse
event maxima via ternary-search optimization over EclipseCalculator objectives.

Boundary: owns ternary-search refinement and eclipse-maximum dispatch. Delegates
shadow geometry and conjunction objectives to EclipseCalculator. Does not own
contact solving, eclipse classification, or canon lookup.

Public surface:
    refine_minimum, refine_lunar_greatest_eclipse, refine_solar_greatest_eclipse

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only.
"""

__all__ = [
    "refine_minimum",
    "refine_lunar_greatest_eclipse",
    "refine_solar_greatest_eclipse",
]


def _sample_window(objective, lo: float, hi: float, sample_count: int = 9) -> list[tuple[float, float]]:
    step = (hi - lo) / (sample_count - 1)
    return [(lo + (idx * step), objective(lo + (idx * step))) for idx in range(sample_count)]


def _sampled_window_is_unimodal(samples: list[tuple[float, float]]) -> bool:
    values = [value for _, value in samples]
    min_index = min(range(len(values)), key=values.__getitem__)
    if min_index == 0 or min_index == len(values) - 1:
        return False
    return (
        all(values[idx] <= values[idx - 1] for idx in range(1, min_index + 1))
        and all(values[idx] >= values[idx - 1] for idx in range(min_index + 1, len(values)))
    )


def _grid_refine_minimum(
    objective,
    lo: float,
    hi: float,
    *,
    tol_days: float,
    max_iter: int,
    subdivisions: int = 8,
) -> float:
    for _ in range(max_iter):
        if hi - lo < tol_days:
            break
        step = (hi - lo) / subdivisions
        points = [lo + (idx * step) for idx in range(subdivisions + 1)]
        values = [objective(point) for point in points]
        best_index = min(range(len(values)), key=values.__getitem__)
        if best_index == 0:
            hi = points[1]
        elif best_index == len(points) - 1:
            lo = points[-2]
        else:
            lo = points[best_index - 1]
            hi = points[best_index + 1]
    return (lo + hi) / 2.0


def refine_minimum(
    objective,
    center_jd: float,
    *,
    window_days: float = 0.125,
    tol_days: float = 5e-5,
    max_iter: int = 30,
) -> float:
    """
    Refine a local minimum near *center_jd*.

    Prefers ternary search when sampled behavior inside the window is smooth and
    unimodal. Falls back to bounded grid refinement when that assumption is not
    supported by the window samples.
    """
    lo = center_jd - window_days
    hi = center_jd + window_days
    samples = _sample_window(objective, lo, hi)
    if not _sampled_window_is_unimodal(samples):
        return _grid_refine_minimum(
            objective,
            lo,
            hi,
            tol_days=tol_days,
            max_iter=max_iter,
        )
    for _ in range(max_iter):
        if hi - lo < tol_days:
            break
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if objective(m1) < objective(m2):
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2.0


def refine_lunar_greatest_eclipse(
    calculator,
    center_jd: float,
    *,
    window_days: float = 0.125,
    tol_days: float = 5e-5,
) -> float:
    """
    Refine a full-moon seed to the current-model lunar greatest eclipse.

    Conducts ternary-search minimization over the calculator's lunar shadow
    axis distance objective (or angular separation fallback) to locate the
    Julian Day of greatest eclipse within the given window.

    Parameters
    ----------
    calculator:
        An EclipseCalculator instance. If it exposes
        ``_lunar_shadow_axis_distance_km``, that callable is used as the
        objective; otherwise falls back to minimizing
        ``|angular_separation_3d - 180°|``.
    center_jd:
        Julian Day near the full-moon seed from which to begin the search.
    window_days:
        Half-width of the ternary-search window in days.
    tol_days:
        Convergence tolerance in days; search halts when the bracket is
        narrower than this value.

    Returns
    -------
    float
        Julian Day of the lunar greatest eclipse refined to within *tol_days*.
    """
    if hasattr(calculator, "_lunar_shadow_axis_distance_km"):
        return refine_minimum(
            calculator._lunar_shadow_axis_distance_km,
            center_jd,
            window_days=window_days,
            tol_days=tol_days,
        )

    return refine_minimum(
        lambda jd: abs(calculator.calculate_jd(jd).angular_separation_3d - 180.0),
        center_jd,
        window_days=window_days,
        tol_days=tol_days,
    )


def refine_solar_greatest_eclipse(
    calculator,
    center_jd: float,
    *,
    window_days: float = 0.125,
    tol_days: float = 5e-5,
) -> float:
    """
    Refine a new-moon seed to the current-model solar greatest eclipse.

    Conducts ternary-search minimization over the calculator's native solar
    conjunction distance objective (or angular separation fallback) to locate
    the Julian Day of greatest eclipse within the given window.

    Parameters
    ----------
    calculator:
        An EclipseCalculator instance. If it exposes
        ``_native_solar_conjunction_distance_deg``, that callable is used as
        the objective; otherwise falls back to minimizing
        ``angular_separation_3d``.
    center_jd:
        Julian Day near the new-moon seed from which to begin the search.
    window_days:
        Half-width of the ternary-search window in days.
    tol_days:
        Convergence tolerance in days; search halts when the bracket is
        narrower than this value.

    Returns
    -------
    float
        Julian Day of the solar greatest eclipse refined to within *tol_days*.
    """

    if hasattr(calculator, "_native_solar_conjunction_distance_deg"):
        return refine_minimum(
            calculator._native_solar_conjunction_distance_deg,
            center_jd,
            window_days=window_days,
            tol_days=tol_days,
        )

    return refine_minimum(
        lambda jd: calculator.calculate_jd(jd).angular_separation_3d,
        center_jd,
        window_days=window_days,
        tol_days=tol_days,
    )
