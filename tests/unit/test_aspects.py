from __future__ import annotations

from moira.aspects import (
    AspectData,
    DeclinationAspect,
    aspects_between,
    aspects_to_point,
    find_aspects,
    find_declination_aspects,
)


def test_find_aspects_detects_wraparound_conjunction() -> None:
    results = find_aspects(
        {
            "Sun": 359.0,
            "Moon": 1.0,
        },
        include_minor=False,
    )

    assert len(results) == 1
    aspect = results[0]
    assert aspect.aspect == "Conjunction"
    assert aspect.body1 == "Sun"
    assert aspect.body2 == "Moon"
    assert aspect.orb == 2.0


def test_aspect_data_repr_includes_applying_and_stationary_flags() -> None:
    aspect = AspectData(
        body1="Sun",
        body2="Moon",
        aspect="Conjunction",
        symbol="☌",
        angle=0.0,
        orb=0.5,
        applying=True,
        stationary=True,
    )

    rendered = repr(aspect)
    assert "Sun" in rendered
    assert "Moon" in rendered
    assert "applying" in rendered
    assert "[stationary]" in rendered


def test_find_aspects_tier_overrides_include_minor_flag() -> None:
    positions = {
        "Sun": 0.0,
        "Moon": 150.0,
    }

    major_only = find_aspects(positions, include_minor=True, tier=0)
    common_minor = find_aspects(positions, include_minor=False, tier=1)

    assert major_only == []
    assert len(common_minor) == 1
    assert common_minor[0].aspect == "Quincunx"


def test_find_aspects_invalid_tier_falls_back_to_major_only() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 60.0,
            "Mars": 150.0,
        },
        tier=999,
        include_minor=True,
    )

    assert [aspect.aspect for aspect in results] == ["Sextile", "Square"]


def test_find_aspects_custom_orbs_override_orb_factor() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 66.0,
        },
        orbs={60.0: 6.0},
        include_minor=False,
        orb_factor=0.1,
    )

    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].orb == 6.0


def test_find_aspects_no_match_returns_empty_list() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 13.0,
        },
        include_minor=False,
        orb_factor=0.1,
    )

    assert results == []


def test_find_aspects_returns_sorted_by_tightest_orb() -> None:
    results = find_aspects(
        {
            "Sun": 0.0,
            "Moon": 121.0,
            "Mercury": 200.0,
            "Venus": 262.0,
        },
        include_minor=False,
    )

    assert [aspect.aspect for aspect in results] == ["Trine", "Sextile"]
    assert [aspect.orb for aspect in results] == [1.0, 2.0]
    assert results[0].orb <= results[1].orb


def test_aspects_between_extended_minor_is_available_at_default_tier() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        36.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Decile"
    assert results[0].orb == 0.0


def test_aspects_between_invalid_tier_falls_back_to_all_aspects() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        36.0,
        tier=999,
    )

    assert len(results) == 1
    assert results[0].aspect == "Decile"


def test_aspects_between_applying_and_separating_respect_wraparound() -> None:
    applying = aspects_between(
        "Sun",
        359.0,
        "Moon",
        1.0,
        tier=0,
        speed_a=2.0,
        speed_b=1.0,
    )
    separating = aspects_between(
        "Sun",
        359.0,
        "Moon",
        1.0,
        tier=0,
        speed_a=1.0,
        speed_b=2.0,
    )

    assert len(applying) == 1
    assert applying[0].applying is True
    assert applying[0].stationary is False

    assert len(separating) == 1
    assert separating[0].applying is False
    assert separating[0].stationary is False


def test_aspects_between_partial_speed_information_yields_unknown_applying() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        60.0,
        tier=0,
        speed_a=1.0,
    )

    assert len(results) == 1
    assert results[0].applying is None
    assert results[0].stationary is False


def test_aspects_between_stationary_body_sets_stationary_and_unknown_applying() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        60.0,
        tier=0,
        speed_a=0.004,
        speed_b=1.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].applying is None
    assert results[0].stationary is True


def test_aspects_between_custom_orbs_override_orb_factor() -> None:
    results = aspects_between(
        "Sun",
        0.0,
        "Moon",
        66.0,
        tier=0,
        orbs={60.0: 6.0},
        orb_factor=0.1,
    )

    assert len(results) == 1
    assert results[0].aspect == "Sextile"
    assert results[0].orb == 6.0


def test_aspects_to_point_respects_point_name_and_sorting() -> None:
    results = aspects_to_point(
        120.0,
        {
            "Sun": 119.0,
            "Moon": 0.0,
            "Mercury": 271.0,
        },
        point_name="MC",
        include_minor=False,
    )

    assert [aspect.body2 for aspect in results] == ["MC", "MC"]
    assert [aspect.body1 for aspect in results] == ["Moon", "Sun"]
    assert [aspect.aspect for aspect in results] == ["Trine", "Conjunction"]
    assert [aspect.orb for aspect in results] == [0.0, 1.0]


def test_aspects_to_point_custom_orbs_and_invalid_tier_paths() -> None:
    results = aspects_to_point(
        60.0,
        {
            "Sun": 126.0,
            "Moon": 0.0,
        },
        point_name="Vertex",
        orbs={60.0: 6.0},
        tier=999,
        orb_factor=0.1,
    )

    assert len(results) == 2
    assert [aspect.body1 for aspect in results] == ["Moon", "Sun"]
    assert [aspect.body2 for aspect in results] == ["Vertex", "Vertex"]
    assert [aspect.aspect for aspect in results] == ["Sextile", "Sextile"]
    assert [aspect.orb for aspect in results] == [0.0, 6.0]


def test_aspects_to_point_no_match_returns_empty_list() -> None:
    results = aspects_to_point(
        120.0,
        {
            "Sun": 10.0,
        },
        include_minor=False,
        orb_factor=0.1,
    )

    assert results == []


def test_find_declination_aspects_detects_parallel() -> None:
    results = find_declination_aspects(
        {
            "Sun": 10.0,
            "Moon": 10.5,
        },
        orb=1.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Parallel"
    assert results[0].body1 == "Sun"
    assert results[0].body2 == "Moon"
    assert round(results[0].orb, 6) == 0.5


def test_find_declination_aspects_detects_contraparallel() -> None:
    results = find_declination_aspects(
        {
            "Sun": 10.0,
            "Mars": -10.2,
        },
        orb=1.0,
    )

    assert len(results) == 1
    assert results[0].aspect == "Contra-Parallel"
    assert results[0].body1 == "Sun"
    assert results[0].body2 == "Mars"
    assert round(results[0].orb, 6) == 0.2


def test_declination_aspect_repr_and_no_match_path() -> None:
    aspect = DeclinationAspect(
        body1="Sun",
        body2="Moon",
        aspect="Parallel",
        dec1=10.0,
        dec2=10.2,
        orb=0.2,
    )

    rendered = repr(aspect)
    assert "Parallel" in rendered
    assert "Sun" in rendered
    assert "Moon" in rendered

    assert find_declination_aspects({"Sun": 10.0, "Moon": 25.0}, orb=1.0) == []
