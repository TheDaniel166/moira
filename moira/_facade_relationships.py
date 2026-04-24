"""
Internal relationship-chart mixin for the public Moira facade.

The methods here are compatibility wrappers. Synastry, composite, and Davison
truth remains owned by ``moira.synastry``.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

from .constants import HouseSystem


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class RelationshipFacadeMixin:
    """RITE: The Chart-Weaver — the layer that routes the public Moira surface
    to relationship chart techniques: synastry aspect overlays, composite
    midpoint charts, and Davison time-space charts.

THEOREM: Mixin that provides relationship-chart method wrappers for the
         public ``moira.facade.Moira`` class, delegating each technique
         to ``moira.synastry`` and related modules.

RITE OF PURPOSE:
    RelationshipFacadeMixin extracts all relationship-chart-facing public
    methods from the monolithic facade.py into a composable unit,
    preserving the legacy Moira surface while routing to the authoritative
    synastry engine without duplicating logic.

LAW OF OPERATION:
    Responsibilities:
        - Delegate synastry aspects, composite chart, and Davison
          computation to ``moira.synastry``.
    Non-responsibilities:
        - Does not implement any synastry or composite math itself.
        - Does not own kernel lifecycle or reader management.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
        - moira.constants.HouseSystem
    Structural invariants:
        - All methods delegate to facade-module callables.

Canon: Moira Sovereign Facade Architecture; moira.synastry relationship
       chart engine.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_relationships.RelationshipFacadeMixin",
    "risk": "medium",
    "api": {"frozen": ["synastry_aspects", "composite", "davison"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def synastry_aspects(
        self,
        chart_a,
        chart_b,
        tier: int = 2,
        orbs: dict[float, float] | None = None,
        orb_factor: float = 1.0,
        include_nodes: bool = True,
    ):
        """Find inter-aspects between two natal charts."""
        return _facade_module().synastry_aspects(
            chart_a,
            chart_b,
            tier=tier,
            orbs=orbs,
            orb_factor=orb_factor,
            include_nodes=include_nodes,
        )

    def house_overlay(
        self,
        chart_source,
        target_houses,
        include_nodes: bool = True,
        source_label: str = "A",
        target_label: str = "B",
    ):
        """Place one chart's points into another chart's houses."""
        return _facade_module().house_overlay(
            chart_source,
            target_houses,
            include_nodes=include_nodes,
            source_label=source_label,
            target_label=target_label,
        )

    def mutual_house_overlays(
        self,
        chart_a,
        houses_a,
        chart_b,
        houses_b,
        include_nodes: bool = True,
    ):
        """Compute house overlays in both synastry directions."""
        return _facade_module().mutual_house_overlays(
            chart_a,
            houses_a,
            chart_b,
            houses_b,
            include_nodes=include_nodes,
        )

    def composite_chart(
        self,
        chart_a,
        chart_b,
        houses_a=None,
        houses_b=None,
    ):
        """Build a Composite chart from corresponding position midpoints."""
        return _facade_module().composite_chart(chart_a, chart_b, houses_a, houses_b)

    def composite_chart_reference_place(
        self,
        chart_a,
        chart_b,
        houses_a,
        houses_b,
        reference_latitude: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy=None,
    ):
        """Build a composite chart using the reference-place house method."""
        return _facade_module().composite_chart_reference_place(
            chart_a,
            chart_b,
            houses_a,
            houses_b,
            reference_latitude,
            house_system=house_system,
            policy=policy,
        )

    def davison_chart(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy=None,
    ):
        """Calculate a Davison Relationship Chart."""
        return _facade_module().davison_chart(
            dt_a,
            lat_a,
            lon_a,
            dt_b,
            lat_b,
            lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_uncorrected(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy=None,
    ):
        """Davison chart using arithmetic midpoint time and location."""
        return _facade_module().davison_chart_uncorrected(
            dt_a,
            lat_a,
            lon_a,
            dt_b,
            lat_b,
            lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_reference_place(
        self,
        dt_a: datetime,
        dt_b: datetime,
        reference_latitude: float,
        reference_longitude: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy=None,
    ):
        """Davison chart using midpoint time and an explicit reference place."""
        return _facade_module().davison_chart_reference_place(
            dt_a,
            dt_b,
            reference_latitude,
            reference_longitude,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_spherical_midpoint(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy=None,
    ):
        """Davison chart using midpoint time and spherical geographic midpoint."""
        return _facade_module().davison_chart_spherical_midpoint(
            dt_a,
            lat_a,
            lon_a,
            dt_b,
            lat_b,
            lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_corrected(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy=None,
    ):
        """Davison chart with midpoint location and corrected midpoint time."""
        return _facade_module().davison_chart_corrected(
            dt_a,
            lat_a,
            lon_a,
            dt_b,
            lat_b,
            lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )
