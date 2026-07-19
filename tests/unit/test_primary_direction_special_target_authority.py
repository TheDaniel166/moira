from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.julian import julian_day, ut_to_tt
from moira.primary_directions import (
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionMethod,
    PrimaryDirectionSpace,
    SpeculumEntry,
)
from moira.primary_directions.antiscia import (
    PrimaryDirectionAntisciaKind,
    project_primary_direction_antiscia_longitude,
)
from moira.primary_directions.fixed_stars import (
    PrimaryDirectionFixedStarTarget,
    resolve_primary_direction_fixed_star_point,
)
from moira.primary_directions.geometry import compute_primary_direction_arcs
from moira.primary_directions.morinus import project_morinus_aspect_point
from moira.primary_directions.placidus import (
    compute_placidian_converse_rapt_parallel_arc,
    compute_placidian_rapt_parallel_arc,
)
from moira.primary_directions.ptolemy import (
    PtolemaicParallelRelation,
    project_ptolemaic_declination_point,
)


_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "primary_directions_special_target_authority.json"
)
_CORPUS = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str) -> dict[str, object]:
    return next(case for case in _CORPUS["cases"] if case["case_id"] == case_id)


def _zodiacal_arc_to_ascendant(
    *,
    promissor_name: str,
    promissor_longitude: float,
    ascendant_longitude: float,
    armc: float,
    obliquity: float,
    geo_latitude: float,
) -> float:
    significator = SpeculumEntry.build(
        "ASC",
        ascendant_longitude,
        0.0,
        armc,
        obliquity,
        geo_latitude,
    )
    promissor = SpeculumEntry.build(
        promissor_name,
        promissor_longitude,
        0.0,
        armc,
        obliquity,
        geo_latitude,
    )
    direct, _converse = compute_primary_direction_arcs(
        PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
        significator,
        promissor,
        space=PrimaryDirectionSpace.IN_ZODIACO,
        latitude_doctrine=PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED,
        geo_lat=geo_latitude,
        armc=armc,
        oa_asc=(armc + 90.0) % 360.0,
    )
    return direct % 360.0


def _rapt_entry(payload: dict[str, object]) -> SpeculumEntry:
    # lon, lat, dec, and f are outside the narrow rapt helper's input surface.
    # The source-owned RA, hour angle, semi-arcs, and hemisphere remain intact.
    return SpeculumEntry(
        name=str(payload["name"]),
        lon=0.0,
        lat=0.0,
        ra=float(payload["ra_degrees"]),
        dec=0.0,
        ha=float(payload["hour_angle_degrees"]),
        dsa=float(payload["dsa_degrees"]),
        nsa=float(payload["nsa_degrees"]),
        upper=bool(payload["upper"]),
        f=0.0,
    )


def test_special_target_authority_corpus_has_explicit_evidence_and_deferrals() -> None:
    assert _CORPUS["schema_version"] == 1
    assert _CORPUS["corpus_id"] == "primary_directions_special_target_authority"

    sources = _CORPUS["sources"]
    admitted_source_classes = {
        "authority_validation",
        "cross_engine_corroboration",
        "secondary_source_corroboration",
    }
    for source in sources.values():
        assert source["url"].startswith("https://")
        assert source["pages"]
        assert source["authority_scope"]
        assert source["license_provenance"]
        assert source["evidence_class"] in admitted_source_classes

    cases = _CORPUS["cases"]
    case_ids = [case["case_id"] for case in cases]
    assert len(case_ids) == len(set(case_ids))
    assert {case["branch"] for case in cases} == {
        "fixed_star",
        "antiscia",
        "ptolemaic_parallel",
        "placidian_rapt_parallel",
        "morinus_aspect_context",
    }
    for case in cases:
        assert case["status"] == "evaluable"
        assert case["evaluator"]
        assert case["product_semantics"]
        assert case["expected"]
        assert case["tolerance"]
        assert case["effective_evidence_class"] in admitted_source_classes
        for layer in case["evidence_layers"]:
            assert layer["source_id"] in sources
            assert layer["role"]

    deferred = _CORPUS["deferred_branches"]
    deferred_ids = [branch["branch_id"] for branch in deferred]
    assert len(deferred_ids) == len(set(deferred_ids))
    assert {
        "fixed_star_true_latitude_in_mundo",
        "fixed_star_to_planet",
        "antiscia_node_and_angle_sources",
        "antiscia_cum_latitudine",
        "ptolemaic_contra_parallel",
        "placidian_rapt_parallel_primary_source",
        "morinus_primary_source_aspect_context",
        "morinus_quadrant_continuation",
    } <= set(deferred_ids)
    for branch in deferred:
        assert branch["status"] == "not_evaluable"
        assert branch["reason"]
        assert branch["required_evidence"]
        assert "evaluator" not in branch
        assert "expected" not in branch
        assert "tolerance" not in branch
        assert all(source_id in sources for source_id in branch["source_ids"])


def test_lilly_vega_zodiacal_direction_matches_original_and_reconstruction() -> None:
    case = _case("lilly_vega_zodiacal_projection_to_asc")
    inputs = case["inputs"]
    civil = inputs["gregorian_ut1_proxy"]
    hour = (
        float(civil["hour"])
        + float(civil["minute"]) / 60.0
        + float(civil["second"]) / 3600.0
    )
    jd_ut1 = julian_day(
        int(civil["year"]),
        int(civil["month"]),
        int(civil["day"]),
        hour,
    )
    jd_tt = ut_to_tt(jd_ut1)

    name, longitude, true_latitude = resolve_primary_direction_fixed_star_point(
        PrimaryDirectionFixedStarTarget(str(inputs["star_name"])),
        jd_tt=jd_tt,
    )
    assert name == "Vega"
    assert abs(true_latitude) > 1.0

    arc = _zodiacal_arc_to_ascendant(
        promissor_name=name,
        promissor_longitude=longitude,
        ascendant_longitude=float(inputs["ascendant_degrees"]),
        armc=float(inputs["armc_degrees"]),
        obliquity=float(inputs["obliquity_degrees"]),
        geo_latitude=float(inputs["geo_latitude_degrees"]),
    )
    expected = case["expected"]
    tolerance = case["tolerance"]

    assert longitude == pytest.approx(
        expected["lilly"]["longitude_degrees"],
        abs=float(tolerance["lilly_longitude_degrees"]),
    )
    assert arc == pytest.approx(
        expected["lilly"]["arc_degrees"],
        abs=float(tolerance["lilly_arc_degrees"]),
    )
    assert longitude == pytest.approx(
        expected["kolev_reconstruction"]["longitude_degrees"],
        abs=float(tolerance["kolev_longitude_degrees"]),
    )
    assert arc == pytest.approx(
        expected["kolev_reconstruction"]["arc_degrees"],
        abs=float(tolerance["kolev_arc_degrees"]),
    )


def test_lilly_jupiter_antiscion_matches_reflected_point_and_arc() -> None:
    case = _case("lilly_jupiter_antiscion_to_asc")
    inputs = case["inputs"]
    reflected = project_primary_direction_antiscia_longitude(
        float(inputs["source_longitude_degrees"]),
        PrimaryDirectionAntisciaKind(str(inputs["kind"])),
    )
    arc = _zodiacal_arc_to_ascendant(
        promissor_name="Jupiter Antiscion",
        promissor_longitude=reflected,
        ascendant_longitude=float(inputs["ascendant_degrees"]),
        armc=float(inputs["armc_degrees"]),
        obliquity=float(inputs["obliquity_degrees"]),
        geo_latitude=float(inputs["geo_latitude_degrees"]),
    )
    expected = case["expected"]
    tolerance = case["tolerance"]

    assert reflected == pytest.approx(
        expected["reflected_longitude_degrees"],
        abs=float(tolerance["reflected_longitude_degrees"]),
    )
    assert arc == pytest.approx(
        expected["arc_degrees"],
        abs=float(tolerance["arc_degrees"]),
    )


def test_sepharial_zodiacal_parallel_matches_published_equivalent_and_arc() -> None:
    case = _case("sepharial_sun_parallel_uranus_zodiacal")
    inputs = case["inputs"]
    projected = project_ptolemaic_declination_point(
        source_longitude=float(inputs["source_longitude_for_branch_selection_degrees"]),
        source_declination=float(inputs["source_declination_degrees"]),
        obliquity=float(inputs["obliquity_degrees"]),
        relation=PtolemaicParallelRelation(str(inputs["relation"])),
    )
    published_arc = (
        (
            float(inputs["published_target_rise_st_hours"])
            - float(inputs["published_source_rise_st_hours"])
        )
        % 24.0
    ) * 15.0
    expected = case["expected"]
    tolerance = case["tolerance"]

    assert projected == pytest.approx(
        expected["equivalent_longitude_degrees"],
        abs=float(tolerance["equivalent_longitude_degrees"]),
    )
    assert published_arc == pytest.approx(
        expected["arc_degrees"],
        abs=float(tolerance["arc_degrees"]),
    )


@pytest.mark.parametrize(
    ("case_id", "calculator"),
    [
        (
            "leo_saturn_rapt_parallel_moon_direct",
            compute_placidian_rapt_parallel_arc,
        ),
        (
            "leo_saturn_rapt_parallel_moon_converse",
            compute_placidian_converse_rapt_parallel_arc,
        ),
    ],
)
def test_leo_rapt_parallel_examples_match_published_arcs(
    case_id: str,
    calculator: object,
) -> None:
    case = _case(case_id)
    inputs = case["inputs"]
    promissor = _rapt_entry(inputs["promissor"])
    significator = _rapt_entry(inputs["significator"])

    arc = calculator(promissor, significator)

    assert arc == pytest.approx(
        case["expected"]["arc_degrees"],
        abs=float(case["tolerance"]["arc_degrees"]),
    )


def test_borealis_morinus_context_matches_published_sextile_point() -> None:
    case = _case("borealis_churchill_jupiter_sinister_sextile")
    inputs = case["inputs"]
    longitude, latitude = project_morinus_aspect_point(
        longitude=float(inputs["longitude_degrees"]),
        latitude=float(inputs["latitude_degrees"]),
        maximum_latitude=float(inputs["maximum_latitude_degrees"]),
        moving_toward_maximum=bool(inputs["moving_toward_maximum"]),
        aspect_angle=float(inputs["aspect_angle_degrees"]),
    )
    expected = case["expected"]
    tolerance = case["tolerance"]

    assert longitude == pytest.approx(
        expected["longitude_degrees"],
        abs=float(tolerance["longitude_degrees"]),
    )
    assert latitude == pytest.approx(
        expected["latitude_degrees"],
        abs=float(tolerance["latitude_degrees"]),
    )
