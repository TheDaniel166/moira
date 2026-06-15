from __future__ import annotations

import importlib

import pytest

import moira.facade as facade

lord_of_the_orb = importlib.import_module("moira.lord_of_the_orb")


def test_annual_lord_facade_lord_of_orb_delegates_to_engine() -> None:
    engine = facade.Moira()

    via_facade = engine.lord_of_orb("Venus", 84)
    direct = lord_of_the_orb.lord_of_orb("Venus", 84)

    assert via_facade == direct
    assert lord_of_the_orb.validate_lord_of_orb_output(via_facade) == []


def test_annual_lord_facade_current_lord_of_orb_delegates_to_engine() -> None:
    engine = facade.Moira()

    assert engine.current_lord_of_orb("Venus", 7) == lord_of_the_orb.current_lord_of_orb(
        "Venus",
        7,
    )


def test_annual_lord_facade_lord_of_orb_accepts_policy() -> None:
    engine = facade.Moira()
    policy = lord_of_the_orb.LordOfOrbPolicy(
        cycle_kind=lord_of_the_orb.LordOfOrbCycleKind.SINGLE_CYCLE,
    )

    assert engine.lord_of_orb("Venus", 24, policy=policy) == lord_of_the_orb.lord_of_orb(
        "Venus",
        24,
        policy=policy,
    )
    assert engine.current_lord_of_orb(
        "Venus",
        13,
        policy=policy,
    ) == lord_of_the_orb.current_lord_of_orb("Venus", 13, policy=policy)


def test_annual_lord_facade_preserves_caller_supplied_birth_planet_boundary() -> None:
    engine = facade.Moira()

    with pytest.raises(ValueError, match="birth_planet must be one of"):
        engine.lord_of_orb("NotAPlanet", 12)

    with pytest.raises(ValueError, match="birth_planet must be one of"):
        engine.current_lord_of_orb("", 0)
