from __future__ import annotations

import pytest


def test_firdaria_standard_day_nodes_are_terminal_without_subperiods() -> None:
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=True)
    major = [p for p in periods if p.level == 1]
    node_major = [p for p in major if p.planet in {"North Node", "South Node"}]

    assert [p.planet for p in node_major] == ["North Node", "South Node"]

    for node_period in node_major:
        subs = [
            p for p in periods
            if p.level == 2
            and p.start_jd >= node_period.start_jd - 1e-9
            and p.end_jd <= node_period.end_jd + 1e-9
        ]
        assert subs == []


def test_firdaria_supports_bonatti_nocturnal_variant() -> None:
    from moira.timelords import firdaria

    standard = [p.planet for p in firdaria(2451545.0, is_day_chart=False) if p.level == 1]
    bonatti = [
        p.planet
        for p in firdaria(2451545.0, is_day_chart=False, variant="bonatti")
        if p.level == 1
    ]

    assert standard[:7] == ["Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury"]
    assert bonatti[:7] == ["Moon", "Saturn", "Jupiter", "Mars", "North Node", "South Node", "Sun"]


def test_current_firdaria_returns_major_for_node_period_when_no_subperiods() -> None:
    from moira.timelords import current_firdaria

    natal_jd = 2451545.0
    current_jd = natal_jd + 70.5 * 365.25
    major, sub = current_firdaria(natal_jd, current_jd, is_day_chart=True)

    assert major.planet == "North Node"
    assert sub.planet == "North Node"


def test_decennials_day_sequence_starts_from_sect_light_in_zodiacal_order() -> None:
    from moira.timelords import decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True, levels=1)

    assert [period.planet for period in periods if period.level == 1] == [
        "Sun", "Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn",
    ]


def test_decennials_night_sequence_starts_from_moon_in_zodiacal_order() -> None:
    from moira.timelords import decennials, DecennialSequenceKind

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, False, levels=1)

    assert [period.planet for period in periods if period.level == 1] == [
        "Moon", "Jupiter", "Saturn", "Sun", "Mercury", "Venus", "Mars",
    ]
    assert all(period.sequence_kind == DecennialSequenceKind.NOCTURNAL_LUNAR for period in periods)


def test_decennials_major_periods_have_expected_lengths_and_cycle() -> None:
    from moira.timelords import decennials, DecennialSequenceKind

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True, levels=1)
    major = [period for period in periods if period.level == 1]

    assert len(major) == 7
    assert all(period.months == pytest.approx(129.0, abs=1e-12) for period in major)
    assert all(period.years == pytest.approx(10.75, abs=1e-12) for period in major)
    assert [period.major_index for period in major] == list(range(7))
    assert all(period.sect_light == "Sun" for period in major)
    assert all(period.sequence_kind == DecennialSequenceKind.DIURNAL_SOLAR for period in major)
    assert all(period.is_diurnal_solar is True for period in major)
    assert all(period.is_nocturnal_lunar is False for period in major)
    assert all(period.month_basis_days == pytest.approx(30.0, abs=1e-12) for period in major)
    assert all(period.major_month_total == pytest.approx(129.0, abs=1e-12) for period in major)
    assert all(period.sequence == ("Sun", "Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn") for period in major)
    assert major[-1].end_jd - major[0].start_jd == pytest.approx(903.0 * 30.0, abs=1e-9)


def test_decennials_subperiods_rotate_major_sequence_and_preserve_months() -> None:
    from moira.timelords import decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True)
    first_major = next(period for period in periods if period.level == 1)
    subs = [period for period in periods if period.level == 2 and period.major_planet == first_major.planet]

    assert [period.planet for period in subs] == [
        "Sun", "Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn",
    ]
    assert [period.sub_index for period in subs] == list(range(7))
    assert [period.sequence_position for period in subs] == list(range(1, 8))
    assert all(period.major_index == 0 for period in subs)
    assert all(period.sequence == first_major.sequence for period in subs)
    assert all(period.effective_major_planet == "Sun" for period in subs)
    assert all(period.rotated_sequence == first_major.sequence for period in subs)
    assert [period.months for period in subs] == pytest.approx([19.0, 20.0, 8.0, 15.0, 25.0, 12.0, 30.0], abs=1e-12)


def test_decennials_phase3_helpers_expose_major_relative_truth() -> None:
    from moira.timelords import decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True)
    major = next(period for period in periods if period.level == 1 and period.planet == "Mercury")
    sub = next(
        period
        for period in periods
        if period.level == 2 and period.major_planet == "Mercury" and period.planet == "Venus"
    )

    assert major.effective_major_planet == "Mercury"
    assert major.sequence_position == 2
    assert major.rotated_sequence == ("Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn", "Sun")
    assert sub.effective_major_planet == "Mercury"
    assert sub.sequence_position == 2
    assert sub.rotated_sequence == ("Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn", "Sun")


def test_decennial_period_rejects_phase3_truth_breaks() -> None:
    from moira.timelords import DecennialPeriod, DecennialSequenceKind

    common = {
        "start_jd": 2451545.0,
        "end_jd": 2451546.0,
        "years": 1.0,
        "months": 12.0,
        "sect_light": "Sun",
        "sequence_kind": DecennialSequenceKind.DIURNAL_SOLAR,
        "sequence": ("Sun", "Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn"),
        "major_month_total": 129.0,
        "month_basis_days": 30.0,
    }

    with pytest.raises(ValueError, match="level-1 periods must not set major_planet"):
        DecennialPeriod(level=1, planet="Sun", major_planet="Sun", major_index=0, **common)

    with pytest.raises(ValueError, match="level-1 periods must not set sub_index"):
        DecennialPeriod(level=1, planet="Sun", sub_index=0, major_index=0, **common)

    with pytest.raises(ValueError, match="level-2 periods must preserve major_planet"):
        DecennialPeriod(level=2, planet="Sun", major_index=0, sub_index=0, **common)

    with pytest.raises(ValueError, match="level-2 periods must preserve sub_index"):
        DecennialPeriod(
            level=2,
            planet="Sun",
            major_planet="Sun",
            parent_planet="Sun",
            parent_level=1,
            ancestor_planets=("Sun",),
            major_index=0,
            **common,
        )

    with pytest.raises(ValueError, match="major planet must match preserved sequence at major_index"):
        DecennialPeriod(level=1, planet="Sun", major_index=1, **common)

    with pytest.raises(ValueError, match="sub planet must match rotated sequence at sub_index"):
        DecennialPeriod(
            level=2,
            planet="Mars",
            major_planet="Mercury",
            parent_planet="Mercury",
            parent_level=1,
            ancestor_planets=("Mercury",),
            major_index=1,
            sub_index=1,
            **common,
        )


def test_decennials_night_periods_preserve_moon_sect_light_truth() -> None:
    from moira.timelords import decennials, DecennialSequenceKind

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, False)

    assert all(period.sect_light == "Moon" for period in periods)
    assert all(period.is_day_chart is False for period in periods)
    assert all(period.sequence_kind == DecennialSequenceKind.NOCTURNAL_LUNAR for period in periods)
    assert all(period.is_nocturnal_lunar is True for period in periods)
    assert all(period.is_diurnal_solar is False for period in periods)
    assert periods[0].sequence == ("Moon", "Jupiter", "Saturn", "Sun", "Mercury", "Venus", "Mars")


def test_decennial_period_rejects_unknown_sequence_kind() -> None:
    from moira.timelords import DecennialPeriod

    with pytest.raises(ValueError, match="sequence_kind must be a supported DecennialSequenceKind"):
        DecennialPeriod(
            level=1,
            planet="Sun",
            start_jd=2451545.0,
            end_jd=2451546.0,
            years=1.0,
            months=12.0,
            sequence_kind="sideways",
        )


def test_current_decennials_returns_active_major_and_subperiod() -> None:
    from moira.timelords import current_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    major, sub = current_decennials(2451545.0, natal_positions, True, 2451545.0 + (19.0 * 30.0) + 1.0)

    assert major.planet == "Sun"
    assert sub.planet == "Mercury"


def test_decennials_levels_one_returns_only_major_periods_and_current_pair_collapses() -> None:
    from moira.timelords import decennials, current_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True, levels=1)
    major, sub = current_decennials(2451545.0, natal_positions, True, 2451545.0 + 10.0, levels=1)

    assert all(period.level == 1 for period in periods)
    assert major.planet == "Sun"
    assert sub.planet == "Sun"


def test_validate_decennials_output_passes_for_genuine_output() -> None:
    from moira.timelords import decennials, validate_decennials_output

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    validate_decennials_output(decennials(2451545.0, natal_positions, True))


def test_decennials_rejects_missing_or_nonfinite_longitudes() -> None:
    from moira.timelords import decennials

    with pytest.raises(ValueError, match="missing required planets"):
        decennials(2451545.0, {"Sun": 10.0}, True)

    with pytest.raises(ValueError, match="must be finite"):
        decennials(
            2451545.0,
            {
                "Sun": 10.0,
                "Mercury": 20.0,
                "Venus": 50.0,
                "Mars": 110.0,
                "Moon": 200.0,
                "Jupiter": 250.0,
                "Saturn": float("nan"),
            },
            True,
        )


def test_decennials_valens_deep_subdivision_admits_levels_three_and_four() -> None:
    from moira.timelords import decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))

    periods = decennials(2451545.0, natal_positions, True, levels=4, policy=policy)

    assert any(period.level == 3 for period in periods)
    assert any(period.level == 4 for period in periods)
    assert all(
        period.deep_subdivision_method == "valens"
        for period in periods
        if period.level >= 3
    )


def test_decennials_hephaistio_admits_level_three_only() -> None:
    from moira.timelords import decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="hephaistio"))

    periods = decennials(2451545.0, natal_positions, True, levels=3, policy=policy)

    assert any(period.level == 3 for period in periods)
    assert not any(period.level == 4 for period in periods)
    assert all(
        period.deep_subdivision_method == "hephaistio"
        for period in periods
        if period.level == 3
    )


def test_decennials_rejects_unadmitted_deep_levels_without_supported_policy() -> None:
    from moira.timelords import decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    with pytest.raises(ValueError, match="supports up to level 2"):
        decennials(2451545.0, natal_positions, True, levels=3)

    hephaistio = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="hephaistio"))
    with pytest.raises(ValueError, match="supports up to level 3"):
        decennials(2451545.0, natal_positions, True, levels=4, policy=hephaistio)


def test_decennials_deep_subdivision_preserves_recursive_proportions() -> None:
    from moira.timelords import decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    periods = decennials(2451545.0, natal_positions, True, levels=4, policy=policy)

    l2_sun = next(period for period in periods if period.level == 2 and period.major_planet == "Sun" and period.planet == "Sun")
    l3_sun = next(
        period for period in periods
        if period.level == 3 and period.ancestor_planets == ("Sun", "Sun") and period.planet == "Sun"
    )
    l4_sun = next(
        period for period in periods
        if period.level == 4 and period.ancestor_planets == ("Sun", "Sun", "Sun") and period.planet == "Sun"
    )

    assert l3_sun.days == pytest.approx(l2_sun.days * (19.0 / 129.0), abs=1e-9)
    assert l4_sun.days == pytest.approx(l3_sun.days * (19.0 / 129.0), abs=1e-9)


def test_current_decennials_returns_deepest_active_period_when_requested() -> None:
    from moira.timelords import current_decennials, decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    periods = decennials(2451545.0, natal_positions, True, levels=4, policy=policy)
    l4 = next(period for period in periods if period.level == 4)
    mid_jd = (l4.start_jd + l4.end_jd) / 2.0

    major, leaf = current_decennials(2451545.0, natal_positions, True, mid_jd, levels=4, policy=policy)

    assert major.level == 1
    assert leaf.level == 4


def test_validate_decennials_output_passes_for_genuine_deep_output() -> None:
    from moira.timelords import decennials, validate_decennials_output, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))

    validate_decennials_output(decennials(2451545.0, natal_positions, True, levels=4, policy=policy))


def test_validate_decennials_output_detects_deep_method_drift() -> None:
    """Deep Decennials validation rejects lineage whose deep method drifts from its parent."""
    from moira.timelords import decennials, validate_decennials_output, DecennialPolicy, TimelordComputationPolicy
    import dataclasses

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    periods = decennials(2451545.0, natal_positions, True, levels=4, policy=policy)
    target = next(period for period in periods if period.level == 3)
    broken = dataclasses.replace(target)
    object.__setattr__(broken, "deep_subdivision_method", "hephaistio")
    tampered = [broken if period is target else period for period in periods]

    with pytest.raises(ValueError, match="must preserve deep_subdivision_method of parent"):
        validate_decennials_output(tampered)


def test_validate_decennials_output_detects_invalid_parent_level_truth() -> None:
    """Deep Decennials validation rejects subordinate periods with broken parent-level truth."""
    from moira.timelords import decennials, validate_decennials_output, DecennialPolicy, TimelordComputationPolicy
    import dataclasses

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="hephaistio"))
    periods = decennials(2451545.0, natal_positions, True, levels=3, policy=policy)
    target = next(period for period in periods if period.level == 3)
    broken = dataclasses.replace(target)
    object.__setattr__(broken, "parent_level", 1)
    tampered = [broken if period is target else period for period in periods]

    with pytest.raises(ValueError, match="must preserve parent_level=2"):
        validate_decennials_output(tampered)


def test_zodiacal_releasing_uses_same_sign_spirit_adjustment() -> None:
    from moira.timelords import zodiacal_releasing

    periods = zodiacal_releasing(
        10.0,
        2451545.0,
        levels=1,
        lot_name="Spirit",
        fortune_longitude=15.0,
    )

    assert periods[0].sign == "Taurus"


def test_zodiacal_releasing_marks_loosing_of_bond_for_long_signs() -> None:
    from moira.timelords import zodiacal_releasing

    periods = [
        p for p in zodiacal_releasing(275.0, 2451545.0, levels=2)
        if p.level == 2
    ]

    first_lb = next(p for p in periods if p.is_loosing_of_bond)
    assert first_lb.sign == "Cancer"


def test_zodiacal_releasing_marks_peak_periods_relative_to_fortune() -> None:
    from moira.timelords import zodiacal_releasing

    periods = [
        p for p in zodiacal_releasing(
            65.0,
            2451545.0,
            levels=1,
            lot_name="Spirit",
            fortune_longitude=10.0,
        )
        if p.level == 1
    ]

    peak_signs = {p.sign for p in periods if p.is_peak_period}
    assert {"Cancer", "Libra", "Capricorn"} <= peak_signs


def test_zodiacal_releasing_level_scaling_uses_symbolic_units() -> None:
    from moira.timelords import zodiacal_releasing

    natal_jd = 2451545.0
    level_1 = [p for p in zodiacal_releasing(0.0, natal_jd, levels=1) if p.level == 1][0]
    level_2 = [p for p in zodiacal_releasing(0.0, natal_jd, levels=2) if p.level == 2][0]
    level_3 = [p for p in zodiacal_releasing(0.0, natal_jd, levels=3) if p.level == 3][0]
    level_4 = [p for p in zodiacal_releasing(0.0, natal_jd, levels=4) if p.level == 4][0]

    assert (level_1.end_jd - level_1.start_jd) == pytest.approx(15 * 360.0, abs=1e-9)
    assert (level_2.end_jd - level_2.start_jd) == pytest.approx(15 * 30.0, abs=1e-9)
    assert (level_3.end_jd - level_3.start_jd) == pytest.approx(15 * 2.5, abs=1e-9)
    assert (level_4.end_jd - level_4.start_jd) == pytest.approx(15 * (5.0 / 24.0), abs=1e-9)
    assert level_1.years == pytest.approx(15.0, abs=1e-9)
    assert level_2.years == pytest.approx(15.0 / 12.0, abs=1e-9)
    assert level_3.years == pytest.approx(15.0 / 144.0, abs=1e-9)
    assert level_4.years == pytest.approx(15.0 / 1728.0, abs=1e-9)


def test_current_releasing_rejects_dates_beyond_full_primary_circuit() -> None:
    from moira.timelords import _TOTAL_MINOR_YEARS, current_releasing

    natal_jd = 2451545.0
    with pytest.raises(ValueError, match="full Zodiacal Releasing circuit cap"):
        current_releasing(0.0, natal_jd, natal_jd + _TOTAL_MINOR_YEARS * 360.0 + 1.0)


# ---------------------------------------------------------------------------
# Phase 1 truth preservation — FirdarPeriod
# ---------------------------------------------------------------------------

def test_firdar_major_period_carries_sect_and_variant() -> None:
    """Major periods preserve is_day_chart and variant on the vessel itself."""
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=True, variant="standard")
    major = [p for p in periods if p.level == 1]

    for p in major:
        assert p.is_day_chart is True
        assert p.variant == "standard"


def test_firdar_sub_period_carries_major_planet() -> None:
    """Sub-periods preserve the name of the level-1 lord they belong to."""
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=True)
    major = [p for p in periods if p.level == 1]
    subs  = [p for p in periods if p.level == 2]

    # Every sub-period's major_planet must match a real major lord
    major_planets = {p.planet for p in major}
    for sub in subs:
        assert sub.major_planet in major_planets


def test_firdar_sub_period_major_planet_matches_enclosing_period() -> None:
    """Each sub-period's major_planet agrees with the major period it falls inside."""
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=False, variant="bonatti")
    major = [p for p in periods if p.level == 1]
    subs  = [p for p in periods if p.level == 2]

    for sub in subs:
        enclosing = next(
            (m for m in major if m.start_jd <= sub.start_jd < m.end_jd),
            None,
        )
        assert enclosing is not None, f"No enclosing major for sub {sub}"
        assert sub.major_planet == enclosing.planet


def test_firdar_major_planet_is_none_for_level_1() -> None:
    """Level-1 periods have no major_planet (they ARE the major planet)."""
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=True)
    for p in periods:
        if p.level == 1:
            assert p.major_planet is None


def test_firdar_period_days_property() -> None:
    """days property equals end_jd - start_jd."""
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=True)
    for p in periods[:10]:
        assert p.days == pytest.approx(p.end_jd - p.start_jd, abs=1e-12)


# ---------------------------------------------------------------------------
# Phase 1 truth preservation — ReleasingPeriod
# ---------------------------------------------------------------------------

def test_releasing_period_carries_use_loosing_of_bond_true() -> None:
    """Periods generated with use_loosing_of_bond=True carry that context."""
    from moira.timelords import zodiacal_releasing

    periods = zodiacal_releasing(0.0, 2451545.0, levels=1, use_loosing_of_bond=True)
    for p in periods:
        assert p.use_loosing_of_bond is True


def test_releasing_period_carries_use_loosing_of_bond_false() -> None:
    """Periods generated with use_loosing_of_bond=False carry that context."""
    from moira.timelords import zodiacal_releasing

    periods = zodiacal_releasing(0.0, 2451545.0, levels=1, use_loosing_of_bond=False)
    for p in periods:
        assert p.use_loosing_of_bond is False


def test_releasing_use_loosing_of_bond_false_produces_no_lb_periods() -> None:
    """When LB doctrine is off, no period is ever flagged is_loosing_of_bond."""
    from moira.timelords import zodiacal_releasing

    periods = zodiacal_releasing(275.0, 2451545.0, levels=2, use_loosing_of_bond=False)
    assert all(not p.is_loosing_of_bond for p in periods)


# ---------------------------------------------------------------------------
# Phase 2 classification — FirdarPeriod
# ---------------------------------------------------------------------------

def test_firdar_sequence_kind_diurnal() -> None:
    """Day-chart periods carry DIURNAL sequence kind."""
    from moira.timelords import firdaria, FirdarSequenceKind

    periods = firdaria(2451545.0, is_day_chart=True)
    for p in periods:
        assert p.sequence_kind == FirdarSequenceKind.DIURNAL


def test_firdar_sequence_kind_nocturnal_standard() -> None:
    """Nocturnal standard periods carry NOCTURNAL_STANDARD sequence kind."""
    from moira.timelords import firdaria, FirdarSequenceKind

    periods = firdaria(2451545.0, is_day_chart=False, variant="standard")
    for p in periods:
        assert p.sequence_kind == FirdarSequenceKind.NOCTURNAL_STANDARD


def test_firdar_sequence_kind_nocturnal_bonatti() -> None:
    """Nocturnal Bonatti periods carry NOCTURNAL_BONATTI sequence kind."""
    from moira.timelords import firdaria, FirdarSequenceKind

    periods = firdaria(2451545.0, is_day_chart=False, variant="bonatti")
    for p in periods:
        assert p.sequence_kind == FirdarSequenceKind.NOCTURNAL_BONATTI


def test_firdar_is_node_period_correct_for_nodes() -> None:
    """is_node_period is True for North Node and South Node periods, False otherwise."""
    from moira.timelords import firdaria

    periods = firdaria(2451545.0, is_day_chart=True)
    for p in periods:
        if p.planet in {"North Node", "South Node"}:
            assert p.is_node_period is True
        else:
            assert p.is_node_period is False


def test_firdar_is_node_period_on_sub_periods() -> None:
    """is_node_period is set correctly on sub-periods when nodes are subdivided."""
    from moira.timelords import firdaria, CHALDEAN_ORDER

    # Sub-periods use Chaldean planets only; none are nodes
    periods = firdaria(2451545.0, is_day_chart=True)
    subs = [p for p in periods if p.level == 2]
    assert all(not p.is_node_period for p in subs)


# ---------------------------------------------------------------------------
# Phase 2 classification — ReleasingPeriod
# ---------------------------------------------------------------------------

def test_releasing_angularity_class_on_peak_periods() -> None:
    """Peak periods carry a non-None angularity_class."""
    from moira.timelords import zodiacal_releasing, ZRAngularityClass

    periods = zodiacal_releasing(65.0, 2451545.0, levels=1,
                                  lot_name="Spirit", fortune_longitude=10.0)
    for p in periods:
        if p.is_peak_period:
            assert p.angularity_class in {
                ZRAngularityClass.ANGULAR,
                ZRAngularityClass.SUCCEDENT,
                ZRAngularityClass.CADENT,
            }


def test_releasing_angularity_class_none_on_non_peak_periods() -> None:
    """Non-peak periods have angularity_class = None."""
    from moira.timelords import zodiacal_releasing

    periods = zodiacal_releasing(65.0, 2451545.0, levels=1,
                                  lot_name="Spirit", fortune_longitude=10.0)
    for p in periods:
        if not p.is_peak_period:
            assert p.angularity_class is None


def test_releasing_angular_houses_are_classified_angular() -> None:
    """Houses 1, 4, 7, 10 from Fortune classify as ANGULAR."""
    from moira.timelords import ZRAngularityClass, _zr_angularity_class

    for house in (1, 4, 7, 10):
        assert _zr_angularity_class(house) == ZRAngularityClass.ANGULAR


def test_releasing_succedent_houses_are_classified_succedent() -> None:
    """Houses 2, 5, 8, 11 from Fortune classify as SUCCEDENT."""
    from moira.timelords import ZRAngularityClass, _zr_angularity_class

    for house in (2, 5, 8, 11):
        assert _zr_angularity_class(house) == ZRAngularityClass.SUCCEDENT


def test_releasing_cadent_houses_are_classified_cadent() -> None:
    """Houses 3, 6, 9, 12 from Fortune classify as CADENT."""
    from moira.timelords import ZRAngularityClass, _zr_angularity_class

    for house in (3, 6, 9, 12):
        assert _zr_angularity_class(house) == ZRAngularityClass.CADENT


# ---------------------------------------------------------------------------
# Phase 3 inspectability — FirdarPeriod
# ---------------------------------------------------------------------------

def test_firdar_period_rejects_invalid_level() -> None:
    """FirdarPeriod.__post_init__ rejects levels outside {1, 2}."""
    from moira.timelords import FirdarPeriod

    with pytest.raises(ValueError, match="level must be 1 or 2"):
        FirdarPeriod(level=0, planet="Sun", start_jd=2451545.0, end_jd=2451546.0, years=1.0)

    with pytest.raises(ValueError, match="level must be 1 or 2"):
        FirdarPeriod(level=3, planet="Sun", start_jd=2451545.0, end_jd=2451546.0, years=1.0)


def test_firdar_period_rejects_inverted_jd() -> None:
    """FirdarPeriod.__post_init__ rejects end_jd <= start_jd."""
    from moira.timelords import FirdarPeriod

    with pytest.raises(ValueError, match="end_jd must be greater than start_jd"):
        FirdarPeriod(level=1, planet="Sun", start_jd=2451546.0, end_jd=2451545.0, years=1.0)

    with pytest.raises(ValueError, match="end_jd must be greater than start_jd"):
        FirdarPeriod(level=1, planet="Sun", start_jd=2451545.0, end_jd=2451545.0, years=1.0)


def test_firdar_period_rejects_non_positive_years() -> None:
    """FirdarPeriod.__post_init__ rejects years <= 0."""
    from moira.timelords import FirdarPeriod

    with pytest.raises(ValueError, match="years must be positive"):
        FirdarPeriod(level=1, planet="Sun", start_jd=2451545.0, end_jd=2451546.0, years=0.0)

    with pytest.raises(ValueError, match="years must be positive"):
        FirdarPeriod(level=1, planet="Sun", start_jd=2451545.0, end_jd=2451546.0, years=-1.0)


def test_firdar_period_is_major_and_is_sub() -> None:
    """is_major is True for level=1; is_sub is True for level=2."""
    from moira.timelords import FirdarPeriod

    major = FirdarPeriod(level=1, planet="Sun", start_jd=2451545.0, end_jd=2455113.0, years=10.0)
    sub   = FirdarPeriod(level=2, planet="Venus", start_jd=2451545.0, end_jd=2452456.0, years=2.5)

    assert major.is_major is True
    assert major.is_sub is False
    assert sub.is_major is False
    assert sub.is_sub is True


def test_firdar_period_level_name() -> None:
    """level_name returns 'Major' for level 1 and 'Sub-period' for level 2."""
    from moira.timelords import FirdarPeriod

    major = FirdarPeriod(level=1, planet="Sun", start_jd=2451545.0, end_jd=2455113.0, years=10.0)
    sub   = FirdarPeriod(level=2, planet="Venus", start_jd=2451545.0, end_jd=2452456.0, years=2.5)

    assert major.level_name == "Major"
    assert sub.level_name == "Sub-period"


def test_firdar_period_is_active_at_boundary_semantics() -> None:
    """is_active_at uses half-open [start, end) interval."""
    from moira.timelords import FirdarPeriod

    p = FirdarPeriod(level=1, planet="Sun", start_jd=2451545.0, end_jd=2455113.0, years=10.0)

    assert p.is_active_at(2451545.0) is True       # exactly at start
    assert p.is_active_at(2453000.0) is True       # mid-period
    assert p.is_active_at(2455113.0) is False      # exactly at end — excluded
    assert p.is_active_at(2455113.1) is False      # past end
    assert p.is_active_at(2451544.9) is False      # before start


# ---------------------------------------------------------------------------
# Phase 3 inspectability — ReleasingPeriod
# ---------------------------------------------------------------------------

def test_releasing_period_rejects_invalid_level() -> None:
    """ReleasingPeriod.__post_init__ rejects levels outside {1, 2, 3, 4}."""
    from moira.timelords import ReleasingPeriod

    with pytest.raises(ValueError, match="level must be 1"):
        ReleasingPeriod(level=0, sign="Aries", ruler="Mars",
                        start_jd=2451545.0, end_jd=2451546.0, years=1.0)

    with pytest.raises(ValueError, match="level must be 1"):
        ReleasingPeriod(level=5, sign="Aries", ruler="Mars",
                        start_jd=2451545.0, end_jd=2451546.0, years=1.0)


def test_releasing_period_rejects_invalid_sign() -> None:
    """ReleasingPeriod.__post_init__ rejects unknown sign names."""
    from moira.timelords import ReleasingPeriod

    with pytest.raises(ValueError, match="valid zodiac sign"):
        ReleasingPeriod(level=1, sign="Unicorn", ruler="Mars",
                        start_jd=2451545.0, end_jd=2451546.0, years=1.0)


def test_releasing_period_rejects_inverted_jd() -> None:
    """ReleasingPeriod.__post_init__ rejects end_jd <= start_jd."""
    from moira.timelords import ReleasingPeriod

    with pytest.raises(ValueError, match="end_jd must be greater than start_jd"):
        ReleasingPeriod(level=1, sign="Aries", ruler="Mars",
                        start_jd=2451546.0, end_jd=2451545.0, years=1.0)


def test_releasing_period_level_name() -> None:
    """level_name returns 'Level N' for levels 1 through 4."""
    from moira.timelords import ReleasingPeriod

    for lvl in (1, 2, 3, 4):
        p = ReleasingPeriod(level=lvl, sign="Taurus", ruler="Venus",
                            start_jd=2451545.0, end_jd=2451546.0, years=1.0)
        assert p.level_name == f"Level {lvl}"


def test_releasing_period_days_equals_jd_span() -> None:
    """days property returns end_jd - start_jd exactly."""
    from moira.timelords import ReleasingPeriod

    p = ReleasingPeriod(level=1, sign="Gemini", ruler="Mercury",
                        start_jd=2451545.0, end_jd=2451910.0, years=1.0)
    assert p.days == pytest.approx(365.0, abs=1e-12)


def test_releasing_period_is_active_at_boundary_semantics() -> None:
    """is_active_at uses half-open [start, end) interval."""
    from moira.timelords import ReleasingPeriod

    p = ReleasingPeriod(level=2, sign="Cancer", ruler="Moon",
                        start_jd=2451545.0, end_jd=2451915.0, years=1.0)

    assert p.is_active_at(2451545.0) is True       # exactly at start
    assert p.is_active_at(2451700.0) is True       # mid-period
    assert p.is_active_at(2451915.0) is False      # exactly at end — excluded
    assert p.is_active_at(2451544.9) is False      # before start


# ---------------------------------------------------------------------------
# Phase 4 doctrine / policy surface — TimelordComputationPolicy
# ---------------------------------------------------------------------------

def test_timelord_default_policy_is_frozen_sentinel() -> None:
    """DEFAULT_TIMELORD_POLICY is a frozen sentinel with expected defaults."""
    from moira.timelords import DEFAULT_TIMELORD_POLICY, TimelordComputationPolicy, DecennialPolicy

    assert isinstance(DEFAULT_TIMELORD_POLICY, TimelordComputationPolicy)
    assert DEFAULT_TIMELORD_POLICY.firdaria_year.year_days == pytest.approx(365.25)
    assert isinstance(DEFAULT_TIMELORD_POLICY.decennials, DecennialPolicy)
    assert DEFAULT_TIMELORD_POLICY.decennials.start_lord_basis == "sect_light"
    assert DEFAULT_TIMELORD_POLICY.decennials.sequence_mode == "zodiacal_from_sect_light"
    assert DEFAULT_TIMELORD_POLICY.decennials.subperiod_mode == "rotated_minor_months"
    assert DEFAULT_TIMELORD_POLICY.decennials.major_months == pytest.approx(129.0)
    assert DEFAULT_TIMELORD_POLICY.decennials.month_basis_days == pytest.approx(30.0)
    assert DEFAULT_TIMELORD_POLICY.decennials.deep_subdivision_method is None
    assert DEFAULT_TIMELORD_POLICY.zr_year.year_days == pytest.approx(360.0)


def test_timelord_policy_none_produces_same_output_as_default() -> None:
    """Passing policy=None produces identical results to the default policy."""
    from moira.timelords import firdaria, DEFAULT_TIMELORD_POLICY

    p_none    = firdaria(2451545.0, is_day_chart=True)
    p_default = firdaria(2451545.0, is_day_chart=True, policy=DEFAULT_TIMELORD_POLICY)

    assert len(p_none) == len(p_default)
    for a, b in zip(p_none, p_default):
        assert a.start_jd == pytest.approx(b.start_jd, abs=1e-9)
        assert a.end_jd   == pytest.approx(b.end_jd,   abs=1e-9)


def test_decennials_policy_none_produces_same_output_as_default() -> None:
    """Passing policy=None preserves the default admitted Decennials doctrine."""
    from moira.timelords import decennials, DEFAULT_TIMELORD_POLICY

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    p_none = decennials(2451545.0, natal_positions, True)
    p_default = decennials(2451545.0, natal_positions, True, policy=DEFAULT_TIMELORD_POLICY)

    assert len(p_none) == len(p_default)
    for a, b in zip(p_none, p_default):
        assert a.start_jd == pytest.approx(b.start_jd, abs=1e-9)
        assert a.end_jd == pytest.approx(b.end_jd, abs=1e-9)
        assert a.month_basis_days == pytest.approx(b.month_basis_days, abs=1e-12)
        assert a.major_month_total == pytest.approx(b.major_month_total, abs=1e-12)


def test_firdaria_policy_year_days_scales_period_boundaries() -> None:
    """Overriding firdaria_year.year_days scales Firdaria period boundaries."""
    from moira.timelords import firdaria, FirdarYearPolicy, TimelordComputationPolicy

    pol_julian  = TimelordComputationPolicy(firdaria_year=FirdarYearPolicy(year_days=365.25))
    pol_savana  = TimelordComputationPolicy(firdaria_year=FirdarYearPolicy(year_days=360.0))

    p_julian = firdaria(2451545.0, is_day_chart=True, policy=pol_julian)
    p_savana = firdaria(2451545.0, is_day_chart=True, policy=pol_savana)

    # The last period's end JD should differ proportionally
    end_julian = p_julian[-1].end_jd - p_julian[0].start_jd
    end_savana = p_savana[-1].end_jd - p_savana[0].start_jd
    assert end_julian != pytest.approx(end_savana, rel=1e-6)
    assert end_julian / end_savana == pytest.approx(365.25 / 360.0, rel=1e-6)


def test_zr_policy_year_days_scales_period_boundaries() -> None:
    """Overriding zr_year.year_days scales Zodiacal Releasing period boundaries."""
    from moira.timelords import zodiacal_releasing, ZRYearPolicy, TimelordComputationPolicy

    pol_360 = TimelordComputationPolicy(zr_year=ZRYearPolicy(year_days=360.0))
    pol_365 = TimelordComputationPolicy(zr_year=ZRYearPolicy(year_days=365.25))

    periods_360 = [p for p in zodiacal_releasing(0.0, 2451545.0, levels=1, policy=pol_360) if p.level == 1]
    periods_365 = [p for p in zodiacal_releasing(0.0, 2451545.0, levels=1, policy=pol_365) if p.level == 1]

    first_360 = periods_360[0]
    first_365 = periods_365[0]

    span_360 = first_360.end_jd - first_360.start_jd
    span_365 = first_365.end_jd - first_365.start_jd
    assert span_360 != pytest.approx(span_365, rel=1e-6)
    assert span_365 / span_360 == pytest.approx(365.25 / 360.0, rel=1e-6)


def test_timelord_policy_rejects_non_positive_year_days() -> None:
    """_validate_timelord_policy raises ValueError for non-positive year_days."""
    from moira.timelords import FirdarYearPolicy, ZRYearPolicy, TimelordComputationPolicy, _validate_timelord_policy

    with pytest.raises(ValueError, match="firdaria_year.year_days must be positive"):
        _validate_timelord_policy(
            TimelordComputationPolicy(firdaria_year=FirdarYearPolicy(year_days=0.0))
        )

    with pytest.raises(ValueError, match="zr_year.year_days must be positive"):
        _validate_timelord_policy(
            TimelordComputationPolicy(zr_year=ZRYearPolicy(year_days=-1.0))
        )


def test_timelord_policy_rejects_unadmitted_decennials_variants() -> None:
    """Phase 4 keeps deferred Decennials variants unselectable."""
    from moira.timelords import DecennialPolicy, TimelordComputationPolicy, _validate_timelord_policy

    with pytest.raises(ValueError, match="start_lord_basis must remain 'sect_light'"):
        _validate_timelord_policy(
            TimelordComputationPolicy(decennials=DecennialPolicy(start_lord_basis="ascendant"))
        )

    with pytest.raises(ValueError, match="sequence_mode must remain 'zodiacal_from_sect_light'"):
        _validate_timelord_policy(
            TimelordComputationPolicy(decennials=DecennialPolicy(sequence_mode="calendar_order"))
        )

    with pytest.raises(ValueError, match="subperiod_mode must remain 'rotated_minor_months'"):
        _validate_timelord_policy(
            TimelordComputationPolicy(decennials=DecennialPolicy(subperiod_mode="equal_months"))
        )

    with pytest.raises(ValueError, match="major_months must remain 129"):
        _validate_timelord_policy(
            TimelordComputationPolicy(decennials=DecennialPolicy(major_months=120.0))
        )

    with pytest.raises(ValueError, match="month_basis_days must remain 30.0"):
        _validate_timelord_policy(
            TimelordComputationPolicy(decennials=DecennialPolicy(month_basis_days=29.5))
        )

    with pytest.raises(ValueError, match="deep_subdivision_method must be 'valens', 'hephaistio', or None"):
        _validate_timelord_policy(
            TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="firmicus"))
        )


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization tests
# ---------------------------------------------------------------------------

def test_group_firdaria_produces_one_group_per_major_period() -> None:
    """group_firdaria returns exactly one FirdarMajorGroup per major period."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    majors = [p for p in periods if p.level == 1]
    groups = group_firdaria(periods)
    assert len(groups) == len(majors)


def test_group_firdaria_major_planets_match_sequence() -> None:
    """FirdarMajorGroup.major.planet matches the Firdaria diurnal sequence order."""
    from moira.timelords import firdaria, group_firdaria, FIRDARIA_DIURNAL
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    groups = group_firdaria(periods)
    expected_planets = [seq[0] for seq in FIRDARIA_DIURNAL]
    actual_planets = [g.major.planet for g in groups]
    assert actual_planets == expected_planets


def test_group_firdaria_non_node_majors_have_seven_subs() -> None:
    """Each non-node major group has exactly 7 sub-periods."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    groups = group_firdaria(periods)
    for g in groups:
        if not g.major.is_node_period:
            assert g.sub_count == 7, (
                f"{g.major.planet} major has {g.sub_count} subs, expected 7"
            )


def test_group_firdaria_node_majors_have_no_subs_by_default() -> None:
    """Node major groups have empty subs when node sub-periods not requested."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True, include_node_subperiods=False)
    groups = group_firdaria(periods)
    node_groups = [g for g in groups if g.major.is_node_period]
    assert node_groups, "expected at least one node major in the sequence"
    for g in node_groups:
        assert g.sub_count == 0
        assert not g.has_subs


def test_group_firdaria_active_sub_at_returns_correct_period() -> None:
    """FirdarMajorGroup.active_sub_at returns the sub-period active at a given JD."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    groups = group_firdaria(periods)
    non_node = next(g for g in groups if g.has_subs)
    first_sub = non_node.subs[0]
    mid_jd = (first_sub.start_jd + first_sub.end_jd) / 2.0
    result = non_node.active_sub_at(mid_jd)
    assert result is not None
    assert result.planet == first_sub.planet


def test_group_firdaria_active_sub_at_returns_none_outside_major() -> None:
    """FirdarMajorGroup.active_sub_at returns None for a JD outside the major."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    groups = group_firdaria(periods)
    non_node = next(g for g in groups if g.has_subs)
    before_major = non_node.major.start_jd - 1.0
    assert non_node.active_sub_at(before_major) is None


def test_firdar_major_group_rejects_non_level1_major() -> None:
    """FirdarMajorGroup raises ValueError when major is not a level-1 period."""
    from moira.timelords import firdaria, FirdarMajorGroup
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    sub_period = next(p for p in periods if p.level == 2)
    with pytest.raises(ValueError, match="level-1"):
        FirdarMajorGroup(major=sub_period, subs=[])


def test_group_decennials_produces_one_group_per_major_period() -> None:
    """group_decennials returns exactly one group per Decennials major period."""
    from moira.timelords import decennials, group_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True)
    majors = [p for p in periods if p.level == 1]
    groups = group_decennials(periods)
    assert len(groups) == len(majors)


def test_group_decennials_major_planets_match_sequence() -> None:
    """DecennialMajorGroup majors preserve the generated Decennials sequence."""
    from moira.timelords import decennials, group_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    groups = group_decennials(decennials(2451545.0, natal_positions, True))
    assert [g.major.planet for g in groups] == ["Sun", "Mercury", "Venus", "Mars", "Moon", "Jupiter", "Saturn"]


def test_group_decennials_each_major_has_seven_subs() -> None:
    """The admitted L2 Decennials doctrine gives every major exactly seven sub-periods."""
    from moira.timelords import decennials, group_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    groups = group_decennials(decennials(2451545.0, natal_positions, True))
    assert all(group.sub_count == 7 for group in groups)
    assert all(group.has_subs for group in groups)


def test_group_decennials_active_sub_at_returns_correct_period() -> None:
    """DecennialMajorGroup.active_sub_at returns the sub-period active at a given JD."""
    from moira.timelords import decennials, group_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    first_group = group_decennials(decennials(2451545.0, natal_positions, True))[0]
    first_sub = first_group.subs[0]
    mid_jd = (first_sub.start_jd + first_sub.end_jd) / 2.0
    result = first_group.active_sub_at(mid_jd)
    assert result is not None
    assert result.planet == first_sub.planet


def test_decennial_major_group_rejects_non_level1_major() -> None:
    """DecennialMajorGroup raises ValueError when major is not a level-1 period."""
    from moira.timelords import decennials, DecennialMajorGroup

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True)
    sub_period = next(p for p in periods if p.level == 2)
    with pytest.raises(ValueError, match="level-1"):
        DecennialMajorGroup(major=sub_period, subs=[])


def test_group_releasing_level1_groups_have_level2_subs() -> None:
    """group_releasing Level 1 groups each have Level 2 sub-groups."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=2)
    groups = group_releasing(periods)
    assert groups, "expected at least one Level 1 group"
    for g in groups:
        assert g.level == 1
        assert g.has_sub_groups


def test_group_releasing_sub_groups_have_correct_level() -> None:
    """ZRPeriodGroup sub-groups are one level deeper than their parent."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=3)
    groups = group_releasing(periods)
    for g1 in groups:
        assert g1.level == 1
        for g2 in g1.sub_groups:
            assert g2.level == 2
            for g3 in g2.sub_groups:
                assert g3.level == 3


def test_group_releasing_active_sub_at_returns_correct_group() -> None:
    """ZRPeriodGroup.active_sub_at returns the sub-group active at the given JD."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=2)
    groups = group_releasing(periods)
    g1 = next(g for g in groups if g.has_sub_groups)
    first_sub = g1.sub_groups[0]
    mid_jd = (first_sub.period.start_jd + first_sub.period.end_jd) / 2.0
    result = g1.active_sub_at(mid_jd)
    assert result is not None
    assert result.period.sign == first_sub.period.sign


def test_group_releasing_empty_input_returns_empty() -> None:
    """group_releasing returns an empty list for empty input."""
    from moira.timelords import group_releasing
    assert group_releasing([]) == []


# ---------------------------------------------------------------------------
# Phase 6 — Relational Hardening / Inspectability tests
# ---------------------------------------------------------------------------

# -- FirdarMajorGroup hardening and subset properties --

def test_firdar_major_group_is_complete_for_non_node_majors() -> None:
    """FirdarMajorGroup.is_complete is True for a 7-sub non-node major."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    groups = group_firdaria(firdaria(JD_BIRTH, is_day_chart=True))
    non_node = next(g for g in groups if not g.major.is_node_period)
    assert non_node.is_complete


def test_firdar_major_group_is_complete_for_node_major_with_no_subs() -> None:
    """FirdarMajorGroup.is_complete is True for a node major with 0 subs."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    groups = group_firdaria(firdaria(JD_BIRTH, is_day_chart=True, include_node_subperiods=False))
    node_group = next(g for g in groups if g.major.is_node_period)
    assert node_group.is_complete


def test_firdar_major_group_luminary_subs_count() -> None:
    """FirdarMajorGroup.luminary_subs contains exactly the Sun and Moon sub-periods."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    groups = group_firdaria(firdaria(JD_BIRTH, is_day_chart=True))
    non_node = next(g for g in groups if not g.major.is_node_period)
    luminaries = non_node.luminary_subs
    assert all(p.planet in {"Sun", "Moon"} for p in luminaries)
    assert len(luminaries) == 2  # each non-node major has one Sun sub and one Moon sub


def test_firdar_major_group_node_subs_are_node_periods() -> None:
    """FirdarMajorGroup.node_subs contains only is_node_period sub-periods."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    groups = group_firdaria(firdaria(JD_BIRTH, is_day_chart=True))
    non_node = next(g for g in groups if not g.major.is_node_period)
    for p in non_node.node_subs:
        assert p.is_node_period


def test_firdar_major_group_planet_subs_are_neither_luminary_nor_node() -> None:
    """FirdarMajorGroup.planet_subs excludes luminaries and nodes."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    groups = group_firdaria(firdaria(JD_BIRTH, is_day_chart=True))
    non_node = next(g for g in groups if not g.major.is_node_period)
    for p in non_node.planet_subs:
        assert not p.is_node_period
        assert p.planet not in {"Sun", "Moon"}


def test_firdar_major_group_subset_partition() -> None:
    """luminary_subs + node_subs + planet_subs partitions all subs completely."""
    from moira.timelords import firdaria, group_firdaria
    JD_BIRTH = 2451545.0
    groups = group_firdaria(firdaria(JD_BIRTH, is_day_chart=True))
    for g in groups:
        total = len(g.luminary_subs) + len(g.node_subs) + len(g.planet_subs)
        assert total == g.sub_count


def test_firdar_major_group_rejects_out_of_order_subs() -> None:
    """FirdarMajorGroup raises ValueError when subs are not in chronological order."""
    from moira.timelords import firdaria, FirdarMajorGroup
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    major = next(p for p in periods if p.level == 1 and not p.is_node_period)
    subs = [p for p in periods if p.level == 2 and p.major_planet == major.planet]
    reversed_subs = list(reversed(subs))
    with pytest.raises(ValueError, match="chronological order"):
        FirdarMajorGroup(major=major, subs=reversed_subs)


def test_decennial_major_group_is_complete_for_admitted_output() -> None:
    """DecennialMajorGroup.is_complete is True for the admitted seven-sub doctrine."""
    from moira.timelords import decennials, group_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    groups = group_decennials(decennials(2451545.0, natal_positions, True))
    assert all(group.is_complete for group in groups)


def test_decennial_major_group_luminary_and_planetary_subs_partition_subs() -> None:
    """Luminary and planetary Decennials subsets partition the seven sub-periods."""
    from moira.timelords import decennials, group_decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    first_group = group_decennials(decennials(2451545.0, natal_positions, True))[0]
    assert {sub.planet for sub in first_group.luminary_subs} == {"Sun", "Moon"}
    assert {sub.planet for sub in first_group.planetary_subs} == {"Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    assert len(first_group.luminary_subs) + len(first_group.planetary_subs) == first_group.sub_count


def test_decennial_major_group_rejects_wrong_major_truth_and_unordered_subs() -> None:
    """DecennialMajorGroup hardens major truth and chronological ordering."""
    from moira.timelords import decennials, group_decennials, DecennialMajorGroup

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    groups = group_decennials(decennials(2451545.0, natal_positions, True))
    first_group = groups[0]
    other_group = groups[1]

    with pytest.raises(ValueError, match="must preserve major_planet 'Sun'"):
        DecennialMajorGroup(major=first_group.major, subs=[other_group.subs[0]])

    reversed_subs = list(reversed(first_group.subs))
    with pytest.raises(ValueError, match="chronological order"):
        DecennialMajorGroup(major=first_group.major, subs=reversed_subs)


def test_group_decennials_builds_recursive_sub_groups_for_deep_output() -> None:
    """Deep Decennials output groups into one-level-at-a-time recursive sub-groups."""
    from moira.timelords import decennials, group_decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    groups = group_decennials(decennials(2451545.0, natal_positions, True, levels=4, policy=policy))

    first_group = groups[0]
    assert first_group.has_sub_groups
    assert len(first_group.sub_groups) == 7
    assert first_group.sub_groups[0].level == 2
    assert first_group.sub_groups[0].has_sub_groups
    assert first_group.sub_groups[0].sub_groups[0].level == 3
    assert first_group.sub_groups[0].sub_groups[0].has_sub_groups
    assert first_group.sub_groups[0].sub_groups[0].sub_groups[0].level == 4
    assert first_group.sub_groups[0].sub_groups[0].sub_groups[0].is_leaf


def test_decennial_major_group_all_periods_flat_includes_deep_descendants() -> None:
    """DecennialMajorGroup.all_periods_flat returns the major and all nested descendants."""
    from moira.timelords import decennials, group_decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="hephaistio"))
    first_group = group_decennials(decennials(2451545.0, natal_positions, True, levels=3, policy=policy))[0]

    flat = first_group.all_periods_flat()

    assert flat[0] == first_group.major
    assert any(period.level == 3 for period in flat)
    assert len(flat) == 1 + 7 + 49


def test_decennial_major_group_active_sub_group_at_returns_recursive_node() -> None:
    """DecennialMajorGroup.active_sub_group_at returns the immediate recursive node active at jd."""
    from moira.timelords import decennials, group_decennials, DecennialPolicy, TimelordComputationPolicy

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    first_group = group_decennials(decennials(2451545.0, natal_positions, True, levels=4, policy=policy))[0]
    first_sub_group = first_group.sub_groups[0]
    mid_jd = (first_sub_group.period.start_jd + first_sub_group.period.end_jd) / 2.0

    result = first_group.active_sub_group_at(mid_jd)

    assert result is not None
    assert result.period == first_sub_group.period


def test_decennial_period_group_rejects_invalid_child_level_or_containment() -> None:
    """DecennialPeriodGroup hardens one-level nesting and parent containment."""
    from moira.timelords import decennials, group_decennials, DecennialPeriodGroup, DecennialPolicy, TimelordComputationPolicy
    import dataclasses

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }
    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    first_group = group_decennials(decennials(2451545.0, natal_positions, True, levels=4, policy=policy))[0]
    l2_group = first_group.sub_groups[0]
    l4_group = l2_group.sub_groups[0].sub_groups[0]

    with pytest.raises(ValueError, match="exactly one level deeper"):
        DecennialPeriodGroup(period=l2_group.period, sub_groups=[l4_group])

    shifted = dataclasses.replace(l2_group.sub_groups[0].period, start_jd=l2_group.period.start_jd - 1.0)
    with pytest.raises(ValueError, match="starts before parent period"):
        DecennialPeriodGroup(
            period=l2_group.period,
            sub_groups=[DecennialPeriodGroup(period=shifted, sub_groups=[])]
        )


# -- ZRPeriodGroup hardening and inspectability --

def test_zr_period_group_is_leaf_at_deepest_level() -> None:
    """ZRPeriodGroup.is_leaf is True for groups at the deepest generated level."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=2)
    groups = group_releasing(periods)
    for g1 in groups:
        for g2 in g1.sub_groups:
            assert g2.is_leaf


def test_zr_period_group_is_not_leaf_when_has_subs() -> None:
    """ZRPeriodGroup.is_leaf is False for groups that have sub-groups."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=2)
    groups = group_releasing(periods)
    for g1 in groups:
        assert not g1.is_leaf


def test_zr_period_group_angularity_class_matches_period() -> None:
    """ZRPeriodGroup.angularity_class matches the underlying period's angularity_class."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=2)
    groups = group_releasing(periods)
    for g1 in groups:
        assert g1.angularity_class == g1.period.angularity_class


def test_zr_period_group_all_periods_flat_count() -> None:
    """ZRPeriodGroup.all_periods_flat() returns all L1 + L2 periods for a Level 1 group."""
    from moira.timelords import zodiacal_releasing, group_releasing
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=2)
    groups = group_releasing(periods)
    g1 = groups[0]
    flat = g1.all_periods_flat()
    assert flat[0] == g1.period
    assert len(flat) == 1 + len(g1.sub_groups)


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition tests
# ---------------------------------------------------------------------------

def test_firdar_condition_profile_fields_match_period() -> None:
    """firdar_condition_profile produces a profile whose fields match the source period."""
    from moira.timelords import firdaria, firdar_condition_profile
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    major = next(p for p in periods if p.level == 1)
    profile = firdar_condition_profile(major)
    assert profile.planet      == major.planet
    assert profile.level       == major.level
    assert profile.level_name  == major.level_name
    assert profile.is_major    == major.is_major
    assert profile.is_node_period == major.is_node_period
    assert profile.sequence_kind  == major.sequence_kind
    assert profile.is_day_chart   == major.is_day_chart
    assert profile.years  == pytest.approx(major.years)
    assert profile.days   == pytest.approx(major.days)


def test_firdar_condition_profile_lord_type_luminary() -> None:
    """firdar_condition_profile assigns 'luminary' lord_type to Sun and Moon periods."""
    from moira.timelords import firdaria, firdar_condition_profile
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    for p in periods:
        if p.planet in {"Sun", "Moon"}:
            assert firdar_condition_profile(p).lord_type == "luminary"


def test_firdar_condition_profile_lord_type_node() -> None:
    """firdar_condition_profile assigns 'node' lord_type to node periods."""
    from moira.timelords import firdaria, firdar_condition_profile
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    for p in periods:
        if p.is_node_period:
            assert firdar_condition_profile(p).lord_type == "node"


def test_firdar_condition_profile_lord_type_planet() -> None:
    """firdar_condition_profile assigns 'planet' lord_type to the five traditional planets."""
    from moira.timelords import firdaria, firdar_condition_profile
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    for p in periods:
        if not p.is_node_period and p.planet not in {"Sun", "Moon"}:
            assert firdar_condition_profile(p).lord_type == "planet"


def test_firdar_condition_profile_sub_period_carries_major_planet() -> None:
    """firdar_condition_profile on a sub-period has major_planet set correctly."""
    from moira.timelords import firdaria, firdar_condition_profile
    JD_BIRTH = 2451545.0
    periods = firdaria(JD_BIRTH, is_day_chart=True)
    sub = next(p for p in periods if p.level == 2)
    profile = firdar_condition_profile(sub)
    assert profile.major_planet == sub.major_planet
    assert not profile.is_major


def test_decennial_condition_profile_fields_match_period() -> None:
    """decennial_condition_profile preserves the source period truth."""
    from moira.timelords import decennials, decennial_condition_profile

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    major = next(p for p in decennials(2451545.0, natal_positions, True) if p.level == 1 and p.planet == "Mercury")
    profile = decennial_condition_profile(major)

    assert profile.planet == major.planet
    assert profile.level == major.level
    assert profile.level_name == major.level_name
    assert profile.is_major == major.is_major
    assert profile.lord_type == "planet"
    assert profile.sequence_kind == major.sequence_kind
    assert profile.major_planet == major.major_planet
    assert profile.parent_planet == major.parent_planet
    assert profile.parent_level == major.parent_level
    assert profile.ancestor_planets == major.ancestor_planets
    assert profile.effective_major_planet == major.effective_major_planet
    assert profile.is_day_chart == major.is_day_chart
    assert profile.sect_light == major.sect_light
    assert profile.major_index == major.major_index
    assert profile.sub_index == major.sub_index
    assert profile.sequence_position == major.sequence_position
    assert profile.deep_subdivision_method == major.deep_subdivision_method
    assert profile.years == pytest.approx(major.years)
    assert profile.months == pytest.approx(major.months)
    assert profile.days == pytest.approx(major.days)
    assert profile.month_basis_days == pytest.approx(major.month_basis_days)


def test_decennial_condition_profile_sub_period_carries_major_truth() -> None:
    """Sub-period Decennials profiles preserve major lord and sect-light truth."""
    from moira.timelords import decennials, decennial_condition_profile

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    sub = next(
        p for p in decennials(2451545.0, natal_positions, False)
        if p.level == 2 and p.major_planet == "Moon" and p.planet == "Jupiter"
    )
    profile = decennial_condition_profile(sub)

    assert not profile.is_major
    assert profile.major_planet == "Moon"
    assert profile.effective_major_planet == "Moon"
    assert profile.sect_light == "Moon"
    assert profile.sequence_position == 2
    assert profile.lord_type == "planet"


def test_decennial_condition_profile_lord_type_luminary() -> None:
    """Decennial luminaries profile as luminaries."""
    from moira.timelords import decennials, decennial_condition_profile

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(2451545.0, natal_positions, True)
    for period in periods:
        if period.planet in {"Sun", "Moon"}:
            assert decennial_condition_profile(period).lord_type == "luminary"


def test_decennial_condition_profile_deep_period_preserves_lineage_truth() -> None:
    """Deep Decennials profiles preserve parent lineage and deep-method truth."""
    from moira.timelords import (
        DecennialPolicy,
        TimelordComputationPolicy,
        decennials,
        decennial_condition_profile,
    )

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    deep_period = next(
        period
        for period in decennials(2451545.0, natal_positions, True, levels=4, policy=policy)
        if period.level == 4
    )
    profile = decennial_condition_profile(deep_period)

    assert profile.level == 4
    assert profile.parent_planet == deep_period.parent_planet
    assert profile.parent_level == 3
    assert profile.ancestor_planets == deep_period.ancestor_planets
    assert profile.effective_major_planet == deep_period.major_planet
    assert profile.deep_subdivision_method == "valens"
    assert profile.month_basis_days == pytest.approx(30.0)


def test_zr_condition_profile_fields_match_period() -> None:
    """zr_condition_profile produces a profile whose fields match the source period."""
    from moira.timelords import zodiacal_releasing, zr_condition_profile
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=1)
    p = periods[0]
    profile = zr_condition_profile(p)
    assert profile.sign                    == p.sign
    assert profile.ruler                   == p.ruler
    assert profile.level                   == p.level
    assert profile.level_name              == p.level_name
    assert profile.lot_name                == p.lot_name
    assert profile.days                    == pytest.approx(p.days)
    assert profile.is_loosing_of_bond      == p.is_loosing_of_bond
    assert profile.is_peak_period          == p.is_peak_period
    assert profile.angularity_from_fortune == p.angularity_from_fortune
    assert profile.angularity_class        == p.angularity_class
    assert profile.use_loosing_of_bond     == p.use_loosing_of_bond


def test_zr_condition_profile_angularity_class_none_for_non_peak() -> None:
    """zr_condition_profile has None angularity_class for non-peak periods."""
    from moira.timelords import zodiacal_releasing, zr_condition_profile
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0  # Fortune in Gemini → house 1 from itself, angular
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=1)
    non_peak = [p for p in periods if not p.is_peak_period]
    assert non_peak, "expected at least one non-peak period in the sequence"
    for p in non_peak:
        assert zr_condition_profile(p).angularity_class is None


def test_zr_condition_profile_level_range() -> None:
    """zr_condition_profile.level is within 1–4 for all generated periods."""
    from moira.timelords import zodiacal_releasing, zr_condition_profile
    JD_BIRTH = 2451545.0
    FORTUNE_LON = 120.0
    periods = zodiacal_releasing(FORTUNE_LON, JD_BIRTH, levels=4)
    for p in periods:
        profile = zr_condition_profile(p)
        assert 1 <= profile.level <= 4


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence tests
# ---------------------------------------------------------------------------

_P8_JD_BIRTH   = 2451545.0
_P8_FORTUNE    = 120.0

# -- FirdarSequenceProfile --

def test_firdar_sequence_profile_major_count_matches_sequence() -> None:
    """FirdarSequenceProfile.major_count equals the number of major periods."""
    from moira.timelords import firdaria, firdar_sequence_profile, FIRDARIA_DIURNAL
    periods = firdaria(_P8_JD_BIRTH, is_day_chart=True)
    agg = firdar_sequence_profile(periods)
    assert agg.major_count == len(FIRDARIA_DIURNAL)


def test_firdar_sequence_profile_lord_type_counts_sum_to_major_count() -> None:
    """lord-type counts in FirdarSequenceProfile sum to major_count."""
    from moira.timelords import firdaria, firdar_sequence_profile
    agg = firdar_sequence_profile(firdaria(_P8_JD_BIRTH, is_day_chart=True))
    assert agg.luminary_major_count + agg.planet_major_count + agg.node_major_count \
           == agg.major_count


def test_firdar_sequence_profile_total_years_is_75() -> None:
    """FirdarSequenceProfile.total_major_years sums to 75 for a complete sequence."""
    from moira.timelords import firdaria, firdar_sequence_profile
    agg = firdar_sequence_profile(firdaria(_P8_JD_BIRTH, is_day_chart=True))
    assert agg.total_major_years == pytest.approx(75.0, abs=1e-9)


def test_firdar_sequence_profile_has_node_majors_diurnal() -> None:
    """FirdarSequenceProfile.has_node_majors is True for the diurnal sequence."""
    from moira.timelords import firdaria, firdar_sequence_profile
    agg = firdar_sequence_profile(firdaria(_P8_JD_BIRTH, is_day_chart=True))
    assert agg.has_node_majors
    assert agg.node_major_count == 2  # North Node + South Node


def test_firdar_sequence_profile_sequence_kind_is_diurnal() -> None:
    """FirdarSequenceProfile.sequence_kind is DIURNAL for a day-chart sequence."""
    from moira.timelords import firdaria, firdar_sequence_profile, FirdarSequenceKind
    agg = firdar_sequence_profile(firdaria(_P8_JD_BIRTH, is_day_chart=True))
    assert agg.sequence_kind == FirdarSequenceKind.DIURNAL


def test_firdar_sequence_profile_rejects_mismatched_count() -> None:
    """FirdarSequenceProfile raises ValueError when major_count does not match profiles."""
    from moira.timelords import firdaria, firdar_sequence_profile, FirdarSequenceProfile
    agg = firdar_sequence_profile(firdaria(_P8_JD_BIRTH, is_day_chart=True))
    with pytest.raises(ValueError, match="major_count must equal"):
        FirdarSequenceProfile(
            profiles             = agg.profiles,
            major_count          = agg.major_count + 1,  # wrong
            luminary_major_count = agg.luminary_major_count,
            planet_major_count   = agg.planet_major_count,
            node_major_count     = agg.node_major_count,
            total_major_years    = agg.total_major_years,
            sequence_kind        = agg.sequence_kind,
        )


# -- DecennialSequenceProfile --

def test_decennial_sequence_profile_major_count_matches_sequence() -> None:
    """DecennialSequenceProfile.major_count equals the seven-major admitted cycle."""
    from moira.timelords import decennials, decennial_sequence_profile

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    agg = decennial_sequence_profile(decennials(_P8_JD_BIRTH, natal_positions, True))
    assert agg.major_count == 7
    assert agg.profile_count == 56
    assert agg.level_count_map == {1: 7, 2: 49}
    assert agg.deepest_level == 2


def test_decennial_sequence_profile_lord_type_counts_sum_to_major_count() -> None:
    """Decennial luminary and planetary major counts sum to the sequence major count."""
    from moira.timelords import decennials, decennial_sequence_profile

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    agg = decennial_sequence_profile(decennials(_P8_JD_BIRTH, natal_positions, True))
    assert agg.luminary_major_count + agg.planetary_major_count == agg.major_count


def test_decennial_sequence_profile_totals_and_doctrine_truth() -> None:
    """Decennial aggregate preserves total years, months, sequence kind, and sect light."""
    from moira.timelords import decennials, decennial_sequence_profile, DecennialSequenceKind

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    agg = decennial_sequence_profile(decennials(_P8_JD_BIRTH, natal_positions, True))
    assert agg.total_major_years == pytest.approx(75.25, abs=1e-9)
    assert agg.total_major_months == pytest.approx(903.0, abs=1e-9)
    assert agg.sequence_kind == DecennialSequenceKind.DIURNAL_SOLAR
    assert agg.sect_light == "Sun"
    assert agg.deep_subdivision_method is None


def test_decennial_sequence_profile_deep_output_preserves_level_map_and_method() -> None:
    """Deep Decennials aggregates preserve total profile counts, level map, and method truth."""
    from moira.timelords import (
        DecennialPolicy,
        TimelordComputationPolicy,
        decennials,
        decennial_sequence_profile,
    )

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    agg = decennial_sequence_profile(decennials(_P8_JD_BIRTH, natal_positions, True, levels=4, policy=policy))

    assert agg.major_count == 7
    assert agg.profile_count == 2800
    assert agg.level_count_map == {1: 7, 2: 49, 3: 343, 4: 2401}
    assert agg.deepest_level == 4
    assert agg.deep_subdivision_method == "valens"


def test_decennial_sequence_profile_rejects_mismatched_count() -> None:
    """DecennialSequenceProfile raises ValueError when major_count does not match level-1 profiles."""
    from moira.timelords import decennials, decennial_sequence_profile, DecennialSequenceProfile

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    agg = decennial_sequence_profile(decennials(_P8_JD_BIRTH, natal_positions, True))
    with pytest.raises(ValueError, match="major_count must equal the number of level-1 profiles"):
        DecennialSequenceProfile(
            profiles=agg.profiles,
            major_count=agg.major_count + 1,
            luminary_major_count=agg.luminary_major_count,
            planetary_major_count=agg.planetary_major_count,
            total_major_years=agg.total_major_years,
            total_major_months=agg.total_major_months,
            sequence_kind=agg.sequence_kind,
            sect_light=agg.sect_light,
            level_count_map=agg.level_count_map,
            deepest_level=agg.deepest_level,
            deep_subdivision_method=agg.deep_subdivision_method,
        )


# -- ZRSequenceProfile --

def test_zr_sequence_profile_period_count_is_12() -> None:
    """ZRSequenceProfile has 12 Level-1 periods (one per sign)."""
    from moira.timelords import zodiacal_releasing, zr_sequence_profile
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=1)
    agg = zr_sequence_profile(periods, level=1)
    assert agg.period_count == 12


def test_zr_sequence_profile_angular_plus_succedent_plus_cadent_equals_peak() -> None:
    """In ZRSequenceProfile, angular+succedent+cadent equals peak_period_count."""
    from moira.timelords import zodiacal_releasing, zr_sequence_profile
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=1)
    agg = zr_sequence_profile(periods, level=1)
    assert agg.angular_count + agg.succedent_count + agg.cadent_count \
           == agg.peak_period_count


def test_zr_sequence_profile_non_peak_count_property() -> None:
    """ZRSequenceProfile.non_peak_count equals period_count minus peak_period_count."""
    from moira.timelords import zodiacal_releasing, zr_sequence_profile
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=1)
    agg = zr_sequence_profile(periods, level=1)
    assert agg.non_peak_count == agg.period_count - agg.peak_period_count


def test_zr_sequence_profile_total_years_is_129() -> None:
    """ZRSequenceProfile.total_years sums to 129 for the complete Level-1 sequence."""
    from moira.timelords import zodiacal_releasing, zr_sequence_profile, MINOR_YEARS
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=1)
    agg = zr_sequence_profile(periods, level=1)
    expected = float(sum(MINOR_YEARS.values()))
    assert agg.total_years == pytest.approx(expected, abs=1e-6)


def test_zr_sequence_profile_rejects_mismatched_period_count() -> None:
    """ZRSequenceProfile raises ValueError when period_count does not match profiles."""
    from moira.timelords import zodiacal_releasing, zr_sequence_profile, ZRSequenceProfile
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=1)
    agg = zr_sequence_profile(periods, level=1)
    with pytest.raises(ValueError, match="period_count must equal"):
        ZRSequenceProfile(
            profiles              = agg.profiles,
            period_count          = agg.period_count + 1,  # wrong
            peak_period_count     = agg.peak_period_count,
            loosing_of_bond_count = agg.loosing_of_bond_count,
            angular_count         = agg.angular_count,
            succedent_count       = agg.succedent_count,
            cadent_count          = agg.cadent_count,
            total_years           = agg.total_years,
        )


# ---------------------------------------------------------------------------
# Phase 9 — Network Intelligence tests
# ---------------------------------------------------------------------------

# -- FirdarActivePair --

def test_firdar_active_pair_major_profile_matches_active_major() -> None:
    """firdar_active_pair returns a pair whose major_profile.planet is the active major."""
    from moira.timelords import firdaria, firdar_active_pair
    periods = firdaria(_P8_JD_BIRTH, is_day_chart=True)
    first_major = next(p for p in periods if p.level == 1)
    mid_jd = (first_major.start_jd + first_major.end_jd) / 2.0
    pair = firdar_active_pair(periods, mid_jd)
    assert pair is not None
    assert pair.major_profile.planet == first_major.planet


def test_firdar_active_pair_has_sub_when_sub_exists() -> None:
    """firdar_active_pair.has_sub is True when sub-periods are generated."""
    from moira.timelords import firdaria, firdar_active_pair
    periods = firdaria(_P8_JD_BIRTH, is_day_chart=True)
    non_node_major = next(p for p in periods if p.level == 1 and not p.is_node_period)
    mid_jd = (non_node_major.start_jd + non_node_major.end_jd) / 2.0
    pair = firdar_active_pair(periods, mid_jd)
    assert pair is not None
    assert pair.has_sub


def test_firdar_active_pair_returns_none_outside_sequence() -> None:
    """firdar_active_pair returns None when jd is before the sequence starts."""
    from moira.timelords import firdaria, firdar_active_pair
    periods = firdaria(_P8_JD_BIRTH, is_day_chart=True)
    before_birth = _P8_JD_BIRTH - 1.0
    assert firdar_active_pair(periods, before_birth) is None


def test_firdar_active_pair_is_same_lord_when_major_sub_lord_identical() -> None:
    """FirdarActivePair.is_same_lord is True when major planet == sub planet."""
    from moira.timelords import firdaria, firdar_active_pair
    periods = firdaria(_P8_JD_BIRTH, is_day_chart=True)
    non_node_major = next(p for p in periods if p.level == 1 and not p.is_node_period)
    # First sub-period's lord is the major planet itself
    first_sub = next(
        p for p in periods
        if p.level == 2 and p.major_planet == non_node_major.planet
    )
    mid_jd = (first_sub.start_jd + first_sub.end_jd) / 2.0
    pair = firdar_active_pair(periods, mid_jd)
    assert pair is not None
    assert pair.is_same_lord


def test_firdar_active_pair_rejects_sub_as_major() -> None:
    """FirdarActivePair raises ValueError when major_profile is not level-1."""
    from moira.timelords import firdaria, firdar_condition_profile, FirdarActivePair
    periods = firdaria(_P8_JD_BIRTH, is_day_chart=True)
    sub = next(p for p in periods if p.level == 2)
    with pytest.raises(ValueError, match="level-1"):
        FirdarActivePair(
            major_profile=firdar_condition_profile(sub),
            sub_profile=None,
        )


# -- DecennialActivePair --

def test_decennial_active_pair_major_profile_matches_active_major() -> None:
    """decennial_active_pair returns a pair whose major_profile is the active major."""
    from moira.timelords import decennials, decennial_active_pair

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P8_JD_BIRTH, natal_positions, True)
    first_major = next(period for period in periods if period.level == 1)
    mid_jd = (first_major.start_jd + first_major.end_jd) / 2.0
    pair = decennial_active_pair(periods, mid_jd)
    assert pair is not None
    assert pair.major_profile.planet == first_major.planet


def test_decennial_active_pair_has_sub_when_sub_exists() -> None:
    """decennial_active_pair.has_sub is True when sub-periods are generated."""
    from moira.timelords import decennials, decennial_active_pair

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P8_JD_BIRTH, natal_positions, True)
    first_major = next(period for period in periods if period.level == 1)
    mid_jd = (first_major.start_jd + first_major.end_jd) / 2.0
    pair = decennial_active_pair(periods, mid_jd)
    assert pair is not None
    assert pair.has_sub


def test_decennial_active_pair_returns_none_outside_sequence() -> None:
    """decennial_active_pair returns None when jd is before the cycle start."""
    from moira.timelords import decennials, decennial_active_pair

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P8_JD_BIRTH, natal_positions, True)
    assert decennial_active_pair(periods, _P8_JD_BIRTH - 1.0) is None


def test_decennial_active_pair_is_same_lord_when_major_sub_identical() -> None:
    """DecennialActivePair relation predicates hold when the major lord repeats at L2."""
    from moira.timelords import decennials, decennial_active_pair

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P8_JD_BIRTH, natal_positions, True)
    first_sub = next(
        period for period in periods
        if period.level == 2 and period.major_planet == "Sun" and period.planet == "Sun"
    )
    mid_jd = (first_sub.start_jd + first_sub.end_jd) / 2.0
    pair = decennial_active_pair(periods, mid_jd)
    assert pair is not None
    assert pair.is_same_lord
    assert pair.is_same_lord_type
    assert pair.shares_sect_light


def test_decennial_active_pair_rejects_sub_as_major() -> None:
    """DecennialActivePair raises ValueError when major_profile is not level-1."""
    from moira.timelords import decennials, decennial_condition_profile, DecennialActivePair

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P8_JD_BIRTH, natal_positions, True)
    sub = next(period for period in periods if period.level == 2)
    with pytest.raises(ValueError, match="level-1"):
        DecennialActivePair(
            major_profile=decennial_condition_profile(sub),
            sub_profile=None,
        )


def test_decennial_active_path_returns_full_deep_lineage() -> None:
    """decennial_active_path returns one active profile per generated Decennials level."""
    from moira.timelords import (
        DecennialPolicy,
        TimelordComputationPolicy,
        decennial_active_path,
        decennials,
    )

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    periods = decennials(_P8_JD_BIRTH, natal_positions, True, levels=4, policy=policy)
    active_leaf = next(period for period in periods if period.level == 4)
    mid_jd = (active_leaf.start_jd + active_leaf.end_jd) / 2.0

    path = decennial_active_path(periods, mid_jd)

    assert path is not None
    assert [profile.level for profile in path.profiles] == [1, 2, 3, 4]
    assert path.major_profile.level == 1
    assert path.deepest_profile.level == 4
    assert path.deepest_level == 4
    assert path.has_deep_subdivision


def test_decennial_active_path_returns_none_outside_sequence() -> None:
    """decennial_active_path returns None when jd falls outside the Decennials cycle."""
    from moira.timelords import decennial_active_path, decennials

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P8_JD_BIRTH, natal_positions, True)
    assert decennial_active_path(periods, _P8_JD_BIRTH - 1.0) is None


def test_decennial_active_path_rejects_non_contiguous_levels() -> None:
    """DecennialActivePath rejects profile tuples that skip a level."""
    from moira.timelords import (
        DecennialActivePath,
        DecennialPolicy,
        TimelordComputationPolicy,
        decennial_condition_profile,
        decennials,
    )

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    periods = decennials(_P8_JD_BIRTH, natal_positions, True, levels=4, policy=policy)
    level1 = decennial_condition_profile(next(period for period in periods if period.level == 1))
    level3 = decennial_condition_profile(next(period for period in periods if period.level == 3))

    with pytest.raises(ValueError, match="advance one level at a time"):
        DecennialActivePath(profiles=(level1, level3))


def test_decennial_subsystem_surfaces_agree_on_active_deep_state() -> None:
    """Current, grouped, aggregate, pair, and path Decennials surfaces agree on one deep active instant."""
    from moira.timelords import (
        DecennialPolicy,
        TimelordComputationPolicy,
        current_decennials,
        decennial_active_pair,
        decennial_active_path,
        decennial_sequence_profile,
        decennials,
        group_decennials,
    )

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    policy = TimelordComputationPolicy(decennials=DecennialPolicy(deep_subdivision_method="valens"))
    periods = decennials(_P8_JD_BIRTH, natal_positions, True, levels=4, policy=policy)
    groups = group_decennials(periods)
    aggregate = decennial_sequence_profile(periods)
    active_leaf = next(period for period in periods if period.level == 4)
    mid_jd = (active_leaf.start_jd + active_leaf.end_jd) / 2.0

    major, leaf = current_decennials(_P8_JD_BIRTH, natal_positions, True, mid_jd, levels=4, policy=policy)
    pair = decennial_active_pair(periods, mid_jd)
    path = decennial_active_path(periods, mid_jd)
    group = next(item for item in groups if item.major.planet == major.planet)

    assert pair is not None
    assert path is not None
    assert aggregate.level_count_map == {1: 7, 2: 49, 3: 343, 4: 2401}
    assert aggregate.deepest_level == 4
    assert group.active_sub_group_at(mid_jd) is not None
    assert major.planet == pair.major_profile.planet == path.major_profile.planet == group.major.planet
    assert leaf.planet == path.deepest_profile.planet
    assert leaf.level == path.deepest_level == 4
    assert pair.sub_profile is not None
    assert pair.sub_profile.planet == path.profiles[1].planet


# -- ZRLevelPair --

def test_zr_level_pair_same_sign_gives_distance_1() -> None:
    """zr_level_pair gives house_distance=1 and signs_are_identical=True for same sign."""
    from moira.timelords import zodiacal_releasing, zr_level_pair
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=2)
    l1 = next(p for p in periods if p.level == 1)
    # Find a Level-2 period with the same sign as the Level-1 period
    same_sign_l2 = next(
        (p for p in periods if p.level == 2 and p.sign == l1.sign), None
    )
    if same_sign_l2 is None:
        pytest.skip("no same-sign Level-2 period found for this birth data")
    pair = zr_level_pair(l1, same_sign_l2)
    assert pair.house_distance == 1
    assert pair.signs_are_identical


def test_zr_level_pair_house_distance_range() -> None:
    """zr_level_pair.house_distance is always 1–12."""
    from moira.timelords import zodiacal_releasing, zr_level_pair
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=2)
    l1_periods = [p for p in periods if p.level == 1]
    l2_periods = [p for p in periods if p.level == 2]
    for l1 in l1_periods[:3]:
        for l2 in l2_periods[:3]:
            pair = zr_level_pair(l1, l2)
            assert 1 <= pair.house_distance <= 12


def test_zr_level_pair_is_adjacent_levels() -> None:
    """zr_level_pair.is_adjacent_levels is True for Level-1 and Level-2 periods."""
    from moira.timelords import zodiacal_releasing, zr_level_pair
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=2)
    l1 = next(p for p in periods if p.level == 1)
    l2 = next(p for p in periods if p.level == 2)
    pair = zr_level_pair(l1, l2)
    assert pair.is_adjacent_levels


def test_zr_level_pair_rejects_inverted_levels() -> None:
    """zr_level_pair raises ValueError when upper is at a deeper level than lower."""
    from moira.timelords import zodiacal_releasing, ZRLevelPair, zr_condition_profile
    periods = zodiacal_releasing(_P8_FORTUNE, _P8_JD_BIRTH, levels=2)
    l1 = next(p for p in periods if p.level == 1)
    l2 = next(p for p in periods if p.level == 2)
    with pytest.raises(ValueError, match="lower level number"):
        ZRLevelPair(
            upper_profile       = zr_condition_profile(l2),  # inverted
            lower_profile       = zr_condition_profile(l1),
            house_distance      = 1,
            signs_are_identical = l1.sign == l2.sign,
        )


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening tests
# ---------------------------------------------------------------------------

_P10_JD_BIRTH  = 2451545.0
_P10_FORTUNE   = 120.0

# -- validate_firdaria_output --

def test_validate_firdaria_output_passes_for_valid_output() -> None:
    """validate_firdaria_output passes silently for genuine firdaria() output."""
    from moira.timelords import firdaria, validate_firdaria_output
    periods = firdaria(_P10_JD_BIRTH, is_day_chart=True)
    validate_firdaria_output(periods)  # must not raise


def test_validate_firdaria_output_detects_out_of_order_majors() -> None:
    """validate_firdaria_output raises when level-1 periods are reversed."""
    from moira.timelords import firdaria, validate_firdaria_output
    import dataclasses
    periods = firdaria(_P10_JD_BIRTH, is_day_chart=True)
    level1 = [p for p in periods if p.level == 1]
    subs   = [p for p in periods if p.level == 2]
    reversed_majors = list(reversed(level1)) + subs
    with pytest.raises(ValueError, match="out of order"):
        validate_firdaria_output(reversed_majors)


def test_validate_firdaria_output_detects_unknown_major_planet() -> None:
    """validate_firdaria_output raises when a sub-period has an unknown major_planet."""
    from moira.timelords import firdaria, validate_firdaria_output, FirdarPeriod
    import dataclasses
    periods = firdaria(_P10_JD_BIRTH, is_day_chart=True)
    bad_sub = dataclasses.replace(
        next(p for p in periods if p.level == 2),
        major_planet="UnknownPlanet",
    )
    tampered = [p for p in periods if not (p.level == 2 and p.planet == bad_sub.planet
                                           and p.major_planet != "UnknownPlanet")]
    tampered.append(bad_sub)
    with pytest.raises(ValueError, match="unknown major_planet"):
        validate_firdaria_output(tampered)


def test_firdar_active_pair_rejects_non_finite_jd() -> None:
    """firdar_active_pair raises ValueError for non-finite jd values."""
    from moira.timelords import firdaria, firdar_active_pair
    import math
    periods = firdaria(_P10_JD_BIRTH, is_day_chart=True)
    with pytest.raises(ValueError, match="finite"):
        firdar_active_pair(periods, math.nan)
    with pytest.raises(ValueError, match="finite"):
        firdar_active_pair(periods, math.inf)


def test_decennial_active_pair_rejects_non_finite_jd() -> None:
    """decennial_active_pair raises ValueError for non-finite jd values."""
    from moira.timelords import decennials, decennial_active_pair
    import math

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P10_JD_BIRTH, natal_positions, True)
    with pytest.raises(ValueError, match="finite"):
        decennial_active_pair(periods, math.nan)
    with pytest.raises(ValueError, match="finite"):
        decennial_active_pair(periods, math.inf)


def test_decennial_active_path_rejects_non_finite_jd() -> None:
    """decennial_active_path raises ValueError for non-finite jd values."""
    from moira.timelords import decennial_active_path, decennials
    import math

    natal_positions = {
        "Sun": 10.0,
        "Mercury": 20.0,
        "Venus": 50.0,
        "Mars": 110.0,
        "Moon": 200.0,
        "Jupiter": 250.0,
        "Saturn": 300.0,
    }

    periods = decennials(_P10_JD_BIRTH, natal_positions, True)
    with pytest.raises(ValueError, match="finite"):
        decennial_active_path(periods, math.nan)
    with pytest.raises(ValueError, match="finite"):
        decennial_active_path(periods, math.inf)


# -- validate_releasing_output --

def test_validate_releasing_output_passes_for_valid_output() -> None:
    """validate_releasing_output passes silently for genuine zodiacal_releasing() output."""
    from moira.timelords import zodiacal_releasing, validate_releasing_output
    periods = zodiacal_releasing(_P10_FORTUNE, _P10_JD_BIRTH, levels=3)
    validate_releasing_output(periods)  # must not raise


def test_validate_releasing_output_detects_out_of_order_level1() -> None:
    """validate_releasing_output raises when Level-1 periods are reversed."""
    from moira.timelords import zodiacal_releasing, validate_releasing_output
    periods = zodiacal_releasing(_P10_FORTUNE, _P10_JD_BIRTH, levels=1)
    reversed_periods = list(reversed(periods))
    with pytest.raises(ValueError, match="out of order"):
        validate_releasing_output(reversed_periods)


def test_validate_releasing_output_detects_containment_violation() -> None:
    """validate_releasing_output raises when a Level-2 period is outside all Level-1 spans."""
    from moira.timelords import zodiacal_releasing, validate_releasing_output
    import dataclasses
    periods = zodiacal_releasing(_P10_FORTUNE, _P10_JD_BIRTH, levels=2)
    l1_periods = [p for p in periods if p.level == 1]
    # Insert a synthetic Level-2 period that falls completely outside the Level-1 span
    first_l2 = next(p for p in periods if p.level == 2)
    outside_l2 = dataclasses.replace(
        first_l2,
        start_jd = l1_periods[0].start_jd - 1000.0,
        end_jd   = l1_periods[0].start_jd - 999.0,
    )
    # Keep only original l2 periods and insert the out-of-span one
    only_l2_original = [p for p in periods if p.level == 2 and p is not first_l2]
    tampered = [p for p in periods if p.level == 1] + only_l2_original + [outside_l2]
    # The validator must raise — either ordering or containment fires
    with pytest.raises(ValueError):
        validate_releasing_output(tampered)
