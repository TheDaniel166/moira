"""Public-surface parity checks for the bounded Track-A composition layer."""

from __future__ import annotations

import moira
import moira.astrocartography as astrocartography
import moira.facade as facade
import moira.locational_forecasting as locational
import moira.relationship_forecasting as relationship


def test_relationship_forecasting_root_and_facade_exports_share_authority() -> None:
    names = (
        "RelationshipChartKind",
        "RelationshipTargetKind",
        "RelationshipChartIdentity",
        "RelationshipTransitTarget",
        "RelationshipChartTargetSet",
        "RelationshipTransitEvent",
        "RelationshipTransitSearchTruth",
        "RelationshipTransitSearchResult",
        "relationship_chart_targets",
        "find_relationship_transits",
        "find_composite_transits",
        "find_davison_transits",
    )
    for name in names:
        authoritative = getattr(relationship, name)
        assert getattr(moira, name) is authoritative
        assert getattr(facade, name) is authoritative
        assert name in moira.__all__
        assert name in facade.__all__


def test_locational_forecasting_root_and_facade_exports_share_authority() -> None:
    names = (
        "ReturnKind",
        "ReturnSearchPolicyTruth",
        "ReturnMomentTruth",
        "ReturnRelocationTruth",
        "RelocatedReturnChart",
        "DynamicAstrocartographyMode",
        "DynamicAstrocartographyPosition",
        "DynamicAstrocartographySnapshotTruth",
        "DynamicAstrocartographySnapshot",
        "AstrocartographyCurvePointShift",
        "DynamicAstrocartographyLineTransition",
        "DynamicAstrocartographySeriesTruth",
        "DynamicAstrocartographySeries",
        "relocated_solar_return",
        "relocated_lunar_return",
        "relocated_planetary_return",
        "transiting_astrocartography",
    )
    for name in names:
        authoritative = getattr(locational, name)
        assert getattr(moira, name) is authoritative
        assert getattr(facade, name) is authoritative
        assert name in moira.__all__
        assert name in facade.__all__


def test_fixed_star_astrocartography_root_and_facade_exports_share_authority() -> None:
    names = (
        "FixedStarAstrocartographySubject",
        "FixedStarAstrocartographyTruth",
        "FixedStarAstrocartographyResult",
        "fixed_star_equatorial_subject",
        "fixed_star_astrocartography",
        "fixed_star_astrocartography_from_chart",
    )
    for name in names:
        authoritative = getattr(astrocartography, name)
        assert getattr(moira, name) is authoritative
        assert getattr(facade, name) is authoritative
        assert name in moira.__all__
        assert name in facade.__all__


def test_moira_facade_exposes_reader_bound_track_a_methods() -> None:
    expected_methods = {
        "relationship_chart_targets",
        "relationship_transits",
        "composite_transits",
        "davison_transits",
        "fixed_star_astrocartography",
        "transiting_astrocartography",
        "relocated_solar_return",
        "relocated_lunar_return",
        "relocated_planetary_return",
    }
    assert expected_methods <= set(dir(moira.Moira))
