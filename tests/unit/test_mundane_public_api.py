"""Public Python admission tests for the neutral Mundane Track B surface."""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade_module
import moira.mundane as mundane_module
import moira.predictive as predictive_module
from moira._facade_predictive import PredictiveFacadeMixin


_CURATED_PUBLIC_NAMES = frozenset(
    {
        "MundaneEvaluationStatus",
        "MundaneEventType",
        "MundaneEventChartProfile",
        "MundaneProfileProvenance",
        "compose_mundane_event_chart_profile",
        "eclipse_receipt_from_event",
        "jupiter_saturn_sequence_from_series",
    }
)
_FROZEN_MUNDANE_HASHES = {
    "moira/mundane.py": (
        "F417DAA618B69E3C43F668C9AE98D1C258FE1EAFE6AA1F0DAB3EB0928771E71D"
    ),
    "tests/unit/test_mundane.py": (
        "BA2FABBC2272E2FBED03CBAD94785D3D7E1E64CB855F03DC71F567744B69F0BD"
    ),
}


def test_b4_preserves_approved_mundane_files_byte_for_byte() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    for relative_path, expected_hash in _FROZEN_MUNDANE_HASHES.items():
        payload = (repository_root / relative_path).read_bytes()
        assert hashlib.sha256(payload).hexdigest().upper() == expected_hash


def test_curated_root_and_facade_exports_share_exact_module_identity() -> None:
    assert set(mundane_module.__all__) & set(moira.__all__) == _CURATED_PUBLIC_NAMES
    assert (
        set(mundane_module.__all__) & set(facade_module.__all__)
        == _CURATED_PUBLIC_NAMES
    )

    for name in _CURATED_PUBLIC_NAMES:
        assert getattr(moira, name) is getattr(mundane_module, name)
        assert getattr(facade_module, name) is getattr(mundane_module, name)


def test_star_import_admits_only_the_curated_mundane_surface() -> None:
    namespace: dict[str, object] = {}
    exec("from moira import *", {}, namespace)

    mundane_names = set(namespace) & set(mundane_module.__all__)
    assert mundane_names == _CURATED_PUBLIC_NAMES


def test_concrete_receipts_and_adapters_remain_outside_curated_tiers() -> None:
    module_only_names = {
        "CardinalIngressReceipt",
        "PrimarySyzygyReceipt",
        "EclipseEventReceipt",
        "JupiterSaturnConjunctionSequenceReceipt",
        "MundaneEventClockReceipt",
        "assess_transit_cardinal_ingress",
        "assess_transit_primary_syzygy",
    }

    assert module_only_names <= set(mundane_module.__all__)
    assert module_only_names.isdisjoint(moira.__all__)
    assert module_only_names.isdisjoint(facade_module.__all__)
    assert set(mundane_module.__all__).isdisjoint(predictive_module.__all__)
    assert not hasattr(moira, "assess_transit_cardinal_ingress")
    assert not hasattr(moira, "assess_transit_primary_syzygy")


def test_moira_mundane_method_signatures_are_explicit_and_reader_bound() -> None:
    signatures = {
        name: inspect.signature(getattr(facade_module.Moira, name))
        for name in (
            "assess_transit_cardinal_ingress",
            "assess_transit_primary_syzygy",
            "eclipse_receipt_from_event",
            "jupiter_saturn_sequence_from_series",
        )
    }

    assert tuple(signatures["assess_transit_cardinal_ingress"].parameters) == (
        "self",
        "event",
    )
    assert tuple(signatures["assess_transit_primary_syzygy"].parameters) == (
        "self",
        "anchor_event",
        "policy",
    )
    policy = signatures["assess_transit_primary_syzygy"].parameters["policy"]
    assert policy.kind is inspect.Parameter.KEYWORD_ONLY
    assert policy.default is None
    assert tuple(signatures["eclipse_receipt_from_event"].parameters) == (
        "self",
        "event",
        "eclipse_id",
    )
    eclipse_id = signatures["eclipse_receipt_from_event"].parameters["eclipse_id"]
    assert eclipse_id.kind is inspect.Parameter.KEYWORD_ONLY
    assert eclipse_id.default is inspect.Parameter.empty
    assert tuple(signatures["jupiter_saturn_sequence_from_series"].parameters) == (
        "self",
        "series",
    )
    assert all("reader" not in signature.parameters for signature in signatures.values())
    assert not hasattr(facade_module.Moira, "compose_mundane_event_chart_profile")


def test_moira_ingress_and_syzygy_methods_bind_exactly_one_instance_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = object()
    event = object()
    anchor_event = object()
    policy = object()
    ingress_result = object()
    syzygy_result = object()
    captured: list[tuple[object, ...]] = []

    def fake_ingress(supplied_event, *, reader):
        captured.append(("ingress", supplied_event, reader))
        return ingress_result

    def fake_syzygy(supplied_anchor, *, reader, policy):
        captured.append(("syzygy", supplied_anchor, reader, policy))
        return syzygy_result

    monkeypatch.setattr(facade_module, "assess_transit_cardinal_ingress", fake_ingress)
    monkeypatch.setattr(facade_module, "assess_transit_primary_syzygy", fake_syzygy)
    engine = SimpleNamespace(_reader=reader)

    assert (
        PredictiveFacadeMixin.assess_transit_cardinal_ingress(engine, event)
        is ingress_result
    )
    assert (
        PredictiveFacadeMixin.assess_transit_primary_syzygy(
            engine,
            anchor_event,
            policy=policy,
        )
        is syzygy_result
    )
    assert captured == [
        ("ingress", event, reader),
        ("syzygy", anchor_event, reader, policy),
    ]


def test_moira_eclipse_and_sequence_methods_bind_exactly_one_instance_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = object()
    event = object()
    series = object()
    eclipse_result = object()
    sequence_result = object()
    captured: list[tuple[object, ...]] = []

    def fake_eclipse(supplied_event, *, eclipse_id, reader):
        captured.append(("eclipse", supplied_event, eclipse_id, reader))
        return eclipse_result

    def fake_sequence(supplied_series, *, reader):
        captured.append(("sequence", supplied_series, reader))
        return sequence_result

    monkeypatch.setattr(facade_module, "eclipse_receipt_from_event", fake_eclipse)
    monkeypatch.setattr(
        facade_module,
        "jupiter_saturn_sequence_from_series",
        fake_sequence,
    )
    engine = SimpleNamespace(_reader=reader)

    assert (
        PredictiveFacadeMixin.eclipse_receipt_from_event(
            engine,
            event,
            eclipse_id="solar-2026-02-17",
        )
        is eclipse_result
    )
    assert (
        PredictiveFacadeMixin.jupiter_saturn_sequence_from_series(engine, series)
        is sequence_result
    )
    assert captured == [
        ("eclipse", event, "solar-2026-02-17", reader),
        ("sequence", series, reader),
    ]


def test_moira_mundane_methods_are_owned_by_predictive_mixin() -> None:
    for name in (
        "assess_transit_cardinal_ingress",
        "assess_transit_primary_syzygy",
        "eclipse_receipt_from_event",
        "jupiter_saturn_sequence_from_series",
    ):
        method = getattr(PredictiveFacadeMixin, name)
        assert getattr(facade_module.Moira, name) is method
        assert method.__module__ == "moira._facade_predictive"
