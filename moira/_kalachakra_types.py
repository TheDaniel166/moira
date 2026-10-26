"""Bounded Kalachakra input and result vessels; exact source intervals are sovereign."""
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
import math

from .kalachakra_policy import CLOCKS, PROFILE_IDS, VERSION, RULE_IDS, CONFLICT_IDS, WEIGHTS, RULERS, GROUPS
from ._kalachakra_recipes import recipe_for_row, source_row, advance, window_total, birth_window


class KalachakraInputError(ValueError):
    """Caller supplied an invalid or incompatible Kalachakra input."""


class KalachakraProjectionError(ValueError):
    """Positive source intervals cannot be represented at the requested JD origin."""

    def __init__(self, message, *, path=None):
        super().__init__(message)
        self.path = path


class KalachakraCoverageError(ValueError):
    """A valid astronomical epoch is outside serving resource coverage."""


class KalachakraResourceError(RuntimeError):
    """Required ephemeris, lunar time identity or live anchor is unavailable."""


class KalachakraInvariantError(RuntimeError):
    """A generated result violates its contract after caller admission."""


def number(value, name):
    if type(value) not in (int, float):
        raise KalachakraInputError(f"{name} must be a finite number, not a boolean or string")
    try:
        result = float(value)
    except OverflowError as exc:
        raise KalachakraInputError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise KalachakraInputError(f"{name} must be finite")
    return result


def angle(value, name="moon_longitude"):
    value = number(value,name)
    if not 0 <= value < 360:
        raise KalachakraInputError(f"{name} must be in [0,360)")
    return value


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise KalachakraInputError(f"{name} must be an integer in [{low},{high}]")
    return value


def ratio(value):
    if type(value) is not Fraction or any(len(str(abs(n))) > 400 for n in (value.numerator,value.denominator)):
        raise KalachakraInputError("source years require an exact ratio bounded to 400 digits")


def named_ayanamsa(value):
    from .sidereal import Ayanamsa
    if type(value) is not str or value not in Ayanamsa.ALL:
        raise KalachakraInputError("ayanamsa_system must be a named Moira ayanamsa")
    return value


def admitted_row(row_id):
    try:
        return recipe_for_row(row_id)
    except ValueError as exc:
        raise KalachakraInputError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class KalachakraEpoch:
    """An aware civil instant or a finite UTC-derived Julian date."""
    kind: str
    value: datetime | float

    def __post_init__(self):
        if self.kind == "datetime" and type(self.kind) is str:
            if not isinstance(self.value,datetime) or self.value.tzinfo is None or self.value.utcoffset() is None:
                raise KalachakraInputError("epoch datetime must be timezone-aware")
            try:
                object.__setattr__(self,"value",self.value.astimezone(timezone.utc))
            except (OverflowError,ValueError) as exc:
                raise KalachakraInputError("epoch datetime cannot normalize to UTC") from exc
        elif self.kind == "jd_utc" and type(self.kind) is str:
            object.__setattr__(self,"value",number(self.value,"jd_utc"))
        else:
            raise KalachakraInputError("epoch kind must be datetime or jd_utc")


def epoch_jd(epoch):
    if type(epoch) is not KalachakraEpoch:
        raise KalachakraInputError("birth/query epoch must be KalachakraEpoch")
    normalized = KalachakraEpoch(epoch.kind,epoch.value)
    if normalized.kind == "jd_utc":
        return normalized.value
    from .julian import jd_from_datetime
    return number(jd_from_datetime(normalized.value),"jd_utc")


def astronomical_epoch(epoch):
    jd = epoch_jd(epoch)
    if not -10000000 <= jd <= 10000000:
        raise KalachakraInputError("astronomical epoch must be in JD [-10000000,10000000]")
    return jd


@dataclass(frozen=True, slots=True)
class KalachakraSeed:
    """Tagged supplied longitude; tropical seeds require a named ayanamsa."""
    basis: str
    moon_longitude: float
    ayanamsa_system: str | None = None

    def __post_init__(self):
        object.__setattr__(self,"moon_longitude",angle(self.moon_longitude))
        if type(self.basis) is not str or self.basis not in ("sidereal","tropical"):
            raise KalachakraInputError("seed basis must be sidereal or tropical")
        if self.basis == "tropical":
            named_ayanamsa(self.ayanamsa_system)
        elif self.ayanamsa_system is not None:
            raise KalachakraInputError("supplied sidereal seed cannot claim an ayanamsa")


@dataclass(frozen=True, slots=True)
class KalachakraProjection:
    """Explicit fixed-day engineering clock, without an implicit default."""
    year_basis: str

    def __post_init__(self):
        if type(self.year_basis) is not str or self.year_basis not in CLOCKS:
            raise KalachakraInputError("year_basis must be savana_360 or julian_365.25")


@dataclass(frozen=True, slots=True)
class KalachakraSourceSpan:
    """Positive exact half-open source-year interval relative to birth."""
    start: Fraction
    end: Fraction

    def __post_init__(self):
        ratio(self.start)
        ratio(self.end)
        if self.start >= self.end:
            raise KalachakraInputError("source span must have positive duration")


@dataclass(frozen=True, slots=True)
class KalachakraDateSpan:
    """Representable positive half-open interval on the UTC-derived JD axis."""
    start_jd_utc: float
    end_jd_utc: float

    def __post_init__(self):
        for name in ("start_jd_utc","end_jd_utc"):
            object.__setattr__(self,name,number(getattr(self,name),name))
        if self.start_jd_utc >= self.end_jd_utc:
            raise KalachakraProjectionError("positive interval collapses at requested JD origin")


@dataclass(frozen=True, slots=True)
class KalachakraAstronomy:
    """Bound reader/time/frame receipt; supplied tropical inputs do not derive Moon."""
    jd_ut1: float
    jd_tt: float
    jd_tdb: float
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
    delta_t_source: str
    ephemeris_identity: str
    planetary_ephemeris: str
    lunar_ephemeris: str
    lunar_tidal_acceleration: float
    ayanamsa_system: str
    ayanamsa_offset: float
    anchor: str | None
    longitude_frame: str = "true_ecliptic_of_date"
    longitude_origin: str = "apparent_geocentric"
    ayanamsa_mode: str = "true"
    corrections: tuple[str,...] = ("light_time","aberration","gravitational_deflection","nutation")


@dataclass(frozen=True, slots=True)
class KalachakraProvenance:
    """Supplied/derived origin and separately identified schedule/astronomy epochs."""
    input_origin: str
    moon_sidereal_lon: float
    birth_jd_utc: float | None = None
    normalized_datetime_utc: str | None = None
    moon_tropical_lon: float | None = None
    astronomy: KalachakraAstronomy | None = None

    def __post_init__(self):
        from .kalachakra import _validate_provenance
        _validate_provenance(self)


@dataclass(frozen=True, slots=True)
class KalachakraBirth:
    """Exact seed classification, independent row totals and birth balance."""
    nakshatra_number: int
    pada_number: int
    group: str
    row_id: str
    row_signs: tuple[int,...]
    fraction_in_pada: Fraction
    row_total_years: int
    elapsed_row_years: Fraction
    natal_row_remaining_years: Fraction
    birth_row_position: int
    birth_md_full_years: int
    birth_md_remaining_years: Fraction
    coverage_years: Fraction
    deha_sign_index: int
    jeeva_sign_index: int
    deha_jeeva_reference: str = "natal_row"

    def __post_init__(self):
        integer(self.nakshatra_number,"nakshatra_number",1,27)
        integer(self.pada_number,"pada_number",1,4)
        integer(self.birth_row_position,"birth_row_position",0,8)
        recipe = admitted_row(self.row_id)
        group = next(g for g,ns in GROUPS.items() if self.nakshatra_number in ns)
        row_id = f"{recipe.namespace}{group}/{self.pada_number}"
        row = source_row(row_id)
        total = sum(WEIGHTS[s] for s in row)
        for name in ("fraction_in_pada","elapsed_row_years","natal_row_remaining_years",
                     "birth_md_remaining_years","coverage_years"):
            ratio(getattr(self,name))
        if not 0 <= self.fraction_in_pada < 1:
            raise KalachakraInputError("fraction_in_pada must be in [0,1)")
        i = self.birth_row_position
        cumulative = sum(WEIGHTS[s] for s in row[:i])
        weight = WEIGHTS[row[i]]
        elapsed = self.fraction_in_pada*total
        full_coverage,deha,jeeva,reference = birth_window(row_id,i)
        from .kalachakra import _strict_equal
        actual = (self.group,self.row_id,self.row_signs,self.row_total_years,self.elapsed_row_years,
            self.natal_row_remaining_years,self.birth_md_full_years,self.birth_md_remaining_years,
            self.coverage_years,self.deha_sign_index,self.jeeva_sign_index,self.deha_jeeva_reference)
        expected = (group,row_id,row,total,elapsed,total-elapsed,weight,Fraction(cumulative+weight)-elapsed,
            Fraction(full_coverage+cumulative)-elapsed,deha,jeeva,reference)
        if not cumulative <= elapsed < cumulative+weight or not _strict_equal(actual,expected):
            raise KalachakraInputError("inconsistent birth classification or source balance")


@dataclass(frozen=True, slots=True)
class KalachakraPeriod:
    """One occurrence, retaining its full source axis and nullable visible intersection."""
    path: tuple[int,...]
    parent_path: tuple[int,...] | None
    row_id: str
    row_position: int
    md_cycle_index: int
    sign_index: int
    ruler: str
    parent_weight: int
    weight: int
    denominator: int
    full_years: KalachakraSourceSpan
    visible_years: KalachakraSourceSpan | None
    full_dates: KalachakraDateSpan | None
    visible_dates: KalachakraDateSpan | None
    visibility: str
    children_status: str
    children: tuple["KalachakraPeriod", ...]

    def __post_init__(self):
        if type(self.path) is not tuple or len(self.path) not in (1,2):
            raise KalachakraInputError("period path requires one or two occurrence ordinals")
        for item in self.path:
            integer(item,"path ordinal",0,8)
        integer(self.row_position,"row_position",0,8)
        integer(self.md_cycle_index,"md_cycle_index",0,1)
        integer(self.sign_index,"sign_index",0,11)
        integer(self.parent_weight,"parent_weight",1,21)
        integer(self.weight,"weight",4,21)
        integer(self.denominator,"denominator",1,189)
        admitted_row(self.row_id)
        if source_row(self.row_id)[self.row_position] != self.sign_index:
            raise KalachakraInputError("period sign/row identity mismatch")
        if self.ruler != RULERS[self.sign_index] or self.weight != WEIGHTS[self.sign_index]:
            raise KalachakraInputError("period ruler/weight mismatch")
        if type(self.full_years) is not KalachakraSourceSpan:
            raise KalachakraInputError("period requires a full exact interval")
        self.full_years.__post_init__()
        if self.full_years.end-self.full_years.start != Fraction(self.parent_weight*self.weight,self.denominator):
            raise KalachakraInputError("full interval disagrees with source weights")
        if self.visible_years is None:
            if self.full_years.end > 0 or self.visibility != "clipped_before_birth" or len(self.path) != 2:
                raise KalachakraInputError("only wholly pre-birth ADs have null visibility")
        else:
            if type(self.visible_years) is not KalachakraSourceSpan:
                raise KalachakraInputError("invalid visible source span")
            self.visible_years.__post_init__()
            if (self.visible_years.start,self.visible_years.end,self.visibility) != (max(Fraction(0),self.full_years.start),self.full_years.end,"visible"):
                raise KalachakraInputError("invalid birth intersection")
        if self.full_dates is None:
            if self.visible_dates is not None:
                raise KalachakraInputError("visible projection requires full projection")
        else:
            if type(self.full_dates) is not KalachakraDateSpan:
                raise KalachakraInputError("invalid full date interval")
            self.full_dates.__post_init__()
            if self.visible_years is None:
                if self.visible_dates is not None:
                    raise KalachakraInputError("clipped AD cannot have visible dates")
            else:
                if type(self.visible_dates) is not KalachakraDateSpan:
                    raise KalachakraInputError("visible source span requires visible dates")
                self.visible_dates.__post_init__()
                if not self.full_dates.start_jd_utc <= self.visible_dates.start_jd_utc < self.visible_dates.end_jd_utc == self.full_dates.end_jd_utc:
                    raise KalachakraInputError("invalid projected containment")
        if type(self.children) is not tuple:
            raise KalachakraInputError("period children must be immutable")
        if len(self.path)==2:
            expected_parent = self.path[:1]
            if self.children or self.children_status != "maximum_depth" or self.parent_path != expected_parent:
                raise KalachakraInputError("invalid AD parent/depth")
            parent_row,parent_pos,_ = advance(self.row_id,self.row_position,-self.path[1])
            if (self.denominator,self.parent_weight) != (
                window_total(parent_row,parent_pos),WEIGHTS[source_row(parent_row)[parent_pos]]):
                raise KalachakraInputError("AD weights must match its profile-owned parent window")
        elif self.parent_path is not None or self.parent_weight != 1 or self.denominator != 1:
            raise KalachakraInputError("invalid MD parent/weights")
        elif self.children_status == "not_requested":
            if self.children:
                raise KalachakraInputError("unrequested ADs must be absent")
        elif self.children_status != "generated" or len(self.children)!=9:
            raise KalachakraInputError("generated MD requires nine full ADs")
        else:
            cursor = self.full_years.start
            for ordinal,child in enumerate(self.children):
                if type(child) is not KalachakraPeriod or child.path != self.path+(ordinal,) or child.children:
                    raise KalachakraInputError("invalid child identity or depth")
                child.__post_init__()
                child_row,child_pos,_ = advance(self.row_id,self.row_position,ordinal)
                if (child.full_years.start,child.row_id,child.row_position,child.md_cycle_index,child.parent_weight) != (
                    cursor,child_row,child_pos,self.md_cycle_index,self.weight):
                    raise KalachakraInputError("invalid child partition or rotation")
                cursor = child.full_years.end
            if cursor != self.full_years.end:
                raise KalachakraInputError("AD partition must conserve full parent")


@dataclass(frozen=True, slots=True)
class KalachakraTransition:
    """Ordered full-period edge; interpretation is deliberately source-bounded."""
    source_path: tuple[int,...]
    destination_path: tuple[int,...]
    source_sign_index: int
    destination_sign_index: int
    source_row_position: int
    destination_row_position: int
    level: int
    boundary_years: Fraction
    boundary_jd_utc: float | None
    row_seam: bool
    visible: bool
    classification_status: str
    classification: str | None
    conflict_ids: tuple[str,...]
    rule_id: str = "KC_GATI"


@dataclass(frozen=True, slots=True)
class KalachakraProjectionReceipt:
    """Fixed-day schedule clock and UTC-derived origin, separate from astronomy."""
    birth_jd_utc: float
    year_basis: str
    year_days: Fraction
    schedule_axis: str = "jd_utc"

    def __post_init__(self):
        number(self.birth_jd_utc,"birth_jd_utc")
        KalachakraProjection(self.year_basis)
        ratio(self.year_days)
        if self.year_days != CLOCKS[self.year_basis] or self.schedule_axis != "jd_utc":
            raise KalachakraInputError("inconsistent calendar clock receipt")


@dataclass(frozen=True, slots=True)
class KalachakraSequence:
    """Deeply validated nine-occurrence source schedule, optionally projected."""
    profile_id: str
    levels: int
    birth: KalachakraBirth
    provenance: KalachakraProvenance
    periods: tuple[KalachakraPeriod,...]
    transitions: tuple[KalachakraTransition,...]
    coverage: KalachakraSourceSpan
    coverage_dates: KalachakraDateSpan | None
    projection: KalachakraProjectionReceipt | None
    generated_node_count: int
    visible_node_count: int
    projection_status: str
    profile_version: str = VERSION
    source_ids: tuple[str,...] = ("L01","L02","L09","L11")
    rule_ids: tuple[str,...] = RULE_IDS
    conflict_ids: tuple[str,...] = CONFLICT_IDS
    eligibility_status: str = "not_evaluated"

    def __post_init__(self):
        from .kalachakra import _validate_sequence
        _validate_sequence(self)


@dataclass(frozen=True, slots=True)
class KalachakraActivePeriod:
    """An active occurrence without duplicating its subtree in the response."""
    path: tuple[int,...]
    sign_index: int
    full_years: KalachakraSourceSpan
    visible_years: KalachakraSourceSpan
    full_dates: KalachakraDateSpan
    visible_dates: KalachakraDateSpan


@dataclass(frozen=True, slots=True)
class KalachakraCurrent:
    """Bounded active line or explicit before-birth/after-coverage result."""
    profile_id: str
    profile_version: str
    levels: int
    birth: KalachakraBirth
    provenance: KalachakraProvenance
    projection: KalachakraProjectionReceipt
    coverage: KalachakraSourceSpan
    coverage_dates: KalachakraDateSpan
    query_jd_utc: float
    status: str
    active_line: tuple[KalachakraActivePeriod,...]
    source_ids: tuple[str,...]
    rule_ids: tuple[str,...]
    conflict_ids: tuple[str,...]
    eligibility_status: str = "not_evaluated"

    def __post_init__(self):
        from .kalachakra import _validate_current
        _validate_current(self)


def admit(profile_id, levels, seed=None, birth_epoch=None, projection=None):
    if type(profile_id) is not str or profile_id not in PROFILE_IDS:
        raise KalachakraInputError("unsupported Kalachakra profile_id")
    integer(levels,"levels",1,2)
    if seed is not None:
        if type(seed) is not KalachakraSeed:
            raise KalachakraInputError("seed must be KalachakraSeed")
        KalachakraSeed(seed.basis,seed.moon_longitude,seed.ayanamsa_system)
    if projection is not None:
        if type(projection) is not KalachakraProjection:
            raise KalachakraInputError("projection must be KalachakraProjection")
        KalachakraProjection(projection.year_basis)
    jd = epoch_jd(birth_epoch) if birth_epoch is not None else None
    if (projection is not None or (seed is not None and seed.basis == "tropical")) and jd is None:
        raise KalachakraInputError("projection and tropical seeds require birth_epoch")
    if seed is not None and seed.basis == "tropical":
        astronomical_epoch(birth_epoch)
    if seed is not None and seed.basis == "sidereal" and projection is None and birth_epoch is not None:
        raise KalachakraInputError("sidereal source-only requests omit birth_epoch")
    return jd
