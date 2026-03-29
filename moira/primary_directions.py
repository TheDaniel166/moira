"""
Moira -- primary_directions.py
The Primary Direction Engine: governs the currently admitted primary-direction
families for natal charts.

Boundary: owns speculum construction, mundane fraction arithmetic, direct and
converse arc computation, and symbolic time-key conversion. Delegates ecliptic-
to-equatorial coordinate transformation to constants (DEG2RAD/RAD2DEG). Does
NOT own natal chart construction, house computation, or ephemeris state.

Public surface:
    DIRECT, CONVERSE,
    SpeculumEntry, PrimaryArc,
    speculum, find_primary_arcs

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - Chart and HouseCusps instances must be fully constructed before calling
      speculum() or find_primary_arcs().
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Iterable

from .constants import Body, DEG2RAD
from .primary_direction_converse import PrimaryDirectionConverseDoctrine
from .primary_direction_geometry import compute_primary_direction_arcs
from .primary_direction_keys import (
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    convert_arc_to_time,
)
from .primary_direction_latitudes import (
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionLatitudePolicy,
)
from .primary_direction_latitude_sources import (
    PrimaryDirectionLatitudeSource,
    PrimaryDirectionLatitudeSourcePolicy,
)
from .primary_direction_methods import PrimaryDirectionMethod
from .primary_direction_morinus import (
    MorinusAspectContext,
    project_morinus_aspect_point,
)
from .primary_direction_perfections import (
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionPolicy,
)
from .primary_direction_placidus import (
    PlacidianRaptParallelTarget,
    compute_placidian_rapt_parallel_arc,
)
from .primary_direction_ptolemy import (
    PtolemaicParallelRelation,
    PtolemaicParallelTarget,
    project_ptolemaic_declination_point,
)
from .primary_direction_relations import (
    PrimaryDirectionRelationPolicy,
    PrimaryDirectionRelationalKind,
    default_positional_relation_policy,
    placidian_rapt_parallel_relation_policy,
    ptolemaic_parallel_relation_policy,
    zodiacal_aspect_relation_policy,
)
from .primary_direction_spaces import PrimaryDirectionSpace
from .primary_direction_targets import (
    PrimaryDirectionTargetClass,
    PrimaryDirectionTargetPolicy,
    primary_direction_target_truth,
)

__all__ = [
    "DIRECT",
    "CONVERSE",
    "PrimaryDirectionSpace",
    "PrimaryDirectionMotion",
    "PrimaryDirectionsPreset",
    "PrimaryDirectionConverseDoctrine",
    "PrimaryDirectionsConditionState",
    "PrimaryDirectionsPolicy",
    "primary_directions_policy_preset",
    "PrimaryDirectionKey",
    "PrimaryDirectionKeyFamily",
    "PrimaryDirectionKeyPolicy",
    "PrimaryDirectionLatitudeDoctrine",
    "PrimaryDirectionLatitudePolicy",
    "PrimaryDirectionLatitudeSource",
    "PrimaryDirectionLatitudeSourcePolicy",
    "PrimaryDirectionMethod",
    "MorinusAspectContext",
    "PlacidianRaptParallelTarget",
    "PtolemaicParallelRelation",
    "PtolemaicParallelTarget",
    "PrimaryDirectionRelationalKind",
    "PrimaryDirectionRelationPolicy",
    "default_positional_relation_policy",
    "zodiacal_aspect_relation_policy",
    "ptolemaic_parallel_relation_policy",
    "placidian_rapt_parallel_relation_policy",
    "PrimaryDirectionPerfectionKind",
    "PrimaryDirectionPerfectionPolicy",
    "PrimaryDirectionTargetClass",
    "PrimaryDirectionTargetPolicy",
    "SpeculumEntry",
    "PrimaryArc",
    "PrimaryDirectionRelation",
    "PrimaryDirectionRelationProfile",
    "PrimaryDirectionsSignificatorProfile",
    "PrimaryDirectionsAggregateProfile",
    "PrimaryDirectionsNetworkNode",
    "PrimaryDirectionsNetworkEdge",
    "PrimaryDirectionsNetworkProfile",
    "speculum",
    "find_primary_arcs",
    "relate_primary_arc",
    "evaluate_primary_direction_relations",
    "evaluate_primary_direction_condition",
    "evaluate_primary_directions_aggregate",
    "evaluate_primary_directions_network",
]

if TYPE_CHECKING:
    from .__init__ import Chart
    from .houses import HouseCusps


_DEFAULT_SOLAR_RATE = 360.0 / 365.25

DIRECT = "D"
CONVERSE = "C"

class PrimaryDirectionMotion(StrEnum):
    DIRECT = "direct"
    CONVERSE = "converse"


class PrimaryDirectionsPreset(StrEnum):
    PLACIDUS_MUNDANE = "placidus_mundane"
    PLACIDIAN_CLASSIC_MUNDANE = "placidian_classic_mundane"
    PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT = "placidian_mundane_rapt_parallel_direct"
    PTOLEMY_MUNDANE = "ptolemy_mundane"
    PTOLEMY_ZODIACAL_ASPECT = "ptolemy_zodiacal_aspect"
    PTOLEMY_ZODIACAL_PARALLEL = "ptolemy_zodiacal_parallel"
    MERIDIAN_MUNDANE = "meridian_mundane"
    MERIDIAN_ZODIACAL = "meridian_zodiacal"
    MERIDIAN_ZODIACAL_ASPECT = "meridian_zodiacal_aspect"
    MORINUS_MUNDANE = "morinus_mundane"
    MORINUS_ZODIACAL = "morinus_zodiacal"
    MORINUS_ZODIACAL_ASPECT = "morinus_zodiacal_aspect"
    REGIOMONTANUS_MUNDANE = "regiomontanus_mundane"
    REGIOMONTANUS_ZODIACAL = "regiomontanus_zodiacal"
    REGIOMONTANUS_ZODIACAL_ASPECT = "regiomontanus_zodiacal_aspect"
    REGIOMONTANUS_ZODIACAL_SIGNIFICATOR_CONDITIONED = "regiomontanus_zodiacal_significator_conditioned"
    CAMPANUS_MUNDANE = "campanus_mundane"
    CAMPANUS_ZODIACAL = "campanus_zodiacal"
    CAMPANUS_ZODIACAL_ASPECT = "campanus_zodiacal_aspect"
    TOPOCENTRIC_MUNDANE = "topocentric_mundane"
    TOPOCENTRIC_ZODIACAL = "topocentric_zodiacal"
    TOPOCENTRIC_ZODIACAL_ASPECT = "topocentric_zodiacal_aspect"


class PrimaryDirectionsConditionState(StrEnum):
    DIRECT_ONLY = "direct_only"
    CONVERSE_ONLY = "converse_only"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsPolicy:
    method: PrimaryDirectionMethod = PrimaryDirectionMethod.PLACIDUS_MUNDANE
    space: PrimaryDirectionSpace = PrimaryDirectionSpace.IN_MUNDO
    include_converse: bool = True
    converse_doctrine: PrimaryDirectionConverseDoctrine = (
        PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    )
    key_policy: PrimaryDirectionKeyPolicy = field(default_factory=PrimaryDirectionKeyPolicy)
    latitude_policy: PrimaryDirectionLatitudePolicy = field(default_factory=PrimaryDirectionLatitudePolicy)
    latitude_source_policy: PrimaryDirectionLatitudeSourcePolicy = field(
        default_factory=PrimaryDirectionLatitudeSourcePolicy
    )
    relation_policy: PrimaryDirectionRelationPolicy = field(default_factory=PrimaryDirectionRelationPolicy)
    target_policy: PrimaryDirectionTargetPolicy = field(default_factory=PrimaryDirectionTargetPolicy)
    perfection_policy: PrimaryDirectionPerfectionPolicy = field(default_factory=PrimaryDirectionPerfectionPolicy)
    morinus_aspect_contexts: tuple[MorinusAspectContext, ...] = ()
    ptolemaic_parallel_targets: tuple[PtolemaicParallelTarget, ...] = ()
    placidian_rapt_parallel_targets: tuple[PlacidianRaptParallelTarget, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.method, PrimaryDirectionMethod):
            raise ValueError(f"Unsupported primary direction method: {self.method}")
        if not isinstance(self.space, PrimaryDirectionSpace):
            raise ValueError(f"Unsupported primary direction space: {self.space}")
        if self.method is not PrimaryDirectionMethod.PLACIDUS_MUNDANE:
            if self.method not in (
                PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
                PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
                PrimaryDirectionMethod.MERIDIAN,
                PrimaryDirectionMethod.MORINUS,
                PrimaryDirectionMethod.REGIOMONTANUS,
                PrimaryDirectionMethod.CAMPANUS,
                PrimaryDirectionMethod.TOPOCENTRIC,
            ):
                raise ValueError(f"Unsupported primary direction method: {self.method}")
        if self.space not in (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionSpace.IN_ZODIACO):
            raise ValueError(f"Unsupported primary direction space: {self.space}")
        if self.include_converse and self.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: include_converse requires converse doctrine"
            )
        if (not self.include_converse) and (
            self.converse_doctrine is not PrimaryDirectionConverseDoctrine.DIRECT_ONLY
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: direct-only policy must disable converse"
            )
        if self.space is PrimaryDirectionSpace.IN_MUNDO:
            if self.latitude_policy.doctrine is not PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED:
                raise ValueError(
                    "PrimaryDirectionsPolicy invariant failed: in_mundo requires mundane-preserved latitude doctrine"
                )
            if self.latitude_source_policy.source is not PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE:
                raise ValueError(
                    "PrimaryDirectionsPolicy invariant failed: mundane-preserved latitude currently requires promissor-native source"
                )
            if self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION:
                raise ValueError(
                    "PrimaryDirectionsPolicy invariant failed: in_mundo requires mundane position perfection"
                )
        else:
            if self.latitude_policy.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED:
                if self.latitude_source_policy.source is not PrimaryDirectionLatitudeSource.ASSIGNED_ZERO:
                    raise ValueError(
                        "PrimaryDirectionsPolicy invariant failed: zodiacal-suppressed latitude currently requires assigned-zero source"
                    )
                if self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION:
                    raise ValueError(
                        "PrimaryDirectionsPolicy invariant failed: zodiacal-suppressed branch requires zodiacal longitude perfection"
                    )
            elif self.latitude_policy.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED:
                if self.latitude_source_policy.source not in (
                    PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE,
                    PrimaryDirectionLatitudeSource.ASPECT_INHERITED,
                ):
                    raise ValueError(
                        "PrimaryDirectionsPolicy invariant failed: zodiacal-promissor-retained latitude currently requires promissor-native or aspect-inherited source"
                    )
                if self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION:
                    raise ValueError(
                        "PrimaryDirectionsPolicy invariant failed: zodiacal-promissor-retained branch requires zodiacal projected perfection"
                    )
            elif self.latitude_policy.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED:
                if self.latitude_source_policy.source is not PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE:
                    raise ValueError(
                        "PrimaryDirectionsPolicy invariant failed: zodiacal-significator-conditioned latitude currently requires significator-native source"
                    )
                if self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION:
                    raise ValueError(
                        "PrimaryDirectionsPolicy invariant failed: zodiacal-significator-conditioned branch requires zodiacal projected perfection"
                    )
            else:
                raise ValueError(
                    "PrimaryDirectionsPolicy invariant failed: in_zodiaco currently requires explicit admitted zodiacal latitude doctrine"
                )
        source_names = [context.source_name for context in self.morinus_aspect_contexts]
        if len(set(source_names)) != len(source_names):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: morinus_aspect_contexts must be unique by source_name"
            )
        parallel_names = [target.name for target in self.ptolemaic_parallel_targets]
        if len(set(parallel_names)) != len(parallel_names):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: ptolemaic_parallel_targets must be unique by name"
            )
        rapt_names = [target.name for target in self.placidian_rapt_parallel_targets]
        if len(set(rapt_names)) != len(rapt_names):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: placidian_rapt_parallel_targets must be unique by name"
            )
        if self.ptolemaic_parallel_targets and self.method is not PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: ptolemaic_parallel_targets currently require the Ptolemy method"
            )
        if self.ptolemaic_parallel_targets and self.space is not PrimaryDirectionSpace.IN_ZODIACO:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: ptolemaic_parallel_targets currently require in_zodiaco"
            )
        required_parallel_kinds = {
            (
                PrimaryDirectionRelationalKind.PARALLEL
                if target.relation is PtolemaicParallelRelation.PARALLEL
                else PrimaryDirectionRelationalKind.CONTRA_PARALLEL
            )
            for target in self.ptolemaic_parallel_targets
        }
        if not required_parallel_kinds <= self.relation_policy.admitted_kinds:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: ptolemaic_parallel_targets require matching admitted relation kinds"
            )
        if (
            self.placidian_rapt_parallel_targets
            and self.method is not PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: placidian_rapt_parallel_targets currently require the Placidian classic method"
            )
        if self.placidian_rapt_parallel_targets and self.space is not PrimaryDirectionSpace.IN_MUNDO:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: placidian_rapt_parallel_targets currently require in_mundo"
            )
        if self.placidian_rapt_parallel_targets and self.include_converse:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: current placidian_rapt_parallel_targets admission is direct-only"
            )
        if self.placidian_rapt_parallel_targets and (
            PrimaryDirectionRelationalKind.RAPT_PARALLEL not in self.relation_policy.admitted_kinds
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: placidian_rapt_parallel_targets require admitted rapt_parallel relation kind"
            )

    @property
    def admitted_motions(self) -> tuple[PrimaryDirectionMotion, ...]:
        if self.include_converse:
            return (PrimaryDirectionMotion.DIRECT, PrimaryDirectionMotion.CONVERSE)
        return (PrimaryDirectionMotion.DIRECT,)


def _preset_converse_doctrine(include_converse: bool) -> PrimaryDirectionConverseDoctrine:
    if include_converse:
        return PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    return PrimaryDirectionConverseDoctrine.DIRECT_ONLY


def _aspect_target_policy() -> PrimaryDirectionTargetPolicy:
    return PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.HOUSE_CUSP,
            }
        ),
        admitted_promissor_classes=frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            }
        ),
    )


def primary_directions_policy_preset(
    preset: PrimaryDirectionsPreset,
    *,
    include_converse: bool = True,
    key_policy: PrimaryDirectionKeyPolicy | None = None,
    morinus_aspect_contexts: tuple[MorinusAspectContext, ...] = (),
    ptolemaic_parallel_targets: tuple[PtolemaicParallelTarget, ...] = (),
    placidian_rapt_parallel_targets: tuple[PlacidianRaptParallelTarget, ...] = (),
) -> PrimaryDirectionsPolicy:
    base_kwargs = {
        "include_converse": include_converse,
        "converse_doctrine": _preset_converse_doctrine(include_converse),
        "key_policy": key_policy if key_policy is not None else PrimaryDirectionKeyPolicy(),
    }
    if preset is PrimaryDirectionsPreset.PLACIDUS_MUNDANE:
        return PrimaryDirectionsPolicy(**base_kwargs)
    if preset is PrimaryDirectionsPreset.PLACIDIAN_CLASSIC_MUNDANE:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT:
        if include_converse:
            raise ValueError(
                "PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT is direct-only"
            )
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            relation_policy=placidian_rapt_parallel_relation_policy(),
            placidian_rapt_parallel_targets=placidian_rapt_parallel_targets,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_MUNDANE:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION),
            relation_policy=ptolemaic_parallel_relation_policy(),
            target_policy=_aspect_target_policy(),
            ptolemaic_parallel_targets=ptolemaic_parallel_targets,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.MERIDIAN_MUNDANE:
        return PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.MERIDIAN, **base_kwargs)
    if preset is PrimaryDirectionsPreset.MERIDIAN_ZODIACAL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MERIDIAN,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=default_positional_relation_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.MERIDIAN_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MERIDIAN,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASPECT_INHERITED),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.MORINUS_MUNDANE:
        return PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.MORINUS, **base_kwargs)
    if preset is PrimaryDirectionsPreset.MORINUS_ZODIACAL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MORINUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=default_positional_relation_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.MORINUS_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MORINUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASPECT_INHERITED),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            morinus_aspect_contexts=morinus_aspect_contexts,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.REGIOMONTANUS_MUNDANE:
        return PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.REGIOMONTANUS, **base_kwargs)
    if preset is PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=default_positional_relation_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASPECT_INHERITED),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL_SIGNIFICATOR_CONDITIONED:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.CAMPANUS_MUNDANE:
        return PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.CAMPANUS, **base_kwargs)
    if preset is PrimaryDirectionsPreset.CAMPANUS_ZODIACAL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.CAMPANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=default_positional_relation_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.CAMPANUS_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.CAMPANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASPECT_INHERITED),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.TOPOCENTRIC_MUNDANE:
        return PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.TOPOCENTRIC, **base_kwargs)
    if preset is PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.TOPOCENTRIC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=default_positional_relation_policy(),
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.TOPOCENTRIC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASPECT_INHERITED),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            target_policy=_aspect_target_policy(),
            **base_kwargs,
        )
    raise ValueError(f"Unsupported primary-directions preset: {preset}")


@dataclass(slots=True)
class SpeculumEntry:
    name: str
    lon: float
    lat: float
    ra: float
    dec: float
    ha: float
    dsa: float
    nsa: float
    upper: bool
    f: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("SpeculumEntry requires a non-empty name")
        if not (0.0 <= self.lon < 360.0):
            raise ValueError(f"SpeculumEntry longitude must be normalized: {self.lon}")
        if not (0.0 <= self.ra < 360.0):
            raise ValueError(f"SpeculumEntry right ascension must be normalized: {self.ra}")
        if not (-90.0 <= self.dec <= 90.0):
            raise ValueError(f"SpeculumEntry declination out of range: {self.dec}")
        if not (-180.0 <= self.ha <= 180.0):
            raise ValueError(f"SpeculumEntry hour angle out of range: {self.ha}")
        if not (0.0 <= self.dsa <= 180.0):
            raise ValueError(f"SpeculumEntry DSA out of range: {self.dsa}")
        if not (0.0 <= self.nsa <= 180.0):
            raise ValueError(f"SpeculumEntry NSA out of range: {self.nsa}")
        if abs((self.dsa + self.nsa) - 180.0) > 1e-7:
            raise ValueError("SpeculumEntry invariant failed: dsa + nsa must equal 180")
        if not (-2.0 - 1e-9 <= self.f <= 2.0 + 1e-9):
            raise ValueError(f"SpeculumEntry mundane fraction out of range: {self.f}")
        if self.upper != (abs(self.ha) <= self.dsa + 1e-9):
            raise ValueError(
                "SpeculumEntry invariant failed: upper hemisphere flag does not match HA/DSA"
            )

    @classmethod
    def build(
        cls,
        name: str,
        lon: float,
        lat: float,
        armc: float,
        obliquity: float,
        geo_lat: float,
    ) -> SpeculumEntry:
        eps = obliquity * DEG2RAD
        phi = geo_lat * DEG2RAD
        l = lon * DEG2RAD
        b = lat * DEG2RAD

        sin_dec = math.sin(b) * math.cos(eps) + math.cos(b) * math.sin(eps) * math.sin(l)
        sin_dec = max(-1.0, min(1.0, sin_dec))
        dec_r = math.asin(sin_dec)

        y = math.sin(l) * math.cos(eps) - math.tan(b) * math.sin(eps)
        ra = math.degrees(math.atan2(y, math.cos(l))) % 360.0
        dec = math.degrees(dec_r)

        ha = (armc - ra + 180.0) % 360.0 - 180.0

        arg = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec_r)))
        dsa = math.degrees(math.acos(arg))
        nsa = 180.0 - dsa

        upper = abs(ha) <= dsa + 1e-9
        if upper:
            f = ha / dsa if dsa > 1e-9 else 0.0
        elif ha > 0:
            f = 1.0 + (ha - dsa) / nsa if nsa > 1e-9 else 1.0
        else:
            f = -1.0 - (-ha - dsa) / nsa if nsa > 1e-9 else -1.0

        return cls(
            name=name,
            lon=lon % 360.0,
            lat=lat,
            ra=ra,
            dec=dec,
            ha=ha,
            dsa=dsa,
            nsa=nsa,
            upper=upper,
            f=f,
        )

    @property
    def hemisphere(self) -> str:
        return "upper" if self.upper else "lower"

    @property
    def is_eastern(self) -> bool:
        return self.ha < 0.0

    @property
    def is_western(self) -> bool:
        return self.ha > 0.0

    @property
    def mundane_sector(self) -> str:
        if self.upper:
            return "upper_east" if self.is_eastern else "upper_west"
        return "lower_east" if self.is_eastern else "lower_west"

    def __repr__(self) -> str:
        hem = "UH" if self.upper else "LH"
        return (
            f"Speculum({self.name:<12} "
            f"lon={self.lon:7.3f}deg RA={self.ra:7.3f}deg Dec={self.dec:+7.3f}deg "
            f"HA={self.ha:+8.3f}deg DSA={self.dsa:6.3f}deg "
            f"f={self.f:+6.3f} {hem})"
        )


@dataclass(slots=True)
class PrimaryArc:
    significator: str
    promissor: str
    arc: float
    direction: str
    method: PrimaryDirectionMethod = field(default=PrimaryDirectionMethod.PLACIDUS_MUNDANE)
    space: PrimaryDirectionSpace = field(default=PrimaryDirectionSpace.IN_MUNDO)
    motion: PrimaryDirectionMotion = field(default=PrimaryDirectionMotion.DIRECT)
    solar_rate: float = field(default=_DEFAULT_SOLAR_RATE)

    def __post_init__(self) -> None:
        if not self.significator or not self.promissor:
            raise ValueError("PrimaryArc requires non-empty significator and promissor")
        if self.significator == self.promissor:
            raise ValueError("PrimaryArc invariant failed: self-directions are not admitted")
        if self.arc <= 0.0:
            raise ValueError("PrimaryArc invariant failed: arc must be positive")
        if self.solar_rate <= 0.0:
            raise ValueError("PrimaryArc invariant failed: solar_rate must be positive")
        expected_direction = DIRECT if self.motion is PrimaryDirectionMotion.DIRECT else CONVERSE
        if self.direction != expected_direction:
            raise ValueError("PrimaryArc invariant failed: direction must match motion")
        if not isinstance(self.method, PrimaryDirectionMethod):
            raise ValueError(f"Unsupported primary direction method: {self.method}")
        if not isinstance(self.space, PrimaryDirectionSpace):
            raise ValueError(f"Unsupported primary direction space: {self.space}")
        if self.method not in (
            PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            PrimaryDirectionMethod.MERIDIAN,
            PrimaryDirectionMethod.MORINUS,
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC,
        ):
            raise ValueError(f"Unsupported primary direction method: {self.method}")
        if self.space not in (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionSpace.IN_ZODIACO):
            raise ValueError(f"Unsupported primary direction space: {self.space}")

    def years(self, key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD) -> float:
        return convert_arc_to_time(self.arc, key, solar_rate=self.solar_rate)

    @property
    def is_direct(self) -> bool:
        return self.motion is PrimaryDirectionMotion.DIRECT

    @property
    def is_converse(self) -> bool:
        return self.motion is PrimaryDirectionMotion.CONVERSE

    @property
    def key_family(self) -> PrimaryDirectionKeyFamily:
        return PrimaryDirectionKeyPolicy().family

    def __repr__(self) -> str:
        return (
            f"PrimaryArc({self.significator} <- {self.promissor}  "
            f"arc={self.arc:.4f}  {self.direction}  "
            f"{self.years():.2f} yr [Naibod])"
        )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelation:
    arc: PrimaryArc
    relation_kind: PrimaryDirectionPerfectionKind
    converse_doctrine: PrimaryDirectionConverseDoctrine
    key_policy: PrimaryDirectionKeyPolicy

    def __post_init__(self) -> None:
        if self.relation_kind not in (
            PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION,
        ):
            raise ValueError(f"Unsupported primary direction relation kind: {self.relation_kind}")
        if (
            self.arc.motion is PrimaryDirectionMotion.CONVERSE
            and self.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY
        ):
            raise ValueError(
                "PrimaryDirectionRelation invariant failed: converse arc not admitted by direct-only doctrine"
            )

    @property
    def years(self) -> float:
        return self.arc.years(self.key_policy.key)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationProfile:
    arc: PrimaryArc
    detected_relation: PrimaryDirectionRelation
    admitted_relations: tuple[PrimaryDirectionRelation, ...]
    scored_relations: tuple[PrimaryDirectionRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.arc != self.arc:
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: detected relation must belong to arc"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionRelationProfile invariant failed: scored relations must be admitted"
                )

    @property
    def admitted_relation_kinds(self) -> tuple[PrimaryDirectionPerfectionKind, ...]:
        return tuple(relation.relation_kind for relation in self.admitted_relations)

    @property
    def scored_relation_kinds(self) -> tuple[PrimaryDirectionPerfectionKind, ...]:
        return tuple(relation.relation_kind for relation in self.scored_relations)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsSignificatorProfile:
    significator: str
    arcs: tuple[PrimaryArc, ...]
    relation_profiles: tuple[PrimaryDirectionRelationProfile, ...]
    state: PrimaryDirectionsConditionState
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float

    def __post_init__(self) -> None:
        if not self.significator:
            raise ValueError("PrimaryDirectionsSignificatorProfile requires a significator")
        if not self.arcs:
            raise ValueError("PrimaryDirectionsSignificatorProfile requires at least one arc")
        if len(self.arcs) != len(self.relation_profiles):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: arcs/profiles length mismatch"
            )
        if any(arc.significator != self.significator for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: all arcs must share significator"
            )
        if self.direct_count + self.converse_count != len(self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: direction counts do not match arc count"
            )
        if self.nearest_arc != min(arc.arc for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: nearest_arc mismatch"
            )
        if self.farthest_arc != max(arc.arc for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: farthest_arc mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsAggregateProfile:
    profiles: tuple[PrimaryDirectionsSignificatorProfile, ...]
    total_arcs: int
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float
    strongest_significator: str
    weakest_significator: str

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionsAggregateProfile requires at least one significator profile")
        unique_significators = {profile.significator for profile in self.profiles}
        if len(unique_significators) != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: duplicate significator profiles"
            )
        computed_total = sum(len(profile.arcs) for profile in self.profiles)
        if self.total_arcs != computed_total:
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: total_arcs mismatch"
            )
        if self.direct_count != sum(profile.direct_count for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: direct_count mismatch"
            )
        if self.converse_count != sum(profile.converse_count for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: converse_count mismatch"
            )
        if self.nearest_arc != min(profile.nearest_arc for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: nearest_arc mismatch"
            )
        if self.farthest_arc != max(profile.farthest_arc for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: farthest_arc mismatch"
            )
        strength_map = {profile.significator: len(profile.arcs) for profile in self.profiles}
        strongest = max(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
        weakest = min(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
        if self.strongest_significator != strongest:
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: strongest_significator mismatch"
            )
        if self.weakest_significator != weakest:
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: weakest_significator mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkNode:
    name: str
    incoming_count: int
    outgoing_count: int
    total_count: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PrimaryDirectionsNetworkNode requires a non-empty name")
        if self.total_count != self.incoming_count + self.outgoing_count:
            raise ValueError(
                "PrimaryDirectionsNetworkNode invariant failed: total_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkEdge:
    promissor: str
    significator: str
    count: int
    nearest_arc: float

    def __post_init__(self) -> None:
        if not self.promissor or not self.significator:
            raise ValueError("PrimaryDirectionsNetworkEdge requires endpoint names")
        if self.promissor == self.significator:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: self-edge not admitted")
        if self.count <= 0:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: count must be positive")
        if self.nearest_arc <= 0.0:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: nearest_arc must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkProfile:
    nodes: tuple[PrimaryDirectionsNetworkNode, ...]
    edges: tuple[PrimaryDirectionsNetworkEdge, ...]
    most_connected: str
    isolated: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionsNetworkProfile requires at least one node")
        node_names = [node.name for node in self.nodes]
        if len(set(node_names)) != len(node_names):
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: duplicate node names"
            )
        node_set = set(node_names)
        for edge in self.edges:
            if edge.promissor not in node_set or edge.significator not in node_set:
                raise ValueError(
                    "PrimaryDirectionsNetworkProfile invariant failed: dangling edge"
                )
        if set(self.isolated) - node_set:
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: isolated list contains unknown node"
            )
        computed_most = max(self.nodes, key=lambda node: (node.total_count, node.name)).name
        if self.most_connected != computed_most:
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: most_connected mismatch"
            )


def _project_zodiacal_point(
    name: str,
    longitude: float,
    latitude: float,
    *,
    armc: float,
    obliquity: float,
    geo_lat: float,
) -> SpeculumEntry:
    """Project one explicit zodiacal point into the active equatorial/mundane frame."""
    return SpeculumEntry.build(
        name,
        longitude % 360.0,
        latitude,
        armc,
        obliquity,
        geo_lat,
    )


def _house_cusp_entries(
    requested_names: Iterable[str],
    houses: HouseCusps,
    *,
    armc: float,
    obliquity: float,
    geo_lat: float,
) -> dict[str, SpeculumEntry]:
    derived: dict[str, SpeculumEntry] = {}
    for name in requested_names:
        try:
            truth = primary_direction_target_truth(name)
        except ValueError:
            continue
        if truth.target_class is not PrimaryDirectionTargetClass.HOUSE_CUSP:
            continue
        cusp_number = int(name[1:])
        derived[name] = SpeculumEntry.build(
            name,
            houses.cusps[cusp_number - 1],
            0.0,
            armc,
            obliquity,
            geo_lat,
        )
    return derived


def _required_relation_kinds_for_requested_promissors(
    requested_names: Iterable[str],
) -> set[PrimaryDirectionRelationalKind]:
    required: set[PrimaryDirectionRelationalKind] = set()
    for name in requested_names:
        if name.endswith(" Rapt Parallel"):
            required.add(PrimaryDirectionRelationalKind.RAPT_PARALLEL)
            continue
        try:
            truth = primary_direction_target_truth(name)
        except ValueError:
            continue
        if truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT:
            required.add(PrimaryDirectionRelationalKind.ZODIACAL_ASPECT)
    return required


def _zodiacal_promissor_entries(
    requested_names: Iterable[str],
    base_entries: dict[str, SpeculumEntry],
    *,
    method: PrimaryDirectionMethod,
    armc: float,
    obliquity: float,
    geo_lat: float,
    latitude_doctrine: PrimaryDirectionLatitudeDoctrine,
    latitude_source: PrimaryDirectionLatitudeSource,
    morinus_contexts: dict[str, MorinusAspectContext] | None = None,
) -> dict[str, SpeculumEntry]:
    derived: dict[str, SpeculumEntry] = {}
    for name in requested_names:
        if name in derived:
            continue
        source_entry = base_entries.get(name)
        if source_entry is not None:
            latitude = (
                0.0
                if latitude_doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                else source_entry.lat
            )
            derived[name] = _project_zodiacal_point(
                name,
                source_entry.lon,
                latitude,
                armc=armc,
                obliquity=obliquity,
                geo_lat=geo_lat,
            )
            continue
        try:
            truth = primary_direction_target_truth(name)
        except ValueError:
            continue
        if truth.target_class is not PrimaryDirectionTargetClass.ASPECTUAL_POINT:
            continue
        assert truth.source_name is not None
        assert truth.aspect_angle is not None
        if latitude_source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE:
            raise ValueError(
                "Aspectual zodiacal promissors require assigned_zero or aspect_inherited latitude source"
            )
        source = base_entries.get(truth.source_name)
        if source is None:
            continue
        if (
            method is PrimaryDirectionMethod.MORINUS
            and morinus_contexts is not None
            and truth.source_name in morinus_contexts
        ):
            context = morinus_contexts[truth.source_name]
            morinus_lon, morinus_lat = project_morinus_aspect_point(
                longitude=source.lon,
                latitude=source.lat,
                maximum_latitude=context.maximum_latitude,
                moving_toward_maximum=context.moving_toward_maximum,
                aspect_angle=truth.aspect_angle,
            )
            derived[name] = _project_zodiacal_point(
                name,
                morinus_lon,
                morinus_lat,
                armc=armc,
                obliquity=obliquity,
                geo_lat=geo_lat,
            )
            continue
        latitude = source.lat if latitude_source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED else 0.0
        derived[name] = _project_zodiacal_point(
            name,
            (source.lon + truth.aspect_angle) % 360.0,
            latitude,
            armc=armc,
            obliquity=obliquity,
            geo_lat=geo_lat,
        )
    return derived


def _zodiacal_pairwise_promissor(
    prom_name: str,
    *,
    sig_entry: SpeculumEntry,
    base_entries: dict[str, SpeculumEntry],
    armc: float,
    obliquity: float,
    geo_lat: float,
    latitude_doctrine: PrimaryDirectionLatitudeDoctrine,
    latitude_source: PrimaryDirectionLatitudeSource,
) -> SpeculumEntry | None:
    if latitude_doctrine is not PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED:
        return None
    if latitude_source is not PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE:
        raise ValueError(
            "Significator-conditioned zodiacal promissors require significator_native latitude source"
        )
    base_entry = base_entries.get(prom_name)
    if base_entry is not None:
        return _project_zodiacal_point(
            prom_name,
            base_entry.lon,
            sig_entry.lat,
            armc=armc,
            obliquity=obliquity,
            geo_lat=geo_lat,
        )
    truth = primary_direction_target_truth(prom_name)
    if truth.target_class is not PrimaryDirectionTargetClass.ASPECTUAL_POINT:
        return None
    assert truth.source_name is not None
    assert truth.aspect_angle is not None
    source = base_entries.get(truth.source_name)
    if source is None:
        return None
    return _project_zodiacal_point(
        prom_name,
        (source.lon + truth.aspect_angle) % 360.0,
        sig_entry.lat,
        armc=armc,
        obliquity=obliquity,
        geo_lat=geo_lat,
    )


def _ptolemaic_declination_promissor_entries(
    targets: Iterable[PtolemaicParallelTarget],
    base_entries: dict[str, SpeculumEntry],
    *,
    armc: float,
    obliquity: float,
    geo_lat: float,
) -> dict[str, SpeculumEntry]:
    derived: dict[str, SpeculumEntry] = {}
    for target in targets:
        source = base_entries.get(target.source_name)
        if source is None:
            continue
        equivalent_longitude = project_ptolemaic_declination_point(
            source_longitude=source.lon,
            source_declination=source.dec,
            obliquity=obliquity,
            relation=target.relation,
        )
        derived[target.name] = _project_zodiacal_point(
            target.name,
            equivalent_longitude,
            0.0,
            armc=armc,
            obliquity=obliquity,
            geo_lat=geo_lat,
        )
    return derived


def _state_for_arcs(arcs: tuple[PrimaryArc, ...]) -> PrimaryDirectionsConditionState:
    direct_count = sum(1 for arc in arcs if arc.is_direct)
    converse_count = len(arcs) - direct_count
    if converse_count == 0:
        return PrimaryDirectionsConditionState.DIRECT_ONLY
    if direct_count == 0:
        return PrimaryDirectionsConditionState.CONVERSE_ONLY
    return PrimaryDirectionsConditionState.MIXED


def _sorted_profiles(profiles: Iterable[PrimaryDirectionsSignificatorProfile]) -> tuple[PrimaryDirectionsSignificatorProfile, ...]:
    return tuple(sorted(profiles, key=lambda profile: (profile.significator, profile.nearest_arc)))


def speculum(
    chart: Chart,
    houses: HouseCusps,
    geo_lat: float,
    obliquity: float | None = None,
    bodies: list[str] | None = None,
) -> list[SpeculumEntry]:
    obl = obliquity if obliquity is not None else chart.obliquity
    armc = houses.armc

    entries: list[SpeculumEntry] = []
    planet_names = bodies if bodies is not None else list(chart.planets.keys())
    for name in planet_names:
        if name in chart.planets:
            p = chart.planets[name]
            entries.append(SpeculumEntry.build(name, p.longitude, p.latitude, armc, obl, geo_lat))

    for name, nd in chart.nodes.items():
        entries.append(SpeculumEntry.build(name, nd.longitude, 0.0, armc, obl, geo_lat))

    for ang_name, ang_lon in [
        ("ASC", houses.asc),
        ("MC", houses.mc),
        ("DSC", houses.dsc),
        ("IC", houses.ic),
    ]:
        entries.append(SpeculumEntry.build(ang_name, ang_lon, 0.0, armc, obl, geo_lat))

    return entries


def find_primary_arcs(
    chart: Chart,
    houses: HouseCusps,
    geo_lat: float,
    max_arc: float = 90.0,
    include_converse: bool = True,
    significators: list[str] | None = None,
    promissors: list[str] | None = None,
    solar_speed: float | None = None,
    obliquity: float | None = None,
    policy: PrimaryDirectionsPolicy | None = None,
) -> list[PrimaryArc]:
    resolved_policy = (
        policy
        if policy is not None
        else PrimaryDirectionsPolicy(
            include_converse=include_converse,
            converse_doctrine=(
                PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
                if include_converse
                else PrimaryDirectionConverseDoctrine.DIRECT_ONLY
            ),
        )
    )
    obl = obliquity if obliquity is not None else chart.obliquity

    if max_arc <= 0.0:
        raise ValueError("find_primary_arcs requires max_arc > 0")

    if solar_speed is not None:
        s_rate = abs(solar_speed)
    else:
        sun = chart.planets.get(Body.SUN)
        s_rate = abs(sun.speed) if sun else _DEFAULT_SOLAR_RATE
    if s_rate <= 0.0:
        s_rate = _DEFAULT_SOLAR_RATE

    spec = speculum(chart, houses, geo_lat, obliquity=obl)
    sp_map = {e.name: e for e in spec}
    oa_asc = sp_map["ASC"].ra

    all_names = list(sp_map.keys())
    sig_candidates = set(significators) if significators is not None else set(all_names)
    ptolemaic_parallel_targets = (
        tuple(
            target
            for target in resolved_policy.ptolemaic_parallel_targets
            if promissors is None or target.name in promissors
        )
        if resolved_policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
        else ()
    )
    ptolemaic_parallel_names = {target.name for target in ptolemaic_parallel_targets}
    placidian_rapt_parallel_targets = (
        tuple(
            target
            for target in resolved_policy.placidian_rapt_parallel_targets
            if promissors is None or target.name in promissors
        )
        if (
            resolved_policy.method is PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC
            and resolved_policy.space is PrimaryDirectionSpace.IN_MUNDO
        )
        else ()
    )
    placidian_rapt_parallel_names = {target.name for target in placidian_rapt_parallel_targets}
    prom_candidates = (
        set(promissors)
        if promissors is not None
        else (set(all_names) | ptolemaic_parallel_names | placidian_rapt_parallel_names)
    )
    candidate_names = set(all_names) | sig_candidates | prom_candidates
    required_relation_kinds = _required_relation_kinds_for_requested_promissors(prom_candidates)
    required_relation_kinds |= {
        (
            PrimaryDirectionRelationalKind.PARALLEL
            if target.relation is PtolemaicParallelRelation.PARALLEL
            else PrimaryDirectionRelationalKind.CONTRA_PARALLEL
        )
        for target in ptolemaic_parallel_targets
    }
    if placidian_rapt_parallel_targets:
        required_relation_kinds.add(PrimaryDirectionRelationalKind.RAPT_PARALLEL)
    if not required_relation_kinds <= resolved_policy.relation_policy.admitted_kinds:
        raise ValueError(
            "find_primary_arcs invariant failed: requested promissors require admitted relation kinds"
        )
    target_truths = {}
    for name in candidate_names:
        try:
            target_truths[name] = primary_direction_target_truth(name)
        except ValueError:
            continue
    derived_cusps = _house_cusp_entries(
        candidate_names,
        houses,
        armc=houses.armc,
        obliquity=obl,
        geo_lat=geo_lat,
    )
    if derived_cusps:
        sp_map.update(derived_cusps)
        spec.extend(derived_cusps.values())
    prom_map: dict[str, SpeculumEntry]
    morinus_context_map = {context.source_name: context for context in resolved_policy.morinus_aspect_contexts}
    if resolved_policy.space is PrimaryDirectionSpace.IN_ZODIACO:
        if (
            resolved_policy.latitude_policy.doctrine
            is not PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
        ):
            prom_map = _zodiacal_promissor_entries(
                prom_candidates,
                sp_map,
                method=resolved_policy.method,
                armc=houses.armc,
                obliquity=obl,
                geo_lat=geo_lat,
                latitude_doctrine=resolved_policy.latitude_policy.doctrine,
                latitude_source=resolved_policy.latitude_source_policy.source,
                morinus_contexts=morinus_context_map,
            )
            if ptolemaic_parallel_targets:
                prom_map.update(
                    _ptolemaic_declination_promissor_entries(
                        ptolemaic_parallel_targets,
                        sp_map,
                        armc=houses.armc,
                        obliquity=obl,
                        geo_lat=geo_lat,
                    )
                )
        else:
            prom_map = {}
    else:
        prom_map = {entry.name: entry for entry in spec}
    sig_set = {
        name
        for name in sig_candidates
        if name in target_truths
        and target_truths[name].target_class in resolved_policy.target_policy.admitted_significator_classes
    }
    prom_set = {
        name
        for name in prom_candidates
        if name in target_truths
        and target_truths[name].target_class in resolved_policy.target_policy.admitted_promissor_classes
    }
    prom_set |= ptolemaic_parallel_names
    prom_set |= placidian_rapt_parallel_names
    placidian_rapt_parallel_map = {
        target.name: target for target in placidian_rapt_parallel_targets
    }

    results: list[PrimaryArc] = []
    for sig_e in spec:
        if sig_e.name not in sig_set:
            continue
        prom_iterable = tuple(prom_map.items())
        if placidian_rapt_parallel_targets:
            prom_iterable += tuple(
                (
                    target.name,
                    sp_map.get(target.source_name),
                )
                for target in placidian_rapt_parallel_targets
            )
        if (
            resolved_policy.space is PrimaryDirectionSpace.IN_ZODIACO
            and resolved_policy.latitude_policy.doctrine
            is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
        ):
            prom_iterable = (
                (
                    prom_name,
                    _zodiacal_pairwise_promissor(
                        prom_name,
                        sig_entry=sig_e,
                        base_entries=sp_map,
                        armc=houses.armc,
                        obliquity=obl,
                        geo_lat=geo_lat,
                        latitude_doctrine=resolved_policy.latitude_policy.doctrine,
                        latitude_source=resolved_policy.latitude_source_policy.source,
                    ),
                )
                for prom_name in prom_set
            )
        for prom_name, prom_e in prom_iterable:
            if prom_e is None:
                continue
            if prom_name not in prom_set or sig_e.name == prom_name:
                continue
            if prom_name in placidian_rapt_parallel_map:
                source_entry = sp_map.get(placidian_rapt_parallel_map[prom_name].source_name)
                if source_entry is None or source_entry.name == sig_e.name:
                    continue
                arc_dir = compute_placidian_rapt_parallel_arc(source_entry, sig_e) % 360.0
                if 0.0 < arc_dir <= max_arc:
                    results.append(
                        PrimaryArc(
                            significator=sig_e.name,
                            promissor=prom_name,
                            arc=arc_dir,
                            direction=DIRECT,
                            method=resolved_policy.method,
                            space=resolved_policy.space,
                            motion=PrimaryDirectionMotion.DIRECT,
                            solar_rate=s_rate,
                        )
                    )
                continue

            raw_dir, raw_conv = compute_primary_direction_arcs(
                resolved_policy.method,
                sig_e,
                prom_e,
                space=resolved_policy.space,
                latitude_doctrine=resolved_policy.latitude_policy.doctrine,
                geo_lat=geo_lat,
                armc=houses.armc,
                oa_asc=oa_asc,
            )
            arc_dir = raw_dir % 360.0
            arc_conv = raw_conv % 360.0

            if 0.0 < arc_dir <= max_arc:
                results.append(
                    PrimaryArc(
                        significator=sig_e.name,
                        promissor=prom_e.name,
                        arc=arc_dir,
                        direction=DIRECT,
                        method=resolved_policy.method,
                        space=resolved_policy.space,
                        motion=PrimaryDirectionMotion.DIRECT,
                        solar_rate=s_rate,
                    )
                )

            if resolved_policy.include_converse and 0.0 < arc_conv <= max_arc:
                results.append(
                    PrimaryArc(
                        significator=sig_e.name,
                        promissor=prom_e.name,
                        arc=arc_conv,
                        direction=CONVERSE,
                        method=resolved_policy.method,
                        space=resolved_policy.space,
                        motion=PrimaryDirectionMotion.CONVERSE,
                        solar_rate=s_rate,
                    )
                )

    results.sort(key=lambda arc: (arc.arc, arc.significator, arc.promissor, arc.direction))
    return results


def relate_primary_arc(
    arc: PrimaryArc,
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionRelation:
    resolved_policy = policy if policy is not None else PrimaryDirectionsPolicy()
    return PrimaryDirectionRelation(
        arc=arc,
        relation_kind=resolved_policy.perfection_policy.kind,
        converse_doctrine=resolved_policy.converse_doctrine,
        key_policy=resolved_policy.key_policy,
    )


def evaluate_primary_direction_relations(
    arc: PrimaryArc,
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionRelationProfile:
    relation = relate_primary_arc(arc, policy=policy)
    admitted = (relation,)
    scored = admitted
    return PrimaryDirectionRelationProfile(
        arc=arc,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=scored,
    )


def evaluate_primary_direction_condition(
    arcs: Iterable[PrimaryArc],
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsSignificatorProfile:
    arc_tuple = tuple(sorted(arcs, key=lambda arc: (arc.arc, arc.promissor, arc.direction)))
    if not arc_tuple:
        raise ValueError("evaluate_primary_direction_condition requires at least one arc")
    significator = arc_tuple[0].significator
    if any(arc.significator != significator for arc in arc_tuple):
        raise ValueError(
            "evaluate_primary_direction_condition requires all arcs to share one significator"
        )
    relation_profiles = tuple(
        evaluate_primary_direction_relations(arc, policy=policy) for arc in arc_tuple
    )
    direct_count = sum(1 for arc in arc_tuple if arc.is_direct)
    converse_count = len(arc_tuple) - direct_count
    return PrimaryDirectionsSignificatorProfile(
        significator=significator,
        arcs=arc_tuple,
        relation_profiles=relation_profiles,
        state=_state_for_arcs(arc_tuple),
        direct_count=direct_count,
        converse_count=converse_count,
        nearest_arc=arc_tuple[0].arc,
        farthest_arc=arc_tuple[-1].arc,
    )


def evaluate_primary_directions_aggregate(
    arcs: Iterable[PrimaryArc],
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsAggregateProfile:
    grouped: dict[str, list[PrimaryArc]] = {}
    for arc in arcs:
        grouped.setdefault(arc.significator, []).append(arc)
    if not grouped:
        raise ValueError("evaluate_primary_directions_aggregate requires at least one arc")
    profiles = _sorted_profiles(
        evaluate_primary_direction_condition(group, policy=policy)
        for group in grouped.values()
    )
    strength_map = {profile.significator: len(profile.arcs) for profile in profiles}
    strongest = max(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
    weakest = min(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
    return PrimaryDirectionsAggregateProfile(
        profiles=profiles,
        total_arcs=sum(len(profile.arcs) for profile in profiles),
        direct_count=sum(profile.direct_count for profile in profiles),
        converse_count=sum(profile.converse_count for profile in profiles),
        nearest_arc=min(profile.nearest_arc for profile in profiles),
        farthest_arc=max(profile.farthest_arc for profile in profiles),
        strongest_significator=strongest,
        weakest_significator=weakest,
    )


def evaluate_primary_directions_network(
    arcs: Iterable[PrimaryArc],
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsNetworkProfile:
    arc_tuple = tuple(arcs)
    if not arc_tuple:
        raise ValueError("evaluate_primary_directions_network requires at least one arc")

    node_names: set[str] = set()
    edge_map: dict[tuple[str, str], list[PrimaryArc]] = {}
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    for arc in arc_tuple:
        node_names.add(arc.significator)
        node_names.add(arc.promissor)
        edge_map.setdefault((arc.promissor, arc.significator), []).append(arc)
        outgoing[arc.promissor] = outgoing.get(arc.promissor, 0) + 1
        incoming[arc.significator] = incoming.get(arc.significator, 0) + 1

    nodes = tuple(
        sorted(
            (
                PrimaryDirectionsNetworkNode(
                    name=name,
                    incoming_count=incoming.get(name, 0),
                    outgoing_count=outgoing.get(name, 0),
                    total_count=incoming.get(name, 0) + outgoing.get(name, 0),
                )
                for name in node_names
            ),
            key=lambda node: node.name,
        )
    )
    edges = tuple(
        sorted(
            (
                PrimaryDirectionsNetworkEdge(
                    promissor=promissor,
                    significator=significator,
                    count=len(group),
                    nearest_arc=min(arc.arc for arc in group),
                )
                for (promissor, significator), group in edge_map.items()
            ),
            key=lambda edge: (edge.nearest_arc, edge.promissor, edge.significator),
        )
    )
    most_connected = max(nodes, key=lambda node: (node.total_count, node.name)).name
    isolated = tuple(sorted(node.name for node in nodes if node.total_count == 0))
    return PrimaryDirectionsNetworkProfile(
        nodes=nodes,
        edges=edges,
        most_connected=most_connected,
        isolated=isolated,
    )
