"""Bounded VED-017 real-event corpus and explicit primary-oracle validation.

Run in the project venv. --external opts into live NASA/JPL requests. Write a
new output directory; never replace an accepted oracle baseline. Point scans
only choose cases: they do not certify the interval search's completeness.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from tools import horizons  # noqa: E402 -- isolated development comparator
from moira._kernel_paths import find_planetary_kernel  # noqa: E402
from moira.spk_reader import SpkReader,use_reader_override  # noqa: E402
from moira._ephemeris_time import _bind_ephemeris_time  # noqa: E402
from moira.gochara import GOCHARA_PLANETS  # noqa: E402
from moira.gochara_dated import GocharaDatePolicy  # noqa: E402
from moira.gochara_windows import gochara_windows  # noqa: E402
from moira.planets import planet_at  # noqa: E402
from moira.sidereal import Ayanamsa,_STAR_ANCHORED,_ayanamsa_at_tt  # noqa: E402
from moira.stars import star_at  # noqa: E402
from moira.coordinates import icrf_to_equatorial  # noqa: E402


def offset(system,tt):
    if system in _STAR_ANCHORED:
        anchor,target=_STAR_ANCHORED[system]
        return (star_at(anchor,tt).longitude-target)%360
    return _ayanamsa_at_tt(tt,system,'true')


def candidates(reader,spec):
    """First detected crossing per combination, with bracket selection receipts."""
    start=spec['event_corpus']['candidate_search_start_jd_ut1']
    rows=[]
    for system in Ayanamsa.ALL:
        missing=set(GOCHARA_PLANETS)
        previous={}
        for day in range(spec['event_corpus']['candidate_search_days']+1):
            t=start+day
            tt=_bind_ephemeris_time(t,reader).epoch_tt
            ay=offset(system,tt)
            for p in GOCHARA_PLANETS:
                if p not in missing:
                    continue
                lon=(planet_at(p,t,reader=reader,jd_tt=tt).longitude-ay)%360
                if p in previous and int(previous[p]//30)!=int(lon//30):
                    rows.append(dict(system=system,planet=p,start_jd_ut1=t-1,end_jd_ut1=t,
                                     before_sign=int(previous[p]//30),after_sign=int(lon//30)))
                    missing.remove(p)
                previous[p]=lon
            if not missing:
                break
        if missing:
            raise RuntimeError(f'candidate corpus missing {system}: {sorted(missing)}')
        print('selected',system,flush=True)
    return rows


def angular(ra,dec,ref):
    # atan2 vector separation stays meaningful below acos's binary64 floor.
    def vector(a,d):
        a,d=math.radians(a),math.radians(d)
        return math.cos(d)*math.cos(a),math.cos(d)*math.sin(a),math.sin(d)
    u,v=vector(ra,dec),vector(ref.right_ascension,ref.declination)
    cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    return math.degrees(math.atan2(math.sqrt(sum(x*x for x in cross)),sum(a*b for a,b in zip(u,v))))*3600


def retro_candidates(reader):
    """Select real +,-,+ visits to the same ray for all five retrograde bodies."""
    missing=set(('Mercury','Venus','Mars','Jupiter','Saturn'))
    previous,history={},{}
    rows=[]
    for day in range(5001):
        t=2458849.5+day  # 2020-01-01 onward; discovery only, not completeness.
        tt=_bind_ephemeris_time(t,reader).epoch_tt
        ay=offset('Lahiri',tt)
        for p in GOCHARA_PLANETS:
            if p not in missing:
                continue
            lon=(planet_at(p,t,reader=reader,jd_tt=tt).longitude-ay)%360
            old=previous.get(p,lon)
            if int(old//30)!=int(lon//30):
                direction=1 if (lon-old+180)%360-180>0 else -1
                ray=(int((lon if direction==1 else old)//30)*30)%360
                row=dict(system='Lahiri',planet=p,start_jd_ut1=t-1,end_jd_ut1=t,
                         before_sign=int(old//30),after_sign=int(lon//30),
                         expected_direction=direction,boundary_degrees=ray)
                visits=history.setdefault((p,ray),[])
                visits.append(row)
                if len(visits)>=3 and [v['expected_direction'] for v in visits[-3:]]==[1,-1,1]:
                    rows.extend(visits[-3:])
                    missing.remove(p)
                    print('selected retrograde sequence',p,flush=True)
            previous[p]=lon
        if not missing:
            return rows
    raise RuntimeError(f'missing retrograde sequence: {sorted(missing)}')


def wrap_candidates(reader):
    """Select Sun and Moon 360-to-0 crossings; scan is fixture discovery only."""
    missing={'Sun','Moon'}
    previous,rows={},[]
    for day in range(367):
        t=2460310.5+day
        tt=_bind_ephemeris_time(t,reader).epoch_tt
        ay=offset('Lahiri',tt)
        for planet in tuple(missing):
            lon=(planet_at(planet,t,reader=reader,jd_tt=tt).longitude-ay)%360
            if previous.get(planet,0.)>=330 and lon<30:
                rows.append(dict(system='Lahiri',planet=planet,start_jd_ut1=t-1,end_jd_ut1=t,
                    before_sign=11,after_sign=0,expected_direction=1,boundary_degrees=0.))
                missing.remove(planet)
            previous[planet]=lon
        if not missing:
            return rows
    raise RuntimeError(f'missing zero-ray sequence: {sorted(missing)}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--external',action='store_true')
    parser.add_argument('--candidates',type=Path)
    parser.add_argument('--reuse-references',type=Path)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--retro-only',action='store_true')
    mode.add_argument('--wrap-only',action='store_true')
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Use a new output directory; existing evidence is not overwritten.')
    args.output.mkdir(parents=True)
    spec_path=ROOT/'tests/fixtures/gochara_windows_validation_spec.json'
    spec=json.loads(spec_path.read_text())
    receipt={'spec_sha256':sha256(spec_path.read_bytes()).hexdigest(),'external_requested':args.external,
             'results':[],'status':'running'}
    path=args.output/'receipt.json'
    path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    raw_request=horizons._request_text
    references={}
    if args.reuse_references:
        for item in json.loads((args.reuse_references/'requests.json').read_text()):
            raw=(args.reuse_references/item['file']).read_text(encoding='utf-8')
            assert sha256(raw.encode()).hexdigest()==item['sha256']
            references[json.dumps(item['params'],sort_keys=True)]=raw
    requests=[]
    def capture(params):
        key=json.dumps(params,sort_keys=True)
        raw=references[key] if key in references else raw_request(params)
        name=f'horizons-{len(requests):03}.json'
        (args.output/name).write_text(raw,encoding='utf-8')
        requests.append({'params':params,'file':name,'sha256':sha256(raw.encode()).hexdigest()})
        (args.output/'requests.json').write_text(json.dumps(requests,indent=2),encoding='utf-8')
        return raw
    horizons._request_text=capture
    try:
        with SpkReader(find_planetary_kernel()) as reader,use_reader_override(reader):
            selected=json.loads(args.candidates.read_text()) if args.candidates else (
                wrap_candidates(reader) if args.wrap_only else
                retro_candidates(reader) if args.retro_only else candidates(reader,spec))
            if args.wrap_only:
                assert len(selected)==2 and {x['planet'] for x in selected}=={'Sun','Moon'}
            elif args.retro_only:
                assert len(selected)==15 and len({x['planet'] for x in selected})==5
            else:
                assert len(selected)==84 and len({(x['system'],x['planet']) for x in selected})==84
            (args.output/'candidates.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
            for n,row in enumerate(selected):
                started=perf_counter()
                policy=GocharaDatePolicy(ayanamsa_system=row['system'])
                result=gochara_windows(2451545.,row['start_jd_ut1'],row['end_jd_ut1'],reader=reader,policy=policy)
                events=[e for e in result.events if e.planet==row['planet']]
                assert events and all(e.kind=='crossing' for e in events),(row,events)
                event=events[0]
                if 'expected_direction' in row:
                    assert event.direction==row['expected_direction'] and event.boundary_degrees==row['boundary_degrees']
                item=dict(row,event=asdict(event),elapsed_seconds=perf_counter()-started,
                          resources=result.resources,coverage=asdict(result.coverage))
                if args.external:
                    t=(event.lower_jd_ut1+event.upper_jd_ut1)/2
                    tt=_bind_ephemeris_time(t,reader).epoch_tt
                    p=planet_at(row['planet'],t,reader=reader,jd_tt=tt,frame='cartesian')
                    ra,dec,distance=icrf_to_equatorial((p.x,p.y,p.z))
                    command=spec['horizons']['targets'][row['planet']]
                    ref=horizons.observer_apparent_position_tt(command,tt)
                    arcsec=angular(ra,dec,ref)
                    km=abs(distance-ref.distance_au*149597870.7)
                    item['horizons']={'jd_tt':tt,'target':command,'angular_error_arcsec':arcsec,
                                      'distance_error_km':km,'reference':asdict(ref)}
                    assert arcsec<=spec['horizons']['angular_threshold_arcsec'],item
                    assert km<=spec['horizons']['distance_threshold_km'],item
                receipt['results'].append(item)
                path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
                print(n+1,'/'+str(len(selected)),row['planet'],row['system'],flush=True)
        receipt['status']='passed' if args.external else 'local_corpus_passed_external_not_run'
    except Exception as exc:
        receipt['status']='failed'
        receipt['failure']=repr(exc)
        raise
    finally:
        path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
