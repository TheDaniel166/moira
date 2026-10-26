"""Reader-bound composition, source independence and resource/error boundaries."""
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import pytest
from moira.kalachakra import (
    KalachakraSeed, KalachakraEpoch, KalachakraProjection, KalachakraInputError,
    KalachakraResourceError, KalachakraCoverageError, KalachakraInvariantError, kalachakra_sequence,
    kalachakra_for_datetime,
)
from moira.kalachakra_policy import PROFILE_ID
from moira.sidereal import Ayanamsa
from moira.spk_reader import MissingKernelError, OutOfRangeError
import moira._kalachakra_astronomy as astronomy

DT = datetime(2000,1,1,12,tzinfo=timezone.utc)


@pytest.fixture
def fake_astronomy(monkeypatch):
    counts = {'binding':0,'moon':0,'ayanamsa':0,'star':0}
    def bind(jd,reader):
        counts['binding'] += 1
        return SimpleNamespace(epoch_tt=jd+64/86400,epoch_tdb=jd+64/86400,
            delta_t_seconds=64.0,delta_t_correction_seconds=0.0,tdb_minus_tt_seconds=0.0,
            raw_delta_t=SimpleNamespace(source_product='fixture_clock'),
            identity=SimpleNamespace(planetary_ephemeris='DE441',lunar_ephemeris='LE441',
                lunar_tidal_acceleration_arcsec_per_cy2=-25.8,summary_label='fixture_DE441_LE441'))
    def moon(*args,**kwargs):
        counts['moon'] += 1
        assert args[0] == 'Moon' and kwargs['jd_tt'] is not None
        assert kwargs['center']=='geocentric' and kwargs['frame']=='ecliptic'
        assert all(kwargs[k] for k in ('apparent','aberration','grav_deflection','nutation'))
        return SimpleNamespace(longitude=57.5)
    def ayan(*args):
        counts['ayanamsa'] += 1
        assert args[2]=='true'
        return 23.8
    def star(*args):
        counts['star'] += 1
        return SimpleNamespace(longitude=203.8)
    monkeypatch.setattr(astronomy,'_bind_ephemeris_time',bind)
    monkeypatch.setattr(astronomy,'planet_at',moon)
    monkeypatch.setattr(astronomy,'_ayanamsa_at_tt',ayan)
    monkeypatch.setattr(astronomy,'star_at',star)
    return counts


def test_one_derivation_and_tropical_parity(fake_astronomy):
    projection = KalachakraProjection('savana_360')
    r = kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system='Lahiri',projection=projection,reader=object())
    assert fake_astronomy == {'binding':1,'moon':1,'ayanamsa':1,'star':0}
    direct = kalachakra_sequence(KalachakraSeed('tropical',57.5,'Lahiri'),profile_id=PROFILE_ID,
        birth_epoch=KalachakraEpoch('datetime',DT),projection=projection,reader=object())
    assert r.periods == direct.periods
    assert fake_astronomy == {'binding':2,'moon':1,'ayanamsa':2,'star':0}
    assert direct.provenance.input_origin == 'supplied_tropical'
    assert r.provenance.input_origin == 'derived_moon'
    assert r.provenance.birth_jd_utc != r.provenance.astronomy.jd_ut1


@pytest.mark.parametrize('system',Ayanamsa.ALL)
def test_every_named_ayanamsa_admitted_and_anchor_receipt(system,fake_astronomy):
    r = kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system=system,reader=object())
    assert fake_astronomy['moon']==1 and fake_astronomy['binding']==1
    if system in astronomy._STAR_ANCHORED:
        assert fake_astronomy['star']==1 and fake_astronomy['ayanamsa']==0
        assert r.provenance.astronomy.anchor == astronomy._STAR_ANCHORED[system][0]
    else:
        assert fake_astronomy['ayanamsa']==1 and r.provenance.astronomy.anchor is None


@pytest.mark.parametrize('exc,expected',[(MissingKernelError('private path'),KalachakraResourceError),
    (OutOfRangeError('outside',[]),KalachakraCoverageError)])
def test_typed_resource_translation(monkeypatch,exc,expected):
    def failure(*args):
        raise exc
    monkeypatch.setattr(astronomy,'_bind_ephemeris_time',failure)
    with pytest.raises(expected):
        kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system='Lahiri',reader=object())


@pytest.mark.parametrize('error',[KeyError,FileNotFoundError,ValueError])
def test_live_anchor_never_falls_back(fake_astronomy,monkeypatch,error):
    def missing(*args):
        raise error('private catalogue path')
    monkeypatch.setattr(astronomy,'star_at',missing)
    with pytest.raises(KalachakraResourceError):
        kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system=next(iter(astronomy._STAR_ANCHORED)),reader=object())
    assert fake_astronomy['ayanamsa']==0 and fake_astronomy['moon']==0


@pytest.mark.parametrize('stage,error',[
    (stage,error)
    for stage in ('_bind_ephemeris_time','_ayanamsa_at_tt','planet_at','star_at')
    for error in (KeyError,IndexError)
    if (stage,error) != ('star_at',KeyError)
])
def test_internal_lookup_failure_is_not_resource_unavailable(fake_astronomy,monkeypatch,stage,error):
    def corrupt(*args,**kwargs):
        raise error('private generated astronomical field')
    monkeypatch.setattr(astronomy,stage,corrupt)
    system = next(iter(astronomy._STAR_ANCHORED)) if stage == 'star_at' else 'Lahiri'
    with pytest.raises(KalachakraInvariantError):
        kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system=system,reader=object())


def test_missing_time_identity(fake_astronomy,monkeypatch):
    original = astronomy._bind_ephemeris_time
    def incomplete(*args):
        result = original(*args)
        result.identity.lunar_tidal_acceleration_arcsec_per_cy2=None
        return result
    monkeypatch.setattr(astronomy,'_bind_ephemeris_time',incomplete)
    with pytest.raises(KalachakraResourceError):
        kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system='Lahiri',reader=object())
    assert fake_astronomy['moon']==0


def test_bad_request_precedes_astronomy(fake_astronomy):
    for kwargs in ({'levels':3},{'profile_id':'candidate'},{'ayanamsa_system':'unknown'}):
        args = dict(profile_id=PROFILE_ID,ayanamsa_system='Lahiri',reader=object())
        args.update(kwargs)
        with pytest.raises(KalachakraInputError):
            kalachakra_for_datetime(DT,**args)
    assert sum(fake_astronomy.values())==0


@pytest.mark.requires_ephemeris
def test_real_kernel_date_direct_timezone_and_facade_parity(moira_engine):
    engine = moira_engine
    projection = KalachakraProjection('julian_365.25')
    r = engine.kalachakra_for_datetime(DT,profile_id=PROFILE_ID,ayanamsa_system='Lahiri',projection=projection)
    shifted = engine.kalachakra_for_datetime(DT.astimezone(timezone(timedelta(hours=-4))),
        profile_id=PROFILE_ID,ayanamsa_system='Lahiri',projection=projection)
    assert shifted == r
    sidereal = kalachakra_sequence(KalachakraSeed('sidereal',r.provenance.moon_sidereal_lon),
        profile_id=PROFILE_ID,birth_epoch=KalachakraEpoch('jd_utc',r.provenance.birth_jd_utc),projection=projection)
    tropical = engine.kalachakra_sequence(KalachakraSeed('tropical',r.provenance.moon_tropical_lon,'Lahiri'),
        profile_id=PROFILE_ID,birth_epoch=KalachakraEpoch('datetime',DT),projection=projection)
    assert sidereal.periods == tropical.periods == r.periods
    assert r.provenance.astronomy.planetary_ephemeris == 'DE441'
    assert r.provenance.astronomy.lunar_ephemeris == 'LE441'
