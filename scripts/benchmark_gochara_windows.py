"""Measure complete bounded Gochar requests; performance is not accuracy proof."""
import argparse
import ctypes
from dataclasses import asdict
import gc
import json
import os
from pathlib import Path
import platform
from time import perf_counter

from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import SpkReader
from moira.gochara_dated import GocharaDatePolicy,GocharaNatalBavMode,GocharaBirthLocation
from moira.gochara_windows import gochara_windows,window_json_bytes


def memory():
    if os.name!='nt':
        return {'measurement':'unavailable_on_this_platform'}
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),
                  *[(n,ctypes.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize',
                    'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]]
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    values=Counters()
    values.cb=ctypes.sizeof(values)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(values),values.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'working_set_bytes':values.WorkingSetSize,'process_peak_working_set_bytes':values.PeakWorkingSetSize,
            'measurement':'Windows process resident working set; peak cumulative across this process, includes shared kernel pages'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system',required=True)
    p.add_argument('--bav',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--concurrent-processes',type=int,default=1)
    p.add_argument('--start-jd',type=float,default=2460676.5)
    p.add_argument('--days',type=int,nargs='+',default=(1,30,366))
    args=p.parse_args()
    if args.output.exists():
        raise SystemExit('Use a new benchmark receipt path.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    receipt={'python':platform.python_version(),'system':args.system,'bav':args.bav,
        'concurrent_processes':args.concurrent_processes,'mode':'synchronous engine requests',
        'warm_semantics':'same serving reader and process, new request-owned caches',
        'start_jd_ut1':args.start_jd,'status':'running','results':[]}
    args.output.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    try:
        policy=GocharaDatePolicy(ayanamsa_system=args.system,
            natal_bav_mode=GocharaNatalBavMode.COMPUTE_RAW if args.bav else GocharaNatalBavMode.OMIT)
        location=GocharaBirthLocation(28.6,77.2) if args.bav else None
        with SpkReader(find_planetary_kernel()) as reader:
            for days in args.days:
                for repeat in (0,1):
                    before=memory()
                    started=perf_counter()
                    result=gochara_windows(2451545.,args.start_jd,args.start_jd+days,
                        reader=reader,policy=policy,birth_location=location)
                    elapsed=perf_counter()-started
                    row={'days':days,'repeat':repeat,'wall_seconds':elapsed,'before':before,'after':memory(),
                         'work':dict(result.work),'coverage':asdict(result.coverage),
                         'events':len(result.events),'cells':len(result.regions),
                         'serialized_bytes':len(window_json_bytes(result)),
                         'cache_receipts':[p for p in result.resources if p[0].startswith('cache:')]}
                    receipt['results'].append(row)
                    args.output.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
                    print(args.system,args.bav,days,repeat,round(elapsed,3),row['serialized_bytes'],flush=True)
                    del result
                    gc.collect()
        receipt['status']='passed'
    except Exception as exc:
        receipt['status']='failed'
        receipt['failure']=repr(exc)
        raise
    finally:
        args.output.write_text(json.dumps(receipt,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
