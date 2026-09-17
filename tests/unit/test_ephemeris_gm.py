"""Pinned JPL Horizons gravity-policy contracts for orbital elements."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from moira._ephemeris_gm import (
    HORIZONS_GM_KM3_S2,
    HORIZONS_GM_SOURCE_BYTES,
    HORIZONS_GM_SOURCE_SHA256,
    select_orbital_gravity,
)
from moira._orbital_errors import OrbitalGravityModelError


IDENTITY = SimpleNamespace(
    planetary_ephemeris="DE441",
    summary_label="DE-0441LE-0441",
)
TIME_AUTHORITY = json.loads(
    (
        Path(__file__).parents[1]
        / "fixtures"
        / "orbital_time_naif0012_reference.json"
    ).read_text(encoding="utf-8")
)


def test_gravity_table_matches_parsed_primary_horizons_pck_fixture():
    expected = {
        int(naif_id): value
        for naif_id, value in TIME_AUTHORITY["gravity_model"][
            "values_by_naif_id"
        ].items()
    }
    assert HORIZONS_GM_KM3_S2 == expected
    assert TIME_AUTHORITY["gravity_model"]["assignment_rule"] == (
        "last textual PCK assignment wins"
    )


@pytest.mark.parametrize(
    ("center", "kind", "naif_id", "components", "rule"),
    [
        ("SUN", "PLANET_BODY", 199, (10, 199), "SUN_PLUS_PLANET_BODY"),
        ("SUN", "PLANET_BODY", 299, (10, 299), "SUN_PLUS_PLANET_BODY"),
        ("SUN", "PLANET_BODY", 399, (10, 399), "SUN_PLUS_PLANET_BODY"),
        ("SUN", "PLANET_SYSTEM_BARYCENTER", 4, (10, 4), "SUN_PLUS_PLANET_SYSTEM"),
        ("SUN", "PLANET_SYSTEM_BARYCENTER", 9, (10, 9), "SUN_PLUS_PLANET_SYSTEM"),
        ("SUN", "EARTH_MOON_BARYCENTER", 3, (10, 3), "SUN_PLUS_EARTH_MOON_SYSTEM"),
        ("EARTH", "MOON", 301, (399, 301), "EARTH_PLUS_MOON"),
        ("SUN", "ASTEROID", 2000001, (10,), "SUN_MASSLESS_TARGET"),
        ("SUN", "COMET", 1000036, (10,), "SUN_MASSLESS_TARGET"),
    ],
)
def test_every_gravity_rule(center, kind, naif_id, components, rule):
    selected = select_orbital_gravity(
        center_key=center,
        body_kind=kind,
        naif_id=naif_id,
        identity=IDENTITY,
    )
    assert selected.rule == rule
    assert selected.component_naif_ids == components
    assert selected.component_gm_km3_s2 == tuple(
        HORIZONS_GM_KM3_S2[item] for item in components
    )
    assert selected.gm_km3_s2 == sum(selected.component_gm_km3_s2)
    assert selected.gm_km3_day2 == selected.gm_km3_s2 * 86400.0**2
    assert selected.source_bytes == HORIZONS_GM_SOURCE_BYTES == 15428
    assert selected.source_sha256 == HORIZONS_GM_SOURCE_SHA256
    assert selected.planetary_ephemeris == "DE441"


@pytest.mark.parametrize("planetary_ephemeris", [None, "DE430", "DE442"])
def test_unadmitted_ephemeris_identity_fails(planetary_ephemeris):
    with pytest.raises(OrbitalGravityModelError):
        select_orbital_gravity(
            center_key="SUN",
            body_kind="PLANET_BODY",
            naif_id=399,
            identity=SimpleNamespace(
                planetary_ephemeris=planetary_ephemeris,
                summary_label="content label",
            ),
        )


def test_de440_is_separately_admitted():
    selected = select_orbital_gravity(
        center_key="SUN",
        body_kind="PLANET_BODY",
        naif_id=399,
        identity=SimpleNamespace(
            planetary_ephemeris="DE440",
            summary_label="DE-0440LE-0440",
        ),
    )
    assert selected.planetary_ephemeris == "DE440"
