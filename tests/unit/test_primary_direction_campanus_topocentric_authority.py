from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

import pytest

import moira.primary_directions.geometry as geometry_module
from moira.constants import Body
from moira.coordinates import equatorial_to_ecliptic
from moira.primary_directions import (
    CONVERSE,
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionMotion,
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionRelationalKind,
    PrimaryDirectionsPreset,
    SpeculumEntry,
    find_primary_arcs,
    primary_directions_policy_preset,
    relate_primary_arc,
)
from moira.primary_directions.geometry import compute_primary_direction_arcs
from moira.primary_directions.latitudes import PrimaryDirectionLatitudeDoctrine
from moira.primary_directions.methods import PrimaryDirectionMethod
from moira.primary_directions.spaces import PrimaryDirectionSpace


_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "primary_directions_campanus_topocentric_authority.json"
)
_FIXTURE = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


@dataclass
class _SourcePlanet:
    longitude: float
    latitude: float = 0.0
    speed: float = 1.0


@dataclass
class _SourceChart:
    planets: dict[str, _SourcePlanet]
    nodes: dict[str, object]
    obliquity: float
    jd_tt: float = 2451545.0
    jd_ut: float = 2451544.9992


@dataclass
class _SourceHouses:
    armc: float
    asc: float = 0.0
    mc: float = 0.0
    dsc: float = 180.0
    ic: float = 180.0
    cusps: tuple[float, ...] = tuple(float(index * 30) for index in range(12))


def _equatorial_source_entry(
    name: str,
    *,
    ra: float,
    dec: float,
    armc: float,
    geo_lat: float,
    lon: float = 0.0,
    lat: float = 0.0,
) -> SpeculumEntry:
    """Reconstruct the minimum speculum fields from printed equatorial facts.

    The fixture deliberately tests each source from its printed RA and
    declination rather than silently substituting a modern natal-chart
    recomputation with different historical input semantics.
    """
    ha = (armc - ra + 180.0) % 360.0 - 180.0
    semi_arc_argument = -math.tan(math.radians(geo_lat)) * math.tan(math.radians(dec))
    dsa = math.degrees(math.acos(semi_arc_argument))
    nsa = 180.0 - dsa
    upper = abs(ha) <= dsa
    if upper:
        mundane_fraction = ha / dsa
    elif ha > 0.0:
        mundane_fraction = 1.0 + (ha - dsa) / nsa
    else:
        mundane_fraction = -1.0 - (-ha - dsa) / nsa
    return SpeculumEntry(
        name=name,
        lon=lon % 360.0,
        lat=lat,
        ra=ra % 360.0,
        dec=dec,
        ha=ha,
        dsa=dsa,
        nsa=nsa,
        upper=upper,
        f=mundane_fraction,
    )


def _signed_circular_arc(arc: float) -> float:
    return (arc + 180.0) % 360.0 - 180.0


def test_authority_fixture_names_scope_provenance_and_rounding_tolerances() -> None:
    assert _FIXTURE["schema_version"] == 1
    assert "wider Campanus mundane-aspect family" in _FIXTURE["evidence_limit"]
    assert "negative-arc converse classification" in _FIXTURE["evidence_limit"]
    assert "traditional role-exchanged converse" in _FIXTURE["evidence_limit"]
    assert "global neo-converse doctrine" in _FIXTURE["evidence_limit"]

    sources = _FIXTURE["sources"]
    assert sources["makransky_primer_part_1"]["isbn"] == "0-9677315-0-X"
    assert sources["polich_topocentric_system"]["evidence_class"] == (
        "origin_text_numeric_example"
    )
    assert sources["makransky_primer_part_2"]["url"].startswith("https://")

    for example in _FIXTURE["examples"].values():
        assert example["source_id"] in sources
        assert example["source_location"]
        assert example["tolerance"]["absolute_deg"] > 0.0
        assert "round" in example["tolerance"]["basis"].lower()


def test_published_campanus_conjunction_attests_shared_narrow_regiomontanus_law() -> None:
    example = _FIXTURE["examples"]["campanus_regiomontanus_mundane_conjunction"]
    inputs = example["inputs_deg"]
    published = example["published_results_deg"]
    tolerance = example["tolerance"]["absolute_deg"]
    sig = _equatorial_source_entry(
        "Mercury",
        ra=inputs["significator_ra"],
        dec=inputs["significator_declination"],
        armc=inputs["armc"],
        geo_lat=inputs["geographic_latitude"],
    )
    prom = _equatorial_source_entry(
        "Sun",
        ra=inputs["promissor_ra"],
        dec=inputs["promissor_declination"],
        armc=inputs["armc"],
        geo_lat=inputs["geographic_latitude"],
    )

    pole = geometry_module._shared_campanus_regio_pole(
        sig, geo_lat=inputs["geographic_latitude"]
    )
    sig_w = geometry_module._under_pole_w(sig, pole, eastern=sig.is_eastern)
    prom_w = geometry_module._under_pole_w(prom, pole, eastern=sig.is_eastern)
    common_kwargs = {
        "space": PrimaryDirectionSpace.IN_MUNDO,
        "latitude_doctrine": PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
        "geo_lat": inputs["geographic_latitude"],
        "armc": inputs["armc"],
        "oa_asc": 0.0,
    }
    campanus = compute_primary_direction_arcs(
        PrimaryDirectionMethod.CAMPANUS, sig, prom, **common_kwargs
    )
    regiomontanus = compute_primary_direction_arcs(
        PrimaryDirectionMethod.REGIOMONTANUS, sig, prom, **common_kwargs
    )

    assert pole == pytest.approx(published["significator_pole"], abs=tolerance)
    assert sig_w == pytest.approx(published["significator_w"], abs=tolerance)
    assert prom_w == pytest.approx(
        published["promissor_w_under_significator_pole"], abs=tolerance
    )
    assert campanus[0] == pytest.approx(published["signed_arc"], abs=tolerance)
    assert campanus == pytest.approx(regiomontanus, abs=1e-12)


def test_polich_origin_example_attests_oblique_ascension_under_named_pole() -> None:
    example = _FIXTURE["examples"]["topocentric_origin_text_oblique_ascension"]
    inputs = example["inputs_deg"]
    published = example["published_results_deg"]
    tolerance = example["tolerance"]["absolute_deg"]
    point = SpeculumEntry.build(
        "Ecliptic degree",
        inputs["ecliptic_longitude"],
        example["semantics"]["ecliptic_latitude_deg"],
        armc=0.0,
        obliquity=inputs["obliquity"],
        geo_lat=inputs["pole"],
    )

    oblique_ascension = geometry_module._under_pole_w(
        point,
        inputs["pole"],
        eastern=True,
    )

    assert oblique_ascension == pytest.approx(
        published["oblique_ascension"], abs=tolerance
    )


def _topocentric_worked_entries() -> tuple[dict[str, object], SpeculumEntry, SpeculumEntry]:
    example = _FIXTURE["examples"]["topocentric_zodiacal_aspect"]
    inputs = example["inputs_deg"]
    sig = _equatorial_source_entry(
        "Saturn",
        ra=inputs["significator_ra"],
        dec=inputs["significator_declination"],
        armc=inputs["armc"],
        geo_lat=inputs["geographic_latitude"],
    )
    prom = _equatorial_source_entry(
        "Moon trine aspect point",
        lon=inputs["promissor_ecliptic_longitude"],
        lat=inputs["promissor_ecliptic_latitude"],
        ra=inputs["promissor_ra"],
        dec=inputs["promissor_declination"],
        armc=inputs["armc"],
        geo_lat=inputs["geographic_latitude"],
    )
    return example, sig, prom


def test_published_topocentric_example_attests_pole_and_under_pole_arc_law() -> None:
    example, sig, prom = _topocentric_worked_entries()
    inputs = example["inputs_deg"]
    published = example["published_results_deg"]
    tolerance = example["tolerance"]["absolute_deg"]

    pole = geometry_module._topocentric_pole(sig, geo_lat=inputs["geographic_latitude"])
    sig_w = geometry_module._under_pole_w(sig, pole, eastern=sig.is_eastern)
    prom_w = geometry_module._under_pole_w(prom, pole, eastern=sig.is_eastern)
    direct, _ = compute_primary_direction_arcs(
        PrimaryDirectionMethod.TOPOCENTRIC,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_ZODIACO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED,
        geo_lat=inputs["geographic_latitude"],
        armc=inputs["armc"],
        oa_asc=0.0,
    )

    assert pole == pytest.approx(published["significator_pole"], abs=tolerance)
    assert sig_w == pytest.approx(published["significator_w"], abs=tolerance)
    assert prom_w == pytest.approx(
        published["promissor_w_under_significator_pole"], abs=tolerance
    )
    assert _signed_circular_arc(direct) == pytest.approx(
        published["signed_arc"], abs=tolerance
    )


def test_traditional_topocentric_converse_remains_role_exchange_for_compatibility() -> None:
    """The additive signed doctrine must not rewrite the established product."""
    example, sig, prom = _topocentric_worked_entries()
    inputs = example["inputs_deg"]
    published = example["published_results_deg"]
    tolerance = example["tolerance"]["absolute_deg"]

    direct, converse = compute_primary_direction_arcs(
        PrimaryDirectionMethod.TOPOCENTRIC,
        sig,
        prom,
        space=PrimaryDirectionSpace.IN_ZODIACO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED,
        geo_lat=inputs["geographic_latitude"],
        armc=inputs["armc"],
        oa_asc=0.0,
    )

    assert example["semantics"]["motion"] == "converse"
    assert _signed_circular_arc(direct) == pytest.approx(
        published["signed_arc"], abs=tolerance
    )
    assert direct > 180.0
    assert converse != pytest.approx(published["arc_magnitude"], abs=tolerance)


def test_published_topocentric_converse_is_public_under_signed_motion_preset() -> None:
    example = _FIXTURE["examples"]["topocentric_zodiacal_aspect"]
    inputs = example["inputs_deg"]
    published = example["published_results_deg"]
    tolerance = example["tolerance"]["absolute_deg"]
    obliquity = _FIXTURE["examples"][
        "topocentric_origin_text_oblique_ascension"
    ]["inputs_deg"]["obliquity"]
    saturn_longitude, saturn_latitude = equatorial_to_ecliptic(
        inputs["significator_ra"],
        inputs["significator_declination"],
        obliquity,
    )
    # The source publishes the zero-latitude trine point.  Reconstruct its
    # source Moon 120 degrees earlier and deliberately give that source a
    # non-zero native latitude so the preset's assigned-zero doctrine is part
    # of the public witness rather than an accidental fixture property.
    moon_longitude = (inputs["promissor_ecliptic_longitude"] - 120.0) % 360.0
    chart = _SourceChart(
        planets={
            Body.SUN: _SourcePlanet(0.0, speed=0.9856),
            Body.SATURN: _SourcePlanet(saturn_longitude, saturn_latitude),
            Body.MOON: _SourcePlanet(moon_longitude, latitude=5.0, speed=13.0),
        },
        nodes={},
        obliquity=obliquity,
    )
    houses = _SourceHouses(armc=inputs["armc"])
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION
    )

    arcs = find_primary_arcs(
        chart,
        houses,
        inputs["geographic_latitude"],
        max_arc=10.0,
        significators=["Saturn"],
        promissors=["Moon Trine"],
        policy=policy,
    )

    assert len(arcs) == 1
    arc = arcs[0]
    assert arc.direction == CONVERSE
    assert arc.motion is PrimaryDirectionMotion.CONVERSE
    assert arc.relational_kind is PrimaryDirectionRelationalKind.ZODIACAL_ASPECT
    assert arc.arc == pytest.approx(published["arc_magnitude"], abs=tolerance)
    relation = relate_primary_arc(arc, policy=policy)
    assert (
        relation.converse_doctrine
        is PrimaryDirectionConverseDoctrine.SIGNED_PRIMARY_MOTION
    )
    assert (
        relation.perfection_kind
        is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
    )
