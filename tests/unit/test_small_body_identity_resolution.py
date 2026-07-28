"""Unified small-body identity and cross-family collision policy."""

from __future__ import annotations

import pytest

import moira.void_of_course as void_of_course_module
from moira.planets import _resolve_small_body_name, planet_at
from moira.small_body_identity import (
    AmbiguousSmallBodyNameError,
    resolve_small_body_identity,
    small_body_name_collisions,
)


def test_collision_inventory_exposes_every_current_cross_family_match() -> None:
    collisions = small_body_name_collisions()

    assert {collision.normalized_name for collision in collisions} == {
        "encke",
        "halley",
    }
    assert {
        (
            collision.normalized_name,
            tuple(
                (candidate.family, candidate.canonical_name, candidate.naif_id)
                for candidate in collision.candidates
            ),
        )
        for collision in collisions
    } == {
        (
            "encke",
            (
                ("asteroid", "Encke", 2_009_134),
                ("comet", "2P/Encke", 1_000_002),
            ),
        ),
        (
            "halley",
            (
                ("asteroid", "Halley", 2_002_688),
                ("comet", "1P/Halley", 1_000_001),
            ),
        ),
    }


@pytest.mark.parametrize("name", ["Halley", "halley", " Encke "])
def test_unqualified_cross_family_names_fail_closed(name: str) -> None:
    with pytest.raises(AmbiguousSmallBodyNameError) as raised:
        resolve_small_body_identity(name)

    error = raised.value
    assert error.query.casefold() in {"halley", "encke"}
    assert [candidate.family for candidate in error.candidates] == [
        "asteroid",
        "comet",
    ]
    assert "ambiguous across families" in str(error)
    assert f"asteroid:{error.query}" in str(error)
    assert f"comet:{error.query}" in str(error)


def test_family_qualification_resolves_each_halley_identity() -> None:
    asteroid = resolve_small_body_identity("asteroid:Halley")
    comet = resolve_small_body_identity(" COMET: halley ")

    assert asteroid is not None
    assert asteroid.family == "asteroid"
    assert asteroid.canonical_name == "Halley"
    assert asteroid.naif_id == 2_002_688
    assert asteroid.is_alias is False

    assert comet is not None
    assert comet.family == "comet"
    assert comet.canonical_name == "1P/Halley"
    assert comet.naif_id == 1_000_001
    assert comet.matched_name == "Halley"
    assert comet.is_alias is True


def test_explicit_family_and_canonical_comet_name_are_unambiguous() -> None:
    asteroid = resolve_small_body_identity("Halley", family="asteroid")
    comet = resolve_small_body_identity("1p/halley")

    assert asteroid is not None
    assert asteroid.qualified_name == "asteroid:Halley"
    assert comet is not None
    assert comet.qualified_name == "comet:1P/Halley"


def test_identity_matching_uses_catalog_nfkc_casefold_policy() -> None:
    identity = resolve_small_body_identity("Ｃｅｒｅｓ")

    assert identity is not None
    assert identity.family == "asteroid"
    assert identity.canonical_name == "Ceres"


def test_invalid_or_conflicting_qualifiers_fail_clearly() -> None:
    with pytest.raises(ValueError, match="unknown small-body family"):
        resolve_small_body_identity("minor-planet:Ceres")
    with pytest.raises(ValueError, match="require a name after"):
        resolve_small_body_identity("comet:")
    with pytest.raises(ValueError, match="conflicts with qualifier"):
        resolve_small_body_identity("comet:Halley", family="asteroid")


def test_planetary_compatibility_resolver_returns_canonical_family_identity() -> None:
    assert _resolve_small_body_name("comet:Halley") == ("comet", "1P/Halley")
    assert _resolve_small_body_name("Halley", family="asteroid") == (
        "asteroid",
        "Halley",
    )
    assert _resolve_small_body_name("NotASmallBody") is None


def test_planet_at_rejects_ambiguous_identity_before_kernel_access() -> None:
    with pytest.raises(AmbiguousSmallBodyNameError, match="asteroid:Halley"):
        planet_at("Halley", 2_451_545.0)


def test_void_of_course_body_lookup_obeys_unified_family_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_asteroid_at(name: str, jd: float, *, reader):
        calls.append(("asteroid", name))
        return type("_Position", (), {"longitude": 12.0})()

    def fake_comet_at(name: str, jd: float, *, reader):
        calls.append(("comet", name))
        return type("_Position", (), {"longitude": 34.0})()

    monkeypatch.setattr(void_of_course_module, "asteroid_at", fake_asteroid_at)
    monkeypatch.setattr(void_of_course_module, "comet_at", fake_comet_at)
    reader = object()

    assert (
        void_of_course_module._body_longitude(
            "asteroid:Halley",
            2_451_545.0,
            reader,
        )
        == 12.0
    )
    assert (
        void_of_course_module._body_longitude(
            "comet:Halley",
            2_451_545.0,
            reader,
        )
        == 34.0
    )
    assert calls == [
        ("asteroid", "Halley"),
        ("comet", "1P/Halley"),
    ]
    with pytest.raises(AmbiguousSmallBodyNameError):
        void_of_course_module._body_longitude("Halley", 2_451_545.0, reader)
