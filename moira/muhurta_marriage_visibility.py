"""SS IX time-degree geometry under an explicit modern apparent-place adapter.

This is the frozen-position diurnal-arc continuous extension of SS IX.4-11,
not longitude-orb combustion, actual daily horizon crossings, or physical
visibility. Geocentric true-of-date RA/declination retain ecliptic latitude.
No atmospheric/topocentric correction belongs to this mathematical object.
"""
from dataclasses import dataclass, field
from math import acos, degrees, radians, tan

from .panchanga_shuddhi import _number, _longitude, ShuddhiBoundary
from .coordinates import equatorial_to_ecliptic
from ._muhurta_marriage_sources import VISIBILITY

# Source: Burgess SS IX.2-9, printed 220-224, PDF 237-240.
# (body, event role, side, threshold time-degrees, crossing direction).
_EVENTS = (
    ('Jupiter', 'appearance', 'east', 11., 1),
    ('Jupiter', 'disappearance', 'west', 11., -1),
    ('Venus', 'appearance', 'east', 8., 1),
    ('Venus', 'disappearance', 'east', 10., -1),
    ('Venus', 'appearance', 'west', 10., 1),
    ('Venus', 'disappearance', 'west', 8., -1),
)


def _declination(name, value):
    value = _number(name, value)
    if not -90 <= value <= 90:
        raise ValueError(f'{name} must be in [-90,90]')
    return value


@dataclass(frozen=True, slots=True)
class MarriageTimeDegrees:
    """Raw equatorial evidence and the independently auditable diurnal arcs."""
    latitude: float
    sun_ra: float
    sun_declination: float
    planet_ra: float
    planet_declination: float
    sun_horizon_hour_angle: float | None
    planet_horizon_hour_angle: float | None
    east_time_degrees: float | None
    west_time_degrees: float | None
    unavailable_reasons: tuple[str, ...]
    profile: str = field(init=False, default=VISIBILITY)


def marriage_time_degrees(latitude, sun_ra, sun_declination,
                          planet_ra, planet_declination) -> MarriageTimeDegrees:
    """Compute rising lead and setting lag in degrees of sidereal rotation.

    The signed RA difference uses [-180,180). At opposition it changes
    branch; it must not be root-solved across that discontinuity. Negative
    lead/lag remains negative. Polar and tangent geometry is unavailable.
    """
    lat = _declination('latitude', latitude)
    sr = _longitude('sun_ra', sun_ra)
    pr = _longitude('planet_ra', planet_ra)
    sd = _declination('sun_declination', sun_declination)
    pd = _declination('planet_declination', planet_declination)
    reasons = []
    angles = []
    for label, dec in (('Sun', sd), ('planet', pd)):
        if abs(lat) == 90 or abs(dec) == 90:
            reasons.append(label + ':degenerate_horizon')
            angles.append(None)
            continue
        c = -tan(radians(lat)) * tan(radians(dec))
        if not -1 < c < 1:
            reasons.append(label + (':tangent_horizon' if abs(c) == 1 else ':circumpolar_horizon'))
            angles.append(None)
        else:
            angles.append(degrees(acos(c)))
    hs, hp = angles
    delta = (pr - sr + 180) % 360 - 180
    east = west = None
    if hs is not None and hp is not None:
        east, west = -delta + hp - hs, delta + hp - hs
    return MarriageTimeDegrees(lat, sr, sd, pr, pd, hs, hp, east, west, tuple(reasons))


@dataclass(frozen=True, slots=True)
class MarriageVisibilitySample:
    """One raw, same-epoch coordinate sample; no caller-provided verdict."""
    jd_ut1: float
    planet: str
    latitude: float
    sun_ra: float
    sun_declination: float
    planet_ra: float
    planet_declination: float
    sun_tropical_longitude: float
    planet_tropical_longitude: float
    true_obliquity: float

    def __post_init__(self):
        _number('jd_ut1', self.jd_ut1)
        if self.planet not in ('Jupiter', 'Venus'):
            raise ValueError('availability is defined for Jupiter and Venus')
        self.geometry()
        _longitude('sun_tropical_longitude', self.sun_tropical_longitude)
        _longitude('planet_tropical_longitude', self.planet_tropical_longitude)
        eps = _number('true_obliquity', self.true_obliquity)
        if not 0 <= eps < 90:
            raise ValueError('true_obliquity must lie in [0,90)')
        for ra,dec,longitude in ((self.sun_ra,self.sun_declination,self.sun_tropical_longitude),
                                 (self.planet_ra,self.planet_declination,self.planet_tropical_longitude)):
            converted = equatorial_to_ecliptic(ra,dec,eps)[0]
            if abs((converted-longitude+180)%360-180)>1e-8:
                raise ValueError('equatorial and ecliptic evidence must share the declared frame')

    def geometry(self):
        return marriage_time_degrees(self.latitude, self.sun_ra, self.sun_declination,
                                     self.planet_ra, self.planet_declination)

    @property
    def side(self):
        delta = (self.planet_tropical_longitude - self.sun_tropical_longitude + 180) % 360 - 180
        return 'east' if delta < 0 else 'west'


@dataclass(frozen=True, slots=True)
class MarriageVisibilityEvent:
    """Directional root bracket, validated against its actual endpoint samples.

    A pair of samples establishes a crossing candidate. It does not prove
    uniqueness or completeness of an event search; that is a separate receipt.
    """
    role: str
    side: str
    boundary: ShuddhiBoundary
    before: MarriageVisibilitySample
    after: MarriageVisibilitySample

    def __post_init__(self):
        if not isinstance(self.boundary, ShuddhiBoundary):
            raise ValueError('event boundary must be ShuddhiBoundary')
        if not isinstance(self.before, MarriageVisibilitySample) or not isinstance(self.after, MarriageVisibilitySample):
            raise ValueError('event endpoints must be visibility samples')
        if (self.before.planet != self.after.planet or self.before.latitude != self.after.latitude
                or self.before.jd_ut1 != self.boundary.lower_jd_ut1
                or self.after.jd_ut1 != self.boundary.upper_jd_ut1
                or self.before.jd_ut1 >= self.after.jd_ut1):
            raise ValueError('event coordinates and bracket must share body, latitude and epochs')
        row = next((r for r in _EVENTS if r[:3] == (self.before.planet, self.role, self.side)), None)
        if row is None:
            raise ValueError('unsupported visibility event role/branch')
        if self.before.side != self.side or self.after.side != self.side:
            raise ValueError('visibility event cannot straddle a solar branch boundary')
        ra_offsets = tuple((s.planet_ra-s.sun_ra+180)%360-180 for s in (self.before,self.after))
        if abs(ra_offsets[1]-ra_offsets[0])>180:
            raise ValueError('visibility event cannot straddle the RA unwrapping cut')
        a = getattr(self.before.geometry(), self.side + '_time_degrees')
        b = getattr(self.after.geometry(), self.side + '_time_degrees')
        if a is None or b is None:
            raise ValueError('a crossing requires available horizon geometry')
        q, direction = row[3:]
        if not direction * (a - q) <= 0 <= direction * (b - q) or a == b:
            raise ValueError('samples do not bracket the selected directional threshold')

    @property
    def planet(self):
        return self.before.planet

    @property
    def threshold_time_degrees(self):
        return next(r[3] for r in _EVENTS if r[:3] == (self.planet, self.role, self.side))


@dataclass(frozen=True, slots=True)
class MarriageApparitionContext:
    """Adjacent role-appropriate events bounding an apparition or an absence.

    Direct callers supply the adjacency claim as astronomical evidence.
    Only a separate reader search certificate can establish it computationally.
    Venus requires history: current east/west separation alone is insufficient.
    """
    previous_event: MarriageVisibilityEvent
    next_event: MarriageVisibilityEvent

    def __post_init__(self):
        a, b = self.previous_event, self.next_event
        if not isinstance(a, MarriageVisibilityEvent) or not isinstance(b, MarriageVisibilityEvent):
            raise ValueError('apparition context requires typed events')
        if (a.planet != b.planet or a.before.latitude != b.before.latitude
                or a.role == b.role or a.boundary.upper_jd_ut1 >= b.boundary.lower_jd_ut1):
            raise ValueError('events must be ordered, same-body, same-latitude and alternate roles')
        if a.role == 'appearance':
            expected_side = 'west' if a.planet == 'Jupiter' else a.side
            if b.side != expected_side:
                raise ValueError('appearance and disappearance do not bound the same apparition')
        elif a.planet == 'Venus' and a.side == b.side:
            raise ValueError('adjacent Venus apparitions alternate solar sides')


@dataclass(frozen=True, slots=True)
class MarriageAvailability:
    """Source-event waiting-period decision with independent availability evidence coverage."""
    planet: str
    state: str
    restricted: bool | None
    post_appearance_days: int | None
    pre_disappearance_days: int | None
    usable_start: ShuddhiBoundary | None
    usable_end: ShuddhiBoundary | None
    context: MarriageApparitionContext | None
    unavailable_reasons: tuple[str, ...]
    clock: str = field(init=False, default='fixed_elapsed_UT1_days')


_BUFFERS = {('Jupiter','east'):(15,15), ('Jupiter','west'):(15,15),
            ('Venus','east'):(3,15), ('Venus','west'):(10,5)}


def marriage_planet_availability(planet, jd_ut1, context=None) -> MarriageAvailability:
    """Apply MC Samskara 27 waiting periods without erasing root uncertainty."""
    jd = _number('jd_ut1', jd_ut1)
    if planet not in ('Jupiter', 'Venus'):
        raise ValueError('planet must be Jupiter or Venus')
    if context is None:
        return MarriageAvailability(planet, 'unavailable', None, None, None, None, None, None,
                                    ('adjacent_apparition_events_missing',))
    if not isinstance(context, MarriageApparitionContext):
        raise ValueError('context must be MarriageApparitionContext')
    a, b = context.previous_event, context.next_event
    if a.planet != planet or not a.boundary.lower_jd_ut1 <= jd <= b.boundary.upper_jd_ut1:
        raise ValueError('context body/epoch does not contain the requested instant')
    for event in (a, b):
        if event.boundary.lower_jd_ut1 <= jd <= event.boundary.upper_jd_ut1:
            return MarriageAvailability(planet, 'uncertain', None, None, None, None, None, context,
                                        ('heliacal_root_band',))
    if a.role == 'disappearance':
        return MarriageAvailability(planet, 'asta', True, None, None, None, None, context, ())
    post, pre = _BUFFERS[(planet,a.side)]
    def shifted(boundary, days, kind):
        return ShuddhiBoundary(kind, boundary.jd_ut1 + days,
                               boundary.lower_jd_ut1 + days, boundary.upper_jd_ut1 + days)
    start = shifted(a.boundary, post, 'post_appearance_buffer_end')
    end = shifted(b.boundary, -pre, 'pre_disappearance_buffer_start')
    if start.lower_jd_ut1 > end.upper_jd_ut1:
        return MarriageAvailability(planet, 'overlapping_waiting_periods', True, post, pre,
                                    start, end, context, ())
    if any(x.lower_jd_ut1 <= jd <= x.upper_jd_ut1 for x in (start, end)):
        state, restricted, reasons = 'uncertain', None, ('shifted_heliacal_root_band',)
    elif jd < start.lower_jd_ut1:
        state, restricted, reasons = 'balya', True, ()
    elif jd > end.upper_jd_ut1:
        state, restricted, reasons = 'vriddha', True, ()
    else:
        state, restricted, reasons = 'available', False, ()
    return MarriageAvailability(planet, state, restricted, post, pre, start, end, context, reasons)


__all__ = ['MarriageTimeDegrees', 'MarriageVisibilitySample', 'MarriageVisibilityEvent',
           'MarriageApparitionContext', 'MarriageAvailability', 'marriage_time_degrees',
           'marriage_planet_availability']
