"""Source-qualified symbolic constructions and prescribed hypothetical orbits.

These products are opt-in conventions, not physical-body ephemerides. Missing
source choices are required inputs, retained in immutable receipts. Angles of
a prescribed ellipse are propagated by their declared rates, never silently
replaced by a semimajor-axis-derived Kepler rate. Geometry is evaluated from
the ellipse and rotated through Moira's admitted orbital frame matrices.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._orbital_frames import LONG_TERM_FRAME_INTERVAL_TT, orbital_frame_transform
from .constants import KM_PER_AU
from .derived_points import _finite_real, DerivedPointDefinition
from .julian import calendar_from_jd, julian_day, ut_to_tt
from .orbits import (
    OrbitalCenter, OrbitalFrame, OrbitalFrameConstruction, OrbitShape,
    OsculatingElements, osculating_elements,
)
from .spk_reader import KernelReader

__all__ = [
    "ConventionClock", "ProserpinaRule", "LongitudeConvention", "ArtaFourPoints",
    "ArtaOsculatingSet", "HistoricalRealization", "PrescribedHypotheticalOrbit",
    "HypotheticalGeometry", "hypothetical_catalog", "arta_four_points",
    "arta_osculating_set_at", "selena_seven_year_at", "abramov_proserpina_at",
    "koch_waldemath_orbit", "weston_stahl_vulcan_orbit", "harrington_1988_orbit",
    "adams_1846_orbit", "leverrier_1846_orbit", "hypothetical_orbit_at",
    "PlanetNineScenario", "fienga_2016_planet_nine_scenario",
]

_ARTA_SOURCE = "https://astrologer.ru/book/light_moon/index.html.en"
_SELENA_SOURCE = "https://djvu.online/file/lBJKQiKf9n4Gd"
_ABRAMOV_SOURCE = "https://www.geocities.ws/rognavaldre/proserpina.html"
_KOCH_SOURCE = "https://groups.io/g/swisseph/messages?after=1149253069000000000&index=979&page=588&subsort=1"
_WESTON_SOURCE = "https://www.innergarden.org/spagyria/vulcan/vulcan.html"
_HARRINGTON_SOURCE = "https://articles.adsabs.harvard.edu/pdf/1988AJ.....96.1476H"
_ADAMS_SOURCE = "https://archive.org/download/anexplanationob00adamgoog/anexplanationob00adamgoog.pdf"
_LEVERRIER_SOURCE = "https://www.e-rara.ch/download/pdf/29059152.pdf"
_FIENGA_SOURCE = "https://arxiv.org/pdf/1602.06116v3"


class ConventionClock(str, Enum):
    """Explicit clock used for the continuous realization of source dates."""

    TT = "TT"
    UT1 = "UT1"


class ProserpinaRule(str, Enum):
    """Distinct realizations of Abramov's rounded annual and daily increments."""

    CALENDAR = "abramov_calendar"
    JULIAN_YEAR = "abramov_julian_year"


@dataclass(frozen=True, slots=True)
class LongitudeConvention:
    """Longitude-only construction with explicit anchor, clock and frame policy."""

    model: str
    longitude: float
    epoch_jd: float
    timescale: ConventionClock
    frame: str
    center: str
    symbol: str
    source_url: str
    parameters: tuple[tuple[str, float], ...]
    limitation: str


@dataclass(frozen=True, slots=True)
class ArtaFourPoints:
    """Unlabelled, sorted fourfold set; no branch is privileged across epochs."""

    longitudes: tuple[float, float, float, float]
    lunar_node: float
    lunar_apogee: float
    solar_apogee: float
    input_model: str
    frame: str
    symbol: str = "\u2bdf"
    model: str = "arta_timashev_four_points"
    source_url: str = _ARTA_SOURCE


@dataclass(frozen=True, slots=True)
class ArtaOsculatingSet:
    """Timashev construction with the exact two admitted geometric input orbits."""

    points: ArtaFourPoints
    lunar_elements: OsculatingElements
    earth_elements: OsculatingElements


@dataclass(frozen=True, slots=True)
class HistoricalRealization:
    """Caller-selected frame, clock, date hour and year length missing in sources."""

    source_equinox_jd_tt: float
    timescale: ConventionClock
    epoch_hour: float
    year_days: float


@dataclass(frozen=True, slots=True)
class PrescribedHypotheticalOrbit:
    """Named ellipse and independently prescribed angular rates, with provenance."""

    model: str
    center: OrbitalCenter
    epoch_jd: float
    timescale: ConventionClock
    source_equinox_jd_tt: float
    semi_major_axis_au: float
    eccentricity: float
    inclination_deg: float
    mean_anomaly_deg: float
    mean_anomaly_rate_deg_per_day: float
    perihelion_longitude_deg: float
    perihelion_rate_deg_per_day: float
    ascending_node_deg: float
    node_rate_deg_per_day: float
    source_url: str
    source_location: str
    realization: str
    parameters: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class HypotheticalGeometry:
    """Instantaneous central-body-relative vector, with the full prescribed orbit."""

    vector_au: tuple[float, float, float]
    longitude: float | None
    latitude: float
    distance_au: float
    epoch_jd: float
    epoch_tt: float
    frame: OrbitalFrame
    source_orbit: PrescribedHypotheticalOrbit
    source_frame: OrbitalFrameConstruction
    target_frame: OrbitalFrameConstruction
    reduction: str = "geometric_no_light_time_no_aberration"


@dataclass(frozen=True, slots=True)
class PlanetNineScenario:
    """One selected location on Fienga 2016's trial ellipse, with no invented epoch."""

    true_anomaly_deg: float
    vector_au: tuple[float, float, float]
    distance_au: float
    source_equinox_jd_tt: float
    model: str = "planet_nine_fienga_2016_scenario"
    frame: str = "caller_realized_source_ecliptic"
    center: str = "SUN"
    source_url: str = _FIENGA_SOURCE
    limitation: str = "Selected trial location only; no dated ephemeris, detection, or present-position claim."


def hypothetical_catalog() -> tuple[DerivedPointDefinition, ...]:
    """Discover named constructions and their required policy inputs."""
    rows = (
        ("arta_timashev_four_points", "Arta four-point set", "symbolic_set", False,
         "All four equivalent branches; supplied input model and common frame required.", _ARTA_SOURCE),
        ("arta_timashev_osculating_set", "Arta osculating four-point set", "symbolic_set", True,
         "Geometric Moon/Earth osculating inputs; explicit output frame required.", _ARTA_SOURCE),
        ("selena_seven_year_anchored", "Selena seven-year anchored convention", "symbolic_longitude", False,
         "Uniform seven-year motion; anchor, year length, clock and frame required.", _SELENA_SOURCE),
        ("abramov_calendar", "Proserpina Abramov calendar approximation", "symbolic_longitude", False,
         "Literal rounded calendar-year/day rule; frame and clock realization required.", _ABRAMOV_SOURCE),
        ("abramov_julian_year", "Proserpina Abramov continuous annual approximation", "symbolic_longitude", False,
         "Annual increment over Julian years; frame and clock realization required.", _ABRAMOV_SOURCE),
        ("waldemath_koch_quoted_2006", "Waldemath Koch quoted-elements realization", "prescribed_orbit", False,
         "Frame and Berlin-noon clock offset required; not a Swiss ephemeris replica.", _KOCH_SOURCE),
        ("weston_stahl_1968", "Vulcan Weston/Stahl 1968 realization", "prescribed_orbit", False,
         "Prescribed mean motion and nodal regression; frame and year length required.", _WESTON_SOURCE),
        ("harrington_1988", "Harrington 1988 nominal Planet X", "historical_prediction", False,
         "Nominal example; frame, clock, date hour and year length required.", _HARRINGTON_SOURCE),
        ("adams_1846_second_hypothesis", "Adams 1846 second Neptune hypothesis", "historical_prediction", False,
         "Historical realization and Uranus distance/year scales required.", _ADAMS_SOURCE),
        ("leverrier_1846_gould_1850", "Le Verrier 1846, Gould 1850 transcription", "historical_prediction", False,
         "Named contemporary transcription; historical realization required.", _LEVERRIER_SOURCE),
        ("planet_nine_fienga_2016_scenario", "Planet Nine Fienga 2016 scenario", "selected_scenario", False,
         "True anomaly and source equinox required; no canonical epoch or current position.", _FIENGA_SOURCE),
    )
    return tuple(DerivedPointDefinition(key, name, kind, description, kernel, source)
                 for key, name, kind, kernel, description, source in rows)


def _label(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty explicit label")
    return value.strip()


def _year_days(value: float) -> float:
    days = _finite_real(value, "year_days")
    if not 365.0 <= days <= 366.0:
        raise ValueError("year_days must be an explicit Earth year length in [365, 366]")
    return days


def _epoch(value: float, name: str) -> float:
    result = _finite_real(value, name)
    if math.ulp(result) >= 1.0:
        raise ValueError(f"{name} must retain sub-day Julian-date precision")
    return result


def arta_four_points(
    lunar_node: float, lunar_apogee: float, solar_apogee: float, *,
    input_model: str, frame: str,
) -> ArtaFourPoints:
    """Evaluate Timashev's formula modulo 90 degrees, returning the entire set.

    Reducing an input by 360 changes the formula by a multiple of 90, so this
    set is invariant under any input angle lift. Sorted array indices are not
    persistent branch labels. No velocity, distance or physical body is implied.
    """
    node, lunar, solar = (_finite_real(value, name) % 360.0 for value, name in (
        (lunar_node, "lunar_node"), (lunar_apogee, "lunar_apogee"),
        (solar_apogee, "solar_apogee"),
    ))
    phase = (node + 7.0 * (lunar - solar + 180.0) / 4.0) % 90.0
    return ArtaFourPoints(
        tuple(phase + 90.0*k for k in range(4)), node, lunar, solar,
        _label(input_model, "input_model"), _label(frame, "frame"),
    )


def arta_osculating_set_at(
    jd_ut: float, *, frame: OrbitalFrame, reader: KernelReader | None = None,
) -> ArtaOsculatingSet:
    """Use strict geometric Moon and Earth orbits, retaining both source receipts.

    Solar geocentric apogee points along Earth's heliocentric PERICENTER:
    reversing the Earth-Sun vector swaps the apsidal directions. This is a
    named modern realization, not certification of Timashev's DE403 tables.
    """
    lunar = osculating_elements("Moon", jd_ut, center=OrbitalCenter.EARTH,
                                frame=frame, reader=reader)
    earth = osculating_elements("Earth", jd_ut, center=OrbitalCenter.SUN,
                                frame=frame, reader=reader)
    if lunar.shape is not OrbitShape.ELLIPTIC or earth.shape is not OrbitShape.ELLIPTIC:
        raise ValueError("Arta apogee inputs require two elliptic orbits")
    if (lunar.frame != earth.frame or lunar.epoch_tt != earth.epoch_tt
            or lunar.epoch_tdb != earth.epoch_tdb):
        raise ValueError("Arta inputs must share the same bound clock and frame")
    node, peri, solar = (lunar.lon_ascending_node_deg,
                        lunar.pericenter_ecliptic_lon_deg, earth.pericenter_ecliptic_lon_deg)
    if node is None or peri is None or solar is None:
        raise ValueError("Arta requires defined lunar node and both apsidal directions")
    return ArtaOsculatingSet(arta_four_points(
        node, (peri+180.0) % 360.0, solar,
        input_model="Moira_strict_osculating_Moon_Earth_geocenter",
        frame=lunar.frame.value,
    ), lunar, earth)


def selena_seven_year_at(
    epoch_jd: float, *, anchor_jd: float, anchor_longitude: float,
    year_days: float, timescale: ConventionClock, frame: str,
) -> LongitudeConvention:
    """Realize the published uniform seven-year doctrine with an explicit anchor.

    No canonical phase or physical radius is inferred from the period. The
    separate seven-years-minus-fifteen-days doctrine is not this construction.
    """
    epoch = _epoch(epoch_jd, "epoch_jd")
    anchor = _epoch(anchor_jd, "anchor_jd")
    phase = _finite_real(anchor_longitude, "anchor_longitude") % 360.0
    year = _year_days(year_days)
    longitude = (phase + math.remainder(epoch-anchor, 7.0*year)*360.0/(7.0*year)) % 360.0
    return LongitudeConvention(
        "selena_seven_year_anchored", longitude, epoch, ConventionClock(timescale),
        _label(frame, "frame"), "symbolic_geocentric", "\u2bdd", _SELENA_SOURCE,
        (("anchor_jd", anchor), ("anchor_longitude", phase), ("year_days", year)),
        "Caller-supplied phase and frame; no physical distance; distinct from lunar perigee.",
    )


def abramov_proserpina_at(
    epoch_jd: float, *, rule: ProserpinaRule, timescale: ConventionClock, frame: str,
) -> LongitudeConvention:
    """Evaluate a named realization of Abramov's approximate heliocentric rule.

    CALENDAR preserves the literal annual+daily formula, including its small
    year-boundary jumps. JULIAN_YEAR uses only the annual increment with a
    365.25-day year. Neither is advertised as an exact orbital ephemeris. The
    source does not define an equinox or time scale; callers must name both.
    """
    epoch = _epoch(epoch_jd, "epoch_jd")
    selected = ProserpinaRule(rule)
    if selected is ProserpinaRule.CALENDAR:
        if not LONG_TERM_FRAME_INTERVAL_TT[0] <= epoch <= LONG_TERM_FRAME_INTERVAL_TT[1]:
            raise ValueError("Calendar realization requires Moira's admitted long-term epoch interval")
        year = calendar_from_jd(epoch)[0]
        day = epoch - julian_day(year, 1, 1)
        years = year - 1900
        longitude = (170.73 + 0.5105*years + 0.0014*day) % 360.0
    else:
        years = (epoch-julian_day(1900, 1, 1))/365.25
        day = 0.0
        longitude = (170.73 + 0.5105*years) % 360.0
    if not math.isfinite(longitude):
        raise ValueError("epoch_jd is outside representable formula arithmetic")
    return LongitudeConvention(
        selected.value, longitude, epoch, ConventionClock(timescale),
        _label(frame, "frame"), "heliocentric", "\u2bd8", _ABRAMOV_SOURCE,
        (("years_since_1900", years), ("day_offset", day)),
        "Rounded source approximation; source frame/clock realized by caller; not asteroid 26 or Avestan 665-year Proserpina.",
    )


def _historical_policy(policy: HistoricalRealization) -> HistoricalRealization:
    equinox = _finite_real(policy.source_equinox_jd_tt, "source_equinox_jd_tt")
    hour = _finite_real(policy.epoch_hour, "epoch_hour")
    if not 0 <= hour < 24:
        raise ValueError("epoch_hour must be in [0, 24)")
    return HistoricalRealization(equinox, ConventionClock(policy.timescale), hour, _year_days(policy.year_days))


def harrington_1988_orbit(policy: HistoricalRealization) -> PrescribedHypotheticalOrbit:
    """Realize the nominal example on p.1478, retaining the printed 1019-year period."""
    p = _historical_policy(policy)
    return PrescribedHypotheticalOrbit(
        "harrington_1988", OrbitalCenter.SUN, julian_day(1789, 8, 6, p.epoch_hour),
        p.timescale, p.source_equinox_jd_tt, 101.2, 0.411, 32.4,
        0.0, 360.0/(1019.0*p.year_days), 208.5+275.4, 0.0, 275.4, 0.0,
        _HARRINGTON_SOURCE, "AJ 96 (1988), p.1478 nominal example",
        "Caller-selected equinox, clock, perihelion date hour and year length; prescribed rounded period.",
        (("year_days", p.year_days), ("epoch_hour", p.epoch_hour)),
    )


def adams_1846_orbit(
    policy: HistoricalRealization, *, uranus_semimajor_axis_au: float,
    uranus_sidereal_period_days: float,
) -> PrescribedHypotheticalOrbit:
    """Realize Adams's second hypothesis, original pp.25-26 (ratio a_U/a=0.515).

    The caller supplies the historical Uranus distance and period scales. Adams's
    two-body hypothesis fixes n/n_U = (a_U/a)**(3/2). Its planar reduction is
    declared explicitly; it is not the modern orbit of Neptune.
    """
    p = _historical_policy(policy)
    a_u = _finite_real(uranus_semimajor_axis_au, "uranus_semimajor_axis_au")
    period_u = _finite_real(uranus_sidereal_period_days, "uranus_sidereal_period_days")
    if a_u <= 0 or period_u <= 0:
        raise ValueError("Uranus distance and period scales must be positive")
    peri = 299.0+11.0/60.0
    return PrescribedHypotheticalOrbit(
        "adams_1846_second_hypothesis", OrbitalCenter.SUN,
        julian_day(1846, 10, 6, p.epoch_hour), p.timescale, p.source_equinox_jd_tt,
        a_u/0.515, 0.120615, 0.0, 323.0+2.0/60.0-peri,
        (360.0/period_u)*0.515**1.5, peri, 0.0, 0.0, 0.0,
        _ADAMS_SOURCE, "1846 original, p.25, section 48, second hypothesis",
        "Planar prediction; caller-selected Uranus scales, frame, clock and date hour.",
        (("uranus_semimajor_axis_au", a_u), ("uranus_sidereal_period_days", period_u),
         ("epoch_hour", p.epoch_hour)),
    )


def leverrier_1846_orbit(policy: HistoricalRealization) -> PrescribedHypotheticalOrbit:
    """Realize the August 1846 prediction as transcribed by Gould (1850), p.21.

    Longitude of perihelion and mean anomaly are retained from the same dated
    table. The 1847 perihelion is the 1800 value plus the table's 47-year
    precession (39m20s), rather than mixing equinoxes within one element set.
    """
    p = _historical_policy(policy)
    peri = 284.0+5.0/60.0+48.0/3600.0 + 39.0/60.0+20.0/3600.0
    return PrescribedHypotheticalOrbit(
        "leverrier_1846_gould_1850", OrbitalCenter.SUN,
        julian_day(1847, 1, 1, p.epoch_hour), p.timescale, p.source_equinox_jd_tt,
        36.1539, 0.10761, 0.0, 34.0+1.0/60.0+56.0/3600.0,
        360.0/(217.387*p.year_days), peri, 0.0, 0.0, 0.0,
        _LEVERRIER_SOURCE, "Gould 1850 Report on the history of the discovery of Neptune, p.21",
        "Planar contemporary transcription, not a modern Neptune ephemeris; caller-selected historical realization.",
        (("year_days", p.year_days), ("epoch_hour", p.epoch_hour)),
    )


def koch_waldemath_orbit(
    *, source_equinox_jd_tt: float, berlin_local_minus_ut1_hours: float,
) -> PrescribedHypotheticalOrbit:
    """Reconstruct Koch's 2006 QUOTED elements, retaining all four source periods.

    Source longitude is treated as MEAN longitude. The Berlin-noon offset is
    explicit (0 for Greenwich clock, about 0.8933 h for Berlin local mean time).
    Apsidal and nodal rates follow from sidereal minus anomalistic/draconitic
    rates. This source-derived realization is not a claim to reproduce Swiss.
    """
    offset = _finite_real(berlin_local_minus_ut1_hours, "berlin_local_minus_ut1_hours")
    if not -24.0 < offset < 24.0:
        raise ValueError("Berlin clock offset must be between -24 and 24 hours")
    equinox = _finite_real(source_equinox_jd_tt, "source_equinox_jd_tt")
    epoch = julian_day(1898, 1, 1, 12.0)-offset/24.0
    perigee = julian_day(1898, 4, 8, 12.0)
    node_epoch = julian_day(1898, 2, 3, 18.0+27.0/60.0)
    sidereal_rate = 360.0/119.227434
    anomaly_rate = 360.0/120.5915
    node_rate = sidereal_rate-360.0/118.003952
    m0 = anomaly_rate*(epoch-perigee)
    return PrescribedHypotheticalOrbit(
        "waldemath_koch_quoted_2006", OrbitalCenter.EARTH, epoch, ConventionClock.UT1,
        equinox, 1026000.0/KM_PER_AU, 0.1587, 2.5, m0, anomaly_rate,
        214.73-m0, sidereal_rate-anomaly_rate,
        315.0+13.0/60.0+180.0+node_rate*(epoch-node_epoch), node_rate,
        _KOCH_SOURCE, "Dieter Koch, Re: Waldemath Lilith positions, May 2006, quoted Table 40",
        "Mean-longitude reading; sidereal-period priority over rounded daily rate; explicit Berlin clock and source equinox; UT1 prescribed motion; no perturbations.",
        (("berlin_local_minus_ut1_hours", offset), ("sidereal_period_days", 119.227434),
         ("anomalistic_period_days", 120.5915), ("draconitic_period_days", 118.003952),
         ("quoted_synodic_period_days", 177.005093), ("quoted_daily_mean_motion", 3.0194393012)),
    )


def weston_stahl_vulcan_orbit(
    *, source_equinox_jd_tt: float, year_days: float,
) -> PrescribedHypotheticalOrbit:
    """Select Stahl's 1968 revision explicitly, rather than mixing Weston editions.

    Jan 0 1900 is realized as Greenwich astronomical noon on Dec 31 1899
    (JD 2415020.0 UT1). The refined daily mean-longitude increment is retained;
    perihelion longitude is fixed at the source's 10 degrees. The descending
    node is anchored June 25 1907 at the chosen noon realization and regresses
    by the printed 18d42m21s per caller-selected year.
    """
    equinox = _finite_real(source_equinox_jd_tt, "source_equinox_jd_tt")
    year = _year_days(year_days)
    epoch = 2415020.0
    node_epoch = julian_day(1907, 6, 25, 12.0)
    node_rate = -(18.0+42.0/60.0+21.0/3600.0)/year
    mean_longitude = 265.0+34.0/60.0+27.0/3600.0
    return PrescribedHypotheticalOrbit(
        "weston_stahl_1968", OrbitalCenter.SUN, epoch, ConventionClock.UT1,
        equinox, 0.13744, 0.019, 7.5, mean_longitude-10.0,
        19.0+22.0/60.0+17.1138/3600.0, 10.0, 0.0,
        92.0+55.0/60.0+180.0+node_rate*(epoch-node_epoch), node_rate,
        _WESTON_SOURCE, "Stahl 1968, Elements p.16 and Revised Tables p.19",
        "Weston/Stahl selected revision; fixed selected equinox; UT1 date realization; prescribed motion, not Keplerian rate from a.",
        (("year_days", year), ("node_anchor_jd_ut1", node_epoch)),
    )


def hypothetical_orbit_at(
    orbit: PrescribedHypotheticalOrbit, epoch_jd: float, *, frame: OrbitalFrame,
) -> HypotheticalGeometry:
    """Evaluate the declared ellipse; return geometric central-focus-relative AU.

    E-e*sin(E)=M has derivative >=1-e>0. Bisection on [-pi,pi] therefore
    supplies a unique, convergent eccentric anomaly for every admitted bound
    ellipse, including high eccentricity. Orbital-plane coordinates are
    a(cos E-e), a sqrt(1-e**2) sin E. The source basis is transformed to ICRF
    by transposing its orthogonal frame matrix, then to the requested frame.
    """
    epoch = _epoch(epoch_jd, "epoch_jd")
    source_epoch = _epoch(orbit.epoch_jd, "orbit.epoch_jd")
    a = _finite_real(orbit.semi_major_axis_au, "semi_major_axis_au")
    e = _finite_real(orbit.eccentricity, "eccentricity")
    if a <= 0 or not 0 <= e < 1:
        raise ValueError("A prescribed ellipse requires a > 0 and 0 <= e < 1")
    angles = tuple(_finite_real(getattr(orbit, key), key) for key in (
        "mean_anomaly_deg", "mean_anomaly_rate_deg_per_day", "perihelion_longitude_deg",
        "perihelion_rate_deg_per_day", "ascending_node_deg", "node_rate_deg_per_day", "inclination_deg",
    ))
    if not 0 <= angles[-1] <= 180:
        raise ValueError("inclination_deg must be in [0, 180]")
    clock = ConventionClock(orbit.timescale)
    OrbitalCenter(orbit.center)
    selected_frame = OrbitalFrame(frame)
    dt = epoch-source_epoch
    m0, nm, peri0, np, node0, nn, inc = angles
    propagated = (m0+nm*dt, peri0+np*dt, node0+nn*dt)
    if not all(map(math.isfinite, propagated)):
        raise ValueError("epoch is outside finite prescribed propagation arithmetic")
    M = math.radians(math.remainder(propagated[0], 360.0))
    left, right = -math.pi, math.pi
    for _ in range(64):
        E = (left+right)/2.0
        if E-e*math.sin(E) < M:
            left = E
        else:
            right = E
    E = (left+right)/2.0
    x, y = a*(math.cos(E)-e), a*math.sqrt((1-e)*(1+e))*math.sin(E)
    node = math.radians(propagated[2] % 360.0)
    arg = math.radians((propagated[1]-propagated[2]) % 360.0)
    inc = math.radians(inc)
    p = (math.cos(node)*math.cos(arg)-math.sin(node)*math.sin(arg)*math.cos(inc),
         math.sin(node)*math.cos(arg)+math.cos(node)*math.sin(arg)*math.cos(inc),
         math.sin(arg)*math.sin(inc))
    q = (-math.cos(node)*math.sin(arg)-math.sin(node)*math.cos(arg)*math.cos(inc),
         -math.sin(node)*math.sin(arg)+math.cos(node)*math.cos(arg)*math.cos(inc),
         math.cos(arg)*math.sin(inc))
    source_vector = tuple(x*p[k]+y*q[k] for k in range(3))
    source = orbital_frame_transform("MEAN_ECLIPTIC_OF_DATE", orbit.source_equinox_jd_tt)
    icrf = tuple(sum(source.matrix[j][k]*source_vector[j] for j in range(3)) for k in range(3))
    epoch_tt = epoch if clock is ConventionClock.TT else ut_to_tt(epoch)
    target = orbital_frame_transform(selected_frame.value, epoch_tt)
    # Identical axes require the identity map, not a numeric round trip through
    # the first-order long-term ICRS-bias approximation (which is not exactly
    # orthogonal). Preserve that algebraic identity, including at a pole.
    if (selected_frame is OrbitalFrame.MEAN_ECLIPTIC_OF_DATE
            and epoch_tt == orbit.source_equinox_jd_tt):
        vector = source_vector
    else:
        vector = tuple(sum(target.matrix[k][j]*icrf[j] for j in range(3)) for k in range(3))
    distance = math.hypot(*vector)
    if distance == 0 or not math.isfinite(distance):
        raise ValueError("Prescribed geometric distance must be finite and positive")
    xy = math.hypot(*vector[:2])
    latitude = math.degrees(math.atan2(vector[2], xy))
    longitude = (math.degrees(math.atan2(vector[1], vector[0])) % 360.0
                 if xy and abs(latitude) != 90.0 else None)
    return HypotheticalGeometry(
        vector, longitude, latitude, distance,
        epoch, epoch_tt, selected_frame, orbit,
        OrbitalFrameConstruction(
            OrbitalFrame.MEAN_ECLIPTIC_OF_DATE, source.routine, source.router_branch,
            source.precession_model, source.obliquity_model, source.nutation_model,
        ),
        OrbitalFrameConstruction(
            selected_frame, target.routine, target.router_branch,
            target.precession_model, target.obliquity_model, target.nutation_model,
        ),
    )


def fienga_2016_planet_nine_scenario(
    true_anomaly_deg: float, *, source_equinox_jd_tt: float,
) -> PlanetNineScenario:
    """Select a point on Table 1's trial ellipse, without inventing a phase epoch.

    Fienga et al. 2016, arXiv v3 p.3: a=700 AU, e=.6, i=30,
    argument of perihelion=150, ascending node=113 degrees. The paper samples
    the entire orbit. Radius is a(1-e²)/(1+e cos nu); the ordinary orbital-plane
    rotation expresses the selected point in the caller-realized source axes.
    """
    anomaly = _finite_real(true_anomaly_deg, "true_anomaly_deg") % 360.0
    equinox = _epoch(source_equinox_jd_tt, "source_equinox_jd_tt")
    nu = math.radians(anomaly)
    radius = 700.0*(1.0-0.6**2)/(1.0+0.6*math.cos(nu))
    angle, node, inc = map(math.radians, (anomaly+150.0, 113.0, 30.0))
    vector = (
        radius*(math.cos(node)*math.cos(angle)-math.sin(node)*math.sin(angle)*math.cos(inc)),
        radius*(math.sin(node)*math.cos(angle)+math.cos(node)*math.sin(angle)*math.cos(inc)),
        radius*math.sin(angle)*math.sin(inc),
    )
    return PlanetNineScenario(anomaly, vector, radius, equinox)
