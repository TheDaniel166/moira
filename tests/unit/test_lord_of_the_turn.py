"""
Unit tests for moira/lord_of_the_turn.py — Lord of the Turn engine.

Coverage targets:
- Profection arithmetic (age → sign / degree)
- Al-Qabisi succession hierarchy (domicile → exaltation → triplicity → bound)
- All four Al-Qabisi selection reasons
- Egyptian/Al-Sijzi: bound primary, testimony winner, bound fallback
- Witnessing (whole-sign Ptolemaic aspects)
- Combust check and retrograde block
- Inspectability properties on LordOfTurnResult
- LordOfTurnConditionProfile integration
- lord_of_turn() dispatch function
- validate_lord_of_turn_output() checks
- Policy surface
- Input validation
- Edge cases
"""

import math
import pytest

from moira.lord_of_the_turn import (
    LordOfTurnMethod,
    LordOfTurnSelectionReason,
    LordOfTurnBlockerReason,
    LordOfTurnPolicy,
    DEFAULT_LORD_OF_TURN_POLICY,
    LordOfTurnSRChart,
    LordOfTurnProfection,
    LordOfTurnCandidateAssessment,
    LordOfTurnResult,
    LordOfTurnConditionProfile,
    lord_of_turn,
    lord_of_turn_al_qabisi,
    lord_of_turn_egyptian_al_sijzi,
    validate_lord_of_turn_output,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _day_sr_minimal(asc: float = 0.0, **planet_lons) -> LordOfTurnSRChart:
    """SR chart without house_placements — triggers DOMICILE_ONLY mode."""
    return LordOfTurnSRChart(sr_asc=asc, planets=dict(planet_lons), is_night=False)


def _day_sr(asc: float, planets: dict, houses: dict,
            retro: frozenset = frozenset()) -> LordOfTurnSRChart:
    return LordOfTurnSRChart(
        sr_asc=asc, planets=planets, house_placements=houses,
        is_night=False, retrograde_planets=retro,
    )


def _night_sr(asc: float, planets: dict, houses: dict,
              retro: frozenset = frozenset()) -> LordOfTurnSRChart:
    return LordOfTurnSRChart(
        sr_asc=asc, planets=planets, house_placements=houses,
        is_night=True, retrograde_planets=retro,
    )


_AL_QABISI = LordOfTurnPolicy(method=LordOfTurnMethod.AL_QABISI)
_EGYPTIAN  = LordOfTurnPolicy(method=LordOfTurnMethod.EGYPTIAN_AL_SIJZI)

# Sign longitudes — start of each sign
_ARIES      =   0.0
_TAURUS     =  30.0
_GEMINI     =  60.0
_CANCER     =  90.0
_LEO        = 120.0
_VIRGO      = 150.0
_LIBRA      = 180.0
_SCORPIO    = 210.0
_SAGITTARIUS= 240.0
_CAPRICORN  = 270.0
_AQUARIUS   = 300.0
_PISCES     = 330.0


# ---------------------------------------------------------------------------
# §1. Profection arithmetic
# ---------------------------------------------------------------------------

class TestProfectionArithmetic:
    """(age * 30 + natal_asc) % 360 gives the profected longitude."""

    def test_age_0_natal_aries_is_aries(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.profection.profected_sign == "Aries"

    def test_age_1_natal_aries_is_taurus(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 1, sr)
        assert r.profection.profected_sign == "Taurus"

    def test_age_11_natal_aries_is_pisces(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 11, sr)
        assert r.profection.profected_sign == "Pisces"

    def test_age_12_natal_aries_wraps_to_aries(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 12, sr)
        assert r.profection.profected_sign == "Aries"

    def test_natal_15_age_2_gives_gemini_15(self):
        # (2*30 + 15) % 360 = 75 → Gemini 15°
        sr = _day_sr_minimal(asc=15.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(15.0, 2, sr)
        assert r.profection.profected_sign == "Gemini"
        assert abs(r.profection.profected_degree_in_sign - 15.0) < 1e-9

    def test_profected_longitude_formula(self):
        # natal_asc=0, age=4 → 120.0 (Leo 0°)
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 4, sr)
        assert abs(r.profection.profected_longitude - 120.0) < 1e-9

    def test_sign_index_matches_sign(self):
        # Taurus = index 1
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 1, sr)
        assert r.profection.profected_sign_index == 1


# ---------------------------------------------------------------------------
# §2. Al-Qabisi — DOMICILE_ONLY (no house placements)
# ---------------------------------------------------------------------------

class TestAlQabisiDomicileOnly:
    """Without house_placements the engine returns the domicile lord unconditionally."""

    def test_aries_returns_mars(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.lord == "Mars"
        assert r.selection_reason is LordOfTurnSelectionReason.DOMICILE_ONLY

    def test_taurus_returns_venus(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 1, sr)
        assert r.lord == "Venus"

    def test_cancer_returns_moon(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 3, sr)
        assert r.lord == "Moon"

    def test_leo_returns_sun(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 4, sr)
        assert r.lord == "Sun"

    def test_sagittarius_returns_jupiter(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 8, sr)  # age=8 → Sagittarius
        assert r.lord == "Jupiter"

    def test_single_candidate_present(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert len(r.candidates) == 1
        assert r.candidates[0].role == "domicile"


# ---------------------------------------------------------------------------
# §3. Al-Qabisi — DOMICILE_WELL_PLACED
# ---------------------------------------------------------------------------

class TestAlQabisiDomicileWellPlaced:
    """
    Aries (age=0), dom=Mars.  Mars in house 1 (good), Sun far away (not combust),
    not retrograde → DOMICILE_WELL_PLACED.
    """

    def setup_method(self):
        self.sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
        )
        self.r = lord_of_turn_al_qabisi(0.0, 0, self.sr)

    def test_lord_is_mars(self):
        assert self.r.lord == "Mars"

    def test_reason_is_domicile_well_placed(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.DOMICILE_WELL_PLACED

    def test_method_is_al_qabisi(self):
        assert self.r.method is LordOfTurnMethod.AL_QABISI

    def test_candidate_is_well_placed(self):
        assert self.r.candidates[0].is_well_placed

    def test_no_blocker_reasons(self):
        assert self.r.candidates[0].blocker_reasons == ()


# ---------------------------------------------------------------------------
# §4. Al-Qabisi — EXALTATION_FALLBACK
# ---------------------------------------------------------------------------

class TestAlQabisiExaltationFallback:
    """
    Aries: dom=Mars in house 3 (cadent → blocked), exalt=Sun in house 1 → well-placed.
    """

    def setup_method(self):
        self.sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 3, "Sun": 1},
        )
        self.r = lord_of_turn_al_qabisi(0.0, 0, self.sr)

    def test_lord_is_sun(self):
        assert self.r.lord == "Sun"

    def test_reason_is_exaltation_fallback(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.EXALTATION_FALLBACK

    def test_mars_in_candidates(self):
        assert any(c.planet == "Mars" for c in self.r.candidates)

    def test_mars_is_blocked(self):
        mars = next(c for c in self.r.candidates if c.planet == "Mars")
        assert not mars.is_well_placed
        assert LordOfTurnBlockerReason.CADENT_IN_SR in mars.blocker_reasons


# ---------------------------------------------------------------------------
# §5. Al-Qabisi — TRIPLICITY_FALLBACK
# ---------------------------------------------------------------------------

class TestAlQabisiTriplicityFallback:
    """
    Aries night chart.  dom=Mars (cadent), exalt=Sun (cadent).
    Night triplicity of Aries = Jupiter.  Jupiter in house 1 (angular) → winner.
    """

    def setup_method(self):
        self.sr = _night_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 270.0, "Mars": 5.0, "Jupiter": 60.0},
            houses={"Mars": 3, "Sun": 3, "Jupiter": 1},
        )
        self.r = lord_of_turn_al_qabisi(0.0, 0, self.sr)

    def test_lord_is_jupiter(self):
        assert self.r.lord == "Jupiter"

    def test_reason_is_triplicity_fallback(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.TRIPLICITY_FALLBACK

    def test_mars_and_sun_blocked(self):
        blocked = {c.planet for c in self.r.candidates if not c.is_well_placed}
        assert "Mars" in blocked
        assert "Sun" in blocked

    def test_jupiter_in_candidates(self):
        assert any(c.planet == "Jupiter" for c in self.r.candidates)


# ---------------------------------------------------------------------------
# §6. Al-Qabisi — BOUND_FALLBACK
# ---------------------------------------------------------------------------

class TestAlQabisiBoundFallback:
    """
    Aries day chart, degree=0 → bound lord = Jupiter (Egyptian 0–6°).
    dom=Mars (cadent), exalt=Sun (cadent), day trip=Sun (same as exalt, skipped).
    All blocked → BOUND_FALLBACK.
    """

    def setup_method(self):
        self.sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0, "Jupiter": 150.0},
            houses={"Mars": 3, "Sun": 3, "Jupiter": 3},
        )
        self.r = lord_of_turn_al_qabisi(0.0, 0, self.sr)

    def test_lord_is_jupiter(self):
        assert self.r.lord == "Jupiter"

    def test_reason_is_bound_fallback(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.BOUND_FALLBACK

    def test_at_least_two_blocked_candidates(self):
        blocked = [c for c in self.r.candidates if not c.is_well_placed]
        assert len(blocked) >= 2


# ---------------------------------------------------------------------------
# §7. Egyptian/Al-Sijzi — BOUND_PRIMARY_WITNESSING
# ---------------------------------------------------------------------------

class TestEgyptianBoundPrimaryWitnessing:
    """
    Aries 0°: bound lord = Jupiter.
    Jupiter at Taurus (idx 1), Sun at Leo (idx 4) — day chart, sect=Sun.
    diff from Leo: (1-4) % 12 = 9 ∈ diffs → Jupiter witnesses sect light.
    """

    def setup_method(self):
        self.sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 120.0, "Moon": 180.0, "Jupiter": 30.0},
            is_night=False,
        )
        self.r = lord_of_turn_egyptian_al_sijzi(0.0, 0, self.sr, _EGYPTIAN)

    def test_lord_is_jupiter(self):
        assert self.r.lord == "Jupiter"

    def test_reason_is_bound_primary_witnessing(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.BOUND_PRIMARY_WITNESSING

    def test_method_is_egyptian(self):
        assert self.r.method is LordOfTurnMethod.EGYPTIAN_AL_SIJZI

    def test_bound_candidate_witnesses(self):
        bound_c = next(c for c in self.r.candidates if c.role == "bound")
        assert bound_c.witnesses_target


# ---------------------------------------------------------------------------
# §8. Egyptian/Al-Sijzi — TESTIMONY_WINNER_WITNESSING
# ---------------------------------------------------------------------------

class TestEgyptianTestimonyWinner:
    """
    Aries 0°: bound lord = Jupiter at Taurus.
    Sun at Aries (sect sign = Aries, idx 0).
    Jupiter: diff from Aries = 1 (not witnessing profected or sect).
    Mars at Aries (idx 0): domicile + face at Aries 0° → testimony=2, witnesses → winner.
    (Sun also has testimony=2 at Aries but "Mars" < "Sun" alphabetically.)
    """

    def setup_method(self):
        self.sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={
                "Sun": 0.0, "Moon": 180.0, "Mars": 5.0, "Jupiter": 30.0,
                "Venus": 30.0, "Mercury": 30.0, "Saturn": 30.0,
            },
            is_night=False,
        )
        self.r = lord_of_turn_egyptian_al_sijzi(0.0, 0, self.sr, _EGYPTIAN)

    def test_lord_is_mars(self):
        assert self.r.lord == "Mars"

    def test_reason_is_testimony_winner(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.TESTIMONY_WINNER_WITNESSING

    def test_jupiter_does_not_witness(self):
        bound_c = next(c for c in self.r.candidates if c.role == "bound")
        assert bound_c.planet == "Jupiter"
        assert not bound_c.witnesses_target

    def test_mars_has_positive_testimony(self):
        mars_c = next((c for c in self.r.candidates if c.planet == "Mars"), None)
        assert mars_c is not None
        assert mars_c.testimony_count >= 1


# ---------------------------------------------------------------------------
# §9. Egyptian/Al-Sijzi — BOUND_FALLBACK
# ---------------------------------------------------------------------------

class TestEgyptianBoundFallback:
    """
    Aries 0°: bound lord = Jupiter at Taurus (idx 1).
    Night chart → sect = Moon at Aries (idx 0).  Sect sign idx = 0.
    Jupiter: (1-0)%12=1 ∉ diffs for both profected and sect → not witnessing.
    All other planets at Taurus: same — not witnessing either target.
    Moon at Aries has 0 testimony at Aries 0° → no testimony winner witnesses.
    Result: BOUND_FALLBACK.
    """

    def setup_method(self):
        self.sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={
                "Sun": 30.0, "Moon": 0.0, "Mars": 30.0, "Jupiter": 30.0,
                "Venus": 30.0, "Mercury": 30.0, "Saturn": 30.0,
            },
            is_night=True,
        )
        self.r = lord_of_turn_egyptian_al_sijzi(0.0, 0, self.sr, _EGYPTIAN)

    def test_lord_is_jupiter(self):
        assert self.r.lord == "Jupiter"

    def test_reason_is_bound_fallback(self):
        assert self.r.selection_reason is LordOfTurnSelectionReason.BOUND_FALLBACK

    def test_bound_lord_does_not_witness(self):
        bound_c = next(c for c in self.r.candidates if c.role == "bound")
        assert not bound_c.witnesses_target


# ---------------------------------------------------------------------------
# §10. Witnessing mechanic (whole-sign Ptolemaic)
# ---------------------------------------------------------------------------

class TestWitnessingMechanic:
    """
    _WITNESSING_DIFFS = {0, 2, 3, 4, 6, 8, 9, 10}
    Non-witnessing diffs: {1, 5, 7, 11}
    """

    def test_conjunction_witnesses(self):
        # Mars at Aries (idx 0), profected = Aries (idx 0): diff = 0 ✓
        sr = _day_sr_minimal(asc=0.0, Sun=90.0, Mars=5.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        c = next(c for c in r.candidates if c.planet == "Mars")
        assert c.witnesses_target

    def test_trine_witnesses(self):
        # Mars at Leo (idx 4), profected = Aries (idx 0): (4-0)%12=4 ∈ diffs ✓
        sr = _day_sr_minimal(asc=0.0, Sun=180.0, Mars=120.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        c = next(c for c in r.candidates if c.planet == "Mars")
        assert c.witnesses_target

    def test_opposition_witnesses(self):
        # Mars at Libra (idx 6), profected = Aries (idx 0): diff=6 ∈ diffs ✓
        sr = _day_sr_minimal(asc=0.0, Sun=90.0, Mars=180.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        c = next(c for c in r.candidates if c.planet == "Mars")
        assert c.witnesses_target

    def test_semisextile_does_not_witness(self):
        # Mars at Taurus (idx 1), Sun at Gemini (idx 2):
        #   diff from Aries (profected) = 1 ✗,  diff from Gemini (sect) = 11 ✗
        sr = _day_sr_minimal(asc=0.0, Sun=60.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        c = next(c for c in r.candidates if c.planet == "Mars")
        assert not c.witnesses_target

    def test_quincunx_does_not_witness(self):
        # Mars at Virgo (idx 5), Sun at Aries (idx 0):
        #   diff from Aries = 5 ✗,  diff from Aries (sect) = 5 ✗
        sr = _day_sr_minimal(asc=0.0, Sun=0.0, Mars=150.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        c = next(c for c in r.candidates if c.planet == "Mars")
        assert not c.witnesses_target


# ---------------------------------------------------------------------------
# §11. Combust check and retrograde block
# ---------------------------------------------------------------------------

class TestBlockers:

    def test_combust_within_default_orb(self):
        # Mars at 3°, Sun at 8° → diff = 5° < 8.5 → combust
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 8.0, "Moon": 180.0, "Mars": 3.0},
            houses={"Mars": 1, "Sun": 4},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars = next(c for c in r.candidates if c.planet == "Mars")
        assert mars.is_combust
        assert not mars.is_well_placed
        assert LordOfTurnBlockerReason.COMBUST in mars.blocker_reasons

    def test_not_combust_beyond_orb(self):
        # Mars at 5°, Sun at 90° → diff = 85° >> 8.5 → not combust
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars = next(c for c in r.candidates if c.planet == "Mars")
        assert not mars.is_combust

    def test_sun_never_combust(self):
        # Exaltation fallback forces Sun into candidates; Sun cannot combust itself
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 5.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 3, "Sun": 1},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        sun = next((c for c in r.candidates if c.planet == "Sun"), None)
        if sun:
            assert not sun.is_combust

    def test_retrograde_blocks_domicile_lord(self):
        # Mars retrograde in house 1 → blocked despite good house
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
            retro=frozenset({"Mars"}),
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars = next(c for c in r.candidates if c.planet == "Mars")
        assert mars.is_retrograde
        assert LordOfTurnBlockerReason.RETROGRADE in mars.blocker_reasons
        assert not mars.is_well_placed
        assert r.selection_reason is not LordOfTurnSelectionReason.DOMICILE_WELL_PLACED


# ---------------------------------------------------------------------------
# §12. Inspectability properties on LordOfTurnResult
# ---------------------------------------------------------------------------

class TestInspectabilityProperties:

    def setup_method(self):
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
        )
        self.r = lord_of_turn_al_qabisi(0.0, 0, sr)

    def test_sign_of_year(self):
        assert self.r.sign_of_year == "Aries"

    def test_age_property(self):
        assert self.r.age == 0

    def test_winning_candidate_planet_matches_lord(self):
        wc = self.r.winning_candidate
        assert wc is not None
        assert wc.planet == self.r.lord

    def test_blocked_candidates_excludes_lord(self):
        for c in self.r.blocked_candidates:
            assert c.planet != self.r.lord

    def test_is_fallback_false_for_domicile_well_placed(self):
        assert not self.r.is_fallback

    def test_is_fallback_true_for_exaltation_fallback(self):
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 3, "Sun": 1},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.is_fallback

    def test_is_fallback_true_for_bound_fallback(self):
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0, "Jupiter": 150.0},
            houses={"Mars": 3, "Sun": 3, "Jupiter": 3},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.is_fallback

    def test_repr_contains_lord_and_sign(self):
        rep = repr(self.r)
        assert "Mars" in rep
        assert "Aries" in rep


# ---------------------------------------------------------------------------
# §13. LordOfTurnConditionProfile
# ---------------------------------------------------------------------------

class TestConditionProfile:

    def setup_method(self):
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
        )
        self.profile = lord_of_turn(0.0, 0, sr)

    def test_returns_condition_profile_type(self):
        assert isinstance(self.profile, LordOfTurnConditionProfile)

    def test_lord_property(self):
        assert self.profile.lord == "Mars"

    def test_sign_of_year_property(self):
        assert self.profile.sign_of_year == "Aries"

    def test_sect_light_is_sun_for_day(self):
        assert self.profile.sect_light == "Sun"

    def test_sect_light_is_moon_for_night(self):
        sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0},
            is_night=True,
        )
        profile = lord_of_turn(0.0, 0, sr)
        assert profile.sect_light == "Moon"

    def test_is_fallback_delegates_to_result(self):
        assert self.profile.is_fallback == self.profile.result.is_fallback

    def test_lord_witnesses_sr_asc(self):
        # Mars at Aries (idx 0), SR ASC at Aries (idx 0): diff=0 → witnesses
        assert self.profile.lord_witnesses_sr_asc

    def test_lord_sr_house_populated(self):
        assert self.profile.lord_sr_house == 1


# ---------------------------------------------------------------------------
# §14. lord_of_turn() dispatch
# ---------------------------------------------------------------------------

class TestDispatch:

    def test_default_policy_uses_al_qabisi(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        profile = lord_of_turn(0.0, 0, sr)
        assert profile.result.method is LordOfTurnMethod.AL_QABISI

    def test_egyptian_policy_dispatches_correctly(self):
        sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 120.0, "Moon": 180.0, "Jupiter": 30.0},
            is_night=False,
        )
        profile = lord_of_turn(0.0, 0, sr, policy=_EGYPTIAN)
        assert profile.result.method is LordOfTurnMethod.EGYPTIAN_AL_SIJZI

    def test_night_chart_sets_sr_is_night(self):
        sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0},
            is_night=True,
        )
        profile = lord_of_turn(0.0, 0, sr)
        assert profile.sr_is_night


# ---------------------------------------------------------------------------
# §15. validate_lord_of_turn_output
# ---------------------------------------------------------------------------

class TestValidation:

    def _valid_day_profile(self) -> LordOfTurnConditionProfile:
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
        )
        return lord_of_turn(0.0, 0, sr)

    def test_valid_result_has_no_failures(self):
        profile = self._valid_day_profile()
        assert validate_lord_of_turn_output(profile) == []

    def test_all_12_sign_ages_validate(self):
        for age in range(12):
            sr = _day_sr_minimal(asc=0.0, Sun=90.0)
            profile = lord_of_turn(0.0, age, sr)
            failures = validate_lord_of_turn_output(profile)
            assert failures == [], f"Age {age}: {failures}"

    def test_egyptian_result_validates(self):
        sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 120.0, "Moon": 180.0, "Jupiter": 30.0},
            is_night=False,
        )
        profile = lord_of_turn(0.0, 0, sr, policy=_EGYPTIAN)
        assert validate_lord_of_turn_output(profile) == []

    def test_invalid_sect_light_caught(self):
        r_inner = lord_of_turn_al_qabisi(0.0, 0, _day_sr_minimal(asc=0.0, Sun=90.0))
        broken = LordOfTurnConditionProfile(
            result=r_inner,
            sr_is_night=False,
            sect_light="Neptune",
            lord_witnesses_sr_asc=False,
            lord_sr_house=None,
        )
        failures = validate_lord_of_turn_output(broken)
        assert any("sect_light" in f for f in failures)

    def test_night_chart_validates(self):
        sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            is_night=True,
        )
        profile = lord_of_turn(0.0, 0, sr)
        assert validate_lord_of_turn_output(profile) == []


# ---------------------------------------------------------------------------
# §16. Policy surface
# ---------------------------------------------------------------------------

class TestPolicy:

    def test_default_method_is_al_qabisi(self):
        assert DEFAULT_LORD_OF_TURN_POLICY.method is LordOfTurnMethod.AL_QABISI

    def test_default_combust_orb_is_8_5(self):
        assert DEFAULT_LORD_OF_TURN_POLICY.combust_orb == 8.5

    def test_custom_combust_orb_applied(self):
        # With 15° orb, Mars 9° from Sun → combust; with default 8.5° → not combust
        policy = LordOfTurnPolicy(combust_orb=15.0)
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 5.0, "Moon": 180.0, "Mars": 14.0},
            houses={"Mars": 1, "Sun": 4},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr, policy)
        mars = next(c for c in r.candidates if c.planet == "Mars")
        assert mars.is_combust  # 9° < 15° orb

    def test_policy_is_frozen(self):
        with pytest.raises(AttributeError):
            DEFAULT_LORD_OF_TURN_POLICY.method = LordOfTurnMethod.EGYPTIAN_AL_SIJZI

    def test_custom_policy_stored_in_profile(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        profile = lord_of_turn(0.0, 0, sr, policy=_EGYPTIAN)
        assert profile.result.method is LordOfTurnMethod.EGYPTIAN_AL_SIJZI


# ---------------------------------------------------------------------------
# §17. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_negative_age_raises(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        with pytest.raises(ValueError, match="age"):
            lord_of_turn_al_qabisi(0.0, -1, sr)

    def test_infinite_natal_asc_raises(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        with pytest.raises(ValueError, match="natal_asc"):
            lord_of_turn_al_qabisi(math.inf, 0, sr)

    def test_nan_natal_asc_raises(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        with pytest.raises(ValueError):
            lord_of_turn_al_qabisi(math.nan, 0, sr)

    def test_invalid_sr_asc_raises(self):
        with pytest.raises(ValueError):
            LordOfTurnSRChart(sr_asc=math.inf, planets={"Sun": 90.0})

    def test_invalid_planet_longitude_raises(self):
        with pytest.raises(ValueError):
            LordOfTurnSRChart(sr_asc=0.0, planets={"Sun": math.nan})

    def test_age_zero_is_valid(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.lord in {
            "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"
        }


# ---------------------------------------------------------------------------
# §18. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_profection_cycle_repeats_at_age_12(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        r0  = lord_of_turn_al_qabisi(0.0, 0, sr)
        r12 = lord_of_turn_al_qabisi(0.0, 12, sr)
        assert r0.sign_of_year == r12.sign_of_year
        assert r0.lord == r12.lord

    def test_high_age_validates(self):
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        profile = lord_of_turn(0.0, 84, sr)
        assert validate_lord_of_turn_output(profile) == []

    def test_natal_asc_360_wraps_to_aries(self):
        # 360.0 % 360 = 0 → Aries at age=0
        sr = _day_sr_minimal(asc=360.0, Sun=90.0)
        r = lord_of_turn_al_qabisi(360.0, 0, sr)
        assert r.profection.profected_sign == "Aries"

    def test_all_12_domicile_lords_are_classical(self):
        classical = {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}
        sr = _day_sr_minimal(asc=0.0, Sun=90.0)
        for age in range(12):
            r = lord_of_turn_al_qabisi(0.0, age, sr)
            assert r.lord in classical, f"Age {age} returned non-classical {r.lord!r}"

    def test_lot_fortune_field_accepted(self):
        sr = LordOfTurnSRChart(
            sr_asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0},
            is_night=False,
            sr_lot_fortune=45.0,
        )
        profile = lord_of_turn(0.0, 0, sr)
        assert validate_lord_of_turn_output(profile) == []


# ---------------------------------------------------------------------------
# §19. Doctrinal-clarity tests
#      Verify the resolved mismatches: witnessing target = SR ASC or sect
#      light (not profected sign), and the absence of an Al-Qabisi tiebreaker.
# ---------------------------------------------------------------------------

class TestDoctrinalClarity:

    # --- witnessing target semantics -----------------------------------------

    def test_witnesses_sr_asc_when_asc_differs_from_profected_sign(self):
        """
        Planet witnesses SR ASC (trine) but does NOT witness the profected sign
        or sect light.  With SR-ASC semantics, witnesses_target=True.

        Setup:
          natal_asc=0, age=0 → profected=Aries (idx 0)
          sr_asc=270 (Capricorn, idx 9)
          Mars at Taurus (idx 1): (1-9)%12=4 → trine SR ASC ✓
          Sun at Gemini  (idx 2): (1-2)%12=11 → aversion to sect light ✗
          diff from profected Aries: (1-0)%12=1 → aversion ✗
        Old profected-sign semantics would give False; correct semantics give True.
        """
        sr = _day_sr_minimal(asc=270.0, Sun=60.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars_c = next(c for c in r.candidates if c.planet == "Mars")
        assert mars_c.witnesses_target, (
            "Mars at Taurus should witness Capricorn SR ASC via trine"
        )

    def test_does_not_witness_when_neither_sr_asc_nor_sect_light(self):
        """
        Planet in aversion to both SR ASC and sect light → witnesses_target=False.

        Setup:
          sr_asc=0 (Aries, idx 0), Sun at Gemini (idx 2)
          Mars at Taurus (idx 1):
            vs SR ASC  (idx 0): (1-0)%12=1 → aversion ✗
            vs sect    (idx 2): (1-2)%12=11 → aversion ✗
        """
        sr = _day_sr_minimal(asc=0.0, Sun=60.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars_c = next(c for c in r.candidates if c.planet == "Mars")
        assert not mars_c.witnesses_target

    def test_witnesses_sect_light_when_aversion_to_sr_asc(self):
        """
        Planet does not witness SR ASC but does witness sect light
        → witnesses_target=True.

        Setup:
          sr_asc=60 (Gemini, idx 2): (1-2)%12=11 → aversion ✗
          Sun at Leo (idx 4, day sect): (1-4)%12=9 → trine ✓
        """
        sr = _day_sr_minimal(asc=60.0, Sun=120.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars_c = next(c for c in r.candidates if c.planet == "Mars")
        assert mars_c.witnesses_target

    def test_witnesses_target_is_sr_asc_not_profected(self):
        """
        Regression guard: when profected sign ≠ SR ASC, witnessing checks
        SR ASC, not profected sign.
        """
        # sr_asc=Capricorn (270, idx 9); profected=Aries (0, idx 0)
        # Mars at Taurus (idx 1): trine Capricorn (diff 4) ✓, aversion Aries (diff 1) ✗
        sr = _day_sr_minimal(asc=270.0, Sun=60.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        mars_c = next(c for c in r.candidates if c.planet == "Mars")
        assert mars_c.witnesses_target

    # --- Al-Qabisi sequential succession / no tiebreaker ---------------------

    def test_al_qabisi_sequential_returns_on_first_pass(self):
        """
        When domicile lord passes condition, the engine returns without assessing
        the exaltation lord — no tiebreaker scenario arises.
        """
        # Aries: dom=Mars (house 1 ✓), exalt=Sun (also house 1 ✓)
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 1},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.lord == "Mars"
        assert r.selection_reason is LordOfTurnSelectionReason.DOMICILE_WELL_PLACED
        # Exaltation lord (Sun) never assessed — not in candidates
        assert not any(c.planet == "Sun" for c in r.candidates), (
            "Exaltation lord should not be assessed when domicile lord passes"
        )

    def test_al_qabisi_single_candidate_when_domicile_passes(self):
        """Sequential succession: only one candidate assessed when domicile passes."""
        sr = _day_sr(
            asc=0.0,
            planets={"Sun": 90.0, "Moon": 180.0, "Mars": 5.0},
            houses={"Mars": 1, "Sun": 4},
        )
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert len(r.candidates) == 1

    # --- DOMICILE_ONLY mode --------------------------------------------------

    def test_domicile_only_witnesses_sr_asc_not_profected(self):
        """
        In DOMICILE_ONLY mode, witnesses_target checks SR ASC, not profected sign.
        Profected=Aries (idx 0).  sr_asc=Capricorn (idx 9).
        Mars at Taurus (idx 1): trine Capricorn (diff 4) ✓.
        """
        sr = _day_sr_minimal(asc=270.0, Sun=60.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.selection_reason is LordOfTurnSelectionReason.DOMICILE_ONLY
        assert r.candidates[0].witnesses_target  # Mars at Taurus trines Capricorn ASC

    def test_domicile_only_witnesses_false_when_aversion(self):
        """
        DOMICILE_ONLY: dom lord at Taurus in aversion to Aries SR ASC (diff=1)
        and Gemini sect (diff=11) → witnesses_target=False.
        """
        sr = _day_sr_minimal(asc=0.0, Sun=60.0, Mars=30.0)
        r = lord_of_turn_al_qabisi(0.0, 0, sr)
        assert r.selection_reason is LordOfTurnSelectionReason.DOMICILE_ONLY
        assert not r.candidates[0].witnesses_target
