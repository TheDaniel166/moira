from __future__ import annotations

import pytest

from moira.primary_directions import (
    MorinusAspectContext,
    PrimaryDirectionAntisciaKind,
    PrimaryDirectionAntisciaTarget,
    PrimaryDirectionFixedStarTarget,
    PlacidianRaptParallelTarget,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionLatitudeSource,
    PrimaryDirectionMethod,
    PrimaryDirectionMotion,
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionSpace,
    PrimaryDirectionTargetClass,
    PrimaryDirectionsPreset,
    PtolemaicParallelRelation,
    PtolemaicParallelTarget,
    primary_directions_policy_preset,
)
from moira.primary_directions.relations import (
    PrimaryDirectionRelationalKind,
)


def test_primary_directions_policy_preset_builds_plain_positional_branch() -> None:
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.REGIOMONTANUS_ZODIACAL)

    assert policy.method is PrimaryDirectionMethod.REGIOMONTANUS
    assert policy.latitude_policy.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
    assert policy.latitude_source_policy.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
    assert policy.perfection_policy.kind is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    assert policy.relation_policy.admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
        }
    )


def test_primary_directions_policy_preset_builds_aspect_branch() -> None:
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.MORINUS_ZODIACAL_ASPECT)

    assert policy.method is PrimaryDirectionMethod.MORINUS
    assert policy.latitude_source_policy.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED
    assert policy.relation_policy.admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
        }
    )


def test_topocentric_signed_primary_motion_preset_is_source_scoped() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION
    )

    assert policy.method is PrimaryDirectionMethod.TOPOCENTRIC
    assert policy.space is PrimaryDirectionSpace.IN_ZODIACO
    assert policy.include_converse is True
    assert (
        policy.converse_doctrine
        is PrimaryDirectionConverseDoctrine.SIGNED_PRIMARY_MOTION
    )
    assert (
        policy.latitude_policy.doctrine
        is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
    )
    assert (
        policy.latitude_source_policy.source
        is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
    )
    assert (
        policy.perfection_policy.kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    )
    assert policy.relation_policy.admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
        }
    )


def test_topocentric_signed_primary_motion_preset_rejects_direct_only_override() -> None:
    with pytest.raises(ValueError, match="requires signed direct/converse admission"):
        primary_directions_policy_preset(
            PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION,
            include_converse=False,
        )


@pytest.mark.parametrize(
    "advanced_kwargs",
    (
        {
            "morinus_aspect_contexts": (
                MorinusAspectContext(
                    source_name="Moon",
                    maximum_latitude=5.0,
                    moving_toward_maximum=True,
                ),
            )
        },
        {
            "antiscia_targets": (
                PrimaryDirectionAntisciaTarget(
                    "Moon",
                    PrimaryDirectionAntisciaKind.ANTISCION,
                ),
            )
        },
        {
            "ptolemaic_parallel_targets": (
                PtolemaicParallelTarget(
                    "Moon",
                    PtolemaicParallelRelation.PARALLEL,
                ),
            )
        },
        {
            "placidian_rapt_parallel_targets": (
                PlacidianRaptParallelTarget("Moon"),
            )
        },
    ),
)
def test_topocentric_signed_primary_motion_preset_rejects_doctrine_widening(
    advanced_kwargs: dict,
) -> None:
    with pytest.raises(ValueError, match="does not admit non-fixed-star advanced"):
        primary_directions_policy_preset(
            PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION,
            **advanced_kwargs,
        )


def test_primary_directions_policy_preset_builds_ptolemaic_parallel_branch() -> None:
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL)

    assert policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
    assert policy.latitude_policy.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
    assert policy.latitude_source_policy.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
    assert policy.perfection_policy.kind is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    assert policy.relation_policy.admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
            PrimaryDirectionRelationalKind.PARALLEL,
            PrimaryDirectionRelationalKind.CONTRA_PARALLEL,
        }
    )


def test_primary_directions_policy_preset_builds_ptolemaic_antiscia_branch() -> None:
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA)

    assert policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
    assert policy.latitude_policy.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
    assert policy.latitude_source_policy.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
    assert policy.perfection_policy.kind is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
    assert policy.relation_policy.admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ANTISCION,
            PrimaryDirectionRelationalKind.CONTRA_ANTISCION,
        }
    )


def test_primary_directions_policy_preset_threads_parallel_targets() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_PARALLEL,
        ptolemaic_parallel_targets=(
            PtolemaicParallelTarget("Venus", PtolemaicParallelRelation.CONTRA_PARALLEL),
        ),
    )

    assert policy.ptolemaic_parallel_targets == (
        PtolemaicParallelTarget("Venus", PtolemaicParallelRelation.CONTRA_PARALLEL),
    )


def test_primary_directions_policy_preset_threads_fixed_star_targets() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
        include_converse=False,
        fixed_star_targets=(PrimaryDirectionFixedStarTarget("Sirius"),),
    )

    assert policy.fixed_star_targets == (PrimaryDirectionFixedStarTarget("Sirius"),)


def test_primary_directions_policy_preset_threads_antiscia_targets() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA,
        antiscia_targets=(
            PrimaryDirectionAntisciaTarget(
                "Sun",
                PrimaryDirectionAntisciaKind.CONTRA_ANTISCION,
            ),
        ),
    )

    assert policy.antiscia_targets == (
        PrimaryDirectionAntisciaTarget(
            "Sun",
            PrimaryDirectionAntisciaKind.CONTRA_ANTISCION,
        ),
    )


def test_primary_directions_policy_preset_respects_direct_only_flag() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
        include_converse=False,
    )

    assert policy.include_converse is False
    assert policy.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY


def test_primary_directions_policy_preset_builds_placidian_rapt_parallel_branch() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT,
        include_converse=False,
        placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget("Moon"),),
    )

    assert policy.method is PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC
    assert policy.include_converse is False
    assert policy.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY
    assert policy.placidian_rapt_parallel_targets == (PlacidianRaptParallelTarget("Moon"),)
    assert policy.relation_policy.admitted_kinds == frozenset(
        {
            PrimaryDirectionRelationalKind.RAPT_PARALLEL,
        }
    )


def test_primary_directions_policy_preset_builds_placidian_converse_rapt_parallel_branch() -> None:
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE,
        include_converse=False,
        placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget("Moon"),),
    )

    assert policy.method is PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC
    assert policy.include_converse is False
    assert (
        policy.converse_doctrine
        is PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    )
    assert policy.placidian_rapt_parallel_targets == (PlacidianRaptParallelTarget("Moon"),)
    assert policy.placidian_rapt_parallel_motion is PrimaryDirectionMotion.CONVERSE
    assert policy.admitted_motions == (PrimaryDirectionMotion.DIRECT,)
    assert policy.admits_motion(
        PrimaryDirectionMotion.CONVERSE,
        relational_kind=PrimaryDirectionRelationalKind.RAPT_PARALLEL,
    )


@pytest.mark.parametrize("preset", tuple(PrimaryDirectionsPreset))
def test_every_preset_composes_with_fixed_star_targets(preset: PrimaryDirectionsPreset) -> None:
    kwargs = {
        "fixed_star_targets": (PrimaryDirectionFixedStarTarget("Sirius"),),
    }
    if preset in (
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT,
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE,
    ):
        kwargs["include_converse"] = False

    policy = primary_directions_policy_preset(preset, **kwargs)

    assert policy.fixed_star_targets == (PrimaryDirectionFixedStarTarget("Sirius"),)
    assert policy.target_policy.admitted_significator_classes <= frozenset(
        {
            # Fixed-star directions are admitted narrowly to planet/angle significators.
            PrimaryDirectionTargetClass.PLANET,
            PrimaryDirectionTargetClass.ANGLE,
        }
    )
