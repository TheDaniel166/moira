from __future__ import annotations

import pytest


def test_vimshottari_default_uses_explicit_julian_year_basis() -> None:
    from moira.dasha import vimshottari

    periods = vimshottari(0.0, 2451545.0, levels=1)
    first = periods[0]

    assert (first.end_jd - first.start_jd) == pytest.approx(first.years * 365.25, abs=1e-9)


def test_vimshottari_can_use_julian_year_variant_explicitly() -> None:
    from moira.dasha import vimshottari

    savana = vimshottari(0.0, 2451545.0, levels=1, year_basis="savana_360")[0]
    julian = vimshottari(0.0, 2451545.0, levels=1, year_basis="julian_365.25")[0]

    assert (savana.end_jd - savana.start_jd) != pytest.approx(julian.end_jd - julian.start_jd, abs=1e-9)
    assert (julian.end_jd - julian.start_jd) == pytest.approx(julian.years * 365.25, abs=1e-9)


def test_vimshottari_supports_prana_level() -> None:
    from moira.dasha import vimshottari

    periods = vimshottari(0.0, 2451545.0, levels=5)

    def _max_level(items):
        max_level = 0
        stack = list(items)
        while stack:
            period = stack.pop()
            max_level = max(max_level, period.level)
            stack.extend(period.sub)
        return max_level

    assert _max_level(periods) == 5


def test_current_dasha_rejects_before_birth_and_beyond_cycle() -> None:
    from moira.dasha import current_dasha

    natal_jd = 2451545.0
    with pytest.raises(ValueError, match="must not be earlier than natal_jd"):
        current_dasha(0.0, natal_jd, natal_jd - 1.0)

    with pytest.raises(ValueError, match="beyond the Vimshottari cycle cap"):
        current_dasha(0.0, natal_jd, natal_jd + 120.0 * 365.25 + 1.0)


def test_invalid_year_basis_fails_clearly() -> None:
    from moira.dasha import vimshottari

    with pytest.raises(ValueError, match="supported Vimshottari doctrine key"):
        vimshottari(0.0, 2451545.0, year_basis="bad")


def test_dasha_period_level_name_includes_prana() -> None:
    from moira.dasha import DashaPeriod

    period = DashaPeriod(level=5, planet="Mercury", start_jd=2451545.0, end_jd=2451546.0)
    assert period.level_name == "Prana"


# ---------------------------------------------------------------------------
# Phase 1 truth preservation — DashaPeriod
# ---------------------------------------------------------------------------

def test_vimshottari_first_mahadasha_carries_birth_nakshatra() -> None:
    """The first Mahadasha preserves the Moon's birth nakshatra."""
    from moira.dasha import vimshottari
    from moira.sidereal import NAKSHATRA_NAMES, NAKSHATRA_SPAN, tropical_to_sidereal, Ayanamsa

    natal_jd = 2451545.0
    moon_lon = 45.0  # tropical longitude

    periods = vimshottari(moon_lon, natal_jd, levels=1)
    first = periods[0]

    sid_lon = tropical_to_sidereal(moon_lon, natal_jd, system=Ayanamsa.LAHIRI)
    expected_nak = NAKSHATRA_NAMES[int(sid_lon / NAKSHATRA_SPAN) % 27]

    assert first.birth_nakshatra == expected_nak


def test_vimshottari_only_first_mahadasha_carries_birth_nakshatra() -> None:
    """Subsequent Mahadashas have birth_nakshatra = None."""
    from moira.dasha import vimshottari

    periods = vimshottari(45.0, 2451545.0, levels=1)
    assert periods[0].birth_nakshatra is not None
    for p in periods[1:]:
        assert p.birth_nakshatra is None


def test_vimshottari_first_mahadasha_carries_nakshatra_fraction() -> None:
    """The first Mahadasha preserves nakshatra_fraction in [0, 1)."""
    from moira.dasha import vimshottari

    periods = vimshottari(45.0, 2451545.0, levels=1)
    frac = periods[0].nakshatra_fraction

    assert frac is not None
    assert 0.0 <= frac < 1.0


def test_vimshottari_nakshatra_fraction_consistent_with_balance() -> None:
    """nakshatra_fraction is consistent with dasha_balance remaining years."""
    from moira.dasha import vimshottari, dasha_balance, VIMSHOTTARI_YEARS

    moon_lon = 45.0
    natal_jd = 2451545.0

    periods = vimshottari(moon_lon, natal_jd, levels=1)
    first = periods[0]
    lord, balance_years = dasha_balance(moon_lon, natal_jd)

    assert lord == first.planet
    # fraction_elapsed = 1 - (balance / total_lord_years)
    expected_fraction = 1.0 - balance_years / VIMSHOTTARI_YEARS[lord]
    assert first.nakshatra_fraction == pytest.approx(expected_fraction, abs=1e-9)


def test_vimshottari_year_basis_preserved_on_mahadasha() -> None:
    """year_basis doctrinal name is preserved on all Mahadashas."""
    from moira.dasha import vimshottari

    for basis in ("julian_365.25", "savana_360"):
        periods = vimshottari(0.0, 2451545.0, levels=1, year_basis=basis)
        for p in periods:
            assert p.year_basis == basis


def test_vimshottari_year_basis_propagates_to_sub_periods() -> None:
    """year_basis propagates from Mahadasha to all generated sub-periods."""
    from moira.dasha import vimshottari

    periods = vimshottari(0.0, 2451545.0, levels=3, year_basis="savana_360")

    def _check(items: list) -> None:
        for p in items:
            assert p.year_basis == "savana_360"
            _check(p.sub)

    _check(periods)


# ---------------------------------------------------------------------------
# Phase 2 classification — DashaPeriod.lord_type
# ---------------------------------------------------------------------------

def test_dasha_lord_type_luminaries() -> None:
    """Sun and Moon periods carry LUMINARY lord_type."""
    from moira.dasha import vimshottari, DashaLordType

    periods = vimshottari(0.0, 2451545.0, levels=2)

    def _all_periods(items):
        for p in items:
            yield p
            yield from _all_periods(p.sub)

    for p in _all_periods(periods):
        if p.planet in ("Sun", "Moon"):
            assert p.lord_type == DashaLordType.LUMINARY


def test_dasha_lord_type_inner_planets() -> None:
    """Mercury and Venus periods carry INNER lord_type."""
    from moira.dasha import vimshottari, DashaLordType

    periods = vimshottari(0.0, 2451545.0, levels=2)

    def _all_periods(items):
        for p in items:
            yield p
            yield from _all_periods(p.sub)

    for p in _all_periods(periods):
        if p.planet in ("Mercury", "Venus"):
            assert p.lord_type == DashaLordType.INNER


def test_dasha_lord_type_outer_planets() -> None:
    """Mars, Jupiter, Saturn periods carry OUTER lord_type."""
    from moira.dasha import vimshottari, DashaLordType

    periods = vimshottari(0.0, 2451545.0, levels=2)

    def _all_periods(items):
        for p in items:
            yield p
            yield from _all_periods(p.sub)

    for p in _all_periods(periods):
        if p.planet in ("Mars", "Jupiter", "Saturn"):
            assert p.lord_type == DashaLordType.OUTER


def test_dasha_lord_type_nodes() -> None:
    """Rahu and Ketu periods carry NODE lord_type."""
    from moira.dasha import vimshottari, DashaLordType

    periods = vimshottari(0.0, 2451545.0, levels=2)

    def _all_periods(items):
        for p in items:
            yield p
            yield from _all_periods(p.sub)

    for p in _all_periods(periods):
        if p.planet in ("Rahu", "Ketu"):
            assert p.lord_type == DashaLordType.NODE


def test_dasha_lord_type_covers_all_nine_planets() -> None:
    """Every planet in VIMSHOTTARI_SEQUENCE has a lord_type."""
    from moira.dasha import VIMSHOTTARI_SEQUENCE, _DASHA_LORD_TYPE, DashaLordType

    valid_types = {DashaLordType.LUMINARY, DashaLordType.INNER,
                   DashaLordType.OUTER, DashaLordType.NODE}
    for planet in VIMSHOTTARI_SEQUENCE:
        assert _DASHA_LORD_TYPE[planet] in valid_types


# ---------------------------------------------------------------------------
# Phase 3 inspectability — DashaPeriod
# ---------------------------------------------------------------------------

def test_dasha_period_rejects_invalid_level() -> None:
    """DashaPeriod.__post_init__ rejects levels outside {1, 2, 3, 4, 5}."""
    from moira.dasha import DashaPeriod

    with pytest.raises(ValueError, match="level must be 1"):
        DashaPeriod(level=0, planet="Sun", start_jd=2451545.0, end_jd=2451546.0)

    with pytest.raises(ValueError, match="level must be 1"):
        DashaPeriod(level=6, planet="Sun", start_jd=2451545.0, end_jd=2451546.0)


def test_dasha_period_rejects_inverted_jd() -> None:
    """DashaPeriod.__post_init__ rejects end_jd <= start_jd."""
    from moira.dasha import DashaPeriod

    with pytest.raises(ValueError, match="end_jd must be greater than start_jd"):
        DashaPeriod(level=1, planet="Moon", start_jd=2451546.0, end_jd=2451545.0)

    with pytest.raises(ValueError, match="end_jd must be greater than start_jd"):
        DashaPeriod(level=1, planet="Moon", start_jd=2451545.0, end_jd=2451545.0)


def test_dasha_period_rejects_unknown_planet() -> None:
    """DashaPeriod.__post_init__ rejects planets not in VIMSHOTTARI_SEQUENCE."""
    from moira.dasha import DashaPeriod

    with pytest.raises(ValueError, match="Vimshottari lord"):
        DashaPeriod(level=1, planet="Pluto", start_jd=2451545.0, end_jd=2451546.0)


def test_dasha_period_is_node_dasha() -> None:
    """is_node_dasha is True for Rahu/Ketu periods, False otherwise."""
    from moira.dasha import DashaPeriod, DashaLordType

    rahu  = DashaPeriod(level=1, planet="Rahu",  start_jd=2451545.0, end_jd=2458122.0,
                        lord_type=DashaLordType.NODE)
    ketu  = DashaPeriod(level=1, planet="Ketu",  start_jd=2451545.0, end_jd=2454102.0,
                        lord_type=DashaLordType.NODE)
    venus = DashaPeriod(level=1, planet="Venus", start_jd=2451545.0, end_jd=2458845.0,
                        lord_type=DashaLordType.INNER)

    assert rahu.is_node_dasha is True
    assert ketu.is_node_dasha is True
    assert venus.is_node_dasha is False


def test_dasha_period_is_luminary_dasha() -> None:
    """is_luminary_dasha is True for Sun/Moon periods, False otherwise."""
    from moira.dasha import DashaPeriod, DashaLordType

    sun   = DashaPeriod(level=1, planet="Sun",  start_jd=2451545.0, end_jd=2453735.0,
                        lord_type=DashaLordType.LUMINARY)
    moon  = DashaPeriod(level=1, planet="Moon", start_jd=2451545.0, end_jd=2455197.0,
                        lord_type=DashaLordType.LUMINARY)
    mars  = DashaPeriod(level=1, planet="Mars", start_jd=2451545.0, end_jd=2454102.0,
                        lord_type=DashaLordType.OUTER)

    assert sun.is_luminary_dasha is True
    assert moon.is_luminary_dasha is True
    assert mars.is_luminary_dasha is False


def test_dasha_period_days_equals_jd_span() -> None:
    """days property returns end_jd - start_jd exactly."""
    from moira.dasha import DashaPeriod

    p = DashaPeriod(level=1, planet="Mercury", start_jd=2451545.0, end_jd=2457755.0)
    assert p.days == pytest.approx(2457755.0 - 2451545.0, abs=1e-12)


def test_dasha_period_is_active_at_boundary_semantics() -> None:
    """is_active_at uses half-open [start, end) interval."""
    from moira.dasha import DashaPeriod

    p = DashaPeriod(level=1, planet="Jupiter", start_jd=2451545.0, end_jd=2457391.0)

    assert p.is_active_at(2451545.0) is True       # exactly at start
    assert p.is_active_at(2454000.0) is True       # mid-period
    assert p.is_active_at(2457391.0) is False      # exactly at end — excluded
    assert p.is_active_at(2457391.1) is False      # past end
    assert p.is_active_at(2451544.9) is False      # before start


# ---------------------------------------------------------------------------
# Phase 4 doctrine / policy surface — VimshottariComputationPolicy
# ---------------------------------------------------------------------------

def test_vimshottari_default_policy_is_frozen_sentinel() -> None:
    """DEFAULT_VIMSHOTTARI_POLICY is a frozen sentinel with expected defaults."""
    from moira.dasha import DEFAULT_VIMSHOTTARI_POLICY, VimshottariComputationPolicy
    from moira.sidereal import Ayanamsa

    assert isinstance(DEFAULT_VIMSHOTTARI_POLICY, VimshottariComputationPolicy)
    assert DEFAULT_VIMSHOTTARI_POLICY.year.year_basis == "julian_365.25"
    assert DEFAULT_VIMSHOTTARI_POLICY.ayanamsa.ayanamsa_system == Ayanamsa.LAHIRI


def test_vimshottari_policy_none_produces_same_output_as_default() -> None:
    """Passing policy=None produces identical results to the default policy."""
    from moira.dasha import vimshottari, DEFAULT_VIMSHOTTARI_POLICY

    p_none    = vimshottari(45.0, 2451545.0, levels=1)
    p_default = vimshottari(45.0, 2451545.0, levels=1, policy=DEFAULT_VIMSHOTTARI_POLICY)

    assert len(p_none) == len(p_default)
    for a, b in zip(p_none, p_default):
        assert a.start_jd == pytest.approx(b.start_jd, abs=1e-9)
        assert a.end_jd   == pytest.approx(b.end_jd,   abs=1e-9)


def test_vimshottari_policy_year_basis_governs_period_boundaries() -> None:
    """Policy year_basis governs period boundary scaling."""
    from moira.dasha import vimshottari, VimshottariYearPolicy, VimshottariComputationPolicy

    pol_julian = VimshottariComputationPolicy(year=VimshottariYearPolicy(year_basis="julian_365.25"))
    pol_savana = VimshottariComputationPolicy(year=VimshottariYearPolicy(year_basis="savana_360"))

    p_julian = vimshottari(0.0, 2451545.0, levels=1, policy=pol_julian)
    p_savana = vimshottari(0.0, 2451545.0, levels=1, policy=pol_savana)

    # Cycle total spans should differ proportionally
    span_julian = p_julian[-1].end_jd - p_julian[0].start_jd
    span_savana = p_savana[-1].end_jd - p_savana[0].start_jd
    assert span_julian != pytest.approx(span_savana, rel=1e-6)
    assert span_julian / span_savana == pytest.approx(365.25 / 360.0, rel=1e-6)


def test_vimshottari_explicit_year_basis_overrides_policy() -> None:
    """An explicit year_basis kwarg takes precedence over the policy default."""
    from moira.dasha import vimshottari, VimshottariYearPolicy, VimshottariComputationPolicy

    # Policy says savana_360 but explicit kwarg says julian_365.25
    pol_savana = VimshottariComputationPolicy(year=VimshottariYearPolicy(year_basis="savana_360"))
    p_override = vimshottari(0.0, 2451545.0, levels=1, year_basis="julian_365.25", policy=pol_savana)
    p_julian   = vimshottari(0.0, 2451545.0, levels=1, year_basis="julian_365.25")

    for a, b in zip(p_override, p_julian):
        assert a.end_jd == pytest.approx(b.end_jd, abs=1e-9)


def test_vimshottari_policy_rejects_invalid_year_basis() -> None:
    """_validate_vimshottari_policy raises ValueError for unknown year_basis."""
    from moira.dasha import VimshottariYearPolicy, VimshottariComputationPolicy, _validate_vimshottari_policy

    with pytest.raises(ValueError, match="supported Vimshottari doctrine key"):
        _validate_vimshottari_policy(
            VimshottariComputationPolicy(year=VimshottariYearPolicy(year_basis="tropical_365"))
        )


def test_vimshottari_policy_rejects_empty_ayanamsa() -> None:
    """_validate_vimshottari_policy raises ValueError for empty ayanamsa_system."""
    from moira.dasha import VimshottariAyanamsaPolicy, VimshottariComputationPolicy, _validate_vimshottari_policy

    with pytest.raises(ValueError, match="ayanamsa_system must be non-empty"):
        _validate_vimshottari_policy(
            VimshottariComputationPolicy(ayanamsa=VimshottariAyanamsaPolicy(ayanamsa_system=""))
        )


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization tests
# ---------------------------------------------------------------------------

# Moon at 10° (Ashvini) → Ketu Mahadasha at birth.
# JD_BIRTH = 2415020.0 ≈ 1900-01-01; birth is treated as JD_BIRTH itself so
# the first Mahadasha is always active at JD_BIRTH + 100 days.
_P5_MOON_LON = 10.0
_P5_JD_BIRTH = 2415020.0
_P5_JD_QUERY = _P5_JD_BIRTH + 100.0  # well inside the first Mahadasha


def _active_at(periods: list, jd: float) -> list:
    """Return all periods (any level) that are active at *jd*."""
    result = []
    for p in periods:
        if p.is_active_at(jd):
            result.append(p)
        if hasattr(p, "sub") and p.sub:
            result.extend(_active_at(p.sub, jd))
    return result


def test_dasha_active_line_mahadasha_is_level1() -> None:
    """dasha_active_line sets mahadasha from the level-1 period."""
    from moira.dasha import vimshottari, dasha_active_line
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    assert line.mahadasha.level == 1


def test_dasha_active_line_antardasha_is_level2() -> None:
    """dasha_active_line sets antardasha from the level-2 period when levels=2."""
    from moira.dasha import vimshottari, dasha_active_line
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    assert line.antardasha is not None
    assert line.antardasha.level == 2


def test_dasha_active_line_depth_matches_levels_generated() -> None:
    """DashaActiveLine.depth equals the number of levels generated."""
    from moira.dasha import vimshottari, dasha_active_line
    for levels in (1, 2, 3):
        periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=levels)
        active = _active_at(periods, _P5_JD_QUERY)
        line = dasha_active_line(active)
        assert line.depth == levels, f"depth {line.depth} != levels {levels}"


def test_dasha_active_line_as_list_round_trips() -> None:
    """DashaActiveLine.as_list() returns periods in level order matching input."""
    from moira.dasha import vimshottari, dasha_active_line
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=3)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    result = line.as_list()
    assert [p.level for p in result] == list(range(1, len(result) + 1))


def test_dasha_active_line_rejects_empty_input() -> None:
    """dasha_active_line raises ValueError for an empty period list."""
    from moira.dasha import dasha_active_line
    with pytest.raises(ValueError, match="must not be empty"):
        dasha_active_line([])


def test_dasha_active_line_rejects_non_level1_mahadasha() -> None:
    """DashaActiveLine raises ValueError when mahadasha is not a level-1 period."""
    from moira.dasha import vimshottari, DashaActiveLine
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    antardasha = next(p for p in active if p.level == 2)
    with pytest.raises(ValueError, match="level 1"):
        DashaActiveLine(mahadasha=antardasha)


def test_dasha_active_line_higher_levels_are_none_when_not_generated() -> None:
    """DashaActiveLine has None for levels beyond those generated."""
    from moira.dasha import vimshottari, dasha_active_line
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    assert line.antardasha      is None
    assert line.pratyantardasha is None
    assert line.sookshma        is None
    assert line.prana           is None


# ---------------------------------------------------------------------------
# Phase 6 — Relational Hardening / Inspectability tests
# ---------------------------------------------------------------------------

def test_dasha_active_line_lord_types_length_matches_depth() -> None:
    """DashaActiveLine.lord_types has one entry per active level."""
    from moira.dasha import vimshottari, dasha_active_line
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=3)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    assert len(line.lord_types) == line.depth


def test_dasha_active_line_lord_types_are_valid_constants() -> None:
    """DashaActiveLine.lord_types contains only recognised DashaLordType strings."""
    from moira.dasha import vimshottari, dasha_active_line, DashaLordType
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=3)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    valid = {DashaLordType.LUMINARY, DashaLordType.INNER,
             DashaLordType.OUTER,    DashaLordType.NODE}
    for lt in line.lord_types:
        assert lt in valid, f"unexpected lord_type {lt!r}"


def test_dasha_active_line_is_node_chain_for_node_mahadasha() -> None:
    """is_node_chain is True when any active lord is Rahu or Ketu."""
    from moira.dasha import vimshottari, dasha_active_line, DashaLordType
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    # Find the first node Mahadasha and query its midpoint
    node_period = next(
        (p for p in periods if p.level == 1 and p.lord_type == DashaLordType.NODE),
        None,
    )
    assert node_period is not None, "expected at least one node Mahadasha in the sequence"
    mid_jd = (node_period.start_jd + node_period.end_jd) / 2.0
    active = _active_at(periods, mid_jd)
    line = dasha_active_line(active)
    assert line.is_node_chain


def test_dasha_active_line_is_not_node_chain_for_outer_planet_mahadasha() -> None:
    """is_node_chain is False when no active lord is a node."""
    from moira.dasha import vimshottari, dasha_active_line, DashaLordType
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    # Find the first outer-planet Mahadasha and query its midpoint
    outer_period = next(
        (p for p in periods if p.level == 1 and p.lord_type == DashaLordType.OUTER),
        None,
    )
    assert outer_period is not None, "expected at least one outer-planet Mahadasha"
    mid_jd = (outer_period.start_jd + outer_period.end_jd) / 2.0
    active = _active_at(periods, mid_jd)
    line = dasha_active_line(active)
    assert not line.is_node_chain


def test_dasha_active_line_is_complete_at_level5() -> None:
    """DashaActiveLine.is_complete is True exactly when depth == 5."""
    from moira.dasha import vimshottari, dasha_active_line
    for levels in range(1, 6):
        periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=levels)
        active = _active_at(periods, _P5_JD_QUERY)
        line = dasha_active_line(active)
        assert line.is_complete == (levels == 5)


def test_dasha_active_line_rejects_temporal_containment_violation() -> None:
    """DashaActiveLine raises ValueError when antardasha is outside mahadasha range."""
    from moira.dasha import vimshottari, DashaActiveLine
    import dataclasses
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    maha = next(p for p in active if p.level == 1)
    antar = next(p for p in active if p.level == 2)
    bad_antar = dataclasses.replace(antar, start_jd=maha.start_jd - 100.0)
    with pytest.raises(ValueError, match="starts before its parent"):
        DashaActiveLine(mahadasha=maha, antardasha=bad_antar)


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition tests
# ---------------------------------------------------------------------------

def test_dasha_condition_profile_fields_match_period() -> None:
    """dasha_condition_profile produces a profile whose fields match the source period."""
    from moira.dasha import vimshottari, dasha_condition_profile
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    maha = periods[0]
    profile = dasha_condition_profile(maha)
    assert profile.planet          == maha.planet
    assert profile.level           == maha.level
    assert profile.level_name      == maha.level_name
    assert profile.lord_type       == maha.lord_type
    assert profile.days            == pytest.approx(maha.days)
    assert profile.year_basis      == maha.year_basis
    assert profile.is_node_dasha   == maha.is_node_dasha
    assert profile.is_luminary_dasha == maha.is_luminary_dasha


def test_dasha_condition_profile_level_name_matches_vimshottari_names() -> None:
    """dasha_condition_profile.level_name matches VIMSHOTTARI_LEVEL_NAMES for all levels."""
    from moira.dasha import vimshottari, dasha_condition_profile, VIMSHOTTARI_LEVEL_NAMES
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=5)
    active = _active_at(periods, _P5_JD_QUERY)
    for p in active:
        profile = dasha_condition_profile(p)
        assert profile.level_name == VIMSHOTTARI_LEVEL_NAMES[p.level]


def test_dasha_condition_profile_birth_nakshatra_on_first_mahadasha() -> None:
    """dasha_condition_profile preserves birth_nakshatra from the first Mahadasha."""
    from moira.dasha import vimshottari, dasha_condition_profile
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    first_maha = periods[0]
    profile = dasha_condition_profile(first_maha)
    assert profile.birth_nakshatra is not None
    assert profile.nakshatra_fraction is not None


def test_dasha_condition_profile_birth_nakshatra_none_on_later_mahadashas() -> None:
    """dasha_condition_profile has None birth_nakshatra for periods after the first."""
    from moira.dasha import vimshottari, dasha_condition_profile
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    for p in periods[1:]:
        profile = dasha_condition_profile(p)
        assert profile.birth_nakshatra is None


def test_dasha_condition_profile_is_node_and_luminary_are_exclusive() -> None:
    """is_node_dasha and is_luminary_dasha cannot both be True for the same period."""
    from moira.dasha import vimshottari, dasha_condition_profile
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    for p in periods:
        profile = dasha_condition_profile(p)
        assert not (profile.is_node_dasha and profile.is_luminary_dasha)


def test_dasha_condition_profile_lord_type_covers_all_nine_lords() -> None:
    """dasha_condition_profile assigns a non-None lord_type to every Mahadasha."""
    from moira.dasha import vimshottari, dasha_condition_profile
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    for p in periods:
        profile = dasha_condition_profile(p)
        assert profile.lord_type is not None


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence tests
# ---------------------------------------------------------------------------

def test_dasha_sequence_profile_mahadasha_count_is_nine() -> None:
    """DashaSequenceProfile has exactly 9 Mahadasha profiles for a complete cycle."""
    from moira.dasha import vimshottari, dasha_sequence_profile, VIMSHOTTARI_SEQUENCE
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    agg = dasha_sequence_profile(periods)
    assert agg.mahadasha_count == len(VIMSHOTTARI_SEQUENCE)


def test_dasha_sequence_profile_lord_type_counts_sum_to_nine() -> None:
    """lord-type counts in DashaSequenceProfile sum to mahadasha_count."""
    from moira.dasha import vimshottari, dasha_sequence_profile
    agg = dasha_sequence_profile(vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1))
    assert (agg.luminary_count + agg.inner_count
            + agg.outer_count + agg.node_count) == agg.mahadasha_count


def test_dasha_sequence_profile_total_years_equals_sum_of_profile_years() -> None:
    """DashaSequenceProfile.total_years equals the sum of individual profile years."""
    from moira.dasha import vimshottari, dasha_sequence_profile
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    agg = dasha_sequence_profile(periods)
    expected = sum(p.years for p in agg.profiles)
    assert agg.total_years == pytest.approx(expected, abs=1e-9)


def test_dasha_sequence_profile_total_years_bounded_by_cycle() -> None:
    """DashaSequenceProfile.total_years is positive and does not exceed 120 years."""
    from moira.dasha import vimshottari, dasha_sequence_profile, VIMSHOTTARI_TOTAL
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    agg = dasha_sequence_profile(periods)
    assert 0 < agg.total_years <= VIMSHOTTARI_TOTAL


def test_dasha_sequence_profile_has_node_dashas() -> None:
    """DashaSequenceProfile.has_node_dashas is True and node_count is 2 (Rahu + Ketu)."""
    from moira.dasha import vimshottari, dasha_sequence_profile
    agg = dasha_sequence_profile(vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1))
    assert agg.has_node_dashas
    assert agg.node_count == 2


def test_dasha_sequence_profile_known_lord_type_counts() -> None:
    """DashaSequenceProfile has the canonical 2/2/3/2 lord-type distribution."""
    from moira.dasha import vimshottari, dasha_sequence_profile
    agg = dasha_sequence_profile(vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1))
    # Luminaries: Sun, Moon = 2
    # Inner: Mercury, Venus = 2
    # Outer: Mars, Jupiter, Saturn = 3
    # Node: Rahu, Ketu = 2
    assert agg.luminary_count == 2
    assert agg.inner_count    == 2
    assert agg.outer_count    == 3
    assert agg.node_count     == 2


def test_dasha_sequence_profile_rejects_mismatched_mahadasha_count() -> None:
    """DashaSequenceProfile raises ValueError when mahadasha_count does not match profiles."""
    from moira.dasha import vimshottari, dasha_sequence_profile, DashaSequenceProfile
    agg = dasha_sequence_profile(vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1))
    with pytest.raises(ValueError, match="mahadasha_count must equal"):
        DashaSequenceProfile(
            profiles        = agg.profiles,
            mahadasha_count = agg.mahadasha_count + 1,  # wrong
            luminary_count  = agg.luminary_count,
            inner_count     = agg.inner_count,
            outer_count     = agg.outer_count,
            node_count      = agg.node_count,
            total_years     = agg.total_years,
        )


# ---------------------------------------------------------------------------
# Phase 9 — Network Intelligence tests
# ---------------------------------------------------------------------------

def test_dasha_lord_pair_maha_profile_matches_active_mahadasha() -> None:
    """dasha_lord_pair.maha_profile.planet matches the active Mahadasha planet."""
    from moira.dasha import vimshottari, dasha_active_line, dasha_lord_pair
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    line = dasha_active_line(active)
    pair = dasha_lord_pair(line)
    assert pair.maha_profile.planet == line.mahadasha.planet


def test_dasha_lord_pair_has_antar_when_level2_active() -> None:
    """DashaLordPair.has_antar is True when levels=2 is requested."""
    from moira.dasha import vimshottari, dasha_active_line, dasha_lord_pair
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    pair = dasha_lord_pair(dasha_active_line(active))
    assert pair.has_antar


def test_dasha_lord_pair_no_antar_when_level1_only() -> None:
    """DashaLordPair.has_antar is False when only Mahadasha level is generated."""
    from moira.dasha import vimshottari, dasha_active_line, dasha_lord_pair
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    active = _active_at(periods, _P5_JD_QUERY)
    pair = dasha_lord_pair(dasha_active_line(active))
    assert not pair.has_antar
    assert pair.antar_profile is None


def test_dasha_lord_pair_is_same_lord_for_self_dasha() -> None:
    """DashaLordPair.is_same_lord is True when Mahadasha and Antardasha lords match."""
    from moira.dasha import vimshottari, dasha_active_line, dasha_lord_pair
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    maha = next(p for p in active if p.level == 1)
    # First sub-period of each Mahadasha is the Mahadasha lord itself
    antar = next(
        p for p in active if p.level == 2 and p.planet == maha.planet
    ) if any(p.level == 2 and p.planet == maha.planet for p in active) else None
    if antar is None:
        # Query during a different moment where self-dasha is active
        import dataclasses as dc
        from moira.dasha import DashaActiveLine, dasha_lord_pair as dlp, dasha_condition_profile
        from moira.dasha import DashaConditionProfile
        fake_antar = dc.replace(maha, level=2)
        from moira.dasha import DashaActiveLine as DAL
        line = DAL(mahadasha=maha, antardasha=fake_antar)
        pair = dlp(line)
        assert pair.is_same_lord
    else:
        from moira.dasha import DashaActiveLine, dasha_lord_pair as dlp
        line = DashaActiveLine(mahadasha=maha, antardasha=antar)
        pair = dlp(line)
        assert pair.is_same_lord


def test_dasha_lord_pair_involves_node_when_either_lord_is_node() -> None:
    """DashaLordPair.involves_node is True when either lord is Rahu or Ketu."""
    from moira.dasha import vimshottari, dasha_active_line, dasha_lord_pair, DashaLordType
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    node_maha = next(
        p for p in periods if p.level == 1 and p.lord_type == DashaLordType.NODE
    )
    mid_jd = (node_maha.start_jd + node_maha.end_jd) / 2.0
    active = _active_at(periods, mid_jd)
    pair = dasha_lord_pair(dasha_active_line(active))
    assert pair.involves_node


def test_dasha_lord_pair_rejects_non_level1_maha() -> None:
    """DashaLordPair raises ValueError when maha_profile is not level 1."""
    from moira.dasha import vimshottari, dasha_condition_profile, DashaLordPair
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    active = _active_at(periods, _P5_JD_QUERY)
    antar = next(p for p in active if p.level == 2)
    with pytest.raises(ValueError, match="level 1"):
        DashaLordPair(
            maha_profile  = dasha_condition_profile(antar),  # wrong level
            antar_profile = None,
        )


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening tests
# ---------------------------------------------------------------------------

def test_validate_vimshottari_output_passes_for_valid_output() -> None:
    """validate_vimshottari_output passes silently for genuine vimshottari() output."""
    from moira.dasha import vimshottari, validate_vimshottari_output
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=3)
    validate_vimshottari_output(periods)  # must not raise


def test_validate_vimshottari_output_detects_out_of_order_mahadashas() -> None:
    """validate_vimshottari_output raises when Mahadasha periods are reversed."""
    from moira.dasha import vimshottari, validate_vimshottari_output
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    reversed_periods = list(reversed(periods))
    with pytest.raises(ValueError, match="out of order"):
        validate_vimshottari_output(reversed_periods)


def test_validate_vimshottari_output_detects_sub_outside_parent() -> None:
    """validate_vimshottari_output raises when a sub-period starts before its parent."""
    from moira.dasha import vimshottari, validate_vimshottari_output, DashaPeriod
    import dataclasses
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=2)
    maha = periods[0]
    if not maha.sub:
        pytest.skip("no sub-periods on first Mahadasha")
    # Craft a sub-period that starts 100 days before the Mahadasha
    bad_sub = dataclasses.replace(
        maha.sub[0],
        start_jd = maha.start_jd - 100.0,
    )
    bad_maha = dataclasses.replace(maha, sub=[bad_sub] + list(maha.sub[1:]))
    tampered = [bad_maha] + periods[1:]
    with pytest.raises(ValueError, match="starts before its parent"):
        validate_vimshottari_output(tampered)


def test_validate_vimshottari_output_detects_overlapping_mahadashas() -> None:
    """validate_vimshottari_output raises when two Mahadasha periods overlap in JD."""
    from moira.dasha import vimshottari, validate_vimshottari_output
    import dataclasses
    periods = vimshottari(_P5_MOON_LON, _P5_JD_BIRTH, levels=1)
    if len(periods) < 2:
        pytest.skip("need at least two Mahadasha periods")
    # Push the second Mahadasha's start_jd back into the first Mahadasha's span
    first  = periods[0]
    second = periods[1]
    overlap_start = (first.start_jd + first.end_jd) / 2.0
    # end_jd must still be > overlap_start so the vessel is valid
    overlap_end   = overlap_start + 1.0
    overlapping   = dataclasses.replace(second, start_jd=overlap_start, end_jd=overlap_end)
    tampered = [first, overlapping] + periods[2:]
    with pytest.raises(ValueError, match="overlap or are out of order"):
        validate_vimshottari_output(tampered)
