"""Public immutable contracts for explicitly bounded eclipse evidence.

These opt-in products retain their model, time scale, exact rational bounds,
source identity, unresolved domains and budgets. They do not replace legacy
event shapes or certify a nearest-event search, physical accuracy or a NASA
solar model. Imports of the computational adapters remain request-local.
"""
from __future__ import annotations

from dataclasses import dataclass,asdict
from fractions import Fraction
import math
from typing import Literal

from ._eclipse_interval import RationalInterval as I

EvidenceState = Literal['proved','bounded','evaluated_zero','not_applicable','not_computed',
                        'unsupported','unresolved','error']


@dataclass(frozen=True, slots=True)
class RationalBound:
    """Exact rational endpoints plus outward binary64 display endpoints."""

    lower_exact: str
    upper_exact: str
    lower: float
    upper: float

    def __post_init__(self):
        lo,hi = Fraction(self.lower_exact),Fraction(self.upper_exact)
        if lo > hi or not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError('finite ordered interval display required')
        if Fraction.from_float(float(self.lower)) > lo or Fraction.from_float(float(self.upper)) < hi:
            raise ValueError('display endpoints must enclose the exact rational endpoints')

    @classmethod
    def from_interval(cls,value):
        value = I.point(value)
        lo,hi = value.to_float_bounds()
        return cls(str(value.lo),str(value.hi),lo,hi)


@dataclass(frozen=True, slots=True)
class EvidenceTimeDomain:
    """Closed offsets from an exact represented epoch in the stated scale."""

    time_scale: Literal['UT1','TT']
    anchor_jd: float
    offset_days: RationalBound


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """Frozen ephemeris/data identities with their guarantee kept explicit."""

    model_id: str
    kernel_name: str | None = None
    kernel_sha256: str | None = None
    record_word_sha256: tuple[str,...] = ()
    table_sha256: tuple[str,...] = ()
    raw_record_words_verified: bool = False
    native_execution_certified: bool = False
    physical_accuracy_certified: bool = False
    kernel_identity_scope: str = 'reader_open_content_identity'
    live_kernel_lifetime_attested: bool = False
    reader_route: str = 'direct_input'
    pool_generation: int | None = None
    arithmetic: str = 'exact_rational_bounds_with_finite_outward_quantization'
    model_definition_version: str = 'stages3_5_reference_v1'
    clock_policy: str | None = None
    source_domain: EvidenceTimeDomain | None = None
    tt_offset_days_from_anchor: RationalBound | None = None


@dataclass(frozen=True, slots=True)
class EvidenceBudget:
    """Product work counters; initialization is disclosed separately."""

    limit: int
    used: int | None
    unit: str
    exhausted: bool = False
    wall_seconds_limit: float | None = None

    def __post_init__(self):
        if type(self.limit) is not int or self.limit < 0 or (self.used is not None and
                (type(self.used) is not int or not 0 <= self.used <= self.limit)):
            raise ValueError('finite counters must remain within the declared product allocation')


@dataclass(frozen=True, slots=True)
class EvidenceQuantity:
    """A named bounded quantity with explicit units; zero is retained."""

    name: str
    unit: str
    bound: RationalBound | None
    state: Literal['bounded','not_computed'] = 'bounded'

    def __post_init__(self):
        if (self.bound is None) != (self.state == 'not_computed'):
            raise ValueError('uncomputed and numeric-zero quantities must remain distinct')


@dataclass(frozen=True, slots=True)
class EvidenceSurfaceRegion:
    """A closed, pole-safe signed cube-face rectangle on zero-elevation WGS84."""

    axis: int
    sign: int
    u: RationalBound
    v: RationalBound


@dataclass(frozen=True, slots=True)
class EvidenceCell:
    """One retained time/surface domain and its independent proof state."""

    domain: RationalBound
    state: str
    cause: str
    surface: EvidenceSurfaceRegion | None = None
    quantities: tuple[EvidenceQuantity,...] = ()
    common_time: RationalBound | None = None
    partition: str | None = None
    coordinate: str = 'time_offset_days'
    time_evidence: tuple[EvidenceCell,...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceWitness:
    """A strict point/common-time witness; no temporal-complement inference."""

    time_offset_days: RationalBound
    surface: EvidenceSurfaceRegion | None
    quantities: tuple[EvidenceQuantity,...]


@dataclass(frozen=True, slots=True)
class EvidenceVertex:
    """Shared algebraic junction identity and exact constraint signs."""

    key: str
    forward: int | None
    horizon: int | None
    nappe: int | None
    tags: tuple[str,...]
    parameter_root_polynomial: tuple[str,...] = ()
    parameter_root_interval: RationalBound | None = None
    generator_chart: int | None = None


@dataclass(frozen=True, slots=True)
class EvidenceArc:
    """One complete open generator/circle cell, with explicit endpoint IDs."""

    family: str
    chart: int
    start: str
    end: str
    parameter_hull: RationalBound | None
    labels: tuple[tuple[str,str],...]


@dataclass(frozen=True, slots=True)
class EvidenceTopology:
    """Constraint arrangement completeness, not counts of filled surface regions."""

    vertices: tuple[EvidenceVertex,...]
    arcs: tuple[EvidenceArc,...]
    clipped_cone_components: int
    complete: bool
    scope: str = 'exact_real_affine_family_of_frozen_coefficients'


@dataclass(frozen=True, slots=True)
class EvidenceLimit:
    """A time-stamped section-limit band, with no invented root uniqueness."""

    side: str
    parameter: RationalBound
    xyz_itrf_km: tuple[RationalBound,...]
    unique_root_proved: bool = False


@dataclass(frozen=True, slots=True)
class EclipseProductEvidence:
    """Independent product outcome; unavailable states never carry a value."""

    product: str
    state: EvidenceState
    cause: str
    domain: EvidenceTimeDomain
    source: EvidenceSource
    budget: EvidenceBudget
    coverage_complete: bool = False
    values: tuple[EvidenceQuantity,...] = ()
    cells: tuple[EvidenceCell,...] = ()
    witnesses: tuple[EvidenceWitness,...] = ()
    sequence: tuple[str,...] = ()
    subtype: str | None = None
    topology: EvidenceTopology | None = None
    metric: str | None = None
    precision_met: bool | None = None
    horizon_policy: str = 'explicit_in_model_id'
    notes: tuple[str,...] = ()
    limits: tuple[EvidenceLimit,...] = ()
    components: tuple[tuple[RationalBound,RationalBound],...] = ()
    event_interval_enclosed: bool | None = None
    full_surface_domain_retained: bool | None = None

    def __post_init__(self):
        if self.state not in ('proved','bounded','evaluated_zero','not_applicable','not_computed',
                              'unsupported','unresolved','error'):
            raise ValueError('unknown evidence state')
        if self.state in ('not_applicable','not_computed','unsupported','error') and (
                self.values or self.witnesses or self.coverage_complete):
            raise ValueError('unavailable product cannot contain a numeric result or completeness proof')
        if self.state == 'evaluated_zero' and not self.coverage_complete:
            raise ValueError('evaluated zero requires complete complementary exclusion')


@dataclass(frozen=True, slots=True)
class EclipseEvidence:
    """One immutable, deterministic evidence bundle on an explicit domain."""

    family: Literal['solar','lunar']
    domain: EvidenceTimeDomain
    products: tuple[EclipseProductEvidence,...]
    preparation: tuple[tuple[str,int],...] = ()
    contract_version: str = 'moira.eclipse-evidence.v1'
    nearest_event_certified: bool = False
    configuration: tuple[EvidenceQuantity,...] = ()


def serialize_eclipse_evidence(value: EclipseEvidence) -> dict:
    """Project frozen contracts into JSON without discarding exact bounds."""
    if not isinstance(value,EclipseEvidence):
        raise TypeError('EclipseEvidence required')
    return asdict(value)


def _request(epoch,offset_days,products,allowed,max_evaluations,tolerance_seconds):
    if isinstance(epoch,bool) or not isinstance(epoch,(int,float)) or not math.isfinite(epoch):
        raise ValueError('finite represented Julian-day anchor required')
    if len(offset_days) != 2:
        raise ValueError('two ordered closed offsets required')
    domain = I(*offset_days)
    if not domain.contains(0):
        raise ValueError('domain must include the reference epoch at offset zero')
    if not products or len(set(products)) != len(products) or any(p not in allowed for p in products):
        raise ValueError('unique supported products must be explicitly selected')
    if type(max_evaluations) is not int or not 0 <= max_evaluations <= 4096:
        raise ValueError('product evaluation budget must be from 0 to 4096')
    tolerance = I.point(tolerance_seconds)
    if tolerance.width or not Fraction(1,1000) <= tolerance.lo <= 86400:
        raise ValueError('time tolerance must be from 0.001 to 86400 seconds')
    return float(epoch),domain,tolerance.lo/86400


def inspect_solar_evidence(jd_ut1, *, reader,offset_days=(-1/6,1/6),
                           products=('geographic_width',),max_evaluations=256,
                           tolerance_seconds=.1,width_tolerance_km=1.):
    """Compute opt-in bounded solar products without selecting a later event.

    Evaluation budgets are per selected product. Deterministic work limits
    are used; elapsed time is benchmark telemetry rather than evidence.
    Source preparation counters are separate. Width/topology are instantaneous;
    occurrence, path and swept-region products retain the requested interval.
    """
    epoch,domain,tolerance = _request(jd_ut1,offset_days,products,
        ('occurrence','central_path','surface_topology','swept_region','geographic_width'),
        max_evaluations,tolerance_seconds)
    if domain.width > 1:
        raise ValueError('solar bounded-evidence interval cannot exceed one day')
    width = I.point(width_tolerance_km)
    if width.width or not 0 < width.lo <= 100:
        raise ValueError('positive width tolerance at most 100 km required')
    from ._eclipse_evidence_solar import compute_solar_evidence
    from ._eclipse_evidence_common import borrow_evidence_reader,annotate_pool,reader_admission_failure
    from ._eclipse_interval_roots import EnclosureUnavailable
    try:
        if max_evaluations == 0:
            return compute_solar_evidence(reader,epoch,domain,tuple(products),max_evaluations,tolerance,width.lo)
        with borrow_evidence_reader(reader) as (resolved,pooled):
            return annotate_pool(compute_solar_evidence(resolved,epoch,domain,tuple(products),
                max_evaluations,tolerance,width.lo),pooled)
    except EnclosureUnavailable as exc:
        return reader_admission_failure(compute_solar_evidence(None,epoch,domain,tuple(products),
            max_evaluations,tolerance,width.lo),products,exc)


def inspect_lunar_evidence(jd_tt, *, reader,offset_days=(-1/6,1/6),policy='danjon_angular',
                           earth_radius_scale=1.,products=('occurrence','contacts'),
                           max_evaluations=256,tolerance_seconds=.1):
    """Compute selected geometric-Moon reference products on an explicit TT domain.

    These policies are not aliases for the legacy native or apparent-Moon
    NASA-canon routes. Their model identifiers, source and assumptions remain
    explicit; canon/native legacy selection is preserved independently.
    """
    epoch,domain,tolerance = _request(jd_tt,offset_days,products,
        ('occurrence','contacts','extrema'),max_evaluations,tolerance_seconds)
    scale = I.point(earth_radius_scale)
    if domain.width > 34 or scale.width or not 0 < scale.lo <= 10:
        raise ValueError('lunar domain <=34 days and scale in (0,10] required')
    if policy not in ('danjon_angular','static_finite_cone') or (policy == 'danjon_angular' and scale.lo != 1):
        raise ValueError('explicit lunar policy required; scale applies only to static_finite_cone')
    from ._eclipse_evidence_lunar import compute_lunar_evidence
    from ._eclipse_evidence_common import borrow_evidence_reader,annotate_pool,reader_admission_failure
    from ._eclipse_interval_roots import EnclosureUnavailable
    try:
        if max_evaluations == 0:
            return compute_lunar_evidence(reader,epoch,domain,policy,float(scale.lo),tuple(products),max_evaluations,tolerance)
        with borrow_evidence_reader(reader) as (resolved,pooled):
            return annotate_pool(compute_lunar_evidence(resolved,epoch,domain,policy,float(scale.lo),
                tuple(products),max_evaluations,tolerance),pooled)
    except EnclosureUnavailable as exc:
        return reader_admission_failure(compute_lunar_evidence(None,epoch,domain,policy,float(scale.lo),
            tuple(products),max_evaluations,tolerance),products,exc)
