"""Kernel-free public export and facade contracts for Pancha Pakshi."""

from __future__ import annotations

import inspect

import pytest

import moira
import moira.facade as facade
import moira.pancha_pakshi as pancha_pakshi
import moira.vedic as vedic


_FACADE_METHODS = (
    "pancha_pakshi_profiles",
    "pancha_pakshi_profile_info",
    "pancha_pakshi_identity_from_initial_vowel",
    "pancha_pakshi_directed_relationship",
    "pancha_pakshi_schedule",
)


@pytest.mark.parametrize("name", pancha_pakshi.__all__)
def test_public_pancha_pakshi_exports_share_identity(name: str) -> None:
    expected = getattr(pancha_pakshi, name)
    for surface in (moira, facade, vedic):
        assert name in surface.__all__
        assert getattr(surface, name) is expected


def test_raw_profile_loader_is_not_promoted_to_a_public_surface() -> None:
    for surface in (moira, facade, vedic):
        assert "PanchaPakshiProfile" not in surface.__all__
        assert "load_pancha_pakshi_profile" not in surface.__all__
        assert not hasattr(surface, "PanchaPakshiProfile")
        assert not hasattr(surface, "load_pancha_pakshi_profile")


def test_facade_requires_explicit_profile_identity_and_keyword_schedule_context() -> None:
    for name in _FACADE_METHODS[1:]:
        profile = inspect.signature(getattr(facade.Moira, name)).parameters[
            "profile_id"
        ]
        assert profile.default is inspect.Parameter.empty

    schedule_parameters = inspect.signature(
        facade.Moira.pancha_pakshi_schedule
    ).parameters
    for name in ("paksha", "half", "weekday"):
        parameter = schedule_parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty


def test_facade_methods_delegate_without_reader_or_kernel_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = None
    calls: list[tuple[object, ...]] = []
    sentinels = [object() for _ in _FACADE_METHODS]

    def profiles():
        calls.append(("profiles",))
        return sentinels[0]

    def profile_info(profile_id):
        calls.append(("profile_info", profile_id))
        return sentinels[1]

    def identity(profile_id, initial_vowel):
        calls.append(("identity", profile_id, initial_vowel))
        return sentinels[2]

    def relationship(profile_id, subject, target):
        calls.append(("relationship", profile_id, subject, target))
        return sentinels[3]

    def schedule(profile_id, *, paksha, half, weekday):
        calls.append(("schedule", profile_id, paksha, half, weekday))
        return sentinels[4]

    monkeypatch.setattr(
        pancha_pakshi,
        "available_pancha_pakshi_profiles",
        profiles,
    )
    monkeypatch.setattr(pancha_pakshi, "pancha_pakshi_profile_info", profile_info)
    monkeypatch.setattr(
        pancha_pakshi,
        "pancha_pakshi_identity_from_initial_vowel",
        identity,
    )
    monkeypatch.setattr(
        pancha_pakshi,
        "pancha_pakshi_directed_relationship",
        relationship,
    )
    monkeypatch.setattr(pancha_pakshi, "pancha_pakshi_schedule", schedule)

    profile_id = "named_source_profile"
    assert engine.pancha_pakshi_profiles() is sentinels[0]
    assert engine.pancha_pakshi_profile_info(profile_id) is sentinels[1]
    assert (
        engine.pancha_pakshi_identity_from_initial_vowel(profile_id, "A")
        is sentinels[2]
    )
    assert (
        engine.pancha_pakshi_directed_relationship(
            profile_id,
            pancha_pakshi.PanchaPakshiBird.OWL,
            pancha_pakshi.PanchaPakshiBird.PEACOCK,
        )
        is sentinels[3]
    )
    assert (
        engine.pancha_pakshi_schedule(
            profile_id,
            paksha=pancha_pakshi.PanchaPakshiPaksha.PURVA,
            half=pancha_pakshi.PanchaPakshiHalf.NIGHT,
            weekday=pancha_pakshi.PanchaPakshiWeekday.SUNDAY,
        )
        is sentinels[4]
    )

    assert calls == [
        ("profiles",),
        ("profile_info", profile_id),
        ("identity", profile_id, "A"),
        (
            "relationship",
            profile_id,
            pancha_pakshi.PanchaPakshiBird.OWL,
            pancha_pakshi.PanchaPakshiBird.PEACOCK,
        ),
        (
            "schedule",
            profile_id,
            pancha_pakshi.PanchaPakshiPaksha.PURVA,
            pancha_pakshi.PanchaPakshiHalf.NIGHT,
            pancha_pakshi.PanchaPakshiWeekday.SUNDAY,
        ),
    ]


@pytest.mark.parametrize("name", _FACADE_METHODS[1:])
def test_facade_rejects_omitted_profile_id_before_delegation(name: str) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = None
    with pytest.raises(TypeError):
        getattr(engine, name)()
