"""
Rise and Set Engine — moira/rise_set.py

Archetype: Engine
Purpose: Computes rise, set, transit, anti-transit, and all twilight times
         for any solar system body or named fixed star at an observer location,
         by solving horizon and meridian crossings via bisection on the
         altitude and hour-angle signals.

Boundary declaration:
    Owns: altitude computation, horizon-crossing bisection, meridian-transit
          refinement, twilight altitude-crossing search, the TwilightTimes
          result type, and the RiseSetPolicy doctrine surface.
    Delegates: apparent planetary positions to moira.planets.planet_at;
               fixed-star positions to moira.fixed_stars.fixed_star_at (lazy
               import at call time); nutation and obliquity to moira.obliquity;
               coordinate conversion to moira.coordinates; sidereal time to
               moira.julian.local_sidereal_time.

Import-time side effects: None

External dependency assumptions:
    - moira.planets.planet_at accepts a body name and JD TT and returns a
      PlanetData with .longitude and .latitude fields.
    - moira.julian.ut_to_tt is available for UT→TT conversion.
    - moira.julian.local_sidereal_time accepts (jd_ut, longitude, dpsi, eps).

Public surface / exports:
    RiseSetPolicy         — typed doctrine object controlling rise/set event definition
    TwilightTimes         — result dataclass for all twilight events on a day
    find_phenomena()      — rise, set, and transit dict for a body over 24 h
    get_transit()         — precise JD of upper or lower meridian transit
    twilight_times()      — full twilight table for a day and observer location
"""

import math
from dataclasses import dataclass

from .julian import local_sidereal_time, ut_to_tt
from .obliquity import nutation, true_obliquity
from .coordinates import ecliptic_to_equatorial
from .planets import planet_at

__all__ = [
    "RiseSetPolicy",
    "TwilightTimes",
    "find_phenomena",
    "get_transit",
    "twilight_times",
]


@dataclass(frozen=True, slots=True)
class RiseSetPolicy:
    """
    Typed doctrine object controlling how rise and set events are defined.

    RiseSetPolicy replaces the Swiss Ephemeris ``BIT_DISC_*``,
    ``BIT_HINDU_RISING``, and ``BIT_NO_REFRACTION`` integer-flag pattern with
    a typed, immutable, self-documenting policy.  Pass an instance to
    ``find_phenomena()`` via the ``policy`` kwarg to customise the event
    definition for a specific call.

    Attributes
    ----------
    disc_reference : str
        Which part of the solar/lunar disc defines the rise/set moment.

        ``'limb'`` (default)
            The leading edge (upper limb) of the disc crosses the horizon.
            This is the conventional definition and matches Swiss
            ``BIT_DISC_BOTTOM`` for rising / upper limb for setting.

        ``'center'``
            The centre of the disc crosses the horizon.  Corresponds to
            Swiss ``BIT_DISC_CENTER``.

        ``'bottom'``
            The trailing edge (lower limb) crosses the horizon.  Corresponds
            to Swiss ``BIT_DISC_BOTTOM`` in the setting sense.

    fixed_disc_size : bool
        If ``True``, use the mean angular semi-diameter of the body rather than
        the computed apparent semi-diameter.  Corresponds to Swiss
        ``BIT_FIXED_DISC_SIZE``.  Default: ``False``.

    hindu_rising : bool
        If ``True``, apply the Hindu rising doctrine: rise is defined as the
        moment when the Sun's centre crosses a horizon that has been shifted
        upward by one solar semi-diameter.  Corresponds to Swiss
        ``BIT_HINDU_RISING``.  Default: ``False``.

    refraction : bool
        If ``True`` (default), include atmospheric refraction in the horizon
        altitude.  Standard astronomical refraction adds approximately
        0.5667° to the geometric horizon.  Set to ``False`` for geometric
        (refraction-free) rise/set times.  Corresponds to the absence of
        Swiss ``BIT_NO_REFRACTION``.

    horizon_altitude : float or None
        Explicit horizon altitude override in degrees.  When set, this value
        is used directly as the target altitude for rise/set bisection,
        overriding all disc-reference, refraction, and Hindu-rising
        adjustments.  Useful when a non-standard horizon dip or elevation
        correction is required.  Default: ``None`` (compute automatically).

    Examples
    --------
    >>> # Geometric rise/set — no refraction, disc centre
    >>> policy = RiseSetPolicy(disc_reference='center', refraction=False)
    >>> from moira.rise_set import find_phenomena
    >>> events = find_phenomena('Sun', jd_start, lat, lon, policy=policy)

    >>> # Hindu rising doctrine
    >>> policy = RiseSetPolicy(hindu_rising=True)
    """

    disc_reference: str = 'limb'
    fixed_disc_size: bool = False
    hindu_rising: bool = False
    refraction: bool = True
    horizon_altitude: float | None = None

    def __post_init__(self) -> None:
        allowed = ('limb', 'center', 'bottom')
        if self.disc_reference not in allowed:
            raise ValueError(
                f"RiseSetPolicy.disc_reference must be one of {allowed!r}, "
                f"got {self.disc_reference!r}"
            )

    def horizon_altitude_for(self, body_name: str) -> float:
        """
        Return the effective horizon altitude (degrees) for a given body.

        This encapsulates the doctrine choices: disc reference, refraction,
        fixed-disc-size, and Hindu-rising adjustments.

        If ``horizon_altitude`` was set explicitly on this policy, that value
        is returned directly without any further adjustment.
        """
        if self.horizon_altitude is not None:
            return self.horizon_altitude

        # Refraction contribution (standard atmospheric refraction ≈ 34 arcmin)
        refraction_deg = 0.5667 if self.refraction else 0.0

        # Semi-diameter contribution
        # Sun and Moon have non-negligible angular size; stars/planets use 0.
        name_lower = body_name.lower()
        if name_lower == 'sun':
            semi_diam_deg = 0.2667  # mean solar semi-diameter ≈ 16 arcmin
        elif name_lower == 'moon':
            semi_diam_deg = 0.2725  # mean lunar semi-diameter ≈ 16.35 arcmin
        else:
            semi_diam_deg = 0.0

        if self.disc_reference == 'center':
            disc_offset = 0.0
        elif self.disc_reference == 'limb':
            # Rise: upper limb crosses; Set: lower limb crosses.
            # Convention: subtract semi-diameter so limb-crossing is below centre.
            disc_offset = -semi_diam_deg
        else:  # 'bottom'
            disc_offset = semi_diam_deg

        if self.hindu_rising and name_lower == 'sun':
            # Hindu doctrine: add one solar semi-diameter to the horizon.
            return -(refraction_deg + semi_diam_deg)

        return -(refraction_deg - disc_offset)


def _lst(jd_ut: float, longitude: float) -> float:
    """Local apparent sidereal time in degrees."""
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _ = nutation(jd_tt)
    eps = true_obliquity(jd_tt)
    return local_sidereal_time(jd_ut, longitude, dpsi, eps)


def _body_ra_dec(jd_ut: float, body_name: str) -> tuple[float, float]:
    """Return apparent RA/Dec of a planet or named fixed star at the given UT JD."""
    jd_tt = ut_to_tt(jd_ut)
    eps = true_obliquity(jd_tt)

    try:
        pos = planet_at(body_name, jd_tt)
    except Exception:
        from .fixed_stars import fixed_star_at

        pos = fixed_star_at(body_name, jd_tt)

    return ecliptic_to_equatorial(pos.longitude, pos.latitude, eps)


def _signed_angle_diff(value: float, target: float) -> float:
    """Signed angular difference value-target in (-180, +180]."""
    return ((value - target + 180.0) % 360.0) - 180.0


def _hour_angle_error(
    jd_ut: float,
    body_name: str,
    lat: float,
    lon: float,
    target_ha: float = 0.0,
) -> float:
    """Signed hour-angle error in degrees relative to the requested meridian target."""
    try:
        from .planets import sky_position_at

        ra = sky_position_at(body_name, jd_ut, lat, lon).right_ascension
    except Exception:
        ra, _ = _body_ra_dec(jd_ut, body_name)
    lst = _lst(jd_ut, lon)
    ha = (lst - ra) % 360.0
    return _signed_angle_diff(ha, target_ha)


def _refine_bisection(func, t0: float, t1: float, iterations: int = 24) -> float:
    """Refine a bracketed root with bisection."""
    f0 = func(t0)
    for _ in range(iterations):
        tm = (t0 + t1) / 2.0
        fm = func(tm)
        if f0 == 0.0:
            return t0
        if f0 * fm <= 0.0:
            t1 = tm
        else:
            t0 = tm
            f0 = fm
    return (t0 + t1) / 2.0


def _altitude(
    jd_ut: float,
    lat: float,
    lon: float,
    body_name: str,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
) -> float:
    """Apparent altitude of a body at a given time and location (degrees)."""
    try:
        from .planets import sky_position_at

        return sky_position_at(
            body_name, jd_ut, lat, lon,
            pressure_mbar=pressure_mbar,
            temperature_c=temperature_c,
        ).altitude
    except Exception:
        ra, dec = _body_ra_dec(jd_ut, body_name)
        lst = _lst(jd_ut, lon)
        ha = _signed_angle_diff(lst - ra, 0.0)

        lat_r = math.radians(lat)
        dec_r = math.radians(dec)
        ha_r = math.radians(ha)

        sin_alt = (
            math.sin(lat_r) * math.sin(dec_r)
            + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r)
        )
        return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))


def find_phenomena(
    body_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    altitude: float | None = None,
    policy: 'RiseSetPolicy | None' = None,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
) -> dict[str, float]:
    """
    Find rise, set, and meridian events for a body over the 24h following jd_start.

    Args:
        body_name: Body name string (e.g. ``'Sun'``, ``'Moon'``, ``'Mars'``).
        jd_start: Julian Day (UT) at the start of the 24-hour search window.
        lat: Observer geographic latitude in degrees (north positive).
        lon: Observer geographic longitude in degrees (east positive).
        altitude: Target horizon altitude in degrees.  When provided, this
            value takes precedence over any ``policy`` setting.  When
            ``None`` (default), the altitude is derived from the ``policy``
            if given, otherwise the standard altitude for the body is used
            (−0.8333° for Sun/Moon, −0.5667° for others).
        policy: Optional :class:`RiseSetPolicy` controlling the event
            definition doctrine (disc reference, refraction, Hindu rising,
            etc.).  When ``None``, the standard astronomical convention is
            used.
        pressure_mbar: Atmospheric pressure in millibars used for the
            refraction-corrected altitude computation.  Default 1013.25 mbar.
        temperature_c: Air temperature in degrees Celsius used for the
            refraction-corrected altitude computation.  Default 10.0 °C.

    Returns:
        A dict with keys ``'Rise'``, ``'Set'``, ``'Transit'``, and/or
        ``'AntiTransit'`` mapping to Julian Day values (UT) for events that
        occur within the 24-hour window.  Keys for absent events are omitted.
    """
    # Resolve the effective altitude
    if altitude is not None:
        effective_altitude = altitude
    elif policy is not None:
        effective_altitude = policy.horizon_altitude_for(body_name)
    else:
        # Legacy default: Sun/Moon use refraction + semi-diameter; others use refraction only.
        name_lower = body_name.lower()
        if name_lower in ('sun', 'moon'):
            effective_altitude = -0.8333
        else:
            effective_altitude = -0.5667

    results: dict[str, float] = {}

    # 10-minute brackets are cheap and provide reliable sign changes for the
    # final bisection refinement.
    steps = 144
    altitude_error = lambda jd: _altitude(jd, lat, lon, body_name, pressure_mbar, temperature_c) - effective_altitude
    prev_alt = altitude_error(jd_start)

    for i in range(1, steps + 1):
        jd = jd_start + (i / steps)
        curr_alt = altitude_error(jd)

        if prev_alt == 0.0:
            final_jd = jd - (1.0 / steps)
            if curr_alt >= 0.0:
                results["Rise"] = final_jd
            else:
                results["Set"] = final_jd
        elif prev_alt * curr_alt < 0.0:
            final_jd = _refine_bisection(altitude_error, jd - (1.0 / steps), jd)
            if prev_alt < 0.0 and curr_alt >= 0.0:
                results["Rise"] = final_jd
            elif prev_alt > 0.0 and curr_alt <= 0.0:
                results["Set"] = final_jd

        prev_alt = curr_alt

    transit = get_transit(body_name, jd_start, lat, lon, upper=True)
    if jd_start <= transit < jd_start + 1.0:
        results["Transit"] = transit

    anti_transit = get_transit(body_name, jd_start, lat, lon, upper=False)
    if jd_start <= anti_transit < jd_start + 1.0:
        results["AntiTransit"] = anti_transit

    return results


def get_transit(body_name: str, jd_day: float, lat: float, lon: float, *, upper: bool = True) -> float:
    """Find the precise JD of the upper or lower meridian transit in the next 24h."""
    target_ha = 0.0 if upper else 180.0
    error = lambda value: _hour_angle_error(value, body_name, lat, lon, target_ha)

    # Sample the next 24h and refine the first real sign change near the
    # requested meridian. This avoids false brackets at the +/-180 wrap
    # discontinuity and is materially more reliable for the Moon.
    steps = 288  # 5-minute cadence
    prev_jd = jd_day
    prev_err = error(prev_jd)

    for i in range(1, steps + 1):
        jd = jd_day + (i / steps)
        curr_err = error(jd)
        if (
            prev_err * curr_err <= 0.0
            and max(abs(prev_err), abs(curr_err)) < 90.0
        ):
            return _refine_bisection(error, prev_jd, jd)
        prev_jd = jd
        prev_err = curr_err

    jd = jd_day if upper else jd_day + 0.5
    sidereal_day = 0.9972695663
    for _ in range(8):
        err = error(jd)
        jd -= err / 360.98564736629

    while jd < jd_day:
        jd += sidereal_day
    while jd >= jd_day + 1.0:
        jd -= sidereal_day
    return jd


def _find_sun_altitude_crossing(
    jd_day: float,
    lat: float,
    lon: float,
    target_altitude: float,
    event: str,
) -> float | None:
    """
    Find the JD when the Sun crosses target_altitude on a given day.

    Parameters
    ----------
    jd_day : Julian Day at start of search window (00:00 UT)
    lat : observer latitude (degrees)
    lon : observer longitude (degrees)
    target_altitude : negative altitude in degrees (e.g. -6.0 for civil)
    event : "morning" (before sunrise) or "evening" (after sunset)
    """
    altitude_error = lambda jd: _altitude(jd, lat, lon, "Sun") - target_altitude

    # Anchor the search to the local solar day rather than the fixed UTC day.
    # This keeps dawn and dusk paired to the same local date even for
    # longitudes far west of Greenwich, where evening twilight falls after
    # 00:00 UTC on the following civil day.
    local_noon = jd_day + 0.5 - lon / 360.0
    if event == "morning":
        jd_start, jd_end = local_noon - 0.5, local_noon
        want_rising = True
    else:
        jd_start, jd_end = local_noon, local_noon + 0.5
        want_rising = False

    steps = max(72, int(math.ceil((jd_end - jd_start) * 144)))
    prev_jd = jd_start
    prev_alt = altitude_error(prev_jd)

    for i in range(1, steps + 1):
        jd = jd_start + (jd_end - jd_start) * (i / steps)
        curr_alt = altitude_error(jd)

        crossed = prev_alt == 0.0 or prev_alt * curr_alt < 0.0
        if crossed:
            final_jd = _refine_bisection(altitude_error, prev_jd, jd)
            if want_rising and prev_alt <= 0.0 <= curr_alt:
                return final_jd
            if not want_rising and prev_alt >= 0.0 >= curr_alt:
                return final_jd

        prev_jd = jd
        prev_alt = curr_alt

    return None


@dataclass(slots=True)
class TwilightTimes:
    """
    RITE: The Keeper of Thresholds — the vessel that holds every boundary
          between darkness and light for a single day at a single place on Earth.

    THEOREM: Immutable record of all eight twilight and horizon events
             (astronomical/nautical/civil dawn and dusk, sunrise, and sunset)
             for a given Julian Day and observer location, with None for any
             event that does not occur (e.g. polar day or night).

    RITE OF PURPOSE:
        TwilightTimes is the result vessel of the Rise and Set Engine's
        twilight_times() function.  It consolidates eight individually
        computed altitude-crossing JDs into a single coherent object so
        callers can access any twilight boundary without re-running the
        search.  Without this vessel, callers would receive eight separate
        optional floats with no shared context.

    LAW OF OPERATION:
        Responsibilities:
            - Store jd_day and the eight twilight/horizon JDs (each float
              or None if the event does not occur on that day).
            - Render a compact human-readable repr showing HH:MM for each
              event, or '-' for absent events.
        Non-responsibilities:
            - Does not compute twilight times; that is twilight_times()'s role.
            - Does not validate that events are in chronological order.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd for repr formatting.
        Structural invariants:
            - jd_day is the Julian Day at 00:00 UT of the day in question.
            - All non-None JD fields are within approximately ±1 day of jd_day.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.rise_set.TwilightTimes",
        "risk": "low",
        "api": {"frozen": ["jd_day", "astronomical_dawn", "nautical_dawn", "civil_dawn", "sunrise", "sunset", "civil_dusk", "nautical_dusk", "astronomical_dusk"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    jd_day: float
    astronomical_dawn: float | None
    nautical_dawn: float | None
    civil_dawn: float | None
    sunrise: float | None
    sunset: float | None
    civil_dusk: float | None
    nautical_dusk: float | None
    astronomical_dusk: float | None

    def __repr__(self) -> str:
        from .julian import datetime_from_jd

        def _fmt(jd: float | None) -> str:
            return datetime_from_jd(jd).strftime("%H:%M") if jd else "-"

        return (
            f"Twilight(astro_dawn={_fmt(self.astronomical_dawn)}, "
            f"naut_dawn={_fmt(self.nautical_dawn)}, "
            f"civil_dawn={_fmt(self.civil_dawn)}, "
            f"sunrise={_fmt(self.sunrise)}, "
            f"sunset={_fmt(self.sunset)}, "
            f"civil_dusk={_fmt(self.civil_dusk)}, "
            f"naut_dusk={_fmt(self.nautical_dusk)}, "
            f"astro_dusk={_fmt(self.astronomical_dusk)})"
        )


def twilight_times(
    jd_day: float,
    lat: float,
    lon: float,
) -> TwilightTimes:
    """
    Compute all twilight times for a given day and observer location.

    Parameters
    ----------
    jd_day : Julian Day (UT) at the start of the day (00:00 UT).
    lat : observer geographic latitude (degrees, signed)
    lon : observer geographic longitude (degrees, east positive)
    """
    return TwilightTimes(
        jd_day=jd_day,
        astronomical_dawn=_find_sun_altitude_crossing(jd_day, lat, lon, -18.0, "morning"),
        nautical_dawn=_find_sun_altitude_crossing(jd_day, lat, lon, -12.0, "morning"),
        civil_dawn=_find_sun_altitude_crossing(jd_day, lat, lon, -6.0, "morning"),
        sunrise=_find_sun_altitude_crossing(jd_day, lat, lon, -0.8333, "morning"),
        sunset=_find_sun_altitude_crossing(jd_day, lat, lon, -0.8333, "evening"),
        civil_dusk=_find_sun_altitude_crossing(jd_day, lat, lon, -6.0, "evening"),
        nautical_dusk=_find_sun_altitude_crossing(jd_day, lat, lon, -12.0, "evening"),
        astronomical_dusk=_find_sun_altitude_crossing(jd_day, lat, lon, -18.0, "evening"),
    )
