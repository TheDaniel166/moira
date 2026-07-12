"""SCP Phase 1 truth-preservation tests for the natal Astrodynes core."""

from __future__ import annotations

import pytest

from moira.astrodynes import (
    ASTRODYNE_ANGLE_POINT_POWER,
    ASTRODYNE_ASPECT_ORB_ROWS,
    ASTRODYNE_DIGNITY_ROWS,
    ASTRODYNE_HOUSE_POWER_ROWS,
    ASTRODYNE_PARALLEL_ORB_ARCMIN,
    ASTRODYNE_ELEMENT_GROUPS,
    ASTRODYNE_QUALITY_GROUPS,
    ASTRODYNE_SOCIETY_GROUPS,
    ASTRODYNE_SIGNS,
    ASTRODYNE_TRINITY_GROUPS,
    DEFAULT_ASTRODYNE_POLICY,
    AstrodyneAspectFamily,
    AstrodyneAspectHarmonyTruth,
    AstrodyneBodyInput,
    AstrodyneBodyKind,
    AstrodyneChartAggregate,
    AstrodyneContributionSource,
    AstrodyneDignityCondition,
    AstrodyneEssentialDignityTruth,
    AstrodyneHousePositionTruth,
    AstrodyneHouseAggregate,
    AstrodyneParallelAspectTruth,
    AstrodynePolicy,
    AstrodyneRelationKind,
    AstrodyneRulerShareTruth,
    AstrodyneSignAggregate,
    AstrodyneSummaryFamily,
    AstrodyneZodiacalAspectTruth,
    aspect_harmony,
    astrodynes_summary,
    essential_dignity,
    evaluate_parallel_relation,
    evaluate_zodiacal_relation,
    house_position_power,
    mutual_reception,
    natal_astrodynes,
    natal_astrodynes_from_geometry,
    parallel_aspect_power,
    ruler_power_share,
    validate_astrodynes_output,
    zodiacal_aspect_power,
)


def _zodiac(sign_index: int, degree: int, minute: int) -> float:
    return sign_index * 30.0 + degree + minute / 60.0


def _declination(degree: int, minute: int, *, south: bool = False) -> float:
    value = degree + minute / 60.0
    return -value if south else value


def _full_chart_inputs() -> tuple[AstrodyneBodyInput, ...]:
    rows = (
        ("Sun", 0.0, 1, "angular", 10.0),
        ("Moon", 60.0, 2, "succedent", 10.5),
        ("Mercury", 120.0, 3, "cadent", 5.0),
        ("Venus", 180.0, 4, "angular", -5.2),
        ("Mars", 240.0, 5, "succedent", 20.0),
        ("Jupiter", 300.0, 6, "cadent", -20.4),
        ("Saturn", 30.0, 7, "angular", 15.0),
        ("Uranus", 90.0, 8, "succedent", -15.2),
        ("Neptune", 150.0, 9, "cadent", 2.0),
        ("Pluto", 210.0, 10, "angular", -2.5),
    )
    planets = tuple(
        AstrodyneBodyInput(
            body=body,
            longitude_deg=longitude,
            house=house,
            house_class=house_class,
            distance_from_weaker_cusp_deg=5.0,
            house_size_deg=30.0,
            declination_deg=declination,
        )
        for body, longitude, house, house_class, declination in rows
    )
    return (
        *planets,
        AstrodyneBodyInput("M.C.", 270.0, 10, "angular", declination_deg=-23.0),
        AstrodyneBodyInput("Asc.", 0.0, 1, "angular", declination_deg=0.0),
    )


class TestSourceTables:
    def test_all_ten_planets_have_one_dignity_row(self) -> None:
        assert len(ASTRODYNE_DIGNITY_ROWS) == 10
        assert len({row.planet for row in ASTRODYNE_DIGNITY_ROWS}) == 10

    def test_full_dignity_table_matches_the_confirmed_source(self) -> None:
        actual = [
            (
                row.planet,
                row.home_signs,
                row.detriment_signs,
                row.exaltation_sign,
                row.exaltation_degree,
                row.fall_sign,
                row.fall_degree,
                row.harmony_sign,
                row.inharmony_sign,
            )
            for row in ASTRODYNE_DIGNITY_ROWS
        ]
        assert actual == [
            ("Sun", ("Leo",), ("Aquarius",), "Aries", 19.0, "Libra", 19.0, "Sagittarius", "Gemini"),
            ("Moon", ("Cancer",), ("Capricorn",), "Taurus", 3.0, "Scorpio", 3.0, "Pisces", "Virgo"),
            ("Mercury", ("Gemini", "Virgo"), ("Sagittarius", "Pisces"), "Aquarius", 15.0, "Leo", 15.0, "Scorpio", "Taurus"),
            ("Venus", ("Taurus", "Libra"), ("Aries", "Scorpio"), "Pisces", 27.0, "Virgo", 27.0, "Aquarius", "Leo"),
            ("Mars", ("Aries", "Scorpio"), ("Taurus", "Libra"), "Capricorn", 28.0, "Cancer", 28.0, "Leo", "Aquarius"),
            ("Jupiter", ("Sagittarius", "Pisces"), ("Gemini", "Virgo"), "Cancer", 15.0, "Capricorn", 15.0, "Taurus", "Scorpio"),
            ("Saturn", ("Capricorn", "Aquarius"), ("Cancer", "Leo"), "Libra", 21.0, "Aries", 21.0, "Virgo", "Pisces"),
            ("Uranus", ("Aquarius",), ("Leo",), "Gemini", 7.0, "Sagittarius", 7.0, "Libra", "Aries"),
            ("Neptune", ("Pisces",), ("Virgo",), "Sagittarius", 18.0, "Gemini", 18.0, "Cancer", "Capricorn"),
            ("Pluto", ("Scorpio",), ("Taurus",), "Leo", 17.0, "Aquarius", 17.0, "Aries", "Libra"),
        ]

    def test_all_twelve_houses_have_one_power_row(self) -> None:
        assert len(ASTRODYNE_HOUSE_POWER_ROWS) == 12
        assert {row.house for row in ASTRODYNE_HOUSE_POWER_ROWS} == set(range(1, 13))
        assert [
            (row.house, row.weaker_cusp_power, row.stronger_cusp_power)
            for row in ASTRODYNE_HOUSE_POWER_ROWS
        ] == [
            (6, 6.5, 7.0),
            (5, 7.0, 7.5),
            (3, 7.5, 8.0),
            (2, 8.0, 8.5),
            (12, 8.6, 9.3),
            (9, 9.3, 10.0),
            (8, 10.0, 10.9),
            (11, 10.9, 11.9),
            (4, 12.0, 14.0),
            (7, 12.5, 14.5),
            (10, 13.0, 15.0),
            (1, 13.0, 15.0),
        ]

    def test_all_nine_zodiacal_aspect_orb_rows_are_preserved(self) -> None:
        assert [row.aspect for row in ASTRODYNE_ASPECT_ORB_ROWS] == [
            "conjunction",
            "semi-sextile",
            "sextile",
            "square",
            "trine",
            "inconjunct",
            "semi-square",
            "sesqui-square",
            "opposition",
        ]
        assert [row.as_tuple() for row in ASTRODYNE_ASPECT_ORB_ROWS] == [
            (0.0, 10.0, 13.0, 12.0, 15.0, 8.0, 11.0),
            (30.0, 2.0, 3.0, 3.0, 4.0, 1.0, 2.0),
            (60.0, 6.0, 7.0, 7.0, 8.0, 5.0, 6.0),
            (90.0, 8.0, 10.0, 10.0, 12.0, 6.0, 8.0),
            (120.0, 8.0, 10.0, 10.0, 12.0, 6.0, 8.0),
            (150.0, 2.0, 3.0, 3.0, 4.0, 1.0, 2.0),
            (45.0, 4.0, 5.0, 5.0, 6.0, 3.0, 4.0),
            (135.0, 4.0, 5.0, 5.0, 6.0, 3.0, 4.0),
            (180.0, 10.0, 13.0, 12.0, 15.0, 8.0, 11.0),
        ]
        assert ASTRODYNE_ANGLE_POINT_POWER == 15.0
        assert ASTRODYNE_PARALLEL_ORB_ARCMIN == 60.0

    def test_mercury_row_preserves_church_of_light_doctrine(self) -> None:
        row = next(row for row in ASTRODYNE_DIGNITY_ROWS if row.planet == "Mercury")
        assert row.home_signs == ("Gemini", "Virgo")
        assert row.detriment_signs == ("Sagittarius", "Pisces")
        assert (row.exaltation_sign, row.exaltation_degree) == ("Aquarius", 15.0)
        assert (row.fall_sign, row.fall_degree) == ("Leo", 15.0)
        assert row.harmony_sign == "Scorpio"
        assert row.inharmony_sign == "Taurus"

    def test_other_corrected_source_rows_are_not_conventionalized(self) -> None:
        rows = {row.planet: row for row in ASTRODYNE_DIGNITY_ROWS}
        assert (rows["Venus"].harmony_sign, rows["Venus"].inharmony_sign) == (
            "Aquarius",
            "Leo",
        )
        assert (rows["Jupiter"].harmony_sign, rows["Jupiter"].inharmony_sign) == (
            "Taurus",
            "Scorpio",
        )
        neptune = rows["Neptune"]
        assert (neptune.exaltation_sign, neptune.fall_sign) == (
            "Sagittarius",
            "Gemini",
        )
        assert (neptune.harmony_sign, neptune.inharmony_sign) == (
            "Cancer",
            "Capricorn",
        )


class TestHousePositionPower:
    def test_manual_venus_twelfth_house_example(self) -> None:
        truth = house_position_power(12, 3.33, 19.55)
        assert isinstance(truth, AstrodyneHousePositionTruth)
        assert truth.weaker_cusp_power == 8.6
        assert truth.stronger_cusp_power == 9.3
        assert truth.variation == pytest.approx(0.7)
        assert truth.interpolation_fraction == pytest.approx(3.33 / 19.55)
        assert truth.astrodyne_power == pytest.approx(8.7192327366)
        assert round(truth.astrodyne_power, 2) == 8.72

    def test_endpoints_preserve_source_cusp_powers(self) -> None:
        assert house_position_power(1, 0.0, 30.0).astrodyne_power == 13.0
        assert house_position_power(1, 30.0, 30.0).astrodyne_power == 15.0

    @pytest.mark.parametrize(
        ("distance", "size"),
        [(-0.1, 30.0), (30.1, 30.0), (1.0, 0.0)],
    )
    def test_invalid_geometry_is_rejected(self, distance: float, size: float) -> None:
        with pytest.raises(ValueError):
            house_position_power(1, distance, size)


class TestZodiacalAspectPower:
    def test_manual_sun_jupiter_trine(self) -> None:
        truth = zodiacal_aspect_power(
            "Sun",
            _zodiac(5, 12, 42),
            "succedent",
            "Jupiter",
            _zodiac(9, 6, 31),
            "succedent",
            "trine",
        )
        assert isinstance(truth, AstrodyneZodiacalAspectTruth)
        assert truth.distance_from_perfect_deg == pytest.approx(6 + 11 / 60)
        assert truth.admitted_presence_orb_deg == 10.0
        assert truth.admitted_scoring_orb_deg == 10.0
        assert truth.within_orb
        assert truth.astrodyne_power == pytest.approx(3 + 49 / 60)
        assert round(truth.astrodyne_power, 2) == 3.82

    def test_manual_mars_mercury_sextile(self) -> None:
        truth = zodiacal_aspect_power(
            "Mars",
            _zodiac(8, 4, 21),
            "angular",
            "Mercury",
            _zodiac(6, 7, 44),
            "succedent",
            "sextile",
        )
        assert truth.distance_from_perfect_deg == pytest.approx(3 + 23 / 60)
        assert truth.admitted_presence_orb_deg == 7.0
        assert truth.admitted_scoring_orb_deg == 7.0
        assert truth.astrodyne_power == pytest.approx(3 + 37 / 60)
        assert round(truth.astrodyne_power, 2) == 3.62

    def test_manual_mercury_saturn_opposition_preserves_two_orb_rule(self) -> None:
        truth = zodiacal_aspect_power(
            "Mercury",
            _zodiac(7, 15, 15),
            "angular",
            "Saturn",
            _zodiac(1, 27, 4),
            "succedent",
            "opposition",
        )
        assert truth.distance_from_perfect_deg == pytest.approx(11 + 49 / 60)
        assert truth.presence_orb_a_deg == 12.0
        assert truth.admitted_presence_orb_deg == 12.0
        assert truth.scoring_orb_a_deg == 15.0
        assert truth.admitted_scoring_orb_deg == 15.0
        assert truth.within_orb
        assert truth.astrodyne_power == pytest.approx(3 + 11 / 60)
        assert round(truth.astrodyne_power, 2) == 3.18

    def test_mercury_scoring_orb_cannot_admit_an_absent_aspect(self) -> None:
        truth = zodiacal_aspect_power(
            "Mercury",
            0.0,
            "angular",
            "Saturn",
            166.0,
            "succedent",
            "opposition",
        )
        assert truth.distance_from_perfect_deg == 14.0
        assert truth.admitted_presence_orb_deg == 12.0
        assert truth.admitted_scoring_orb_deg == 15.0
        assert not truth.within_orb
        assert truth.astrodyne_power == 0.0

    def test_mc_and_ascendant_require_angular_orb_column(self) -> None:
        with pytest.raises(ValueError, match="angular"):
            zodiacal_aspect_power(
                "M.C.", 0.0, "cadent", "Sun", 120.0, "angular", "trine"
            )


class TestParallelAspectPower:
    def test_manual_sun_saturn_opposite_hemisphere_example(self) -> None:
        truth = parallel_aspect_power(
            "Sun",
            _declination(20, 23),
            "cadent",
            "Saturn",
            _declination(20, 1, south=True),
            "angular",
        )
        assert isinstance(truth, AstrodyneParallelAspectTruth)
        assert truth.magnitude_separation_arcmin == pytest.approx(22.0)
        assert truth.scale_fraction == pytest.approx(38 / 60)
        assert truth.scaled_power_a == pytest.approx(6.9666666667)
        assert truth.scaled_power_b == pytest.approx(7.6)
        assert truth.astrodyne_power == pytest.approx(7.6)

    def test_manual_mercury_venus_59_arcminute_example(self) -> None:
        truth = parallel_aspect_power(
            "Mercury",
            _declination(14, 19),
            "angular",
            "Venus",
            _declination(15, 18),
            "succedent",
        )
        assert truth.magnitude_separation_arcmin == pytest.approx(59.0)
        assert truth.scaled_power_a == pytest.approx(0.25)
        assert truth.scaled_power_b == pytest.approx(1 / 6)
        assert truth.astrodyne_power == pytest.approx(0.25)

    def test_manual_uranus_jupiter_opposite_hemisphere_example(self) -> None:
        truth = parallel_aspect_power(
            "Uranus",
            _declination(3, 38, south=True),
            "succedent",
            "Jupiter",
            _declination(4, 2),
            "cadent",
        )
        assert truth.magnitude_separation_arcmin == pytest.approx(24.0)
        assert truth.scaled_power_a == pytest.approx(6.0)
        assert truth.scaled_power_b == pytest.approx(4.8)
        assert truth.astrodyne_power == pytest.approx(6.0)

    def test_beyond_sixty_arcminutes_is_absent(self) -> None:
        truth = parallel_aspect_power(
            "Sun", 10.0, "angular", "Moon", 11.1, "angular"
        )
        assert not truth.within_orb
        assert truth.scale_fraction == 0.0
        assert truth.astrodyne_power == 0.0


class TestEssentialDignity:
    def test_mercury_in_aquarius_is_exalted_not_traditional_virgo(self) -> None:
        truth = essential_dignity("Mercury", "Aquarius", 10.0)
        assert isinstance(truth, AstrodyneEssentialDignityTruth)
        assert truth.condition == "exaltation"
        assert truth.harmony_delta == 3.0
        assert truth.exact_degree == 15.0

        virgo = essential_dignity("Mercury", "Virgo", 15.0)
        assert virgo.condition == "home"
        assert virgo.harmony_delta == 2.0

    @pytest.mark.parametrize("degree", [14.0, 15.0, 16.0])
    def test_degree_of_exaltation_band_is_inclusive(self, degree: float) -> None:
        truth = essential_dignity("Mercury", "Aquarius", degree)
        assert truth.condition == "degree_of_exaltation"
        assert truth.degree_emphasis_applied
        assert truth.harmony_delta == 4.0

    def test_outside_degree_band_uses_sign_exaltation(self) -> None:
        truth = essential_dignity("Mercury", "Aquarius", 16.000001)
        assert truth.condition == "exaltation"
        assert not truth.degree_emphasis_applied
        assert truth.harmony_delta == 3.0

    def test_degree_of_fall_is_negative_four(self) -> None:
        truth = essential_dignity("Mercury", "Leo", 15.5)
        assert truth.condition == "degree_of_fall"
        assert truth.harmony_delta == -4.0

    @pytest.mark.parametrize(
        ("sign", "condition", "delta"),
        [
            ("Gemini", "home", 2.0),
            ("Sagittarius", "detriment", -2.0),
            ("Scorpio", "harmony", 1.0),
            ("Taurus", "inharmony", -1.0),
            ("Cancer", None, 0.0),
        ],
    )
    def test_mercury_source_row_conditions(
        self,
        sign: str,
        condition: str | None,
        delta: float,
    ) -> None:
        truth = essential_dignity("Mercury", sign, 5.0)
        assert truth.condition == condition
        assert truth.harmony_delta == delta

    def test_neptune_row_uses_church_of_light_axis(self) -> None:
        assert essential_dignity("Neptune", "Sagittarius", 10.0).harmony_delta == 3.0
        assert essential_dignity("Neptune", "Gemini", 10.0).harmony_delta == -3.0
        assert essential_dignity("Neptune", "Cancer", 10.0).harmony_delta == 1.0
        assert essential_dignity("Neptune", "Capricorn", 10.0).harmony_delta == -1.0


class TestAspectHarmony:
    def test_harmonious_aspect_plus_jupiter_nature(self) -> None:
        truth = aspect_harmony("Sun", "Jupiter", "trine", 8.0)
        assert isinstance(truth, AstrodyneAspectHarmonyTruth)
        assert truth.base_harmony == 8.0
        assert truth.base_discord == 0.0
        assert truth.total_harmony == 12.0
        assert truth.total_discord == 0.0
        assert truth.net_harmony == 12.0

    def test_discordant_aspect_plus_saturn_nature(self) -> None:
        truth = aspect_harmony("Moon", "Saturn", "square", 6.0)
        assert truth.base_discord == 6.0
        assert truth.total_discord == 9.0
        assert truth.net_harmony == -9.0

    def test_neutral_parallel_preserves_opposed_planet_natures(self) -> None:
        truth = aspect_harmony("Venus", "Mars", "parallel", 4.0)
        assert truth.base_harmony == 0.0
        assert truth.base_discord == 0.0
        assert truth.total_harmony == 1.0
        assert truth.total_discord == 1.0
        assert truth.net_harmony == 0.0

    def test_negative_power_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            aspect_harmony("Sun", "Moon", "conjunction", -1.0)


class TestClassificationInspectabilityAndPolicy:
    def test_truth_uses_typed_classification(self) -> None:
        dignity = essential_dignity("Mercury", "Aquarius", 10.0)
        harmony = aspect_harmony("Sun", "Jupiter", "trine", 8.0)
        assert dignity.condition is AstrodyneDignityCondition.EXALTATION
        assert dignity.is_dignified
        assert not dignity.is_debilitated
        assert harmony.family is AstrodyneAspectFamily.HARMONIOUS
        assert harmony.is_harmonious

    def test_default_policy_makes_fixed_doctrine_visible(self) -> None:
        assert DEFAULT_ASTRODYNE_POLICY.degree_emphasis_orb_deg == 1.0
        assert DEFAULT_ASTRODYNE_POLICY.parallel_orb_arcmin == 60.0
        assert DEFAULT_ASTRODYNE_POLICY.mutual_reception_bonus == 5.0

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"degree_emphasis_orb_deg": 2.0},
            {"parallel_orb_arcmin": 59.0},
            {"mutual_reception_bonus": 4.0},
        ],
    )
    def test_policy_rejects_unsourced_alternatives(self, kwargs: dict[str, float]) -> None:
        with pytest.raises(ValueError):
            AstrodynePolicy(**kwargs)


class TestRelations:
    def test_zodiacal_relation_distinguishes_detected_admitted_and_scored(self) -> None:
        admitted = evaluate_zodiacal_relation(
            "Sun", 0.0, "angular", "Moon", 120.0, "angular", "trine"
        )
        absent = evaluate_zodiacal_relation(
            "Sun", 0.0, "angular", "Moon", 140.0, "angular", "trine"
        )
        assert admitted.kind is AstrodyneRelationKind.ZODIACAL_ASPECT
        assert admitted.detected and admitted.admitted and admitted.scored
        assert absent.detected and not absent.admitted and not absent.scored

    def test_parallel_relation_preserves_relation_kind(self) -> None:
        relation = evaluate_parallel_relation(
            "Sun", 10.0, "angular", "Moon", -10.5, "succedent"
        )
        assert relation.kind is AstrodyneRelationKind.PARALLEL
        assert relation.aspect == "parallel"
        assert relation.admitted

    def test_mercury_uranus_mutual_reception_uses_astrodyne_table(self) -> None:
        relation = mutual_reception("Mercury", "Aquarius", "Uranus", "Gemini")
        assert relation.kind is AstrodyneRelationKind.MUTUAL_RECEPTION
        assert relation.a_occupies_b_dignity
        assert relation.b_occupies_a_dignity
        assert relation.admitted and relation.scored
        assert relation.bonus_each == 5.0

    def test_one_sided_reception_is_detected_but_not_admitted(self) -> None:
        relation = mutual_reception("Mercury", "Aquarius", "Uranus", "Cancer")
        assert relation.a_occupies_b_dignity
        assert not relation.b_occupies_a_dignity
        assert relation.detected and not relation.admitted and not relation.scored
        assert relation.bonus_each == 0.0


def _published_trump_aggregate() -> AstrodyneChartAggregate:
    """Reconstruct the official Class 5 summary inputs, not chart geometry."""

    sign_rows = (
        ("Aries", 16.65, 1.85),
        # The displayed sign rows sum to 784.06 while every published summary
        # family sums to 784.05. Reconcile Taurus by the one-cent display
        # uncertainty so this synthetic aggregate preserves the engine checksum.
        ("Taurus", 64.88, -4.47),
        ("Gemini", 170.30, 7.52),
        ("Cancer", 129.65, 10.54),
        ("Leo", 159.52, 17.98),
        ("Virgo", 14.38, -0.56),
        ("Libra", 71.14, 43.23),
        ("Scorpio", 17.85, -0.43),
        ("Sagittarius", 95.77, 16.11),
        ("Capricorn", 8.71, 1.26),
        ("Aquarius", 22.82, 3.89),
        ("Pisces", 12.38, 9.29),
    )
    house_rows = (
        (1, 121.44, 23.41),
        (2, 33.29, -7.55),
        (3, 52.22, 50.22),
        (4, 17.85, -0.43),
        (5, 95.77, 16.11),
        (6, 8.71, 1.26),
        (7, 22.82, 3.89),
        (8, 12.38, 9.29),
        (9, 16.65, 1.85),
        (10, 64.89, -4.47),
        (11, 199.05, 6.40),
        (12, 138.98, 6.23),
    )

    signs = tuple(
        AstrodyneSignAggregate(
            sign=sign,
            rulers=("Sun",),
            cusp_count=0,
            intercepted_houses=(),
            ruler_fraction=0.0,
            occupants=(),
            ruler_power=0.0,
            occupant_power=power,
            total_power=power,
            total_harmony=max(net_harmony, 0.0),
            total_discord=max(-net_harmony, 0.0),
            net_harmony=net_harmony,
        )
        for sign, power, net_harmony in sign_rows
    )
    houses = tuple(
        AstrodyneHouseAggregate(
            house=house,
            cusp_sign=ASTRODYNE_SIGNS[house - 1],
            intercepted_signs=(),
            occupants=(),
            ruler_power=0.0,
            occupant_power=power,
            total_power=power,
            total_harmony=max(net_harmony, 0.0),
            total_discord=max(-net_harmony, 0.0),
            net_harmony=net_harmony,
        )
        for house, power, net_harmony in house_rows
    )
    return AstrodyneChartAggregate(
        signs=signs,
        houses=houses,
        total_body_power=537.08,
        total_sign_power=sum(item.total_power for item in signs),
        total_house_power=sum(item.total_power for item in houses),
        total_sign_harmony=sum(item.net_harmony for item in signs),
        total_house_harmony=sum(item.net_harmony for item in houses),
    )


class TestClassFiveSummaries:
    def test_source_owned_group_memberships(self) -> None:
        assert ASTRODYNE_SOCIETY_GROUPS == (
            ("Personal", (12, 1, 2, 3)),
            ("Companionship", (4, 5, 6, 7)),
            ("Public", (8, 9, 10, 11)),
        )
        assert ASTRODYNE_TRINITY_GROUPS == (
            ("Life", (1, 5, 9)),
            ("Wealth", (2, 6, 10)),
            ("Association", (3, 7, 11)),
            ("Psychism", (4, 8, 12)),
        )
        assert ASTRODYNE_ELEMENT_GROUPS == (
            ("Fire", ("Aries", "Leo", "Sagittarius")),
            ("Earth", ("Taurus", "Virgo", "Capricorn")),
            ("Air", ("Gemini", "Libra", "Aquarius")),
            ("Water", ("Cancer", "Scorpio", "Pisces")),
        )
        assert ASTRODYNE_QUALITY_GROUPS == (
            ("Movable", ("Aries", "Cancer", "Libra", "Capricorn")),
            ("Fixed", ("Taurus", "Leo", "Scorpio", "Aquarius")),
            ("Mutable", ("Gemini", "Virgo", "Sagittarius", "Pisces")),
        )

    def test_official_trump_summary_oracle(self) -> None:
        summary = astrodynes_summary(_published_trump_aggregate())

        published = {
            AstrodyneSummaryFamily.SOCIETY: (
                ("Personal", 345.93, 44.1, 72.31),
                ("Companionship", 145.15, 18.5, 20.83),
                ("Public", 292.97, 37.4, 13.08),
            ),
            AstrodyneSummaryFamily.TRINITY: (
                ("Life", 233.86, 29.8, 41.38),
                ("Wealth", 106.89, 13.6, -10.76),
                ("Association", 274.09, 35.0, 60.52),
                ("Psychism", 169.21, 21.6, 15.09),
            ),
            AstrodyneSummaryFamily.ELEMENT: (
                ("Fire", 271.94, 34.7, 35.95),
                ("Earth", 87.97, 11.2, -3.77),
                ("Air", 264.26, 33.7, 54.64),
                ("Water", 159.88, 20.4, 19.40),
            ),
            AstrodyneSummaryFamily.QUALITY: (
                ("Movable", 226.15, 28.8, 56.88),
                ("Fixed", 265.07, 33.8, 16.97),
                ("Mutable", 292.83, 37.3, 32.37),
            ),
        }
        for family, expected_rows in published.items():
            actual_rows = summary.family(family)
            assert tuple(item.name for item in actual_rows) == tuple(
                row[0] for row in expected_rows
            )
            for actual, (_, power, percentage, harmony) in zip(
                actual_rows, expected_rows, strict=True
            ):
                # Published source inputs and outputs are both rounded to 0.01.
                assert actual.power == pytest.approx(power, abs=0.011)
                assert actual.rounded_percentage == percentage
                assert actual.net_harmony == pytest.approx(harmony, abs=0.011)
        assert summary.dominant(AstrodyneSummaryFamily.SOCIETY).name == "Personal"
        assert summary.dominant(AstrodyneSummaryFamily.TRINITY).name == "Association"
        assert summary.dominant(AstrodyneSummaryFamily.ELEMENT).name == "Fire"
        assert summary.dominant(AstrodyneSummaryFamily.QUALITY).name == "Mutable"


class TestIntegratedChart:
    def setup_method(self) -> None:
        self.inputs = _full_chart_inputs()
        self.result = natal_astrodynes(
            self.inputs,
            (
                "Aries",
                "Taurus",
                "Gemini",
                "Cancer",
                "Leo",
                "Virgo",
                "Libra",
                "Scorpio",
                "Sagittarius",
                "Capricorn",
                "Aquarius",
                "Pisces",
            ),
        )

    def test_body_inputs_classify_planets_and_angles(self) -> None:
        assert self.inputs[0].body_kind is AstrodyneBodyKind.PLANET
        assert self.inputs[-1].body_kind is AstrodyneBodyKind.ANGLE
        assert self.inputs[0].sign == "Aries"
        assert self.inputs[0].sign_degree == 0.0

    def test_profile_preserves_contribution_totals(self) -> None:
        mercury = self.result.profile("Mercury")
        assert mercury.dignity is not None
        assert mercury.total_power == pytest.approx(
            sum(item.power for item in mercury.contributions)
        )
        assert mercury.net_harmony == pytest.approx(
            mercury.total_harmony - mercury.total_discord
        )
        assert mercury.contributions_from(AstrodyneContributionSource.HOUSE_POSITION)

    def test_sign_and_house_checksums_pass(self) -> None:
        aggregate = self.result.aggregate
        assert aggregate.checksums_pass
        assert aggregate.power_checksum_delta == pytest.approx(0.0, abs=1e-9)
        assert aggregate.harmony_checksum_delta == pytest.approx(0.0, abs=1e-9)

    def test_summary_is_integrated_and_partitions_chart_totals(self) -> None:
        assert self.result.summary == astrodynes_summary(self.result.aggregate)
        for family in AstrodyneSummaryFamily:
            entries = self.result.summary.family(family)
            assert sum(item.power for item in entries) == pytest.approx(
                self.result.summary.total_power
            )
            assert sum(item.percentage for item in entries) == pytest.approx(100.0)

    def test_manual_ruler_share_examples(self) -> None:
        taurus = ruler_power_share(("Venus",), (34.16,), cusp_count=1)
        gemini = ruler_power_share(("Mercury",), (52.08,), intercepted_count=1)
        aquarius_cusp = ruler_power_share(
            ("Saturn", "Uranus"), (28.22, 40.50), cusp_count=1
        )
        aquarius_two_cusps = ruler_power_share(
            ("Saturn", "Uranus"), (28.22, 40.50), cusp_count=2
        )
        assert isinstance(taurus, AstrodyneRulerShareTruth)
        assert taurus.contribution == pytest.approx(17.08)
        assert gemini.contribution == pytest.approx(13.02)
        assert aquarius_cusp.average_ruler_power == pytest.approx(34.36)
        assert aquarius_cusp.contribution == pytest.approx(17.18)
        assert aquarius_two_cusps.contribution == pytest.approx(34.36)
        assert taurus.contribution + 36.48 + 24.18 == pytest.approx(77.74)
        assert gemini.contribution + 28.22 == pytest.approx(41.24)
        assert 34.16 + 36.48 + 24.18 == pytest.approx(94.82)
        assert taurus.contribution + 24.18 == pytest.approx(41.26)
        assert (
            taurus.contribution + 24.18 + gemini.contribution + 28.22
        ) == pytest.approx(82.50)

    def test_manual_sign_harmony_rollups(self) -> None:
        sagittarius_ruler_share = 18.24 / 2.0
        assert sagittarius_ruler_share + 7.22 - 12.16 == pytest.approx(4.18)
        capricorn_ruler_discord = 14.12 / 2.0
        assert capricorn_ruler_discord + 6.20 == pytest.approx(13.26)

    def test_double_ruler_signs_are_derived_from_source_home_rows(self) -> None:
        assert self.result.sign("Aquarius").rulers == ("Saturn", "Uranus")
        assert self.result.sign("Pisces").rulers == ("Jupiter", "Neptune")
        assert self.result.sign("Scorpio").rulers == ("Mars", "Pluto")

    def test_network_aligns_with_admitted_relations(self) -> None:
        assert len(self.result.network.nodes) == 12
        assert len(self.result.network.edges) == len(self.result.relations.admitted)
        assert self.result.network.neighbors("Sun")

    def test_validation_has_no_failures(self) -> None:
        assert validate_astrodynes_output(self.result) == ()

    def test_input_order_does_not_change_deterministic_output(self) -> None:
        reverse = natal_astrodynes(
            tuple(reversed(self.inputs)),
            tuple(self.result.aggregate.signs[index].sign for index in range(12)),
        )
        assert [profile.body for profile in reverse.profiles] == [
            profile.body for profile in self.result.profiles
        ]
        assert [relation.sort_key for relation in reverse.relations.detected] == [
            relation.sort_key for relation in self.result.relations.detected
        ]
        assert reverse.aggregate.total_sign_power == pytest.approx(
            self.result.aggregate.total_sign_power
        )

    def test_incomplete_chart_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="all ten planets"):
            natal_astrodynes(self.inputs[:-1], tuple(ASTRODYNE_SIGNS))

    def test_house_class_must_match_house_number(self) -> None:
        with pytest.raises(ValueError, match="requires house_class"):
            AstrodyneBodyInput(
                "Sun",
                0.0,
                2,
                "angular",
                distance_from_weaker_cusp_deg=1.0,
                house_size_deg=30.0,
            )


class TestExplicitGeometryAdapter:
    def test_derives_house_interpolation_and_interceptions(self) -> None:
        cusp_longitudes = (
            0.0,
            30.0,
            90.0,
            120.0,
            150.0,
            180.0,
            210.0,
            240.0,
            270.0,
            300.0,
            330.0,
            345.0,
        )
        planet_longitudes = {
            body: longitude
            for body, longitude in zip(
                (
                    "Sun",
                    "Moon",
                    "Mercury",
                    "Venus",
                    "Mars",
                    "Jupiter",
                    "Saturn",
                    "Uranus",
                    "Neptune",
                    "Pluto",
                ),
                (5.0, 45.0, 95.0, 125.0, 155.0, 185.0, 215.0, 245.0, 275.0, 305.0),
                strict=True,
            )
        }
        declinations = {body: 2.0 * index for index, body in enumerate(planet_longitudes)}
        declinations.update({"M.C.": 20.0, "Asc.": 0.0})

        result = natal_astrodynes_from_geometry(
            planet_longitudes,
            declinations,
            cusp_longitudes,
            mc_longitude=300.0,
            asc_longitude=0.0,
        )

        sun = result.profile("Sun")
        assert sun.house_position is not None
        assert sun.house_position.house == 1
        assert sun.house_position.house_size_deg == 30.0
        assert sun.house_position.distance_from_weaker_cusp_deg == 25.0
        assert result.sign("Gemini").intercepted_houses == (2,)

    def test_requires_angles_to_match_their_cusps(self) -> None:
        longitudes = {
            body: index * 30.0 + 1.0
            for index, body in enumerate(
                ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
            )
        }
        declinations = {body: 0.0 for body in longitudes}
        declinations.update({"M.C.": 0.0, "Asc.": 0.0})
        with pytest.raises(ValueError, match="asc_longitude"):
            natal_astrodynes_from_geometry(
                longitudes,
                declinations,
                tuple(float(index * 30) for index in range(12)),
                mc_longitude=270.0,
                asc_longitude=1.0,
            )


def test_phase_one_is_not_curated_at_package_root() -> None:
    import moira

    assert "AstrodyneHousePositionTruth" not in moira.__dict__
    assert "house_position_power" not in moira.__dict__
