"""
Tests for moira/draconic.py.

The draconic frame is pure longitude rotation. These tests use synthetic
positions and chart-shaped objects; no ephemeris kernel is required.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.draconic as _draconic
import moira.facade as facade
from moira.constants import Body
from moira.coordinates import angular_distance
from moira.draconic import (
    DRACONIC_NODE_MODES,
    DraconicAnchor,
    DraconicChart,
    DraconicPosition,
    draconic_chart,
    draconic_chart_from_positions,
    draconic_longitude,
    draconic_positions,
)


_POSITIONS = {
    "Sun": 10.0,
    "Moon": 82.0,
    "Mars": 244.0,
}


class _FakeChart:
    jd_ut = 2451545.0
    nodes = {
        Body.TRUE_NODE: SimpleNamespace(longitude=120.0),
        Body.MEAN_NODE: SimpleNamespace(longitude=118.0),
    }

    def longitudes(self, include_nodes: bool = True) -> dict[str, float]:
        positions = {"Sun": 150.0, "Moon": 300.0}
        if include_nodes:
            positions.update({
                Body.TRUE_NODE: self.nodes[Body.TRUE_NODE].longitude,
                Body.MEAN_NODE: self.nodes[Body.MEAN_NODE].longitude,
            })
        return positions


def test_module_all_is_exact() -> None:
    assert set(_draconic.__all__) == {
        "DraconicNodeMode",
        "DRACONIC_NODE_MODES",
        "DraconicAnchor",
        "DraconicPosition",
        "DraconicChart",
        "draconic_longitude",
        "draconic_positions",
        "draconic_chart_from_positions",
        "draconic_chart",
    }


def test_facade_reexports_draconic_surface() -> None:
    for name in _draconic.__all__:
        assert hasattr(facade, name)
        assert name in facade.__all__


def test_node_modes_are_only_mean_and_true() -> None:
    assert DRACONIC_NODE_MODES == ("mean", "true")


def test_draconic_longitude_subtracts_anchor_and_wraps() -> None:
    assert draconic_longitude(10.0, 123.0) == pytest.approx(247.0)
    assert draconic_longitude(361.0, 1.0) == pytest.approx(0.0)
    assert 0.0 <= draconic_longitude(-1e-15, 0.0) < 360.0


def test_anchor_maps_to_zero_aries() -> None:
    assert draconic_longitude(123.456, 123.456) == pytest.approx(0.0)


def test_draconic_positions_preserve_pairwise_separations() -> None:
    transformed = draconic_positions(_POSITIONS, anchor_longitude=123.0)
    by_body = {position.body: position for position in transformed}

    for left in _POSITIONS:
        for right in _POSITIONS:
            source_sep = angular_distance(_POSITIONS[left], _POSITIONS[right])
            draconic_sep = angular_distance(
                by_body[left].draconic_longitude,
                by_body[right].draconic_longitude,
            )
            assert draconic_sep == pytest.approx(source_sep)


def test_draconic_longitude_dual_path_equivalence() -> None:
    """Rotating a raw longitude equals rotating its reduced form exactly."""

    for lon in (-720.25, 36000.3, 1_000_000.3, 1_000_000_000.3):
        assert draconic_longitude(lon, 123.456) == draconic_longitude(lon % 360.0, 123.456)


def test_draconic_positions_admit_multi_revolution_longitudes() -> None:
    """Regression: unwrapped multi-revolution longitudes formerly tripped the
    vessel's rotation-consistency gate once |longitude| exceeded ~9000 deg."""

    for lon in (36000.3, -36000.3, 1_000_000.3, 1_000_000_000.3):
        transformed = draconic_positions({"X": lon}, anchor_longitude=123.456)
        position = transformed[0]
        assert position.source_longitude == pytest.approx(lon % 360.0)
        assert position.draconic_longitude == pytest.approx(
            draconic_longitude(lon % 360.0, 123.456)
        )


def test_draconic_anchor_normalizes_and_records_policy() -> None:
    anchor = DraconicAnchor(node_mode="TRUE", longitude=480.0)
    assert anchor.node_mode == "true"
    assert anchor.node_name == Body.TRUE_NODE
    assert anchor.longitude == pytest.approx(120.0)
    assert anchor.rotation_degrees == pytest.approx(240.0)
    assert anchor.source == "moira.true_node"


def test_draconic_anchor_rejects_node_name_policy_mismatch() -> None:
    with pytest.raises(ValueError, match="does not match"):
        DraconicAnchor(node_mode="true", longitude=120.0, node_name=Body.MEAN_NODE)


def test_draconic_position_derives_sign_fields() -> None:
    position = DraconicPosition(
        body="True Node",
        source_longitude=120.0,
        draconic_longitude=0.0,
        anchor_longitude=120.0,
    )

    assert position.sign == "Aries"
    assert position.sign_degree == pytest.approx(0.0)


def test_draconic_position_rejects_non_rotation_value() -> None:
    with pytest.raises(ValueError, match="does not match"):
        DraconicPosition(
            body="Sun",
            source_longitude=150.0,
            draconic_longitude=42.0,
            anchor_longitude=120.0,
        )


def test_draconic_chart_from_positions_materializes_first_class_vessel() -> None:
    anchor = DraconicAnchor(node_mode="mean", longitude=118.0)
    chart = draconic_chart_from_positions(
        {
            Body.MEAN_NODE: 118.0,
            "Sun": 150.0,
        },
        anchor=anchor,
        jd_ut=2451545.0,
    )

    assert isinstance(chart, DraconicChart)
    assert chart.anchor is anchor
    assert chart.jd_ut == pytest.approx(2451545.0)
    assert chart.longitudes()[Body.MEAN_NODE] == pytest.approx(0.0)
    assert chart.longitudes()["Sun"] == pytest.approx(32.0)
    assert chart.source_longitudes()["Sun"] == pytest.approx(150.0)
    assert chart.anchor_residual == pytest.approx(0.0)


def test_draconic_chart_uses_true_node_policy_from_chart() -> None:
    chart = draconic_chart(_FakeChart(), node_mode="true", include_nodes=True)

    assert chart.anchor.node_mode == "true"
    assert chart.anchor.longitude == pytest.approx(120.0)
    assert chart.longitudes()[Body.TRUE_NODE] == pytest.approx(0.0)
    assert chart.longitudes()[Body.MEAN_NODE] == pytest.approx(358.0)
    assert chart.longitudes()["Sun"] == pytest.approx(30.0)
    assert chart.anchor_residual == pytest.approx(0.0)


def test_draconic_chart_uses_mean_node_policy_from_chart() -> None:
    chart = draconic_chart(_FakeChart(), node_mode="mean", include_nodes=True)

    assert chart.anchor.node_mode == "mean"
    assert chart.anchor.longitude == pytest.approx(118.0)
    assert chart.longitudes()[Body.MEAN_NODE] == pytest.approx(0.0)
    assert chart.longitudes()[Body.TRUE_NODE] == pytest.approx(2.0)


def test_draconic_chart_can_exclude_nodes_from_output_but_still_uses_anchor() -> None:
    chart = draconic_chart(_FakeChart(), node_mode="true", include_nodes=False)

    assert set(chart.longitudes()) == {"Sun", "Moon"}
    assert chart.anchor_residual is None
    assert chart.longitudes()["Sun"] == pytest.approx(30.0)


def test_draconic_chart_requires_explicit_node_mode() -> None:
    with pytest.raises(TypeError):
        draconic_chart(_FakeChart())  # type: ignore[call-arg]


def test_draconic_chart_rejects_missing_anchor_node() -> None:
    chart = _FakeChart()
    chart.nodes = {Body.MEAN_NODE: SimpleNamespace(longitude=118.0)}

    with pytest.raises(ValueError, match="True Node"):
        draconic_chart(chart, node_mode="true")


def test_draconic_chart_does_not_promote_to_package_root_all() -> None:
    import moira

    for name in _draconic.__all__:
        assert name not in moira.__all__
