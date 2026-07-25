from __future__ import annotations

import json
from pathlib import Path

from moira.aspects import find_aspects
from moira.asteroid_families import (
    ASTEROID_FAMILY_CATALOG_SOURCE,
    asteroid_families,
    asteroid_family,
    families_in_chart,
    family_members,
    find_resonant_aspects,
)


def test_complete_memberships_preserve_nested_families_and_display_primary() -> None:
    assert asteroid_family(8) == "Flora"
    assert asteroid_families(8) == ["Flora", "Baptistina"]

    assert asteroid_family(158) == "Koronis2"
    assert asteroid_families(158) == ["Koronis2", "Karin", "Koronis"]

    assert asteroid_family(321) == "Florentina"
    assert asteroid_families(321) == [
        "Florentina",
        "Karin",
        "Koronis2",
        "Koronis",
    ]


def test_uncatalogued_asteroid_is_not_mislabeled_as_non_familial() -> None:
    assert asteroid_family(1) is None
    assert asteroid_families(1) == []


def test_legacy_family_names_resolve_to_current_canonical_names() -> None:
    assert family_members("Koronis(2)") == family_members("Koronis2")
    assert family_members("RJ") == family_members("1996 RJ")
    assert family_members("UV209") == family_members("2001 UV209")


def test_chart_grouping_preserves_every_membership() -> None:
    assert families_in_chart([8, 298]) == {
        "Baptistina": [8, 298],
        "Flora": [8, 298],
    }


def test_resonance_emits_one_qualifier_for_each_shared_family() -> None:
    aspect = find_aspects({"Astraea": 0.0, "Baptistina": 0.5}, tier=0)[0]
    resonances = find_resonant_aspects(
        [aspect],
        {"Astraea": 8, "Baptistina": 298},
    )

    assert [item.resonance.family_name for item in resonances] == [
        "Baptistina",
        "Flora",
    ]


def test_bundled_metadata_records_audited_source_boundary() -> None:
    metadata_path = (
        Path(__file__).resolve().parents[2]
        / "moira"
        / "data"
        / "asteroid_families.metadata.json"
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["catalog_id"] == (
        "Moira_asteroid_families_Proper25_2026_plus_PDS_exclusions"
    )
    assert metadata["counts"] == {
        "family_count": 342,
        "maximum_memberships_per_asteroid": 4,
        "membership_row_count": 221095,
        "multi_membership_asteroid_count": 18185,
        "pds_legacy_membership_row_count": 1078,
        "proper25_numbered_membership_row_count": 220017,
        "unique_numbered_asteroid_count": 200726,
    }
    assert ASTEROID_FAMILY_CATALOG_SOURCE == (
        "Proper25_2026_plus_NASA_PDS_2015_excluded_populations"
    )
