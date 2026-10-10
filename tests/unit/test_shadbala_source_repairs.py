"""VA-02/03/04/05/06 source and adversarial witnesses.

Raman 1996 local PDF SHA256
727c8063f64816a0c1c7f6bc577c249629854e980bf860bf4cfd8de16ec9bab2:
PDF7 positions; PDF27-28 article30/example9; PDF40-46 temporal rules;
PDF64-66 Ayana and war algebra. Printed decimal precision is retained.
BPHS Santhanam I PDF264/printed265 supplies the separately named scale.
"""

from dataclasses import replace
from itertools import permutations
from types import SimpleNamespace
import math
import pytest

from moira.shadbala import (
    sthana_bala,
    kala_bala,
    shadbala,
    ShadbalaPolicy,
    validate_shadbala_output,
    shadbala_network_profile,
    SthanaBala,
    KalaBala,
    _resolve_wars,
    graha_yuddha_pairs,
)
from moira.shadbala_context import ShadbalaContext, ShadbalaContextError, SEVEN
from moira._shadbala_components import saptavargaja_breakdown, strength_varga_sign


def context(positions=None, fraction=0.5, jd=2451545.0, declinations=None):
    p = (
        dict(zip(SEVEN, (0.0, 179.9, 90.0, 31.0, 150.0, 210.0, 270.0)))
        if positions is None
        else positions
    )
    return ShadbalaContext(
        jd,
        "Lahiri",
        tuple(p.items()),
        tuple((p, 0.0 if declinations is None else declinations[p]) for p in SEVEN),
        tuple((p, 30.0) for p in SEVEN),
        fraction,
        jd - 0.25,
        jd + 0.25,
        jd + 0.75,
        "Sun",
        "Moon",
        "Sun",
    )


def kala(p, c):
    lons = dict(c.sidereal_longitudes)
    return kala_bala(
        p, lons[p], lons["Sun"], c.jd, 1, c.is_day, c.vara_lord, {}, context=c
    )


@pytest.mark.parametrize(
    "fraction,day",
    [(0.0, 0.0), (0.125, 15.0), (0.25, 30.0), (0.5, 60.0), (0.75, 30.0), (0.875, 15.0)],
)
def test_nathonnatha_source_linear_apparent_time(fraction, day):
    c = context(fraction=fraction)
    assert kala("Sun", c).nathonnatha == day
    assert kala("Moon", c).nathonnatha == 60 - day
    assert kala("Mercury", c).nathonnatha == 60


def test_continuous_paksha_and_moon_doubling():
    c = context()
    assert kala("Moon", c).paksha == pytest.approx(2 * 179.9 / 3, abs=1e-12)
    for phase in (
        0.0,
        math.nextafter(180.0, 0.0),
        180.0,
        math.nextafter(180.0, 360.0),
        359.9,
    ):
        p = dict(c.sidereal_longitudes)
        p["Moon"] = phase
        cc = context(p)
        bright = min(phase, 360 - phase) / 3
        assert kala("Venus", cc).paksha == pytest.approx(bright, abs=1e-12)
        assert kala("Sun", cc).paksha == pytest.approx(60 - bright, abs=1e-12)


@pytest.mark.parametrize(
    "offset,lord",
    [
        (0, "Mercury"),
        (1 / 6, "Sun"),
        (1 / 3, "Saturn"),
        (0.5, "Moon"),
        (2 / 3, "Venus"),
        (5 / 6, "Mars"),
    ],
)
def test_tribhaga_exact_thirds(offset, lord):
    rise = 2451544.75
    c = context(jd=rise + offset)
    c = replace(c, sunrise_jd=rise, sunset_jd=rise + 0.5, next_sunrise_jd=rise + 1)
    assert kala(lord, c).tribhaga == 60
    assert kala("Jupiter", c).tribhaga == 60
    assert sum(kala(p, c).tribhaga for p in SEVEN) == 120


@pytest.mark.parametrize(
    "planet,dec,expected",
    [
        ("Sun", -8.75, 38.125),
        ("Moon", -10.75, 43.4375),
        ("Mars", -22.45, 1.9375),
        ("Mercury", -9.0, 41.25),
        ("Jupiter", 23.5, 59.375),
        ("Venus", -4.96, 23.8),
        ("Saturn", 13.0, 13.75),
    ],
)
def test_ayana_source_algebra(planet, dec, expected):
    c = context(declinations=dict.fromkeys(SEVEN, dec))
    assert kala(planet, c).ayana == pytest.approx(expected, abs=1e-12)
    # Some printed example totals contain rounding/arithmetic discrepancies;
    # this test follows the explicitly printed article75 algebra and inputs.


def test_raman_printed_sun_saptavargaja_90():
    dms = (
        (180, 53, 55),
        (311, 17, 19),
        (229, 30, 34),
        (181, 31, 34),
        (84, 0, 49),
        (171, 9, 56),
        (124, 22, 41),
    )
    positions = {p: d + m / 60 + s / 3600 for p, (d, m, s) in zip(SEVEN, dms)}
    entries = saptavargaja_breakdown("Sun", positions["Sun"], positions)
    assert [e.shashtiamsas for e in entries] == [7.5, 30, 7.5, 7.5, 7.5, 7.5, 22.5]
    assert sum(e.shashtiamsas for e in entries) == 90
    other = saptavargaja_breakdown(
        "Sun", positions["Sun"], positions, "bphs_santhanam_27"
    )
    assert [e.shashtiamsas for e in other] == [10, 30, 10, 10, 10, 10, 20]


@pytest.mark.parametrize(
    "lon,expected", [(1.0, 30.0), (31.0, 0.0), (4.0, 15.0), (34.0, 15.0)]
)
def test_mercury_ojayugma_source_parities(lon, expected):
    positions = dict(context().sidereal_longitudes)
    positions["Mercury"] = lon
    b = sthana_bala(
        "Mercury",
        lon,
        SimpleNamespace(asc=0.0),
        2451545.0,
        sidereal_longitudes=positions,
    )
    assert b.ojayugma == expected


def test_moolatrikona_actual_degree_and_d1_only():
    p = dict(context().sidereal_longitudes)
    p["Sun"] = 125.0
    e = saptavargaja_breakdown("Sun", 125.0, p)
    assert e[0].dignity == "mulatrikona" and e[0].shashtiamsas == 45
    assert all(x.shashtiamsas <= 30 for x in e[1:])
    p["Sun"] = 145.0
    assert saptavargaja_breakdown("Sun", 145.0, p)[0].shashtiamsas == 30


@pytest.mark.parametrize(
    "lon,n,expected",
    [(30.0, 7, 7), (30.0, 12, 1), (10.0, 30, 8), (40.0, 30, 5), (55.0, 30, 7)],
)
def test_source_divisions(lon, n, expected):
    assert strength_varga_sign(lon, n) == expected


def test_context_required_polar_and_mismatch():
    with pytest.raises(ShadbalaContextError, match="requires explicit"):
        kala_bala("Sun", 0.0, 0.0, 2451545.0, 1, True, "Sun", {})
    c = replace(context(), sunrise_jd=None, sunset_jd=None, next_sunrise_jd=None)
    assert c.missing_components == ("tribhaga",)
    with pytest.raises(ShadbalaContextError, match="missing sunrise"):
        kala("Sun", c)
    with pytest.raises(ShadbalaContextError, match="position mismatch"):
        context().check_positions(2451545.0, "Lahiri", {"Sun": 1.0})


def test_war_source_formula_multiway_conservation_and_permutation():
    positions = dict(zip(SEVEN, (90.0, 180.0, 10.0, 10.2, 10.4, 210.0, 270.0)))
    s = SthanaBala(10, 30, 15, 30, 0, 85)
    k = KalaBala(30, 30, 60, 45, 30, 0, 195)
    raw = {p: (s, float(i * 10), k, 30.0, 20.0, 0.0) for i, p in enumerate(SEVEN)}
    baseline = _resolve_wars(raw, positions)
    # Mars/Mercury aggregate difference10 divided by 9.4-6.6 = 25/7.
    pair = next(w for w in baseline.pairs if {w.victor, w.loser} == {"Mars", "Mercury"})
    assert pair.victor == "Mars"
    assert pair.adjustment_shashtiamsas == pytest.approx(25 / 7, abs=1e-12)
    assert pair.chesta_transferred is None
    assert math.fsum(v for _, v in baseline.adjustments) == pytest.approx(0, abs=1e-12)
    assert dict(baseline.raw_chesta) == dict.fromkeys(SEVEN, 30.0)
    for order in permutations(("Mars", "Mercury", "Jupiter")):
        reordered = {
            p: positions[p] for p in (*order, "Sun", "Moon", "Venus", "Saturn")
        }
        assert _resolve_wars(dict(reversed(list(raw.items()))), reordered) == baseline
    assert not graha_yuddha_pairs({"Mars": 10.0, "Mercury": 11.0})
    tie = _resolve_wars(raw, {**positions, "Mercury": 10.0}).pairs
    assert next(w for w in tie if w.tied).adjustment_shashtiamsas == 0.0


def test_canonical_ledger_controls_network_and_detects_tamper():
    c = context(dict(zip(SEVEN, (90.0, 180.0, 10.0, 10.2, 10.4, 210.0, 270.0))))
    r = shadbala(
        dict(c.sidereal_longitudes),
        dict.fromkeys(SEVEN, 1.0),
        SimpleNamespace(asc=0.0),
        c.jd,
        1,
        c.vara_lord,
        c.is_day,
        context=c,
        policy=ShadbalaPolicy(),
    )
    validate_shadbala_output(r)
    assert shadbala_network_profile(r).active_wars == r.war_resolution.pairs
    ps = r.planets["Mars"]
    broken = replace(
        r,
        planets={
            **r.planets,
            "Mars": replace(ps, kala_bala=replace(ps.kala_bala, yuddha=0.0)),
        },
    )
    with pytest.raises(ValueError, match="inconsistent"):
        validate_shadbala_output(broken)


@pytest.mark.parametrize("origin", range(12))
@pytest.mark.parametrize("distance", range(1, 13))
def test_shared_temporary_friendship_source_houses(origin, distance):
    from moira.vedic_dignities import _temporary_relationship

    assert _temporary_relationship(origin, (origin + distance - 1) % 12) == (
        "friend" if distance in (2, 3, 4, 10, 11, 12) else "enemy"
    )


@pytest.mark.parametrize(
    "values",
    [
        (0, 40, 80, 120, 160),
        (10, 10.2, 80, 120, 160),
        (10, 10.2, 10.4, 120, 160),
        (10.4, 10.2, 10, 120, 160),
        (10, 10.8, 11.6, 120, 160),
        (10, 10.2, 10.4, 10.6, 10.8),
        (10, 10, 10, 10, 10),
    ],
)
def test_war_graphs_against_independent_pair_sum(values):
    eligible = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    positions = {"Sun": 200.0, "Moon": 250.0, **dict(zip(eligible, values))}
    diam = dict(zip(eligible, (9.4, 6.6, 190.4, 16.6, 158.0)))
    # Fixed bases include a zero; every expected amount follows the printed quotient.
    bases = dict(zip(SEVEN, (0.0, 0.0, 0.0, 10.0, 30.0, 60.0, 100.0)))
    raw = {
        p: (
            SthanaBala(0, 0, 0, 0, 0, 0),
            bases[p],
            KalaBala(0, 0, 0, 0, 0, 0, 0),
            0.0,
            0.0,
            0.0,
        )
        for p in SEVEN
    }
    expected = dict.fromkeys(SEVEN, 0.0)
    for i, p in enumerate(eligible):
        for q in eligible[i + 1 :]:
            if abs(positions[p] - positions[q]) >= 1 or positions[p] == positions[q]:
                continue
            w, l = (p, q) if positions[p] < positions[q] else (q, p)
            delta = abs(bases[p] - bases[q]) / abs(diam[p] - diam[q])
            expected[w] += delta
            expected[l] -= delta
    ledger = _resolve_wars(raw, positions)
    assert dict(ledger.adjustments) == pytest.approx(expected, abs=1e-12)
    assert math.fsum(v for _, v in ledger.adjustments) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize(
    "field,value",
    [
        ("jd", True),
        ("jd", 10**1000),
        ("local_apparent_day_fraction", "0.5"),
        ("ayanamsa_system", True),
        ("observer_latitude", False),
    ],
)
def test_context_strict_scalar_admission(field, value):
    with pytest.raises(ShadbalaContextError):
        replace(context(), **{field: value})


def test_context_receipts_and_signed_fields_cannot_be_forged():
    c = context()
    r = shadbala(
        dict(c.sidereal_longitudes),
        dict.fromkeys(SEVEN, 1.0),
        SimpleNamespace(asc=0.0),
        c.jd,
        1,
        c.vara_lord,
        c.is_day,
        context=c,
    )
    for bad in (
        replace(r, war_resolution=None),
        replace(r, context=None),
        replace(r, war_resolution=replace(r.war_resolution, source="invented")),
    ):
        with pytest.raises(ValueError):
            validate_shadbala_output(bad)
    ps = r.planets["Sun"]
    with pytest.raises(ValueError):
        validate_shadbala_output(
            replace(
                r,
                planets={
                    **r.planets,
                    "Sun": replace(ps, kala_bala=replace(ps.kala_bala, ayana=True)),
                },
            )
        )


@pytest.mark.parametrize(
    "phase",
    [0.0, math.nextafter(84.0, 0.0), 84.0, math.nextafter(264.0, 0.0), 264.0, 359.0],
)
def test_named_paksha_nature_boundaries_and_mercury_options(phase):
    p = dict(context().sidereal_longitudes)
    p["Moon"] = phase
    c = context(p)
    bright = min(phase, 360 - phase) / 3
    expected = 2 * (bright if 84 <= phase < 264 else 60 - bright)
    assert kala("Moon", c).paksha == pytest.approx(expected, abs=1e-12)
    assert kala(
        "Mercury", replace(c, mercury_nature="benefic")
    ).paksha == pytest.approx(bright, abs=1e-12)
    assert kala(
        "Mercury", replace(c, mercury_nature="malefic")
    ).paksha == pytest.approx(60 - bright, abs=1e-12)


@pytest.mark.parametrize("dec", [-30.0, -24.0, 0.0, 24.0, 30.0])
def test_ayana_signed_extrema_and_mercury_floor(dec):
    c = context(declinations=dict.fromkeys(SEVEN, dec))
    assert kala("Sun", c).ayana == pytest.approx((24 + dec) * 2.5, abs=1e-12)
    assert kala("Moon", c).ayana == pytest.approx((24 - dec) * 1.25, abs=1e-12)
    assert kala("Mercury", c).ayana == pytest.approx((24 + abs(dec)) * 1.25, abs=1e-12)
    assert kala("Mercury", c).ayana >= 30


def test_strength_cyclic_negative_and_context_boundary_identity():
    p = dict(context().sidereal_longitudes)
    p["Mercury"] = -1e-300
    s = sthana_bala(
        "Mercury",
        p["Mercury"],
        SimpleNamespace(asc=0.0),
        2451545.0,
        sidereal_longitudes=p,
    )
    assert s.ojayugma == 0
    canonical = {**p, "Mercury": math.nextafter(360.0, 0.0)}
    c = context(canonical)
    result = shadbala(
        p,
        dict.fromkeys(SEVEN, 1.0),
        SimpleNamespace(asc=0.0),
        c.jd,
        1,
        c.vara_lord,
        c.is_day,
        context=c,
    )
    validate_shadbala_output(result)
    assert result.planets["Mercury"].sthana_bala == s
