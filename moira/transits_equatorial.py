"""
Moira — transits_equatorial.py
The Predictive Equatorial Engine: governs declination parallels and
contra-parallels, and owns the shared apparent-declination primitive that
equatorial predictive work reads.

Out-of-bounds excursions are solved by ``moira.out_of_bounds``, which reads
the ``_declination`` primitive defined here so that parallels and bounds
never disagree about a body's declination.
"""

from __future__ import annotations

from dataclasses import dataclass

from .spk_reader import SpkReader, get_reader
from .transits import _auto_step, _require_non_empty_body, _validate_transit_range, _validate_search_motion, _require_positive, TransitComputationPolicy, _validate_policy
from .planets import planet_at
from .small_body_identity import resolve_small_body_identity
from .stars import star_at
from ._ephemeris_time import _ut1_to_ephemeris_tt
from .julian import tt_to_tdb
from .constants import Body
from .planets import _npe_body_route_segment_specs
try:
    from . import moira_native as mn
except ImportError:
    mn = None

__all__ = ["EquatorialTransitEvent", "find_declination_transits"]

#: Points Moira models as longitude-only. ``nodes.NodeData`` carries no
#: ecliptic latitude, so no declination can be formed for them, and they are
#: refused by name rather than routed into a position API that would either
#: raise an opaque KeyError or silently answer from a different object.
_LONGITUDE_ONLY_POINTS: frozenset[str] = frozenset(
    {Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH, Body.TRUE_LILITH}
)

@dataclass(slots=True)
class EquatorialTransitEvent:
    """An exact declination parallel or contra-parallel hit."""
    body: str
    target: str | float
    is_contra_parallel: bool
    jd_exact: float
    declination: float
    search_motion: str = "forward"

def _declination(spec: str | float, jd: float, reader: SpkReader) -> float:
    """Resolves the equatorial declination of a body or a static float.

    Resolution order is planets and points, then small bodies, then stars.
    Small bodies route through ``planets.planet_at``, which is the engine's
    unified front door: it admits asteroids and comets alike, including the
    family-qualified ``asteroid:Name`` and ``comet:Name`` forms, and delegates
    to the same asteroid and comet pipelines those surfaces own. Routing here
    rather than calling ``asteroid_at`` directly is what lets comets form
    declination aspects and go out of bounds at all; the asteroid results are
    bit-identical either way.

    An ambiguous unqualified small-body name raises
    ``AmbiguousSmallBodyNameError`` from the identity registry rather than
    silently preferring one family.
    """
    if isinstance(spec, (int, float)):
        return float(spec)

    name = str(spec).strip()
    lon = lat = 0.0
    jd_tt = _ut1_to_ephemeris_tt(jd, reader)
    if name in Body.ALL_PLANETS:
        p = planet_at(name, jd, reader=reader)
        lon, lat = p.longitude, p.latitude
    elif name in _LONGITUDE_ONLY_POINTS:
        raise ValueError(
            f"Equatorial declination is undefined for {name}: Moira models the "
            "lunar nodes and apogees as longitude-only points (NodeData carries "
            "no ecliptic latitude), so they have no declination product. Note "
            "that a node lies on the ecliptic by construction, so its "
            "declination magnitude could never exceed the obliquity in any "
            "case."
        )
    elif resolve_small_body_identity(name) is not None:
        b = planet_at(name, jd, reader=reader)
        lon, lat = b.longitude, b.latitude
    else:
        try:
            s = star_at(name, jd_tt, product="apparent", reader=reader)
            lon, lat = s.longitude, s.latitude
        except Exception as exc:
            raise ValueError(f"Equatorial target specification could not be resolved: {name}") from exc

    from .coordinates import ecliptic_to_equatorial
    from .obliquity import true_obliquity
    eps = true_obliquity(jd_tt)
    ra, dec = ecliptic_to_equatorial(lon, lat, eps)
    return dec

def _find_declination_crossing(
    body: str,
    target: str | float,
    is_contra: bool,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,
) -> float:
    """Bisect to find when body declination equals target declination (or -target for contra)."""
    def _diff(jd_val: float) -> float:
        b_dec = _declination(body, jd_val, reader)
        t_dec = _declination(target, jd_val, reader)
        return b_dec - (-t_dec if is_contra else t_dec)

    sign_lo = _diff(jd_lo)
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2.0
        if jd_hi - jd_lo < tol_days:
            break
        sign_mid = _diff(jd_mid)
        if sign_lo * sign_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            sign_lo = sign_mid
    return (jd_lo + jd_hi) / 2.0

def _get_native_evaluator(body: str, specs: dict, path: str) -> object | None:
    """Construct one TT-facing evaluator for a body's raw TDB route."""
    if mn is None or body not in specs:
        return None
    route = specs[body]
    evals = [mn.load_spk_segment_evaluator(path, s[0], s[1], True, s[2]) for s in route]
    if len(evals) == 1:
        raw = evals[0]
    elif len(evals) == 2:
        raw = mn.SumEvaluator(evals[0], evals[1])
    else:
        return None
    return mn.TtToTdbEvaluator(raw)

def _find_candidate_declination_windows_native(
    body: str,
    target: str,
    is_contra: bool,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> list[tuple[float, float]]:
    """Use native batch processing to find windows where a declination hit might occur."""
    if isinstance(reader, SpkReader):
        planetary_reader = reader
    else:
        resolver = getattr(reader, "_primary_planetary_reader", None)
        planetary_reader = resolver() if callable(resolver) else None
    if not isinstance(planetary_reader, SpkReader):
        return None
    
    jd_tt_start = _ut1_to_ephemeris_tt(jd_start, reader)
    epoch_tdb_start = tt_to_tdb(jd_tt_start)
    specs = _npe_body_route_segment_specs(planetary_reader, epoch_tdb_start)
    if not specs: return None
    
    path = str(planetary_reader.path)
    e_body = _get_native_evaluator(body, specs, path)
    e_target = _get_native_evaluator(target, specs, path) if isinstance(target, str) and target in specs else None
    e_earth = _get_native_evaluator('Earth', specs, path)
    if not e_body or not e_earth: return None
    
    jds = []
    curr = jd_start
    while curr <= jd_end:
        jds.append(_ut1_to_ephemeris_tt(curr, reader)); curr += step_days
    if not jds: return []
    
    b_decs = mn.declination_batch(e_body, e_earth, jds)
    if e_target:
        t_decs = mn.declination_batch(e_target, e_earth, jds)
    else:
        # Static target declination
        t_dec_static = float(target)
        t_decs = [t_dec_static] * len(jds)
        
    windows = []
    for i in range(len(jds) - 1):
        d1 = b_decs[i] - (-t_decs[i] if is_contra else t_decs[i])
        d2 = b_decs[i+1] - (-t_decs[i+1] if is_contra else t_decs[i+1])
        if d1 * d2 <= 0:
            windows.append((jd_start + i * step_days, jd_start + (i+1) * step_days))
    return windows

def find_declination_transits(
    body: str,
    target: str | float,
    jd_start: float,
    jd_end: float,
    is_contra_parallel: bool = False,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
    search_motion: str = "forward",
) -> list[EquatorialTransitEvent]:
    """Find all declination parallel (or contra-parallel) transits."""
    _require_non_empty_body(body)
    _validate_transit_range(jd_start, jd_end)
    _validate_search_motion(search_motion)
    if step_days is not None:
        _require_positive(step_days, "step_days")
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    if step_days is None:
        step_days = policy.transit.step_days_override or _auto_step(body)

    # --- HYBRID NATIVE SCAN ---
    if body in Body.ALL_PLANETS and (isinstance(target, (int, float)) or target in Body.ALL_PLANETS):
        windows = _find_candidate_declination_windows_native(body, target, is_contra_parallel, jd_start, jd_end, 1.0, reader)
        if windows:
            events = []
            ordered_windows = windows if search_motion == "forward" else list(reversed(windows))
            for jd_lo, jd_hi in ordered_windows:
                jd_exact = _find_declination_crossing(body, target, is_contra_parallel, max(jd_start, jd_lo-0.1), min(jd_end, jd_hi+0.1), reader, policy.transit.solver_tolerance_days)
                exact_dec = _declination(body, jd_exact, reader)
                events.append(EquatorialTransitEvent(body, target, is_contra_parallel, jd_exact, exact_dec, search_motion))
            return events
        return []

    # --- FALLBACK LOOP ---
    events: list[EquatorialTransitEvent] = []
    jd = jd_start if search_motion == "forward" else jd_end
    
    def _diff(jd_val: float) -> float:
        b_dec = _declination(body, jd_val, reader)
        t_dec = _declination(target, jd_val, reader)
        return b_dec - (-t_dec if is_contra_parallel else t_dec)

    diff_prev = _diff(jd)

    while (jd < jd_end) if search_motion == "forward" else (jd > jd_start):
        jd_next = (
            min(jd + step_days, jd_end)
            if search_motion == "forward"
            else max(jd - step_days, jd_start)
        )
        diff_next = _diff(jd_next)

        if diff_prev * diff_next < 0:
            jd_exact = _find_declination_crossing(body, target, is_contra_parallel, jd, jd_next, reader, policy.transit.solver_tolerance_days)
            exact_dec = _declination(body, jd_exact, reader)
            events.append(EquatorialTransitEvent(
                body=body,
                target=target,
                is_contra_parallel=is_contra_parallel,
                jd_exact=jd_exact,
                declination=exact_dec,
                search_motion=search_motion,
            ))

        jd = jd_next
        diff_prev = diff_next

    return events
