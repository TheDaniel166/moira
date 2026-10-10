"""Paired serving-record marriage benchmark; timings are not accuracy evidence.

Run with the project Python and MOIRA_NO_DOWNLOAD=1. Each pair uses fresh
request-local caches and the same warmed reader, with alternating execution
order. Exact result/certificate/counter agreement is required. The temporary
reference override belongs only to this standalone, single-threaded process.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from moira import _muhurta_marriage_astronomy as astronomy  # noqa: E402
from moira._kernel_paths import find_planetary_kernel  # noqa: E402
from moira._muhurta_marriage_search import (  # noqa: E402
    MarriageSearchLimits,WorkMeter,borrow_marriage_reader)
from moira.muhurta_marriage import MarriageElectionPolicy  # noqa: E402
from moira.muhurta_marriage_dated import _Context  # noqa: E402
from moira.spk_reader import SpkReader,use_reader_override  # noqa: E402


def run_case(serving,body,step):
    """Exercise every certified exclusion and root in the fixed four-day case."""
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(serving,meter) as reader,use_reader_override(reader):
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),
                         'Asia/Kolkata',MarriageElectionPolicy('vows','all_regions'))
        cert=context.certifier
        context.body(body,2461324.)
        cert.angular_signal(((body,1),),2461324.,2461324.001,True)
        start=time.perf_counter()
        roots,gaps=cert.angular(((body,1),),2461324.,2461328.,
                               tuple(i*360/108 for i in range(108)),step,'profile_'+body)
        elapsed=time.perf_counter()-start
        evidence={'roots':[asdict(root) for root in roots],'gaps':gaps,
                  'counts':meter.counts,'records':cert.records}
    del context,cert
    gc.collect()
    return elapsed,json.dumps(evidence,sort_keys=True,separators=(',',':'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repetitions',type=int,choices=(1,2,3),default=2)
    args=parser.parse_args()
    kernel=find_planetary_kernel()
    if kernel is None:
        parser.error('a discovered planetary kernel is required; this benchmark cannot skip')
    native=astronomy._cheb
    rows=[]
    try:
        with SpkReader(kernel) as reader:
            source=asdict(reader._source_identity)
            for body,step in (('Moon',.25),('Rahu',.125),('Venus',1.)):
                for repetition in range(args.repetitions):
                    order=('python','native') if repetition%2==0 else ('native','python')
                    times={}
                    results={}
                    for mode in order:
                        astronomy._cheb=astronomy._cheb_python if mode=='python' else native
                        times[mode],results[mode]=run_case(reader,body,step)
                    if results['python']!=results['native']:
                        raise AssertionError(f'{body}: optimized evidence differs from reference')
                    row={'body':body,'repetition':repetition,'order':order,'seconds':times,
                         'speedup':times['python']/times['native'],
                         'evidence_sha256':hashlib.sha256(results['native'].encode()).hexdigest()}
                    rows.append(row)
                    print(json.dumps(row),flush=True)
    finally:
        astronomy._cheb=native
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'evidence_class':'paired performance and regression equivalence',
        'source':source,'cases':rows},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
