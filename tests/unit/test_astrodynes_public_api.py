"""SCP Phase 12 public-surface contract for natal Astrodynes."""

from __future__ import annotations

import importlib

import moira
import moira.astrodynes as astrodynes
import moira.facade as facade


ROOT_EXPORTS = (
    "AstrodyneBodyKind",
    "AstrodyneDignityCondition",
    "AstrodyneAspectFamily",
    "AstrodyneRelationKind",
    "AstrodynePolicy",
    "DEFAULT_ASTRODYNE_POLICY",
    "AstrodyneRelationSet",
    "AstrodyneBodyInput",
    "AstrodyneBodyConditionProfile",
    "AstrodyneSignAggregate",
    "AstrodyneHouseAggregate",
    "AstrodyneChartAggregate",
    "AstrodyneNetwork",
    "AstrodyneChartResult",
    "natal_astrodynes",
    "validate_astrodynes_output",
)


def test_module_all_is_bound_unique_and_private_free() -> None:
    assert len(astrodynes.__all__) == len(set(astrodynes.__all__))
    assert all(not name.startswith("_") for name in astrodynes.__all__)
    assert all(hasattr(astrodynes, name) for name in astrodynes.__all__)


def test_curated_root_and_facade_exports_share_module_identity() -> None:
    for name in ROOT_EXPORTS:
        expected = getattr(astrodynes, name)
        assert getattr(moira, name) is expected
        assert getattr(facade, name) is expected
        assert name in moira.__all__
        assert name in facade.__all__


def test_private_assembly_helpers_are_not_root_exports() -> None:
    for name in (
        "_build_relation_set",
        "_build_body_profile",
        "_build_chart_aggregate",
        "_build_network",
        "_canonical_interceptions",
    ):
        assert name not in astrodynes.__all__
        assert name not in moira.__dict__
        assert name not in facade.__dict__


def test_moira_facade_method_delegates_without_kernel(monkeypatch) -> None:
    facade_module = importlib.import_module("moira.facade")
    sentinel = object()
    captured: dict[str, object] = {}

    def fake_natal(body_inputs, cusp_signs, *, intercepted_signs_by_house, policy):
        captured.update(
            body_inputs=body_inputs,
            cusp_signs=cusp_signs,
            intercepted_signs_by_house=intercepted_signs_by_house,
            policy=policy,
        )
        return sentinel

    monkeypatch.setattr(facade_module, "natal_astrodynes", fake_natal)
    engine = moira.Moira()
    policy = astrodynes.DEFAULT_ASTRODYNE_POLICY
    result = engine.astrodynes(
        ("inputs",),
        ("cusps",),
        intercepted_signs_by_house={1: ("Gemini",)},
        policy=policy,
    )

    assert result is sentinel
    assert captured == {
        "body_inputs": ("inputs",),
        "cusp_signs": ("cusps",),
        "intercepted_signs_by_house": {1: ("Gemini",)},
        "policy": policy,
    }
