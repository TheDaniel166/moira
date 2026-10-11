"""Residential action, facing and qualification contracts."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from moira.muhurta_vastu import VastuElectionPolicy, VastuElectionContext, assess_vastu_election
from moira.lunar_month import LunarMonthSystem
from moira._muhurta_election_dated import _admit, admit_window
from .common import _StrictModel
from ._vedic_inputs import CivilDateTime, FiniteNumber
from .muhurta_marriage import _EngineModel, _engine_value, StrictText, MarriageLimitsModel
from .muhurta_election import (
    ElectionParticipantModel, ElectionEvidenceModel, ElectionCatalogueResponse,
    ElectionAssessmentResponse, ElectionSnapshotResponse, ElectionWindowsResponse,
)


class VastuPolicyRequest(_EngineModel):
    _engine_type = VastuElectionPolicy
    purpose: Literal['foundation','first_entry','return_entry','old_house_entry','extraordinary_entry']
    profile: Literal['mc_maniprabha_1948_residential.v1'] = 'mc_maniprabha_1948_residential.v1'
    ayanamsa_system: Literal['Lahiri'] = 'Lahiri'
    month_system: LunarMonthSystem = LunarMonthSystem.PURNIMANTA
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=.01, le=1)] = .1


class VastuContextRequest(_EngineModel):
    _engine_type = VastuElectionContext
    facing: Literal['east','south','west','north']
    excavation_corner: Literal['northeast','southeast','southwest','northwest'] | None = None
    extraordinary_reason: Literal['fire','flood','illness','authority_displacement'] | None = None
    participant: ElectionParticipantModel | None = None


class VastuPolicyResponse(VastuPolicyRequest):
    family: Literal['vastu']
    foundation_calendar: str
    entry_calendar: str
    star28_profile: str
    nature_profile: str
    house_profile: str
    availability_profile: str
    facing_star_profile: str
    godhuli: Literal[False]

    def to_engine(self):
        return VastuElectionPolicy(**{n: _engine_value(getattr(self,n)) for n in VastuPolicyRequest.model_fields})


class VastuContextResponse(VastuContextRequest):
    family: Literal['vastu']
    facing_basis: str

    def to_engine(self):
        return VastuElectionContext(**{n: _engine_value(getattr(self,n)) for n in VastuContextRequest.model_fields})


class VastuDirectRequest(_StrictModel):
    evidence: ElectionEvidenceModel
    policy: VastuPolicyRequest
    context: VastuContextRequest

    @model_validator(mode='after')
    def _admit(self):
        assess_vastu_election(self.evidence.to_engine(), policy=self.policy.to_engine(), context=self.context.to_engine())
        return self


class VastuDateTimeRequest(_StrictModel):
    dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(gt=-90, lt=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    timezone: Annotated[StrictText, Field(min_length=1, max_length=128)]
    policy: VastuPolicyRequest
    context: VastuContextRequest
    limits: MarriageLimitsModel = Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        _admit('vastu', self.dt, self.latitude, self.longitude, self.timezone,
               self.policy.to_engine(), self.context.to_engine(), self.limits.to_engine())
        return self


class VastuWindowsRequest(_StrictModel):
    start: CivilDateTime
    end: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(gt=-90, lt=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    timezone: Annotated[StrictText, Field(min_length=1, max_length=128)]
    policy: VastuPolicyRequest
    context: VastuContextRequest
    limits: MarriageLimitsModel = Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        admit_window('vastu', self.start, self.end, self.latitude, self.longitude, self.timezone,
                     self.policy.to_engine(), self.context.to_engine(), self.limits.to_engine())
        return self


class VastuCatalogueResponse(ElectionCatalogueResponse):
    directions: tuple[str, ...]
    excavation_corners: tuple[str, ...]


VastuAssessmentResponse = ElectionAssessmentResponse[VastuPolicyResponse, VastuContextResponse]
VastuSnapshotResponse = ElectionSnapshotResponse[VastuPolicyResponse, VastuContextResponse]
VastuWindowsResponse = ElectionWindowsResponse[VastuPolicyResponse, VastuContextResponse]
