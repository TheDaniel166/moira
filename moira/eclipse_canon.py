"""
Moira — eclipse_canon.py
The Warden of Eclipse Canon: governs NASA-style lunar eclipse canon
compatibility — gamma computation, contact solving in TT, and method
comparison.

Boundary: owns canon geometry, TT-based contact solving, and method
comparison. Delegates shadow geometry primitives to eclipse_geometry,
refinement to eclipse_search, and time conversion to julian. Does NOT own
Moira's native eclipse truth surface.

Public surface:
    LunarCanonMethodId, LunarCanonGeometry, LunarCanonValidationCase,
    LunarCanonCaseResidual, LunarCanonMethodComparison, LunarCanonContacts,
    DEFAULT_LUNAR_CANON_METHOD, LUNAR_CANON_METHOD_IDS,
    lunar_canon_source_model, lunar_canon_geometry,
    refine_lunar_greatest_eclipse_canon_tt, find_lunar_contacts_canon,
    compare_lunar_canon_methods

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
"""

from dataclasses import dataclass
import math

from .constants import Body
from .corrections import apply_light_time
from .eclipse_geometry import (
    EARTH_RADIUS_KM,
    MOON_RADIUS_KM,
    apparent_radius,
    penumbra_radius,
    umbra_radius,
)
from .eclipse_search import refine_minimum
from .planets import _barycentric, _earth_barycentric, _geocentric
from .julian import tt_to_ut_nasa_canon, ut_to_tt_nasa_canon
from typing import Literal

LunarCanonMethodId = Literal[
    "nasa_shadow_axis_geometric_moon",
    "nasa_shadow_axis_retarded_moon",
]

DEFAULT_LUNAR_CANON_METHOD: LunarCanonMethodId = "nasa_shadow_axis_geometric_moon"

LUNAR_CANON_METHOD_IDS: tuple[LunarCanonMethodId, ...] = (
    "nasa_shadow_axis_geometric_moon",
    "nasa_shadow_axis_retarded_moon",
)

_LUNAR_CANON_SOURCE_MODELS: dict[LunarCanonMethodId, str] = {
    "nasa_shadow_axis_geometric_moon": (
        "NASA lunar canon compatibility layer "
        "(TT gamma minimum, geometric Moon, geometric Sun axis)"
    ),
    "nasa_shadow_axis_retarded_moon": (
        "NASA lunar canon experiment "
        "(TT gamma minimum, retarded Moon, geometric Sun axis)"
    ),
}


@dataclass(frozen=True, slots=True)
class LunarCanonGeometry:
    """
    RITE: The Lunar Canon Geometry Vessel

    THEOREM: Governs the storage of NASA-style lunar eclipse geometry in
    Earth-radii units at a specific TT Julian Day.

    RITE OF PURPOSE:
        LunarCanonGeometry is the authoritative data vessel for the NASA-canon
        shadow-axis geometry at a single TT epoch. It captures gamma (the
        minimum distance from the Moon's centre to the Earth's umbral-shadow
        axis in Earth equatorial radii), the raw axis distance in km, apparent
        radii of the Moon, umbra, and penumbra in Earth radii, and the derived
        umbral and penumbral magnitudes. Without it, callers would receive
        unstructured tuples with no field-level guarantees. It exists to give
        every higher-level consumer a single, named, immutable record of the
        canon geometry at a given TT epoch.

    LAW OF OPERATION:
        Responsibilities:
            - Store NASA-canon shadow-axis geometry as named, typed fields
            - Express all radii in Earth equatorial radii for direct gamma
              comparison
            - Serve as a read-only vessel passed between all higher-level
              consumers
        Non-responsibilities:
            - Computing geometry (delegates to lunar_canon_geometry)
            - Converting TT to UT (delegates to julian)
            - Performing eclipse detection or classification
        Dependencies:
            - Populated exclusively by lunar_canon_geometry()
        Structural invariants:
            - jd_tt is always a finite float
            - gamma_earth_radii is non-negative at greatest eclipse
        Behavioral invariants:
            - All consumers treat LunarCanonGeometry as read-only after
              construction

    Canon: NASA Five Millennium Canon of Lunar Eclipses (Espenak & Meeus)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse_canon.LunarCanonGeometry",
      "risk": "high",
      "api": {
        "frozen": [
          "jd_tt", "gamma_earth_radii", "axis_km",
          "moon_radius_earth_radii", "umbra_radius_earth_radii",
          "penumbra_radius_earth_radii", "umbral_magnitude",
          "penumbral_magnitude", "method"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["lunar_canon_geometry"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    jd_tt: float
    gamma_earth_radii: float
    axis_km: float
    moon_radius_earth_radii: float
    umbra_radius_earth_radii: float
    penumbra_radius_earth_radii: float
    umbral_magnitude: float
    penumbral_magnitude: float
    method: LunarCanonMethodId = DEFAULT_LUNAR_CANON_METHOD


@dataclass(frozen=True, slots=True)
class LunarCanonValidationCase:
    """
    RITE: The Lunar Canon Validation Case Vessel

    THEOREM: Governs the storage of a single NASA published eclipse row used
    for canon method validation.

    RITE OF PURPOSE:
        LunarCanonValidationCase is the authoritative data vessel for a single
        row from the NASA Five Millennium Canon of Lunar Eclipses. It captures
        the published UT of greatest eclipse, the published gamma value, and
        the eclipse type label. Without it, validation cases would be passed as
        unstructured tuples with no field-level guarantees. It exists to give
        compare_lunar_canon_methods a typed, named, immutable record of each
        NASA reference row.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single NASA published eclipse row as named, typed fields
            - Serve as a read-only input vessel for canon method comparison
        Non-responsibilities:
            - Computing any geometry (delegates to lunar_canon_geometry)
            - Performing eclipse detection or classification
            - Converting between time scales
        Dependencies:
            - Populated by callers of compare_lunar_canon_methods()
        Structural invariants:
            - nasa_ut is a finite float (Julian Day in UT)
            - label is a non-empty string identifying the eclipse
        Behavioral invariants:
            - All consumers treat LunarCanonValidationCase as read-only after
              construction

    Canon: NASA Five Millennium Canon of Lunar Eclipses (Espenak & Meeus)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse_canon.LunarCanonValidationCase",
      "risk": "medium",
      "api": {
        "frozen": ["label", "nasa_ut", "nasa_gamma_earth_radii", "eclipse_type"],
        "internal": []
      },
      "state": {"mutable": false, "owners": []},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    label: str
    nasa_ut: float
    nasa_gamma_earth_radii: float
    eclipse_type: str


@dataclass(frozen=True, slots=True)
class LunarCanonCaseResidual:
    """
    RITE: The Lunar Canon Case Residual Vessel

    THEOREM: Governs the storage of timing and gamma residuals between a Moira
    canon method and a single NASA published eclipse row.

    RITE OF PURPOSE:
        LunarCanonCaseResidual is the authoritative data vessel for the
        per-case residuals produced when a Moira canon method is compared
        against a single NASA reference row. It captures both the NASA
        published values and the Moira-computed values, together with the
        derived timing residual in seconds and the gamma residual in Earth
        radii. Without it, residual data would be scattered across unstructured
        collections. It exists to give LunarCanonMethodComparison a typed,
        named, immutable record of each per-case comparison result.

    LAW OF OPERATION:
        Responsibilities:
            - Store per-case residuals as named, typed fields
            - Carry both the NASA reference values and the Moira-computed
              values for full traceability
            - Serve as a read-only vessel inside LunarCanonMethodComparison
        Non-responsibilities:
            - Computing residuals (delegates to compare_lunar_canon_methods)
            - Performing eclipse detection or classification
            - Aggregating statistics across cases
        Dependencies:
            - Populated exclusively by compare_lunar_canon_methods()
        Structural invariants:
            - timing_residual_seconds = (moira_ut - nasa_ut) * 86400
            - gamma_residual_earth_radii = moira_gamma - nasa_gamma
        Behavioral invariants:
            - All consumers treat LunarCanonCaseResidual as read-only after
              construction

    Canon: NASA Five Millennium Canon of Lunar Eclipses (Espenak & Meeus)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse_canon.LunarCanonCaseResidual",
      "risk": "medium",
      "api": {
        "frozen": [
          "label", "method", "source_model",
          "nasa_ut", "nasa_gamma_earth_radii",
          "moira_ut", "moira_gamma_earth_radii",
          "timing_residual_seconds", "gamma_residual_earth_radii",
          "eclipse_type"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["compare_lunar_canon_methods"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    label: str
    method: LunarCanonMethodId
    source_model: str
    nasa_ut: float
    nasa_gamma_earth_radii: float
    moira_ut: float
    moira_gamma_earth_radii: float
    timing_residual_seconds: float
    gamma_residual_earth_radii: float
    eclipse_type: str


@dataclass(frozen=True, slots=True)
class LunarCanonMethodComparison:
    """
    RITE: The Lunar Canon Method Comparison Vessel

    THEOREM: Governs the storage of aggregate residual statistics for a single
    lunar canon method across all validation cases.

    RITE OF PURPOSE:
        LunarCanonMethodComparison is the authoritative data vessel for the
        aggregate comparison results of a single Moira canon method against the
        full set of NASA reference rows. It carries the per-case residuals
        together with the derived mean and maximum timing residuals and the
        maximum gamma residual. Without it, aggregate statistics would be
        scattered across unstructured collections. It exists to give callers of
        compare_lunar_canon_methods a typed, named, immutable summary of each
        method's accuracy.

    LAW OF OPERATION:
        Responsibilities:
            - Store aggregate residual statistics as named, typed fields
            - Carry the full tuple of per-case residuals for traceability
            - Serve as a read-only vessel returned by compare_lunar_canon_methods
        Non-responsibilities:
            - Computing residuals or statistics (delegates to
              compare_lunar_canon_methods)
            - Performing eclipse detection or classification
            - Selecting or ranking methods
        Dependencies:
            - Populated exclusively by compare_lunar_canon_methods()
        Structural invariants:
            - case_residuals is a non-empty tuple of LunarCanonCaseResidual
            - mean_timing_residual_seconds >= 0
            - max_timing_residual_seconds >= mean_timing_residual_seconds
        Behavioral invariants:
            - All consumers treat LunarCanonMethodComparison as read-only after
              construction

    Canon: NASA Five Millennium Canon of Lunar Eclipses (Espenak & Meeus)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse_canon.LunarCanonMethodComparison",
      "risk": "medium",
      "api": {
        "frozen": [
          "method", "source_model", "case_residuals",
          "mean_timing_residual_seconds", "max_timing_residual_seconds",
          "max_gamma_residual_earth_radii"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["compare_lunar_canon_methods"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    method: LunarCanonMethodId
    source_model: str
    case_residuals: tuple[LunarCanonCaseResidual, ...]
    mean_timing_residual_seconds: float
    max_timing_residual_seconds: float
    max_gamma_residual_earth_radii: float


@dataclass(frozen=True, slots=True)
class LunarCanonContacts:
    """
    RITE: The Lunar Canon Contacts Vessel

    THEOREM: Governs the storage of the seven NASA-canon contact Julian Days in
    TT with UT conversion properties.

    RITE OF PURPOSE:
        LunarCanonContacts is the authoritative data vessel for all seven
        phase-boundary contact times of a lunar eclipse solved in TT using the
        NASA-canon parameterisation: penumbral ingress (P1), partial umbral
        ingress (U1), totality ingress (U2), greatest eclipse, totality egress
        (U3), partial umbral egress (U4), and penumbral egress (P4). It
        exposes each contact in both TT (stored fields) and UT (computed
        properties via the NASA-canon Delta T path). Without it, callers would
        receive unstructured tuples with no field-level guarantees. It exists
        to give every higher-level consumer a single, named, immutable record
        of the canon eclipse timeline.

    LAW OF OPERATION:
        Responsibilities:
            - Store the seven contact Julian Days in TT as named, typed fields
            - Expose UT equivalents via read-only properties using the
              NASA-canon Delta T conversion
            - Permit None for contacts that do not occur (e.g. U2/U3 for a
              partial eclipse)
            - Serve as a read-only vessel passed between all higher-level
              consumers
        Non-responsibilities:
            - Computing contact times (delegates to find_lunar_contacts_canon)
            - Performing shadow geometry (delegates to lunar_canon_geometry)
            - Converting Julian Days to calendar dates or display strings
        Dependencies:
            - Populated exclusively by find_lunar_contacts_canon()
            - UT properties delegate to tt_to_ut_nasa_canon()
        Structural invariants:
            - greatest_tt is always a finite float
            - p1_tt, u1_tt, u2_tt, u3_tt, u4_tt, p4_tt are float | None
        Behavioral invariants:
            - All consumers treat LunarCanonContacts as read-only after
              construction

    Canon: NASA Five Millennium Canon of Lunar Eclipses (Espenak & Meeus)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse_canon.LunarCanonContacts",
      "risk": "high",
      "api": {
        "frozen": [
          "p1_tt", "u1_tt", "u2_tt", "greatest_tt",
          "u3_tt", "u4_tt", "p4_tt"
        ],
        "internal": [
          "p1_ut", "u1_ut", "u2_ut", "greatest_ut",
          "u3_ut", "u4_ut", "p4_ut"
        ]
      },
      "state": {"mutable": false, "owners": ["find_lunar_contacts_canon"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    p1_tt: float | None
    u1_tt: float | None
    u2_tt: float | None
    greatest_tt: float
    u3_tt: float | None
    u4_tt: float | None
    p4_tt: float | None

    @property
    def p1_ut(self) -> float | None:
        return None if self.p1_tt is None else tt_to_ut_nasa_canon(self.p1_tt)

    @property
    def u1_ut(self) -> float | None:
        return None if self.u1_tt is None else tt_to_ut_nasa_canon(self.u1_tt)

    @property
    def u2_ut(self) -> float | None:
        return None if self.u2_tt is None else tt_to_ut_nasa_canon(self.u2_tt)

    @property
    def greatest_ut(self) -> float:
        return tt_to_ut_nasa_canon(self.greatest_tt)

    @property
    def u3_ut(self) -> float | None:
        return None if self.u3_tt is None else tt_to_ut_nasa_canon(self.u3_tt)

    @property
    def u4_ut(self) -> float | None:
        return None if self.u4_tt is None else tt_to_ut_nasa_canon(self.u4_tt)

    @property
    def p4_ut(self) -> float | None:
        return None if self.p4_tt is None else tt_to_ut_nasa_canon(self.p4_tt)


def lunar_canon_source_model(method: LunarCanonMethodId = DEFAULT_LUNAR_CANON_METHOD) -> str:
    """Return the human-readable source model description for the given canon method."""
    return _LUNAR_CANON_SOURCE_MODELS[method]


def _lunar_canon_axis_geometry_tt(
    calculator,
    jd_tt: float,
    *,
    method: LunarCanonMethodId,
) -> tuple[float, float, float, float, float]:
    """
    Return shadow-axis geometry in physical units for a specific canon method.
    """
    reader = calculator._reader
    earth_ssb = _earth_barycentric(jd_tt, reader)
    sun_xyz = _geocentric(Body.SUN, jd_tt, reader)
    if method == "nasa_shadow_axis_geometric_moon":
        moon_xyz = _geocentric(Body.MOON, jd_tt, reader)
    elif method == "nasa_shadow_axis_retarded_moon":
        moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, reader, earth_ssb, _barycentric)
    else:
        raise ValueError(f"Unsupported lunar canon method: {method!r}")

    sun_xyz_ecl = sun_xyz
    moon_xyz_ecl = moon_xyz
    sun_norm = math.sqrt(sum(v * v for v in sun_xyz_ecl))
    axis_unit = tuple(-v / sun_norm for v in sun_xyz_ecl)
    axis_proj = sum(moon_xyz_ecl[i] * axis_unit[i] for i in range(3))
    perp = [moon_xyz_ecl[i] - axis_proj * axis_unit[i] for i in range(3)]
    axis_km = math.sqrt(sum(v * v for v in perp))
    sun_dist = sun_norm
    moon_dist = math.sqrt(sum(v * v for v in moon_xyz))
    moon_radius_deg = apparent_radius(MOON_RADIUS_KM, moon_dist)
    umbra_radius_deg = umbra_radius(sun_dist, moon_dist)
    penumbra_radius_deg = penumbra_radius(sun_dist, moon_dist)
    return axis_km, moon_dist, moon_radius_deg, umbra_radius_deg, penumbra_radius_deg


def lunar_canon_geometry(
    calculator,
    jd_tt: float,
    *,
    method: LunarCanonMethodId = DEFAULT_LUNAR_CANON_METHOD,
) -> LunarCanonGeometry:
    """
    Compute NASA-canon lunar eclipse geometry at a given TT Julian Day.

    Parameters
    ----------
    calculator:
        Moira calculator instance providing ephemeris access.
    jd_tt:
        Julian Day in Terrestrial Time at which to evaluate the geometry.
    method:
        Canon method identifier controlling how the Moon position is computed.

    Returns
    -------
    LunarCanonGeometry
        Shadow-axis geometry in Earth-radii units at jd_tt, including gamma,
        apparent radii, and umbral/penumbral magnitudes.
    """
    axis_km, moon_dist_km, moon_radius_deg, umbra_radius_deg, penumbra_radius_deg = (
        _lunar_canon_axis_geometry_tt(calculator, jd_tt, method=method)
    )
    gamma = axis_km / EARTH_RADIUS_KM
    moon_r = math.radians(moon_radius_deg) * moon_dist_km / EARTH_RADIUS_KM
    umbra_r = math.radians(umbra_radius_deg) * moon_dist_km / EARTH_RADIUS_KM
    penumbra_r = math.radians(penumbra_radius_deg) * moon_dist_km / EARTH_RADIUS_KM
    umbral_mag = (umbra_r + moon_r - gamma) / (2.0 * moon_r)
    penumbral_mag = (penumbra_r + moon_r - gamma) / (2.0 * moon_r)
    return LunarCanonGeometry(
        jd_tt=jd_tt,
        gamma_earth_radii=gamma,
        axis_km=axis_km,
        moon_radius_earth_radii=moon_r,
        umbra_radius_earth_radii=umbra_r,
        penumbra_radius_earth_radii=penumbra_r,
        umbral_magnitude=umbral_mag,
        penumbral_magnitude=penumbral_mag,
        method=method,
    )


def _bisect_root(func, a: float, b: float, iterations: int = 60) -> float:
    """Bisect to find a root of func in [a, b] to the given iteration depth."""
    fa = func(a)
    fb = func(b)
    for _ in range(iterations):
        m = (a + b) / 2.0
        fm = func(m)
        if fa == 0.0:
            return a
        if fb == 0.0:
            return b
        if fa * fm <= 0.0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return (a + b) / 2.0


def _find_roots(func, start: float, end: float, step_days: float) -> list[float]:
    """Scan [start, end] in steps of step_days and collect all sign-change roots of func."""
    roots: list[float] = []
    x = start
    fx = func(x)
    while x < end:
        nx = x + step_days
        fn = func(nx)
        if fx == 0.0 or fn == 0.0 or fx * fn < 0.0:
            roots.append(_bisect_root(func, x, nx))
        x, fx = nx, fn
    return roots


def refine_lunar_greatest_eclipse_canon_tt(
    calculator,
    center_jd_ut: float,
    *,
    method: LunarCanonMethodId = DEFAULT_LUNAR_CANON_METHOD,
    window_days: float = 0.125,
    tol_days: float = 1e-7,
) -> float:
    """
    Refine the TT Julian Day of greatest eclipse (minimum gamma) near a UT estimate.

    Parameters
    ----------
    calculator:
        Moira calculator instance providing ephemeris access.
    center_jd_ut:
        Approximate Julian Day in UT near the eclipse maximum.
    method:
        Canon method identifier controlling how the Moon position is computed.
    window_days:
        Half-width of the search window around center_jd_ut in days.
    tol_days:
        Convergence tolerance in days for the minimum search.

    Returns
    -------
    float
        Julian Day in TT of the refined greatest eclipse (minimum gamma).
    """
    center_tt = ut_to_tt_nasa_canon(center_jd_ut)
    return refine_minimum(
        lambda jd_tt: lunar_canon_geometry(
            calculator,
            jd_tt,
            method=method,
        ).gamma_earth_radii,
        center_tt,
        window_days=window_days,
        tol_days=tol_days,
        max_iter=100,
    )


def find_lunar_contacts_canon(
    calculator,
    center_jd_ut: float,
    *,
    method: LunarCanonMethodId = DEFAULT_LUNAR_CANON_METHOD,
    window_days: float = 0.2,
    coarse_step_seconds: float = 60.0,
) -> LunarCanonContacts:
    """
    Solve the seven NASA-canon lunar eclipse contact times near a UT estimate.

    Contacts are solved in TT using the canon geometry for the given method:
    - P1/P4: penumbral ingress/egress
    - U1/U4: partial umbral ingress/egress
    - U2/U3: totality ingress/egress (None for partial eclipses)

    Parameters
    ----------
    calculator:
        Moira calculator instance providing ephemeris access.
    center_jd_ut:
        Approximate Julian Day in UT near the eclipse maximum.
    method:
        Canon method identifier controlling how the Moon position is computed.
    window_days:
        Half-width of the search window around greatest eclipse in days.
    coarse_step_seconds:
        Step size in seconds for the coarse root scan.

    Returns
    -------
    LunarCanonContacts
        The seven contact Julian Days in TT (with UT properties) for the
        eclipse. Contacts that do not occur are None.
    """
    greatest_tt = refine_lunar_greatest_eclipse_canon_tt(
        calculator,
        center_jd_ut,
        method=method,
        window_days=window_days,
    )

    def geom(jd_tt: float) -> LunarCanonGeometry:
        return lunar_canon_geometry(calculator, jd_tt, method=method)

    def p_contact(jd_tt: float) -> float:
        g = geom(jd_tt)
        return g.gamma_earth_radii - (g.penumbra_radius_earth_radii + g.moon_radius_earth_radii)

    def u_contact(jd_tt: float) -> float:
        g = geom(jd_tt)
        return g.gamma_earth_radii - (g.umbra_radius_earth_radii + g.moon_radius_earth_radii)

    def total_contact(jd_tt: float) -> float:
        g = geom(jd_tt)
        return g.gamma_earth_radii - (g.umbra_radius_earth_radii - g.moon_radius_earth_radii)

    step_days = coarse_step_seconds / 86400.0
    start = greatest_tt - window_days
    end = greatest_tt + window_days

    p_roots = _find_roots(p_contact, start, end, step_days)
    u_roots = _find_roots(u_contact, start, end, step_days)
    t_roots = _find_roots(total_contact, start, end, step_days)

    return LunarCanonContacts(
        p1_tt=p_roots[0] if len(p_roots) >= 1 else None,
        u1_tt=u_roots[0] if len(u_roots) >= 1 else None,
        u2_tt=t_roots[0] if len(t_roots) >= 1 else None,
        greatest_tt=greatest_tt,
        u3_tt=t_roots[1] if len(t_roots) >= 2 else None,
        u4_tt=u_roots[1] if len(u_roots) >= 2 else None,
        p4_tt=p_roots[1] if len(p_roots) >= 2 else None,
    )


def compare_lunar_canon_methods(
    calculator,
    cases: tuple[LunarCanonValidationCase, ...] | list[LunarCanonValidationCase],
    *,
    methods: tuple[LunarCanonMethodId, ...] = LUNAR_CANON_METHOD_IDS,
) -> tuple[LunarCanonMethodComparison, ...]:
    """
    Compare supported lunar-canon methods against published NASA rows.
    """
    comparisons: list[LunarCanonMethodComparison] = []
    for method in methods:
        residuals: list[LunarCanonCaseResidual] = []
        for case in cases:
            moira_tt = refine_lunar_greatest_eclipse_canon_tt(
                calculator,
                case.nasa_ut,
                method=method,
            )
            moira_ut = tt_to_ut_nasa_canon(moira_tt)
            nasa_geom = lunar_canon_geometry(
                calculator,
                ut_to_tt_nasa_canon(case.nasa_ut),
                method=method,
            )
            residuals.append(
                LunarCanonCaseResidual(
                    label=case.label,
                    method=method,
                    source_model=lunar_canon_source_model(method),
                    nasa_ut=case.nasa_ut,
                    nasa_gamma_earth_radii=case.nasa_gamma_earth_radii,
                    moira_ut=moira_ut,
                    moira_gamma_earth_radii=nasa_geom.gamma_earth_radii,
                    timing_residual_seconds=(moira_ut - case.nasa_ut) * 86400.0,
                    gamma_residual_earth_radii=(
                        nasa_geom.gamma_earth_radii - case.nasa_gamma_earth_radii
                    ),
                    eclipse_type=case.eclipse_type,
                )
            )

        timing_errors = [abs(item.timing_residual_seconds) for item in residuals]
        gamma_errors = [abs(item.gamma_residual_earth_radii) for item in residuals]
        comparisons.append(
            LunarCanonMethodComparison(
                method=method,
                source_model=lunar_canon_source_model(method),
                case_residuals=tuple(residuals),
                mean_timing_residual_seconds=sum(timing_errors) / len(timing_errors),
                max_timing_residual_seconds=max(timing_errors),
                max_gamma_residual_earth_radii=max(gamma_errors),
            )
        )

    return tuple(comparisons)
