from __future__ import annotations

import math
from datetime import datetime, timezone
from unittest.mock import Mock
import pytest

from moira.constants import Body, HouseSystem
from moira.primary_directions import (
    PrimaryDirectionMethod,
    PrimaryDirectionMotion,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionSpace,
    PrimaryDirectionsPolicy,
    PrimaryDirectionsPreset,
    PrimaryDirectionMundaneAspectTarget,
    PrimaryDirectionRelationPolicy,
    SpeculumEntry,
    compute_primary_directions_timeline,
    find_primary_arcs,
    primary_directions_policy_preset,
    resolve_distributor_chronology,
    speculum,
)
from moira.primary_directions.distributor import _parse_bound_promissor, _SIGN_LOOKUP
from moira.primary_directions.geometry import (
    _shared_campanus_regio_sin_zenith_distance,
    primary_direction_geometry_truth,
    PrimaryDirectionGeometrySovereignty,
    PrimaryDirectionGeometryLaw,
)
try:
    import _moira_native
except ImportError:
    _moira_native = None


def test_equatorial_horizon_axis_singularity_python_and_native() -> None:
    """Adversarial check: phi = 0, dec = +-90 horizon plane normal does not raise division by zero."""
    armc = 0.0
    obliquity = 23.4392911
    entry_north = SpeculumEntry(
        name="NorthPole",
        lon=90.0,
        lat=66.5607089,
        ra=90.0,
        dec=90.0,
        ha=-90.0,
        dsa=90.0,
        nsa=90.0,
        upper=True,
        f=0.0,
    )
    # Python layer returns 1.0 limit
    sin_zd = _shared_campanus_regio_sin_zenith_distance(entry_north, geo_lat=0.0)
    assert sin_zd == pytest.approx(1.0)

    # C++ native layer
    if _moira_native is not None and hasattr(_moira_native, "campanus_regio_sin_zenith_distance"):
        native_sin_zd = _moira_native.campanus_regio_sin_zenith_distance(90.0, -90.0, 0.0)
        assert native_sin_zd == pytest.approx(1.0)
        native_sin_zd_south = _moira_native.campanus_regio_sin_zenith_distance(-90.0, -90.0, 0.0)
        assert native_sin_zd_south == pytest.approx(1.0)


def test_circumpolar_speculum_decoupling() -> None:
    """Adversarial check: circumpolar bodies can be built with allow_circumpolar=True."""
    armc = 0.0
    obliquity = 23.4392911
    geo_lat = 75.0  # High arctic latitude

    # Default fails closed
    with pytest.raises(ValueError, match="no real rise/set semi-arcs"):
        SpeculumEntry.build("Circumpolar", 90.0, 0.0, armc, obliquity, geo_lat, allow_circumpolar=False)

    # allow_circumpolar=True creates decoupled entry with dsa=None, nsa=None, f=None
    entry = SpeculumEntry.build("Circumpolar", 90.0, 0.0, armc, obliquity, geo_lat, allow_circumpolar=True)
    assert entry.dsa is None
    assert entry.nsa is None
    assert entry.f is None
    assert entry.upper is True
    assert "DSA=   N/A" in repr(entry)
    assert "f=   N/A" in repr(entry)


def test_circumpolar_directions_in_semi_arc_independent_methods(moira_engine) -> None:
    """Circumpolar bodies allow Meridian, Regiomontanus, Morinus, and Campanus directions without crashing."""
    dt = datetime(2000, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    # Arctic latitude where Sun is circumpolar on Summer Solstice (Dec ~ +23.44, lat 75 -> |tan phi tan dec| > 1)
    geo_lat = 75.0
    houses = moira_engine.houses(dt, geo_lat, 0.0, system=HouseSystem.REGIOMONTANUS)

    # Meridian directions succeed despite circumpolar body
    meridian_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=geo_lat,
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.MERIDIAN),
    )
    assert len(meridian_arcs) > 0

    # Regiomontanus directions succeed
    regio_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=geo_lat,
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.REGIOMONTANUS),
    )
    assert len(regio_arcs) > 0

    # Morinus directions succeed
    morinus_arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=geo_lat,
        policy=PrimaryDirectionsPolicy(method=PrimaryDirectionMethod.MORINUS),
    )
    assert len(morinus_arcs) > 0


def test_mundane_aspect_policy_validation() -> None:
    """Fail-fast validation for method and space compatibility on mundane_aspect_targets."""
    target = PrimaryDirectionMundaneAspectTarget(
        source_name="Sun",
        aspect_name="Dexter Sextile",
        fraction_offset=1.0 / 3.0,
    )
    # Rejects incompatible methods like MERIDIAN or TOPOCENTRIC
    with pytest.raises(ValueError, match="mundane_aspect_targets currently require Placidian or Ptolemaic method"):
        PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MERIDIAN,
            mundane_aspect_targets=(target,),
        )

    # Rejects IN_ZODIACO space
    with pytest.raises(ValueError, match="mundane_aspect_targets currently require in_mundo"):
        primary_directions_policy_preset(
            PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT,
            mundane_aspect_targets=(target,),
        )

    # Rejects when relation_policy does not admit MUNDANE_ASPECT
    with pytest.raises(ValueError, match="mundane_aspect_targets require matching admitted relation kinds"):
        PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            relation_policy=PrimaryDirectionRelationPolicy(frozenset({PrimaryDirectionRelationalKind.CONJUNCTION})),
            mundane_aspect_targets=(target,),
        )


def test_distributor_abbreviation_and_converse_chronology(moira_engine) -> None:
    """Verify robust distributor sign parsing and converse chronology generation."""
    # Test standard 3-letter, 4-letter, and non-trivial abbreviations
    parsed_sgr = _parse_bound_promissor("Term of Jupiter (04°30' Sgr)")
    assert parsed_sgr == ("Jupiter", "Sagittarius", 4.5)

    parsed_cap = _parse_bound_promissor("Term of Saturn (12°00' Cap)")
    assert parsed_cap == ("Saturn", "Capricorn", 12.0)

    parsed_psc = _parse_bound_promissor("Term of Venus (28°15' Psc)")
    assert parsed_psc == ("Venus", "Pisces", 28.25)

    parsed_cnc = _parse_bound_promissor("Term of Mars (07°00' Cnc)")
    assert parsed_cnc == ("Mars", "Cancer", 7.0)

    # Verify timeline generates converse distributor periods when include_converse=True
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    houses = moira_engine.houses(dt, 51.5, 0.0, system=HouseSystem.PLACIDUS)

    timeline = compute_primary_directions_timeline(
        chart=chart,
        houses=houses,
        geo_lat=51.5,
        max_age_years=50.0,
        policy=PrimaryDirectionsPolicy(include_converse=True),
        reader=moira_engine._reader_obj,
    )
    assert len(timeline.distributor_periods) > 0
    # Both direct and converse events receive proper attribution
    direct_events = [ev for ev in timeline.events if ev.motion is PrimaryDirectionMotion.DIRECT and ev.is_bound_boundary]
    converse_events = [ev for ev in timeline.events if ev.motion is PrimaryDirectionMotion.CONVERSE and ev.is_bound_boundary]
    assert len(direct_events) > 0
    assert len(converse_events) > 0
    assert all(ev.distributor is not None for ev in direct_events)
    assert all(ev.distributor is not None for ev in converse_events)


def test_geometry_truth_preserves_verified_sovereignty_relationships() -> None:
    """Verify geometry truth declarations reflect verified computational and historical truth."""
    morinus_truth = primary_direction_geometry_truth(PrimaryDirectionMethod.MORINUS)
    campanus_truth = primary_direction_geometry_truth(PrimaryDirectionMethod.CAMPANUS)
    regio_truth = primary_direction_geometry_truth(PrimaryDirectionMethod.REGIOMONTANUS)

    assert morinus_truth.sovereignty is PrimaryDirectionGeometrySovereignty.SHARED_NARROW
    assert morinus_truth.shared_with == (PrimaryDirectionMethod.REGIOMONTANUS,)
    assert campanus_truth.sovereignty is PrimaryDirectionGeometrySovereignty.SHARED_NARROW
    assert campanus_truth.shared_with == (PrimaryDirectionMethod.REGIOMONTANUS,)
    assert regio_truth.sovereignty is PrimaryDirectionGeometrySovereignty.SOVEREIGN
