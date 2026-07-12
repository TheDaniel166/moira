from __future__ import annotations

import pytest

import moira.facade as facade
from moira.behenian_stars import available_behenian_stars
from moira.paran_stars import (
    PARAN_STAR_CANON,
    ParanStarTier,
    list_paran_stars,
    paran_star_tiers,
)
from moira.royal_stars import available_royal_stars
from moira.stars import star_at


def test_paran_star_canon_is_stable_unique_and_catalog_resolved() -> None:
    available = list_paran_stars()

    assert len(available) == 51
    assert len({entry.name for entry in PARAN_STAR_CANON}) == len(PARAN_STAR_CANON)
    assert [entry.name for entry in available][:4] == ["Algol", "Mirfak", "Alcyone", "Maia"]
    assert all(entry.tiers[0] is ParanStarTier.WORKING_CANON for entry in PARAN_STAR_CANON)
    for entry in available:
        assert star_at(entry.name, 2451545.0).name == entry.name


def test_paran_star_tier_memberships_reuse_existing_groups() -> None:
    royal = list_paran_stars(tiers=[ParanStarTier.ROYAL])
    behenian = list_paran_stars(tiers=["behenian"])

    assert [entry.name for entry in royal] == available_royal_stars()
    assert {entry.name for entry in behenian} == set(available_behenian_stars())
    assert paran_star_tiers() == tuple(ParanStarTier)


def test_paran_star_tier_filter_is_union_and_rejects_unknown_tier() -> None:
    selected = list_paran_stars(tiers=["royal", "behenian"])

    assert {entry.name for entry in selected} == (
        set(available_royal_stars()) | set(available_behenian_stars())
    )
    with pytest.raises(ValueError, match="unknown paran star tier"):
        list_paran_stars(tiers=["navigational"])


def test_paran_star_canon_is_exported_through_facade() -> None:
    assert facade.PARAN_STAR_CANON is PARAN_STAR_CANON
    assert facade.ParanStarTier is ParanStarTier
    assert facade.list_paran_stars() == list_paran_stars()
