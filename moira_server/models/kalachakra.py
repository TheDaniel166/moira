"""Strict, bounded REST contracts for the named Kalachakra profiles."""
from typing import Annotated, Literal
from pydantic import AfterValidator, ConfigDict, Field, StrictBool, model_validator
import math
from moira.kalachakra import (
    KalachakraEpoch, KalachakraSeed, KalachakraProjection,
    KalachakraSource, KalachakraRule, KalachakraConflict, KalachakraProfile,
)
from moira._kalachakra_types import admit, astronomical_epoch
from moira.sidereal import Ayanamsa
from moira._kalachakra_recipes import RECIPES, DENOMINATORS, recipe_for_row
from .common import _StrictModel
from ._vedic_inputs import FiniteNumber, CivilDateTime, KnownAyanamsa, SignIndex

ProfileId = Literal['bphs_santhanam_longitude_row_cycle_v1','rao_2000_longitude_continuous_v1']
YearBasis = Literal['savana_360','julian_365.25']
Level = Annotated[int, Field(strict=True,ge=1,le=2)]
RowPosition = Annotated[int, Field(strict=True,ge=0,le=8)]
Path = Annotated[list[RowPosition], Field(min_length=1,max_length=2)]
Angle = Annotated[float, Field(strict=True,ge=0,lt=360,allow_inf_nan=False)]
AyanamsaName = Annotated[KnownAyanamsa,Field(json_schema_extra={'enum':list(Ayanamsa.ALL)})]
RowId = Annotated[str,Field(pattern=r'^(R2000/)?[SA][12]/[1-4]$')]


def admitted_denominator(value):
    if value not in DENOMINATORS:
        raise ValueError('denominator must belong to an admitted source window')
    return value


Denominator = Annotated[int,Field(strict=True,json_schema_extra={'enum':list(DENOMINATORS)}),
                       AfterValidator(admitted_denominator)]


class DatetimeEpochRequest(_StrictModel):
    kind: Literal['datetime']
    value: CivilDateTime


class JulianEpochRequest(_StrictModel):
    kind: Literal['jd_utc']
    value: FiniteNumber


EpochRequest = Annotated[DatetimeEpochRequest | JulianEpochRequest, Field(discriminator='kind')]


class SiderealSeedRequest(_StrictModel):
    basis: Literal['sidereal']
    moon_sidereal_lon: Angle


class TropicalSeedRequest(_StrictModel):
    basis: Literal['tropical']
    moon_tropical_lon: Angle
    ayanamsa_system: AyanamsaName


SeedRequest = Annotated[SiderealSeedRequest | TropicalSeedRequest, Field(discriminator='basis')]


class ProjectionRequest(_StrictModel):
    year_basis: YearBasis


def engine_epoch(value):
    return None if value is None else KalachakraEpoch(value.kind,value.value)


def engine_seed(value):
    if isinstance(value,SiderealSeedRequest):
        return KalachakraSeed('sidereal',value.moon_sidereal_lon)
    return KalachakraSeed('tropical',value.moon_tropical_lon,value.ayanamsa_system)


def engine_projection(value):
    return None if value is None else KalachakraProjection(value.year_basis)


class KalachakraSequenceRequest(_StrictModel):
    profile_id: ProfileId
    seed: SeedRequest
    levels: Level = 2
    birth_epoch: EpochRequest | None = None
    projection: ProjectionRequest | None = None

    @model_validator(mode='after')
    def admitted_combination(self):
        admit(self.profile_id,self.levels,engine_seed(self.seed),
            engine_epoch(self.birth_epoch),engine_projection(self.projection))
        return self


class KalachakraChartRequest(_StrictModel):
    profile_id: ProfileId
    birth_datetime: CivilDateTime
    ayanamsa_system: AyanamsaName
    levels: Level = 2
    projection: ProjectionRequest | None = None

    @model_validator(mode='after')
    def admitted_epoch(self):
        astronomical_epoch(KalachakraEpoch('datetime',self.birth_datetime))
        return self


class KalachakraCurrentRequest(KalachakraSequenceRequest):
    query_epoch: EpochRequest

    @model_validator(mode='after')
    def projected_lookup(self):
        if self.projection is None:
            raise ValueError('current lookup requires projection')
        engine_epoch(self.query_epoch)
        return self


class KalachakraChartCurrentRequest(KalachakraChartRequest):
    query_epoch: EpochRequest

    @model_validator(mode='after')
    def projected_lookup(self):
        if self.projection is None:
            raise ValueError('current lookup requires projection')
        engine_epoch(self.query_epoch)
        return self


class ExactRatioResponse(_StrictModel):
    numerator: Annotated[str, Field(pattern=r'^(0|-?[1-9][0-9]*)$',max_length=401)]
    denominator: Annotated[str, Field(pattern=r'^[1-9][0-9]*$',max_length=400)]

    @model_validator(mode='after')
    def canonical_ratio(self):
        if len(self.numerator.lstrip('-'))>400 or math.gcd(int(self.numerator),int(self.denominator)) != 1:
            raise ValueError('exact ratios must be reduced and bounded to 400 digits')
        return self


class SourceSpanResponse(_StrictModel):
    start: ExactRatioResponse
    end: ExactRatioResponse


class DateSpanResponse(_StrictModel):
    start_jd_utc: FiniteNumber
    end_jd_utc: FiniteNumber


class AstronomyResponse(_StrictModel):
    jd_ut1: FiniteNumber
    jd_tt: FiniteNumber
    jd_tdb: FiniteNumber
    delta_t_seconds: FiniteNumber
    delta_t_correction_seconds: FiniteNumber
    tdb_minus_tt_seconds: FiniteNumber
    delta_t_source: str
    ephemeris_identity: str
    planetary_ephemeris: str
    lunar_ephemeris: str
    lunar_tidal_acceleration: FiniteNumber
    ayanamsa_system: AyanamsaName
    ayanamsa_offset: FiniteNumber
    anchor: str | None
    longitude_frame: Literal['true_ecliptic_of_date']
    longitude_origin: Literal['apparent_geocentric']
    ayanamsa_mode: Literal['true']
    corrections: tuple[Literal['light_time'],Literal['aberration'],Literal['gravitational_deflection'],Literal['nutation']]


class ProvenanceResponse(_StrictModel):
    input_origin: Literal['supplied_sidereal','supplied_tropical','derived_moon']
    moon_sidereal_lon: Angle
    birth_jd_utc: FiniteNumber | None
    normalized_datetime_utc: str | None
    moon_tropical_lon: Angle | None
    astronomy: AstronomyResponse | None


class BirthResponse(_StrictModel):
    nakshatra_number: Annotated[int,Field(strict=True,ge=1,le=27)]
    pada_number: Annotated[int,Field(strict=True,ge=1,le=4)]
    group: Literal['S1','S2','A1','A2']
    row_id: RowId
    row_signs: Annotated[list[SignIndex],Field(min_length=9,max_length=9)]
    fraction_in_pada: ExactRatioResponse
    row_total_years: Literal[83,85,86,100]
    elapsed_row_years: ExactRatioResponse
    natal_row_remaining_years: ExactRatioResponse
    birth_row_position: RowPosition
    birth_md_full_years: Annotated[int,Field(strict=True,ge=4,le=21)]
    birth_md_remaining_years: ExactRatioResponse
    coverage_years: ExactRatioResponse
    deha_sign_index: SignIndex
    jeeva_sign_index: SignIndex
    deha_jeeva_reference: Literal['natal_row','birth_nine_md_window']


class PeriodResponse(_StrictModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra={'allOf':[
        {'if':{'properties':{'children_status':{'const':'generated'}}},
         'then':{'properties':{'children':{'minItems':9,'maxItems':9}}},
         'else':{'properties':{'children':{'maxItems':0}}}},
    ]})
    path: Path
    parent_path: Path | None
    row_id: RowId
    row_position: RowPosition
    md_cycle_index: Annotated[int,Field(strict=True,ge=0,le=1)]
    sign_index: SignIndex
    ruler: Literal['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn']
    parent_weight: Annotated[int,Field(strict=True,ge=1,le=21)]
    weight: Annotated[int,Field(strict=True,ge=4,le=21)]
    denominator: Denominator
    full_years: SourceSpanResponse
    visible_years: SourceSpanResponse | None
    full_dates: DateSpanResponse | None
    visible_dates: DateSpanResponse | None
    visibility: Literal['visible','clipped_before_birth']
    children_status: Literal['not_requested','generated','maximum_depth']
    children: Annotated[list['PeriodResponse'],Field(max_length=9)]

    @model_validator(mode='after')
    def bounded_children(self):
        if self.children_status == 'generated':
            if len(self.path) != 1 or len(self.children) != 9 or any(c.children for c in self.children):
                raise ValueError('generated MDs require exactly nine leaf ADs')
        elif self.children:
            raise ValueError('leaf or unrequested children must be empty')
        return self


class TransitionResponse(_StrictModel):
    source_path: Path
    destination_path: Path
    source_sign_index: SignIndex
    destination_sign_index: SignIndex
    source_row_position: RowPosition
    destination_row_position: RowPosition
    level: Level
    boundary_years: ExactRatioResponse
    boundary_jd_utc: FiniteNumber | None
    row_seam: StrictBool
    visible: StrictBool
    classification_status: Literal['classified','unresolved_source_conflict','row_seam_not_classified','not_classified_by_profile']
    classification: Literal['mandooki','simhavlokan','markati'] | None
    conflict_ids: Annotated[list[Literal['KC-10']],Field(max_length=1)]
    rule_id: Literal['KC_GATI','R2000_GATI']


class ProjectionResponse(_StrictModel):
    birth_jd_utc: FiniteNumber
    year_basis: YearBasis
    year_days: ExactRatioResponse
    schedule_axis: Literal['jd_utc']


class ResultIdentity(_StrictModel):
    profile_id: ProfileId
    profile_version: Literal['ved014.1','ved014.rao2000.1']
    levels: Level
    birth: BirthResponse
    provenance: ProvenanceResponse
    source_ids: list[str]
    rule_ids: list[str]
    conflict_ids: list[str]
    eligibility_status: Literal['not_evaluated']

    @model_validator(mode='after')
    def profile_identity(self):
        recipe = RECIPES[self.profile_id]
        if (self.profile_version,tuple(self.source_ids),tuple(self.rule_ids),tuple(self.conflict_ids),
            self.birth.deha_jeeva_reference) != (
            recipe.version,recipe.source_ids,recipe.rule_ids,recipe.conflict_ids,recipe.deha_jeeva_reference):
            raise ValueError('result metadata disagrees with its named profile')
        if recipe_for_row(self.birth.row_id) is not recipe:
            raise ValueError('birth row belongs to another profile')
        return self


class KalachakraSequenceResponse(ResultIdentity):
    periods: Annotated[list[PeriodResponse],Field(min_length=9,max_length=9)]
    transitions: Annotated[list[TransitionResponse],Field(min_length=8,max_length=80)]
    coverage: SourceSpanResponse
    coverage_dates: DateSpanResponse | None
    projection: ProjectionResponse | None
    generated_node_count: Literal[9,90]
    visible_node_count: Annotated[int,Field(strict=True,ge=9,le=90)]
    projection_status: Literal['not_requested','projected']

    @model_validator(mode='after')
    def generated_bounds(self):
        expected = 9 if self.levels==1 else 90
        count = len(self.periods)+sum(len(p.children) for p in self.periods)
        if count != expected or self.generated_node_count != expected:
            raise ValueError('generated nodes disagree with requested depth')
        if any(p.children_status != ('generated' if self.levels==2 else 'not_requested') for p in self.periods):
            raise ValueError('children status disagrees with depth')
        if any(recipe_for_row(p.row_id).profile_id != self.profile_id
               for md in self.periods for p in (md,*md.children)):
            raise ValueError('period row belongs to another profile')
        if (self.projection_status=='projected') != (self.projection is not None and self.coverage_dates is not None):
            raise ValueError('inconsistent projection status')
        return self


class ActivePeriodResponse(_StrictModel):
    path: Path
    sign_index: SignIndex
    full_years: SourceSpanResponse
    visible_years: SourceSpanResponse
    full_dates: DateSpanResponse
    visible_dates: DateSpanResponse


class KalachakraCurrentResponse(ResultIdentity):
    projection: ProjectionResponse
    coverage: SourceSpanResponse
    coverage_dates: DateSpanResponse
    query_jd_utc: FiniteNumber
    status: Literal['before_birth','active','after_coverage']
    active_line: Annotated[list[ActivePeriodResponse],Field(max_length=2)]

    @model_validator(mode='after')
    def active_depth(self):
        if len(self.active_line) != (self.levels if self.status=='active' else 0):
            raise ValueError('active line disagrees with status/depth')
        return self


class KalachakraCatalogueResponse(_StrictModel):
    catalogue_version: Literal['ved014.2']
    profiles: list[KalachakraProfile]
    sources: list[KalachakraSource]
    rules: list[KalachakraRule]
    conflicts: list[KalachakraConflict]
    ayanamsa_systems: list[AyanamsaName]
    supported_levels: tuple[Literal[1],Literal[2]]
    year_bases: tuple[Literal['savana_360'],Literal['julian_365.25']]
    major_period_count: Literal[9]
    maximum_period_nodes: Literal[90]
    eligibility_status: Literal['not_evaluated']
