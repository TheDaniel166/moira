"""Circumambulations, transmissions, and fail-closed offices."""

from __future__ import annotations

import inspect

import pytest

from moira.circumambulations import (
    CircumambulationStatus,
    CircumambulationTimeKey,
    circumambulate,
)
from moira.egyptian_bounds import egyptian_bound_of
from moira.hellenistic_offices import (
    OFFICE_NOT_ADMITTED_REASON,
    HellenisticOfficeStatus,
    hunt_hellenistic_offices,
)
from moira.valens_transmissions import (
    TransmissionKind,
    TransmissionStatus,
    valens_transmission_graph,
)


def test_circumambulation_walks_egyptian_bounds_and_prorates_first_bound() -> None:
    result = circumambulate(
        10.0,
        2451545.0,
        significator_name="Ascendant",
    )
    first = egyptian_bound_of(10.0)
    assert result.status is CircumambulationStatus.EVALUATED
    assert result.time_key is CircumambulationTimeKey.BOUND_LORD_MINOR_YEARS
    assert result.periods[0].lord == first.ruler
    assert result.periods[0].span_deg == pytest.approx(2.0)
    assert result.periods[0].years == pytest.approx(8 * (2.0 / 6.0))
    assert sum(period.span_deg for period in result.periods) == pytest.approx(360.0)
    assert result.periods[-1].end_longitude == pytest.approx(10.0)


def test_circumambulation_fails_closed_on_unadmitted_time_keys() -> None:
    rising = circumambulate(
        10.0,
        2451545.0,
        significator_name="Moon",
        time_key=CircumambulationTimeKey.RISING_TIMES,
    )
    equatorial = circumambulate(
        10.0,
        2451545.0,
        significator_name="Moon",
        time_key=CircumambulationTimeKey.EQUATORIAL,
    )
    assert rising.status is CircumambulationStatus.NOT_EVALUABLE
    assert rising.reason == "rising_time_table_not_admitted"
    assert rising.periods == ()
    assert equatorial.reason == "equatorial_key_is_primary_direction"


def test_transmission_graph_has_no_effect_fields() -> None:
    graph = valens_transmission_graph(
        positions={"Sun": 10.0, "Moon": 45.0},
        lots={"Fortune": 50.0},
        asc_longitude=15.0,
        profection_lord="Mars",
        profection_monthly_lords=("Mars",) * 12,
        decennial_l1="Sun",
        decennial_l2="Moon",
        zr_l1_sign="Aries",
        zr_l2_sign="Taurus",
    )
    assert graph.status is TransmissionStatus.EVALUATED
    kinds = {edge.kind for edge in graph.edges}
    assert TransmissionKind.PROFECTED_YEAR_TO_MONTH in kinds
    assert TransmissionKind.DECENNIAL_L1_TO_L2 in kinds
    assert TransmissionKind.ZR_L1_TO_L2 in kinds
    assert TransmissionKind.NATAL_POINT_TO_PLACE in kinds
    assert not hasattr(graph, "effects")
    for edge in graph.edges:
        assert not hasattr(edge, "effect")
        assert not hasattr(edge, "prose")


def test_offices_preserve_candidates_and_never_select() -> None:
    hunt = hunt_hellenistic_offices(
        positions={
            "Sun": 10.0,
            "Moon": 100.0,
            "Mercury": 20.0,
            "Venus": 40.0,
            "Mars": 80.0,
            "Jupiter": 200.0,
            "Saturn": 300.0,
        },
        is_day_chart=True,
        asc_longitude=15.0,
        lots={"Fortune": 50.0},
    )
    assert hunt.status is HellenisticOfficeStatus.NOT_EVALUABLE
    assert hunt.predominator is None
    assert hunt.house_master is None
    assert hunt.reason == OFFICE_NOT_ADMITTED_REASON
    names = {item.name for item in hunt.candidates}
    assert {"Sun", "Moon", "Fortune", "Ascendant"} <= names
    sun = next(item for item in hunt.candidates if item.name == "Sun")
    assert sun.is_sect_light is True
    assert sun.is_angular is True
    import moira.hellenistic_offices as offices

    source = inspect.getsource(offices)
    assert "import" not in source or "longevity" not in {
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    }
    assert "find_hyleg" not in source
    assert "from .longevity" not in source
    assert "calculate_longevity" not in source
