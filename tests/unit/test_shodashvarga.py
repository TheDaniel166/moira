"""
Unit tests for the Shodashvarga completion wrappers added to moira.varga.

Tests cover:
  - D2  Hora           Parashari odd/even + first/second half rule
  - D4  Chaturthamsha  Parashari sign-offset rule
  - D27 Saptavimshamsha triplicity-start rule
  - D40 Khavedamsha    odd/even-start rule
  - D45 Akshavedamsha  odd/even-start rule
  - D6/D8/D16/D20/D24/D60  generic formula wrappers
  - VargaPoint structural invariants for all new wrappers
"""
from __future__ import annotations

import math
import pytest

from moira.varga import (
    VargaPoint,
    hora, chaturthamsha, shashthamsha, ashtamsha,
    shodashamsha, vimshamsha, chaturvimshamsha,
    saptavimshamsha, khavedamsha, akshavedamsha, shashtiamsha,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sign_idx_of(vp: VargaPoint) -> int:
    from moira.constants import SIGNS
    return list(SIGNS).index(vp.sign)


# ---------------------------------------------------------------------------
# D2 Hora — Parashari odd/even rule
# ---------------------------------------------------------------------------

class TestHora:
    # Odd D1 signs (0-based index % 2 == 0): first half → Leo, second half → Cancer
    # Aries  (idx 0, odd):  0°–15° → Leo,    15°–30° → Cancer
    # Taurus (idx 1, even): 0°–15° → Cancer, 15°–30° → Leo

    @pytest.mark.parametrize("lon,expected_sign", [
        (0.0,  "Leo"),     # Aries 0° — odd sign, first half
        (7.5,  "Leo"),     # Aries 7.5° — odd sign, first half
        (14.9, "Leo"),     # Aries 14.9° — odd sign, still first half
        (15.0, "Cancer"),  # Aries 15° — odd sign, second half
        (29.9, "Cancer"),  # Aries 29.9° — odd sign, second half
    ])
    def test_odd_sign_aries(self, lon, expected_sign):
        assert hora(lon).sign == expected_sign

    @pytest.mark.parametrize("lon,expected_sign", [
        (30.0,  "Cancer"),  # Taurus 0° — even sign, first half
        (37.5,  "Cancer"),  # Taurus 7.5° — even sign, first half
        (44.9,  "Cancer"),  # Taurus 14.9° — even sign, first half
        (45.0,  "Leo"),     # Taurus 15° — even sign, second half
        (59.9,  "Leo"),     # Taurus 29.9° — even sign, second half
    ])
    def test_even_sign_taurus(self, lon, expected_sign):
        assert hora(lon).sign == expected_sign

    def test_hora_sign_always_cancer_or_leo(self):
        for lon in range(0, 360, 3):
            vp = hora(float(lon))
            assert vp.sign in ("Cancer", "Leo"), f"lon={lon}: got {vp.sign}"

    def test_hora_varga_number(self):
        assert hora(0.0).varga_number == 2

    def test_hora_sign_degree_in_range(self):
        for lon in range(0, 360, 7):
            vp = hora(float(lon))
            assert 0.0 <= vp.sign_degree < 30.0

    def test_hora_longitude_reduced(self):
        assert hora(360.0).sign == hora(0.0).sign
        assert hora(720.0 + 5.0).sign == hora(5.0).sign

    def test_hora_odd_even_pattern_all_signs(self):
        """All 12 signs: odd-indexed signs yield Leo first, Cancer second."""
        from moira.constants import SIGNS
        for sign_i, sign_name in enumerate(SIGNS):
            base = sign_i * 30.0
            first_half  = hora(base + 5.0).sign
            second_half = hora(base + 20.0).sign
            is_odd = (sign_i % 2 == 0)
            if is_odd:
                assert first_half == "Leo",    f"{sign_name}: first half should be Leo"
                assert second_half == "Cancer", f"{sign_name}: second half should be Cancer"
            else:
                assert first_half == "Cancer", f"{sign_name}: first half should be Cancer"
                assert second_half == "Leo",    f"{sign_name}: second half should be Leo"


# ---------------------------------------------------------------------------
# D4 Chaturthamsha — Parashari sign-offset rule
# ---------------------------------------------------------------------------

class TestChaturthamsha:
    # Each sign's four 7.5° segments map to sign+0, sign+1, sign+2, sign+3
    # Aries (idx 0): 0°→Aries, 7.5°→Taurus, 15°→Gemini, 22.5°→Cancer

    @pytest.mark.parametrize("deg_in_aries,expected_sign", [
        (0.0,  "Aries"),
        (7.5,  "Taurus"),
        (15.0, "Gemini"),
        (22.5, "Cancer"),
    ])
    def test_aries_segments(self, deg_in_aries, expected_sign):
        assert chaturthamsha(deg_in_aries).sign == expected_sign

    def test_capricorn_segments(self):
        # Capricorn (idx 9): 0°→Capricorn, 7.5°→Aquarius, 15°→Pisces, 22.5°→Aries
        base = 9 * 30.0
        assert chaturthamsha(base + 0.0).sign == "Capricorn"
        assert chaturthamsha(base + 7.5).sign == "Aquarius"
        assert chaturthamsha(base + 15.0).sign == "Pisces"
        assert chaturthamsha(base + 22.5).sign == "Aries"

    def test_varga_number(self):
        assert chaturthamsha(0.0).varga_number == 4

    def test_sign_degree_in_range(self):
        for lon in range(0, 360, 3):
            vp = chaturthamsha(float(lon))
            assert 0.0 <= vp.sign_degree < 30.0


# ---------------------------------------------------------------------------
# D27 Saptavimshamsha — triplicity-start rule
# ---------------------------------------------------------------------------

class TestSaptavimshamsha:
    # Fire  signs (0,4,8)  → start Aries (0)
    # Earth signs (1,5,9)  → start Cancer (3)
    # Air   signs (2,6,10) → start Libra (6)
    # Water signs (3,7,11) → start Capricorn (9)

    @pytest.mark.parametrize("sign_base,expected_first_sign", [
        (0,  "Aries"),       # Aries — fire
        (4,  "Aries"),       # Leo — fire
        (8,  "Aries"),       # Sagittarius — fire
        (1,  "Cancer"),      # Taurus — earth
        (5,  "Cancer"),      # Virgo — earth
        (9,  "Cancer"),      # Capricorn — earth
        (2,  "Libra"),       # Gemini — air
        (6,  "Libra"),       # Libra — air
        (10, "Libra"),       # Aquarius — air
        (3,  "Capricorn"),   # Cancer — water
        (7,  "Capricorn"),   # Scorpio — water
        (11, "Capricorn"),   # Pisces — water
    ])
    def test_triplicity_start(self, sign_base, expected_first_sign):
        vp = saptavimshamsha(sign_base * 30.0 + 0.5)
        assert vp.sign == expected_first_sign, (
            f"sign {sign_base}: expected first division in {expected_first_sign}, got {vp.sign}"
        )

    def test_varga_number(self):
        assert saptavimshamsha(0.0).varga_number == 27

    def test_sign_degree_in_range(self):
        for lon in range(0, 360, 5):
            vp = saptavimshamsha(float(lon))
            assert 0.0 <= vp.sign_degree < 30.0


# ---------------------------------------------------------------------------
# D40 Khavedamsha — odd/even-start rule
# ---------------------------------------------------------------------------

class TestKhavedamsha:
    # Odd signs (idx % 2 == 0): start Aries (0)
    # Even signs (idx % 2 == 1): start Libra (6)

    def test_aries_starts_aries(self):
        assert khavedamsha(0.0).sign == "Aries"

    def test_taurus_starts_libra(self):
        assert khavedamsha(30.0).sign == "Libra"

    def test_gemini_starts_aries(self):
        assert khavedamsha(60.0).sign == "Aries"

    def test_cancer_starts_libra(self):
        assert khavedamsha(90.0).sign == "Libra"

    def test_all_odd_signs_start_from_aries(self):
        from moira.constants import SIGNS
        for i in range(0, 12, 2):  # odd signs: Aries, Gemini, Leo, ...
            vp = khavedamsha(i * 30.0 + 0.01)
            assert vp.sign == "Aries", f"Odd sign {SIGNS[i]}: expected Aries start"

    def test_all_even_signs_start_from_libra(self):
        from moira.constants import SIGNS
        for i in range(1, 12, 2):  # even signs: Taurus, Cancer, Virgo, ...
            vp = khavedamsha(i * 30.0 + 0.01)
            assert vp.sign == "Libra", f"Even sign {SIGNS[i]}: expected Libra start"

    def test_varga_number(self):
        assert khavedamsha(0.0).varga_number == 40

    def test_sign_degree_in_range(self):
        for lon in range(0, 360, 5):
            vp = khavedamsha(float(lon))
            assert 0.0 <= vp.sign_degree < 30.0


# ---------------------------------------------------------------------------
# D45 Akshavedamsha — odd/even-start rule
# ---------------------------------------------------------------------------

class TestAkshavedamsha:
    # Odd signs: start Aries (0)
    # Even signs: start Capricorn (9)

    def test_aries_starts_aries(self):
        assert akshavedamsha(0.0).sign == "Aries"

    def test_taurus_starts_capricorn(self):
        assert akshavedamsha(30.0).sign == "Capricorn"

    def test_all_odd_signs_start_aries(self):
        from moira.constants import SIGNS
        for i in range(0, 12, 2):
            vp = akshavedamsha(i * 30.0 + 0.01)
            assert vp.sign == "Aries", f"Odd sign {SIGNS[i]}: expected Aries"

    def test_all_even_signs_start_capricorn(self):
        from moira.constants import SIGNS
        for i in range(1, 12, 2):
            vp = akshavedamsha(i * 30.0 + 0.01)
            assert vp.sign == "Capricorn", f"Even sign {SIGNS[i]}: expected Capricorn"

    def test_varga_number(self):
        assert akshavedamsha(0.0).varga_number == 45

    def test_sign_degree_in_range(self):
        for lon in range(0, 360, 5):
            vp = akshavedamsha(float(lon))
            assert 0.0 <= vp.sign_degree < 30.0


# ---------------------------------------------------------------------------
# Generic wrappers — varga_number and structural invariants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fn,n,name", [
    (shashthamsha,     6,  "Shashthamsha"),
    (ashtamsha,        8,  "Ashtamsha"),
    (shodashamsha,    16,  "Shodashamsha"),
    (vimshamsha,      20,  "Vimshamsha"),
    (chaturvimshamsha, 24, "Chaturvimshamsha"),
    (shashtiamsha,    60,  "Shashtiamsha"),
])
class TestGenericWrappers:
    def test_varga_number(self, fn, n, name):
        assert fn(0.0).varga_number == n

    def test_varga_name(self, fn, n, name):
        assert fn(0.0).varga_name == name

    def test_sign_degree_in_range(self, fn, n, name):
        for lon in range(0, 360, 13):
            vp = fn(float(lon))
            assert 0.0 <= vp.sign_degree < 30.0, f"{name}({lon}): sign_degree={vp.sign_degree}"

    def test_varga_longitude_in_range(self, fn, n, name):
        for lon in range(0, 360, 13):
            vp = fn(float(lon))
            assert 0.0 <= vp.varga_longitude < 360.0

    def test_longitude_reduction(self, fn, n, name):
        """360° wrap gives same result as 0°."""
        assert fn(360.0).sign == fn(0.0).sign


# ---------------------------------------------------------------------------
# VargaPoint structural invariants — all new wrappers
# ---------------------------------------------------------------------------

ALL_NEW_WRAPPERS = [
    hora, chaturthamsha, shashthamsha, ashtamsha,
    shodashamsha, vimshamsha, chaturvimshamsha,
    saptavimshamsha, khavedamsha, akshavedamsha, shashtiamsha,
]


def test_all_wrappers_return_vargapoint():
    for fn in ALL_NEW_WRAPPERS:
        assert isinstance(fn(45.0), VargaPoint)


def test_sign_and_sign_symbol_consistent():
    from moira.constants import SIGNS, SIGN_SYMBOLS
    signs = list(SIGNS)
    symbols = list(SIGN_SYMBOLS)
    for fn in ALL_NEW_WRAPPERS:
        for lon in range(0, 360, 30):
            vp = fn(float(lon))
            idx = signs.index(vp.sign)
            assert vp.sign_symbol == symbols[idx]


def test_varga_longitude_consistent_with_sign_and_degree():
    for fn in ALL_NEW_WRAPPERS:
        for lon in range(0, 360, 17):
            vp = fn(float(lon))
            from moira.constants import SIGNS
            sign_idx = list(SIGNS).index(vp.sign)
            expected_vl = sign_idx * 30.0 + vp.sign_degree
            assert math.isclose(vp.varga_longitude, expected_vl, abs_tol=1e-8), (
                f"{fn.__name__}({lon}): varga_longitude={vp.varga_longitude}, "
                f"expected={expected_vl}"
            )
