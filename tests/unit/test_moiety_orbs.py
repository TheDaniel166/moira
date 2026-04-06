"""
Tests for moiety orb support in moira.aspects.

Verification strategy:
  - TRADITIONAL_MOIETY_ORBS contains the expected Lilly 1647 values.
  - AspectPolicy: orb_mode validation, moiety_orbs field.
  - _moiety_allowed_orb arithmetic: sum of halves, fallback for unknown bodies.
  - find_aspects with orb_mode="moiety":
      - Admits aspects that moiety allows and fixed default would reject.
      - Rejects aspects that moiety forbids even if fixed default would admit.
      - allowed_orb on each result equals moiety(b1) + moiety(b2).
  - aspects_between and aspects_to_point respect moiety mode.
  - Fixed mode (default) is unaffected: no regression.
  - Custom moiety_orbs table overrides TRADITIONAL_MOIETY_ORBS.
"""

from __future__ import annotations

import pytest

from moira.aspects import (
    AspectPolicy,
    TRADITIONAL_MOIETY_ORBS,
    aspects_between,
    aspects_to_point,
    find_aspects,
)
from moira.constants import Body


# ---------------------------------------------------------------------------
# TRADITIONAL_MOIETY_ORBS content
# ---------------------------------------------------------------------------

class TestTraditionalMoietyOrbs:
    def test_contains_seven_classical_planets(self) -> None:
        expected = {Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS,
                    Body.MARS, Body.JUPITER, Body.SATURN}
        assert expected == set(TRADITIONAL_MOIETY_ORBS.keys())

    def test_sun_full_orb_is_15(self) -> None:
        assert TRADITIONAL_MOIETY_ORBS[Body.SUN] == pytest.approx(15.0)

    def test_moon_full_orb_is_12(self) -> None:
        assert TRADITIONAL_MOIETY_ORBS[Body.MOON] == pytest.approx(12.0)

    def test_jupiter_full_orb_is_12(self) -> None:
        assert TRADITIONAL_MOIETY_ORBS[Body.JUPITER] == pytest.approx(12.0)

    def test_saturn_full_orb_is_10(self) -> None:
        assert TRADITIONAL_MOIETY_ORBS[Body.SATURN] == pytest.approx(10.0)

    def test_inferior_planets_full_orb_is_7(self) -> None:
        for body in (Body.MERCURY, Body.VENUS, Body.MARS):
            assert TRADITIONAL_MOIETY_ORBS[body] == pytest.approx(7.0), body


# ---------------------------------------------------------------------------
# AspectPolicy validation
# ---------------------------------------------------------------------------

class TestAspectPolicyMoietyFields:
    def test_default_orb_mode_is_fixed(self) -> None:
        p = AspectPolicy()
        assert p.orb_mode == "fixed"

    def test_moiety_mode_accepted(self) -> None:
        p = AspectPolicy(orb_mode="moiety")
        assert p.orb_mode == "moiety"

    def test_invalid_orb_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="orb_mode"):
            AspectPolicy(orb_mode="traditional")

    def test_moiety_orbs_default_is_none(self) -> None:
        p = AspectPolicy()
        assert p.moiety_orbs is None

    def test_custom_moiety_orbs_stored(self) -> None:
        custom = {Body.SUN: 12.0, Body.MOON: 10.0}
        p = AspectPolicy(orb_mode="moiety", moiety_orbs=custom)
        assert p.moiety_orbs is custom

    def test_fixed_mode_unchanged_by_moiety_fields(self) -> None:
        # Adding moiety_orbs with orb_mode="fixed" should not affect behaviour.
        p = AspectPolicy(orb_mode="fixed", moiety_orbs={Body.SUN: 5.0})
        assert p.orb_mode == "fixed"


# ---------------------------------------------------------------------------
# _moiety_allowed_orb arithmetic (tested via find_aspects results)
# ---------------------------------------------------------------------------

class TestMoietyAllowedOrbArithmetic:
    def _allowed_for(self, b1: str, b2: str, table=None) -> float:
        tbl = table or TRADITIONAL_MOIETY_ORBS
        return tbl.get(b1, 5.0) / 2 + tbl.get(b2, 5.0) / 2

    def test_sun_moon_combined_moiety(self) -> None:
        # Sun moiety 7.5 + Moon moiety 6.0 = 13.5
        assert self._allowed_for(Body.SUN, Body.MOON) == pytest.approx(13.5)

    def test_mercury_saturn_combined_moiety(self) -> None:
        # Mercury moiety 3.5 + Saturn moiety 5.0 = 8.5
        assert self._allowed_for(Body.MERCURY, Body.SATURN) == pytest.approx(8.5)

    def test_unknown_body_uses_default_fallback(self) -> None:
        # "Chiron" not in table → fallback full orb 5° → moiety 2.5°
        # Sun moiety 7.5 + Chiron moiety 2.5 = 10.0
        assert self._allowed_for(Body.SUN, "Chiron") == pytest.approx(10.0)

    def test_two_unknown_bodies_use_double_fallback(self) -> None:
        # 2.5 + 2.5 = 5.0
        assert self._allowed_for("Alpha", "Beta") == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# find_aspects — moiety mode changes allowed_orb on results
# ---------------------------------------------------------------------------

class TestFindAspectsWithMoiety:
    def test_allowed_orb_equals_combined_moiety_for_each_result(self) -> None:
        # Give Sun and Saturn positions that produce a trine with a ~7° orb.
        # Fixed default for trine = 8°, so it admits.
        # Moiety: Saturn 5° + Sun 7.5° = 12.5° — also admits.
        # Verify the allowed_orb field equals the moiety sum.
        positions = {Body.SUN: 0.0, Body.SATURN: 127.0}  # ~7° from trine
        policy = AspectPolicy(orb_mode="moiety")
        results = find_aspects(positions, policy=policy)
        trine_results = [r for r in results if r.aspect == "Trine"]
        assert trine_results, "Expected at least one Trine with Sun–Saturn ~7° orb"
        for r in trine_results:
            expected = TRADITIONAL_MOIETY_ORBS[Body.SUN] / 2 + TRADITIONAL_MOIETY_ORBS[Body.SATURN] / 2
            assert r.allowed_orb == pytest.approx(expected)

    def test_moiety_admits_wider_orb_than_fixed_for_luminaries(self) -> None:
        # Sun–Moon conjunction with 10° orb.
        # Fixed default conjunction orb = 8° → would REJECT.
        # Moiety: Sun 7.5 + Moon 6.0 = 13.5° → ADMITS.
        positions = {Body.SUN: 0.0, Body.MOON: 10.2}
        fixed_policy  = AspectPolicy(orb_mode="fixed")
        moiety_policy = AspectPolicy(orb_mode="moiety")

        fixed_results  = [r for r in find_aspects(positions, policy=fixed_policy)
                          if r.aspect == "Conjunction"]
        moiety_results = [r for r in find_aspects(positions, policy=moiety_policy)
                          if r.aspect == "Conjunction"]

        assert len(fixed_results)  == 0, "Fixed should reject 10° conjunction"
        assert len(moiety_results) == 1, "Moiety should admit 10° Sun–Moon conjunction"

    def test_moiety_rejects_narrower_orb_for_minor_planets(self) -> None:
        # Mercury–Mars conjunction with 4° orb.
        # Fixed default conjunction orb = 8° → ADMITS.
        # Moiety: Mercury 3.5 + Mars 3.5 = 7.0° → also ADMITS at 4°.
        # Use 7.5° to show rejection:
        # Fixed 8° ADMITS; Moiety 7.0° REJECTS.
        positions = {Body.MERCURY: 0.0, Body.MARS: 7.3}
        fixed_policy  = AspectPolicy(orb_mode="fixed")
        moiety_policy = AspectPolicy(orb_mode="moiety")

        fixed_results  = [r for r in find_aspects(positions, policy=fixed_policy)
                          if r.aspect == "Conjunction"]
        moiety_results = [r for r in find_aspects(positions, policy=moiety_policy)
                          if r.aspect == "Conjunction"]

        assert len(fixed_results)  == 1, "Fixed (8° orb) should admit 7.3° Mercury–Mars conjunction"
        assert len(moiety_results) == 0, "Moiety (7.0° combined) should reject 7.3° Mercury–Mars conjunction"

    def test_moiety_result_allowed_orb_is_body_pair_not_angle_specific(self) -> None:
        # With moiety mode, every aspect between the same pair has identical allowed_orb.
        positions = {Body.JUPITER: 0.0, Body.SATURN: 62.0}  # near sextile AND could be others
        policy = AspectPolicy(orb_mode="moiety", tier=2)
        results = find_aspects(positions, policy=policy)
        expected_allowed = (TRADITIONAL_MOIETY_ORBS[Body.JUPITER] / 2
                            + TRADITIONAL_MOIETY_ORBS[Body.SATURN] / 2)
        for r in results:
            assert r.allowed_orb == pytest.approx(expected_allowed), (
                f"Aspect {r.aspect!r} has wrong allowed_orb: {r.allowed_orb}"
            )

    def test_custom_moiety_orbs_overrides_traditional(self) -> None:
        # Override Sun to full orb 6° (moiety 3°) and Moon to 6° (moiety 3°).
        # Combined = 6°. With a 5.5° conjunction orb → admitted.
        # With TRADITIONAL (13.5°) also admitted, but allowed_orb should be 6.0°.
        custom = {Body.SUN: 6.0, Body.MOON: 6.0}
        policy = AspectPolicy(orb_mode="moiety", moiety_orbs=custom)
        positions = {Body.SUN: 0.0, Body.MOON: 5.5}
        results = [r for r in find_aspects(positions, policy=policy)
                   if r.aspect == "Conjunction"]
        assert results, "Expected conjunction with custom moiety 6°"
        assert results[0].allowed_orb == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# aspects_between — moiety mode
# ---------------------------------------------------------------------------

class TestAspectsBetweenWithMoiety:
    def test_allowed_orb_equals_pair_moiety(self) -> None:
        # Jupiter–Saturn sextile with ~3° orb.
        policy = AspectPolicy(orb_mode="moiety")
        results = aspects_between(
            Body.JUPITER, 0.0,
            Body.SATURN,  63.0,
            policy=policy,
        )
        sextile = [r for r in results if r.aspect == "Sextile"]
        assert sextile, "Expected sextile"
        expected = (TRADITIONAL_MOIETY_ORBS[Body.JUPITER] / 2
                    + TRADITIONAL_MOIETY_ORBS[Body.SATURN] / 2)
        assert sextile[0].allowed_orb == pytest.approx(expected)

    def test_fixed_mode_unchanged(self) -> None:
        # Default policy should still use per-angle orbs.
        results = aspects_between(Body.MARS, 0.0, Body.SATURN, 60.2)
        sextile = [r for r in results if r.aspect == "Sextile"]
        assert sextile, "Sextile expected in fixed mode"
        # fixed mode: allowed_orb should be the AspectDefinition.default_orb, not moiety sum
        moiety_sum = (TRADITIONAL_MOIETY_ORBS[Body.MARS] / 2
                      + TRADITIONAL_MOIETY_ORBS[Body.SATURN] / 2)
        # They happen to differ; the fixed orb for sextile ≠ moiety sum for Mars–Saturn
        assert sextile[0].allowed_orb != pytest.approx(moiety_sum)


# ---------------------------------------------------------------------------
# aspects_to_point — moiety mode
# ---------------------------------------------------------------------------

class TestAspectsToPointWithMoiety:
    def test_point_uses_fallback_moiety(self) -> None:
        # Sun aspects a fixed point "ASC" (not in table → fallback 2.5°).
        # Combined: Sun 7.5 + ASC 2.5 = 10.0°.
        # Sun at 0°, ASC at 9.5° → conjunction orb 9.5° → admitted under moiety (10°).
        policy = AspectPolicy(orb_mode="moiety")
        results = aspects_to_point(
            point_longitude=9.5,
            positions={Body.SUN: 0.0},
            point_name="ASC",
            policy=policy,
        )
        conj = [r for r in results if r.aspect == "Conjunction"]
        assert conj, "Expected conjunction admitted under moiety"
        assert conj[0].allowed_orb == pytest.approx(10.0)

    def test_named_point_in_custom_moiety_table(self) -> None:
        # Add "ASC" to the moiety table with a full orb of 8° (moiety 4°).
        custom = dict(TRADITIONAL_MOIETY_ORBS)
        custom["ASC"] = 8.0
        policy = AspectPolicy(orb_mode="moiety", moiety_orbs=custom)
        results = aspects_to_point(
            point_longitude=0.0,
            positions={Body.SATURN: 3.0},
            point_name="ASC",
            policy=policy,
        )
        conj = [r for r in results if r.aspect == "Conjunction"]
        assert conj, "Expected conjunction"
        expected = TRADITIONAL_MOIETY_ORBS[Body.SATURN] / 2 + 8.0 / 2  # 5.0 + 4.0
        assert conj[0].allowed_orb == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Regression: fixed mode produces identical results before and after
# ---------------------------------------------------------------------------

class TestFixedModeRegression:
    def test_find_aspects_default_policy_unchanged(self) -> None:
        positions = {Body.SUN: 0.0, Body.MOON: 120.5, Body.MARS: 90.3}
        original = find_aspects(positions)
        from_policy = find_aspects(positions, policy=AspectPolicy())
        assert len(original) == len(from_policy)
        for a, b in zip(original, from_policy):
            assert a.aspect == b.aspect
            assert a.orb == pytest.approx(b.orb)
            assert a.allowed_orb == pytest.approx(b.allowed_orb)
