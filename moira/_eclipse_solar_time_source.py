"""Request-local DE441/current-policy adapter for Stage 4 time coverage.

The mathematical profile is the explicit real Stage 3 policy lift. Raw
record words, clock/table identities and rotation scopes remain inspectable.
No claim about every native rounding, physical Delta-T, or IAU conformance
is implied. General vector requests precede all solar-cone admission tests.
"""
from dataclasses import dataclass, field

from ._eclipse_interval import RationalInterval as I
from ._eclipse_continuous_policy_clock import (
    freeze_continuous_policy_clock, bound_continuous_policy_tt,
)
from ._eclipse_piecewise_vectors import freeze_eclipse_records
from ._eclipse_piecewise_vector_values import bound_piecewise_vector_values
from ._eclipse_continuous_solar_stage3 import (
    prepare_continuous_solar_stage3, continuous_solar_stage3_provider,
)
from ._eclipse_solar_time_surface import global_disc_separation


@dataclass(slots=True)
class SolarTimeSource:
    """Frozen clock/records and lazily bounded celestial/ITRF vector domains.

    RITE: Stage 4 source adapter.
    THEOREM: Whole-domain bounds compose the explicit real policy lift.
    RITE OF PURPOSE: Supply vectors independently of cone eligibility.
    LAW OF OPERATION: Borrow an open reader and own all mutable caches.
    Canon: NAIF type 2; the Stage 3 continuous-current-policy profile.
    [MACHINE_CONTRACT v1]
    {"scope":"private bounded solar time source","id":"moira.eclipse.solar_time_source",
     "risk":"high","api":["scene","separation"],
     "state":{"mutable":true,"owners":["request caller"],"contents":"frozen records, clock, request-local rotation and vector caches"},
     "effects":["bounded reads from borrowed SPK reader","request-local cache mutation"],
     "concurrency":{"thread":"request_local","cross_thread_calls":"forbidden","owner_thread_only_mutation":true},
     "failures":["missing resources","unsupported clock or source domain","interval budgets"],
     "succession":"uses existing Stage 3 source and rotation foundations",
     "agent":"continuous real model; no native rounding or physical accuracy attestation"}
    [/MACHINE_CONTRACT]
    """

    reader: object = field(repr=False)
    anchor_jd_ut1: float
    domain: I
    clock: object
    records: object
    rotation_scopes: list = field(default_factory=list, repr=False)
    separation_cache: dict = field(default_factory=dict, repr=False)
    scene_cache: dict = field(default_factory=dict, repr=False)
    scope: str = 'continuous_real_current_policy_retarded_sun_and_moon'
    serving_rounding_attested: bool = False
    physical_accuracy_certified: bool = False

    def _check(self, domain):
        if domain.lo < self.domain.lo or domain.hi > self.domain.hi:
            raise ValueError('request outside frozen UT1 domain')

    def separation(self, domain):
        """Enclose the whole-Earth necessary predicate before orientation."""
        self._check(domain)
        if domain not in self.separation_cache:
            tt, _ = bound_continuous_policy_tt(self.clock,domain)
            sun, moon = bound_piecewise_vector_values(self.records,tt[0],retarded_moon=True)
            self.separation_cache[domain] = global_disc_separation(
                sun,moon)
        return self.separation_cache[domain]

    def scene(self, domain):
        """Bound full ITRF positions, including epochs without a shadow axis."""
        self._check(domain)
        if domain not in self.scene_cache:
            for scope, provider in self.rotation_scopes:
                if scope.domain.lo <= domain.lo <= domain.hi <= scope.domain.hi:
                    break
            else:
                scope = prepare_continuous_solar_stage3(self.reader,self.anchor_jd_ut1,
                                                       domain,panel_count=1)
                provider, _ = continuous_solar_stage3_provider(scope,scene_only=True)
                self.rotation_scopes.append((scope,provider))
            self.scene_cache[domain] = provider(domain)
        return self.scene_cache[domain]


def prepare_solar_time_source(reader, anchor_jd_ut1, domain):
    """Copy verified records for an explicitly bounded UT1 request."""
    clock = freeze_continuous_policy_clock(reader,anchor_jd_ut1,domain)
    tt, _ = bound_continuous_policy_tt(clock,domain)
    records = freeze_eclipse_records(reader,anchor_jd_ut1,tt[0],max_records=256)
    return SolarTimeSource(reader,float(anchor_jd_ut1),domain,clock,records)
