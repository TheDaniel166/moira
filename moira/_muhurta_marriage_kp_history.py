"""KP XIV previous/current/next occupied stars without MC lunar-reset doctrine."""
from ._muhurta_marriage_traditions import row
from ._muhurta_marriage_tradition_sources import KP
from ._muhurta_marriage_rules import measure,_eq,_and,_or,_nnot
from ._muhurta_marriage_context import _history_bands,_band_possibilities,_possibly_malefic
from .muhurta_lagna import _nature
from .panchanga_shuddhi import _sector


def _mercury(history,passage):
    start,end=passage.entry.lower_jd_ut1,passage.exit.upper_jd_ut1
    spans=history.vedha_spans
    complete=bool(spans and spans[0].interval.start.upper_jd_ut1<=start and spans[-1].interval.end.lower_jd_ut1>=end)
    hits=[]
    for span in spans:
        if span.interval.end.upper_jd_ut1<=start or span.interval.start.lower_jd_ut1>=end:
            continue
        sky={p.planet:p.sidereal_longitude for p in span.planets}
        match=None if 'Mercury' not in sky else _sector(sky['Mercury'],27)==passage.star_index
        certain=max(start,span.interval.start.upper_jd_ut1)<min(end,span.interval.end.lower_jd_ut1)
        hits.append(_and((match,_nnot(_nature(sky)['Mercury']),True if certain else None)))
    for edge,band in _history_bands(history):
        if edge.upper_jd_ut1<=start or edge.lower_jd_ut1>=end:
            continue
        samples,signs,moon_bad=_band_possibilities(band)
        if ('Mercury' not in samples or any(_sector(x,27)==passage.star_index for x in samples['Mercury'])) and _possibly_malefic('Mercury',signs,moon_bad):
            hits.append(None)
    return _or((*hits,False if complete else None))


def findings(e,p):
    history,jd=e.star_history,e.jd_ut1
    target=None if 'Moon' not in p else _sector(p['Moon'],27)
    for planet in ('Sun','Mars','Mercury','Saturn','Rahu','Ketu'):
        passages=[] if history is None else [x for x in history.passages if x.planet==planet]
        before=[x for x in passages if x.exit.upper_jd_ut1<=jd]
        current=[x for x in passages if x.entry.lower_jd_ut1<=jd<=x.exit.upper_jd_ut1]
        after=[x for x in passages if x.entry.lower_jd_ut1>jd]
        selected=before[-1:]+current+after[:1]
        complete=bool(before and current and after and all(a.exit==b.entry for a,b in zip(selected,selected[1:])))
        hits=[]
        values=[]
        for i,passage in enumerate(selected):
            match=_eq(target,passage.star_index)
            nature=_mercury(history,passage) if planet=='Mercury' and match is not False else True
            hits.append(_and((match,nature)))
            values.extend((measure(f'passage_{i}_star',passage.star_index,'zero_based27'),measure(f'passage_{i}_malefic',nature)))
        yield row(KP,'star_history',_or((*hits,False if complete else None)),
            'KP XIV/PDF123-124: named nearest previous/current/next passage adapter; event-time nature; no MC clearance',
            suffix=planet.lower(),values=values)
