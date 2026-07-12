"""Three-chart Church of Light natal Astrodyne parity corpus."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from moira import Body
from moira.astrodynes import (
    ASTRODYNE_PLANETS,
    AstrodyneAspectRelation,
    natal_astrodynes_from_geometry,
)
from moira.coordinates import ecliptic_to_equatorial


pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris]

_FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "astrodynes_church_of_light.json"
)
_BODY_IDS = {body: index for index, body in enumerate((*ASTRODYNE_PLANETS, "M.C.", "Asc."))}
_EPHEMERIS_BODIES = tuple(getattr(Body, body.upper()) for body in ASTRODYNE_PLANETS)


def _corpus() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _pair_key(body_a: str, body_b: str, kind: str) -> tuple[str, str, str]:
    first, second = sorted((body_a, body_b), key=_BODY_IDS.__getitem__)
    return first, second, kind


def _result_for(moira_engine, fixture: dict):
    epoch = datetime.fromisoformat(fixture["ephemeris_epoch_utc"])
    chart = moira_engine.chart(
        epoch,
        bodies=list(_EPHEMERIS_BODIES),
        include_nodes=False,
    )
    declinations: dict[str, float] = {}
    for body in ASTRODYNE_PLANETS:
        position = chart.planets[body]
        _, declination = ecliptic_to_equatorial(
            position.longitude,
            position.latitude,
            chart.obliquity,
        )
        declinations[body] = declination
    for body, longitude_key in (
        ("M.C.", "mc_longitude_deg"),
        ("Asc.", "asc_longitude_deg"),
    ):
        _, declination = ecliptic_to_equatorial(
            fixture[longitude_key],
            0.0,
            chart.obliquity,
        )
        declinations[body] = declination

    return natal_astrodynes_from_geometry(
        fixture["planet_longitudes_deg"],
        declinations,
        fixture["cusp_longitudes_deg"],
        fixture["mc_longitude_deg"],
        fixture["asc_longitude_deg"],
    )


@pytest.fixture(scope="module", params=_corpus()["charts"], ids=lambda row: row["id"])
def church_chart(request, moira_engine):
    fixture = request.param
    return fixture, _result_for(moira_engine, fixture)


def test_corpus_pins_all_125_published_relation_cells() -> None:
    corpus = _corpus()
    assert corpus["authority"]["url"] == (
        "https://www.churchoflight.tv/pdf/01-Astrodynes-Planets.pdf"
    )
    assert sum(len(chart["expected_relations"]) for chart in corpus["charts"]) == 125


def test_published_relation_grid(church_chart) -> None:
    fixture, result = church_chart
    expected = {
        _pair_key(body_a, body_b, kind): (power, harmony)
        for body_a, body_b, kind, power, harmony in fixture["expected_relations"]
    }
    actual = {
        _pair_key(
            relation.body_a,
            relation.body_b,
            "parallel" if relation.aspect == "parallel" else "zodiacal",
        ): relation
        for relation in result.relations.admitted
        if isinstance(relation, AstrodyneAspectRelation)
    }

    assert set(actual) == set(expected), fixture["id"]
    for key, (expected_power, expected_harmony) in expected.items():
        relation = actual[key]
        # Zodiacal positions are printed to arcminutes and the source applies
        # its two-place minute conversion table before scoring. Parallels use
        # DE441 declinations because the reports do not print declinations.
        tolerance = 0.05 if key[2] == "parallel" else 0.026
        assert relation.power == pytest.approx(expected_power, abs=tolerance), (
            fixture["id"],
            key,
        )
        assert relation.net_harmony == pytest.approx(expected_harmony, abs=tolerance), (
            fixture["id"],
            key,
        )


def test_published_planet_and_chart_totals(church_chart) -> None:
    fixture, result = church_chart
    for body, (expected_power, expected_harmony) in fixture["expected_planets"].items():
        profile = result.profile(body)
        assert profile.total_power == pytest.approx(expected_power, abs=0.08), (
            fixture["id"],
            body,
        )
        assert profile.net_harmony == pytest.approx(expected_harmony, abs=0.08), (
            fixture["id"],
            body,
        )

    expected_power, expected_harmony = fixture["expected_total"]
    assert sum(profile.total_power for profile in result.profiles) == pytest.approx(
        expected_power,
        abs=0.15,
    )
    assert sum(profile.net_harmony for profile in result.profiles) == pytest.approx(
        expected_harmony,
        abs=0.15,
    )


def test_published_sign_house_and_summary_rows(church_chart) -> None:
    fixture, result = church_chart
    for house, (expected_power, expected_harmony) in fixture["expected_houses"].items():
        aggregate = result.house(int(house))
        assert aggregate.total_power == pytest.approx(expected_power, abs=0.12), (
            fixture["id"],
            "house",
            house,
        )
        assert aggregate.net_harmony == pytest.approx(expected_harmony, abs=0.12), (
            fixture["id"],
            "house",
            house,
        )

    for sign, (expected_power, expected_harmony) in fixture["expected_signs"].items():
        aggregate = result.sign(sign)
        assert aggregate.total_power == pytest.approx(expected_power, abs=0.12), (
            fixture["id"],
            "sign",
            sign,
        )
        assert aggregate.net_harmony == pytest.approx(expected_harmony, abs=0.12), (
            fixture["id"],
            "sign",
            sign,
        )

    for family_name, expected_entries in fixture["expected_summaries"].items():
        actual_entries = {
            entry.name: entry for entry in getattr(result.summary, family_name)
        }
        assert set(actual_entries) == set(expected_entries)
        for name, (expected_power, expected_harmony) in expected_entries.items():
            entry = actual_entries[name]
            assert entry.power == pytest.approx(expected_power, abs=0.18), (
                fixture["id"],
                family_name,
                name,
            )
            assert entry.net_harmony == pytest.approx(expected_harmony, abs=0.18), (
                fixture["id"],
                family_name,
                name,
            )
