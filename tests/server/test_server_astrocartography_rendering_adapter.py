"""Structural tests for the internal Astrocartography rendering adapter."""

from __future__ import annotations

from moira.astrocartography import ACGLine
from moira_server.models.astrocartography import AstrocartographyDirectLinesRequest
from moira_server.serializers.astrocartography import serialize_astrocartography_lines
from moira_server.services.astrocartography import compute_astrocartography_direct_lines
from moira_server.services.astrocartography_rendering import (
    adapt_acg_lines_for_rendering,
    adapt_astrocartography_response_for_rendering,
)


def _primitive_map(packet):
    return {
        (primitive.body, primitive.line_type): primitive
        for primitive in packet.primitives
    }


def test_meridian_materialization_preserves_source_longitude() -> None:
    provenance = {"coordinate_source": "direct_ra_dec"}
    packet = adapt_acg_lines_for_rendering(
        [ACGLine(planet="Sun", line_type="MC", longitude=200.0)],
        source_provenance=provenance,
    )

    primitive = packet.primitives[0]
    assert primitive.body == "Sun"
    assert primitive.line_type == "MC"
    assert primitive.primitive_type == "meridian"
    assert primitive.wrap_policy == "none"
    assert primitive.segments[0][0].latitude == -90.0
    assert primitive.segments[0][1].latitude == 90.0
    assert primitive.segments[0][0].longitude == -160.0
    assert primitive.segments[0][1].longitude == -160.0
    assert primitive.source_provenance is provenance
    assert packet.source_provenance is provenance


def test_sampled_curve_splits_at_antimeridian_without_dropping_points() -> None:
    line = ACGLine(
        planet="Moon",
        line_type="ASC",
        points=[(-20.0, 170.0), (0.0, 190.0), (20.0, 200.0)],
    )

    packet = adapt_acg_lines_for_rendering([line])
    primitive = packet.primitives[0]

    assert primitive.primitive_type == "sampled_curve"
    assert primitive.wrap_policy == "antimeridian_split"
    assert len(primitive.segments) == 2
    rendered_points = [point for segment in primitive.segments for point in segment]
    assert [(point.latitude, point.longitude) for point in rendered_points] == [
        (-20.0, 170.0),
        (0.0, -170.0),
        (20.0, -160.0),
    ]
    assert packet.metadata.antimeridian_split_count == 1


def test_sampled_curve_without_crossing_remains_one_segment() -> None:
    line = ACGLine(
        planet="Venus",
        line_type="DSC",
        points=[(-20.0, 10.0), (0.0, 20.0), (20.0, 30.0)],
    )

    packet = adapt_acg_lines_for_rendering([line])
    primitive = packet.primitives[0]

    assert primitive.wrap_policy == "none"
    assert len(primitive.segments) == 1
    assert len(primitive.segments[0]) == 3


def test_style_hints_do_not_change_geometry() -> None:
    line = ACGLine(
        planet="Mars",
        line_type="ASC",
        points=[(0.0, 10.0), (10.0, 20.0)],
    )

    plain = adapt_acg_lines_for_rendering([line])
    styled = adapt_acg_lines_for_rendering(
        [line],
        style_hints={"Mars:ASC": "accented-mars-asc"},
    )

    assert styled.primitives[0].style_key == "accented-mars-asc"
    assert styled.primitives[0].segments == plain.primitives[0].segments


def test_primitive_ordering_is_deterministic_by_body_line_type_and_source() -> None:
    lines = [
        ACGLine(planet="Venus", line_type="DSC", points=[(0.0, 10.0)]),
        ACGLine(planet="Sun", line_type="ASC", points=[(0.0, 20.0)]),
        ACGLine(planet="Sun", line_type="MC", longitude=30.0),
        ACGLine(planet="Venus", line_type="MC", longitude=40.0),
    ]

    packet = adapt_acg_lines_for_rendering(lines)

    assert [
        (primitive.body, primitive.line_type, primitive.source_index)
        for primitive in packet.primitives
    ] == [
        ("Sun", "MC", 2),
        ("Sun", "ASC", 1),
        ("Venus", "MC", 3),
        ("Venus", "DSC", 0),
    ]


def test_adapts_serialized_astrocartography_route_response_shape() -> None:
    request = AstrocartographyDirectLinesRequest.model_validate(
        {
            "positions": {
                "Sun": {"right_ascension": 100.0, "declination": 10.0}
            },
            "gmst_deg": 20.0,
            "lat_step": 10.0,
            "refraction": False,
        }
    )
    response_body = serialize_astrocartography_lines(
        compute_astrocartography_direct_lines(request)
    ).model_dump(mode="json")
    packet = adapt_astrocartography_response_for_rendering(response_body)
    primitives = _primitive_map(packet)

    assert set(primitives) == {
        ("Sun", "MC"),
        ("Sun", "IC"),
        ("Sun", "ASC"),
        ("Sun", "DSC"),
    }
    assert primitives[("Sun", "MC")].primitive_type == "meridian"
    assert primitives[("Sun", "ASC")].primitive_type == "sampled_curve"
    assert packet.source_provenance is response_body["provenance"]
    assert all(
        primitive.source_provenance is response_body["provenance"]
        for primitive in packet.primitives
    )
    assert packet.metadata.generated_primitive_count == 4
