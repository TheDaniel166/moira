"""Strict, lossless transport of engine-owned Muhurta Lagna evidence."""
from typing import Annotated, Literal
from datetime import datetime
from pydantic import Field, model_validator
from moira.muhurta_lagna import MuhurtaLagnaPolicy, evaluate_muhurta_lagna_strength
from moira.shadbala import SthanaBala, KalaBala, PlanetShadbala, ShadbalaResult
from .common import _StrictModel
from ._vedic_inputs import FiniteNumber, ClassicalPlanet, CivilDateTime
from .varga import VargaPointResponse
from .gochara_dated import GocharaEpochResponse
from .muhurta_dosha import DoshaPredicateResponse

Angle = Annotated[FiniteNumber, Field(ge=0, lt=360)]
PlanetName = Literal['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu']
Purpose = Literal['mc_nakshatra_44.v1','mc_vivaha_75_78_84_88_92.v1']
Navamsa = Literal['mc_avasthi_vivaha_84_four.v1','mc_vivaha_84_optional_pisces.v1']
Parihara = Literal['mc_vivaha_88_natural_avasthas_orb.v1']


class LagnaPolicyRequest(_StrictModel):
    purpose_profile: Purpose = 'mc_vivaha_75_78_84_88_92.v1'
    navamsa_profile: Navamsa = 'mc_avasthi_vivaha_84_four.v1'
    parihara_profile: Parihara | None = None
    ayanamsa_system: Annotated[str, Field(strict=True)] = 'Lahiri'

    def to_engine(self):
        return MuhurtaLagnaPolicy(**self.model_dump())

    @model_validator(mode='after')
    def _admit(self):
        self.to_engine()
        return self


class LagnaSthanaModel(_StrictModel):
    uchcha: FiniteNumber
    saptavargaja: FiniteNumber
    ojayugma: FiniteNumber
    kendradi: FiniteNumber
    drekkana: FiniteNumber
    total: FiniteNumber


class LagnaKalaModel(_StrictModel):
    nathonnatha: FiniteNumber
    paksha: FiniteNumber
    tribhaga: FiniteNumber
    abda_masa_vara_hora: FiniteNumber
    ayana: FiniteNumber
    yuddha: FiniteNumber
    total: FiniteNumber


class LagnaStrengthModel(_StrictModel):
    planet: ClassicalPlanet
    sthana_bala: LagnaSthanaModel
    dig_bala: FiniteNumber
    kala_bala: LagnaKalaModel
    chesta_bala: FiniteNumber
    naisargika_bala: FiniteNumber
    drig_bala: FiniteNumber
    total_shashtiamsas: FiniteNumber
    total_rupas: FiniteNumber
    required_rupas: FiniteNumber
    is_sufficient: Annotated[bool, Field(strict=True)]

    def to_engine(self):
        values=self.model_dump(exclude={'sthana_bala','kala_bala'})
        return PlanetShadbala(**values, sthana_bala=SthanaBala(**self.sthana_bala.model_dump()),
                             kala_bala=KalaBala(**self.kala_bala.model_dump()))


class LagnaShadbalaInput(_StrictModel):
    jd: FiniteNumber
    ayanamsa_system: Annotated[str, Field(strict=True)]
    planets: dict[ClassicalPlanet,LagnaStrengthModel]

    def to_engine(self):
        return ShadbalaResult(self.jd, self.ayanamsa_system, {p:v.to_engine() for p,v in self.planets.items()})


class LagnaDirectRequest(_StrictModel):
    sidereal_longitudes: dict[PlanetName,Angle]
    jd_ut1: FiniteNumber
    lagna_sidereal_longitude: Angle | None = None
    natal_moon_sidereal_longitude: Angle | None = None
    natal_lagna_sidereal_longitude: Angle | None = None
    shadbala_result: LagnaShadbalaInput | None = None
    policy: LagnaPolicyRequest = Field(default_factory=LagnaPolicyRequest)

    def engine_inputs(self):
        return self.model_dump(exclude={'policy','shadbala_result'}) | {
            'policy':self.policy.to_engine(),
            'shadbala_result':None if self.shadbala_result is None else self.shadbala_result.to_engine()}

    @model_validator(mode='after')
    def _admit(self):
        evaluate_muhurta_lagna_strength(**self.engine_inputs())
        return self


class LagnaDatetimeRequest(_StrictModel):
    dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    include_shadbala: Annotated[bool, Field(strict=True)] = False
    hora_lord: ClassicalPlanet | None = None
    natal_moon_sidereal_longitude: Angle | None = None
    natal_lagna_sidereal_longitude: Angle | None = None
    policy: LagnaPolicyRequest = Field(default_factory=LagnaPolicyRequest)

    @model_validator(mode='after')
    def _admit(self):
        if self.hora_lord is not None and not self.include_shadbala:
            raise ValueError('hora_lord requires include_shadbala')
        return self


class LagnaPolicyResponse(LagnaPolicyRequest):
    house_basis: str
    aspect_profile: str
    relationship_profile: str
    nature_profile: str
    shadbala_role: str

    def to_engine(self):
        return MuhurtaLagnaPolicy(**{k:getattr(self,k) for k in LagnaPolicyRequest.model_fields})


class LagnaPlanetResponse(_StrictModel):
    planet: PlanetName
    sidereal_longitude: Angle
    sign_index: int
    navamsa: VargaPointResponse
    house: int | None
    benefic: bool | None


class LagnaRuleResponse(_StrictModel):
    rule_id: str
    satisfied: bool | None
    prerequisites: tuple[DoshaPredicateResponse,...]
    citation: str


class LagnaContributionResponse(_StrictModel):
    planet: PlanetName
    house: int | None
    favorable_houses: tuple[int,...]
    weight: float
    points: float | None


class LagnaScoreResponse(_StrictModel):
    entries: tuple[LagnaContributionResponse,...]
    total: float | None
    known_points: float
    possible_bands: tuple[Literal['prohibited','inauspicious','middling','auspicious'],...]
    maximum: Literal[20.]
    citation: str


class LagnaRestrictionResponse(_StrictModel):
    rule_id: str
    planet: PlanetName
    detected: bool | None
    state: Literal['clear','unavailable','neutralized','exception_unavailable','detected']
    predicates: tuple[DoshaPredicateResponse,...]
    parihara_profile: Parihara | None
    neutralized: bool | None
    exception_predicates: tuple[DoshaPredicateResponse,...]
    citation: str


class LagnaAssessmentResponse(_StrictModel):
    jd_ut1: float
    policy: LagnaPolicyResponse
    lagna_sidereal_longitude: Angle | None
    lagna_navamsa: VargaPointResponse | None
    natal_moon_sidereal_longitude: Angle | None
    natal_lagna_sidereal_longitude: Angle | None
    planets: tuple[LagnaPlanetResponse,...]
    rules: tuple[LagnaRuleResponse,...]
    placement_score: LagnaScoreResponse | None
    restrictions: tuple[LagnaRestrictionResponse,...]
    shadbala: tuple[LagnaStrengthModel,...]
    unavailable_reasons: tuple[str,...]
    excluded_rules: tuple[str,...]
    activity_suitability: Literal['not_evaluated']
    input_basis: str


class LagnaSnapshotResponse(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    epoch: GocharaEpochResponse
    assessment: LagnaAssessmentResponse
    reader_binding: Literal['discovered_reader','caller_owned_reader']
    shadbala_basis: str
    hora_lord: ClassicalPlanet | None
    node_mode: str
    longitude_frame: str
    interval_semantics: str


class LagnaCatalogueResponse(_StrictModel):
    purpose_profiles: tuple[Purpose,...]
    navamsa_profiles: tuple[Navamsa,...]
    parihara_profiles: tuple[Parihara,...]
    source: str
    excluded_rules: tuple[str,...]
    score_maximum: float
    grade_boundary_policy: str
    relationship_direction: str
    nature_boundary_policy: str
    strength_policy: str
