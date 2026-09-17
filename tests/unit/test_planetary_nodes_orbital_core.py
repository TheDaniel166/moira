"""Stage 3 contracts for the geometric-node orbital-core adapter."""

from __future__ import annotations

from dataclasses import fields
import inspect
from types import SimpleNamespace

import pytest

from moira._orbital_errors import (
    OrbitalFrameUnavailableError,
    OrbitalInputError,
    OrbitalStateDegenerateError,
)
from moira.orbits import OrbitalCenter, OrbitalFrame
from moira import planetary_nodes
from moira.planetary_nodes import OrbitalNode, geometric_node


def _elements(**overrides) -> SimpleNamespace:
    values = {
        "body": SimpleNamespace(name="1 Ceres"),
        "epoch_tdb": 2460110.5008,
        "lon_ascending_node_deg": 80.25,
        "lon_pericenter_deg": 222.0,
        "pericenter_ecliptic_lon_deg": 120.5,
        "inclination_deg": 10.5,
        "eccentricity": 0.08,
        "semi_major_axis_au": 2.77,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_orbital_node_vessel_is_unchanged() -> None:
    assert [field.name for field in fields(OrbitalNode)] == [
        "planet",
        "ascending_node",
        "perihelion",
        "aphelion",
        "inclination",
        "eccentricity",
        "semi_major_axis",
    ]


def test_geometric_node_delegates_once_with_explicit_sun_true_date_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, float, object, object, object]] = []
    reader = object()

    def fake_osculating_elements(body, jd_ut, *, center, frame, reader):
        calls.append((body, jd_ut, center, frame, reader))
        return _elements()

    monkeypatch.setattr(
        planetary_nodes,
        "osculating_elements",
        fake_osculating_elements,
    )

    result = geometric_node(2000001, 2460110.5, reader)

    assert calls == [
        (
            2000001,
            2460110.5,
            OrbitalCenter.SUN,
            OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
            reader,
        )
    ]
    assert result == OrbitalNode(
        planet="1 Ceres",
        ascending_node=80.25,
        perihelion=120.5,
        aphelion=300.5,
        inclination=10.5,
        eccentricity=0.08,
        semi_major_axis=2.77,
    )
    assert result.perihelion != 222.0


@pytest.mark.parametrize(
    "field",
    (
        "lon_ascending_node_deg",
        "pericenter_ecliptic_lon_deg",
        "semi_major_axis_au",
    ),
)
def test_geometric_node_fails_closed_when_legacy_vessel_field_is_undefined(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    monkeypatch.setattr(
        planetary_nodes,
        "osculating_elements",
        lambda *args, **kwargs: _elements(**{field: None}),
    )

    with pytest.raises(OrbitalStateDegenerateError) as caught:
        geometric_node("Ceres", 2460110.5, object())

    assert caught.value.condition == f"ORBITAL_NODE_FIELDS_UNDEFINED:{field}"
    assert caught.value.body == "1 Ceres"
    assert caught.value.epoch_tdb == 2460110.5008


def test_geometric_node_preserves_strict_frame_failure_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = OrbitalFrameUnavailableError(
        OrbitalFrame.TRUE_ECLIPTIC_OF_DATE.value,
        2500000.0,
        ((2415020.0, 2488070.0),),
    )

    def unavailable(*args, **kwargs):
        raise expected

    monkeypatch.setattr(planetary_nodes, "osculating_elements", unavailable)

    with pytest.raises(OrbitalFrameUnavailableError) as caught:
        geometric_node("Mars", 2500000.0, object())

    assert caught.value is expected


@pytest.mark.parametrize(
    ("body", "jd_ut", "parameter"),
    (
        (True, 2460110.5, "body"),
        ("Mars", True, "jd_ut"),
    ),
)
def test_geometric_node_rejects_boolean_identifiers_and_epochs(
    body,
    jd_ut,
    parameter,
) -> None:
    with pytest.raises(OrbitalInputError) as caught:
        geometric_node(body, jd_ut, object())

    assert caught.value.parameter == parameter


def test_geometric_node_contains_no_duplicate_state_frame_or_conic_pipeline() -> None:
    source = inspect.getsource(planetary_nodes)
    forbidden = (
        "_barycentric_state",
        "precession_matrix_equatorial",
        "nutation_matrix_equatorial",
        "_GM_SUN",
        "Specific angular momentum h = r",
    )
    assert all(token not in source for token in forbidden)
