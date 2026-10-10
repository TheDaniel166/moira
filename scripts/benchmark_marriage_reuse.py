"""Paired exact-reuse benchmark; timings never establish astronomical accuracy.

Run with the project Python and MOIRA_NO_DOWNLOAD=1. Fresh request scopes use
the same warmed reader and alternate execution order. The reference disables
only the newly admitted pure-computation memos inside this single-threaded
process. Numerical evidence, sources and work counters must agree exactly.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from moira import _muhurta_marriage_astronomy as A, _muhurta_marriage_frames as F  # noqa: E402
from moira._kernel_paths import find_planetary_kernel  # noqa: E402
from moira._muhurta_marriage_search import MarriageSearchLimits,WorkMeter,borrow_marriage_reader  # noqa: E402
from moira.muhurta_marriage import MarriageElectionPolicy  # noqa: E402
from moira.muhurta_marriage_dated import _Context  # noqa: E402
from moira.spk_reader import SpkReader,use_reader_override  # noqa: E402


@contextmanager
def reuse_mode(enabled):
    """Standalone validation override, never a serving request selector."""
    original=A.bounded_memo,F.bounded_memo
    if not enabled:
        A.bounded_memo=F.bounded_memo=lambda function,**kwargs:function
    try:
        yield
    finally:
        A.bounded_memo,F.bounded_memo=original


def run_case(serving,case):
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(serving,meter) as reader,use_reader_override(reader):
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),
                         'Asia/Kolkata',MarriageElectionPolicy('vows','all_regions'))
        cert=context.certifier
        context.body('Moon',2461324.)
        cert.angular_signal((('Moon',1),),2461324.,2461324.001,True)
        start=time.perf_counter()
        if case=='shared_sky':
            values=[]
            for jd in (base+index/32 for base in (2451545.,2461324.) for index in range(16)):
                for coarse in (True,False):
                    for body in ('Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Rahu','Ketu'):
                        values.append(asdict(cert.angular_signal(((body,1),),jd,jd+.0001,coarse)))
                    for terms in ((('Moon',1),('Sun',-1)),(('Moon',1),('Sun',1))):
                        values.append(asdict(cert.angular_signal(terms,jd,jd+.0001,coarse)))
            payload={'signals':values}
        else:
            step={'Moon':.25,'Rahu':.125,'Venus':1.}[case]
            roots,gaps=cert.angular(((case,1),),2461324.,2461328.,
                tuple(i*360/108 for i in range(108)),step,'profile_'+case)
            payload={'roots':[asdict(r) for r in roots],'gaps':gaps}
        elapsed=time.perf_counter()-start
        payload.update(counts=meter.counts,records=cert.records,sources=sorted(cert.astro.records.sources))
        caches={name:fn.cache_info()._asdict() for name,fn in (
            ('tdb',cert.astro._tdb),('record_arguments',cert.astro._record_arguments),
            ('frame_polynomials',cert.astro.frames._polynomials),('frame_angles',cert.astro.frames.angles),
            ('frame_sincos',cert.astro.frames.sincos))
            if hasattr(fn,'cache_info')}
        evidence=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)
    del context,cert
    gc.collect()
    return elapsed,evidence,caches


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repetitions',type=int,choices=(1,2,3),default=2)
    args=parser.parse_args()
    kernel=find_planetary_kernel()
    if kernel is None:
        parser.error('a discovered planetary kernel is required; no skipped benchmark')
    rows=[]
    with SpkReader(kernel) as reader:
        source=asdict(reader._source_identity)
        for case in ('Moon','Rahu','Venus','shared_sky'):
            for repetition in range(args.repetitions):
                order=('reference','reuse') if repetition%2==0 else ('reuse','reference')
                measured={}
                for mode in order:
                    with reuse_mode(mode=='reuse'):
                        measured[mode]=run_case(reader,case)
                if measured['reference'][1]!=measured['reuse'][1]:
                    raise AssertionError(case+': exact evidence/source/counter mismatch')
                row={'case':case,'repetition':repetition,'order':order,
                     'seconds':{mode:measured[mode][0] for mode in order},
                     'speedup':measured['reference'][0]/measured['reuse'][0],
                     'evidence_sha256':hashlib.sha256(measured['reuse'][1].encode()).hexdigest(),
                     'reuse':measured['reuse'][2]}
                rows.append(row)
                print(json.dumps(row),flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'evidence_class':'paired timing and exact regression equivalence',
        'source':source,'cases':rows},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
