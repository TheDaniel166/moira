"""
Multiple Star Systems Oracle — moira/multiple_stars.py

Archetype: Oracle
Purpose: Catalog and orbital-mechanics engine for astrologically significant
         multiple star systems (binary, triple, and higher-order).

Boundary declaration
--------------------
Owns:
    - MultiType         — classification constants (VISUAL, WIDE, SPECTROSCOPIC, OPTICAL).
    - StarComponent     — frozen record for one stellar component (label, spectral
                          type, magnitude, mass, astrological note).
    - OrbitalElements   — Campbell visual-binary orbital elements for one pair,
                          or a reference separation/PA for WIDE/OPTICAL pairs.
    - MultipleStarSystem — complete catalog record for one multiple system.
    - _CATALOG          — module-level dict of all registered systems.
    - _solve_kepler()           — Newton-Raphson eccentric-anomaly solver.
    - _visual_binary_rho_theta() — Thiele-Innes sky-plane projection.
    - angular_separation_at()   — angular separation (arcsec) at a given JD.
    - position_angle_at()       — position angle (°, N through E) at a given JD.
    - is_resolvable()           — Dawes-limit check for a given telescope aperture.
    - dominant_component()      — brightest (smallest magnitude) component.
    - combined_magnitude()      — combined apparent V magnitude of the system.
    - components_at()           — full snapshot dict at a given JD.
    - multiple_star()           — catalog lookup by name or designation.
    - list_multiple_stars()     — sorted list of canonical system names.
    - multiple_stars_by_type()  — filter catalog by MultiType.
    - sirius_ab_separation_at() — convenience: Sirius A–B separation in arcsec.
    - sirius_b_resolvable()     — convenience: can Sirius B be split at given aperture?
    - castor_separation_at()    — convenience: Castor A–B separation in arcsec.
    - alpha_cen_separation_at() — convenience: α Cen A–B separation in arcsec.
Delegates:
    - Nothing; all computation is self-contained pure arithmetic (stdlib math only).

Import-time side effects:
    - _CATALOG is populated at import time by module-level _reg() calls.
      This is a pure in-memory dict build; no I/O occurs.

External dependency assumptions:
    - No Qt, no database, no OS threads, no network.
    - No external catalog files required.

Public surface / exports:
    MultiType, StarComponent, OrbitalElements, MultipleStarSystem
    angular_separation_at(), position_angle_at()
    is_resolvable(), dominant_component(), combined_magnitude(), components_at()
    multiple_star(), list_multiple_stars(), multiple_stars_by_type()
    sirius_ab_separation_at(), sirius_b_resolvable()
    castor_separation_at(), alpha_cen_separation_at()

Multiple-star types handled
---------------------------
  VISUAL        — Visual binary with a published orbital solution (Campbell elements).
                  angular_separation_at() and position_angle_at() compute the current
                  projected sky position from Kepler's equation + Thiele-Innes
                  constants.  Used for Sirius (50-yr orbit) and α Centauri (80-yr).

  WIDE          — Visual pair whose orbital period is centuries or millennia long,
                  making the elements poorly constrained or the orbital motion
                  imperceptibly slow.  Reference separation and position angle
                  (at approximately J2000) are stored; the functions return those
                  fixed values.  Used for Castor, Mizar, Acrux.

  SPECTROSCOPIC — Pair detectable only by Doppler shifts; the angular separation
                  is measured in milli-arcseconds and is never resolvable by any
                  ground-based telescope.  angular_separation_at() returns 0.0 and
                  is_resolvable() always returns False.  Used for Capella, Spica.

  OPTICAL       — Chance line-of-sight alignment; the stars are at different
                  distances and are not gravitationally bound.  Treated like WIDE
                  (fixed reference values) but flagged as unbound.  Used for Albireo
                  (Gaia DR3 parallax differences confirm non-association).

Orbital mechanics
-----------------
For VISUAL systems the projected position is computed using the standard
visual-binary formalism:

  1. Mean anomaly:         M = 2π(t − T₀) / P
  2. Eccentric anomaly E:  solve M = E − e·sin E  (Newton-Raphson, ≤50 iter)
  3. Thiele-Innes constants from (a, i, Ω, ω):
       A = a(cos ω·cos Ω − sin ω·sin Ω·cos i)
       B = a(cos ω·sin Ω + sin ω·cos Ω·cos i)
       F = a(−sin ω·cos Ω − cos ω·sin Ω·cos i)
       G = a(−sin ω·sin Ω + cos ω·cos Ω·cos i)
  4. Ellipse coords:       X = cos E − e,   Y = √(1−e²)·sin E
  5. Sky coords:           x_E = B·X + G·Y  (East),  y_N = A·X + F·Y  (North)
  6. Separation:           ρ = √(x_E² + y_N²)
     Position angle:       θ = atan2(x_E, y_N) mod 360°   [N through E]

Catalog sources
---------------
  WDS  — Washington Double Star Catalog (Mason et al., ongoing)
  INT4 — Fourth Interferometric Catalog (Hartkopf & Mason 2004)
  6OC  — Sixth Orbit Catalog (Hartkopf et al. 2001, updated)
  Pourbaix et al. 2002, A&A 386, 280    — α Centauri AB
  Bond et al. 2017, ApJ 840, 70         — Sirius AB
  Torres et al. 2009, A&A 502, 253      — Capella
  Herbison-Evans et al. 1971, MNRAS 151 — Spica

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE FREEZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The design below is frozen.  No system type, solver constant, resolvability
formula, magnitude formula, or catalog entry schema may change without
explicit revision of this docstring, the VALIDATION CODEX below, and the
corresponding tests.

System type doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    VISUAL        — Kepler + Thiele-Innes projection; full ρ/θ computation.
    WIDE          — Reference separation and PA returned as fixed values.
    SPECTROSCOPIC — angular_separation_at() returns 0.0; is_resolvable()
                    always returns False regardless of aperture.
    OPTICAL       — Treated like WIDE (fixed reference values); flagged as
                    gravitationally unbound (Gaia parallax evidence).

Kepler solver doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Newton-Raphson iteration on M = E − e·sin(E).
    Convergence tolerance: |ΔE| < 1e-12  (machine precision for all
    eccentricities in catalog, e < 0.62).
    Maximum iterations: 50.
    Initial guess: E = M for e < 0.8, else E = π.

Thiele-Innes projection doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Campbell elements (a, i, Ω, ω) → Thiele-Innes constants (A, B, F, G).
    Sky coordinates: x_E = B·X + G·Y  (East),  y_N = A·X + F·Y  (North).
    Separation ρ = √(x_E² + y_N²).
    Position angle θ = atan2(x_E, y_N) mod 360°, measured N through E.

Resolvability doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Dawes' empirical limit: R″ = 116 / D_mm.
    SPECTROSCOPIC systems are never resolvable regardless of aperture.
    For all other types, is_resolvable returns True iff
    angular_separation_at(system, jd) ≥ 116 / aperture_mm.

Combined magnitude doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    combined_magnitude = −2.5 · log10(Σ 10^(−m_i / 2.5))
    where the sum runs over all components with finite magnitude.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION CODEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every rule below must be provable by an existing test.  Adding a rule
requires adding a test.  Removing a test requires removing or revising
the corresponding rule.

RULE-01  Catalog lookup raises on unknown names
    multiple_star() raises KeyError for any name not in _CATALOG.

RULE-02  SPECTROSCOPIC separation is always 0.0
    angular_separation_at(system, jd) == 0.0 for any system with
    system_type == MultiType.SPECTROSCOPIC, for any jd.

RULE-03  SPECTROSCOPIC is never resolvable
    is_resolvable(system, jd, aperture_mm) is False for any SPECTROSCOPIC
    system, for any jd and any aperture_mm.

RULE-04  VISUAL separation is positive and varies with JD
    For a VISUAL system (Sirius, α Cen), angular_separation_at returns a
    positive float that differs between two JDs separated by several years.

RULE-05  WIDE/OPTICAL return fixed reference values
    For WIDE and OPTICAL systems, angular_separation_at returns the same
    value for any two distinct JDs (the reference separation is constant).

RULE-06  Dawes limit formula
    is_resolvable returns True iff separation ≥ 116.0 / aperture_mm.
    At exactly the limit, the result is True (≥, not >).

RULE-07  dominant_component returns minimum-magnitude component
    dominant_component(system) returns the StarComponent with the
    smallest .magnitude value among all components.

RULE-08  combined_magnitude formula
    combined_magnitude(system) == −2.5·log10(Σ 10^(−m_i/2.5)) within
    1e-9 for all catalog systems.

RULE-09  list_multiple_stars is sorted
    list_multiple_stars() returns names in ascending lexicographic order.

RULE-10  multiple_stars_by_type filters correctly
    multiple_stars_by_type(MultiType.VISUAL) returns only systems whose
    system_type == MultiType.VISUAL; same for all other type strings.

RULE-11  Public surface sealed
    moira.__all__ and moira.multiple_stars.__all__ expose exactly
    {MultiType, StarComponent, OrbitalElements, MultipleStarSystem,
     angular_separation_at, position_angle_at, is_resolvable,
     dominant_component, combined_magnitude, components_at,
     multiple_star, list_multiple_stars, multiple_stars_by_type,
     sirius_ab_separation_at, sirius_b_resolvable,
     castor_separation_at, alpha_cen_separation_at}.
    No internal name (_CATALOG, _reg, _solve_kepler, etc.) appears in
    either __all__.
"""

import math
from dataclasses import dataclass

__all__ = [
    "MultiType",
    "StarComponent",
    "OrbitalElements",
    "MultipleStarSystem",
    "angular_separation_at",
    "position_angle_at",
    "is_resolvable",
    "dominant_component",
    "combined_magnitude",
    "components_at",
    "multiple_star",
    "list_multiple_stars",
    "multiple_stars_by_type",
    "sirius_ab_separation_at",
    "sirius_b_resolvable",
    "castor_separation_at",
    "alpha_cen_separation_at",
]


# ---------------------------------------------------------------------------
# Classification constants
# ---------------------------------------------------------------------------

class MultiType:
    """
    Namespace of multiple-star classification constants.

    VISUAL        — Gravitationally bound pair with a published orbital solution;
                    separation and position angle are computed from Kepler mechanics.
    WIDE          — Bound (or possibly bound) visual pair with a period too long
                    to yield a reliable computed orbit; reference values are used.
    SPECTROSCOPIC — Bound pair detectable only by radial-velocity variations;
                    the angular separation is sub-milliarcsecond and unresolvable.
    OPTICAL       — Chance line-of-sight alignment; not gravitationally bound.
    """
    VISUAL        = "visual"
    WIDE          = "wide"
    SPECTROSCOPIC = "spectroscopic"
    OPTICAL       = "optical"


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class StarComponent:
    """
    Immutable record for one stellar component within a multiple system.

    Fields
    ------
    label         : "A", "B", "C", "Aa", "Ab", etc.
    spectral_type : MK spectral classification (e.g. "A1Vm", "DA2", "G2V").
    magnitude     : Apparent Johnson V magnitude of this component alone.
                    Use math.nan where individual magnitudes are unresolved.
    mass_solar    : Mass in solar units.  math.nan if unknown.
    note          : One-line astrological and astronomical characterisation.
    """
    label:         str
    spectral_type: str
    magnitude:     float
    mass_solar:    float
    note:          str


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """
    Campbell visual-binary orbital elements for one pair, or reference position
    data for WIDE / OPTICAL / SPECTROSCOPIC pairs.

    Fields
    ------
    label             : Pair identifier, e.g. "AB", "(AB)C", "Aa-Ab".
    period_yr         : Orbital period in Julian years.  0.0 = unknown / too long.
    epoch_jd          : Julian Day of periastron passage (ignored when period_yr = 0).
    ecc               : Eccentricity [0, 1).
    semi_major_arcsec : Apparent semi-major axis in arcseconds (VISUAL), OR the
                        reference angular separation for WIDE / OPTICAL pairs.
    incl_deg          : Orbital inclination in degrees.
    node_deg          : Position angle of ascending node Ω in degrees.
    arg_peri_deg      : Argument of periastron ω in degrees (for primary component).
    ref_pa_deg        : Reference position angle for WIDE / OPTICAL pairs (degrees,
                        N through E, approximately J2000).  Ignored for VISUAL.
    period_uncertain  : True when the orbital period is based on a short arc and
                        carries significant uncertainty.
    """
    label:             str
    period_yr:         float
    epoch_jd:          float
    ecc:               float
    semi_major_arcsec: float
    incl_deg:          float
    node_deg:          float
    arg_peri_deg:      float
    ref_pa_deg:        float = 0.0
    period_uncertain:  bool  = False


@dataclass(frozen=True, slots=True)
class MultipleStarSystem:
    """
    Complete catalog record for one multiple star system.

    Fields
    ------
    name              : Canonical common name (e.g. "Sirius", "Alpha Centauri").
    designation       : Bayer / Flamsteed (e.g. "alp CMa", "alp Gem").
    also_known_as     : Tuple of additional name/designation aliases.
    system_type       : MultiType constant for the primary (closest) pair.
    components        : Tuple of StarComponent records, one per visual component.
                        Spectroscopic sub-components may be described in notes.
    orbits            : Tuple of OrbitalElements records.  orbits[0] is for the
                        primary (tightest / most astrologically relevant) pair.
    combined_mag      : Combined apparent Johnson V magnitude of the whole system.
    classical_quality : "malefic", "benefic", "neutral", or "mixed".
    note              : Extended astrological and physical description.
    """
    name:              str
    designation:       str
    also_known_as:     tuple[str, ...]
    system_type:       str
    components:        tuple[StarComponent, ...]
    orbits:            tuple[OrbitalElements, ...]
    combined_mag:      float
    classical_quality: str
    note:              str


# ---------------------------------------------------------------------------
# Kepler mechanics
# ---------------------------------------------------------------------------

def _solve_kepler(M: float, ecc: float) -> float:
    """
    Solve Kepler's equation M = E − e·sin(E) for the eccentric anomaly E.

    Uses Newton-Raphson iteration.  Converges to machine precision (|ΔE| < 1e-12)
    in ≤ 10 iterations for all eccentricities encountered here (e < 0.62).

    Parameters
    ----------
    M   : mean anomaly in radians (any range; reduced mod 2π internally)
    ecc : orbital eccentricity [0, 1)

    Returns
    -------
    Eccentric anomaly E in radians, in [0, 2π).
    """
    tau = 2.0 * math.pi
    M   = M % tau
    E   = M if ecc < 0.8 else math.pi
    for _ in range(50):
        dE = (M - E + ecc * math.sin(E)) / (1.0 - ecc * math.cos(E))
        E += dE
        if abs(dE) < 1e-12:
            break
    return E % tau


def _visual_binary_rho_theta(orb: OrbitalElements, jd: float) -> tuple[float, float]:
    """
    Compute the projected angular separation and position angle of a visual binary.

    Uses the Thiele-Innes formulation of the Campbell orbital elements.

    Parameters
    ----------
    orb : OrbitalElements with period_yr > 0
    jd  : Julian Day (TT)

    Returns
    -------
    (rho, theta) — separation in arcseconds, position angle in degrees [0, 360)
    measured North through East.
    """
    t_yr = (jd - orb.epoch_jd) / 365.25
    P    = orb.period_yr
    e    = orb.ecc
    a    = orb.semi_major_arcsec

    M = (2.0 * math.pi * t_yr / P) % (2.0 * math.pi)
    E = _solve_kepler(M, e)

    # Thiele-Innes constants (Campbell elements → sky-plane basis)
    omega = math.radians(orb.arg_peri_deg)
    Omega = math.radians(orb.node_deg)
    incl  = math.radians(orb.incl_deg)

    co = math.cos(omega);  so = math.sin(omega)
    cO = math.cos(Omega);  sO = math.sin(Omega)
    ci = math.cos(incl)

    A =  a * ( co * cO - so * sO * ci)
    B =  a * ( co * sO + so * cO * ci)
    F =  a * (-so * cO - co * sO * ci)
    G =  a * (-so * sO + co * cO * ci)

    # Ellipse coordinates in the orbital plane
    X = math.cos(E) - e
    Y = math.sqrt(1.0 - e * e) * math.sin(E)

    # Project to sky (East = x_e, North = y_n)
    x_e = B * X + G * Y
    y_n = A * X + F * Y

    rho   = math.hypot(x_e, y_n)
    theta = math.degrees(math.atan2(x_e, y_n)) % 360.0
    return rho, theta


# ---------------------------------------------------------------------------
# Public API — orbital queries
# ---------------------------------------------------------------------------

def angular_separation_at(system: MultipleStarSystem, jd: float) -> float:
    """
    Return the angular separation (arcseconds) of the primary pair at JD.

    Dispatch:
      VISUAL        — computed from orbital elements via Kepler + Thiele-Innes.
      WIDE / OPTICAL — returns the stored reference separation (approximately
                       valid for the J2000–J2100 window; orbital motion is below
                       0.1 arcsec/century for these systems).
      SPECTROSCOPIC  — returns 0.0 (sub-milliarcsecond separation; unresolvable).

    Parameters
    ----------
    system : MultipleStarSystem from the catalog
    jd     : Julian Day (TT or UT; the difference is negligible here)

    Returns
    -------
    Separation in arcseconds.
    """
    if not system.orbits:
        return 0.0
    orb = system.orbits[0]
    if system.system_type == MultiType.SPECTROSCOPIC:
        return 0.0
    if orb.period_yr <= 0.0 or system.system_type in (MultiType.WIDE, MultiType.OPTICAL):
        return orb.semi_major_arcsec
    rho, _ = _visual_binary_rho_theta(orb, jd)
    return rho


def position_angle_at(system: MultipleStarSystem, jd: float) -> float:
    """
    Return the position angle (degrees, N through E) of the primary pair at JD.

    Dispatch follows the same rules as angular_separation_at().
    SPECTROSCOPIC systems return 0.0 (undefined).

    Parameters
    ----------
    system : MultipleStarSystem from the catalog
    jd     : Julian Day (TT)

    Returns
    -------
    Position angle in degrees [0, 360).
    """
    if not system.orbits:
        return 0.0
    orb = system.orbits[0]
    if system.system_type == MultiType.SPECTROSCOPIC:
        return 0.0
    if orb.period_yr <= 0.0 or system.system_type in (MultiType.WIDE, MultiType.OPTICAL):
        return orb.ref_pa_deg
    _, theta = _visual_binary_rho_theta(orb, jd)
    return theta


def is_resolvable(
    system: MultipleStarSystem,
    jd: float,
    aperture_mm: float = 100.0,
) -> bool:
    """
    Return True if the primary pair can be split by a telescope of aperture_mm.

    Uses Dawes' empirical limit: R″ = 116 / D_mm.  Examples:
      60 mm   → 1.93″   (typical beginner refractor)
      100 mm  → 1.16″   (default — good 4-inch telescope)
      200 mm  → 0.58″   (8-inch)
      400 mm  → 0.29″   (16-inch)

    SPECTROSCOPIC systems always return False regardless of aperture.

    Parameters
    ----------
    system      : MultipleStarSystem from the catalog
    jd          : Julian Day
    aperture_mm : Telescope clear aperture in millimetres (default 100)

    Returns
    -------
    True if the current separation ≥ Dawes' limit for the given aperture.
    """
    if system.system_type == MultiType.SPECTROSCOPIC:
        return False
    rho          = angular_separation_at(system, jd)
    dawes_limit  = 116.0 / aperture_mm
    return rho >= dawes_limit


def dominant_component(system: MultipleStarSystem) -> StarComponent:
    """
    Return the visually brightest (smallest V magnitude) stellar component.

    This is the component that dominates the combined light and therefore
    the astrological quality of the system.

    Parameters
    ----------
    system : MultipleStarSystem from the catalog

    Returns
    -------
    The StarComponent with the smallest magnitude value.
    """
    return min(system.components, key=lambda c: c.magnitude)


def combined_magnitude(system: MultipleStarSystem) -> float:
    """
    Return the combined apparent V magnitude of the whole system.

    The value is derived from the listed component magnitudes by summing flux:

      combined_magnitude = -2.5 * log10(sum(10 ** (-m_i / 2.5)))

    Components with non-finite magnitudes are ignored. This keeps the function
    aligned with the subsystem's frozen validation doctrine instead of merely
    echoing a stored catalog approximation.

    Parameters
    ----------
    system : MultipleStarSystem from the catalog

    Returns
    -------
    Combined V magnitude.
    """
    flux = sum(
        10.0 ** (-component.magnitude / 2.5)
        for component in system.components
        if math.isfinite(component.magnitude)
    )
    return -2.5 * math.log10(flux) if flux > 0.0 else math.nan


def components_at(system: MultipleStarSystem, jd: float) -> dict:
    """
    Return a full snapshot of the system state at a given JD.

    Returns
    -------
    dict with keys:
      "separation_arcsec"    — float: current A–B separation
      "position_angle_deg"   — float: current position angle (N through E)
      "is_resolvable_100mm"  — bool:  splittable with a 100 mm telescope
      "is_resolvable_200mm"  — bool:  splittable with a 200 mm telescope
      "dominant_component"   — str:   label of the brightest component
      "components"           — dict[label → {spectral_type, magnitude,
                                              mass_solar, note}]
    """
    rho = angular_separation_at(system, jd)
    pa  = position_angle_at(system, jd)
    return {
        "separation_arcsec":   rho,
        "position_angle_deg":  pa,
        "is_resolvable_100mm": is_resolvable(system, jd, 100.0),
        "is_resolvable_200mm": is_resolvable(system, jd, 200.0),
        "dominant_component":  dominant_component(system).label,
        "components": {
            c.label: {
                "spectral_type": c.spectral_type,
                "magnitude":     c.magnitude,
                "mass_solar":    c.mass_solar,
                "note":          c.note,
            }
            for c in system.components
        },
    }


# ---------------------------------------------------------------------------
# Catalog lookup
# ---------------------------------------------------------------------------

_CATALOG: dict[str, MultipleStarSystem] = {}


def _reg(system: MultipleStarSystem) -> MultipleStarSystem:
    _CATALOG[system.name.lower()] = system
    _CATALOG[system.designation.lower()] = system
    for alias in system.also_known_as:
        _CATALOG[alias.lower()] = system
    return system


def multiple_star(name: str) -> MultipleStarSystem:
    """
    Return a MultipleStarSystem by name, designation, or alias.

    Raises
    ------
    KeyError if the name is not in the catalog.  Use list_multiple_stars()
    to inspect available systems.
    """
    key = name.lower().strip()
    if key not in _CATALOG:
        raise KeyError(
            f"Unknown multiple star system: {name!r}. "
            f"Available: {list_multiple_stars()}"
        )
    return _CATALOG[key]


def list_multiple_stars() -> list[str]:
    """Return a sorted list of canonical system names in the catalog."""
    return sorted({s.name for s in _CATALOG.values()})


def multiple_stars_by_type(multi_type: str) -> list[MultipleStarSystem]:
    """
    Return all systems of a given MultiType, deduplicated by name.

    Parameters
    ----------
    multi_type : one of MultiType.VISUAL / WIDE / SPECTROSCOPIC / OPTICAL
    """
    seen: set[str] = set()
    result: list[MultipleStarSystem] = []
    for s in _CATALOG.values():
        if s.system_type == multi_type and s.name not in seen:
            seen.add(s.name)
            result.append(s)
    return result


# ---------------------------------------------------------------------------
# Catalog — 8 astrologically significant multiple star systems
# ---------------------------------------------------------------------------

# ── 1. Sirius (α Canis Majoris) — VISUAL binary, 50.09-year orbit ───────────
#
# Orbital elements: Bond et al. 2017, ApJ 840, 70.
# T_peri = 1994.3 yr → JD 2449463  (J2000 − 5.7 yr × 365.25 d/yr)
# The most precisely known stellar orbit for a naked-eye binary.

_reg(MultipleStarSystem(
    name         = "Sirius",
    designation  = "alp CMa",
    also_known_as= ("alpha canis majoris", "α cma", "sirius ab", "dog star"),
    system_type  = MultiType.VISUAL,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "A1Vm",
            magnitude     = -1.46,
            mass_solar    = 2.063,
            note          = (
                "The visible Sirius — brightest star in the sky.  A1V main-sequence "
                "star, 25× solar luminosity, 1.71× solar radius.  The solar champion: "
                "heroic radiance, worldly excellence, the kingly fire of the Dog Star.  "
                "In Egypt, its heliacal rising marked the Nile flood and the new year."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "DA2",
            magnitude     = 8.44,
            mass_solar    = 1.018,
            note          = (
                "Sirius B — the Pup, a white dwarf: the compressed remnant of a star "
                "that was once larger than A.  Roughly the size of Earth, it contains "
                "a solar mass.  Discovered 1862 (Alvan Clark).  In Dogon cosmology it "
                "is 'Digitaria' (po tolo) — the smallest and heaviest thing, source of "
                "all existence, known centuries before telescopes confirmed it.  "
                "The occult knowledge: the hidden fire that outweighs the visible star."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 50.090,
            epoch_jd          = 2449463.0,   # T_peri 1994.3
            ecc               = 0.5914,
            semi_major_arcsec = 7.56,
            incl_deg          = 136.336,
            node_deg          = 44.57,
            arg_peri_deg      = 147.27,
        ),
    ),
    combined_mag      = -1.46,
    classical_quality = "benefic",
    note = (
        "SIRIUS — The Dog Star, α Canis Majoris.  Brightest star in the night sky "
        "(V = −1.46).  A binary system: Sirius A (A1V, blazing main-sequence star) "
        "and Sirius B (DA2, white dwarf).  Orbital period 50.09 years; eccentricity "
        "0.59 — a highly elongated orbit that carries B from 3\" at periastron to over "
        "11\" at apastron.  Last periastron: 1994.3.  Next: ~2044.  As of 2026 the "
        "pair is moving back toward each other (separation ~8–10\"), still easily "
        "split in any 60 mm telescope.\n\n"
        "The two stars embody opposite principles: A is the seen, the solar, the "
        "worldly crown; B is the hidden, the compressed, the ancestral dead.  "
        "When Sirius B is wide (near apastron ~2019) the occult knowledge is "
        "accessible and distant.  As B closes toward A (approaching periastron ~2044) "
        "the hidden approaches the visible — an intensification of the dual nature.\n\n"
        "Ptolemy: Jupiter/Mars nature.  Later tradition adds Venus.  Lilly: 'very "
        "fortunate if well placed'.  Heliacal rising used by Egyptians to open the "
        "sacred year — the original star clock."
    ),
))


# ── 2. Castor (α Geminorum) — WIDE visual binary, sextuple system ────────────
#
# Castor is the most numerically complex stellar system among bright naked-eye
# stars: six components in three nested pairs.
# Visual A+B: P ≈ 467 yr (Heintz 1988), only ~1/5 of the orbit observed;
# elements are unreliable for precise computation — stored as WIDE.
# Reference separation (J2020): ~3.9″, PA ~52°.
# Castor A = Aa+Ab (spectroscopic binary, P = 9.21 d)
# Castor B = Ba+Bb (spectroscopic binary, P = 2.93 d)
# Castor C = YY Gem (Ca+Cb, eclipsing binary, P = 0.814 d) — 72″ away

_reg(MultipleStarSystem(
    name         = "Castor",
    designation  = "alp Gem",
    also_known_as= ("alpha geminorum", "α gem", "castor ab", "castor abc"),
    system_type  = MultiType.WIDE,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "A2Vm+A",
            magnitude     = 1.93,
            mass_solar    = 2.76,
            note          = (
                "Castor A — combined light of spectroscopic pair Aa (A2Vm) + Ab (~A0V), "
                "period 9.21 days.  The 'mortal twin' of Gemini.  Mercury/Apollo nature: "
                "intellect, craft, the skilled hand.  Dominant in the visual separation."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "Am+K",
            magnitude     = 2.97,
            mass_solar    = 2.37,
            note          = (
                "Castor B — combined light of spectroscopic pair Ba+Bb, period 2.93 days.  "
                "Am (metallic-line A) + K-type companion.  The secondary voice — softer, "
                "closer, complementary to A's dominance.  Always within 4–6\" of A."
            ),
        ),
        StarComponent(
            label         = "C",
            spectral_type = "M1Ve+M1Ve",
            magnitude     = 8.80,
            mass_solar    = 0.62,
            note          = (
                "Castor C = YY Geminorum — a 9th-magnitude eclipsing binary at 72\" "
                "(≈72 000 AU) from AB.  Two red M-dwarfs orbiting every 0.814 days.  "
                "Too faint for the naked eye; the hidden third heart of the system.  "
                "Gravitationally bound despite the enormous separation."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 467.0,
            epoch_jd          = 0.0,            # not used (WIDE type)
            ecc               = 0.33,
            semi_major_arcsec = 3.9,            # reference separation J2020
            incl_deg          = 0.0,
            node_deg          = 0.0,
            arg_peri_deg      = 0.0,
            ref_pa_deg        = 52.0,           # reference PA J2020
            period_uncertain  = True,
        ),
        OrbitalElements(
            label             = "AB-C",
            period_yr         = 0.0,            # unknown; likely ~14000 yr
            epoch_jd          = 0.0,
            ecc               = 0.0,
            semi_major_arcsec = 72.0,           # reference separation
            incl_deg          = 0.0,
            node_deg          = 0.0,
            arg_peri_deg      = 0.0,
            ref_pa_deg        = 164.0,
            period_uncertain  = True,
        ),
    ),
    combined_mag      = 1.57,
    classical_quality = "neutral",
    note = (
        "CASTOR — α Geminorum.  The mortal twin of the Gemini pair (Pollux is the "
        "immortal; Castor is named for the tamer of horses).  What appears to the "
        "naked eye as a single star of magnitude 1.6 is in truth a sextuple system:\n\n"
        "  • Castor A  (mag 1.93) = spectroscopic binary Aa+Ab, P = 9.21 d\n"
        "  • Castor B  (mag 2.97) = spectroscopic binary Ba+Bb, P = 2.93 d\n"
        "  • Castor C  (mag 8.80) = eclipsing binary Ca+Cb (YY Gem), P = 0.814 d\n\n"
        "Visual A+B separation ~3.9\" (PA ~52°, epoch 2020) — resolvable in any 60 mm "
        "telescope.  The ~467-year visual orbit has only been observed across ~1/5 of "
        "its arc; orbital elements are poorly constrained.\n\n"
        "The astrological principle: Gemini is the sign of duality, and Castor is "
        "duality iterated.  The surface duality (A vs. B, 3.9\" apart) conceals a "
        "duality within each component, and a third hidden pair (C) gravitationally "
        "bound at 72\" — duality three levels deep.  The mind does not divide once; "
        "it divides endlessly.  Mercury nature: quick, bifurcating, adaptive."
    ),
))


# ── 3. Alpha Centauri — VISUAL triple, 79.91-year A+B orbit ─────────────────
#
# Orbital elements: Pourbaix et al. 2002, A&A 386, 280 (still the standard).
# T_peri = 1955.67 yr → JD 2435353  (J2000 − 44.33 yr × 365.25 d/yr)
# Last periastron 1955.67; next ~2035.58.  Currently (2026) approaching
# next periastron; separation decreasing from ~21.5\" (apastron ~1995) toward ~4\".
# Proxima Centauri (M5.5Ve, V=11.13, P_outer ~547 000 yr): bound but too
# widely separated to include as an OrbitalElements entry.

_reg(MultipleStarSystem(
    name         = "Alpha Centauri",
    designation  = "alp Cen",
    also_known_as= (
        "alpha centauri", "rigil kentaurus", "rigil kent", "rigil",
        "α cen", "alp cen ab", "proxima centauri system",
    ),
    system_type  = MultiType.VISUAL,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "G2V",
            magnitude     = 0.01,
            mass_solar    = 1.100,
            note          = (
                "α Cen A — a near-perfect solar twin: G2V, 1.1 M☉, 1.22 R☉, surface "
                "temperature 5790 K.  The nearest other sun.  At 4.37 ly it is the "
                "brightest of the nearest stars.  Sol's sibling in spectral class: "
                "what our own Sun looks like from 4 light-years away."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "K1V",
            magnitude     = 1.33,
            mass_solar    = 0.907,
            note          = (
                "α Cen B — K1V dwarf, cooler and dimmer than A, slightly smaller than "
                "the Sun.  Orange-gold hue.  In the binary pair it plays Venus/Saturn "
                "to A's Sun: measured, reflective, inward.  Candidate host for "
                "rocky planets (though Proxima b is currently the nearest known "
                "exoplanet in the system)."
            ),
        ),
        StarComponent(
            label         = "C",
            spectral_type = "M5.5Ve",
            magnitude     = 11.13,
            mass_solar    = 0.122,
            note          = (
                "Proxima Centauri — the nearest star to the Sun (4.24 ly, slightly "
                "closer than A+B).  A red M-dwarf flare star, gravitationally bound "
                "to AB in an enormous ~547 000-year orbit at ~1.3° angular separation.  "
                "Too faint for the naked eye.  Host of Proxima Centauri b, a rocky "
                "planet in the habitable zone — the nearest known exoworld."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 79.91,
            epoch_jd          = 2435353.0,   # T_peri 1955.67
            ecc               = 0.5179,
            semi_major_arcsec = 17.57,
            incl_deg          = 79.20,
            node_deg          = 204.85,
            arg_peri_deg      = 231.65,
        ),
    ),
    combined_mag      = -0.27,
    classical_quality = "benefic",
    note = (
        "ALPHA CENTAURI — Rigil Kentaurus, α Centauri AB.  Third brightest star "
        "in the sky (combined V = −0.27).  The nearest stellar system to the Sun "
        "(4.37 light-years for A+B; 4.24 ly for Proxima C).\n\n"
        "A triple: α Cen A (G2V solar twin) + α Cen B (K1V, orange dwarf) in a "
        "79.91-year visual orbit, plus Proxima Centauri (M5.5Ve red dwarf) in an "
        "immense outer orbit of ~547 000 years.\n\n"
        "A+B orbital arc 2025–2035: the pair is currently approaching periastron "
        "(next ~2035.6).  At apastron (~1995) the separation reached ~22\"; by "
        "periastron it shrinks to ~4\" before the cycle resumes.  A telescope of "
        "60 mm can split the pair through most of the orbit.\n\n"
        "The astrological picture: two distinct suns in intimate orbit — the solar "
        "twin (A) and its companion (B) each represent a complete solar principle.  "
        "Their proximity embodies the nearest possible 'other' — the mirror of self, "
        "the companion who is almost identical but fundamentally other.  In "
        "Southern Hemisphere traditions α Cen was a navigation star and anchor of "
        "the Southern Cross — an orientation point for the whole sky.\n\n"
        "Proxima C adds the dimension of the hidden nearest: the closest star of all "
        "is dim, red, and ordinarily invisible — another occult undercurrent beneath "
        "the brilliant pair.  Ptolemy: Venus/Jupiter nature."
    ),
))


# ── 4. Mizar (ζ Ursae Majoris) — WIDE visual binary, first telescopic binary ─
#
# Discovered as a visual double in 1650 by Riccioli — the first telescopic
# binary found.  Mizar A was also the first spectroscopic binary discovered
# (Pickering 1889).  Reference separation (J2000): ~14.4″, PA ~152°.
# The wide outer companion Alcor (80 UMa, mag 3.99) is at ~11′ 49″;
# included as a separate wide component for completeness.

_reg(MultipleStarSystem(
    name         = "Mizar",
    designation  = "zet UMa",
    also_known_as= ("zeta ursae majoris", "ζ uma", "mizar-alcor", "80 uma"),
    system_type  = MultiType.WIDE,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "A2V+A2V",
            magnitude     = 2.23,
            mass_solar    = 2.2,
            note          = (
                "Mizar A — itself a spectroscopic binary (Aa+Ab, P = 20.54 d), the "
                "first spectroscopic binary ever discovered.  Apparent magnitude 2.23.  "
                "The dominant star of the Mizar visual pair."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "A1V",
            magnitude     = 3.88,
            mass_solar    = 1.6,
            note          = (
                "Mizar B — A1V dwarf at 14.4\" from A.  Also a spectroscopic binary "
                "(Ba+Bb, P = 175.6 d).  Separated from A by ~500 AU; gravitationally "
                "bound, orbiting over an estimated ~5000 years."
            ),
        ),
        StarComponent(
            label         = "C",
            spectral_type = "A5V",
            magnitude     = 3.99,
            mass_solar    = 1.8,
            note          = (
                "Alcor (80 UMa) — the 'rider' to Mizar's 'horse'.  At ~11′ 49\" "
                "angular separation; recently confirmed as gravitationally bound "
                "(Mamajek et al. 2010).  Both are members of the Ursa Major Moving Group.  "
                "Alcor is itself a close spectroscopic pair."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 0.0,            # estimated ~5000 yr; not constrained
            epoch_jd          = 0.0,
            ecc               = 0.0,
            semi_major_arcsec = 14.4,           # reference separation (J2000)
            incl_deg          = 0.0,
            node_deg          = 0.0,
            arg_peri_deg      = 0.0,
            ref_pa_deg        = 152.0,
            period_uncertain  = True,
        ),
    ),
    combined_mag      = 2.04,
    classical_quality = "neutral",
    note = (
        "MIZAR — ζ Ursae Majoris.  The handle of the Big Dipper, the horse of the "
        "'horse and rider' pair (Mizar + Alcor).  The first binary star observed "
        "through a telescope (Riccioli 1650).  Mizar A was also the first "
        "spectroscopic binary ever discovered (Pickering 1889).\n\n"
        "A+B separation ~14.4\" (PA ~152°) — easily split in any small telescope, "
        "and to sharp eyes the 3.99-magnitude Alcor is visible ~12′ away without "
        "optical aid.  The Arabic 'test of eyesight' tradition: those who could "
        "see Alcor next to Mizar were fit for the army.\n\n"
        "The system is a quadruple (Mizar A+B visual) + Alcor (possible fifth and "
        "sixth component), all members of the Ursa Major Moving Group — a loose "
        "open cluster of which the five middle Dipper stars are remnants.\n\n"
        "Astrological principle: the directed gaze reveals multiplicity.  The "
        "ordinary turns extraordinary under scrutiny.  Ursa Major is circumpolar "
        "for mid-northern latitudes — it never sets, the eternal guardian, the "
        "compass of the sky.  Mars nature according to Ptolemy."
    ),
))


# ── 5. Albireo (β Cygni) — OPTICAL pair, complementary-colour double ─────────
#
# The most visually striking colour-contrast pair in the sky: K3 orange giant
# + B9 blue star.  Gaia DR3 (2022) parallaxes show significantly different
# distances (A ≈ 380 ly, B ≈ 340 ly), confirming this is an optical double —
# chance alignment, not a gravitationally bound binary.
# Albireo A is itself a spectroscopic binary (K3II + A0V, P = 214 d).

_reg(MultipleStarSystem(
    name         = "Albireo",
    designation  = "bet Cyg",
    also_known_as= ("beta cygni", "β cyg", "albireo ab"),
    system_type  = MultiType.OPTICAL,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "K3II+A0",
            magnitude     = 3.09,
            mass_solar    = float("nan"),
            note          = (
                "Albireo A — amber/gold K3 giant, itself a spectroscopic binary "
                "(K3II + A0V, P = 214 d, unresolvable).  The warm, 'female' pole "
                "of the colour-contrast pair.  ~380 light-years distant."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "B9V",
            magnitude     = 5.11,
            mass_solar    = float("nan"),
            note          = (
                "Albireo B — sapphire-blue B9V main-sequence star.  The cool, "
                "'male' pole.  ~340 light-years distant — confirming that A and B "
                "are not physically associated.  The beauty is a coincidence of line "
                "of sight, which makes it no less real."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 0.0,            # optical — no orbit
            epoch_jd          = 0.0,
            ecc               = 0.0,
            semi_major_arcsec = 34.4,           # reference separation (J2000)
            incl_deg          = 0.0,
            node_deg          = 0.0,
            arg_peri_deg      = 0.0,
            ref_pa_deg        = 54.0,
            period_uncertain  = False,
        ),
    ),
    combined_mag      = 3.08,
    classical_quality = "benefic",
    note = (
        "ALBIREO — β Cygni, at the beak of the Swan.  The most celebrated "
        "colour-contrast double in amateur astronomy: gold (K3II, mag 3.09) and "
        "sapphire-blue (B9V, mag 5.11) at 34.4\" separation.  Resolvable in any "
        "binocular or small telescope.\n\n"
        "Gaia DR3 (2022) confirmed what was long suspected: A is ~380 ly away and "
        "B ~340 ly — a chance alignment, not a bound binary.  The stars are not "
        "companions; they are strangers whose light crosses our sky together.\n\n"
        "Astrological principle: beauty without bond.  The optical double is the "
        "archetype of apparent unity masking real difference.  In Cygnus the Swan "
        "(associated with Apollo, Orpheus, the dying god's song), the beak-star "
        "offers complementary qualities — the warm creativity of K3 orange and the "
        "piercing clarity of blue B9.  Venus/Mercury nature.  A reminder that not "
        "all apparent partnerships are true conjunctions."
    ),
))


# ── 6. Capella (α Aurigae) — SPECTROSCOPIC binary, two G giants ──────────────
#
# Capella is the sixth brightest star in the sky.  It is a spectroscopic binary
# of two nearly identical G-type giants, impossible to separate visually
# (angular separation ~0.001″).  Orbital period 104.022 days.
# Torres et al. 2009, A&A 502, 253 give the definitive orbital solution.

_reg(MultipleStarSystem(
    name         = "Capella",
    designation  = "alp Aur",
    also_known_as= ("alpha aurigae", "α aur", "capella ab", "the goat star"),
    system_type  = MultiType.SPECTROSCOPIC,
    components   = (
        StarComponent(
            label         = "Aa",
            spectral_type = "G8III",
            magnitude     = 0.91,
            mass_solar    = 2.5687,
            note          = (
                "Capella Aa — G8 giant, just past the red-giant branch base.  "
                "Slightly cooler and larger than Ab.  The 'elder' of the two goats.  "
                "Jupiter/Saturn nature: authority, beneficence approaching the "
                "reflective phase of the late giant."
            ),
        ),
        StarComponent(
            label         = "Ab",
            spectral_type = "G0III",
            magnitude     = 0.76,
            mass_solar    = 2.4828,
            note          = (
                "Capella Ab — G0 giant, slightly hotter and more luminous than Aa.  "
                "The 'younger' of the pair.  Within ~100 million years both will "
                "become red giants; they are evolutionary twins at slightly different "
                "stages.  The more active partner (chromospheric emission detected)."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "Aa-Ab",
            period_yr         = 104.022 / 365.25,   # 0.28477 yr
            epoch_jd          = 2440537.320,         # Torres et al. 2009 T0
            ecc               = 0.00000,             # circular orbit
            semi_major_arcsec = 0.001,               # ~0.001″ — unresolvable
            incl_deg          = 137.156,
            node_deg          = 40.522,
            arg_peri_deg      = 342.6,
        ),
    ),
    combined_mag      = 0.08,
    classical_quality = "benefic",
    note = (
        "CAPELLA — α Aurigae.  The sixth brightest star (V = 0.08), and the most "
        "luminous binary among the brightest 10 stars.  The charioteer's goat.\n\n"
        "Two nearly identical G-type giants — Aa (G8III, 2.57 M☉) and Ab (G0III, "
        "2.48 M☉) — orbiting every 104.022 days in a near-perfect circle.  They "
        "are separated by only ~100 million km (~0.67 AU), closer than Earth is to "
        "the Sun.  Angular separation ~0.001\" — no telescope can split them.  "
        "The duality is invisible, encoded in spectral lines.\n\n"
        "Astrologically, Capella exemplifies hidden duality: the perfect partnership "
        "of equals that cannot be seen from outside.  The two giants will become red "
        "giants within ~100 million years, nearly simultaneously — they will end "
        "together as they live together.  The charioteer who drives two horses as "
        "one: mastery through integration rather than division.\n\n"
        "Jupiter nature (Ptolemy).  Lilly: 'of the nature of Mercury and Saturn… "
        "good fortune and preferment'.  The charioteer stars (Auriga) were "
        "associated with safe passage and skill."
    ),
))


# ── 7. Acrux (α Crucis) — WIDE visual binary, foot of the Southern Cross ─────
#
# Brightest star in Crux (Southern Cross), 14th brightest star overall.
# Visual pair A+B at ~4.0″ separation (PA ~114°).  Orbital period unknown
# (very long; estimated >1500 yr).  Acrux A is itself a spectroscopic binary
# (Aa+Ab, P = 75.8 d).  A third component Acrux C at ~90″ is an unrelated
# B5 star.

_reg(MultipleStarSystem(
    name         = "Acrux",
    designation  = "alp Cru",
    also_known_as= ("alpha crucis", "α cru", "acrux ab", "becrux partner"),
    system_type  = MultiType.WIDE,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "B0.5IV+B",
            magnitude     = 1.33,
            mass_solar    = 17.8,
            note          = (
                "Acrux A — B0.5IV subgiant, itself a spectroscopic binary (Aa+Ab, "
                "P = 75.8 d).  The dominant component.  Extremely hot (30 000 K), "
                "intense UV/X-ray source.  Mars/Saturn martial character: cutting, "
                "precise, navigational."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "B1V",
            magnitude     = 1.73,
            mass_solar    = 14.0,
            note          = (
                "Acrux B — B1V main-sequence star.  Slightly cooler than A but of "
                "the same martial blue-white quality.  Both A and B will end as "
                "supernovae within a few million years.  Two blue giants, "
                "two cutting forces."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 0.0,            # unknown; estimated >1500 yr
            epoch_jd          = 0.0,
            ecc               = 0.0,
            semi_major_arcsec = 4.0,            # reference separation (J2000)
            incl_deg          = 0.0,
            node_deg          = 0.0,
            arg_peri_deg      = 0.0,
            ref_pa_deg        = 114.0,
            period_uncertain  = True,
        ),
    ),
    combined_mag      = 0.77,
    classical_quality = "malefic",
    note = (
        "ACRUX — α Crucis.  The brightest point of the Southern Cross (Crux), "
        "14th brightest star overall (V = 0.77 combined).  Never visible above "
        "~25° N latitude.  The anchor of the Southern celestial pole finder.\n\n"
        "Visual pair A (B0.5IV, 1.33) + B (B1V, 1.73) at ~4\" separation (PA ~114°) "
        "— split in any 60 mm telescope.  Both are massive OB stars: A is ~17.8 M☉, "
        "B is ~14 M☉.  Both will explode as core-collapse supernovae within a few "
        "million years.  Acrux A is itself a spectroscopic binary (period 75.8 days).\n\n"
        "Astrological principle: the Southern Cross was the primary navigation star "
        "of the Southern Hemisphere — orientation, direction, the true south.  Its "
        "two brightest stars mark the long axis of the cross, the pointer toward the "
        "south celestial pole.  Two blue-white giants of pure martial intensity: Mars "
        "doubled.  Piercing, precise, inevitable.  The navigational sword: "
        "you cannot get lost if you look at it rightly."
    ),
))


# ── 8. Spica (α Virginis) — SPECTROSCOPIC binary, behenian star ──────────────
#
# Spica is both a behenian star (variable_stars.py tracks its ellipsoidal
# variability) and a spectroscopic binary.  The two B-type giants orbit every
# 4.0145 days in a slightly eccentric orbit, tidally distorted into egg shapes
# (ellipsoidal variable, hence the variability tracked in variable_stars.py).
# Herbison-Evans et al. 1971, MNRAS 151, 161.

_reg(MultipleStarSystem(
    name         = "Spica",
    designation  = "alp Vir",
    also_known_as= ("alpha virginis", "α vir", "spica ab", "azimech"),
    system_type  = MultiType.SPECTROSCOPIC,
    components   = (
        StarComponent(
            label         = "A",
            spectral_type = "B1III-IV",
            magnitude     = 0.98,
            mass_solar    = 10.25,
            note          = (
                "Spica A — B1 giant/subgiant, primary source of the system's light.  "
                "10.25 M☉, radius 7.4 R☉, luminosity ~12 000 L☉.  Dominates the "
                "combined magnitude of 0.97.  Venus/Mars in Ptolemy."
            ),
        ),
        StarComponent(
            label         = "B",
            spectral_type = "B2IV",
            magnitude     = 3.60,
            mass_solar    = 6.97,
            note          = (
                "Spica B — B2 subgiant, 6.97 M☉, radius 3.6 R☉.  The secondary "
                "makes a minor contribution to the combined light.  The close orbit "
                "(0.18 AU separation) raises tidal distortions in both stars — their "
                "egg-shaped deformation drives the ellipsoidal light variation "
                "tracked in variable_stars.py."
            ),
        ),
    ),
    orbits = (
        OrbitalElements(
            label             = "AB",
            period_yr         = 4.0145 / 365.25,   # 0.010990 yr
            epoch_jd          = 2440678.09,          # Herbison-Evans T0
            ecc               = 0.067,
            semi_major_arcsec = 0.0,                 # unresolvable (~0.0003″)
            incl_deg          = 65.4,
            node_deg          = 255.0,
            arg_peri_deg      = 255.0,
        ),
    ),
    combined_mag      = 0.97,
    classical_quality = "benefic",
    note = (
        "SPICA — α Virginis.  Fifteenth brightest star (V = 0.97), the jewel in "
        "the ear of the celestial Maiden.  One of the fifteen Behenian fixed stars.  "
        "Hipparchos used Spica to discover the precession of the equinoxes (127 BCE).\n\n"
        "Beneath the perfect stellar point lies intense hidden dynamism: two B-type "
        "giants (A: B1III, 10.25 M☉; B: B2IV, 6.97 M☉) orbiting every 4.0145 days "
        "at only 0.18 AU separation.  The tidal forces at this range have deformed "
        "both stars into prolate ellipsoids, producing the ellipsoidal brightness "
        "variation (~0.03 mag) tracked as a variable in variable_stars.py.\n\n"
        "The angular separation (~0.0003″) is wholly unresolvable: the duality is "
        "as hidden as possible, encoded only in Doppler shifts.  Spica presents as "
        "perfection; the reality is two massive stars in furious mutual orbit.\n\n"
        "Ptolemy: Venus/Mars nature.  In Virgo, associated with grain, harvest, "
        "the synthesis of matter and spirit.  A behenian stone: emerald.  "
        "A behenian herb: sage.  The image: a mantled and armed man."
    ),
))


# ---------------------------------------------------------------------------
# Convenience functions — named-system shortcuts
# ---------------------------------------------------------------------------

def sirius_ab_separation_at(jd: float) -> float:
    """
    Return the current angular separation of Sirius A and B in arcseconds.

    Computed from the Bond et al. (2017) orbital elements.  The separation
    ranges from ~3″ (near periastron, ~2044) to ~11.5″ (near apastron, ~2019).

    Parameters
    ----------
    jd : Julian Day (TT)
    """
    return angular_separation_at(multiple_star("Sirius"), jd)


def sirius_b_resolvable(jd: float, aperture_mm: float = 100.0) -> bool:
    """
    Return True if Sirius B can be split from Sirius A at the given aperture.

    Uses Dawes' limit (116 / D_mm arcseconds).  With a 60 mm telescope the
    limit is 1.93″; Sirius B remains splittable at any separation > 1.93″,
    which covers the vast majority of its 50-year orbit.

    Parameters
    ----------
    jd          : Julian Day (TT)
    aperture_mm : Telescope clear aperture in millimetres (default 100)
    """
    return is_resolvable(multiple_star("Sirius"), jd, aperture_mm)


def castor_separation_at(jd: float) -> float:
    """
    Return the reference angular separation of Castor A and B in arcseconds.

    Note: the Castor AB orbit (~467 yr) is not well-characterized; this
    function returns the J2020-epoch reference value of ~3.9 arcseconds.
    The true current separation varies slowly (~0.01 arcsec/yr).

    Parameters
    ----------
    jd : Julian Day (TT)
    """
    return angular_separation_at(multiple_star("Castor"), jd)


def alpha_cen_separation_at(jd: float) -> float:
    """
    Return the current angular separation of α Centauri A and B in arcseconds.

    Computed from the Pourbaix et al. (2002) orbital elements.  The separation
    ranges from ~4″ (periastron, last 1955.67, next ~2035.6) to ~22″ (apastron
    ~1995.6).  As of 2026 the pair is approaching next periastron.

    Parameters
    ----------
    jd : Julian Day (TT)
    """
    return angular_separation_at(multiple_star("Alpha Centauri"), jd)
