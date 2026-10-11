"""Finite commercial roles, anchors and strict election transport."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from moira.muhurta_business import BusinessElectionPolicy, BusinessElectionContext, assess_business_election
from moira.lunar_month import LunarMonthSystem
from moira._muhurta_election_dated import _admit, admit_window
from .common import _StrictModel
from ._vedic_inputs import CivilDateTime, FiniteNumber
from .muhurta_marriage import _EngineModel, _engine_value, StrictText, MarriageLimitsModel
from .muhurta_election import (ElectionEvidenceModel, ElectionCatalogueResponse,
    ElectionAssessmentResponse, ElectionSnapshotResponse, ElectionWindowsResponse)


class BusinessPolicyRequest(_EngineModel):
    _engine_type = BusinessElectionPolicy
    purpose: Literal['purchase','sale','first_opening_for_trade']
    profile: Literal['mc_avasthi_2004_commerce.v1'] = 'mc_avasthi_2004_commerce.v1'
    ayanamsa_system: Literal['Lahiri'] = 'Lahiri'
    solver_tolerance_seconds: Annotated[FiniteNumber,Field(ge=.01,le=1)] = .1


class BusinessContextRequest(_EngineModel):
    _engine_type = BusinessElectionContext
    actor_id: Annotated[StrictText,Field(min_length=1,max_length=120)]
    actor_role: Literal['buyer','seller','trading_operator']
    anchor: Literal['acceptance_exchange','first_opening_for_trade']
    counterparty_id: Annotated[StrictText,Field(min_length=1,max_length=120)] | None = None


class BusinessPolicyResponse(BusinessPolicyRequest):
    family: Literal['business']
    good_tithi_profile: str
    placement_profile: str
    nature_profile: str
    month_system: LunarMonthSystem
    godhuli: Literal[False]

    def to_engine(self):
        return BusinessElectionPolicy(**{n:_engine_value(getattr(self,n)) for n in BusinessPolicyRequest.model_fields})


class BusinessContextResponse(BusinessContextRequest):
    family: Literal['business']
    participant: None

    def to_engine(self):
        return BusinessElectionContext(**{n:_engine_value(getattr(self,n)) for n in BusinessContextRequest.model_fields})


class BusinessDirectRequest(_StrictModel):
    evidence: ElectionEvidenceModel
    policy: BusinessPolicyRequest
    context: BusinessContextRequest

    @model_validator(mode='after')
    def _admit(self):
        assess_business_election(self.evidence.to_engine(),policy=self.policy.to_engine(),context=self.context.to_engine())
        return self


class BusinessDateTimeRequest(_StrictModel):
    dt: CivilDateTime
    latitude: Annotated[FiniteNumber,Field(gt=-90,lt=90)]
    longitude: Annotated[FiniteNumber,Field(ge=-180,le=180)]
    timezone: Annotated[StrictText,Field(min_length=1,max_length=128)]
    policy: BusinessPolicyRequest
    context: BusinessContextRequest
    limits: MarriageLimitsModel = Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        _admit('business',self.dt,self.latitude,self.longitude,self.timezone,self.policy.to_engine(),self.context.to_engine(),self.limits.to_engine())
        return self


class BusinessWindowsRequest(_StrictModel):
    start: CivilDateTime
    end: CivilDateTime
    latitude: Annotated[FiniteNumber,Field(gt=-90,lt=90)]
    longitude: Annotated[FiniteNumber,Field(ge=-180,le=180)]
    timezone: Annotated[StrictText,Field(min_length=1,max_length=128)]
    policy: BusinessPolicyRequest
    context: BusinessContextRequest
    limits: MarriageLimitsModel = Field(default_factory=MarriageLimitsModel)

    @model_validator(mode='after')
    def _admit(self):
        admit_window('business',self.start,self.end,self.latitude,self.longitude,self.timezone,self.policy.to_engine(),self.context.to_engine(),self.limits.to_engine())
        return self


class BusinessCatalogueResponse(ElectionCatalogueResponse):
    roles: tuple[tuple[str,str], ...]
    anchors: tuple[str, ...]


BusinessAssessmentResponse = ElectionAssessmentResponse[BusinessPolicyResponse,BusinessContextResponse]
BusinessSnapshotResponse = ElectionSnapshotResponse[BusinessPolicyResponse,BusinessContextResponse]
BusinessWindowsResponse = ElectionWindowsResponse[BusinessPolicyResponse,BusinessContextResponse]


class BusinessComparisonRequest(_StrictModel):
    evidence: ElectionEvidenceModel
    buyer_id: Annotated[StrictText,Field(min_length=1,max_length=120)]
    seller_id: Annotated[StrictText,Field(min_length=1,max_length=120)]

    @model_validator(mode='after')
    def _admit(self):
        BusinessElectionContext(self.buyer_id,'buyer','acceptance_exchange',self.seller_id)
        return self


class BusinessComparisonResponse(_StrictModel):
    buyer: BusinessAssessmentResponse
    seller: BusinessAssessmentResponse
    preferred_star_sets_disjoint: Literal[True]
