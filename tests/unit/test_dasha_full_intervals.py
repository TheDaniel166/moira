"""VA-01: BPHS 46 balance / 51 proportional children on the full parent axis."""

import pytest
import math

from moira.dasha import vimshottari, current_dasha, validate_vimshottari_output
from moira.dasha_systems import yogini_dasha, YoginiPolicy
from moira.sidereal import ayanamsa


@pytest.mark.parametrize(
    "year_days,year_basis", [(360.0, "savana_360"), (365.25, "julian_365.25")]
)
def test_half_ashwini_keeps_elapsed_ketu_subperiods(year_days, year_basis):
    jd = 2451545.0
    lon = ayanamsa(jd) + 20 / 3
    periods = vimshottari(lon, jd, levels=5, year_basis=year_basis)
    first = periods[0]
    # Ketu's first three children occupy 7*(7+20+6)/120 years. The next
    # Moon and Mars occupy 7*(10+7)/120: Rahu begins at 35/12 years.
    rahu = first.sub[0]
    assert rahu.planet == "Rahu"
    assert rahu.start_jd == jd
    assert rahu.full_start_jd == pytest.approx(jd - 7 * year_days / 12, abs=1e-9)
    assert rahu.end_jd == pytest.approx(jd + 7 * year_days / 15, abs=1e-9)
    assert first.full_start_jd == pytest.approx(jd - 3.5 * year_days, abs=1e-9)
    assert (
        current_dasha(lon, jd, jd, year_basis=year_basis, levels=2)[1].planet == "Rahu"
    )
    validate_vimshottari_output(periods)

    def check(p):
        assert p.full_start_jd <= p.start_jd < p.end_jd <= p.full_end_jd
        if p.sub:
            assert p.sub[0].start_jd == p.start_jd
            assert p.sub[-1].end_jd == p.end_jd
            assert all(a.end_jd == b.start_jd for a, b in zip(p.sub, p.sub[1:]))
            for child in p.sub:
                check(child)

    for p in periods:
        check(p)


def test_yogini_birth_and_horizon_clip_full_axis():
    jd = 2451545.0
    periods = yogini_dasha(
        ayanamsa(jd) + 20 / 3,
        jd,
        levels=4,
        policy=YoginiPolicy(year_basis="savana_360"),
    )
    assert periods[0].lord == "Bhramari"
    assert periods[0].sub[0].lord == "Siddha"
    assert periods[-1].end_jd == jd + 36 * 360
    assert periods[-1].full_end_jd == jd + 38 * 360
    assert periods[-1].sub[-1].lord == "Siddha"
    assert periods[0].year_days == 360
    assert periods[0].year_basis == "savana_360"
    # Legacy .years is explicitly Julian; the computation basis is separate.
    assert periods[0].years == 720 / 365.25


def test_einstein_balance_reference_precession_independently():
    """VA-11: ERFA p_A + IAU 2000A corroboration, no Dasha engine oracle."""
    import erfa
    from moira.julian import ut_to_tt
    from moira.precession import general_precession_in_longitude

    jd = 2407422.95138889
    tt = ut_to_tt(jd)
    pa = math.degrees(erfa.p06e(2451545.0, tt - 2451545.0)[12])
    assert general_precession_in_longitude(tt) == pytest.approx(pa, abs=1e-12)
    external_ayanamsa = (
        23.857092317461543
        + pa
        + math.degrees(erfa.nut00a(2451545.0, tt - 2451545.0)[0])
    )
    # 0.001 arcsecond is the established standards comparison tolerance.
    assert abs(ayanamsa(jd) - external_ayanamsa) * 3600 < 0.001
    # Frozen composition receipt uses the engine's independently checked
    # nutation value (not ERFA's slightly different series evaluation).
    reference = 23.857092317461543 + pa + 0.004135164632346308
    assert reference == pytest.approx(22.174240802711857, abs=1e-12)


@pytest.mark.parametrize(
    "values",
    [
        (True, 2.0, None, None),
        (None, 2.0, None, None),
        (0.0, 2.0, False, 3.0),
        (0.0, 2.0, None, 3.0),
        (0.0, 2.0, 0.0, 10**1000),
    ],
)
def test_full_interval_rejects_invalid_provenance(values):
    from moira._dasha_intervals import validate_interval

    with pytest.raises(ValueError):
        validate_interval(*values)


@pytest.mark.parametrize("year_days", [360.0, 365.25, 365.2422, 365.2564])
@pytest.mark.parametrize(
    "system,sequence,weights",
    [
        (
            "ashtottari",
            ("Sun", "Moon", "Mars", "Mercury", "Saturn", "Jupiter", "Rahu", "Venus"),
            (6, 15, 8, 17, 10, 19, 12, 21),
        ),
        (
            "yogini",
            (
                "Mangala",
                "Pingala",
                "Dhanya",
                "Bhramari",
                "Bhadrika",
                "Ulka",
                "Siddha",
                "Sankata",
            ),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    ],
)
@pytest.mark.parametrize("elapsed", [0.0, 0.5, 0.999])
def test_alternate_full_axis_all_clocks(year_days, system, sequence, weights, elapsed):
    from moira.dasha_systems import _compute_dashas

    birth = 2451545.0
    total = sum(weights)
    periods = _compute_dashas(
        sequence[3],
        elapsed,
        birth,
        dict(zip(sequence, weights)),
        list(sequence),
        total,
        year_days,
        system,
        4,
    )
    assert periods[0].start_jd == birth
    assert periods[-1].end_jd == birth + total * year_days

    def check(parent):
        if not parent.sub:
            return
        index = sequence.index(parent.lord)
        order = sequence[index:] + sequence[:index]
        elapsed_weight = 0
        expected = []
        for lord in order:
            a = (
                parent.full_start_jd
                + (parent.full_end_jd - parent.full_start_jd) * elapsed_weight / total
            )
            elapsed_weight += weights[sequence.index(lord)]
            b = (
                parent.full_start_jd
                + (parent.full_end_jd - parent.full_start_jd) * elapsed_weight / total
            )
            lo, hi = max(a, parent.start_jd), min(b, parent.end_jd)
            if hi > lo:
                expected.append((lord, lo, hi))
        assert len(expected) == len(parent.sub)
        for child, (lord, lo, hi) in zip(parent.sub, expected):
            assert child.lord == lord
            assert child.start_jd == pytest.approx(lo, abs=1e-9)
            assert child.end_jd == pytest.approx(hi, abs=1e-9)
            check(child)

    for period in periods:
        check(period)
