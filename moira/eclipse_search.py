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

def refine_minimum(
    objective,
    center_jd: float,
    *,
    window_days: float = 0.125,
    tol_days: float = 5e-5,
    max_iter: int = 30,
) -> float:
    """
    Refine a local minimum near *center_jd* using ternary search.

    The objective is assumed to be smooth and unimodal inside the search window.
    """
    lo = center_jd - window_days
    hi = center_jd + window_days
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
