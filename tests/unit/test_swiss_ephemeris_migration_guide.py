"""Drift guards for the public Swiss Ephemeris migration guide."""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import moira
from moira import Body, HouseSystem, Moira
from moira.aspects import AspectPolicy
from moira.houses import HouseCusps, HousePolicy
from moira.julian import DeltaTPolicy, jd_from_datetime, julian_day
from moira.planets import CartesianPosition, PlanetData, SkyPosition, planet_at
from moira.sidereal import Ayanamsa
from moira.sky.events import RiseSetPolicy, find_phenomena
from moira.spk_reader import SpkReader, use_reader_override


REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE_PATH = REPO_ROOT / "wiki" / "02_services" / "MIGRATING_FROM_SWISS_EPHEMERIS.md"


def _guide() -> str:
    return GUIDE_PATH.read_text(encoding="utf-8")


def test_python_examples_are_syntactically_valid() -> None:
    blocks = re.findall(r"```python\n(.*?)```", _guide(), flags=re.DOTALL)

    assert len(blocks) >= 12
    for index, source in enumerate(blocks, start=1):
        try:
            ast.parse(source, filename=f"migration-guide-example-{index}.py")
        except SyntaxError as exc:  # pragma: no cover - assertion detail
            raise AssertionError(f"Python example {index} does not compile") from exc


def test_local_markdown_links_resolve() -> None:
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", _guide())
    local_targets = [
        target.split("#", 1)[0]
        for target in targets
        if not target.startswith(("http://", "https://", "#"))
    ]

    assert local_targets
    for target in local_targets:
        assert (GUIDE_PATH.parent / target).resolve().exists(), target


def test_guide_declares_version_scope_and_non_drop_in_boundary() -> None:
    text = _guide()

    assert f"**Verified against:** `moira-astro` {moira.__version__}" in text
    assert "**Last verified:** 2026-08-11" in text
    assert "not a drop-in reimplementation" in text
    assert "direct" in text
    assert "policy translation" in text
    assert "separate product" in text
    assert "no direct equivalent" in text


def test_guide_states_swiss_digits_are_not_a_target() -> None:
    text = _guide()

    assert "Why a Swiss number is not a Moira number" in text
    assert "does not treat Swiss digits as a target" in text
    assert "4–7′" in text
    assert "IERS 2003 **secular** mean apogee" in text
    assert "ELP **hybrid**" in text
    assert "SE_MEAN_APOG` → `Body.LILITH` is a **policy translation**" in text


def test_documented_facade_and_low_level_signatures_still_exist() -> None:
    assert list(inspect.signature(Moira).parameters) == ["kernel_path"]
    assert {
        "dt",
        "bodies",
        "include_nodes",
        "observer_lat",
        "observer_lon",
        "observer_elev_m",
    } <= set(inspect.signature(Moira.chart).parameters)
    assert {"dt", "latitude", "longitude", "system", "policy"} <= set(
        inspect.signature(Moira.houses).parameters
    )
    assert {"apparent", "aberration", "grav_deflection", "nutation"} <= set(
        inspect.signature(planet_at).parameters
    )
    assert {"center", "frame", "observer_lat", "observer_lon"} <= set(
        inspect.signature(planet_at).parameters
    )
    assert list(inspect.signature(jd_from_datetime).parameters) == ["dt"]
    assert list(inspect.signature(julian_day).parameters) == [
        "year",
        "month",
        "day",
        "hour",
    ]
    assert {"body_name", "jd_start", "lat", "lon", "policy"} <= set(
        inspect.signature(find_phenomena).parameters
    )


def test_documented_body_and_house_identity_mappings_are_current() -> None:
    assert Body.SUN == "Sun"
    assert Body.MOON == "Moon"
    assert Body.MEAN_NODE == "Mean Node"
    assert Body.TRUE_NODE == "True Node"
    assert Body.LILITH == "Lilith"
    assert Body.TRUE_LILITH == "True Lilith"
    assert Body.CHIRON == "Chiron"

    assert HouseSystem.PLACIDUS == "P"
    assert HouseSystem.EQUAL == "E"
    assert HouseSystem.SUNSHINE == "N"
    assert HouseSystem.CARTER == "CT"
    assert HouseSystem.EQUAL_MC == "EM"
    assert HouseSystem.PULLEN_SD == "PSD"
    assert HouseSystem.PULLEN_SR == "PSR"
    assert Body.ALL_PLANETS == [
        Body.SUN,
        Body.MOON,
        Body.MERCURY,
        Body.VENUS,
        Body.MARS,
        Body.JUPITER,
        Body.SATURN,
        Body.URANUS,
        Body.NEPTUNE,
        Body.PLUTO,
    ]
    assert {Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH, Body.TRUE_LILITH} <= set(
        Body.ALL_POINTS
    )


def test_documented_result_and_policy_fields_are_current() -> None:
    assert {
        "longitude",
        "latitude",
        "distance",
        "speed",
        "retrograde",
        "is_topocentric",
    } <= set(PlanetData.__annotations__)
    assert isinstance(PlanetData.distance_au, property)
    assert {"right_ascension", "declination", "azimuth", "altitude", "distance"} <= set(
        SkyPosition.__annotations__
    )
    assert {"x", "y", "z", "center"} <= set(CartesianPosition.__annotations__)
    assert {"system", "effective_system", "fallback", "fallback_reason", "policy"} <= set(
        HouseCusps.__annotations__
    )

    assert DeltaTPolicy(model="hybrid").model == "hybrid"
    assert DeltaTPolicy(model="physical").model == "physical"
    assert DeltaTPolicy(model="nasa_canon").model == "nasa_canon"
    assert DeltaTPolicy(model="fixed", fixed_delta_t=69.0).fixed_delta_t == 69.0
    strict_houses = HousePolicy.strict()
    assert strict_houses.unknown_system.value == "raise"
    assert strict_houses.polar_fallback.value == "raise"
    assert AspectPolicy(tier=0, include_minor=False).tier == 0
    assert isinstance(RiseSetPolicy(), RiseSetPolicy)
    assert Ayanamsa.LAHIRI == "Lahiri"
    assert callable(SpkReader)
    assert callable(use_reader_override)
    assert callable(Moira.heliocentric)
    assert callable(Moira.ssb_chart)


def test_high_risk_migration_warnings_remain_prominent() -> None:
    text = _guide()

    required_phrases = (
        "**`.distance` is kilometres**",
        "proleptic Gregorian calendar",
        "`jd_ut` means **UT1**",
        "Never pass an existing Swiss house-code literal through to Moira",
        "No Moshier fallback",
        "Missing latitude/radial speed is not represented as zero",
        "gate on `/ready`, not only `/health`",
        "circular_error_deg",
    )
    for phrase in required_phrases:
        assert phrase in text


def test_guide_is_discoverable_and_publishable() -> None:
    home = (REPO_ROOT / "wiki" / "Home.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    llms = (REPO_ROOT / "llms.txt").read_text(encoding="utf-8")
    llms_full = (REPO_ROOT / "llms-full.txt").read_text(encoding="utf-8")
    publication = (REPO_ROOT / "website_docs" / "publication_sources.json").read_text(
        encoding="utf-8"
    )

    for document in (home, readme, llms, llms_full):
        assert "MIGRATING_FROM_SWISS_EPHEMERIS.md" in document
    assert '"id": "migrating-from-swiss-ephemeris"' in publication
    assert '"route": "/docs/migrating-from-swiss-ephemeris"' in publication
