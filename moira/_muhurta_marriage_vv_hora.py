"""VV8.8-11's two distinct horas and explicitly selected classical Shadvarga.

The astronomical adapter uses exact apparent Lagna/Sun and local sunrise.
The edition's criticized Lanka day-start approximation is not resurrected.
"""
from fractions import Fraction
from math import ceil

from ._muhurta_marriage_tradition_sources import VV
from ._muhurta_marriage_traditions import row
from ._muhurta_marriage_rules import measure,_and,_or,_nnot
from .muhurta_lagna import _LORDS
from .varga import varga_sign_index
from .panchanga_shuddhi import ShuddhiInterval,_sector
from .muhurta_dosha import _shift

SEQUENCE=('Sun','Venus','Mercury','Moon','Saturn','Jupiter','Mars')
WEEK=('Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn')


def varga_lords(longitude):
    """D1/D2/D3/D9 and self-counted D12, unequal planetary D30 (BJ1.7)."""
    sign=_sector(longitude,12)
    degree=Fraction.from_float(float(longitude))-sign*30
    lords=[_LORDS[varga_sign_index(longitude,n)] for n in (1,2,3,9)]
    lords.append(_LORDS[(sign+int(degree*2/5))%12])
    table=((5,'Mars'),(10,'Saturn'),(18,'Jupiter'),(25,'Mercury'),(30,'Venus')) if sign%2==0 else (
        (5,'Venus'),(12,'Mercury'),(20,'Jupiter'),(25,'Saturn'),(30,'Mars'))
    lords.append(next(body for end,body in table if degree<end))
    return tuple(lords)


def findings(e,p,nature):
    lords=None if e.lagna_sidereal_longitude is None else varga_lords(e.lagna_sidereal_longitude)
    values=() if lords is None else tuple(nature[body] for body in lords)
    good=None if not values or None in values else sum(values)>3
    bad=None if not values or None in values else sum(not x for x in values)>3
    solar=e.solar
    angle=None if e.lagna_sidereal_longitude is None or 'Sun' not in p else (e.lagna_sidereal_longitude-p['Sun'])%360
    angular=None if angle is None or solar is None else SEQUENCE[(SEQUENCE.index(WEEK[solar.weekday])+_sector(angle,24))%7]
    # Preserve the sunrise uncertainty in every one-hour clock boundary.
    clock_hits=[]
    measures=[]
    if solar is not None:
        for i in range(ceil((solar.day.end.upper_jd_ut1-solar.day.start.lower_jd_ut1)*24)+1):
            window=ShuddhiInterval(_shift(solar.day.start,i/24,'VV_clock_hora_start'),_shift(solar.day.start,(i+1)/24,'VV_clock_hora_end'))
            state=window.contains(e.jd_ut1)
            if state is not False:
                lord=SEQUENCE[(SEQUENCE.index(WEEK[solar.weekday])+i)%7]
                clock_hits.append(_and((state,_nnot(nature[lord]))))
                from ._muhurta_marriage_tradition_time import _witness
                measures.extend(_witness(window,'hora'+str(i)))
    clock_bad=_or(clock_hits) if solar is not None else None
    angular_bad=None if angular is None else _nnot(nature[angular])
    weekday_good=None if solar is None else nature[WEEK[solar.weekday]]
    night=None if solar is None else ShuddhiInterval(solar.sunset,solar.day.end).contains(e.jd_ut1)
    relief=_or((good,weekday_good,night))
    detected=_and((_or((angular_bad,clock_bad)),_nnot(relief)))
    yield row(VV,'hora',detected,'VV8.8-11/PDF74-76; BJ1.7/9 Shadvarga adapter; local sunrise replaces criticized Lanka approximation',
        values=(*measures,measure('varga_lords',None if lords is None else ','.join(lords),'D1,D2,D3,D9,D12,D30'),
            measure('angular_hora_lord',angular,'planet'),measure('majority_benefic',good),
            measure('majority_malefic',bad),measure('source_8_9_relief',relief),
            measure('both_malefic_and_majority_malefic',_and((angular_bad,clock_bad,bad)))))
