"""Reader-bound birth avasthas and previous-sunrise Sayanadi ghati.

Reuses daily Panchanga civil/event ownership, rise_set's altitude signal,
the admitted Gochar epoch/ayanamsa composition, house geometry and true nodes.
No new astronomical substrate or external runtime dependency is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import math

from .avasthas import (
    AvasthaChartResult, AvasthaPolicy, SayanadiContext, SayanadiGhati,
    SayanadiName, SayanadiPolicy, _sayanadi_number, evaluate_avasthas,
)
from .daily_panchanga import (
    PanchangaMoment, PanchangaSunriseDefinition, _moment, _resolve_timezone, _solar_date,
)
from .gochara_dated import GocharaDatePolicy, GocharaEpoch, GocharaResourceError, _epoch
from .houses import _asc_from_armc
from .julian import _local_sidereal_time_at_tt, jd_from_datetime, utc_to_ut1
from .nodes import true_node
from .obliquity import mean_obliquity, nutation
from .rise_set import _altitude
from .spk_reader import KernelReader, MissingKernelError, OutOfRangeError, get_reader, use_reader_override
from ._ephemeris_time import _EphemerisTimeBasisError

__all__ = [
    "SayanadiBirthPolicy", "SayanadiSunriseBracket", "AvasthaBirthResult",
    "SayanadiResourceError", "SayanadiCoverageError", "avasthas_for_datetime",
]


class SayanadiResourceError(RuntimeError):
    """Required serving-reader, clock or ayanamsa resource is unavailable."""


class SayanadiCoverageError(ValueError):
    """Birth or adjacent solar date is outside the serving kernel coverage."""


@dataclass(frozen=True, slots=True)
class SayanadiBirthPolicy:
    ayanamsa_system: str = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: float = 0.1
    evaluate_nodes: bool = False
    lajjitadi_nodes: bool = False
    sayanadi: SayanadiPolicy = field(default_factory=SayanadiPolicy)
    node_mode: str = field(init=False, default="true_geometric_of_date")
    longitude_frame: str = field(init=False, default="apparent_geocentric_true_ecliptic_of_date")
    ayanamsa_mode: str = field(init=False, default="true")
    horizon_model: str = field(init=False, default="level_horizon_zero_elevation_no_terrain")
    clock_basis: str = field(init=False, default="elapsed_UT1_from_previous_local_sunrise")
    maximum_civil_dates: int = field(init=False, default=3)

    def __post_init__(self) -> None:
        GocharaDatePolicy(ayanamsa_system=self.ayanamsa_system)
        if not isinstance(self.sunrise_definition, PanchangaSunriseDefinition):
            raise TypeError("sunrise_definition must be PanchangaSunriseDefinition")
        tolerance = _sayanadi_number("solver_tolerance_seconds", self.solver_tolerance_seconds)
        if not 0.01 <= tolerance <= 1:
            raise ValueError("solver_tolerance_seconds must be in [0.01, 1]")
        if type(self.evaluate_nodes) is not bool or type(self.lajjitadi_nodes) is not bool:
            raise TypeError("node controls must be bool")
        if not isinstance(self.sayanadi, SayanadiPolicy):
            raise TypeError("sayanadi must be SayanadiPolicy")


@dataclass(frozen=True, slots=True)
class SayanadiSunriseBracket:
    moment: PanchangaMoment
    lower_jd_ut1: float
    upper_jd_ut1: float

    def __post_init__(self) -> None:
        low = _sayanadi_number("lower_jd_ut1", self.lower_jd_ut1)
        high = _sayanadi_number("upper_jd_ut1", self.upper_jd_ut1)
        if not low <= self.moment.jd_ut1 <= high:
            raise ValueError("sunrise moment must be inside its root bracket")

    @property
    def bracket_width_seconds(self) -> float:
        return (self.upper_jd_ut1 - self.lower_jd_ut1) * 86400


@dataclass(frozen=True, slots=True)
class AvasthaBirthResult:
    status: str
    unavailable_reasons: tuple[str, ...]
    birth: datetime
    birth_jd_ut1: float
    latitude: float
    longitude: float
    timezone: str
    name: SayanadiName
    policy: SayanadiBirthPolicy
    avastha_policy: AvasthaPolicy
    reader_binding: str
    sunrise: SayanadiSunriseBracket | None = None
    next_sunrise: SayanadiSunriseBracket | None = None
    elapsed_seconds_lower: float | None = None
    elapsed_seconds_upper: float | None = None
    ghati_candidates: tuple[int, ...] = ()
    epoch: GocharaEpoch | None = None
    lagna_tropical: float | None = None
    lagna_sidereal: float | None = None
    node_longitudes: dict[str, float] = field(default_factory=dict)
    chart: AvasthaChartResult | None = None

    def __post_init__(self) -> None:
        if self.status == "unavailable":
            if not self.unavailable_reasons or self.chart is not None or self.epoch is not None:
                raise ValueError("unavailable birth result needs reasons and no computed chart")
        elif self.status == "evaluated":
            if (self.unavailable_reasons or self.chart is None or self.epoch is None
                    or self.sunrise is None or self.next_sunrise is None
                    or len(self.ghati_candidates) != 1 or self.chart.sayanadi_context is None
                    or self.chart.sayanadi_context.ghati.ordinal != self.ghati_candidates[0]):
                raise ValueError("evaluated birth result requires complete clock/chart evidence")
        else:
            raise ValueError("unknown birth evaluation status")


def _refine_sunrise(estimate, zone, lat, lon, policy):
    """Expose a root bracket over the SAME admitted altitude signal.

    Daily Panchanga supplies event discovery. A bounded +/-60-second local
    refinement makes ghati boundary uncertainty inspectable. This bracket
    bounds numerical root location, not observational/model sunrise error.
    """
    def signal(jd):
        return _altitude(jd, lat, lon, "Sun", 1013.25, 10.0) - policy.sunrise_definition.altitude_degrees

    width = 1.0
    while width <= 60:
        low, high = estimate - width / 86400, estimate + width / 86400
        left, right = signal(low), signal(high)
        if left <= 0 <= right:
            break
        width *= 2
    else:
        return None
    for _ in range(64):
        if left == 0:
            high = low
            break
        if right == 0:
            low = high
            break
        if (high - low) * 86400 <= policy.solver_tolerance_seconds:
            break
        middle = (low + high) / 2
        if middle == low or middle == high:
            break
        value = signal(middle)
        if value == 0:
            low = high = middle
            break
        if value < 0:
            low, left = middle, value
        else:
            high, right = middle, value
    return SayanadiSunriseBracket(_moment((low + high) / 2, zone), low, high)


def _lagna(epoch, latitude, longitude):
    dpsi, deps = nutation(epoch.jd_tt)
    mean_eps = mean_obliquity(epoch.jd_tt)
    eps = mean_eps + deps
    armc = _local_sidereal_time_at_tt(epoch.jd_ut1, epoch.jd_tt, longitude, dpsi, mean_eps)
    theta, epsilon, phi = map(math.radians, (armc, eps, latitude))
    x = math.sin(theta) * math.cos(epsilon) + math.tan(phi) * math.sin(epsilon)
    if math.hypot(x, -math.cos(theta)) < 1e-12:
        raise ValueError("birth horizon/ecliptic does not define a unique Lagna")
    tropical = _asc_from_armc(armc, eps, latitude)
    return tropical, (tropical - epoch.ayanamsa_degrees) % 360


def avasthas_for_datetime(birth: datetime, latitude: float, longitude: float, *,
                         name: SayanadiName, timezone_name: str | None = None,
                         policy: SayanadiBirthPolicy | None = None,
                         avastha_policy: AvasthaPolicy | None = None,
                         reader: KernelReader | None = None) -> AvasthaBirthResult:
    """Birth chart and ghati derived from the last local sunrise.

    The previous/current/next local civil dates are the finite admitted search
    scope. Polar/absent or ambiguous roots remain unavailable. No civil-time,
    location, clock or resource fallback; borrowed readers are never closed.
    """
    if not isinstance(birth, datetime) or birth.tzinfo is None or birth.utcoffset() is None:
        raise ValueError("birth must be a timezone-aware civil datetime")
    if not 2 <= birth.year <= 9998:
        raise ValueError("birth year must allow adjacent civil dates [2, 9998]")
    roundtrip = birth.astimezone(timezone.utc).astimezone(birth.tzinfo)
    if roundtrip.replace(tzinfo=None) != birth.replace(tzinfo=None) or roundtrip.fold != birth.fold:
        raise ValueError("birth is a nonexistent or inconsistent local civil instant")
    if not isinstance(name, SayanadiName):
        raise TypeError("name must be SayanadiName")
    active = SayanadiBirthPolicy() if policy is None else policy
    ordinary = AvasthaPolicy() if avastha_policy is None else avastha_policy
    if not isinstance(active, SayanadiBirthPolicy) or not isinstance(ordinary, AvasthaPolicy):
        raise TypeError("birth and avastha policies must be typed")
    if ordinary.vriddha_fraction is not None:
        fraction = _sayanadi_number("vriddha_fraction", ordinary.vriddha_fraction)
        if not 0 <= fraction <= 1:
            raise ValueError("vriddha_fraction must be in [0, 1]")
    lat, lon = _sayanadi_number("latitude", latitude), _sayanadi_number("longitude", longitude)
    if not -90 < lat < 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be in (-90, 90), longitude in [-180, 180]")
    zone = birth.tzinfo if timezone_name is None else _resolve_timezone(timezone_name)
    local_date = birth.astimezone(zone).date()
    jd = utc_to_ut1(jd_from_datetime(birth))
    common = dict(birth=birth, birth_jd_ut1=jd, latitude=lat, longitude=lon,
                  timezone=timezone_name if timezone_name is not None else str(zone),
                  name=name, policy=active, avastha_policy=ordinary,
                  reader_binding="discovered_reader" if reader is None else "caller_owned_reader")

    def unavailable(reason, **evidence):
        return AvasthaBirthResult("unavailable", (reason,), **common, **evidence)

    try:
        bound_reader = get_reader() if reader is None else reader
        with use_reader_override(bound_reader):
            roots = []
            for offset in (-1, 0, 1):
                day = _solar_date(local_date + timedelta(days=offset), zone, lat, lon,
                                  active.sunrise_definition.altitude_degrees)
                if len(day.sunrises) > 1:
                    return unavailable("multiple_sunrises_in_local_civil_date")
                for event in day.sunrises:
                    refined = _refine_sunrise(event.jd_ut1, zone, lat, lon, active)
                    if refined is None:
                        return unavailable("sunrise_root_bracket_unresolved")
                    roots.append(refined)
            if any(root.lower_jd_ut1 <= jd < root.upper_jd_ut1 for root in roots):
                return unavailable("sunrise_ownership_uncertain")
            before = [root for root in roots if root.upper_jd_ut1 <= jd]
            after = [root for root in roots if root.lower_jd_ut1 > jd]
            if not before or not after:
                return unavailable("previous_or_next_sunrise_absent_in_three_civil_dates")
            previous, following = max(before, key=lambda r: r.moment.jd_ut1), min(after, key=lambda r: r.moment.jd_ut1)
            x = Fraction.from_float(jd)
            low = (x - Fraction.from_float(previous.upper_jd_ut1)) * 86400
            high = (x - Fraction.from_float(previous.lower_jd_ut1)) * 86400
            candidates = tuple(sorted({max(1, math.ceil(low / 1440)), max(1, math.ceil(high / 1440))}))
            evidence = dict(sunrise=previous, next_sunrise=following,
                            elapsed_seconds_lower=float(low), elapsed_seconds_upper=float(high),
                            ghati_candidates=candidates)
            if len(candidates) != 1:
                return unavailable("ghati_ordinal_uncertain_inside_sunrise_bracket", **evidence)
            elapsed = float((x - Fraction.from_float(previous.moment.jd_ut1)) * 86400)
            context = SayanadiContext(SayanadiGhati(candidates[0], "sunrise_derived_ut1", elapsed),
                                      name, active.sayanadi, active.evaluate_nodes)
            epoch = _epoch(jd, bound_reader, GocharaDatePolicy(ayanamsa_system=active.ayanamsa_system))
            tropical, sidereal = _lagna(epoch, lat, lon)
            nodes = {}
            if active.evaluate_nodes or active.lajjitadi_nodes:
                rahu = (true_node(jd, reader=bound_reader, jd_tt=epoch.jd_tt).longitude - epoch.ayanamsa_degrees) % 360
                nodes = {"Rahu": rahu, "Ketu": (rahu + 180) % 360}
            # The node context used by Lajjitadi is independently selected.
            inputs = {p.planet: p.position.sidereal_longitude for p in epoch.positions}
            chart = evaluate_avasthas(inputs, sidereal, ordinary,
                                      node_longitudes=nodes if active.lajjitadi_nodes else None,
                                      sayanadi_context=SayanadiContext(context.ghati, name, active.sayanadi))
            if active.evaluate_nodes:
                from .avasthas import sayanadi_avastha
                from dataclasses import replace
                node_results = {p: sayanadi_avastha(p, inputs | nodes, sidereal, context=context)
                                for p in ("Rahu", "Ketu")}
                # Context identity is shared by every canonical result.
                planets = {key: replace(pa, sayanadi=sayanadi_avastha(key, inputs, sidereal, context=context))
                           for key, pa in chart.planets.items()}
                chart = AvasthaChartResult(ordinary, planets, "evaluated", context, node_results)
            return AvasthaBirthResult("evaluated", (), **common, **evidence, epoch=epoch,
                                      lagna_tropical=tropical, lagna_sidereal=sidereal,
                                      node_longitudes=nodes, chart=chart)
    except OutOfRangeError as exc:
        raise SayanadiCoverageError("birth or adjacent solar date is outside serving kernel coverage") from exc
    except (MissingKernelError, GocharaResourceError, _EphemerisTimeBasisError, LookupError, FileNotFoundError) as exc:
        raise SayanadiResourceError("required Sayanadi reader, clock identity or anchor resource is unavailable") from exc
