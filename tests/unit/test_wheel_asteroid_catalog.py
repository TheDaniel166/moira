from __future__ import annotations

from moira._wheel_asteroid_catalog import (
    CATALOG_DIR,
    CATALOG_ID,
    CATALOG_VERSION,
    TARGETS_PATH,
    load_targets,
)

LOCKED = [
    (1, "Ceres", 2000001),
    (2, "Pallas", 2000002),
    (3, "Juno", 2000003),
    (4, "Vesta", 2000004),
    (5, "Astraea", 2000005),
    (7, "Iris", 2000007),
    (10, "Hygiea", 2000010),
    (16, "Psyche", 2000016),
    (433, "Eros", 2000433),
    (1181, "Lilith", 2001181),
    (1221, "Amor", 2001221),
    (2060, "Chiron", 2002060),
    (5145, "Pholus", 2005145),
    (7066, "Nessus", 2007066),
    (8405, "Asbolus", 2008405),
    (10199, "Chariklo", 2010199),
    (10370, "Hylonome", 2010370),
    (20000, "Varuna", 2020000),
    (28978, "Ixion", 2028978),
    (50000, "Quaoar", 2050000),
    (90377, "Sedna", 2090377),
    (90482, "Orcus", 2090482),
    (136108, "Haumea", 2136108),
    (136199, "Eris", 2136199),
    (136472, "Makemake", 2136472),
]


def test_locked_roster_is_exactly_twenty_five_naif_ordered_bodies() -> None:
    rows = load_targets()
    assert CATALOG_ID == "moira-asteroids-wheel"
    assert CATALOG_VERSION == "2026.08.14.1"
    assert TARGETS_PATH == CATALOG_DIR / "targets.json"
    assert [(row["number"], row["name"], row["naif_id"]) for row in rows] == LOCKED
    assert [row["naif_id"] for row in rows] == sorted(row["naif_id"] for row in rows)
    assert "Hidalgo" not in {row["name"] for row in rows}
