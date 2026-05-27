from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.varshaphal as varshaphal_module
from moira.constants import HouseSystem
from moira.houses import calculate_houses
from moira.varshaphal import (
    active_mudda_dasha,
    active_tasira_period,
    build_varshaphal_chart,
    muntha,
    mudda_dasha,
    mudda_period_judgement,
    muntha_condition_profile,
    tasira_periods,
    tajika_panchavargi_strength,
    tajika_shadbala_profile,
    tajika_aspects,
    tajika_yogas,
    varshesha,
    varshaphal_judgement_profile,
    varshaphal_topic_judgements,
    varshaphal_topic_windows,
    varshaphal_year_judgement,
    varshaphal_year_summary,
    varshaphal_sahams,
)


def test_muntha_advances_one_sign_per_completed_year() -> None:
    assert muntha(312.0, 0) == pytest.approx(312.0)
    assert muntha(312.0, 23) == pytest.approx((312.0 + 23 * 30.0) % 360.0)


def test_muntha_rejects_negative_years() -> None:
    with pytest.raises(ValueError, match="years_elapsed"):
        muntha(120.0, -1)


def test_mudda_dasha_uses_gauri_year_ruler_rule_and_birth_fraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        varshaphal_module,
        "all_planets_at",
        lambda *args, **kwargs: {"Moon": SimpleNamespace(longitude=0.0)},
    )
    monkeypatch.setattr(
        varshaphal_module,
        "nakshatra_of",
        lambda *args, **kwargs: SimpleNamespace(
            nakshatra="Rohini",
            nakshatra_index=3,
            nakshatra_lord="Moon",
            degrees_in=(40.0 / 60.0) * (360.0 / 27.0),
        ),
    )
    monkeypatch.setattr(
        varshaphal_module,
        "_varshaphal_jd",
        lambda birth_jd, year, **kwargs: 2451545.0 + ((year - 2000) * 365.25),
    )

    result = mudda_dasha(2451545.0, 2007)

    assert result.school == "gauri"
    assert result.natal_nakshatra == "Rohini"
    assert result.year_ruler == "Venus"
    assert result.birth_elapsed_ghatis == pytest.approx(40.0)
    assert result.birth_remaining_ghatis == pytest.approx(20.0)
    assert result.periods[0].lord == "Venus"
    assert result.periods[0].duration_days == pytest.approx(20.0)
    assert result.periods[1].lord == "Sun"
    assert result.periods[-1].lord == "Venus"
    assert result.periods[-1].duration_days == pytest.approx(40.0)
    assert result.periods[-1].end_day == pytest.approx(360.0)
    assert sum(period.duration_days for period in result.periods) == pytest.approx(360.0)


def test_mudda_dasha_subperiods_follow_sixty_based_multiplier_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        varshaphal_module,
        "all_planets_at",
        lambda *args, **kwargs: {"Moon": SimpleNamespace(longitude=0.0)},
    )
    monkeypatch.setattr(
        varshaphal_module,
        "nakshatra_of",
        lambda *args, **kwargs: SimpleNamespace(
            nakshatra="Krittika",
            nakshatra_index=2,
            nakshatra_lord="Sun",
            degrees_in=0.0,
        ),
    )
    monkeypatch.setattr(
        varshaphal_module,
        "_varshaphal_jd",
        lambda birth_jd, year, **kwargs: 2451545.0 + ((year - 2000) * 365.25),
    )

    result = mudda_dasha(2451545.0, 2000)
    sun_period = result.periods[1]

    assert sun_period.lord == "Moon"
    assert result.periods[0].duration_days == pytest.approx(18.0)
    assert sun_period.duration_days == pytest.approx(30.0)
    assert sum(sub.duration_days for sub in sun_period.sub) == pytest.approx(sun_period.duration_days)
    assert sun_period.sub[0].lord == "Moon"
    assert sun_period.sub[0].duration_days == pytest.approx(4.0)
    assert sun_period.sub[1].lord == "Mars"
    assert sun_period.sub[1].duration_days == pytest.approx(2.5)
    assert sun_period.sub[-1].lord == "Sun"
    assert sun_period.sub[-1].duration_days == pytest.approx(2.0)


def test_active_mudda_dasha_selects_current_major_and_subperiod() -> None:
    mudda = varshaphal_module.MuddaDasha(
        school="gauri",
        natal_nakshatra="Krittika",
        natal_nakshatra_index=2,
        natal_nakshatra_lord="Sun",
        birth_elapsed_ghatis=0.0,
        birth_remaining_ghatis=60.0,
        year_ruler="Sun",
        year_start_jd=1000.0,
        year_end_jd=1360.0,
        periods=(
            varshaphal_module.MuddaDashaPeriod(
                level=1,
                lord="Sun",
                start_day=0.0,
                end_day=18.0,
                duration_days=18.0,
                start_jd=1000.0,
                end_jd=1018.0,
                source_fraction="full_period",
                sub=(
                    varshaphal_module.MuddaDashaPeriod(2, "Sun", 0.0, 1.2, 1.2, 1000.0, 1001.2, "multiplier_subperiod"),
                    varshaphal_module.MuddaDashaPeriod(2, "Moon", 1.2, 3.6, 2.4, 1001.2, 1003.6, "multiplier_subperiod"),
                ),
            ),
            varshaphal_module.MuddaDashaPeriod(
                level=1,
                lord="Moon",
                start_day=18.0,
                end_day=48.0,
                duration_days=30.0,
                start_jd=1018.0,
                end_jd=1048.0,
                source_fraction="full_period",
                sub=(
                    varshaphal_module.MuddaDashaPeriod(2, "Moon", 18.0, 22.0, 4.0, 1018.0, 1022.0, "multiplier_subperiod"),
                    varshaphal_module.MuddaDashaPeriod(2, "Mars", 22.0, 24.5, 2.5, 1022.0, 1024.5, "multiplier_subperiod"),
                ),
            ),
        ),
    )

    activation = active_mudda_dasha(mudda, 1023.0)

    assert activation.major_period.lord == "Moon"
    assert activation.sub_period.lord == "Mars"


def test_tasira_periods_follow_ascendant_aspect_strength_order() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 180.0,
            "Moon": 120.0,
            "Mercury": 90.0,
            "Mars": 30.0,
        },
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=1000.0,
            year_end_jd=1360.0,
            periods=(),
        ),
    )

    result = tasira_periods(fake)

    assert tuple(period.lord for period in result.periods) == ("Sun", "Moon", "Mercury")
    assert result.periods[0].nominal_days == pytest.approx(160.0)
    assert result.periods[1].nominal_days == pytest.approx(120.0)
    assert result.periods[-1].end_day == pytest.approx(360.0)


def test_active_tasira_period_selects_current_period() -> None:
    tasira = varshaphal_module.TasiraDasha(
        year_start_jd=1000.0,
        year_end_jd=1360.0,
        periods=(
            varshaphal_module.TasiraPeriod("Sun", 180.0, 60.0, 160.0, 0.0, 160.0, 1000.0, 1160.0),
            varshaphal_module.TasiraPeriod("Moon", 120.0, 45.0, 120.0, 160.0, 280.0, 1160.0, 1280.0),
            varshaphal_module.TasiraPeriod("Mercury", 90.0, 30.0, 80.0, 280.0, 360.0, 1280.0, 1360.0),
        ),
    )

    active = active_tasira_period(tasira, 1200.0)

    assert active.lord == "Moon"


def test_varshaphal_sahams_apply_30_degree_correction_when_asc_not_between() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 40.0,
        "Moon": 200.0,
        "Mars": 10.0,
        "Mercury": 80.0,
        "Jupiter": 150.0,
        "Venus": 120.0,
        "Saturn": 300.0,
    }

    sahams = {s.name: s for s in varshaphal_sahams(20.0, planets, houses, is_day=True)}
    punya = sahams["Punya"]

    assert punya.correction_applied is True
    assert punya.longitude == pytest.approx((200.0 - 40.0 + 20.0 + 30.0) % 360.0)


def test_varshaphal_sahams_reverse_default_formulas_at_night() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 40.0,
        "Moon": 80.0,
        "Mars": 10.0,
        "Mercury": 50.0,
        "Jupiter": 150.0,
        "Venus": 120.0,
        "Saturn": 300.0,
    }

    sahams = {s.name: s for s in varshaphal_sahams(60.0, planets, houses, is_day=False)}

    assert sahams["Punya"].reversed_for_night is True
    assert sahams["Bhratru"].reversed_for_night is False


def test_varshaphal_sahams_support_derived_dependencies() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 40.0,
        "Moon": 80.0,
        "Mars": 10.0,
        "Mercury": 50.0,
        "Jupiter": 150.0,
        "Venus": 120.0,
        "Saturn": 300.0,
    }

    sahams = {s.name: s for s in varshaphal_sahams(60.0, planets, houses, is_day=True)}
    yasa = sahams["Yasa"]
    punya = sahams["Punya"]
    expected = (planets["Jupiter"] - punya.longitude + 60.0) % 360.0
    if yasa.correction_applied:
        expected = (expected + 30.0) % 360.0

    assert yasa.longitude == pytest.approx(expected)


def test_muntha_condition_profile_tracks_lord_house_geometry() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    sidereal_planets = {
        "Sun": 10.0,
        "Moon": 20.0,
        "Mars": 65.0,
        "Mercury": 80.0,
        "Jupiter": 140.0,
        "Venus": 200.0,
        "Saturn": 260.0,
    }

    profile = muntha_condition_profile(
        muntha_longitude=5.0,
        muntha_house=1,
        muntha_lord="Sun",
        sidereal_planets=sidereal_planets,
        sidereal_houses=houses,
    )

    assert profile.muntha_sign == "Aries"
    assert profile.muntha_lord_sign == "Aries"
    assert profile.muntha_lord_house == 1
    assert profile.muntha_lord_house_from_muntha == 1
    assert profile.muntha_lord_dignity.dignity_rank == "exaltation"
    assert profile.muntha_lord_dignity_profile.tier == "strong"
    assert profile.lord_in_kendra is True
    assert profile.lord_in_dusthana is False
    assert profile.lord_is_strong is True
    assert profile.lord_is_weak is False


def test_tajika_aspects_classify_benefic_and_inimical_relations() -> None:
    aspects = tajika_aspects(
        {
            "Sun": 10.0,
            "Moon": 130.0,
            "Mars": 100.0,
            "Mercury": 70.0,
            "Jupiter": 250.0,
            "Venus": 190.0,
            "Saturn": 310.0,
        },
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )

    by_pair = {(a.body1, a.body2): a for a in aspects}
    trine = by_pair[("Sun", "Moon")]
    square = by_pair[("Sun", "Mars")]

    assert trine.relation == "open_friend"
    assert trine.is_benefic_relation is True
    assert trine.relation_strength == pytest.approx(0.75)
    assert square.relation == "secret_enemy"
    assert square.is_benefic_relation is False
    assert square.relation_strength == pytest.approx(0.5)


def test_tajika_yogas_distinguish_ithasala_from_isarpha() -> None:
    aspects = tajika_aspects(
        {
            "Sun": 10.0,
            "Moon": 130.0,
            "Mars": 100.0,
            "Mercury": 70.0,
            "Jupiter": 250.0,
            "Venus": 190.0,
            "Saturn": 310.0,
        },
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )
    yogas = tajika_yogas(aspects)
    isarpha = next(
        yoga for yoga in yogas
        if yoga.name == "Isarpha" and {yoga.body1, yoga.body2} == {"Sun", "Moon"}
    )
    ithasala = next(
        yoga for yoga in yogas
        if yoga.name == "Ithasala" and {yoga.body1, yoga.body2} == {"Sun", "Mars"}
    )

    assert isarpha.favorable is False
    assert ithasala.favorable is True


def test_tajika_yogas_detect_nakta_with_moon_bridge() -> None:
    aspects = tajika_aspects(
        {
            "Sun": 10.0,
            "Moon": 41.0,
            "Mars": 260.0,
            "Mercury": 130.0,
            "Jupiter": 342.0,
            "Venus": 200.0,
            "Saturn": 300.0,
        },
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )

    nakta = next(
        yoga for yoga in tajika_yogas(aspects)
        if yoga.name == "Nakta" and {yoga.body1, yoga.body2} == {"Mercury", "Jupiter"}
    )

    assert nakta.mediator == "Moon"
    assert len(nakta.supporting_aspects) == 2
    assert {aspect.body1 if aspect.body1 == "Moon" else aspect.body2 for aspect in nakta.supporting_aspects} == {"Moon"}


def test_tajika_yogas_detect_yamaya_with_slow_intermediary() -> None:
    aspects = tajika_aspects(
        {
            "Sun": 130.0,
            "Moon": 20.0,
            "Mars": 250.0,
            "Mercury": 0.0,
            "Jupiter": 90.0,
            "Venus": 20.0,
            "Saturn": 300.0,
        },
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )

    yamaya = next(
        yoga for yoga in tajika_yogas(aspects)
        if yoga.name == "Yamaya" and {yoga.body1, yoga.body2} == {"Mercury", "Venus"}
    )

    assert yamaya.mediator == "Jupiter"
    assert len(yamaya.supporting_aspects) == 2
    assert all(aspect.aspect.applying is True for aspect in yamaya.supporting_aspects)


def test_tajika_yogas_detect_kamboola_when_moon_joins_ithasala() -> None:
    planets = {
        "Sun": 0.0,
        "Moon": 0.0,
        "Mars": 60.0,
        "Mercury": 200.0,
        "Jupiter": 260.0,
        "Venus": 320.0,
        "Saturn": 150.0,
    }
    aspects = tajika_aspects(
        planets,
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )

    kamboola = next(
        yoga for yoga in tajika_yogas(aspects, planets)
        if yoga.name == "Kamboola" and {yoga.body1, yoga.body2} == {"Sun", "Mars"}
    )

    assert kamboola.mediator == "Moon"
    assert kamboola.aspect is not None
    assert kamboola.aspect.aspect.applying is True
    assert len(kamboola.supporting_aspects) >= 2


def test_tajika_yogas_detect_ikkavala_and_induvara_from_house_distribution() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    ikkavala = tajika_yogas(
        (),
        planets={
            "Sun": 5.0,
            "Moon": 35.0,
            "Mars": 95.0,
            "Mercury": 125.0,
            "Jupiter": 185.0,
            "Venus": 215.0,
            "Saturn": 275.0,
        },
        sidereal_houses=houses,
    )
    induvara = tajika_yogas(
        (),
        planets={
            "Sun": 65.0,
            "Moon": 155.0,
            "Mars": 245.0,
            "Mercury": 335.0,
            "Jupiter": 68.0,
            "Venus": 158.0,
            "Saturn": 248.0,
        },
        sidereal_houses=houses,
    )

    assert any(yoga.name == "Ikkavala" and yoga.favorable for yoga in ikkavala)
    assert any(yoga.name == "Induvara" and not yoga.favorable for yoga in induvara)


def test_tajika_yogas_detect_manahoo_when_malefic_blocks_faster_planet() -> None:
    planets = {
        "Sun": 0.0,
        "Moon": 220.0,
        "Mars": 40.0,
        "Mercury": 150.0,
        "Jupiter": 60.0,
        "Venus": 300.0,
        "Saturn": 0.0,
    }
    aspects = tajika_aspects(
        planets,
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )

    manahoo = next(
        yoga for yoga in tajika_yogas(aspects, planets)
        if yoga.name == "Manahoo" and {yoga.body1, yoga.body2} == {"Sun", "Jupiter"}
    )

    assert manahoo.mediator == "Saturn"
    assert manahoo.aspect is not None
    assert manahoo.aspect.aspect.applying is True


def test_tajika_yogas_detect_radda_when_ithasala_planet_is_retrograde() -> None:
    planets = {
        "Sun": 200.0,
        "Moon": 20.0,
        "Mars": 120.0,
        "Mercury": 0.0,
        "Jupiter": 50.0,
        "Venus": 300.0,
        "Saturn": 40.0,
    }
    speeds = {
        "Sun": 1.0,
        "Moon": 13.0,
        "Mars": 0.6,
        "Mercury": -1.2,
        "Jupiter": 0.08,
        "Venus": 1.1,
        "Saturn": 0.03,
    }
    aspects = tajika_aspects(planets, planet_speeds=speeds)

    radda = next(
        yoga for yoga in tajika_yogas(aspects, planets, speeds)
        if yoga.name == "Radda" and {yoga.body1, yoga.body2} == {"Mercury", "Jupiter"}
    )

    assert radda.mediator == "Mercury"
    assert radda.aspect is not None
    assert radda.aspect.aspect.applying is True


def test_tajika_yogas_detect_dupparikutha_with_strong_slow_planet() -> None:
    planets = {
        "Sun": 200.0,
        "Moon": 20.0,
        "Mars": 120.0,
        "Mercury": 0.0,
        "Jupiter": 95.0,
        "Venus": 300.0,
        "Saturn": 40.0,
    }
    speeds = {
        "Sun": 1.0,
        "Moon": 13.0,
        "Mars": 0.6,
        "Mercury": 1.2,
        "Jupiter": 0.08,
        "Venus": 1.1,
        "Saturn": 0.03,
    }
    aspects = tajika_aspects(planets, planet_speeds=speeds)

    dupparikutha = next(
        yoga for yoga in tajika_yogas(aspects, planets, speeds)
        if yoga.name == "Dupparikutha" and {yoga.body1, yoga.body2} == {"Mercury", "Jupiter"}
    )

    assert dupparikutha.mediator == "Jupiter"
    assert dupparikutha.aspect is not None
    assert dupparikutha.aspect.aspect.applying is True


def test_tajika_yogas_detect_duttota_with_explicit_role_context() -> None:
    planets = {
        "Sun": 200.0,
        "Moon": 20.0,
        "Mars": 120.0,
        "Mercury": 90.0,
        "Jupiter": 240.0,
        "Venus": 120.0,
        "Saturn": 40.0,
    }
    speeds = {
        "Sun": 1.0,
        "Moon": 13.0,
        "Mars": 0.6,
        "Mercury": 1.2,
        "Jupiter": 0.08,
        "Venus": 1.1,
        "Saturn": 0.03,
    }
    aspects = tajika_aspects(planets, planet_speeds=speeds)

    duttota = next(
        yoga for yoga in tajika_yogas(
            aspects,
            planets,
            speeds,
            lagna_lord="Mercury",
            significator="Venus",
        )
        if yoga.name == "Duttota" and yoga.body1 == "Mercury" and yoga.body2 == "Venus"
    )

    assert duttota.mediator == "Jupiter"
    assert len(duttota.supporting_aspects) == 1
    assert duttota.supporting_aspects[0].aspect.applying is True


def test_tajika_yogas_detect_thambira_across_sign_boundary() -> None:
    planets = {
        "Sun": 200.0,
        "Moon": 20.0,
        "Mars": 120.0,
        "Mercury": 176.0,
        "Jupiter": 182.0,
        "Venus": 300.0,
        "Saturn": 40.0,
    }
    speeds = {
        "Sun": 1.0,
        "Moon": 13.0,
        "Mars": 0.6,
        "Mercury": 1.2,
        "Jupiter": 0.08,
        "Venus": 1.1,
        "Saturn": 0.03,
    }
    aspects = tajika_aspects(planets, planet_speeds=speeds)

    thambira = next(
        yoga for yoga in tajika_yogas(aspects, planets, speeds)
        if yoga.name == "Thambira" and {yoga.body1, yoga.body2} == {"Mercury", "Jupiter"}
    )

    assert thambira.mediator == "Mercury"
    assert thambira.aspect is not None
    assert thambira.aspect.aspect.applying is True


def test_tajika_panchavargi_strength_exposes_component_scores() -> None:
    strength = tajika_panchavargi_strength(
        "Mars",
        0.0,
        {
            "Sun": 60.0,
            "Moon": 150.0,
            "Mars": 0.0,
            "Mercury": 210.0,
            "Jupiter": 120.0,
            "Venus": 240.0,
            "Saturn": 300.0,
        },
    )

    assert strength.sign == "Aries"
    assert strength.domicile_lord == "Mars"
    assert strength.domicile_relationship == "own"
    assert strength.domicile_score == pytest.approx(7.5)
    assert strength.hadda_lord == "Jupiter"
    assert strength.hadda_relationship == "great_friend"
    assert strength.hadda_score == pytest.approx(2.8125)
    assert strength.decan_lord == "Mars"
    assert strength.decan_score == pytest.approx(2.5)
    assert strength.musallaha_lord == "Mars"
    assert strength.musallaha_score == pytest.approx(1.25)
    assert strength.total_score > 15.0
    assert strength.category == "full"


def test_tajika_panchavargi_strength_tracks_exaltation_basis_relationship() -> None:
    strength = tajika_panchavargi_strength(
        "Sun",
        90.0,
        {
            "Sun": 90.0,
            "Moon": 150.0,
            "Mars": 0.0,
            "Mercury": 210.0,
            "Jupiter": 120.0,
            "Venus": 240.0,
            "Saturn": 300.0,
        },
    )

    assert strength.exaltation_basis_planet == "Jupiter"
    assert strength.exaltation_relationship == "neutral"
    assert strength.exaltation_score == pytest.approx(0.6944444444444444)


def test_tajika_shadbala_profile_collects_non_panchavargi_layers() -> None:
    houses = calculate_houses(2451545.0, 28.6, 77.2, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 0.0,
        "Moon": 130.0,
        "Mars": 100.0,
        "Mercury": 70.0,
        "Jupiter": 250.0,
        "Venus": 40.0,
        "Saturn": 310.0,
    }
    profile = tajika_shadbala_profile(
        "Moon",
        sidereal_planets=planets,
        sidereal_houses=houses,
        year_asc=houses.asc,
        jd_ut=2451545.25,
        latitude=28.6,
        longitude=77.2,
        planet_speeds={
            "Sun": 1.0,
            "Moon": 12.0,
            "Mars": 0.5,
            "Mercury": 1.1,
            "Jupiter": 0.07,
            "Venus": 1.0,
            "Saturn": 0.03,
        },
    )

    assert profile.natural_strength > 0.0
    assert profile.temporal_strength.luminary_elongation_strength > 0.0
    assert profile.aspect_strength.total_score >= 0.0
    assert profile.motion_strength.total_score >= 0.0
    assert profile.total_score > profile.panchavargi_strength.total_score


def test_varshesha_prefers_candidate_aspecting_year_asc_with_more_claims() -> None:
    result = varshesha(
        natal_sidereal_asc=0.0,
        year_asc=0.0,
        muntha_longitude=0.0,
        sidereal_planets={
            "Sun": 40.0,
            "Moon": 130.0,
            "Mars": 0.0,
            "Mercury": 200.0,
            "Jupiter": 250.0,
            "Venus": 300.0,
            "Saturn": 20.0,
        },
        is_day=True,
    )

    assert result.planet == "Mars"
    assert "muntha_lord" in result.roles
    assert result.asc_aspect is not None
    assert result.asc_aspect.body1 == "Mars"


def test_varshesha_uses_panchavargi_strength_before_natural_rank() -> None:
    result = varshesha(
        natal_sidereal_asc=30.0,
        year_asc=0.0,
        muntha_longitude=60.0,
        sidereal_planets={
            "Sun": 60.0,
            "Moon": 150.0,
            "Mars": 0.0,
            "Mercury": 210.0,
            "Jupiter": 120.0,
            "Venus": 240.0,
            "Saturn": 300.0,
        },
        is_day=True,
    )

    by_planet = {candidate.planet: candidate for candidate in result.candidates}

    assert result.selection_basis == "aspect_claims_tajika_strength"
    assert result.planet == "Mars"
    assert by_planet["Mars"].panchavargi_strength.total_score > by_planet["Venus"].panchavargi_strength.total_score


def test_varshesha_applies_moon_transfer_rule_from_primary_source() -> None:
    planets = {
        "Sun": 40.0,
        "Moon": 100.0,
        "Mars": 130.0,
        "Mercury": 200.0,
        "Jupiter": 250.0,
        "Venus": 300.0,
        "Saturn": 20.0,
    }
    speeds = {
        "Sun": 1.0,
        "Moon": 13.0,
        "Mars": 0.6,
        "Mercury": 1.2,
        "Jupiter": 0.08,
        "Venus": 1.1,
        "Saturn": 0.03,
    }
    annual_aspects = tajika_aspects(
        planets,
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )
    annual_yogas = tajika_yogas(
        annual_aspects,
        planets,
        speeds,
    )
    result = varshesha(
        natal_sidereal_asc=0.0,
        year_asc=0.0,
        muntha_longitude=90.0,
        sidereal_planets=planets,
        is_day=False,
        annual_yogas=annual_yogas,
    )

    assert result.selection_basis == "moon_ithasala_transfer"
    assert result.planet == "Mercury"


def test_varshaphal_judgement_profile_tracks_varshesha_and_yoga_balance() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        varshesha=SimpleNamespace(planet="Mars"),
        sidereal_planets={
            "Sun": 10.0,
            "Moon": 20.0,
            "Mars": 95.0,
            "Mercury": 180.0,
            "Jupiter": 215.0,
            "Venus": 240.0,
            "Saturn": 300.0,
        },
        sidereal_houses=houses,
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Mars", body2="Moon", favorable=True),
            SimpleNamespace(name="Radda", body1="Mars", body2="Moon", favorable=False),
        ),
    )
    profile = varshaphal_judgement_profile(fake)

    assert profile.varshesha.planet == "Mars"
    assert "Ithasala" in profile.supportive_yogas
    assert "Radda" in profile.obstructive_yogas
    assert profile.varshesha_strength.total_score > 0.0
    assert profile.varshesha_shadbala.total_score >= profile.varshesha_strength.total_score
    assert profile.muntha_lord_shadbala.total_score > 0.0
    assert profile.actor_rankings
    assert profile.mudda_period is None
    assert profile.strongest_testimonies
    assert profile.yearly_strength_balance in {"supportive", "mixed", "adverse"}
    assert profile.ascendant_authority_indication in {"supportive", "mixed", "adverse"}


def test_mudda_period_judgement_reuses_annual_actor_strength_for_planetary_lords() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        jd_ut=2451545.0,
        ayanamsa_system="Lahiri",
        chart=SimpleNamespace(
            latitude=0.0,
            longitude=0.0,
            planets={
                "Sun": SimpleNamespace(speed=1.0),
                "Moon": SimpleNamespace(speed=12.0),
                "Mars": SimpleNamespace(speed=0.6),
                "Mercury": SimpleNamespace(speed=1.2),
                "Jupiter": SimpleNamespace(speed=0.08),
                "Venus": SimpleNamespace(speed=1.1),
                "Saturn": SimpleNamespace(speed=0.03),
            },
            nodes={},
        ),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 0.0,
            "Moon": 45.0,
            "Mars": 120.0,
            "Mercury": 180.0,
            "Jupiter": 240.0,
            "Venus": 300.0,
            "Saturn": 330.0,
        },
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Sun", body2="Moon", mediator=None, favorable=True),
            SimpleNamespace(name="Radda", body1="Sun", body2="Moon", mediator=None, favorable=False),
        ),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=2451545.0,
            year_end_jd=2451905.0,
            periods=(
                varshaphal_module.MuddaDashaPeriod(
                    level=1,
                    lord="Sun",
                    start_day=0.0,
                    end_day=18.0,
                    duration_days=18.0,
                    start_jd=2451545.0,
                    end_jd=2451563.0,
                    source_fraction="full_period",
                    sub=(
                        varshaphal_module.MuddaDashaPeriod(2, "Sun", 0.0, 1.2, 1.2, 2451545.0, 2451546.2, "multiplier_subperiod"),
                    ),
                ),
            ),
        ),
    )

    result = mudda_period_judgement(fake)

    assert result.activation.major_period.lord == "Sun"
    assert result.major_actor_judgement is not None
    assert result.major_actor_judgement.planet == "Sun"
    assert result.major_supportive_yoga_count == 1
    assert result.major_obstructive_yoga_count == 1
    assert result.major_authority in {"strong", "supportive", "mixed", "strained"}
    assert result.major_result.manifestation == "governs_year"
    assert result.major_result.result_fullness == "governing"
    assert result.sub_result.result_fullness == "governing"


def test_mudda_period_judgement_marks_ithasala_with_varshesha_as_full() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        jd_ut=2451545.0,
        ayanamsa_system="Lahiri",
        chart=SimpleNamespace(latitude=0.0, longitude=0.0, planets={}, nodes={}),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 0.0,
            "Moon": 120.0,
            "Mars": 210.0,
            "Mercury": 180.0,
            "Jupiter": 240.0,
            "Venus": 300.0,
            "Saturn": 330.0,
        },
        varshesha=SimpleNamespace(planet="Sun"),
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Sun", body2="Moon", mediator=None, favorable=True),
        ),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=2451545.0,
            year_end_jd=2451905.0,
            periods=(
                varshaphal_module.MuddaDashaPeriod(
                    level=1,
                    lord="Moon",
                    start_day=0.0,
                    end_day=30.0,
                    duration_days=30.0,
                    start_jd=2451545.0,
                    end_jd=2451575.0,
                    source_fraction="full_period",
                    sub=(
                        varshaphal_module.MuddaDashaPeriod(2, "Moon", 0.0, 4.0, 4.0, 2451545.0, 2451549.0, "multiplier_subperiod"),
                    ),
                ),
            ),
        ),
    )

    result = mudda_period_judgement(fake)

    assert result.major_result.relation_to_varshesha == "ithasala"
    assert result.major_result.result_fullness == "full"
    assert result.major_result.manifestation == "manifest"


def test_mudda_period_judgement_marks_isarpha_as_blocked() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        jd_ut=2451545.0,
        ayanamsa_system="Lahiri",
        chart=SimpleNamespace(latitude=0.0, longitude=0.0, planets={}, nodes={}),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 0.0,
            "Moon": 120.0,
            "Mars": 210.0,
            "Mercury": 180.0,
            "Jupiter": 240.0,
            "Venus": 300.0,
            "Saturn": 330.0,
        },
        varshesha=SimpleNamespace(planet="Sun"),
        tajika_yogas=(
            SimpleNamespace(name="Isarpha", body1="Sun", body2="Moon", mediator=None, favorable=False),
        ),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=2451545.0,
            year_end_jd=2451905.0,
            periods=(
                varshaphal_module.MuddaDashaPeriod(
                    level=1,
                    lord="Moon",
                    start_day=0.0,
                    end_day=30.0,
                    duration_days=30.0,
                    start_jd=2451545.0,
                    end_jd=2451575.0,
                    source_fraction="full_period",
                    sub=(
                        varshaphal_module.MuddaDashaPeriod(2, "Moon", 0.0, 4.0, 4.0, 2451545.0, 2451549.0, "multiplier_subperiod"),
                    ),
                ),
            ),
        ),
    )

    result = mudda_period_judgement(fake)

    assert result.major_result.relation_to_varshesha == "isarpha"
    assert result.major_result.manifestation == "blocked"
    assert result.major_result.result_fullness == "withheld"


def test_varshaphal_year_judgement_consolidates_annual_layers() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        jd_ut=2451545.0,
        ayanamsa_system="Lahiri",
        chart=SimpleNamespace(
            latitude=0.0,
            longitude=0.0,
            planets={
                "Sun": SimpleNamespace(speed=1.0),
                "Moon": SimpleNamespace(speed=12.0),
                "Mars": SimpleNamespace(speed=0.6),
                "Mercury": SimpleNamespace(speed=1.2),
                "Jupiter": SimpleNamespace(speed=0.08),
                "Venus": SimpleNamespace(speed=1.1),
                "Saturn": SimpleNamespace(speed=0.03),
            },
            nodes={},
        ),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 0.0,
            "Moon": 120.0,
            "Mars": 90.0,
            "Mercury": 180.0,
            "Jupiter": 240.0,
            "Venus": 300.0,
            "Saturn": 330.0,
        },
        varshesha=SimpleNamespace(planet="Sun"),
        muntha_lord="Mars",
        sahams=(
            SimpleNamespace(name="Punya", house=1, ruler="Sun"),
            SimpleNamespace(name="Artha", house=2, ruler="Moon"),
        ),
        natal_chart=SimpleNamespace(
            latitude=0.0,
            longitude=0.0,
            planets={
                "Sun": SimpleNamespace(speed=1.0),
                "Moon": SimpleNamespace(speed=12.0),
                "Mars": SimpleNamespace(speed=0.6),
                "Mercury": SimpleNamespace(speed=1.2),
                "Jupiter": SimpleNamespace(speed=0.08),
                "Venus": SimpleNamespace(speed=1.1),
                "Saturn": SimpleNamespace(speed=0.03),
            },
        ),
        natal_sidereal_houses=houses,
        natal_sidereal_planets={
            "Sun": 0.0,
            "Moon": 120.0,
            "Mars": 90.0,
            "Mercury": 180.0,
            "Jupiter": 240.0,
            "Venus": 300.0,
            "Saturn": 330.0,
        },
        natal_sahams=(
            SimpleNamespace(name="Punya", house=1, ruler="Sun"),
            SimpleNamespace(name="Artha", house=2, ruler="Moon"),
        ),
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Sun", body2="Mars", mediator=None, favorable=True),
            SimpleNamespace(name="Kamboola", body1="Sun", body2="Mars", mediator="Moon", favorable=True),
        ),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=2451545.0,
            year_end_jd=2451905.0,
            periods=(
                varshaphal_module.MuddaDashaPeriod(
                    level=1,
                    lord="Sun",
                    start_day=0.0,
                    end_day=18.0,
                    duration_days=18.0,
                    start_jd=2451545.0,
                    end_jd=2451563.0,
                    source_fraction="full_period",
                    sub=(
                        varshaphal_module.MuddaDashaPeriod(2, "Mars", 0.0, 1.5, 1.5, 2451545.0, 2451546.5, "multiplier_subperiod"),
                    ),
                ),
            ),
        ),
    )

    year = varshaphal_year_judgement(fake)

    assert year.profile.varshesha.planet == "Sun"
    assert year.dominant_governor is not None
    assert year.key_sahams
    assert year.topics
    assert year.foreground_topics
    assert year.prioritized_sahams
    assert year.timed_period is not None
    assert year.supportive_yogas == ("Ithasala", "Kamboola")
    assert year.obstructive_yogas == ()
    assert year.decisive_testimonies
    assert year.final_verdict in {"supportive", "mixed", "adverse"}
    assert year.conflict_resolution
    assert any(topic.topic == "authority" for topic in year.topics)
    assert any(item.startswith("dominant_governor:") for item in year.verdict_basis)


def test_varshaphal_topic_judgements_expose_named_channels() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        judgement=SimpleNamespace(
            mudda_period=SimpleNamespace(
                major_result=SimpleNamespace(manifestation="manifest"),
                activation=SimpleNamespace(
                    major_period=SimpleNamespace(lord="Venus"),
                    sub_period=SimpleNamespace(lord="Jupiter"),
                ),
            ),
        ),
        sidereal_houses=houses,
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Sun", body2="Venus", mediator=None, favorable=True),
            SimpleNamespace(name="Isarpha", body1="Sun", body2="Mars", mediator=None, favorable=False),
        ),
        varshesha=SimpleNamespace(planet="Sun"),
    )
    priorities = (
        SimpleNamespace(saham_name="Artha", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Venus")),
        SimpleNamespace(saham_name="Vivaha", priority="secondary", is_considered=True, annual_judgement=SimpleNamespace(ruler="Venus")),
        SimpleNamespace(saham_name="Roga", priority="disregarded", is_considered=False, annual_judgement=SimpleNamespace(ruler="Mars")),
        SimpleNamespace(saham_name="Putra", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Jupiter")),
        SimpleNamespace(saham_name="Karyasiddhi", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Venus")),
        SimpleNamespace(saham_name="Paradesa", priority="secondary", is_considered=True, annual_judgement=SimpleNamespace(ruler="Jupiter")),
        SimpleNamespace(saham_name="Raja", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Venus")),
    )
    topics = varshaphal_topic_judgements(
        fake,
        profile=fake.judgement,
        saham_priorities=tuple(item for item in priorities if item.is_considered),
        disregarded_sahams=tuple(item for item in priorities if not item.is_considered),
    )

    by_name = {topic.topic: topic for topic in topics}
    assert by_name["wealth"].judgement in {"foreground", "activated", "conditional"}
    assert by_name["marriage"].saham_name == "Vivaha"
    assert by_name["illness"].judgement == "background"
    assert by_name["children"].timed_activation == "active"
    assert by_name["career"].saham_name == "Karyasiddhi"
    assert by_name["travel"].saham_name == "Paradesa"
    assert by_name["authority"].saham_name == "Raja"


def test_varshaphal_topic_judgements_apply_primary_source_rulebooks() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        judgement=SimpleNamespace(
            mudda_period=None,
            year_lagna_lord="Mars",
        ),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 130.0,
            "Moon": 45.0,
            "Mars": 15.0,
            "Mercury": 165.0,
            "Jupiter": 125.0,
            "Venus": 195.0,
            "Saturn": 250.0,
        },
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Mars", body2="Venus", mediator=None, favorable=True),
            SimpleNamespace(name="Ithasala", body1="Mars", body2="Sun", mediator=None, favorable=True),
        ),
        varshesha=SimpleNamespace(planet="Jupiter"),
    )
    priorities = (
        SimpleNamespace(saham_name="Artha", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Venus", authority="supportive")),
        SimpleNamespace(saham_name="Vivaha", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Venus", authority="supportive")),
        SimpleNamespace(saham_name="Putra", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Jupiter", authority="supportive")),
    )

    topics = varshaphal_topic_judgements(fake, profile=fake.judgement, saham_priorities=priorities)
    by_name = {topic.topic: topic for topic in topics}

    assert "wealth_easy_gain:lagna_second_ithasala" in by_name["wealth"].basis
    assert by_name["wealth"].judgement == "foreground"
    assert "marriage_testimony:lagna_seventh_ithasala" in by_name["marriage"].basis
    assert "marriage_venus_in_seventh" in by_name["marriage"].basis
    assert by_name["marriage"].judgement == "foreground"
    assert "children_happiness:jupiter_year_ruler_in_fifth_or_eleventh" in by_name["children"].basis
    assert by_name["children"].judgement == "foreground"


def test_varshaphal_topic_judgements_foreground_illness_when_disease_rules_dominate() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        judgement=SimpleNamespace(
            year_lagna_lord="Mars",
            mudda_period=SimpleNamespace(
                major_result=SimpleNamespace(manifestation="manifest"),
                activation=SimpleNamespace(
                    major_period=SimpleNamespace(lord="Mercury"),
                    sub_period=SimpleNamespace(lord="Saturn"),
                ),
            ),
        ),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 10.0,
            "Moon": 40.0,
            "Mars": 220.0,
            "Mercury": 155.0,
            "Jupiter": 280.0,
            "Venus": 190.0,
            "Saturn": 165.0,
        },
        chart=SimpleNamespace(planets={"Saturn": SimpleNamespace(speed=-0.25)}),
        tajika_yogas=(),
        varshesha=SimpleNamespace(planet="Saturn"),
    )
    priorities = (
        SimpleNamespace(saham_name="Roga", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Mercury", authority="supportive")),
    )

    topics = varshaphal_topic_judgements(fake, profile=fake.judgement, saham_priorities=priorities)
    by_name = {topic.topic: topic for topic in topics}

    assert "illness_active:ruler_in_disease_house" in by_name["illness"].basis
    assert "illness_compounded:saturn_retrograde_in_sixth" in by_name["illness"].basis
    assert by_name["illness"].judgement == "foreground"


def test_varshaphal_topic_judgements_apply_remaining_rulebooks() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        judgement=SimpleNamespace(
            year_lagna_lord="Mars",
            yearly_strength_balance="supportive",
            mudda_period=SimpleNamespace(
                major_result=SimpleNamespace(manifestation="manifest"),
                activation=SimpleNamespace(
                    major_period=SimpleNamespace(lord="Jupiter"),
                    sub_period=SimpleNamespace(lord="Venus"),
                ),
            ),
        ),
        sidereal_houses=houses,
        sidereal_planets={
            "Sun": 275.0,
            "Moon": 35.0,
            "Mars": 15.0,
            "Mercury": 140.0,
            "Jupiter": 245.0,
            "Venus": 305.0,
            "Saturn": 285.0,
        },
        tajika_yogas=(
            SimpleNamespace(name="Ithasala", body1="Mars", body2="Saturn", mediator=None, favorable=True),
            SimpleNamespace(name="Ithasala", body1="Mars", body2="Jupiter", mediator=None, favorable=True),
            SimpleNamespace(name="Kamboola", body1="Jupiter", body2="Venus", mediator="Moon", favorable=True),
        ),
        varshesha=SimpleNamespace(planet="Jupiter"),
    )
    priorities = (
        SimpleNamespace(saham_name="Karyasiddhi", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Saturn", authority="supportive", house=10)),
        SimpleNamespace(saham_name="Paradesa", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Jupiter", authority="supportive", house=9)),
        SimpleNamespace(saham_name="Raja", priority="high", is_considered=True, annual_judgement=SimpleNamespace(ruler="Sun", authority="supportive", house=10)),
    )

    topics = varshaphal_topic_judgements(fake, profile=fake.judgement, saham_priorities=priorities)
    by_name = {topic.topic: topic for topic in topics}

    assert "career_supported:tenth_lord_ithasala_with_lagna" in by_name["career"].basis
    assert "career_visibility:sun_in_tenth" in by_name["career"].basis
    assert by_name["career"].judgement == "foreground"
    assert "travel_planned:ninth_lord_ithasala_with_lagna" in by_name["travel"].basis
    assert "travel_signified:ninth_lord_in_third_or_ninth" in by_name["travel"].basis
    assert "travel_happy:ninth_lord_kamboola" in by_name["travel"].basis
    assert by_name["travel"].judgement == "foreground"
    assert "authority_rank:sun_in_tenth" in by_name["authority"].basis
    assert "authority_flourishes:raja_saham_in_tenth" in by_name["authority"].basis
    assert by_name["authority"].judgement == "foreground"


def test_varshaphal_topic_windows_follow_mudda_subperiods() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        sidereal_houses=houses,
        sahams=(SimpleNamespace(name="Artha", ruler="Venus"),),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=1000.0,
            year_end_jd=1360.0,
            periods=(
                varshaphal_module.MuddaDashaPeriod(
                    level=1,
                    lord="Venus",
                    start_day=0.0,
                    end_day=60.0,
                    duration_days=60.0,
                    start_jd=1000.0,
                    end_jd=1060.0,
                    source_fraction="full_period",
                    sub=(
                        varshaphal_module.MuddaDashaPeriod(2, "Sun", 0.0, 6.0, 6.0, 1000.0, 1006.0, "multiplier_subperiod"),
                        varshaphal_module.MuddaDashaPeriod(2, "Venus", 6.0, 12.0, 6.0, 1006.0, 1012.0, "multiplier_subperiod"),
                    ),
                ),
            ),
        ),
    )
    windows = varshaphal_topic_windows(fake, "wealth")

    assert windows
    assert windows[0].topic == "wealth"
    assert windows[0].activation_kind in {"house_ruler", "saham_ruler"}
    assert windows[0].source == "mudda"


def test_varshaphal_topic_windows_include_tasira_activations() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        sidereal_houses=houses,
        sahams=(SimpleNamespace(name="Artha", ruler="Venus"),),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=1000.0,
            year_end_jd=1360.0,
            periods=(),
        ),
        tasira_dasha=varshaphal_module.TasiraDasha(
            year_start_jd=1000.0,
            year_end_jd=1360.0,
            periods=(
                varshaphal_module.TasiraPeriod("Venus", 120.0, 45.0, 120.0, 0.0, 120.0, 1000.0, 1120.0),
            ),
        ),
    )

    windows = varshaphal_topic_windows(fake, "wealth")

    assert any(window.source == "tasira" for window in windows)
    assert any(window.activation_kind == "tasira_saham_ruler" for window in windows)


def test_varshaphal_year_summary_collects_report_surface() -> None:
    year = SimpleNamespace(
        final_verdict="supportive",
        dominant_governor=SimpleNamespace(actor="varshesha", planet="Sun"),
        foreground_topics=(SimpleNamespace(topic="wealth"), SimpleNamespace(topic="authority")),
        obstructed_topics=(SimpleNamespace(topic="illness"),),
        background_topics=(SimpleNamespace(topic="travel"),),
        decisive_testimonies=("varshesha:Sun", "saham:Artha"),
        verdict_basis=("strength_balance:supportive",),
    )
    chart = SimpleNamespace(
        year_judgement=year,
        sidereal_houses=calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0),
        sahams=(SimpleNamespace(name="Artha", ruler="Venus"), SimpleNamespace(name="Raja", ruler="Sun")),
        mudda_dasha=varshaphal_module.MuddaDasha(
            school="gauri",
            natal_nakshatra="Krittika",
            natal_nakshatra_index=2,
            natal_nakshatra_lord="Sun",
            birth_elapsed_ghatis=0.0,
            birth_remaining_ghatis=60.0,
            year_ruler="Sun",
            year_start_jd=1000.0,
            year_end_jd=1360.0,
            periods=(
                varshaphal_module.MuddaDashaPeriod(
                    level=1,
                    lord="Venus",
                    start_day=0.0,
                    end_day=60.0,
                    duration_days=60.0,
                    start_jd=1000.0,
                    end_jd=1060.0,
                    source_fraction="full_period",
                    sub=(varshaphal_module.MuddaDashaPeriod(2, "Sun", 0.0, 6.0, 6.0, 1000.0, 1006.0, "multiplier_subperiod"),),
                ),
            ),
        ),
    )
    summary = varshaphal_year_summary(chart, year)

    assert summary.yearly_tone == "supportive"
    assert summary.dominant_governor == "varshesha:Sun"
    assert "wealth" in summary.foreground_topics
    assert "illness" in summary.obstructed_topics
    assert summary.strongest_testimonies


def test_varshaphal_year_judgement_disregards_sahams_weak_in_both_charts() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake = SimpleNamespace(
        judgement=SimpleNamespace(
            actor_rankings=(
                SimpleNamespace(actor="varshesha", planet="Sun", authority="mixed", authority_score=100.0),
            ),
            key_saham_rankings=(
                SimpleNamespace(
                    saham_name="Roga",
                    house=8,
                    ruler="Moon",
                    ruler_house=8,
                    ruler_strength=SimpleNamespace(total_score=40.0),
                    relevance_score=20.0,
                    authority="strained",
                ),
            ),
            mudda_period=None,
            supportive_yogas=(),
            obstructive_yogas=("Radda",),
            strongest_testimonies=("varshesha:Sun",),
            yearly_strength_balance="mixed",
            ascendant_authority_indication="mixed",
        ),
        natal_chart=SimpleNamespace(
            latitude=0.0,
            longitude=0.0,
            planets={"Moon": SimpleNamespace(speed=12.0), "Sun": SimpleNamespace(speed=1.0)},
        ),
        natal_sidereal_houses=houses,
        natal_sidereal_planets={"Sun": 180.0, "Moon": 210.0},
        natal_sahams=(SimpleNamespace(name="Roga", house=8, ruler="Moon"),),
        sidereal_houses=houses,
        sidereal_planets={"Sun": 0.0, "Moon": 210.0},
        birth_jd=2451545.0,
        varshesha=SimpleNamespace(planet="Sun"),
    )

    year = varshaphal_module.varshaphal_year_judgement(fake)

    assert year.prioritized_sahams == ()
    assert year.disregarded_sahams
    assert year.disregarded_sahams[0].saham_name == "Roga"


def test_varshaphal_year_judgement_lets_prioritized_sahams_temper_blocked_mudda() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    period = SimpleNamespace(
        major_result=SimpleNamespace(manifestation="blocked", result_fullness="withheld"),
        sub_result=SimpleNamespace(manifestation="manifest", result_fullness="full"),
        activation=SimpleNamespace(
            major_period=SimpleNamespace(lord="Moon"),
            sub_period=SimpleNamespace(lord="Sun"),
        ),
    )
    fake = SimpleNamespace(
        judgement=SimpleNamespace(
            actor_rankings=(
                SimpleNamespace(actor="varshesha", planet="Sun", authority="supportive", authority_score=160.0),
            ),
            key_saham_rankings=(
                SimpleNamespace(
                    saham_name="Punya",
                    house=1,
                    ruler="Sun",
                    ruler_house=1,
                    ruler_strength=SimpleNamespace(total_score=180.0),
                    relevance_score=180.0,
                    authority="supportive",
                ),
            ),
            mudda_period=period,
            supportive_yogas=("Ithasala",),
            obstructive_yogas=(),
            strongest_testimonies=("varshesha:Sun", "saham:Punya"),
            yearly_strength_balance="supportive",
            ascendant_authority_indication="supportive",
        ),
        natal_chart=SimpleNamespace(
            latitude=0.0,
            longitude=0.0,
            planets={"Sun": SimpleNamespace(speed=1.0)},
        ),
        natal_sidereal_houses=houses,
        natal_sidereal_planets={"Sun": 0.0},
        natal_sahams=(SimpleNamespace(name="Punya", house=1, ruler="Sun"),),
        sidereal_houses=houses,
        sidereal_planets={"Sun": 0.0},
        birth_jd=2451545.0,
        varshesha=SimpleNamespace(planet="Sun"),
    )

    year = varshaphal_module.varshaphal_year_judgement(fake)

    assert year.prioritized_sahams
    assert year.final_verdict == "mixed"
    assert year.conflict_resolution == "strong_sahams_temper_blocked_mudda_major"


def test_build_varshaphal_chart_collects_muntha_and_sahams(monkeypatch: pytest.MonkeyPatch) -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake_chart = SimpleNamespace(
        planets={
            "Sun": SimpleNamespace(longitude=100.0, speed=1.0),
            "Moon": SimpleNamespace(longitude=130.0, speed=12.0),
            "Mars": SimpleNamespace(longitude=160.0, speed=0.5),
            "Mercury": SimpleNamespace(longitude=190.0, speed=1.2),
            "Jupiter": SimpleNamespace(longitude=220.0, speed=0.1),
            "Venus": SimpleNamespace(longitude=250.0, speed=1.1),
            "Saturn": SimpleNamespace(longitude=280.0, speed=0.05),
        },
        is_day=True,
    )

    monkeypatch.setattr(
        varshaphal_module,
        "_varshaphal_jd",
        lambda birth_jd, year, **kwargs: 2460123.25 + (year - 2001) * 365.25,
    )
    monkeypatch.setattr(varshaphal_module, "_varshaphal_chart", lambda *args, **kwargs: fake_chart)
    monkeypatch.setattr(
        varshaphal_module,
        "all_planets_at",
        lambda *args, **kwargs: {"Moon": SimpleNamespace(longitude=130.0)},
    )
    monkeypatch.setattr(varshaphal_module, "create_chart", lambda *args, **kwargs: fake_chart)
    monkeypatch.setattr(varshaphal_module, "ayanamsa", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(varshaphal_module, "calculate_houses", lambda *args, **kwargs: houses)
    monkeypatch.setattr(varshaphal_module, "tropical_to_sidereal", lambda lon, jd, system=None: lon % 360.0)

    result = build_varshaphal_chart(
        birth_jd=2451545.0,
        natal_latitude=12.0,
        natal_longitude=77.0,
        year=2001,
        latitude=28.6,
        longitude=77.2,
        house_system=HouseSystem.WHOLE_SIGN,
    )

    assert result.return_year == 2001
    assert result.years_elapsed == 1
    assert result.muntha_longitude == pytest.approx((houses.asc + 30.0) % 360.0)
    assert result.muntha_profile.muntha_lord == result.muntha_lord
    assert result.muntha_profile.muntha_house == result.muntha_house
    assert result.varshesha.planet in result.sidereal_planets
    assert result.judgement is not None
    assert result.year_judgement is not None
    assert result.natal_sidereal_planets
    assert result.natal_sahams
    assert result.judgement.actor_rankings
    assert result.judgement.key_saham_rankings
    assert result.judgement.mudda_period is not None
    assert result.judgement.strongest_testimonies
    assert result.year_judgement.profile is result.judgement
    assert result.year_judgement.topics
    assert result.year_judgement.prioritized_sahams
    assert result.year_judgement.decisive_testimonies
    assert any(testimony.startswith("mudda_major:") for testimony in result.judgement.strongest_testimonies)
    assert any(aspect.relation == "open_friend" for aspect in result.tajika_aspects)
    assert any(yoga.name in {"Ithasala", "Isarpha", "Nakta", "Yamaya", "Kamboola", "Manahoo", "Radda", "Dupparikutha", "Thambira"} for yoga in result.tajika_yogas)
    assert result.saham("Punya").name == "Punya"
    assert result.muntha_house in range(1, 13)
    assert result.mudda_dasha.year_ruler in result.sidereal_planets
    assert result.mudda_dasha.periods[0].start_jd == pytest.approx(result.jd_ut)
    assert result.mudda_dasha.periods[-1].end_jd == pytest.approx(result.mudda_dasha.year_end_jd)
    assert result.tasira_dasha.periods
    assert result.tasira_dasha.periods[0].start_jd == pytest.approx(result.mudda_dasha.year_start_jd)
    assert result.tasira_dasha.periods[-1].end_jd == pytest.approx(result.mudda_dasha.year_end_jd)
