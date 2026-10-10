"""VA2: composition regressions from the second adversarial review."""

from dataclasses import asdict, replace
from datetime import datetime
import math
from types import SimpleNamespace

import pytest

from moira.dasha import DashaPeriod, _validate_dasha_sub_containment
from moira.dasha_systems import AlternateDashaPeriod, _validate_alternate_children
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.muhurta_lagna import evaluate_muhurta_lagna_strength
from moira.sade_sati import sade_sati_status
from moira.shadbala import shadbala, validate_shadbala_output, bhava_bala
from moira.shadbala_context import SEVEN, ShadbalaContext
from moira_server.models.alternate_dashas import AlternateDashaPeriodRequest


def strength_at(sun=90.0):
    positions = dict(zip(SEVEN, (sun, 179.9, 135., 31., 150., 210., 270.)))
    jd = 2451545.
    context = ShadbalaContext(
        jd, 'Lahiri', tuple(positions.items()), tuple((p, 0.) for p in SEVEN),
        tuple((p, 30.) for p in SEVEN), .5, jd-.25, jd+.25, jd+.75,
        'Sun', 'Moon', 'Sun',
    )
    return shadbala(positions, dict.fromkeys(SEVEN, 1.), SimpleNamespace(asc=0.),
                    jd, 1, 'Sun', True, context=context)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('dt,lord', [('2005-01-01T00:00:00+00:00', 'Saturn'),
                                   ('2020-01-01T00:00:00+00:00', 'Mercury')])
def test_derived_weekday_uses_civil_utc(moira_engine, dt, lord):
    utc = jd_from_datetime(datetime.fromisoformat(dt))
    context = moira_engine.shadbala_context(utc_to_ut1(utc), 28.6, 77.2)
    assert context.vara_lord == lord
    assert context.vara_basis == 'civil_utc_midnight'
    assert context.vara_jd_utc == utc


@pytest.mark.parametrize('boundary', [90., 10./3])
@pytest.mark.parametrize('toward', [0., 360.])
def test_lagna_canonicalizes_tolerated_angles_before_discrete_decisions(boundary, toward):
    strength = strength_at(boundary)
    positions = dict(strength.context.sidereal_longitudes)
    baseline = evaluate_muhurta_lagna_strength(positions, jd_ut1=strength.jd,
        lagna_sidereal_longitude=0., shadbala_result=strength)
    positions['Sun'] = math.nextafter(boundary, toward)
    actual = evaluate_muhurta_lagna_strength(positions, jd_ut1=strength.jd,
        lagna_sidereal_longitude=0., shadbala_result=strength)
    assert actual.planets == baseline.planets
    assert actual.placement_score == baseline.placement_score
    assert actual.rules == baseline.rules


@pytest.mark.parametrize('component', ['uchcha', 'ojayugma', 'drekkana', 'drig'])
def test_context_rejects_balanced_component_corruption(component):
    result = strength_at()
    ps = result.planets['Sun']
    sb = ps.sthana_bala
    if component == 'drig':
        changed = replace(ps, drig_bala=ps.drig_bala+1, dig_bala=ps.dig_bala-1)
    else:
        # Keep every aggregate unchanged, including the planetary war receipt.
        changed = replace(ps, sthana_bala=replace(sb,
            **{component: getattr(sb, component)+1, 'kendradi': sb.kendradi-1}))
    corrupted = replace(result, planets=result.planets | {'Sun': changed})
    with pytest.raises(ValueError, match='context positional|context Drig'):
        validate_shadbala_output(corrupted)


def period_pair(kind, **child_changes):
    shared = dict(start_jd=100., end_jd=200., full_start_jd=0., full_end_jd=200.,
                  year_days=360., year_basis='savana_360')
    if kind == 'vimshottari':
        child = DashaPeriod(2, 'Sun', **(shared | child_changes))
        return DashaPeriod(1, 'Ketu', sub=[child], **shared), _validate_dasha_sub_containment
    child = AlternateDashaPeriod('yogini', 2, 'Mangala', sub=[], **(shared | child_changes))
    return AlternateDashaPeriod('yogini', 1, 'Bhramari', sub=[child], **shared), _validate_alternate_children


@pytest.mark.parametrize('kind', ['vimshottari', 'yogini'])
def test_dasha_child_full_interval_cannot_escape_parent(kind):
    period, validate = period_pair(kind, full_start_jd=-1e6, full_end_jd=1e6)
    with pytest.raises(ValueError, match='[Ff]ull'):
        validate(period)


def test_alternate_transport_reuses_owner_year_validation():
    period, validate = period_pair('yogini', year_days=365.25, year_basis='julian_365.25')
    with pytest.raises(ValueError):
        validate(period)
    with pytest.raises(ValueError):
        AlternateDashaPeriodRequest.model_validate(asdict(period))


def test_alternate_partial_tree_mode_retains_provenance_checks():
    parent, validate = period_pair('yogini')
    child = replace(parent.sub[0], start_jd=120., end_jd=130.,
                    full_start_jd=120., full_end_jd=130.)
    partial = replace(parent, sub=[child])
    validate(partial, require_complete=False)
    with pytest.raises(ValueError, match='cover'):
        validate(partial)
    AlternateDashaPeriodRequest.model_validate(asdict(partial))
    for change in ({'year_basis': 'julian_365.25', 'year_days':365.25},
                   {'full_start_jd': -1000.}, {'full_end_jd': 140.}):
        invalid = replace(parent, sub=[replace(child, **change)])
        with pytest.raises(ValueError):
            validate(invalid, require_complete=False)
        with pytest.raises(ValueError):
            AlternateDashaPeriodRequest.model_validate(asdict(invalid))


@pytest.mark.parametrize('moon,saturn,expected', [(-1e-300, 0., (11, 0, 'setting')),
                                               (0., -1e-300, (0, 11, 'rising'))])
def test_sade_sati_uses_half_open_normalization(moon, saturn, expected):
    result = sade_sati_status(moon, saturn)
    assert (result.janma_rashi_index, result.saturn_rashi_index, result.phase) == expected


def test_lagna_preserves_missing_bodies_and_rejects_incompatible_positions():
    strength = strength_at()
    partial = {'Sun': math.nextafter(90., 0.), 'Rahu': 20., 'Ketu': 200.}
    result = evaluate_muhurta_lagna_strength(partial, jd_ut1=strength.jd,
        shadbala_result=strength)
    assert {p.planet for p in result.planets} == set(partial)
    assert result.planets[0].sidereal_longitude == 90.
    assert 'missing_position:Moon' in result.unavailable_reasons
    with pytest.raises(ValueError, match='position mismatch'):
        evaluate_muhurta_lagna_strength({'Sun': 90.+1e-8}, jd_ut1=strength.jd,
                                       shadbala_result=strength)


def test_bhava_uses_canonical_context_and_checks_positions():
    strength = strength_at()
    positions = dict(strength.context.sidereal_longitudes)
    houses = SimpleNamespace(asc=0., cusps=tuple(float(i*30) for i in range(12)))
    baseline = bhava_bala(strength, positions, houses)
    assert bhava_bala(strength, positions | {'Sun': math.nextafter(90., 0.)}, houses) == baseline
    with pytest.raises(ValueError, match='position mismatch'):
        bhava_bala(strength, positions | {'Sun': 89.}, houses)


@pytest.mark.parametrize('kind', ['vimshottari', 'yogini'])
def test_dasha_rejects_inexact_clip_even_with_valid_visible_coverage(kind):
    parent, validate = period_pair(kind)
    first = replace(parent.sub[0], end_jd=150., full_end_jd=175.)
    second = replace(parent.sub[0], start_jd=150., full_start_jd=150.)
    parent = replace(parent, sub=[first, second])
    with pytest.raises(ValueError, match='clipped'):
        validate(parent)


@pytest.mark.parametrize('kind', ['vimshottari', 'yogini'])
def test_dasha_legacy_unknown_provenance_stays_unknown(kind):
    parent, validate = period_pair(kind)
    child = replace(parent.sub[0], full_start_jd=None, full_end_jd=None)
    for full_start, full_end in ((None, None), (0., 200.)):
        legacy = replace(parent, full_start_jd=full_start, full_end_jd=full_end, sub=[child])
        validate(legacy)
        assert legacy.sub[0].full_start_jd is None
    # A known child can still be checked against an unknown parent's visible axis.
    validate(replace(parent, full_start_jd=None, full_end_jd=None))


def test_vimshottari_rejects_inconsistent_or_missing_child_year_label():
    parent, validate = period_pair('vimshottari', year_basis=None)
    with pytest.raises(ValueError, match='year basis'):
        validate(parent)
    with pytest.raises(ValueError, match='year_basis'):
        replace(parent, year_basis='julian_365.25')


@pytest.mark.parametrize('bad', [True, None, '0', float('nan'), float('inf'), 10**1000])
def test_sade_sati_rejects_invalid_longitudes(bad):
    with pytest.raises((ValueError, TypeError)):
        sade_sati_status(bad, 0.)
    with pytest.raises((ValueError, TypeError)):
        sade_sati_status(0., bad)


@pytest.mark.parametrize('moon,saturn', [(-0., 0.), (720., -720.),
    (-1e-300, 0.), (math.nextafter(360., 0.), 0.), (0., -1e-300)])
def test_sade_sati_status_and_window_share_sign_partition(monkeypatch, moon, saturn):
    from moira.sade_sati import sade_sati_windows
    from moira.varga import _normalize_longitude
    monkeypatch.setattr('moira.sade_sati._saturn_sidereal_sign',
                        lambda *args: int(_normalize_longitude(saturn)//30))
    status = sade_sati_status(moon, saturn)
    windows = sade_sati_windows(moon, 2451545., 2451546.)
    assert status.janma_rashi_index == windows.janma_rashi_index
    assert windows.windows[0].sign_index == status.saturn_rashi_index
    assert windows.windows[0].phase == status.phase


@pytest.mark.parametrize('basis,utc,lord', [('unknown', None, 'Sun'),
    ('supplied', 2451545., 'Sun'), ('civil_utc_midnight', None, 'Sun'),
    ('civil_utc_midnight', True, 'Sun')])
def test_context_rejects_invalid_weekday_evidence(basis, utc, lord):
    with pytest.raises(ValueError):
        replace(strength_at().context, vara_basis=basis, vara_jd_utc=utc, vara_lord=lord)
