"""
Moira -- primary_directions/__init__.py
The primary-directions public engine package for the currently admitted
recoverable surface.

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
from numbers import Real
from typing import TYPE_CHECKING, Iterable

from ..constants import Body, DEG2RAD
from ..julian import ut_to_tt as _ut_to_tt, decimal_year as _decimal_year
from ..planets import approx_year as _pd_approx_year
from .converse import PrimaryDirectionConverseDoctrine
from .antiscia import (
    PrimaryDirectionAntisciaKind,
    PrimaryDirectionAntisciaTarget,
    project_primary_direction_antiscia_longitude,
)
from .fixed_stars import (
    PrimaryDirectionFixedStarTarget,
    resolve_primary_direction_fixed_star_point,
)
from .geometry import compute_primary_direction_arcs
from .keys import (
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    convert_arc_to_time,
)
from .latitudes import (
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionLatitudePolicy,
)
from .latitude_sources import (
    PrimaryDirectionLatitudeSource,
    PrimaryDirectionLatitudeSourcePolicy,
)
from .methods import (
    PrimaryDirectionMethod,
    classify_primary_direction_method,
    primary_direction_method_truth,
)
from .morinus import (
    MorinusAspectContext,
    project_morinus_aspect_point,
)
from .perfections import (
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionPolicy,
)
from .placidus import (
    PlacidianRaptParallelTarget,
    compute_placidian_converse_rapt_parallel_arc,
    compute_placidian_rapt_parallel_arc,
)
from .ptolemy import (
    PtolemaicParallelRelation,
    PtolemaicParallelTarget,
    project_ptolemaic_declination_point,
)
from .relations import (
    PrimaryDirectionRelationPolicy,
    PrimaryDirectionRelationalKind,
    default_positional_relation_policy,
    antiscia_relation_policy,
    placidian_rapt_parallel_relation_policy,
    ptolemaic_parallel_relation_policy,
    zodiacal_aspect_relation_policy,
)
from .spaces import PrimaryDirectionSpace
from .targets import (
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
    "PrimaryDirectionAntisciaKind",
    "PrimaryDirectionAntisciaTarget",
    "PrimaryDirectionFixedStarTarget",
    "PlacidianRaptParallelTarget",
    "PtolemaicParallelRelation",
    "PtolemaicParallelTarget",
    "PrimaryDirectionRelationalKind",
    "PrimaryDirectionRelationPolicy",
    "default_positional_relation_policy",
    "antiscia_relation_policy",
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
    from ..facade import Chart
    from ..houses import HouseCusps


_DEFAULT_SOLAR_RATE = 360.0 / 365.25

DIRECT = "D"
CONVERSE = "C"


def _finite_real(value: object, name: str) -> float:
    """Return one finite real value while rejecting bool-as-number inputs."""
    if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    return float(value)

class PrimaryDirectionMotion(StrEnum):
    """Vessel: Enumeration of primary direction motion vectors (Direct/Converse)."""
    DIRECT = "direct"
    CONVERSE = "converse"


class PrimaryDirectionsPreset(StrEnum):
    """Vessel: Collection of pre-configured primary direction calculation regimes."""
    PLACIDUS_MUNDANE = "placidus_mundane"
    PLACIDIAN_CLASSIC_MUNDANE = "placidian_classic_mundane"
    PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT = "placidian_mundane_rapt_parallel_direct"
    PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE = "placidian_mundane_rapt_parallel_converse"
    PTOLEMY_MUNDANE = "ptolemy_mundane"
    PTOLEMY_ZODIACAL_ANTISCIA = "ptolemy_zodiacal_antiscia"
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
    """Vessel: State enumeration for primary direction search completeness."""
    DIRECT_ONLY = "direct_only"
    CONVERSE_ONLY = "converse_only"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsPolicy:
    """Vessel: Governance policy for primary direction computation and relation detection."""
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
    antiscia_targets: tuple[PrimaryDirectionAntisciaTarget, ...] = ()
    ptolemaic_parallel_targets: tuple[PtolemaicParallelTarget, ...] = ()
    placidian_rapt_parallel_targets: tuple[PlacidianRaptParallelTarget, ...] = ()
    fixed_star_targets: tuple[PrimaryDirectionFixedStarTarget, ...] = ()
    placidian_rapt_parallel_motion: PrimaryDirectionMotion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.include_converse, bool):
            raise ValueError("PrimaryDirectionsPolicy include_converse must be bool")
        if not isinstance(self.method, PrimaryDirectionMethod):
            raise ValueError(f"Unsupported primary direction method: {self.method}")
        if not isinstance(self.space, PrimaryDirectionSpace):
            raise ValueError(f"Unsupported primary direction space: {self.space}")
        policy_types = (
            ("converse_doctrine", self.converse_doctrine, PrimaryDirectionConverseDoctrine),
            ("key_policy", self.key_policy, PrimaryDirectionKeyPolicy),
            ("latitude_policy", self.latitude_policy, PrimaryDirectionLatitudePolicy),
            (
                "latitude_source_policy",
                self.latitude_source_policy,
                PrimaryDirectionLatitudeSourcePolicy,
            ),
            ("relation_policy", self.relation_policy, PrimaryDirectionRelationPolicy),
            ("target_policy", self.target_policy, PrimaryDirectionTargetPolicy),
            ("perfection_policy", self.perfection_policy, PrimaryDirectionPerfectionPolicy),
        )
        for name, value, expected_type in policy_types:
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"PrimaryDirectionsPolicy {name} must be {expected_type.__name__}"
                )

        sequence_fields = (
            ("morinus_aspect_contexts", self.morinus_aspect_contexts, MorinusAspectContext),
            ("antiscia_targets", self.antiscia_targets, PrimaryDirectionAntisciaTarget),
            (
                "ptolemaic_parallel_targets",
                self.ptolemaic_parallel_targets,
                PtolemaicParallelTarget,
            ),
            (
                "placidian_rapt_parallel_targets",
                self.placidian_rapt_parallel_targets,
                PlacidianRaptParallelTarget,
            ),
            ("fixed_star_targets", self.fixed_star_targets, PrimaryDirectionFixedStarTarget),
        )
        for name, values, expected_type in sequence_fields:
            if isinstance(values, (str, bytes)):
                raise ValueError(f"PrimaryDirectionsPolicy {name} must be an iterable of vessels")
            try:
                normalized = tuple(values)
            except TypeError as exc:
                raise ValueError(
                    f"PrimaryDirectionsPolicy {name} must be an iterable of vessels"
                ) from exc
            if any(not isinstance(value, expected_type) for value in normalized):
                raise ValueError(
                    f"PrimaryDirectionsPolicy {name} requires {expected_type.__name__} values"
                )
            object.__setattr__(self, name, normalized)

        if (
            self.placidian_rapt_parallel_motion is not None
            and not isinstance(self.placidian_rapt_parallel_motion, PrimaryDirectionMotion)
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy placidian_rapt_parallel_motion must be a primary-direction motion"
            )
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
        method_classification = classify_primary_direction_method(
            primary_direction_method_truth(self.method)
        )
        if (
            self.space is PrimaryDirectionSpace.IN_ZODIACO
            and not method_classification.zodiacal
        ):
            raise ValueError(
                f"PrimaryDirectionsPolicy method {self.method.value!r} does not admit in_zodiaco"
            )
        if self.include_converse and self.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: include_converse requires converse doctrine"
            )
        explicit_converse_rapt = (
            self.placidian_rapt_parallel_motion is PrimaryDirectionMotion.CONVERSE
        )
        if (not self.include_converse) and (
            self.converse_doctrine is not PrimaryDirectionConverseDoctrine.DIRECT_ONLY
        ) and not explicit_converse_rapt:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: direct-only policy must disable converse"
            )
        if explicit_converse_rapt and (
            self.converse_doctrine
            is not PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: converse rapt-parallel motion requires traditional-converse doctrine"
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
        fixed_star_names = [target.name for target in self.fixed_star_targets]
        if len(set(fixed_star_names)) != len(fixed_star_names):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: fixed_star_targets must be unique by name"
            )
        antiscia_names = [target.name for target in self.antiscia_targets]
        if len(set(antiscia_names)) != len(antiscia_names):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: antiscia_targets must be unique by name"
            )
        derived_target_names = (
            antiscia_names + parallel_names + rapt_names + fixed_star_names
        )
        if len(set(derived_target_names)) != len(derived_target_names):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: derived target names must be unique across target families"
            )
        if (
            self.fixed_star_targets
            and not self.target_policy.admitted_significator_classes
            <= frozenset(
                {
                    PrimaryDirectionTargetClass.ANGLE,
                    PrimaryDirectionTargetClass.PLANET,
                }
            )
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: current fixed_star_targets admission is limited to angle and planet significators"
            )
        if (
            self.fixed_star_targets
            and PrimaryDirectionRelationalKind.CONJUNCTION
            not in self.relation_policy.admitted_kinds
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: fixed_star_targets require conjunction admission"
            )
        if self.ptolemaic_parallel_targets and self.method is not PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: ptolemaic_parallel_targets currently require the Ptolemy method"
            )
        if self.antiscia_targets and self.method is not PrimaryDirectionMethod.PTOLEMY_SEMI_ARC:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: antiscia_targets currently require the Ptolemy method"
            )
        if self.antiscia_targets and self.space is not PrimaryDirectionSpace.IN_ZODIACO:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: antiscia_targets currently require in_zodiaco"
            )
        if self.antiscia_targets and (
            self.latitude_policy.doctrine is not PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            or self.latitude_source_policy.source is not PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            or self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: antiscia_targets currently require the zodiacal-suppressed longitude-perfection branch"
            )
        required_antiscia_kinds = {
            (
                PrimaryDirectionRelationalKind.ANTISCION
                if target.kind is PrimaryDirectionAntisciaKind.ANTISCION
                else PrimaryDirectionRelationalKind.CONTRA_ANTISCION
            )
            for target in self.antiscia_targets
        }
        if not required_antiscia_kinds <= self.relation_policy.admitted_kinds:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: antiscia_targets require matching admitted relation kinds"
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
        if self.placidian_rapt_parallel_targets and self.placidian_rapt_parallel_motion is None:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: placidian_rapt_parallel_targets require an explicit admitted motion"
            )
        if (
            self.placidian_rapt_parallel_motion is not None
            and self.placidian_rapt_parallel_motion not in (
                PrimaryDirectionMotion.DIRECT,
                PrimaryDirectionMotion.CONVERSE,
            )
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: placidian_rapt_parallel_motion must be a primary-direction motion"
            )

    @property
    def admitted_motions(self) -> tuple[PrimaryDirectionMotion, ...]:
        if self.include_converse:
            return (PrimaryDirectionMotion.DIRECT, PrimaryDirectionMotion.CONVERSE)
        return (PrimaryDirectionMotion.DIRECT,)

    def admits_motion(
        self,
        motion: PrimaryDirectionMotion,
        *,
        relational_kind: PrimaryDirectionRelationalKind,
    ) -> bool:
        """Return motion admission under relation-specific rapt doctrine."""
        if not isinstance(motion, PrimaryDirectionMotion):
            raise ValueError("PrimaryDirectionsPolicy motion must be PrimaryDirectionMotion")
        if not isinstance(relational_kind, PrimaryDirectionRelationalKind):
            raise ValueError(
                "PrimaryDirectionsPolicy relational_kind must be PrimaryDirectionRelationalKind"
            )
        if (
            relational_kind is PrimaryDirectionRelationalKind.RAPT_PARALLEL
            and self.placidian_rapt_parallel_motion is not None
        ):
            return motion is self.placidian_rapt_parallel_motion
        return motion in self.admitted_motions


def _preset_converse_doctrine(include_converse: bool) -> PrimaryDirectionConverseDoctrine:
    if include_converse:
        return PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    return PrimaryDirectionConverseDoctrine.DIRECT_ONLY


def _aspect_target_policy(*, fixed_star_targets: bool = False) -> PrimaryDirectionTargetPolicy:
    significator_classes = {
        PrimaryDirectionTargetClass.PLANET,
        PrimaryDirectionTargetClass.NODE,
        PrimaryDirectionTargetClass.ANGLE,
        PrimaryDirectionTargetClass.HOUSE_CUSP,
    }
    if fixed_star_targets:
        # The admitted fixed-star branch currently limits significators to
        # planets and angles; composing it with aspects must preserve both
        # doctrines instead of letting one keyword silently replace the other.
        significator_classes &= {
            PrimaryDirectionTargetClass.PLANET,
            PrimaryDirectionTargetClass.ANGLE,
        }
    return PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset(significator_classes),
        admitted_promissor_classes=frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            }
        ),
    )


def _fixed_star_target_policy() -> PrimaryDirectionTargetPolicy:
    return PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset(
            {
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.PLANET,
            }
        ),
        admitted_promissor_classes=PrimaryDirectionTargetPolicy().admitted_promissor_classes,
    )


def _rapt_parallel_relation_policy(
    *,
    fixed_star_targets: bool,
) -> PrimaryDirectionRelationPolicy:
    admitted = set(placidian_rapt_parallel_relation_policy().admitted_kinds)
    if fixed_star_targets:
        admitted.add(PrimaryDirectionRelationalKind.CONJUNCTION)
    return PrimaryDirectionRelationPolicy(frozenset(admitted))


def primary_directions_policy_preset(
    preset: PrimaryDirectionsPreset,
    *,
    include_converse: bool = True,
    key_policy: PrimaryDirectionKeyPolicy | None = None,
    morinus_aspect_contexts: tuple[MorinusAspectContext, ...] = (),
    antiscia_targets: tuple[PrimaryDirectionAntisciaTarget, ...] = (),
    ptolemaic_parallel_targets: tuple[PtolemaicParallelTarget, ...] = (),
    placidian_rapt_parallel_targets: tuple[PlacidianRaptParallelTarget, ...] = (),
    fixed_star_targets: tuple[PrimaryDirectionFixedStarTarget, ...] = (),
) -> PrimaryDirectionsPolicy:
    base_kwargs = {
        "include_converse": include_converse,
        "converse_doctrine": _preset_converse_doctrine(include_converse),
        "key_policy": key_policy if key_policy is not None else PrimaryDirectionKeyPolicy(),
        "fixed_star_targets": fixed_star_targets,
        "antiscia_targets": antiscia_targets,
    }
    if fixed_star_targets:
        base_kwargs["target_policy"] = _fixed_star_target_policy()
    aspect_kwargs = dict(base_kwargs)
    aspect_kwargs["target_policy"] = _aspect_target_policy(
        fixed_star_targets=bool(fixed_star_targets)
    )
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
            relation_policy=_rapt_parallel_relation_policy(
                fixed_star_targets=bool(fixed_star_targets)
            ),
            placidian_rapt_parallel_targets=placidian_rapt_parallel_targets,
            placidian_rapt_parallel_motion=PrimaryDirectionMotion.DIRECT,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE:
        if include_converse:
            raise ValueError(
                "PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE is converse-only and does not use the ambient converse toggle"
            )
        converse_rapt_kwargs = dict(base_kwargs)
        converse_rapt_kwargs["converse_doctrine"] = (
            PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
        )
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            relation_policy=_rapt_parallel_relation_policy(
                fixed_star_targets=bool(fixed_star_targets)
            ),
            placidian_rapt_parallel_targets=placidian_rapt_parallel_targets,
            placidian_rapt_parallel_motion=PrimaryDirectionMotion.CONVERSE,
            **converse_rapt_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_MUNDANE:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            **base_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            include_converse=base_kwargs["include_converse"],
            converse_doctrine=base_kwargs["converse_doctrine"],
            key_policy=base_kwargs["key_policy"],
            relation_policy=antiscia_relation_policy(),
            target_policy=base_kwargs.get("target_policy", PrimaryDirectionTargetPolicy()),
            fixed_star_targets=base_kwargs["fixed_star_targets"],
            antiscia_targets=antiscia_targets,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            **aspect_kwargs,
        )
    if preset is PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.ASSIGNED_ZERO),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION),
            relation_policy=ptolemaic_parallel_relation_policy(),
            ptolemaic_parallel_targets=ptolemaic_parallel_targets,
            **aspect_kwargs,
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
            **aspect_kwargs,
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
            morinus_aspect_contexts=morinus_aspect_contexts,
            **aspect_kwargs,
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
            **aspect_kwargs,
        )
    if preset is PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL_SIGNIFICATOR_CONDITIONED:
        return PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.REGIOMONTANUS,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            latitude_policy=PrimaryDirectionLatitudePolicy(PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE),
            perfection_policy=PrimaryDirectionPerfectionPolicy(PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION),
            relation_policy=zodiacal_aspect_relation_policy(),
            **aspect_kwargs,
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
            **aspect_kwargs,
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
            **aspect_kwargs,
        )
    raise ValueError(f"Unsupported primary-directions preset: {preset}")


@dataclass(frozen=True, slots=True)
class SpeculumEntry:
    """
    RITE: The Equatorial Mirror — the Engine that projects a zodiacal point
          into the active equatorial and mundane frame of a specific locality.

    THEOREM: Governs the derivation of Right Ascension, Declination, Hour Angle,
             and Mundane Semi-Arcs for any ecliptic point.

    RITE OF PURPOSE:
        SpeculumEntry is the primary coordinate vessel for all primary direction
        subsystems. It encapsulates the transformation from static zodiacal
        longitude/latitude to dynamic mundane coordinates (HA, f) relative
        to a specific Meridian and Horizon.

    LAW OF OPERATION:
        Responsibilities:
            - Store normalized equatorial and ecliptic coordinates.
            - Validate spherical invariants (e.g., DSA + NSA = 180°).
            - Expose mundane position fraction (f) for Placidian arithmetic.
        Non-responsibilities:
            - Does not compute time-keys or arcs.
            - Does not handle precession or nutation (expects input in active frame).
        Invariants:
            - lon, ra are in [0, 360).
            - dsa + nsa == 180.0.
            - |f| <= 2.0 (IC to IC via Meridian).

    Canon: Placidus de Titis, Tabulae Primi Mobilis (1657)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.primary_directions.SpeculumEntry",
      "risk": "medium",
      "api": {"frozen": ["name", "lon", "lat", "ra", "dec"], "internal": ["build"]},
      "state": {"mutable": false},
      "effects": {"io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "exception"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
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
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("SpeculumEntry requires a non-empty name")
        for name in ("lon", "lat", "ra", "dec", "ha", "dsa", "nsa", "f"):
            try:
                value = _finite_real(getattr(self, name), f"SpeculumEntry {name}")
            except ValueError as exc:
                raise ValueError("SpeculumEntry requires finite real coordinates") from exc
            object.__setattr__(self, name, value)
        if not isinstance(self.upper, bool):
            raise ValueError("SpeculumEntry upper must be bool")
        if not (0.0 <= self.lon < 360.0):
            raise ValueError(f"SpeculumEntry longitude must be normalized: {self.lon}")
        if not (-90.0 <= self.lat <= 90.0):
            raise ValueError(f"SpeculumEntry ecliptic latitude out of range: {self.lat}")
        if not (0.0 <= self.ra < 360.0):
            raise ValueError(f"SpeculumEntry right ascension must be normalized: {self.ra}")
        if not (-90.0 <= self.dec <= 90.0):
            raise ValueError(f"SpeculumEntry declination out of range: {self.dec}")
        if not (-180.0 <= self.ha <= 180.0):
            raise ValueError(f"SpeculumEntry hour angle out of range: {self.ha}")
        if not (0.0 < self.dsa < 180.0):
            raise ValueError(f"SpeculumEntry DSA out of range: {self.dsa}")
        if not (0.0 < self.nsa < 180.0):
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
        inputs = {
            "longitude": lon,
            "latitude": lat,
            "ARMC": armc,
            "obliquity": obliquity,
            "geographic latitude": geo_lat,
        }
        if not all(
            isinstance(value, Real)
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in inputs.values()
        ):
            raise ValueError("SpeculumEntry.build requires finite real coordinates")
        if not -90.0 <= lat <= 90.0:
            raise ValueError("SpeculumEntry.build requires ecliptic latitude in [-90, 90]")
        if not -90.0 < geo_lat < 90.0:
            raise ValueError("SpeculumEntry.build requires geographic latitude in (-90, 90)")

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

        arg = -math.tan(phi) * math.tan(dec_r)
        if arg < -1.0 - 1e-12 or arg > 1.0 + 1e-12:
            raise ValueError(
                "SpeculumEntry.build has no real rise/set semi-arcs at this latitude"
            )
        arg = max(-1.0, min(1.0, arg))
        dsa = math.degrees(math.acos(arg))
        nsa = 180.0 - dsa
        if dsa <= 1e-9 or nsa <= 1e-9:
            raise ValueError(
                "SpeculumEntry.build does not admit a limiting tangent with a zero semi-arc"
            )

        upper = abs(ha) <= dsa + 1e-9
        if upper:
            f = ha / dsa
        elif ha > 0:
            f = 1.0 + (ha - dsa) / nsa
        else:
            f = -1.0 - (-ha - dsa) / nsa

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


@dataclass(frozen=True, slots=True)
class PrimaryArc:
    """
    RITE: The Primary Path — the Engine that records a single motion cycle
          between a Significator and a Promissor.

    THEOREM: Governs the storage of the angular arc and the conversion of
             that arc into temporal years via a specified time-key.

    RITE OF PURPOSE:
        PrimaryArc is the canonical result vessel of the primary direction engine.
        It preserves the computational method, motion direction (Direct/Converse),
        and the final angular arc, providing a unified surface for time-key
        projection.

    LAW OF OPERATION:
        Responsibilities:
            - Store arc and calculation parameters.
            - Provide convert_arc_to_time via the .years() method.
            - Validate structural consistency (e.g., significator != promissor).
        Non-responsibilities:
            - Does not compute the arc itself (delegates to geometry subsystem).
            - Does not handle relation detection (delegates to relation subsystem).
        Invariants:
            - arc > 0.0.
            - significator != promissor.

    Canon: Various (Ptolemy, Placidus, Magini, Argoli, etc.)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.primary_directions.PrimaryArc",
      "risk": "low",
      "api": {"frozen": ["significator", "promissor", "arc"], "internal": ["years"]},
      "state": {"mutable": false},
      "effects": {"io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "exception"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    significator: str
    promissor: str
    arc: float
    direction: str
    method: PrimaryDirectionMethod = field(default=PrimaryDirectionMethod.PLACIDUS_MUNDANE)
    space: PrimaryDirectionSpace = field(default=PrimaryDirectionSpace.IN_MUNDO)
    motion: PrimaryDirectionMotion = field(default=PrimaryDirectionMotion.DIRECT)
    solar_rate: float | None = None
    relational_kind: PrimaryDirectionRelationalKind = field(
        default=PrimaryDirectionRelationalKind.CONJUNCTION
    )
    _solar_rate_explicit: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.significator, str)
            or not self.significator.strip()
            or not isinstance(self.promissor, str)
            or not self.promissor.strip()
        ):
            raise ValueError("PrimaryArc requires non-empty significator and promissor")
        if self.significator == self.promissor:
            raise ValueError("PrimaryArc invariant failed: self-directions are not admitted")
        object.__setattr__(self, "arc", _finite_real(self.arc, "PrimaryArc arc"))
        solar_rate_explicit = self.solar_rate is not None
        resolved_solar_rate = (
            _finite_real(self.solar_rate, "PrimaryArc solar_rate")
            if solar_rate_explicit
            else _DEFAULT_SOLAR_RATE
        )
        object.__setattr__(self, "solar_rate", resolved_solar_rate)
        object.__setattr__(self, "_solar_rate_explicit", solar_rate_explicit)
        if self.arc <= 0.0:
            raise ValueError("PrimaryArc invariant failed: arc must be positive")
        if self.solar_rate <= 0.0:
            raise ValueError("PrimaryArc invariant failed: solar_rate must be positive")
        if not isinstance(self.motion, PrimaryDirectionMotion):
            raise ValueError(f"Unsupported primary direction motion: {self.motion}")
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
        method_classification = classify_primary_direction_method(
            primary_direction_method_truth(self.method)
        )
        if (
            self.space is PrimaryDirectionSpace.IN_ZODIACO
            and not method_classification.zodiacal
        ):
            raise ValueError(
                f"PrimaryArc method {self.method.value!r} does not admit in_zodiaco"
            )
        if not isinstance(self.relational_kind, PrimaryDirectionRelationalKind):
            raise ValueError(
                f"Unsupported primary direction relational kind: {self.relational_kind}"
            )

    def years(self, key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD) -> float:
        return convert_arc_to_time(
            self.arc,
            key,
            solar_rate=self.solar_rate if self._solar_rate_explicit else None,
        )

    @property
    def solar_rate_explicit(self) -> bool:
        """Whether the stored rate came from an explicit/generated natal rate."""
        return self._solar_rate_explicit

    @property
    def is_direct(self) -> bool:
        return self.motion is PrimaryDirectionMotion.DIRECT

    @property
    def is_converse(self) -> bool:
        return self.motion is PrimaryDirectionMotion.CONVERSE

    def __repr__(self) -> str:
        return (
            f"PrimaryArc({self.significator} <- {self.promissor}  "
            f"arc={self.arc:.4f}  {self.direction}  "
            f"{self.years():.2f} yr [Naibod])"
        )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelation:
    """
    RITE: The Perfection Binding — the Engine that determines the exact
          temporal and doctrinal manifestation of a primary arc.

    THEOREM: Governs the mapping of raw arcs to specific mundane or zodiacal
             perfections based on the active converse doctrine and key policy.

    RITE OF PURPOSE:
        PrimaryDirectionRelation elevates a bare PrimaryArc into a qualified
        astrological event. It couples the arc with the specific perfection
        kind and governance policies that define its temporal "hit" date.

    LAW OF OPERATION:
        Responsibilities:
            - Store the arc and its perfection parameters.
            - Provide year derivation via the years property.
            - Validate that converse arcs are only admitted when the doctrine allows.
        Non-responsibilities:
            - Does not compute the arc.
            - Does not aggregate multiple relations (delegates to profiles).
        Invariants:
            - converse arcs require MIXED or CONVERSE_ONLY doctrine.

    Canon: Various (Primary Direction Tradition)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.primary_directions.PrimaryDirectionRelation",
      "risk": "low",
      "api": {"frozen": ["arc", "relation_kind"], "internal": ["years"]},
      "state": {"mutable": false},
      "effects": {"io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "exception"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    arc: PrimaryArc
    relation_kind: PrimaryDirectionPerfectionKind
    converse_doctrine: PrimaryDirectionConverseDoctrine
    key_policy: PrimaryDirectionKeyPolicy
    relational_kind: PrimaryDirectionRelationalKind | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.arc, PrimaryArc):
            raise ValueError("PrimaryDirectionRelation arc must be PrimaryArc")
        if not isinstance(self.relation_kind, PrimaryDirectionPerfectionKind):
            raise ValueError(
                f"Unsupported primary direction relation kind: {self.relation_kind}"
            )
        if self.relation_kind not in (
            PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION,
        ):
            raise ValueError(f"Unsupported primary direction relation kind: {self.relation_kind}")
        if not isinstance(self.converse_doctrine, PrimaryDirectionConverseDoctrine):
            raise ValueError(
                "PrimaryDirectionRelation converse_doctrine must be PrimaryDirectionConverseDoctrine"
            )
        if not isinstance(self.key_policy, PrimaryDirectionKeyPolicy):
            raise ValueError("PrimaryDirectionRelation key_policy must be PrimaryDirectionKeyPolicy")
        if self.relational_kind is None:
            object.__setattr__(self, "relational_kind", self.arc.relational_kind)
        if not isinstance(self.relational_kind, PrimaryDirectionRelationalKind):
            raise ValueError(
                "PrimaryDirectionRelation relational_kind must be PrimaryDirectionRelationalKind"
            )
        if self.relational_kind is not self.arc.relational_kind:
            raise ValueError(
                "PrimaryDirectionRelation invariant failed: relational_kind must match arc"
            )
        if (
            self.arc.space is PrimaryDirectionSpace.IN_MUNDO
            and self.relation_kind
            is not PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
        ):
            raise ValueError(
                "PrimaryDirectionRelation invariant failed: in_mundo arcs require mundane position perfection"
            )
        if (
            self.arc.space is PrimaryDirectionSpace.IN_ZODIACO
            and self.relation_kind
            not in (
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION,
                PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION,
            )
        ):
            raise ValueError(
                "PrimaryDirectionRelation invariant failed: in_zodiaco arcs require zodiacal perfection"
            )
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

    @property
    def perfection_kind(self) -> PrimaryDirectionPerfectionKind:
        """Explicit name for the compatibility ``relation_kind`` field."""
        return self.relation_kind


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationProfile:
    """Vessel: Aggregated relation profile for a single primary arc."""
    arc: PrimaryArc
    detected_relation: PrimaryDirectionRelation
    admitted_relations: tuple[PrimaryDirectionRelation, ...]
    scored_relations: tuple[PrimaryDirectionRelation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.arc, PrimaryArc):
            raise ValueError("PrimaryDirectionRelationProfile arc must be PrimaryArc")
        if not isinstance(self.detected_relation, PrimaryDirectionRelation):
            raise ValueError(
                "PrimaryDirectionRelationProfile detected_relation must be PrimaryDirectionRelation"
            )
        for name in ("admitted_relations", "scored_relations"):
            values = tuple(getattr(self, name))
            if any(not isinstance(value, PrimaryDirectionRelation) for value in values):
                raise ValueError(
                    f"PrimaryDirectionRelationProfile {name} requires relation vessels"
                )
            object.__setattr__(self, name, values)
        if self.detected_relation.arc != self.arc:
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: detected relation must belong to arc"
            )
        if any(relation.arc != self.arc for relation in self.admitted_relations):
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: admitted relations must belong to arc"
            )
        if any(relation.arc != self.arc for relation in self.scored_relations):
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: scored relations must belong to arc"
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

    @property
    def admitted_relational_kinds(self) -> tuple[PrimaryDirectionRelationalKind, ...]:
        return tuple(relation.relational_kind for relation in self.admitted_relations)

    @property
    def scored_relational_kinds(self) -> tuple[PrimaryDirectionRelationalKind, ...]:
        return tuple(relation.relational_kind for relation in self.scored_relations)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsSignificatorProfile:
    """Vessel: Complete direction and relation summary for a single significator."""
    significator: str
    arcs: tuple[PrimaryArc, ...]
    relation_profiles: tuple[PrimaryDirectionRelationProfile, ...]
    state: PrimaryDirectionsConditionState
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float

    def __post_init__(self) -> None:
        if not isinstance(self.significator, str) or not self.significator.strip():
            raise ValueError("PrimaryDirectionsSignificatorProfile requires a significator")
        object.__setattr__(self, "arcs", tuple(self.arcs))
        object.__setattr__(self, "relation_profiles", tuple(self.relation_profiles))
        if not self.arcs:
            raise ValueError("PrimaryDirectionsSignificatorProfile requires at least one arc")
        if any(not isinstance(arc, PrimaryArc) for arc in self.arcs):
            raise ValueError("PrimaryDirectionsSignificatorProfile arcs must be PrimaryArc vessels")
        if any(
            not isinstance(profile, PrimaryDirectionRelationProfile)
            for profile in self.relation_profiles
        ):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile relation_profiles must be relation-profile vessels"
            )
        if not isinstance(self.state, PrimaryDirectionsConditionState):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile state must be PrimaryDirectionsConditionState"
            )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in (self.direct_count, self.converse_count)
        ):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile direction counts must be non-negative integers"
            )
        object.__setattr__(
            self,
            "nearest_arc",
            _finite_real(self.nearest_arc, "PrimaryDirectionsSignificatorProfile nearest_arc"),
        )
        object.__setattr__(
            self,
            "farthest_arc",
            _finite_real(self.farthest_arc, "PrimaryDirectionsSignificatorProfile farthest_arc"),
        )
        if len(self.arcs) != len(self.relation_profiles):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: arcs/profiles length mismatch"
            )
        if any(arc.significator != self.significator for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: all arcs must share significator"
            )
        if any(
            profile.arc != arc
            for arc, profile in zip(self.arcs, self.relation_profiles, strict=True)
        ):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: relation profiles must preserve arc order and identity"
            )
        actual_direct = sum(arc.is_direct for arc in self.arcs)
        actual_converse = len(self.arcs) - actual_direct
        if self.direct_count != actual_direct or self.converse_count != actual_converse:
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: direction counts do not match arc motions"
            )
        if self.direct_count + self.converse_count != len(self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: direction counts do not match arc count"
            )
        if self.state is not _state_for_arcs(self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: state does not match arc motions"
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
    """Vessel: Engine-wide summary of all direction results for a given search."""
    profiles: tuple[PrimaryDirectionsSignificatorProfile, ...]
    total_arcs: int
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float
    strongest_significator: str
    weakest_significator: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "profiles", tuple(self.profiles))
        if not self.profiles:
            raise ValueError("PrimaryDirectionsAggregateProfile requires at least one significator profile")
        if any(
            not isinstance(profile, PrimaryDirectionsSignificatorProfile)
            for profile in self.profiles
        ):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile profiles must be significator-profile vessels"
            )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in (self.total_arcs, self.direct_count, self.converse_count)
        ):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile counts must be non-negative integers"
            )
        object.__setattr__(
            self,
            "nearest_arc",
            _finite_real(self.nearest_arc, "PrimaryDirectionsAggregateProfile nearest_arc"),
        )
        object.__setattr__(
            self,
            "farthest_arc",
            _finite_real(self.farthest_arc, "PrimaryDirectionsAggregateProfile farthest_arc"),
        )
        if not isinstance(self.strongest_significator, str) or not self.strongest_significator:
            raise ValueError("PrimaryDirectionsAggregateProfile strongest_significator must be set")
        if not isinstance(self.weakest_significator, str) or not self.weakest_significator:
            raise ValueError("PrimaryDirectionsAggregateProfile weakest_significator must be set")
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
    """Vessel: Graph node representation of a significator or promissor."""
    name: str
    incoming_count: int
    outgoing_count: int
    total_count: int
    direct_count: int | None = None
    converse_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PrimaryDirectionsNetworkNode requires a non-empty name")
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in (self.incoming_count, self.outgoing_count, self.total_count)
        ):
            raise ValueError("PrimaryDirectionsNetworkNode counts must be non-negative integers")
        if self.total_count != self.incoming_count + self.outgoing_count:
            raise ValueError(
                "PrimaryDirectionsNetworkNode invariant failed: total_count mismatch"
            )
        if (self.direct_count is None) != (self.converse_count is None):
            raise ValueError(
                "PrimaryDirectionsNetworkNode direct/converse counts must be both known or both unknown"
            )
        if self.direct_count is not None and self.converse_count is not None:
            if any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in (self.direct_count, self.converse_count)
            ):
                raise ValueError(
                    "PrimaryDirectionsNetworkNode motion counts must be non-negative integers"
                )
            if self.direct_count + self.converse_count != self.total_count:
                raise ValueError(
                    "PrimaryDirectionsNetworkNode invariant failed: motion counts must equal total_count"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkEdge:
    """Vessel: Graph edge representation of a direction between two nodes."""
    promissor: str
    significator: str
    count: int
    nearest_arc: float
    direct_count: int | None = None
    converse_count: int | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.promissor, str)
            or not self.promissor.strip()
            or not isinstance(self.significator, str)
            or not self.significator.strip()
        ):
            raise ValueError("PrimaryDirectionsNetworkEdge requires endpoint names")
        if self.promissor == self.significator:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: self-edge not admitted")
        if not isinstance(self.count, int) or isinstance(self.count, bool) or self.count <= 0:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: count must be positive")
        object.__setattr__(
            self,
            "nearest_arc",
            _finite_real(self.nearest_arc, "PrimaryDirectionsNetworkEdge nearest_arc"),
        )
        if self.nearest_arc <= 0.0:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: nearest_arc must be positive")
        if (self.direct_count is None) != (self.converse_count is None):
            raise ValueError(
                "PrimaryDirectionsNetworkEdge direct/converse counts must be both known or both unknown"
            )
        if self.direct_count is not None and self.converse_count is not None:
            if any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in (self.direct_count, self.converse_count)
            ):
                raise ValueError(
                    "PrimaryDirectionsNetworkEdge motion counts must be non-negative integers"
                )
            if self.direct_count + self.converse_count != self.count:
                raise ValueError(
                    "PrimaryDirectionsNetworkEdge invariant failed: motion counts must equal count"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkProfile:
    """Vessel: Graph-theory model of the entire primary direction network."""
    nodes: tuple[PrimaryDirectionsNetworkNode, ...]
    edges: tuple[PrimaryDirectionsNetworkEdge, ...]
    most_connected: str
    isolated: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "isolated", tuple(self.isolated))
        if not self.nodes:
            raise ValueError("PrimaryDirectionsNetworkProfile requires at least one node")
        if any(not isinstance(node, PrimaryDirectionsNetworkNode) for node in self.nodes):
            raise ValueError("PrimaryDirectionsNetworkProfile nodes must be node vessels")
        if any(not isinstance(edge, PrimaryDirectionsNetworkEdge) for edge in self.edges):
            raise ValueError("PrimaryDirectionsNetworkProfile edges must be edge vessels")
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
        if tuple(sorted(self.isolated)) != self.isolated or len(set(self.isolated)) != len(self.isolated):
            raise ValueError(
                "PrimaryDirectionsNetworkProfile isolated identities must be unique and sorted"
            )
        computed_isolated = tuple(sorted(node.name for node in self.nodes if node.total_count == 0))
        if self.isolated != computed_isolated:
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: isolated identities do not match nodes"
            )
        incoming = {name: 0 for name in node_set}
        outgoing = {name: 0 for name in node_set}
        direct = {name: 0 for name in node_set}
        converse = {name: 0 for name in node_set}
        seen_edges: set[tuple[str, str]] = set()
        for edge in self.edges:
            identity = (edge.promissor, edge.significator)
            if identity in seen_edges:
                raise ValueError("PrimaryDirectionsNetworkProfile invariant failed: duplicate edge")
            seen_edges.add(identity)
            outgoing[edge.promissor] += edge.count
            incoming[edge.significator] += edge.count
            if edge.direct_count is not None and edge.converse_count is not None:
                direct[edge.promissor] += edge.direct_count
                direct[edge.significator] += edge.direct_count
                converse[edge.promissor] += edge.converse_count
                converse[edge.significator] += edge.converse_count
        for node in self.nodes:
            if (
                node.incoming_count != incoming[node.name]
                or node.outgoing_count != outgoing[node.name]
            ):
                raise ValueError(
                    "PrimaryDirectionsNetworkProfile invariant failed: node counts do not match edges"
                )
            if node.direct_count is not None and node.converse_count is not None:
                if (
                    node.direct_count != direct[node.name]
                    or node.converse_count != converse[node.name]
                ):
                    raise ValueError(
                        "PrimaryDirectionsNetworkProfile invariant failed: node motion counts do not match edges"
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
        if name.endswith(" Antiscion"):
            required.add(PrimaryDirectionRelationalKind.ANTISCION)
            continue
        if name.endswith(" Contra-Antiscion"):
            required.add(PrimaryDirectionRelationalKind.CONTRA_ANTISCION)
            continue
        try:
            truth = primary_direction_target_truth(name)
        except ValueError:
            continue
        if truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT:
            assert truth.aspect_angle is not None
            if abs(truth.aspect_angle) <= 1e-12:
                required.add(PrimaryDirectionRelationalKind.CONJUNCTION)
            elif abs(abs(truth.aspect_angle) - 180.0) <= 1e-12:
                required.add(PrimaryDirectionRelationalKind.OPPOSITION)
            else:
                required.add(PrimaryDirectionRelationalKind.ZODIACAL_ASPECT)
        else:
            required.add(PrimaryDirectionRelationalKind.CONJUNCTION)
    return required


def _identity_tuple(
    values: Iterable[str] | None,
    name: str,
) -> tuple[str, ...] | None:
    if values is None:
        return None
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of target names, not one string")
    try:
        normalized = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{name} must be an iterable of target names") from exc
    if any(not isinstance(value, str) or not value.strip() for value in normalized):
        raise ValueError(f"{name} must contain non-empty string target names")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} may not contain duplicate target names")
    return normalized


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


def _antiscia_promissor_entries(
    targets: Iterable[PrimaryDirectionAntisciaTarget],
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
        reflected_longitude = project_primary_direction_antiscia_longitude(
            source.lon,
            target.kind,
        )
        derived[target.name] = _project_zodiacal_point(
            target.name,
            reflected_longitude,
            0.0,
            armc=armc,
            obliquity=obliquity,
            geo_lat=geo_lat,
        )
    return derived


def _fixed_star_promissor_entries(
    targets: Iterable[PrimaryDirectionFixedStarTarget],
    *,
    jd_tt: float,
    armc: float,
    obliquity: float,
    geo_lat: float,
    latitude_doctrine: PrimaryDirectionLatitudeDoctrine,
) -> dict[str, SpeculumEntry]:
    derived: dict[str, SpeculumEntry] = {}
    for target in targets:
        _catalog_name, longitude, latitude = resolve_primary_direction_fixed_star_point(
            target,
            jd_tt=jd_tt,
        )
        derived[target.name] = SpeculumEntry.build(
            target.name,
            longitude,
            (
                0.0
                if latitude_doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                else latitude
            ),
            armc,
            obliquity,
            geo_lat,
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
    geo_lat = _finite_real(geo_lat, "speculum geographic latitude")
    if not -90.0 < geo_lat < 90.0:
        raise ValueError("speculum requires geographic latitude in (-90, 90)")
    obl = _finite_real(
        obliquity if obliquity is not None else chart.obliquity,
        "speculum obliquity",
    )
    if not 0.0 <= obl < 90.0:
        raise ValueError("speculum requires obliquity in [0, 90)")
    armc = houses.armc

    entries: list[SpeculumEntry] = []
    normalized_bodies = _identity_tuple(bodies, "speculum bodies")
    planet_names = normalized_bodies if normalized_bodies is not None else tuple(chart.planets)
    if normalized_bodies is not None:
        missing = tuple(name for name in normalized_bodies if name not in chart.planets)
        if missing:
            raise ValueError(f"speculum requested unavailable chart bodies: {missing!r}")
    for name in planet_names:
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
    if not isinstance(include_converse, bool):
        raise ValueError("find_primary_arcs include_converse must be bool")
    if policy is not None and not isinstance(policy, PrimaryDirectionsPolicy):
        raise ValueError("find_primary_arcs policy must be PrimaryDirectionsPolicy")
    max_arc = _finite_real(max_arc, "find_primary_arcs max_arc")
    geo_lat = _finite_real(geo_lat, "find_primary_arcs geographic latitude")
    if not 0.0 < max_arc <= 360.0:
        raise ValueError("find_primary_arcs requires max_arc in (0, 360]")
    if not -90.0 < geo_lat < 90.0:
        raise ValueError("find_primary_arcs requires geographic latitude in (-90, 90)")
    normalized_significators = _identity_tuple(significators, "find_primary_arcs significators")
    normalized_promissors = _identity_tuple(promissors, "find_primary_arcs promissors")

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
    obl = _finite_real(
        obliquity if obliquity is not None else chart.obliquity,
        "find_primary_arcs obliquity",
    )
    if not 0.0 <= obl < 90.0:
        raise ValueError("find_primary_arcs requires obliquity in [0, 90)")

    if solar_speed is not None:
        s_rate = _finite_real(solar_speed, "find_primary_arcs solar_speed")
    else:
        sun = chart.planets.get(Body.SUN)
        if sun is None:
            raise ValueError(
                "find_primary_arcs requires explicit solar_speed or a chart with natal Sun speed"
            )
        s_rate = abs(_finite_real(sun.speed, "find_primary_arcs natal Sun speed"))
    if s_rate <= 0.0:
        raise ValueError(
            "find_primary_arcs requires explicit solar_speed or a chart with positive natal Sun speed"
        )

    spec = speculum(chart, houses, geo_lat, obliquity=obl)
    sp_map = {e.name: e for e in spec}
    # Oblique ascension of the eastern horizon is an equatorial coordinate:
    # OA(ASC) = local sidereal time + 90 degrees.  It is not the right
    # ascension of the ecliptic Ascendant, which differs at non-zero obliquity
    # and would miswire the Placidian-classic endpoint law.
    oa_asc = (houses.armc + 90.0) % 360.0

    all_names = list(sp_map.keys())
    sig_candidates = (
        set(normalized_significators)
        if normalized_significators is not None
        else set(all_names)
    )
    fixed_star_targets = tuple(
        target
        for target in resolved_policy.fixed_star_targets
        if normalized_promissors is None or target.name in normalized_promissors
    )
    fixed_star_names = {target.name for target in fixed_star_targets}
    antiscia_targets = (
        tuple(
            target
            for target in resolved_policy.antiscia_targets
            if normalized_promissors is None or target.name in normalized_promissors
        )
        if resolved_policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
        else ()
    )
    antiscia_names = {target.name for target in antiscia_targets}
    ptolemaic_parallel_targets = (
        tuple(
            target
            for target in resolved_policy.ptolemaic_parallel_targets
            if normalized_promissors is None or target.name in normalized_promissors
        )
        if resolved_policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
        else ()
    )
    ptolemaic_parallel_names = {target.name for target in ptolemaic_parallel_targets}
    placidian_rapt_parallel_targets = (
        tuple(
            target
            for target in resolved_policy.placidian_rapt_parallel_targets
            if normalized_promissors is None or target.name in normalized_promissors
        )
        if (
            resolved_policy.method is PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC
            and resolved_policy.space is PrimaryDirectionSpace.IN_MUNDO
        )
        else ()
    )
    placidian_rapt_parallel_names = {target.name for target in placidian_rapt_parallel_targets}
    prom_candidates = (
        set(normalized_promissors)
        if normalized_promissors is not None
        else (
            set(all_names)
            | fixed_star_names
            | antiscia_names
            | ptolemaic_parallel_names
            | placidian_rapt_parallel_names
        )
    )
    candidate_names = set(all_names) | sig_candidates | prom_candidates
    relational_kind_by_name: dict[str, PrimaryDirectionRelationalKind] = {
        target.name: (
            PrimaryDirectionRelationalKind.ANTISCION
            if target.kind is PrimaryDirectionAntisciaKind.ANTISCION
            else PrimaryDirectionRelationalKind.CONTRA_ANTISCION
        )
        for target in antiscia_targets
    }
    relational_kind_by_name.update(
        {
            target.name: (
                PrimaryDirectionRelationalKind.PARALLEL
                if target.relation is PtolemaicParallelRelation.PARALLEL
                else PrimaryDirectionRelationalKind.CONTRA_PARALLEL
            )
            for target in ptolemaic_parallel_targets
        }
    )
    relational_kind_by_name.update(
        {
            target.name: PrimaryDirectionRelationalKind.RAPT_PARALLEL
            for target in placidian_rapt_parallel_targets
        }
    )
    relational_kind_by_name.update(
        {
            target.name: PrimaryDirectionRelationalKind.CONJUNCTION
            for target in fixed_star_targets
        }
    )
    required_relation_kinds = (
        _required_relation_kinds_for_requested_promissors(normalized_promissors)
        if normalized_promissors is not None
        else set()
    )
    required_relation_kinds.update(
        relational_kind_by_name[name]
        for name in (normalized_promissors or ())
        if name in relational_kind_by_name
    )
    if not required_relation_kinds <= resolved_policy.relation_policy.admitted_kinds:
        raise ValueError(
            "find_primary_arcs invariant failed: requested promissors require admitted relation kinds"
        )
    target_truths = {}
    for name in candidate_names:
        try:
            truth = primary_direction_target_truth(name)
        except ValueError:
            if (
                name not in relational_kind_by_name
                and (
                    normalized_significators is not None
                    and name in normalized_significators
                    or normalized_promissors is not None
                    and name in normalized_promissors
                )
            ):
                raise
            continue
        target_truths[name] = truth
        if truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT:
            assert truth.aspect_angle is not None
            if abs(truth.aspect_angle) <= 1e-12:
                relational_kind_by_name[name] = PrimaryDirectionRelationalKind.CONJUNCTION
            elif abs(abs(truth.aspect_angle) - 180.0) <= 1e-12:
                relational_kind_by_name[name] = PrimaryDirectionRelationalKind.OPPOSITION
            else:
                relational_kind_by_name[name] = PrimaryDirectionRelationalKind.ZODIACAL_ASPECT
        else:
            relational_kind_by_name.setdefault(
                name,
                PrimaryDirectionRelationalKind.CONJUNCTION,
            )
    # Aspectual promissors may be derived from a house cusp (for example,
    # ``H10 Trine``).  Materialize that named source cusp even though the
    # derived aspect name, rather than the source, is the requested candidate.
    aspect_source_names = {
        truth.source_name
        for truth in target_truths.values()
        if (
            truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
            and truth.source_name is not None
        )
    }
    derived_cusps = _house_cusp_entries(
        candidate_names | aspect_source_names,
        houses,
        armc=houses.armc,
        obliquity=obl,
        geo_lat=geo_lat,
    )
    if derived_cusps:
        sp_map.update(derived_cusps)
        spec.extend(derived_cusps.values())
    _jd_tt = chart.jd_tt
    derived_fixed_stars = _fixed_star_promissor_entries(
        fixed_star_targets,
        jd_tt=_jd_tt,
        armc=houses.armc,
        obliquity=obl,
        geo_lat=geo_lat,
        latitude_doctrine=resolved_policy.latitude_policy.doctrine,
    )
    if derived_fixed_stars:
        sp_map.update(derived_fixed_stars)
        spec.extend(derived_fixed_stars.values())
    source_bound_targets = (
        tuple(antiscia_targets)
        + tuple(ptolemaic_parallel_targets)
        + tuple(placidian_rapt_parallel_targets)
    )
    for target in source_bound_targets:
        if target.source_name not in sp_map:
            raise ValueError(
                f"find_primary_arcs requested derived promissor {target.name!r} "
                f"but source {target.source_name!r} is unavailable"
            )
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
            if antiscia_targets:
                prom_map.update(
                    _antiscia_promissor_entries(
                        antiscia_targets,
                        sp_map,
                        armc=houses.armc,
                        obliquity=obl,
                        geo_lat=geo_lat,
                    )
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
    prom_set |= antiscia_names
    prom_set |= fixed_star_names
    prom_set |= ptolemaic_parallel_names
    prom_set |= placidian_rapt_parallel_names
    if resolved_policy.placidian_rapt_parallel_motion is not None:
        # Rapt presets are pair-specific.  Composing configured fixed stars
        # admits those named conjunction targets, not every ordinary bodily
        # conjunction merely because both share one relation-kind token.
        prom_set &= fixed_star_names | placidian_rapt_parallel_names
    placidian_rapt_parallel_map = {
        target.name: target for target in placidian_rapt_parallel_targets
    }
    if normalized_significators is not None:
        for name in normalized_significators:
            truth = target_truths.get(name)
            if name not in sp_map:
                raise ValueError(
                    f"find_primary_arcs requested significator {name!r} is unavailable"
                )
            if (
                truth is None
                or truth.target_class
                not in resolved_policy.target_policy.admitted_significator_classes
            ):
                raise ValueError(
                    f"find_primary_arcs requested significator {name!r} is not admitted by policy"
                )
    if normalized_promissors is not None:
        for name in normalized_promissors:
            if name not in prom_set:
                raise ValueError(
                    f"find_primary_arcs requested promissor {name!r} is not admitted by policy"
                )
            if (
                resolved_policy.latitude_policy.doctrine
                is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED
            ):
                truth = target_truths.get(name)
                available = name in sp_map or (
                    truth is not None
                    and truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
                    and truth.source_name in sp_map
                )
            else:
                available = name in prom_map or name in placidian_rapt_parallel_map
            if not available:
                raise ValueError(
                    f"find_primary_arcs requested promissor {name!r} is unavailable"
                )

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
            relational_kind = relational_kind_by_name.get(
                prom_name,
                PrimaryDirectionRelationalKind.CONJUNCTION,
            )
            if relational_kind not in resolved_policy.relation_policy.admitted_kinds:
                continue
            if prom_name in placidian_rapt_parallel_map:
                source_entry = sp_map.get(placidian_rapt_parallel_map[prom_name].source_name)
                if source_entry is None or source_entry.name == sig_e.name:
                    continue
                if resolved_policy.placidian_rapt_parallel_motion is PrimaryDirectionMotion.DIRECT:
                    rapt_arc = compute_placidian_rapt_parallel_arc(source_entry, sig_e) % 360.0
                    direction = DIRECT
                    motion = PrimaryDirectionMotion.DIRECT
                else:
                    rapt_arc = compute_placidian_converse_rapt_parallel_arc(source_entry, sig_e) % 360.0
                    direction = CONVERSE
                    motion = PrimaryDirectionMotion.CONVERSE
                if 0.0 < rapt_arc <= max_arc:
                    results.append(
                        PrimaryArc(
                            significator=sig_e.name,
                            promissor=prom_name,
                            arc=rapt_arc,
                            direction=direction,
                            method=resolved_policy.method,
                            space=resolved_policy.space,
                            motion=motion,
                            solar_rate=s_rate,
                            relational_kind=relational_kind,
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
                        relational_kind=relational_kind,
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
                        relational_kind=relational_kind,
                    )
                )

    results.sort(key=lambda arc: (arc.arc, arc.significator, arc.promissor, arc.direction))
    return results


def relate_primary_arc(
    arc: PrimaryArc,
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionRelation:
    if not isinstance(arc, PrimaryArc):
        raise ValueError("relate_primary_arc requires a PrimaryArc")
    if policy is not None and not isinstance(policy, PrimaryDirectionsPolicy):
        raise ValueError("relate_primary_arc policy must be PrimaryDirectionsPolicy")
    resolved_policy = policy if policy is not None else PrimaryDirectionsPolicy()
    if arc.method is not resolved_policy.method:
        raise ValueError(
            "relate_primary_arc invariant failed: arc method does not match policy method"
        )
    if arc.space is not resolved_policy.space:
        raise ValueError(
            "relate_primary_arc invariant failed: arc space does not match policy space"
        )
    if not resolved_policy.admits_motion(
        arc.motion,
        relational_kind=arc.relational_kind,
    ):
        raise ValueError(
            "relate_primary_arc invariant failed: arc motion is not admitted by policy"
        )
    if arc.relational_kind not in resolved_policy.relation_policy.admitted_kinds:
        raise ValueError(
            "relate_primary_arc invariant failed: arc relational kind is not admitted by policy"
        )
    return PrimaryDirectionRelation(
        arc=arc,
        relation_kind=resolved_policy.perfection_policy.kind,
        converse_doctrine=resolved_policy.converse_doctrine,
        key_policy=resolved_policy.key_policy,
        relational_kind=arc.relational_kind,
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
    try:
        supplied_arcs = tuple(arcs)
    except TypeError as exc:
        raise ValueError(
            "evaluate_primary_direction_condition requires an iterable of PrimaryArc vessels"
        ) from exc
    if any(not isinstance(arc, PrimaryArc) for arc in supplied_arcs):
        raise ValueError(
            "evaluate_primary_direction_condition requires PrimaryArc vessels"
        )
    arc_tuple = tuple(
        sorted(supplied_arcs, key=lambda arc: (arc.arc, arc.promissor, arc.direction))
    )
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
    try:
        arc_tuple = tuple(arcs)
    except TypeError as exc:
        raise ValueError(
            "evaluate_primary_directions_aggregate requires an iterable of PrimaryArc vessels"
        ) from exc
    if any(not isinstance(arc, PrimaryArc) for arc in arc_tuple):
        raise ValueError(
            "evaluate_primary_directions_aggregate requires PrimaryArc vessels"
        )
    grouped: dict[str, list[PrimaryArc]] = {}
    for arc in arc_tuple:
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
    try:
        arc_tuple = tuple(arcs)
    except TypeError as exc:
        raise ValueError(
            "evaluate_primary_directions_network requires an iterable of PrimaryArc vessels"
        ) from exc
    if not arc_tuple:
        raise ValueError("evaluate_primary_directions_network requires at least one arc")

    node_names: set[str] = set()
    edge_map: dict[tuple[str, str], list[PrimaryArc]] = {}
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    direct: dict[str, int] = {}
    converse: dict[str, int] = {}
    for arc in arc_tuple:
        if not isinstance(arc, PrimaryArc):
            raise ValueError("evaluate_primary_directions_network requires PrimaryArc vessels")
        node_names.add(arc.significator)
        node_names.add(arc.promissor)
        edge_map.setdefault((arc.promissor, arc.significator), []).append(arc)
        outgoing[arc.promissor] = outgoing.get(arc.promissor, 0) + 1
        incoming[arc.significator] = incoming.get(arc.significator, 0) + 1
        motion_counts = direct if arc.is_direct else converse
        motion_counts[arc.promissor] = motion_counts.get(arc.promissor, 0) + 1
        motion_counts[arc.significator] = motion_counts.get(arc.significator, 0) + 1

    nodes = tuple(
        sorted(
            (
                PrimaryDirectionsNetworkNode(
                    name=name,
                    incoming_count=incoming.get(name, 0),
                    outgoing_count=outgoing.get(name, 0),
                    total_count=incoming.get(name, 0) + outgoing.get(name, 0),
                    direct_count=direct.get(name, 0),
                    converse_count=converse.get(name, 0),
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
                    direct_count=sum(arc.is_direct for arc in group),
                    converse_count=sum(arc.is_converse for arc in group),
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
