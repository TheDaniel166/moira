"""Source-selected marriage election evidence, policy and aggregate ownership.

Direct assessment is kernel-free and conditional on caller-supplied astronomy.
Missing prerequisites are visible; they never authorize a pass or cancellation.
The dated owner builds these same immutable inputs with its serving reader.
"""
from dataclasses import dataclass, field

from ._muhurta_marriage_sources import ORDINARY, PERSONAL, GODHULI, NINE, RULES, EXCLUSIONS, RESEARCH_VARIANTS
from .panchanga_shuddhi import (_number, _integer, _longitude, ShuddhiBoundary,
                               ShuddhiInterval)
from .muhurta_dosha import DoshaPhaseSpan, MuhurtaDoshaInputs
from .lunar_month import LunarMonthResult, LunarMonthSystem
from .muhurta_marriage_visibility import MarriageApparitionContext
from ._muhurta_marriage_roundoff import ARITHMETIC_MODEL


def _tuple(name, value, cls, maximum):
    if type(value) is not tuple or len(value) > maximum or any(not isinstance(v, cls) for v in value):
        raise ValueError(f'{name} must be a tuple of {cls.__name__}, maximum {maximum}')


def _choice(name, value, choices):
    if type(value) is not str or value not in choices:
        raise ValueError(f'unsupported {name}: {value!r}')


REGIONS = ('all_regions', 'kuru_bahlika', 'kalinga_vanga', 'saurashtra_shalva', 'dakshinatya')
REMEDIES = ('mc68_own_or_exalted_luminaries', 'mc83_lagna_aspect',
            'mc88_weak_afflictors', 'mc89_benefic_kendra_trikona',
            'mc90_anvaya_disjunction', 'mc90_moon_eleventh',
            'mc91_lagna_lords_placement')


@dataclass(frozen=True, slots=True)
class MarriageElectionPolicy:
    """Explicit ritual, regional tradition and independently selected remedies."""
    ritual_anchor: str
    regional_tradition: str
    profile: str = ORDINARY
    remedies: tuple[str, ...] = ('mc68_own_or_exalted_luminaries', 'mc83_lagna_aspect', 'mc88_weak_afflictors')
    godhuli: bool = False
    ayanamsa_system: str = 'Lahiri'
    month_system: LunarMonthSystem = LunarMonthSystem.AMANTA
    navamsa_profile: str = 'mc_avasthi_vivaha_84_four.v1'
    solver_tolerance_seconds: float = .1
    nature_profile: str = field(init=False, default='bphs_3_11_verse_phase_same_sign.v1')
    abhijit_pada_convention: str = field(init=False, default='equal_abhijit_subarcs_other_stars_original_padas.v1')
    calendar_precedence: str = field(init=False, default='vivaha13_over_general_samskara26')
    ingress_clock: str = field(init=False, default='mc79_sunrise_dates_mc80_symmetric_total_ghatis')
    history_occupancy_profile: str = field(init=False, default='mc58_nearest_passages_distinct_afflictor_event_time_nature.v1')
    history_piercing_profile: str = field(init=False, default='mc58_persistent_vedha_complete_Moon28_clearance.v1')
    numerical_arithmetic_model: str = field(init=False, default=ARITHMETIC_MODEL)

    def __post_init__(self):
        if type(self.ritual_anchor) is not str or not self.ritual_anchor.strip() or len(self.ritual_anchor) > 160:
            raise ValueError('ritual_anchor must be a nonempty label of at most 160 characters')
        _choice('profile', self.profile, (ORDINARY,))
        _choice('regional_tradition', self.regional_tradition, REGIONS)
        _tuple('remedies', self.remedies, str, len(REMEDIES))
        if len(set(self.remedies)) != len(self.remedies) or any(x not in REMEDIES for x in self.remedies):
            raise ValueError('remedies must be unique admitted identifiers')
        if type(self.godhuli) is not bool:
            raise ValueError('godhuli must be boolean')
        # This initial composition admits one consistently shared sidereal basis.
        _choice('ayanamsa_system', self.ayanamsa_system, ('Lahiri',))
        if self.month_system is not LunarMonthSystem.AMANTA:
            raise ValueError('this marriage composition requires the physical amanta lunar-month system')
        _choice('navamsa_profile', self.navamsa_profile,
                ('mc_avasthi_vivaha_84_four.v1', 'mc_vivaha_84_optional_pisces.v1'))
        if not .01 <= _number('solver_tolerance_seconds', self.solver_tolerance_seconds) <= 1:
            raise ValueError('solver_tolerance_seconds must be in [.01,1]')


@dataclass(frozen=True, slots=True)
class MarriagePlanet:
    """Same-election-epoch apparent sidereal longitude and optional motion."""
    planet: str
    sidereal_longitude: float
    longitude_speed: float | None = None
    motion_basis: str = field(init=False,default='tropical_true_of_date_circular_difference_TT_plus_minus_0.002_days')

    def __post_init__(self):
        _choice('planet', self.planet, NINE)
        _longitude('sidereal_longitude', self.sidereal_longitude)
        if self.longitude_speed is not None:
            _number('longitude_speed', self.longitude_speed)


@dataclass(frozen=True, slots=True)
class MarriageExtent:
    """A complete history extent; unlike a solar-day interval it may span years."""
    start_jd_ut1: float
    end_jd_ut1: float

    def __post_init__(self):
        if not _number('start_jd_ut1', self.start_jd_ut1) < _number('end_jd_ut1', self.end_jd_ut1):
            raise ValueError('extent must be positive and half-open')


@dataclass(frozen=True, slots=True)
class MarriageTimeSpan:
    """An original multi-day parent with independently enclosed endpoints."""
    start: ShuddhiBoundary
    end: ShuddhiBoundary

    def __post_init__(self):
        if not isinstance(self.start, ShuddhiBoundary) or not isinstance(self.end, ShuddhiBoundary) or self.start.upper_jd_ut1 >= self.end.lower_jd_ut1:
            raise ValueError('time span requires ordered disjoint typed boundaries')

    def contains(self, jd_ut1):
        jd = _number('jd_ut1', jd_ut1)
        if any(b.lower_jd_ut1 < b.upper_jd_ut1 and b.lower_jd_ut1 <= jd <= b.upper_jd_ut1 for b in (self.start, self.end)):
            return None
        return self.start.jd_ut1 <= jd < self.end.jd_ut1


@dataclass(frozen=True, slots=True)
class MarriageSolarContext:
    """Full sunrise-owned day, daylight, and optional complete sunrise history."""
    day: ShuddhiInterval
    sunset: ShuddhiBoundary
    weekday: int
    half_set: ShuddhiBoundary | None = None
    sunrise_history: tuple[ShuddhiBoundary, ...] = ()
    history_extent: MarriageExtent | None = None
    upper_limb_set: ShuddhiBoundary | None = None

    def __post_init__(self):
        if not isinstance(self.day, ShuddhiInterval) or not isinstance(self.sunset, ShuddhiBoundary):
            raise ValueError('solar context requires typed day and sunset')
        _integer('weekday', self.weekday, 0, 6)
        if not self.day.start.upper_jd_ut1 < self.sunset.lower_jd_ut1 <= self.sunset.upper_jd_ut1 < self.day.end.lower_jd_ut1:
            raise ValueError('sunset must lie strictly inside its full sunrise day')
        if self.half_set is not None:
            if not isinstance(self.half_set, ShuddhiBoundary) or abs(self.half_set.jd_ut1 - self.sunset.jd_ut1) > 1/24:
                raise ValueError('half_set must be a solar horizon event near sunset')
        if self.upper_limb_set is not None:
            if not isinstance(self.upper_limb_set, ShuddhiBoundary) or self.half_set is None or not 0 <= self.upper_limb_set.jd_ut1-self.half_set.jd_ut1 <= 1/24:
                raise ValueError('upper_limb_set requires an ordered half-set anchor within one hour')
        _tuple('sunrise_history', self.sunrise_history, ShuddhiBoundary, 128)
        if self.history_extent is None:
            if self.sunrise_history:
                raise ValueError('sunrise history requires its complete searched extent')
        else:
            if not isinstance(self.history_extent, MarriageExtent):
                raise ValueError('history_extent must be MarriageExtent')
            for a, b in zip(self.sunrise_history, self.sunrise_history[1:]):
                if a.upper_jd_ut1 >= b.lower_jd_ut1:
                    raise ValueError('sunrise history must be ordered and disjoint')
            if any(not self.history_extent.start_jd_ut1 <= x.lower_jd_ut1 <= x.upper_jd_ut1 <= self.history_extent.end_jd_ut1 for x in self.sunrise_history):
                raise ValueError('sunrise history must lie inside its searched extent')
            if not any(x == self.day.start for x in self.sunrise_history) or not any(x == self.day.end for x in self.sunrise_history):
                raise ValueError('sunrise history must include the current day endpoints')


@dataclass(frozen=True, slots=True)
class MarriageIngress:
    """Directional sign ingress bracket and any required sunrise-owned solar exclusion parent."""
    planet: str
    entered_sign: int
    direction: int
    boundary: ShuddhiBoundary
    cardinal_solar_days: MarriageTimeSpan | None = None

    def __post_init__(self):
        _choice('planet', self.planet, NINE[:7])
        _integer('entered_sign', self.entered_sign, 0, 11)
        if type(self.direction) is not int or self.direction not in (-1, 1):
            raise ValueError('ingress direction must be -1 or +1')
        if not isinstance(self.boundary, ShuddhiBoundary):
            raise ValueError('ingress requires a typed boundary')
        if self.cardinal_solar_days is not None:
            if self.planet != 'Sun' or self.entered_sign not in (0, 3, 6, 9) or not isinstance(self.cardinal_solar_days, MarriageTimeSpan):
                raise ValueError('three-date exclusion applies only to cardinal Sun ingress')
            if self.cardinal_solar_days.contains(self.boundary.jd_ut1) is not True:
                raise ValueError('cardinal solar date extent must contain the ingress')


@dataclass(frozen=True, slots=True)
class MarriageIngressHistory:
    """Declared search extent, participating bodies and chronologically ordered ingresses."""
    extent: MarriageExtent
    planets: tuple[str, ...]
    events: tuple[MarriageIngress, ...]

    def __post_init__(self):
        if not isinstance(self.extent, MarriageExtent):
            raise ValueError('ingress history requires an extent')
        _tuple('planets', self.planets, str, 7)
        if len(set(self.planets)) != len(self.planets) or any(p not in NINE[:7] for p in self.planets):
            raise ValueError('ingress history planet identities must be unique classical planets')
        _tuple('events', self.events, MarriageIngress, 4096)
        previous = {}
        for e in self.events:
            if e.planet not in self.planets or not self.extent.start_jd_ut1 <= e.boundary.lower_jd_ut1 <= e.boundary.upper_jd_ut1 <= self.extent.end_jd_ut1:
                raise ValueError('ingress is outside its history body/extent')
            if e.planet in previous and previous[e.planet] >= e.boundary.lower_jd_ut1:
                raise ValueError('per-planet ingresses must be ordered and disjoint')
            previous[e.planet] = e.boundary.upper_jd_ut1


@dataclass(frozen=True, slots=True)
class MarriageStarPassage:
    """Complete original star passage, not a clipped search-window fragment."""
    planet: str
    star_index: int
    entry: ShuddhiBoundary
    exit: ShuddhiBoundary

    def __post_init__(self):
        _choice('planet', self.planet, NINE)
        _integer('star_index', self.star_index, 0, 26)
        if not isinstance(self.entry, ShuddhiBoundary) or not isinstance(self.exit, ShuddhiBoundary) or self.entry.upper_jd_ut1 >= self.exit.lower_jd_ut1:
            raise ValueError('star passage requires ordered, disjoint entry and exit')


@dataclass(frozen=True, slots=True)
class MarriageHistoricalSkySpan:
    """Raw sky witness inside a full cell of constant historical rule inputs."""
    interval: ShuddhiInterval
    jd_ut1: float
    planets: tuple[MarriagePlanet,...]

    def __post_init__(self):
        if not isinstance(self.interval,ShuddhiInterval) or self.interval.contains(self.jd_ut1) is not True:
            raise ValueError('historical witness must lie inside its full rule cell')
        MarriageElectionEvidence(self.jd_ut1,self.planets)


@dataclass(frozen=True, slots=True)
class MarriageHistoricalLongitude:
    """Unwrapped longitude enclosure over an entire historical root band."""
    planet: str
    lower_degrees: float
    upper_degrees: float

    def __post_init__(self):
        _choice('planet',self.planet,NINE)
        lo=_number('lower_degrees',self.lower_degrees)
        hi=_number('upper_degrees',self.upper_degrees)
        if not 0<=hi-lo<360 or not -720<=lo<=hi<=1080:
            raise ValueError('historical longitude requires an ordered bounded unwrapped arc')


@dataclass(frozen=True, slots=True)
class MarriageHistoricalSkyBand:
    """Joint uncertain event interval with raw full-band angular bounds."""
    boundary: ShuddhiBoundary
    longitudes: tuple[MarriageHistoricalLongitude,...]
    phase_bounds: tuple[float,float] | None = None
    unavailable_reasons: tuple[str,...] = ()

    def __post_init__(self):
        if not isinstance(self.boundary,ShuddhiBoundary):
            raise ValueError('historical sky band requires a boundary')
        _tuple('longitudes',self.longitudes,MarriageHistoricalLongitude,9)
        if len({p.planet for p in self.longitudes})!=len(self.longitudes):
            raise ValueError('historical band planets must be unique')
        _tuple('unavailable_reasons',self.unavailable_reasons,str,32)
        if self.phase_bounds is not None:
            if type(self.phase_bounds) is not tuple or len(self.phase_bounds)!=2:
                raise ValueError('phase bounds require an ordered pair')
            lo,hi=(_number('phase_bound',x) for x in self.phase_bounds)
            if not 0<=hi-lo<360 or not -720<=lo<=hi<=1080:
                raise ValueError('invalid unwrapped historical phase bounds')


@dataclass(frozen=True, slots=True)
class MarriageMoon28Passage:
    """A complete Moon traversal of an unequal, Abhijit-inclusive star."""
    star_index: int
    entry: ShuddhiBoundary
    exit: ShuddhiBoundary

    def __post_init__(self):
        _integer('star_index',self.star_index,0,27)
        MarriageTimeSpan(self.entry,self.exit)


@dataclass(frozen=True, slots=True)
class MarriageStarHistory:
    """Nearest previous/current/next passages and actual Moon clearance.

    Nearest-event selection is the named Moira interpretation of MC58's
    unquantified past/future language. A fixed number of days is not clearance.
    """
    extent: MarriageExtent
    planets: tuple[str, ...]
    passages: tuple[MarriageStarPassage, ...]
    vedha_spans: tuple[MarriageHistoricalSkySpan,...] = ()
    moon28_passages: tuple[MarriageMoon28Passage,...] = ()
    transition_bands: tuple[MarriageHistoricalSkyBand,...] = ()

    def __post_init__(self):
        if not isinstance(self.extent, MarriageExtent):
            raise ValueError('star history requires an extent')
        _tuple('planets', self.planets, str, 9)
        if len(set(self.planets)) != len(self.planets) or any(p not in NINE for p in self.planets):
            raise ValueError('star history identities must be unique')
        _tuple('passages', self.passages, MarriageStarPassage, 4096)
        last = {}
        for p in self.passages:
            if p.planet not in self.planets or not self.extent.start_jd_ut1 <= p.entry.lower_jd_ut1 < p.exit.upper_jd_ut1 <= self.extent.end_jd_ut1:
                raise ValueError('star passage lies outside its history body/extent')
            if p.planet in last and last[p.planet] > p.entry.lower_jd_ut1:
                raise ValueError('star passages of one planet must not overlap')
            last[p.planet] = p.exit.lower_jd_ut1
        _tuple('vedha_spans',self.vedha_spans,MarriageHistoricalSkySpan,4096)
        _tuple('moon28_passages',self.moon28_passages,MarriageMoon28Passage,4096)
        _tuple('transition_bands',self.transition_bands,MarriageHistoricalSkyBand,4096)
        expected={s.interval.end for s in self.vedha_spans[:-1]
                  if s.interval.end.lower_jd_ut1<s.interval.end.upper_jd_ut1}
        actual={b.boundary for b in self.transition_bands}
        if len(actual)!=len(self.transition_bands) or not actual<=expected:
            raise ValueError('historical uncertainty bands must be unique shared cell boundaries')
        for span in self.vedha_spans:
            if not self.extent.start_jd_ut1<=span.interval.start.lower_jd_ut1<span.interval.end.upper_jd_ut1<=self.extent.end_jd_ut1:
                raise ValueError('historical vedha cell lies outside history extent')
        for a,b in zip(self.vedha_spans,self.vedha_spans[1:]):
            if a.interval.end!=b.interval.start:
                raise ValueError('historical vedha cells must retain every shared transition band')
        for p in self.moon28_passages:
            if not self.extent.start_jd_ut1<=p.entry.lower_jd_ut1<p.exit.upper_jd_ut1<=self.extent.end_jd_ut1:
                raise ValueError('Moon28 passage lies outside history extent')
        for a,b in zip(self.moon28_passages,self.moon28_passages[1:]):
            if a.exit!=b.entry or b.star_index!=(a.star_index+1)%28:
                raise ValueError('Moon28 history requires consecutive full star passages')


@dataclass(frozen=True, slots=True)
class MarriageYogaEnding:
    """Full source Yoga occurrence and its ending Moon/Sun context."""
    yoga_index: int
    boundary: ShuddhiBoundary
    moon_sidereal_longitude: float
    sun_sidereal_longitude: float

    def __post_init__(self):
        _integer('yoga_index', self.yoga_index, 0, 26)
        if not isinstance(self.boundary, ShuddhiBoundary):
            raise ValueError('yoga ending requires a typed boundary')
        _longitude('moon_sidereal_longitude', self.moon_sidereal_longitude)
        _longitude('sun_sidereal_longitude', self.sun_sidereal_longitude)
        target = ((self.yoga_index + 1) * 360 / 27) % 360
        delta = ((self.moon_sidereal_longitude + self.sun_sidereal_longitude - target + 180) % 360) - 180
        # Numerical event coordinates may be at either side of a <=1s bracket.
        if abs(delta) > .001:
            raise ValueError('ending coordinates must agree with the yoga boundary target')


@dataclass(frozen=True, slots=True)
class MarriageElectionEvidence:
    """Validated immutable astronomical inputs; missing evidence remains explicit."""
    jd_ut1: float
    planets: tuple[MarriagePlanet, ...] = ()
    lagna_sidereal_longitude: float | None = None
    solar: MarriageSolarContext | None = None
    phase_spans: tuple[DoshaPhaseSpan, ...] = ()
    yoga_span: ShuddhiInterval | None = None
    karana_span: ShuddhiInterval | None = None
    lunar_month: LunarMonthResult | None = None
    ingress_history: MarriageIngressHistory | None = None
    star_history: MarriageStarHistory | None = None
    yoga_endings: tuple[MarriageYogaEnding, ...] = ()
    jupiter_apparition: MarriageApparitionContext | None = None
    venus_apparition: MarriageApparitionContext | None = None
    ayanamsa_system: str = 'Lahiri'
    longitude_frame: str = field(init=False, default='apparent_geocentric_true_ecliptic_of_date')
    node_basis: str = field(init=False, default='true_geometric_of_date')

    def __post_init__(self):
        _number('jd_ut1', self.jd_ut1)
        _tuple('planets', self.planets, MarriagePlanet, 9)
        if len({p.planet for p in self.planets}) != len(self.planets):
            raise ValueError('planet identities must be unique')
        _choice('ayanamsa_system', self.ayanamsa_system, ('Lahiri',))
        if self.lagna_sidereal_longitude is not None:
            _longitude('lagna_sidereal_longitude', self.lagna_sidereal_longitude)
        if self.solar is not None and (not isinstance(self.solar, MarriageSolarContext) or self.solar.day.contains(self.jd_ut1) is False):
            raise ValueError('solar context must contain the election epoch')
        _tuple('phase_spans', self.phase_spans, DoshaPhaseSpan, 64)
        positions = {p.planet: p.sidereal_longitude for p in self.planets}
        if 'Rahu' in positions and 'Ketu' in positions:
            if abs(((positions['Ketu'] - positions['Rahu']) % 360) - 180) > 1e-10:
                raise ValueError('Rahu and Ketu must be antipodal')
        if {'Sun', 'Moon'} <= positions.keys():
            MuhurtaDoshaInputs(positions['Sun'], positions['Moon'], self.jd_ut1,
                None if self.solar is None else self.solar.weekday,
                self.lagna_sidereal_longitude, self.phase_spans,
                None if self.solar is None else self.solar.day,
                None if self.solar is None else self.solar.sunset)
        elif self.phase_spans or self.yoga_span or self.karana_span:
            raise ValueError('phase evidence requires Sun and Moon positions')
        for name in ('yoga_span', 'karana_span'):
            span = getattr(self, name)
            if span is not None and (not isinstance(span, ShuddhiInterval) or span.contains(self.jd_ut1) is False):
                raise ValueError(f'{name} must contain the election epoch')
        if self.lunar_month is not None:
            if not isinstance(self.lunar_month, LunarMonthResult):
                raise ValueError('lunar_month must be canonical LunarMonthResult')
            self.lunar_month.__post_init__()
            for lunation in (self.lunar_month.previous_lunation,self.lunar_month.amanta_lunation,self.lunar_month.next_lunation):
                lunation.__post_init__()
            if self.lunar_month.jd_ut1 != self.jd_ut1 or self.lunar_month.policy.ayanamsa_system != self.ayanamsa_system:
                raise ValueError('lunar month epoch and ayanamsa must match election')
            if {'Sun', 'Moon'} <= positions.keys():
                from .panchanga_shuddhi import _sector
                tithi = _sector((positions['Moon']-positions['Sun']) % 360, 30)
                if self.lunar_month.tithi_number != tithi % 15 + 1 or self.lunar_month.paksha != ('Shukla' if tithi < 15 else 'Krishna'):
                    raise ValueError('lunar month tithi must agree with supplied positions')
        for name, cls in (('ingress_history', MarriageIngressHistory), ('star_history', MarriageStarHistory)):
            h = getattr(self, name)
            if h is not None and (not isinstance(h, cls) or not h.extent.start_jd_ut1 <= self.jd_ut1 < h.extent.end_jd_ut1):
                raise ValueError(f'{name} must cover the election epoch')
        if self.star_history is not None:
            from .panchanga_shuddhi import _sector
            for passage in self.star_history.passages:
                if passage.entry.upper_jd_ut1 < self.jd_ut1 < passage.exit.lower_jd_ut1 and passage.planet in positions:
                    if _sector(positions[passage.planet],27)!=passage.star_index:
                        raise ValueError('current star history contradicts the election longitude')
            from ._muhurta_marriage_rules import star28
            from .muhurta_lagna import _nature
            for passage in self.star_history.moon28_passages:
                if passage.entry.upper_jd_ut1<self.jd_ut1<passage.exit.lower_jd_ut1 and 'Moon' in positions:
                    if star28(positions['Moon'])[0]!=passage.star_index:
                        raise ValueError('current Moon28 history contradicts election longitude')
            for span in self.star_history.vedha_spans:
                if span.interval.contains(self.jd_ut1) is not True:
                    continue
                historical={p.planet:p.sidereal_longitude for p in span.planets}
                for body in positions.keys() & historical.keys():
                    if star28(positions[body])!=star28(historical[body]):
                        raise ValueError('current historical sky cell contradicts election star/pada')
                before,now=_nature(historical),_nature(positions)
                if any(before[p] is not None and now[p] is not None and before[p]!=now[p] for p in NINE):
                    raise ValueError('current historical sky cell contradicts election planet nature')
        if self.ingress_history is not None:
            for planet in self.ingress_history.planets:
                earlier=[x for x in self.ingress_history.events if x.planet==planet and x.boundary.upper_jd_ut1<self.jd_ut1]
                if earlier and planet in positions:
                    from .panchanga_shuddhi import _sector
                    if earlier[-1].entered_sign!=_sector(positions[planet],12):
                        raise ValueError('most recent ingress contradicts the election sign')
        _tuple('yoga_endings', self.yoga_endings, MarriageYogaEnding, 64)
        for a, b in zip(self.yoga_endings, self.yoga_endings[1:]):
            if a.boundary.upper_jd_ut1 >= b.boundary.lower_jd_ut1:
                raise ValueError('yoga endings must be ordered and disjoint')
            if b.yoga_index!=(a.yoga_index+1)%27:
                raise ValueError('yoga endings must retain consecutive indices')
        for planet, name in (('Jupiter', 'jupiter_apparition'), ('Venus', 'venus_apparition')):
            context = getattr(self, name)
            if context is not None:
                from .muhurta_marriage_visibility import marriage_planet_availability
                marriage_planet_availability(planet, self.jd_ut1, context)


@dataclass(frozen=True, slots=True)
class MarriageParticipant:
    """Supplied natal evidence and explicit traditional rule role, never inferred."""
    participant_id: str
    role: str
    natal_moon_sidereal_longitude: float | None = None
    natal_lagna_sidereal_longitude: float | None = None
    birth_lunar_month_index: int | None = None
    birth_tithi_index: int | None = None
    first_born: bool | None = None
    natal_jd_ut1: float | None = None
    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self):
        if type(self.participant_id) is not str or not self.participant_id.strip() or len(self.participant_id) > 80:
            raise ValueError('participant_id must be a nonempty string of at most 80 characters')
        _choice('role', self.role, ('bride', 'groom'))
        _choice('ayanamsa_system', self.ayanamsa_system, ('Lahiri',))
        for name in ('natal_moon_sidereal_longitude', 'natal_lagna_sidereal_longitude'):
            if getattr(self, name) is not None:
                _longitude(name, getattr(self, name))
        if self.birth_lunar_month_index is not None:
            _integer('birth_lunar_month_index', self.birth_lunar_month_index, 0, 11)
        if self.birth_tithi_index is not None:
            _integer('birth_tithi_index', self.birth_tithi_index, 0, 29)
        if self.first_born is not None and type(self.first_born) is not bool:
            raise ValueError('first_born must be boolean or None')
        if self.natal_jd_ut1 is not None:
            _number('natal_jd_ut1', self.natal_jd_ut1)


@dataclass(frozen=True, slots=True)
class MarriagePersonalContext:
    """Explicit participants and role-specific natal context for personal assessment."""
    participants: tuple[MarriageParticipant, ...]
    profile: str = PERSONAL

    def __post_init__(self):
        _choice('personal profile', self.profile, (PERSONAL,))
        _tuple('participants', self.participants, MarriageParticipant, 2)
        if len(self.participants) != 2 or len({p.participant_id for p in self.participants}) != 2 or {p.role for p in self.participants} != {'bride', 'groom'}:
            raise ValueError('personal context requires two distinct identities with bride/groom rule roles')


@dataclass(frozen=True, slots=True)
class MarriageMeasure:
    """Named source witness value with its kind and explanatory provenance."""
    name: str
    value: float | int | str | bool | None
    unit: str

    def __post_init__(self):
        if type(self.name) is not str or not self.name or type(self.unit) is not str or not self.unit:
            raise ValueError('measure requires a name and unit')
        if self.value is not None and type(self.value) not in (str,bool,int,float):
            raise ValueError('measure must contain a scalar value or None')
        if type(self.value) in (int,float):
            _number('measure',self.value)


@dataclass(frozen=True, slots=True)
class MarriageException:
    """Named remedy prerequisite outcome and its exact source-supported effect."""
    exception_id: str
    targets: tuple[str, ...]
    satisfied: bool | None
    prerequisites: tuple[MarriageMeasure, ...]
    source: str

    def __post_init__(self):
        if not self.exception_id or not self.source or type(self.exception_id) is not str or type(self.source) is not str:
            raise ValueError('exception requires source and identity')
        _tuple('targets',self.targets,str,512)
        _tuple('prerequisites',self.prerequisites,MarriageMeasure,128)
        if not self.targets or len(set(self.targets))!=len(self.targets):
            raise ValueError('exception requires unique explicit targets')
        if self.satisfied is not None and type(self.satisfied) is not bool:
            raise ValueError('exception satisfaction must be boolean or None')


@dataclass(frozen=True, slots=True)
class MarriageFinding:
    """Detected source rule with raw witnesses, named exceptions and independent coverage."""
    rule_id: str
    family_id: str
    source: str
    applicable: bool | None
    detected: bool | None
    measures: tuple[MarriageMeasure, ...]
    exceptions: tuple[MarriageException, ...]
    unavailable_reasons: tuple[str, ...]
    advisory: bool = False

    def __post_init__(self):
        for name in ('rule_id','family_id','source'):
            if type(getattr(self,name)) is not str or not getattr(self,name):
                raise ValueError('finding requires identity and source')
        for name in ('applicable','detected'):
            if getattr(self,name) is not None and type(getattr(self,name)) is not bool:
                raise ValueError('finding predicates must be boolean or None')
        if type(self.advisory) is not bool:
            raise ValueError('advisory must be boolean')
        _tuple('measures',self.measures,MarriageMeasure,8192)
        _tuple('exceptions',self.exceptions,MarriageException,32)
        _tuple('unavailable_reasons',self.unavailable_reasons,str,128)
        if any(self.rule_id not in x.targets for x in self.exceptions):
            raise ValueError('attached exception must target this finding')

    @property
    def effective_restriction(self):
        if self.applicable is False or self.advisory or self.detected is False:
            return False
        if self.applicable is None or self.detected is None:
            return None
        return not any(e.satisfied is True and self.rule_id in e.targets for e in self.exceptions)

    @property
    def coverage_complete(self):
        return self.advisory or self.applicable is False or (self.applicable is True and self.detected is not None
            and not self.unavailable_reasons and all(e.satisfied is not None for e in self.exceptions))


@dataclass(frozen=True, slots=True)
class MarriageDecision:
    """Aggregate selected-profile status retaining coverage and detected restrictions separately."""
    status: str
    coverage_complete: bool
    effective_restriction_ids: tuple[str, ...]
    unresolved_rule_ids: tuple[str, ...]

    def __post_init__(self):
        _choice('status', self.status, ('not_requested', 'restricted', 'indeterminate', 'passes_selected_profile'))
        if type(self.coverage_complete) is not bool:
            raise ValueError('coverage_complete must be boolean')
        for name in ('effective_restriction_ids', 'unresolved_rule_ids'):
            values = getattr(self, name)
            _tuple(name, values, str, 2048)
            if len(set(values)) != len(values) or any(not x for x in values):
                raise ValueError('decision references must be unique nonempty rule identifiers')
        if self.status == 'not_requested':
            if self.coverage_complete or self.effective_restriction_ids or self.unresolved_rule_ids:
                raise ValueError('unrequested layer cannot claim coverage or findings')
            return
        expected = ('restricted' if self.effective_restriction_ids else
                    'indeterminate' if self.unresolved_rule_ids else 'passes_selected_profile')
        if self.status != expected or self.coverage_complete != (not self.unresolved_rule_ids):
            raise ValueError('decision contradicts its restriction or unresolved references')


def _decision(findings, requested=True):
    if not requested:
        return MarriageDecision('not_requested', False, (), ())
    bad = tuple(f.rule_id for f in findings if f.effective_restriction is True)
    missing = tuple(f.rule_id for f in findings if not f.coverage_complete)
    status = 'restricted' if bad else 'indeterminate' if missing else 'passes_selected_profile'
    return MarriageDecision(status, not missing, bad, missing)


@dataclass(frozen=True, slots=True)
class MarriageElectionAssessment:
    """Pure source assessment retaining raw, personal and composed findings and decisions."""
    policy: MarriageElectionPolicy
    evidence: MarriageElectionEvidence
    personal: MarriagePersonalContext | None
    astronomical_findings: tuple[MarriageFinding, ...]
    personal_findings: tuple[MarriageFinding, ...]
    composition_findings: tuple[MarriageFinding, ...]
    astronomical: MarriageDecision
    personal_decision: MarriageDecision
    requested_composition: MarriageDecision
    input_basis: str = 'caller_supplied_conditional_on_evidence'
    exclusions: tuple[tuple[str, str], ...] = field(init=False, default=EXCLUSIONS)

    def __post_init__(self):
        if not isinstance(self.policy, MarriageElectionPolicy) or not isinstance(self.evidence, MarriageElectionEvidence):
            raise ValueError('assessment requires typed policy and evidence')
        if self.personal is not None and not isinstance(self.personal, MarriagePersonalContext):
            raise ValueError('assessment personal context must be typed')
        for name in ('astronomical_findings', 'personal_findings', 'composition_findings'):
            rows = getattr(self, name)
            _tuple(name, rows, MarriageFinding, 2048)
            if len({f.rule_id for f in rows}) != len(rows):
                raise ValueError('each assessment layer requires unique finding identifiers')
        if self.personal is None and self.personal_findings:
            raise ValueError('unrequested personal layer cannot contain findings')
        for actual, expected in (
            (self.astronomical, _decision(self.astronomical_findings)),
            (self.personal_decision, _decision(self.personal_findings, self.personal is not None)),
            (self.requested_composition, _decision(self.composition_findings + self.personal_findings)),
        ):
            if actual != expected:
                raise ValueError('assessment decision contradicts its retained findings')
        if type(self.input_basis) is not str or not self.input_basis:
            raise ValueError('assessment requires an input basis')


def assess_marriage_election(evidence, *, policy, personal=None):
    """Evaluate the selected profile from raw supplied evidence without a reader."""
    if not isinstance(policy, MarriageElectionPolicy) or not isinstance(evidence, MarriageElectionEvidence):
        raise ValueError('typed marriage policy and evidence are required')
    if personal is not None and not isinstance(personal, MarriagePersonalContext):
        raise ValueError('personal must be MarriagePersonalContext')
    if evidence.ayanamsa_system != policy.ayanamsa_system:
        raise ValueError('evidence ayanamsa must match selected policy')
    if evidence.lunar_month is not None and evidence.lunar_month.policy.system != policy.month_system:
        raise ValueError('lunar month system must match selected policy')
    if personal is not None and any(p.ayanamsa_system != policy.ayanamsa_system for p in personal.participants):
        raise ValueError('natal and election evidence must share the selected sidereal basis')
    from ._muhurta_marriage_rules import evaluate
    astronomical, personal_findings, composition = evaluate(evidence, policy, personal)
    return MarriageElectionAssessment(policy, evidence, personal,
        astronomical, personal_findings, composition,
        _decision(astronomical), _decision(personal_findings, personal is not None),
        _decision(composition + personal_findings))


def marriage_election_catalogue():
    """Finite source manifest with explicit selected-profile admission."""
    from ._muhurta_marriage_manifest import marriage_rule_contracts,SUPPORTING_CONTRACTS,SOURCE_RECEIPT,HISTORY_COMPOSITION,REMEDY_CONTRACTS
    from ._muhurta_marriage_search import MarriageSearchLimits,SEARCH_HARD_MAXIMA,MINIMUM_PARENT_HISTORY_DAYS
    return {'ordinary_profile': ORDINARY, 'personal_profile': PERSONAL,
            'godhuli_profile': GODHULI, 'admission_status': 'source_scoped_public',
            'rules': RULES, 'remedies': REMEDIES, 'regional_traditions': REGIONS,
            'exclusions': EXCLUSIONS, 'research_variants': RESEARCH_VARIANTS,
            'rule_contracts':marriage_rule_contracts(),'supporting_contracts':SUPPORTING_CONTRACTS,
            'source_receipt':SOURCE_RECEIPT,'history_composition':HISTORY_COMPOSITION,
            'numerical_arithmetic_model':ARITHMETIC_MODEL,'remedy_contracts':REMEDY_CONTRACTS,
            'default_limits':MarriageSearchLimits(),'hard_maxima':MarriageSearchLimits(**dict(SEARCH_HARD_MAXIMA)),
            'minimum_parent_history_days':MINIMUM_PARENT_HISTORY_DAYS,
            'numerical_epoch_year_domain':(1900,2100)}


__all__ = ['MarriageElectionPolicy', 'MarriagePlanet', 'MarriageExtent', 'MarriageTimeSpan', 'MarriageSolarContext',
           'MarriageIngress', 'MarriageIngressHistory', 'MarriageStarPassage', 'MarriageStarHistory',
           'MarriageHistoricalSkySpan', 'MarriageMoon28Passage',
           'MarriageHistoricalLongitude', 'MarriageHistoricalSkyBand',
           'MarriageYogaEnding', 'MarriageElectionEvidence', 'MarriageParticipant',
           'MarriagePersonalContext', 'MarriageMeasure', 'MarriageException', 'MarriageFinding',
           'MarriageDecision', 'MarriageElectionAssessment', 'assess_marriage_election',
           'marriage_election_catalogue']
