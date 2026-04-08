"""
Unit tests for moira.shadbala.

Coverage
--------
1.  NAISARGIKA_BALA constants — all 7 planets present, canonical values.
2.  REQUIRED_RUPAS constants — all 7 planets present, canonical values.
3.  MEAN_DAILY_MOTION constants — all 7 planets present, positive values.
4.  chesta_bala() — retrograde, standstill, mean speed, capped maximum.
5.  drig_bala() — Jupiter 7th-sign opposition, Saturn 7th-sign opposition,
    Mars special 4th/8th aspects, no aspect → 0.
6.  kala_bala() — Mercury always-60 fields, Vara lord bonus, Paksha Bala
    computation for benefics and malefics, tithi boundary.
7.  sthana_bala() — returns SthanaBala; total == sum of sub-components.
8.  dig_bala() — returns a float in [0, 60]; at strong cusp → maximum (≈60).
9.  shadbala() integration — returns ShadbalaResult; all 7 planets present;
    total_rupas == total_shashtiamsas / 60; is_sufficient reflects threshold;
    invalid tithi raises ValueError.
10. Vessel invariants — SthanaBala, KalaBala, PlanetShadbala, ShadbalaResult
    are all frozen; have no __dict__ (slots=True).
11. Public surface — all __all__ names importable.

Source authority: Parashara BPHS Shadbala Adhyaya;
                  B.V. Raman, "Graha and Bhava Balas" (1959).
"""
from __future__ import annotations

import math
import pytest

from moira.shadbala import (
    MEAN_DAILY_MOTION,
    NAISARGIKA_BALA,
    REQUIRED_RUPAS,
    KalaBala,
    PlanetShadbala,
    ShadbalaChartProfile,
    ShadbalaConditionProfile,
    ShadbalaPolicy,
    ShadbalaResult,
    ShadbalaTier,
    SthanaBala,
    chesta_bala,
    dig_bala,
    drig_bala,
    kala_bala,
    shadbala,
    shadbala_chart_profile,
    shadbala_condition_profile,
    sthana_bala,
    validate_shadbala_output,
)

_J2000 = 2451545.0
_PLANETS = ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn')


# ---------------------------------------------------------------------------
# Minimal house stub — equal-house, tropical Ascendant at 0°
# ---------------------------------------------------------------------------

class _MockHouses:
    """Equal-house stub: tropical Ascendant = 0°, cusps every 30°."""
    asc: float = 0.0
    cusps: tuple[float, ...] = tuple(float(i * 30) for i in range(12))


# ---------------------------------------------------------------------------
# Typical sidereal longitudes for integration tests (one planet per sign)
# ---------------------------------------------------------------------------

_LONS: dict[str, float] = {
    'Sun':     0.0,
    'Moon':    30.0,
    'Mars':    60.0,
    'Mercury': 90.0,
    'Jupiter': 120.0,
    'Venus':   150.0,
    'Saturn':  180.0,
}

_SPEEDS: dict[str, float] = {p: MEAN_DAILY_MOTION[p] for p in _PLANETS}


# ===========================================================================
# 1. NAISARGIKA_BALA constants
# ===========================================================================

class TestNaisargikaBala:

    def test_has_all_seven_planets(self):
        for p in _PLANETS:
            assert p in NAISARGIKA_BALA, f"NAISARGIKA_BALA missing {p!r}"

    def test_sun_is_60(self):
        assert NAISARGIKA_BALA['Sun'] == pytest.approx(60.00)

    def test_saturn_is_8_57(self):
        assert NAISARGIKA_BALA['Saturn'] == pytest.approx(8.57)

    def test_sun_is_maximum(self):
        assert NAISARGIKA_BALA['Sun'] == max(NAISARGIKA_BALA.values())

    def test_saturn_is_minimum(self):
        assert NAISARGIKA_BALA['Saturn'] == min(NAISARGIKA_BALA.values())

    def test_all_values_positive(self):
        for p, v in NAISARGIKA_BALA.items():
            assert v > 0.0, f"NAISARGIKA_BALA[{p!r}] is not positive"

    def test_descending_order_by_tradition(self):
        # Canonical order: Sun > Moon > Venus > Jupiter > Mercury > Mars > Saturn
        order = ('Sun', 'Moon', 'Venus', 'Jupiter', 'Mercury', 'Mars', 'Saturn')
        for i in range(len(order) - 1):
            assert NAISARGIKA_BALA[order[i]] > NAISARGIKA_BALA[order[i + 1]]


# ===========================================================================
# 2. REQUIRED_RUPAS constants
# ===========================================================================

class TestRequiredRupas:

    def test_has_all_seven_planets(self):
        for p in _PLANETS:
            assert p in REQUIRED_RUPAS

    def test_mercury_is_highest_at_7(self):
        assert REQUIRED_RUPAS['Mercury'] == 7.0

    def test_sun_is_6_5(self):
        assert REQUIRED_RUPAS['Sun'] == 6.5

    def test_all_values_between_4_and_8(self):
        for p, v in REQUIRED_RUPAS.items():
            assert 4.0 <= v <= 8.0, f"REQUIRED_RUPAS[{p!r}] = {v} out of expected range"


# ===========================================================================
# 3. MEAN_DAILY_MOTION constants
# ===========================================================================

class TestMeanDailyMotion:

    def test_has_all_seven_planets(self):
        for p in _PLANETS:
            assert p in MEAN_DAILY_MOTION

    def test_all_values_positive(self):
        for p, v in MEAN_DAILY_MOTION.items():
            assert v > 0.0

    def test_moon_fastest(self):
        assert MEAN_DAILY_MOTION['Moon'] == max(MEAN_DAILY_MOTION.values())

    def test_saturn_slowest(self):
        assert MEAN_DAILY_MOTION['Saturn'] == min(MEAN_DAILY_MOTION.values())


# ===========================================================================
# 4. chesta_bala()
# ===========================================================================

class TestChestaBala:

    def test_retrograde_gives_60(self):
        assert chesta_bala('Mars', -0.3) == 60.0

    def test_standstill_gives_0(self):
        assert chesta_bala('Jupiter', 0.0) == pytest.approx(0.0)

    def test_mean_speed_gives_30(self):
        for p in _PLANETS:
            assert chesta_bala(p, MEAN_DAILY_MOTION[p]) == pytest.approx(30.0)

    def test_double_mean_speed_gives_60(self):
        for p in _PLANETS:
            assert chesta_bala(p, 2.0 * MEAN_DAILY_MOTION[p]) == pytest.approx(60.0)

    def test_beyond_double_is_capped_at_60(self):
        assert chesta_bala('Sun', 100.0) == pytest.approx(60.0)


# ===========================================================================
# 5. drig_bala()
# ===========================================================================

class TestDrigBala:

    def test_jupiter_opposing_benefic_adds_positive(self):
        # Jupiter at Aries (sign 0) opposes a planet at Libra (sign 6)
        # dist = (6 - 0) % 12 + 1 = 7 → full aspect, weight 1.0
        # Jupiter is benefic → +60.0 Sha
        lons = {
            'Jupiter': 10.0,   # in Aries
            'Venus':   190.0,  # in Libra
        }
        score = drig_bala('Venus', lons)
        assert score == pytest.approx(60.0)

    def test_saturn_opposing_planet_subtracts(self):
        # Saturn at sign 0 opposes planet at sign 6
        lons = {
            'Saturn': 10.0,   # Aries
            'Sun':   190.0,  # Libra
        }
        score = drig_bala('Sun', lons)
        assert score == pytest.approx(-60.0)

    def test_mars_special_4th_aspect(self):
        # Mars at sign 0, target at sign 3 (4th from Mars)
        # dist = (3 - 0) % 12 + 1 = 4 → Mars special, weight 0.75
        # Mars is malefic → -45.0 Sha
        lons = {
            'Mars':  5.0,     # Aries (sign 0)
            'Moon': 95.0,    # Cancer (sign 3)
        }
        score = drig_bala('Moon', lons)
        assert score == pytest.approx(-45.0)

    def test_jupiter_5th_special_aspect(self):
        # Jupiter at sign 0, target at sign 4 (5th from Jupiter)
        # weight 0.75, Jupiter is benefic → +45.0 Sha
        lons = {
            'Jupiter': 5.0,    # Aries (sign 0)
            'Mercury': 125.0,  # Leo (sign 4)
        }
        score = drig_bala('Mercury', lons)
        assert score == pytest.approx(45.0)

    def test_no_aspects_gives_0(self):
        # Single planet in dict (itself only)
        lons = {'Sun': 0.0}
        assert drig_bala('Sun', lons) == pytest.approx(0.0)


# ===========================================================================
# 6. kala_bala()
# ===========================================================================

class TestKalaBala:

    def _call(self, planet, is_day=True, tithi=1, vara_lord='Sun'):
        return kala_bala(
            planet, 0.0, 0.0, _J2000,
            tithi_number=tithi,
            is_day=is_day,
            vara_lord=vara_lord,
            planet_speeds=_SPEEDS,
        )

    def test_mercury_nathonnatha_always_60(self):
        r_day   = self._call('Mercury', is_day=True)
        r_night = self._call('Mercury', is_day=False)
        assert r_day.nathonnatha   == pytest.approx(60.0)
        assert r_night.nathonnatha == pytest.approx(60.0)

    def test_mercury_tribhaga_always_60(self):
        r_day   = self._call('Mercury', is_day=True)
        r_night = self._call('Mercury', is_day=False)
        assert r_day.tribhaga   == pytest.approx(60.0)
        assert r_night.tribhaga == pytest.approx(60.0)

    def test_vara_lord_gets_45_sha(self):
        # Vara Bala = 45 Sha per Raman Ch. 4.
        # With sun_sidereal_lon=0.0 at J2000 (Saturday), both Abda and Masa
        # lords are Saturn (Sankranti is "now" → same weekday as current JD).
        # Sun != Saturn, so only Vara (45 Sha) contributes for Sun.
        r = self._call('Sun', vara_lord='Sun')
        assert r.abda_masa_vara_hora == pytest.approx(45.0)

    def test_planet_matching_no_lord_gets_0_amvh(self):
        # With sun_sidereal_lon=0.0 at J2000 (Saturday=Saturn), both Abda and
        # Masa lords are Saturn.  Moon is not Saturn (abda/masa) and not Sun
        # (vara), so abda_masa_vara_hora = 0.
        r = self._call('Moon', vara_lord='Sun')
        assert r.abda_masa_vara_hora == pytest.approx(0.0)

    def test_paksha_for_benefic_waxing(self):
        # Tithi 10, Moon is benefic → paksha = 10 * 4 = 40
        r = self._call('Moon', tithi=10)
        assert r.paksha == pytest.approx(40.0)

    def test_paksha_for_malefic_waxing(self):
        # Tithi 10, Sun is malefic → shukla=10, paksha = (15-10) * 4 = 20
        r = self._call('Sun', tithi=10)
        assert r.paksha == pytest.approx(20.0)

    def test_total_equals_sum_of_components(self):
        r = self._call('Venus')
        expected = (r.nathonnatha + r.paksha + r.tribhaga +
                    r.abda_masa_vara_hora + r.ayana + r.yuddha)
        assert r.total == pytest.approx(expected)

    def test_kala_bala_returns_kala_bala_instance(self):
        r = self._call('Jupiter')
        assert isinstance(r, KalaBala)

    def test_abda_lord_recognized(self):
        # JD 2451316.0: Sun sidereal ~32.3° (Lahiri); Mesha Sankranti falls at
        # JD 2451282.74 (Abda lord = Mercury), verified by kernel bisection.
        # vara_lord is set to Saturn (≠ Mercury) to isolate the Abda component.
        _TAURUS_JD = 2451316.0
        r = kala_bala('Mercury', 32.3, 32.3, _TAURUS_JD,
                      tithi_number=1, is_day=True,
                      vara_lord='Saturn', planet_speeds=_SPEEDS)
        assert r.abda_masa_vara_hora >= 15.0, (
            f"Mercury should get at least Abda Bala (15 Sha) "
            f"but got {r.abda_masa_vara_hora}"
        )

    def test_masa_lord_recognized(self):
        # JD 2451316.0: Sun sidereal ~32.3° (Lahiri); Taurus Sankranti (30°) falls
        # at JD 2451313.61 (Masa lord = Saturn), verified by kernel bisection.
        # vara_lord is set to Jupiter (≠ Saturn) to isolate the Masa component.
        _TAURUS_JD = 2451316.0
        r = kala_bala('Saturn', 32.3, 32.3, _TAURUS_JD,
                      tithi_number=1, is_day=True,
                      vara_lord='Jupiter', planet_speeds=_SPEEDS)
        assert r.abda_masa_vara_hora >= 30.0, (
            f"Saturn should get at least Masa Bala (30 Sha) "
            f"but got {r.abda_masa_vara_hora}"
        )


# ===========================================================================
# 7. sthana_bala()
# ===========================================================================

class TestSthanaBala:

    def test_returns_sthana_bala_instance(self):
        result = sthana_bala('Sun', 10.0, _MockHouses(), _J2000)
        assert isinstance(result, SthanaBala)

    def test_total_equals_sum_of_sub_components(self):
        for planet in _PLANETS:
            lon = _LONS[planet]
            s = sthana_bala(planet, lon, _MockHouses(), _J2000)
            expected = s.uchcha + s.saptavargaja + s.ojayugma + s.kendradi + s.drekkana
            assert s.total == pytest.approx(expected)

    def test_uchcha_range_is_0_to_60(self):
        for planet in _PLANETS:
            s = sthana_bala(planet, _LONS[planet], _MockHouses(), _J2000)
            assert 0.0 <= s.uchcha <= 60.0

    def test_kendradi_is_one_of_three_values(self):
        valid = {15.0, 30.0, 60.0}
        for planet in _PLANETS:
            s = sthana_bala(planet, _LONS[planet], _MockHouses(), _J2000)
            assert s.kendradi in valid


# ===========================================================================
# 8. dig_bala() function (integration with houses)
# ===========================================================================

class TestDigBala:

    def test_returns_float(self):
        assert isinstance(dig_bala('Sun', 0.0, _MockHouses(), _J2000), float)

    def test_result_in_0_to_60_range(self):
        for planet in _PLANETS:
            val = dig_bala(planet, _LONS[planet], _MockHouses(), _J2000)
            assert 0.0 <= val <= 60.0, f"{planet} dig_bala={val} out of range"


# ===========================================================================
# 9. shadbala() integration
# ===========================================================================

class TestShadbalaIntegration:

    @pytest.fixture(scope='class')
    def result(self) -> ShadbalaResult:
        return shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=10,
            vara_lord='Sun',
            is_day=True,
        )

    def test_returns_shadbala_result(self, result):
        assert isinstance(result, ShadbalaResult)

    def test_all_seven_planets_present(self, result):
        for p in _PLANETS:
            assert p in result.planets

    def test_total_rupas_equals_sha_over_60(self, result):
        for p, ps in result.planets.items():
            assert ps.total_rupas == pytest.approx(ps.total_shashtiamsas / 60.0)

    def test_is_sufficient_reflects_threshold(self, result):
        for p, ps in result.planets.items():
            expected = ps.total_rupas >= ps.required_rupas
            assert ps.is_sufficient == expected

    def test_naisargika_bala_matches_constant(self, result):
        for p, ps in result.planets.items():
            assert ps.naisargika_bala == pytest.approx(NAISARGIKA_BALA[p])

    def test_required_rupas_matches_constant(self, result):
        for p, ps in result.planets.items():
            assert ps.required_rupas == pytest.approx(REQUIRED_RUPAS[p])

    def test_all_sha_values_are_finite(self, result):
        for p, ps in result.planets.items():
            assert math.isfinite(ps.total_shashtiamsas), f"{p} total_sha is not finite"

    def test_jd_stored_correctly(self, result):
        assert result.jd == pytest.approx(_J2000)

    def test_chesta_bala_in_each_planet_result(self, result):
        for p, ps in result.planets.items():
            assert math.isfinite(ps.chesta_bala)

    def test_invalid_tithi_raises_value_error(self):
        with pytest.raises(ValueError, match="tithi_number"):
            shadbala(
                sidereal_longitudes=_LONS,
                planet_speeds=_SPEEDS,
                houses=_MockHouses(),
                jd=_J2000,
                tithi_number=0,   # invalid: must be 1–30
                vara_lord='Sun',
                is_day=True,
            )


# ===========================================================================
# 10. Vessel invariants
# ===========================================================================

class TestVesselInvariants:

    def _planet_shadbala(self) -> PlanetShadbala:
        result = shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=1,
            vara_lord='Sun',
            is_day=True,
        )
        return result.planets['Sun']

    def test_sthana_bala_is_frozen(self):
        ps = self._planet_shadbala()
        with pytest.raises((AttributeError, TypeError)):
            ps.sthana_bala.uchcha = 999.0  # type: ignore[misc]

    def test_kala_bala_is_frozen(self):
        ps = self._planet_shadbala()
        with pytest.raises((AttributeError, TypeError)):
            ps.kala_bala.paksha = 999.0  # type: ignore[misc]

    def test_planet_shadbala_is_frozen(self):
        ps = self._planet_shadbala()
        with pytest.raises((AttributeError, TypeError)):
            ps.planet = "mutated"  # type: ignore[misc]

    def test_shadbala_result_is_frozen(self):
        result = shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=1,
            vara_lord='Sun',
            is_day=True,
        )
        with pytest.raises((AttributeError, TypeError)):
            result.jd = 0.0  # type: ignore[misc]

    def test_sthana_bala_has_slots(self):
        ps = self._planet_shadbala()
        assert "__dict__" not in type(ps.sthana_bala).__slots__

    def test_planet_shadbala_has_slots(self):
        ps = self._planet_shadbala()
        assert "__dict__" not in type(ps).__slots__


# ===========================================================================
# 11. Public surface
# ===========================================================================

class TestHoraLordAt:
    """hora_lord_at() — Chaldean hora sequence from sunrise JD."""

    # At J2000 (Saturday = Saturn), we use a synthetic sunrise 6 h before noon.
    _SUNRISE = _J2000 - 6.0 / 24.0   # 06:00 UT on J2000 day

    def test_returns_string(self):
        from moira.shadbala import hora_lord_at
        result = hora_lord_at(_J2000, self._SUNRISE)
        assert isinstance(result, str)

    def test_first_hora_equals_vara_lord(self):
        # Birth 30 min after sunrise (midpoint of first hora): lord = Saturn.
        from moira.shadbala import hora_lord_at
        assert hora_lord_at(self._SUNRISE + 0.5 / 24, self._SUNRISE) == 'Saturn'

    def test_second_hora_follows_chaldean(self):
        # Saturn's next hora in Chaldean sequence is Jupiter.
        # Use midpoint of second hora (1.5 h after sunrise) to avoid float edge.
        from moira.shadbala import hora_lord_at
        assert hora_lord_at(self._SUNRISE + 1.5 / 24, self._SUNRISE) == 'Jupiter'

    def test_sixth_hora_from_saturn(self):
        # Saturn (idx=4) + 6 steps in HORA_SEQUENCE = idx 10 % 7 = 3 = Moon.
        # Use midpoint of seventh hora (6.5 h after sunrise).
        from moira.shadbala import hora_lord_at
        assert hora_lord_at(self._SUNRISE + 6.5 / 24, self._SUNRISE) == 'Moon'

    def test_result_always_one_of_seven_planets(self):
        from moira.shadbala import hora_lord_at
        valid = {'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'}
        for h in range(7):
            lord = hora_lord_at(self._SUNRISE + h / 24, self._SUNRISE)
            assert lord in valid

    def test_uses_hora_lord_in_kala_bala(self):
        # Passing hora_lord='Sun' to kala_bala for planet='Sun' adds 60 Sha.
        r_no_hora = kala_bala('Sun', 0.0, 0.0, _J2000, 1, True, 'Sun', _SPEEDS)
        r_with_hora = kala_bala('Sun', 0.0, 0.0, _J2000, 1, True, 'Sun', _SPEEDS,
                                hora_lord='Sun')
        assert r_with_hora.abda_masa_vara_hora == pytest.approx(
            r_no_hora.abda_masa_vara_hora + 60.0
        )


# ===========================================================================
# 12. Public surface
# ===========================================================================

class TestPublicSurface:

    @staticmethod
    def _mod():
        import importlib
        return importlib.import_module('moira.shadbala')

    def test_all_all_names_importable(self):
        mod = self._mod()
        for name in mod.__all__:
            assert hasattr(mod, name), f"__all__ lists {name!r} but absent"

    def test_key_names_in_all(self):
        mod = self._mod()
        for name in ('NAISARGIKA_BALA', 'REQUIRED_RUPAS', 'SthanaBala',
                     'KalaBala', 'PlanetShadbala', 'ShadbalaResult',
                     'sthana_bala', 'dig_bala', 'kala_bala',
                     'chesta_bala', 'drig_bala', 'shadbala',
                     'hora_lord_at'):
            assert name in mod.__all__


# ===========================================================================
# 13. ShadbalaTier -- P2
# ===========================================================================

class TestShadbalaTier:

    def test_sufficient_constant_value(self):
        assert ShadbalaTier.SUFFICIENT == 'sufficient'

    def test_insufficient_constant_value(self):
        assert ShadbalaTier.INSUFFICIENT == 'insufficient'

    def test_constants_are_distinct(self):
        assert ShadbalaTier.SUFFICIENT != ShadbalaTier.INSUFFICIENT


# ===========================================================================
# 14. ShadbalaPolicy -- P4
# ===========================================================================

class TestShadbalaPolicy:

    def test_default_ayanamsa_is_lahiri(self):
        p = ShadbalaPolicy()
        assert p.ayanamsa_system == 'Lahiri'

    def test_custom_ayanamsa_accepted(self):
        p = ShadbalaPolicy(ayanamsa_system='Krishnamurti')
        assert p.ayanamsa_system == 'Krishnamurti'

    def test_empty_ayanamsa_raises(self):
        with pytest.raises(ValueError):
            ShadbalaPolicy(ayanamsa_system='')

    def test_policy_is_frozen(self):
        p = ShadbalaPolicy()
        with pytest.raises((AttributeError, TypeError)):
            p.ayanamsa_system = 'mutated'  # type: ignore[misc]


# ===========================================================================
# 15. PlanetShadbala.strength_ratio -- P3
# ===========================================================================

class TestStrengthRatio:

    @pytest.fixture(scope='class')
    def result(self) -> ShadbalaResult:
        return shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=10,
            vara_lord='Sun',
            is_day=True,
        )

    def test_strength_ratio_equals_rupas_over_required(self, result):
        for p, ps in result.planets.items():
            expected = ps.total_rupas / ps.required_rupas
            assert ps.strength_ratio == pytest.approx(expected)

    def test_sufficient_planet_has_ratio_ge_one(self, result):
        for p, ps in result.planets.items():
            if ps.is_sufficient:
                assert ps.strength_ratio >= 1.0

    def test_insufficient_planet_has_ratio_lt_one(self, result):
        for p, ps in result.planets.items():
            if not ps.is_sufficient:
                assert ps.strength_ratio < 1.0


# ===========================================================================
# 16. PlanetShadbala guards -- P10
# ===========================================================================

class TestPlanetShadbalaGuards:

    def _make_stub_sthanabala(self) -> SthanaBala:
        return SthanaBala(
            uchcha=30.0, saptavargaja=60.0, ojayugma=15.0,
            kendradi=60.0, drekkana=15.0, total=180.0,
        )

    def _make_stub_kalabala(self) -> KalaBala:
        return KalaBala(
            nathonnatha=30.0, paksha=30.0, tribhaga=0.0,
            abda_masa_vara_hora=90.0, ayana=30.0, yuddha=0.0, total=180.0,
        )

    def test_invalid_planet_raises(self):
        with pytest.raises(ValueError):
            PlanetShadbala(
                planet='Pluto',
                sthana_bala=self._make_stub_sthanabala(),
                dig_bala=30.0,
                kala_bala=self._make_stub_kalabala(),
                chesta_bala=30.0,
                naisargika_bala=60.0,
                drig_bala=5.0,
                total_shashtiamsas=505.0,
                total_rupas=505.0 / 60.0,
                required_rupas=6.5,
                is_sufficient=True,
            )

    def test_negative_total_sha_raises(self):
        with pytest.raises(ValueError):
            PlanetShadbala(
                planet='Sun',
                sthana_bala=self._make_stub_sthanabala(),
                dig_bala=30.0,
                kala_bala=self._make_stub_kalabala(),
                chesta_bala=30.0,
                naisargika_bala=60.0,
                drig_bala=5.0,
                total_shashtiamsas=-1.0,
                total_rupas=-1.0 / 60.0,
                required_rupas=6.5,
                is_sufficient=False,
            )

    def test_zero_required_rupas_raises(self):
        with pytest.raises(ValueError):
            PlanetShadbala(
                planet='Sun',
                sthana_bala=self._make_stub_sthanabala(),
                dig_bala=30.0,
                kala_bala=self._make_stub_kalabala(),
                chesta_bala=30.0,
                naisargika_bala=60.0,
                drig_bala=5.0,
                total_shashtiamsas=505.0,
                total_rupas=505.0 / 60.0,
                required_rupas=0.0,
                is_sufficient=False,
            )


# ===========================================================================
# 17. ShadbalaConditionProfile -- P7
# ===========================================================================

class TestShadbalaConditionProfile:

    @pytest.fixture(scope='class')
    def planet_result(self) -> PlanetShadbala:
        r = shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=10,
            vara_lord='Sun',
            is_day=True,
        )
        return r.planets['Sun']

    def test_tier_matches_is_sufficient(self, planet_result):
        prof = shadbala_condition_profile(planet_result)
        if planet_result.is_sufficient:
            assert prof.tier == ShadbalaTier.SUFFICIENT
        else:
            assert prof.tier == ShadbalaTier.INSUFFICIENT

    def test_planet_propagated(self, planet_result):
        prof = shadbala_condition_profile(planet_result)
        assert prof.planet == 'Sun'

    def test_total_rupas_matches(self, planet_result):
        prof = shadbala_condition_profile(planet_result)
        assert prof.total_rupas == planet_result.total_rupas

    def test_strength_ratio_matches(self, planet_result):
        prof = shadbala_condition_profile(planet_result)
        assert prof.strength_ratio == pytest.approx(planet_result.strength_ratio)

    def test_profile_is_frozen(self, planet_result):
        prof = shadbala_condition_profile(planet_result)
        with pytest.raises((AttributeError, TypeError)):
            prof.tier = ShadbalaTier.INSUFFICIENT  # type: ignore[misc]


# ===========================================================================
# 18. ShadbalaChartProfile -- P8
# ===========================================================================

class TestShadbalaChartProfile:

    @pytest.fixture(scope='class')
    def result(self) -> ShadbalaResult:
        return shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=10,
            vara_lord='Sun',
            is_day=True,
        )

    def test_sufficient_plus_insufficient_equals_total(self, result):
        prof = shadbala_chart_profile(result)
        assert prof.sufficient_count + prof.insufficient_count == len(result.planets)

    def test_strongest_has_highest_ratio(self, result):
        prof = shadbala_chart_profile(result)
        max_ratio = max(ps.strength_ratio for ps in result.planets.values())
        assert result.planets[prof.strongest_planet].strength_ratio == pytest.approx(max_ratio)

    def test_weakest_has_lowest_ratio(self, result):
        prof = shadbala_chart_profile(result)
        min_ratio = min(ps.strength_ratio for ps in result.planets.values())
        assert result.planets[prof.weakest_planet].strength_ratio == pytest.approx(min_ratio)

    def test_planet_tiers_keys_match_planets(self, result):
        prof = shadbala_chart_profile(result)
        assert set(prof.planet_tiers.keys()) == set(result.planets.keys())

    def test_strength_ratios_keys_match_planets(self, result):
        prof = shadbala_chart_profile(result)
        assert set(prof.strength_ratios.keys()) == set(result.planets.keys())

    def test_ayanamsa_system_propagated(self, result):
        prof = shadbala_chart_profile(result)
        assert prof.ayanamsa_system == result.ayanamsa_system

    def test_profile_is_frozen(self, result):
        prof = shadbala_chart_profile(result)
        with pytest.raises((AttributeError, TypeError)):
            prof.sufficient_count = 0  # type: ignore[misc]


# ===========================================================================
# 19. validate_shadbala_output -- P10
# ===========================================================================

class TestValidateShadbalaOutput:

    @pytest.fixture(scope='class')
    def result(self) -> ShadbalaResult:
        return shadbala(
            sidereal_longitudes=_LONS,
            planet_speeds=_SPEEDS,
            houses=_MockHouses(),
            jd=_J2000,
            tithi_number=10,
            vara_lord='Sun',
            is_day=True,
        )

    def test_valid_result_does_not_raise(self, result):
        validate_shadbala_output(result)  # must not raise

    def test_key_planet_mismatch_raises(self, result):
        sun_ps = result.planets['Sun']
        bad_planets = dict(result.planets)
        bad_planets['Moon'] = sun_ps  # key=Moon but planet=Sun
        bad_result = ShadbalaResult.__new__(ShadbalaResult)
        object.__setattr__(bad_result, 'jd', result.jd)
        object.__setattr__(bad_result, 'ayanamsa_system', result.ayanamsa_system)
        object.__setattr__(bad_result, 'planets', bad_planets)
        with pytest.raises(ValueError):
            validate_shadbala_output(bad_result)
