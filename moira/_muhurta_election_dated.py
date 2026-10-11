"""Exact, bounded serving-reader transport for admitted purpose elections.

The finite family dispatch owns dependencies and transition closure. Numerical
work uses the existing request context and certificates, without importing the
marriage verdict or its remedies. Root uncertainty is returned, never sampled
away. All caches, work counters and source bindings belong to one request.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone as utc_timezone
from math import floor, ceil

from ._muhurta_election_evidence import ElectionDependencies, build_evidence
from ._muhurta_marriage_sources import SEVEN
from ._muhurta_marriage_search import (
    MarriageSearchLimits, WorkMeter, borrow_marriage_reader,
    MINIMUM_PARENT_HISTORY_DAYS,
)
from .muhurta_marriage_dated import _Context, _check_output, MarriageSearchReceipt
from .muhurta_election import ElectionEvidence, ElectionAssessment, ElectionFinding, ElectionSearchBudgetError
from .muhurta_marriage import _decision
from ._muhurta_marriage_windows import _clipped_bands
from .panchanga_shuddhi import _number, _point, ShuddhiBoundary, ShuddhiInterval
from .daily_panchanga import _resolve_timezone
from .julian import jd_from_datetime, utc_to_ut1
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from ._ephemeris_time import _EphemerisTimeBasisError
from .muhurta_search import MuhurtaResourceError, MuhurtaCoverageError


ElectionSearchLimits = MarriageSearchLimits


def _profile(family, policy, context):
    if family == 'vastu':
        from .muhurta_vastu import assess_vastu_election, _admit_context
        _admit_context(policy, context)
        return assess_vastu_election, ElectionDependencies(planets=SEVEN,
            month=policy.purpose not in ('foundation', 'return_entry'),
            apparitions=policy.purpose == 'first_entry')
    if family == 'business':
        from .muhurta_business import assess_business_election, _admit_context
        _admit_context(policy, context)
        purchase = policy.purpose == 'purchase'
        return assess_business_election, ElectionDependencies(
            planets=('Moon',) if purchase else SEVEN, lagna=not purchase, solar=not purchase)
    if family == 'travel':
        from .muhurta_travel import assess_travel_election, _admit_context
        from ._muhurta_travel_sources import KP_WEEKDAY
        _admit_context(policy, context)
        from ._muhurta_travel_mc_sources import PROFILE
        if policy.profile==PROFILE:
            return assess_travel_election,ElectionDependencies(phases=True,ingresses=True,stars=True,
                apparitions=True,apparition_planets=('Venus',))
        weekday_only = policy.profile == KP_WEEKDAY
        return assess_travel_election, ElectionDependencies(
            planets=() if weekday_only else ('Sun','Moon'), lagna=not weekday_only, solar=True)
    raise ValueError('unknown election family')


def _admit(family, dt, latitude, longitude, timezone, policy, context, limits):
    evaluator, dependencies = _profile(family, policy, context)
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('dt must be a timezone-aware civil datetime')
    roundtrip = dt.astimezone(utc_timezone.utc).astimezone(dt.tzinfo)
    if roundtrip.replace(tzinfo=None) != dt.replace(tzinfo=None) or roundtrip.fold != dt.fold:
        raise ValueError('dt is nonexistent or has an inconsistent fold')
    if not 3 <= dt.year <= 9997:
        raise ValueError('civil years must lie in [3,9997] for supporting searches')
    evaluator(ElectionEvidence(utc_to_ut1(jd_from_datetime(dt))), policy=policy, context=context)
    lat, lon = _number('latitude', latitude), _number('longitude', longitude)
    if not -90 < lat < 90 or not -180 <= lon <= 180:
        raise ValueError('latitude must be in (-90,90) and longitude in [-180,180]')
    zone = _resolve_timezone(timezone)
    active = ElectionSearchLimits() if limits is None else limits
    if not isinstance(active, ElectionSearchLimits):
        raise ValueError('limits must be ElectionSearchLimits')
    active.__post_init__()
    required_history = MINIMUM_PARENT_HISTORY_DAYS if dependencies.month else 4 if dependencies.solar or dependencies.phases else 1
    if active.max_history_days < required_history:
        raise ElectionSearchBudgetError('history_days', active.max_history_days, required_history, 'election_dependency_preflight')
    return lat, lon, zone, active, evaluator, dependencies


def admit_window(family, start, end, latitude, longitude, timezone, policy, context, limits):
    admitted = _admit(family, start, latitude, longitude, timezone, policy, context, limits)
    _admit(family, end, latitude, longitude, timezone, policy, context, admitted[3])
    lo, hi = (utc_to_ut1(jd_from_datetime(dt)) for dt in (start, end))
    if lo >= hi:
        raise ValueError('window requires start before end')
    if hi-lo > admitted[3].max_range_days:
        raise ElectionSearchBudgetError('range_days', admitted[3].max_range_days, hi-lo, 'preflight')
    return (*admitted, lo, hi)


@dataclass(frozen=True, slots=True)
class ElectionSnapshot:
    """Serving-reader instant, source-owned assessment and numerical receipt."""
    dt: datetime
    latitude: float
    longitude: float
    timezone: str
    assessment: ElectionAssessment
    kernel_label: str
    reader_binding: str
    jd_tt: float
    jd_tdb: float
    search_receipt: MarriageSearchReceipt


@dataclass(frozen=True, slots=True)
class ElectionCell:
    """Open stable interior bounded by retained transition brackets."""
    interval: ShuddhiInterval
    assessment: ElectionAssessment
    constancy_certified: bool

    def __post_init__(self):
        if not isinstance(self.interval, ShuddhiInterval) or not isinstance(self.assessment, ElectionAssessment):
            raise ValueError('cell requires a typed interval and assessment')
        if type(self.constancy_certified) is not bool:
            raise ValueError('constancy_certified must be boolean')
        if self.interval.contains(self.assessment.evidence.jd_ut1) is not True:
            raise ValueError('cell witness must lie inside its definite interval')
        if self.constancy_certified and self.assessment.input_basis != 'serving_reader_derived; conditional_numerical_model_certified':
            raise ValueError('certified cell requires an admitted numerical assessment')


@dataclass(frozen=True, slots=True)
class ElectionWindows:
    """Complete requested partition, with uncertainty bands and no gap filling."""
    start: datetime
    end: datetime
    jd_start_ut1: float
    jd_end_ut1: float
    latitude: float
    longitude: float
    timezone: str
    family: str
    policy: object
    context: object
    cells: tuple[ElectionCell, ...]
    transition_bands: tuple[ShuddhiBoundary, ...]
    kernel_label: str
    reader_binding: str
    search_receipt: MarriageSearchReceipt

    def __post_init__(self):
        _profile(self.family, self.policy, self.context)
        if type(self.cells) is not tuple or type(self.transition_bands) is not tuple:
            raise ValueError('window partition must be immutable')
        bands = self.transition_bands
        if not bands or bands[0].lower_jd_ut1 != self.jd_start_ut1 or bands[-1].upper_jd_ut1 != self.jd_end_ut1:
            raise ValueError('transition bands must cover the requested endpoints')
        if any(not isinstance(b, ShuddhiBoundary) for b in bands) or any(a.upper_jd_ut1 >= b.lower_jd_ut1 for a, b in zip(bands, bands[1:])):
            raise ValueError('transition bands must be typed, sorted and disjoint')
        pairs = tuple((a, b) for a, b in zip(bands, bands[1:]) if a.upper_jd_ut1 < b.lower_jd_ut1)
        if len(pairs) != len(self.cells):
            raise ValueError('every stable interior needs exactly one retained cell')
        for (a, b), cell in zip(pairs, self.cells):
            if not isinstance(cell, ElectionCell) or cell.interval != ShuddhiInterval(a, b):
                raise ValueError('cell partition contradicts transition bands')
            if (cell.assessment.family, cell.assessment.policy, cell.assessment.context) != (self.family, self.policy, self.context):
                raise ValueError('cell policy/context differs from its window')
            if cell.constancy_certified and self.search_receipt.crossing_completeness != 'complete_under_declared_arithmetic_model':
                raise ValueError('cell cannot outclaim its numerical receipt')

    @property
    def eligible_intervals(self):
        return tuple(c.interval for c in self.cells if c.constancy_certified and
                     c.assessment.requested_composition.status == 'passes_selected_profile')

    @property
    def indeterminate_cell_indices(self):
        return tuple(i for i, c in enumerate(self.cells) if not c.constancy_certified or
                     c.assessment.requested_composition.status == 'indeterminate')

    def at(self, jd_ut1):
        jd = _number('jd_ut1', jd_ut1)
        return next((c.assessment for c in self.cells if c.constancy_certified and c.interval.contains(jd) is True), None)


def _retain_gap(assessment, receipt, extra=()):
    if receipt.crossing_completeness == 'complete_under_declared_arithmetic_model' and not extra:
        return replace(assessment, input_basis='serving_reader_derived; conditional_numerical_model_certified')
    reasons = tuple(dict.fromkeys((*receipt.unavailable_reasons, *extra))) or ('numerical_certificate_required',)
    guard = ElectionFinding('numerical_search_completeness', 'numerical_search_completeness',
        'Moira numerical event admission', True, None, (), (), reasons)
    findings = assessment.astronomical_findings + (guard,)
    return replace(assessment, astronomical_findings=findings, astronomical=_decision(findings),
        requested_composition=_decision(findings + assessment.personal_findings),
        input_basis='serving_reader_derived; numerical_candidate_history_not_certified')


def _transitions(ctx, lo, hi, dependencies, action_context):
    """Finite admitted rule closure; full roots, not a temporal sample grid."""
    if ctx.policy.family=='travel':
        from ._muhurta_travel_mc_sources import PROFILE
        if ctx.policy.profile==PROFILE:
            from ._muhurta_marriage_windows import _candidate_boundaries
            boundaries=_candidate_boundaries(ctx,lo,hi,
                evidence_factory=lambda jd:build_evidence(ctx,jd,dependencies,ElectionEvidence),apparition_buffers=False)
            boundaries.extend(r.boundary for r in ctx.angular((('Venus',1),('Sun',-1)),lo,hi,
                (0.,180.),min(1.,hi-lo),'travel_venus_horizon_direction'))
            return boundaries
    boundaries = [_point('range_start', lo), _point('range_end', hi)]
    signs = tuple(i*30. for i in range(12))
    star27 = tuple(i*360/27 for i in range(27))
    stars = tuple(sorted(set((*star27, 830/3, 2528/9))))
    for planet in dependencies.planets:
        targets = signs
        if ctx.policy.family == 'vastu':
            if planet == 'Moon' or (planet == 'Sun' and ctx.policy.purpose == 'foundation'):
                targets = tuple(sorted(set(signs + stars)))
            elif planet == 'Sun':
                targets = tuple(sorted(set(signs + star27)))
        elif ctx.policy.family == 'business':
            if ctx.policy.purpose == 'purchase':
                targets = star27
            elif planet == 'Moon':
                targets = tuple(sorted(set(signs + star27)))
        elif ctx.policy.family == 'travel':
            targets = star27
        boundaries.extend(r.boundary for r in ctx.angular(((planet, 1),), lo, hi, targets, min(1., hi-lo), planet+'_election_transitions'))
    if dependencies.lagna:
        if ctx.lagna((lo+hi)/2) is None:
            ctx.reasons.append('lagna_domain_not_certified_for_window')
        else:
            boundaries.extend(r.boundary for r in ctx.angular((('Lagna', 1),), lo, hi, signs, min(1/24, hi-lo), 'election_lagna'))
    if {'Sun','Moon'} <= set(dependencies.planets):
        boundaries.extend(r.boundary for r in ctx.angular((('Moon', 1), ('Sun', -1)), lo, hi,
            tuple(i*12. for i in range(30)), min(1., hi-lo), 'election_tithi_and_nature'))
    if dependencies.solar:
        for day in range(floor(lo)-1, ceil(hi)+1):
            solar = ctx.solar_context(min(hi, max(lo, day+.5)))
            if solar is not None:
                boundaries.extend((solar.day.start, solar.day.end))
                if ctx.policy.family == 'travel':
                    from ._muhurta_travel_sources import KP_WEEKDAY, RELEASE_GHATIS
                    from .panchanga_shuddhi import _shift
                    if ctx.policy.profile == KP_WEEKDAY:
                        boundaries.append(_shift(solar.day.start,dict(RELEASE_GHATIS)[action_context.direction]*1440,'kp_weekday_release'))
    # Build every supporting calendar/visibility range before collecting its
    # roots. Context memoization shares only exact, semantically identical work.
    for jd in (lo, (lo+hi)/2, hi):
        if dependencies.month:
            ctx.lunar_month(jd)
        if dependencies.apparitions:
            for planet in dependencies.apparition_planets:
                ctx.apparition(planet,jd)
    for _, _, phases, ingresses in ctx.months:
        boundaries.extend(ShuddhiBoundary('calendar_'+b.kind, b.jd_ut1, b.lower_jd_ut1, b.upper_jd_ut1)
                          for b in (*phases, *ingresses))
    for events in ctx.apparition_events.values():
        boundaries.extend(e.boundary for e in events)
    return boundaries


def election_for_datetime(family, dt, latitude, longitude, *, timezone, policy, context, limits=None, reader=None):
    lat, lon, zone, active, evaluator, deps = _admit(family, dt, latitude, longitude, timezone, policy, context, limits)
    meter = WorkMeter(active, budget_error=ElectionSearchBudgetError)
    try:
        serving = get_reader() if reader is None else reader
        with borrow_marriage_reader(serving, meter) as borrowed, use_reader_override(borrowed):
            jd = utc_to_ut1(jd_from_datetime(dt))
            ctx = _Context(borrowed, meter, lat, lon, zone, timezone, policy)
            ctx.range_anchor, ctx.range_radius = jd, 0.
            evidence = build_evidence(ctx, jd, deps, ElectionEvidence)
            # Certify a small neighbourhood to expose exact boundary ambiguity
            # at an instant, independently of any historical parent certificate.
            pad = max(1., policy.solver_tolerance_seconds*4)/86400
            roots = _transitions(ctx, jd-pad, jd+pad, deps, context)
            result = evaluator(evidence, policy=policy, context=context)
            if deps.phases:
                from ._muhurta_marriage_windows import _derived_boundaries
                roots.extend(_derived_boundaries(result))
            uncertain = any(b.kind not in ('range_start', 'range_end') and b.lower_jd_ut1 <= jd <= b.upper_jd_ut1 for b in roots)
            result = _retain_gap(result, ctx.receipt(), ('instant_lies_in_transition_uncertainty',) if uncertain else ())
            epoch = ctx.epoch(jd)
            snapshot = ElectionSnapshot(dt, lat, lon, timezone, result, epoch.identity.summary_label,
                'discovered_reader' if reader is None else 'caller_owned_reader', epoch.epoch_tt, epoch.epoch_tdb, ctx.receipt())
            _check_output(snapshot, meter)
            return replace(snapshot, search_receipt=ctx.receipt())
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError('election or supporting history exceeds serving coverage') from exc
    except (MissingKernelError, _EphemerisTimeBasisError, FileNotFoundError) as exc:
        raise MuhurtaResourceError('election requires serving planetary and clock resources') from exc


def election_windows(family, start, end, latitude, longitude, *, timezone, policy, context, limits=None, reader=None):
    lat, lon, zone, active, evaluator, deps, lo, hi = admit_window(family, start, end, latitude, longitude, timezone, policy, context, limits)
    meter = WorkMeter(active, budget_error=ElectionSearchBudgetError)
    try:
        serving = get_reader() if reader is None else reader
        with borrow_marriage_reader(serving, meter) as borrowed, use_reader_override(borrowed):
            ctx = _Context(borrowed, meter, lat, lon, zone, timezone, policy)
            ctx.range_anchor, ctx.range_radius = (lo+hi)/2, (hi-lo)/2
            boundaries=_transitions(ctx, lo, hi, deps, context)
            if deps.phases:
                from ._muhurta_marriage_windows import _derived_boundaries
                initial=_clipped_bands(boundaries,lo,hi)
                for a,b in zip(initial,initial[1:]):
                    if a.upper_jd_ut1>=b.lower_jd_ut1:
                        continue
                    sample=(a.upper_jd_ut1+b.lower_jd_ut1)/2
                    assessment=evaluator(build_evidence(ctx,sample,deps,ElectionEvidence),policy=policy,context=context)
                    boundaries.extend(_derived_boundaries(assessment))
            bands = _clipped_bands(boundaries, lo, hi)
            ctx.certifier.maximum_boundary_width_seconds = max(ctx.certifier.maximum_boundary_width_seconds,
                max((b.upper_jd_ut1-b.lower_jd_ut1)*86400 for b in bands))
            pending = []
            for a, b in zip(bands, bands[1:]):
                if a.upper_jd_ut1 >= b.lower_jd_ut1:
                    continue
                meter.tick('cells')
                evidence = build_evidence(ctx, (a.upper_jd_ut1+b.lower_jd_ut1)/2, deps, ElectionEvidence)
                assessment = evaluator(evidence, policy=policy, context=context)
                _check_output(assessment, meter, additional=True)
                pending.append((ShuddhiInterval(a, b), assessment))
            receipt = ctx.receipt()
            certified = receipt.crossing_completeness == 'complete_under_declared_arithmetic_model'
            cells = tuple(ElectionCell(interval, _retain_gap(assessment, receipt), certified) for interval, assessment in pending)
            epoch = ctx.epoch((lo+hi)/2)
            result = ElectionWindows(start, end, lo, hi, lat, lon, timezone, family, policy, context, cells, bands,
                epoch.identity.summary_label, 'discovered_reader' if reader is None else 'caller_owned_reader', receipt)
            _check_output(result, meter)
            return replace(result, search_receipt=ctx.receipt())
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError('election range or supporting history exceeds serving coverage') from exc
    except (MissingKernelError, _EphemerisTimeBasisError, FileNotFoundError) as exc:
        raise MuhurtaResourceError('election requires serving planetary and clock resources') from exc
