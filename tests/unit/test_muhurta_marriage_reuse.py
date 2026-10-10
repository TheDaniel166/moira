"""Exact reuse boundaries for marriage's clock, frames and serving records."""
from dataclasses import fields, is_dataclass
from math import nextafter, inf
from zoneinfo import ZoneInfo

import pytest

from moira._bounded_memo import binary64_key
from moira._muhurta_marriage_enclosure import Interval as I, PI, EnclosureUnavailable
from moira import _muhurta_marriage_frames as F
from moira import _muhurta_marriage_astronomy as A
from moira._muhurta_marriage_search import WorkMeter, MarriageSearchLimits, MarriageSearchBudgetError, borrow_marriage_reader
from moira.muhurta_marriage import MarriageElectionPolicy
from moira.muhurta_marriage_dated import _Context
from moira.spk_reader import use_reader_override


def bits(value):
    """Retain exact floating bits recursively, including signed zero."""
    if type(value) is float:
        return binary64_key(value)
    if isinstance(value,tuple):
        return tuple(bits(v) for v in value)
    if is_dataclass(value):
        return tuple(bits(getattr(value,f.name)) for f in fields(value))
    return value


def _original_angles(owner,tt,coarse):
    """Pre-reuse arithmetic schedule; no polynomial sharing or memoization."""
    t=(tt-2451545.)/F._CY
    fw=tuple(F._jet_polynomial(p,t)*F._AS for p in F._FW)
    psi,eps=owner.nutation(tt,coarse=coarse)
    true_eps=fw[3]+eps
    ayanamsa=F._jet_polynomial(F._PA,t)*F._AS+psi+I.point(F._AYANAMSA_AT_J2000['Lahiri'])*PI/180
    return fw,psi,eps,true_eps,ayanamsa


@pytest.mark.parametrize('jd',(2415020.5,2451545.,2461324.,2488434.49))
def test_shared_frame_polynomials_match_original_bit_schedule(jd):
    owner=F.FrameEnclosures(WorkMeter(MarriageSearchLimits()))
    for centered in (False,True):
        for width in (0.,1e-5,.001):
            tt=F.Differential(I(jd,jd+width),I.point(1.))
            tt=F.Differential(tt.value,tt.rate,I.point(jd+width/2),width/2,centered)
            for coarse in (True,False):
                expected=bits(_original_angles(owner,tt,coarse))
                assert bits(owner.angles(tt,coarse=coarse))==expected
                assert bits(owner.angles(tt,coarse=coarse))==expected
    assert owner.angles.cache_info().hits>=12
    assert owner._polynomials.cache_info().hits==6


def test_differential_keys_preserve_every_state_field():
    base=[0.,0.,0.,0.,0.,0.,0.]
    def make(values,centered=False):
        return F.Differential(I(*values[:2]),I(*values[2:4]),I(*values[4:6]),values[6],centered)
    reference=F._differential_key(make(base))
    for index in range(7):
        changed=base.copy()
        changed[index]=-0.
        assert F._differential_key(make(changed))!=reference
    assert F._differential_key(make(base,True))!=reference
    point=F.Differential.point(2461324.)
    neighbor=F.Differential.point(nextafter(2461324.,inf))
    assert F._differential_key(point)!=F._differential_key(neighbor)


def test_separate_frame_owners_cannot_share_source_dependent_results():
    a=F.FrameEnclosures(WorkMeter(MarriageSearchLimits()))
    b=F.FrameEnclosures(WorkMeter(MarriageSearchLimits()))
    b.coarse=tuple((v*2,r*2) for v,r in b.coarse)
    tt=F.Differential.point(2461324.)
    assert bits(a.angles(tt,coarse=True))!=bits(b.angles(tt,coarse=True))
    assert a.angles.cache_info().misses==b.angles.cache_info().misses==1
    with pytest.raises(EnclosureUnavailable,match='outside_1900_2100'):
        a.angles(F.Differential.point(2488434.5))


def test_astronomy_memos_do_not_retain_finished_request_or_reader():
    import gc
    import weakref
    class Reader:
        pass
    class Context:
        pass
    context=Context()
    context.reader=Reader()
    context.meter=WorkMeter(MarriageSearchLimits())
    astro=A.AstronomyEnclosures(context)
    tt=F.Differential.point(2461324.)
    astro._tdb(tt)
    astro.frames.angles(tt)
    references=weakref.ref(context),weakref.ref(context.reader),weakref.ref(astro)
    del context,astro
    gc.collect()
    assert all(reference() is None for reference in references)


@pytest.mark.requires_ephemeris
def test_record_argument_reuse_does_not_bypass_reader_budget(moira_engine):
    meter=WorkMeter(MarriageSearchLimits(max_reader_calls=1))
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        context=_Context(reader,meter,0.,0.,ZoneInfo('UTC'),'UTC',MarriageElectionPolicy('vows','all_regions'))
        astro=context.certifier.astro
        tdb=F.Differential.point(2461324.)
        # Bypass only the pre-existing pair cache to exercise the new inner
        # memo boundary; every admitted pair calculation still pays its meter.
        astro.pair.__wrapped__(3,301,tdb)
        assert astro._record_arguments.cache_info().currsize>0
        with pytest.raises(MarriageSearchBudgetError) as failure:
            astro.pair.__wrapped__(3,301,tdb)
        assert failure.value.limit_kind=='reader_calls' and failure.value.count==2


@pytest.mark.requires_ephemeris
def test_reused_astronomy_keeps_exact_outputs_sources_and_work_accounting(moira_engine,monkeypatch):
    def run(enabled):
        meter=WorkMeter(MarriageSearchLimits())
        with monkeypatch.context() as patch:
            if not enabled:
                patch.setattr(A,'bounded_memo',lambda function,**kwargs:function)
                patch.setattr(F,'bounded_memo',lambda function,**kwargs:function)
            with borrow_marriage_reader(moira_engine._reader,meter) as reader,use_reader_override(reader):
                context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),
                                 'Asia/Kolkata',MarriageElectionPolicy('vows','all_regions'))
                cert=context.certifier
                values=[]
                for a in (2451545.,2461324.,nextafter(2461324.,inf)):
                    for coarse in (True,False):
                        for planet in ('Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Rahu','Ketu'):
                            values.append(cert.angular_signal(((planet,1),),a,a+.0001,coarse))
                        values.append(cert.angular_signal((('Moon',1),('Sun',-1)),a,a+.0001,coarse))
                if enabled:
                    assert cert.astro._tdb.cache_info().hits>0
                    assert cert.astro._record_arguments.cache_info().hits>0
                    assert cert.astro.frames.angles.cache_info().hits>0
                    assert cert.astro.frames._polynomials.cache_info().hits>0
                    assert cert.astro.frames.sincos.cache_info().hits>0
                return bits(tuple(values)),meter.counts,cert.astro.records.sources
    assert run(True)==run(False)
