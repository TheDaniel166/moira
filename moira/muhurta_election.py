"""Shared, source-neutral vessels for purpose-specific election assessments.

Raw astronomy retains the already admitted immutable evidence contract. A
family supplies its own policy, context and rule manifest; no shared score or
cross-tradition cancellation is inferred. Direct inputs are conditional claims,
not certificates that a reader search has been executed.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

from .muhurta_marriage import (
    MarriageElectionEvidence, MarriagePlanet, MarriageFinding, MarriageMeasure,
    MarriageException, MarriageDecision, _decision, _choice, _tuple,
)
from .panchanga_shuddhi import _number, _longitude, _sector
from .muhurta_lagna import _and as _and, _or as _or
from ._muhurta_marriage_search import MarriageSearchBudgetError


class ElectionSearchBudgetError(MarriageSearchBudgetError):
    """Canonical work limit for a purpose election, without a partial success."""
    def __init__(self, kind, limit, count, stage):
        super().__init__(kind, limit, count, stage)
        self.args = (f'election {kind} budget exceeded at {stage}: {count} > {limit}',)


ElectionPlanet = MarriagePlanet
ElectionFinding = MarriageFinding
ElectionMeasure = MarriageMeasure
ElectionException = MarriageException
ElectionDecision = MarriageDecision


@dataclass(frozen=True, slots=True)
class ElectionEvidence(MarriageElectionEvidence):
    """Same-epoch astronomical components, independently of an elected purpose."""


@dataclass(frozen=True, slots=True)
class ElectionParticipant:
    """Declared natal evidence for one named actor; no partner is inferred."""
    participant_id: str
    natal_moon_sidereal_longitude: float | None = None
    natal_lagna_sidereal_longitude: float | None = None
    natal_jd_ut1: float | None = None
    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self):
        if type(self.participant_id) is not str or not self.participant_id.strip() or len(self.participant_id) > 120:
            raise ValueError('participant_id must be a nonempty label of at most 120 characters')
        _choice('ayanamsa_system', self.ayanamsa_system, ('Lahiri',))
        for name in ('natal_moon_sidereal_longitude', 'natal_lagna_sidereal_longitude'):
            value = getattr(self, name)
            if value is not None:
                _longitude(name, value)
        if self.natal_jd_ut1 is not None:
            _number('natal_jd_ut1', self.natal_jd_ut1)


@dataclass(frozen=True, slots=True)
class ElectionRuleContract:
    """Finite source rule, dependency closure and explicit transition ownership."""
    rule_id: str
    source: str
    formula: str
    purposes: tuple[str, ...]
    dependencies: tuple[str, ...]
    transitions: tuple[str, ...]
    attribution: str = 'verse_and_selected_commentary'

    def __post_init__(self):
        for name in ('rule_id', 'source', 'formula', 'attribution'):
            if type(getattr(self, name)) is not str or not getattr(self, name):
                raise ValueError('rule contract requires identity, source, formula and attribution')
        for name in ('purposes', 'dependencies', 'transitions'):
            values = getattr(self, name)
            _tuple(name, values, str, 128)
            if not values or len(set(values)) != len(values):
                raise ValueError('rule contract sets must be nonempty and unique')


@dataclass(frozen=True, slots=True)
class ElectionAssessment:
    """Family-owned policy and retained findings with separate personal coverage."""
    family: str
    policy: object
    context: object
    evidence: ElectionEvidence
    astronomical_findings: tuple[ElectionFinding, ...]
    personal_findings: tuple[ElectionFinding, ...]
    astronomical: ElectionDecision
    personal_decision: ElectionDecision
    requested_composition: ElectionDecision
    source_manifest_sha256: str
    exclusions: tuple[tuple[str, str], ...]
    input_basis: str = 'caller_supplied_conditional_on_evidence'

    def __post_init__(self):
        _choice('family', self.family, ('vastu', 'business', 'travel'))
        from .muhurta_vastu import VastuElectionPolicy,VastuElectionContext
        from .muhurta_business import BusinessElectionPolicy,BusinessElectionContext
        from .muhurta_travel import TravelElectionPolicy,TravelElectionContext
        classes={'vastu':(VastuElectionPolicy,VastuElectionContext),
                 'business':(BusinessElectionPolicy,BusinessElectionContext),
                 'travel':(TravelElectionPolicy,TravelElectionContext)}
        policy_type,context_type=classes[self.family]
        if not isinstance(self.policy,policy_type) or not isinstance(self.context,context_type):
            raise ValueError('assessment requires canonical family policy and context vessels')
        if not isinstance(self.evidence, ElectionEvidence):
            raise ValueError('assessment requires canonical election evidence')
        if getattr(self.policy, 'family', None) != self.family or getattr(self.context, 'family', None) != self.family:
            raise ValueError('assessment policy/context must belong to the declared family')
        for name in ('astronomical_findings', 'personal_findings'):
            rows = getattr(self, name)
            _tuple(name, rows, ElectionFinding, 2048)
            if len({r.rule_id for r in rows}) != len(rows):
                raise ValueError('finding identities must be unique within an assessment layer')
        requested = getattr(self.context, 'participant', None) is not None
        if not requested and self.personal_findings:
            raise ValueError('unrequested personal layer cannot have findings')
        for actual, expected in (
            (self.astronomical, _decision(self.astronomical_findings)),
            (self.personal_decision, _decision(self.personal_findings, requested)),
            (self.requested_composition, _decision(self.astronomical_findings + self.personal_findings)),
        ):
            if actual != expected:
                raise ValueError('assessment decision contradicts retained findings')
        if type(self.source_manifest_sha256) is not str or len(self.source_manifest_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.source_manifest_sha256):
            raise ValueError('assessment requires a source manifest SHA-256')
        _tuple('exclusions', self.exclusions, tuple, 128)
        if any(len(x) != 2 or any(type(v) is not str or not v for v in x) for x in self.exclusions):
            raise ValueError('exclusions require identity and reason')
        _choice('input_basis', self.input_basis, (
            'caller_supplied_conditional_on_evidence',
            'serving_reader_derived; conditional_numerical_model_certified',
            'serving_reader_derived; numerical_candidate_history_not_certified',
        ))


def _admit_evidence(evidence, policy, context):
    if not isinstance(evidence, ElectionEvidence):
        raise ValueError('evidence must be ElectionEvidence')
    evidence.__post_init__()
    policy.__post_init__()
    context.__post_init__()
    if evidence.ayanamsa_system != policy.ayanamsa_system:
        raise ValueError('evidence must use the selected sidereal reference')
    if evidence.lunar_month is not None and evidence.lunar_month.policy.system != policy.month_system:
        raise ValueError('lunar month convention must match selected policy')
    from .muhurta_marriage_visibility import MarriageApparitionContext
    for name in ('jupiter_apparition', 'venus_apparition'):
        apparition = getattr(evidence, name)
        if apparition is not None and not isinstance(apparition, MarriageApparitionContext):
            raise ValueError('apparition geometry does not belong to the selected purpose profile; SS horizon evidence required')
    p = context.participant
    if p is not None and p.ayanamsa_system != policy.ayanamsa_system:
        raise ValueError('natal and election evidence must share the selected sidereal reference')


def _measure(name, value, unit='predicate'):
    return ElectionMeasure(name, value, unit)


def _finding(contract, passes, *, suffix='', measures=(), exceptions=(), applicable=True, advisory=False, reasons=()):
    rid = contract.rule_id + ('.' + suffix if suffix else '')
    missing = tuple(reasons)
    if passes is None and applicable is not False and not missing:
        missing = ('required_evidence_missing_or_boundary_uncertain',)
    return ElectionFinding(rid, contract.rule_id, contract.source, applicable,
                           None if passes is None else not passes, tuple(measures),
                           tuple(exceptions), missing, advisory)


def _assessment(family, policy, context, evidence, findings, personal, manifest, exclusions):
    findings, personal = tuple(findings), tuple(personal)
    return ElectionAssessment(family, policy, context, evidence, findings, personal,
                              _decision(findings), _decision(personal, context.participant is not None),
                              _decision(findings + personal), manifest, exclusions)


def _manifest_digest(value):
    from dataclasses import asdict, is_dataclass
    def plain(x):
        if is_dataclass(x):
            return {k: plain(v) for k, v in asdict(x).items()}
        if isinstance(x, (tuple, list)):
            return [plain(v) for v in x]
        if isinstance(x, dict):
            return {k: plain(v) for k, v in x.items()}
        return x
    return sha256(json.dumps(plain(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _sign(value):
    return None if value is None else _sector(value, 12)


def _house(value, origin):
    return None if value is None or origin is None else (_sign(value) - _sign(origin)) % 12 + 1


def _member(value, choices):
    return None if value is None else value in choices


def _not(value):
    return None if value is None else not value


def _classical_nature(positions):
    """Named seven-planet BPHS phase/association interpretation, excluding nodes.

    MC's collective placement language is evaluated on the seven visible
    grahas in this composition. Requiring both antipodal nodes in3/6/11 is
    unsatisfiable. The selected reading is metadata, not a silent source claim.
    """
    phase = None if not {'Sun', 'Moon'} <= positions.keys() else (positions['Moon']-positions['Sun']) % 360
    nature = dict(Sun=False, Mars=False, Saturn=False, Jupiter=True, Venus=True,
                  Moon=None if phase is None else 0 < phase <= 180)
    sign = _sign(positions.get('Mercury'))
    joined = []
    for body, benefic in nature.items():
        other = _sign(positions.get(body))
        joined.append(False if benefic is True else None if sign is None or other is None else
                      False if sign != other else None if benefic is None else True)
    bad = _or(joined)
    nature['Mercury'] = None if sign is None or bad is None else not bad
    return nature


__all__ = ['ElectionEvidence', 'ElectionPlanet', 'ElectionParticipant', 'ElectionRuleContract',
           'ElectionAssessment', 'ElectionFinding', 'ElectionMeasure', 'ElectionException', 'ElectionDecision',
           'ElectionSearchBudgetError']
