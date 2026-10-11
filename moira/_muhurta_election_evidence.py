"""Demand-driven assembly of exact request-owned astronomical evidence.

The dependency set selects work, never doctrine. The full marriage path keeps
its original evaluation order and public evidence type. No ambient cache is
introduced: positions, parents and certificates remain on the serving context.
"""
from dataclasses import dataclass

from ._muhurta_marriage_sources import NINE
from .muhurta_marriage import MarriageElectionEvidence, MarriagePlanet


@dataclass(frozen=True, slots=True)
class ElectionDependencies:
    """Immutable dependency closure for one selected source evaluation."""
    planets: tuple[str, ...] = NINE
    lagna: bool = True
    solar: bool = True
    phases: bool = False
    month: bool = False
    ingresses: bool = False
    stars: bool = False
    apparitions: bool = False
    apparition_planets: tuple[str, ...] = ('Jupiter', 'Venus')

    def __post_init__(self):
        if type(self.planets) is not tuple or len(set(self.planets)) != len(self.planets) or any(p not in NINE for p in self.planets):
            raise ValueError('dependencies require unique canonical planets')
        for name in ('lagna', 'solar', 'phases', 'month', 'ingresses', 'stars', 'apparitions'):
            if type(getattr(self, name)) is not bool:
                raise ValueError('dependency switches must be booleans')
        if type(self.apparition_planets) is not tuple or len(set(self.apparition_planets)) != len(self.apparition_planets) or any(p not in ('Jupiter','Venus') for p in self.apparition_planets):
            raise ValueError('apparition dependencies require unique admitted planets')


FULL_MARRIAGE = ElectionDependencies(phases=True, month=True, ingresses=True, stars=True, apparitions=True)


def build_evidence(context, jd, dependencies=FULL_MARRIAGE, evidence_type=MarriageElectionEvidence):
    from ._muhurta_marriage_enclosure import EnclosureUnavailable
    context.meter.stage = 'instant_positions'
    try:
        bound = context.certifier.astro.tt(jd, jd)
        if not bound.lo <= context.epoch(jd).epoch_tt <= bound.hi:
            context.reasons.append('clock_source_changed_during_initial_binding')
    except EnclosureUnavailable as exc:
        context.reasons.append(str(exc))
    planets = tuple(MarriagePlanet(p, context.longitude_at(p, jd), context.body(p, jd).speed)
                    for p in dependencies.planets)
    solar = context.solar_context(jd) if dependencies.solar else None
    spans, yoga, karana, endings = context.phase_context(jd) if dependencies.phases else ((), None, None, ())
    month = context.lunar_month(jd) if dependencies.month else None
    # Argument evaluation order intentionally matches the admitted marriage owner.
    return evidence_type(jd, planets, context.lagna(jd) if dependencies.lagna else None,
        solar, spans, yoga, karana, month,
        context.ingresses(jd) if dependencies.ingresses else None,
        context.star_history(jd) if dependencies.stars else None, endings,
        context.apparition('Jupiter', jd) if dependencies.apparitions and 'Jupiter' in dependencies.apparition_planets else None,
        context.apparition('Venus', jd) if dependencies.apparitions and 'Venus' in dependencies.apparition_planets else None,
        context.policy.ayanamsa_system)
