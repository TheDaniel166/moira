"""Strict named travel component contracts and declared departure context."""
from typing import Annotated,Literal
from pydantic import Field,model_validator
from moira.muhurta_travel import TravelElectionPolicy,TravelElectionContext,assess_travel_election
from moira.lunar_month import LunarMonthSystem
from moira._muhurta_election_dated import _admit,admit_window
from .common import _StrictModel
from ._vedic_inputs import CivilDateTime,FiniteNumber
from .muhurta_marriage import _EngineModel,_engine_value,StrictText,MarriageLimitsModel
from pydantic import StrictInt
from .muhurta_election import (ElectionParticipantModel,ElectionEvidenceModel,ElectionCatalogueResponse,
    ElectionAssessmentResponse,ElectionSnapshotResponse,ElectionWindowsResponse)


class TravelPolicyRequest(_EngineModel):
    _engine_type=TravelElectionPolicy
    profile: Literal['mc_maniprabha_1948_ordinary_land.v1','kp_1917_weekday_direction_release.v1','kp_1917_travel_modular_tests.v1']
    tithi_ordinal: Literal['month_1_to_30','paksha_1_to_15']='month_1_to_30'
    ayanamsa_system: Literal['Lahiri']='Lahiri'
    solver_tolerance_seconds: Annotated[FiniteNumber,Field(ge=.01,le=1)]=.1


class TravelContextRequest(_EngineModel):
    _engine_type=TravelElectionContext
    traveller_id: Annotated[StrictText,Field(min_length=1,max_length=120)]
    anchor: Literal['leave_residence','cross_settlement_boundary','leave_room']
    direction: Literal['east','southeast','south','southwest','west','northwest','north','northeast'] | None=None
    leg: Literal['outbound','return']='outbound'
    participant: ElectionParticipantModel | None=None
    prior_departure_jd_ut1: FiniteNumber | None=None
    completed_stop_nights: Annotated[StrictInt,Field(ge=0,le=10000)] | None=None


class TravelPolicyResponse(TravelPolicyRequest):
    purpose: Literal['departure']
    family: Literal['travel']
    scope: Literal['named_component','ordinary_land_departure']
    ghati_clock: str
    month_system: LunarMonthSystem
    godhuli: Literal[False]

    def to_engine(self):
        return TravelElectionPolicy(**{n:_engine_value(getattr(self,n)) for n in TravelPolicyRequest.model_fields})


class TravelContextResponse(TravelContextRequest):
    family: Literal['travel']
    direction_basis: str

    def to_engine(self):
        return TravelElectionContext(**{n:_engine_value(getattr(self,n)) for n in TravelContextRequest.model_fields})


class TravelDirectRequest(_StrictModel):
    evidence: ElectionEvidenceModel
    policy: TravelPolicyRequest
    context: TravelContextRequest

    @model_validator(mode='after')
    def _admit(self):
        assess_travel_election(self.evidence.to_engine(),policy=self.policy.to_engine(),context=self.context.to_engine())
        return self


class TravelDateTimeRequest(_StrictModel):
    dt: CivilDateTime
    latitude: Annotated[FiniteNumber,Field(gt=-90,lt=90)]
    longitude: Annotated[FiniteNumber,Field(ge=-180,le=180)]
    timezone: Annotated[StrictText,Field(min_length=1,max_length=128)]
    policy: TravelPolicyRequest
    context: TravelContextRequest
    limits: MarriageLimitsModel=Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        _admit('travel',self.dt,self.latitude,self.longitude,self.timezone,self.policy.to_engine(),self.context.to_engine(),self.limits.to_engine())
        return self


class TravelWindowsRequest(_StrictModel):
    start: CivilDateTime
    end: CivilDateTime
    latitude: Annotated[FiniteNumber,Field(gt=-90,lt=90)]
    longitude: Annotated[FiniteNumber,Field(ge=-180,le=180)]
    timezone: Annotated[StrictText,Field(min_length=1,max_length=128)]
    policy: TravelPolicyRequest
    context: TravelContextRequest
    limits: MarriageLimitsModel=Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        admit_window('travel',self.start,self.end,self.latitude,self.longitude,self.timezone,self.policy.to_engine(),self.context.to_engine(),self.limits.to_engine())
        return self


class TravelCatalogueResponse(ElectionCatalogueResponse):
    profile_scopes: tuple[tuple[str,str],...]
    profile_sources: tuple[tuple[str,str,str,str],...]
    imported_families: tuple[str,...]
    directions: tuple[str,...]
    anchors: tuple[str,...]


TravelAssessmentResponse=ElectionAssessmentResponse[TravelPolicyResponse,TravelContextResponse]
TravelSnapshotResponse=ElectionSnapshotResponse[TravelPolicyResponse,TravelContextResponse]
TravelWindowsResponse=ElectionWindowsResponse[TravelPolicyResponse,TravelContextResponse]
