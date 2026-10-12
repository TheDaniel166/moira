"""All named Gochar frames over the same serving apparent-place model.

No sampled speed or frozen ayanamsa supplies an exclusion certificate. Live
anchors use the sovereign point owner's exact propagation and transformation.
"""
from functools import lru_cache
from hashlib import sha256
from math import atan2, degrees, isfinite

from ._event_search.astronomy import AstronomyEnclosures, longitude_differential, unit, hull
from ._event_search.frames import FrameEnclosures, Differential as D, true_equator, rotate_x
from ._event_search.intervals import Interval as I, PI
from ._event_search.clocks import MarriageClockEnclosures
from ._ephemeris_time import _bind_ephemeris_time
from ._bounded_memo import bounded_memo
from ._event_search.frames import _differential_key
from .gochara_dated import GocharaResourceError
from .gochara_windows import GocharaWindowDomainError
from .sidereal import _STAR_ANCHORED, _AYANAMSA_AT_J2000, _AYANAMSA_DRIFT_PER_CENTURY
from . import stars, julian


def _propagate(record, tt):
    """Interval extension of stars._propagate_icrs_vector, including J2000."""
    values = (record.ra_deg, record.dec_deg, record.pmra_mas_yr,
              record.pmdec_mas_yr, record.radial_velocity_km_s)
    if not all(isfinite(v) for v in values):
        raise GocharaResourceError("live anchor has nonfinite propagation inputs")
    ra, dec = (D.point(I.point(v)*PI/180) for v in values[:2])
    c, s, cr, sr = dec.cos(), dec.sin(), ra.cos(), ra.sin()
    p = (c*cr, c*sr, s)
    east, north = (-sr, cr, D.point(0.)), (-s*cr, -s*sr, c)
    # Sovereign owner uses mu_alpha*/cos(dec), with a declared polar branch.
    if c.value.lo <= 1e-12 <= c.value.hi or c.value.lo <= -1e-12 <= c.value.hi:
        raise GocharaResourceError("live anchor polar branch is ambiguous")
    dra = D.point(0.) if c.value.magnitude <= 1e-12 else record.pmra_mas_yr * D.point(stars._MAS2RAD) / c
    ddec = record.pmdec_mas_yr * D.point(stars._MAS2RAD)
    velocity = tuple(dra*c*e+ddec*n for e, n in zip(east, north))
    dt = (tt-2451545.)/365.25
    if isfinite(record.parallax_mas) and record.parallax_mas > 0:
        distance = D.point(1000.)/record.parallax_mas
        rv = record.radial_velocity_km_s*(D.point(31557600.)/(D.point(149597870.7)*206264.806247096355))
        vector = tuple(distance*x+(v*distance+rv*x)*dt for x, v in zip(p, velocity))
    else:
        vector = tuple(x+v*dt for x, v in zip(p, velocity))
    normalized = unit(vector)
    if tt.value.lo <= 2451545. <= tt.value.hi:
        # The point owner returns p directly at J2000, without normalization.
        # Retain that branch only at the point; no false constant derivative.
        if tt.value.lo == tt.value.hi:
            return tuple(hull((x, y)) for x, y in zip(normalized, p))
    return normalized


class SiderealFrames(FrameEnclosures):
    """Named frame policy; mutation/caches remain owned by a single request."""
    def __init__(self, meter, system):
        self.system = system
        self.anchor = _STAR_ANCHORED.get(system)
        self.record = None
        if self.anchor:
            self.record = stars._resolve_star_record(self.anchor[0], stars.DEFAULT_FIXED_STAR_POLICY.lookup)[0]
        super().__init__(meter)
        self.offset = bounded_memo(self.offset,
            key=lambda t, coarse=False: _differential_key(t)+bytes((coarse,)), maxsize=4096)

    def offset(self, tt, coarse=False):
        angles = super().angles(tt, coarse=coarse)
        if self.anchor:
            xyz = _propagate(self.record, tt)
            eq = true_equator(xyz, angles, sincos=self.sincos)
            tropical = rotate_x(eq, angles[3], sincos=self.sincos)
            reference = degrees(atan2(tropical[1].center.lo+tropical[1].center.hi,
                                      tropical[0].center.lo+tropical[0].center.hi))
            return (longitude_differential(tropical, reference)-self.anchor[1])*PI/180
        _, precession = self._polynomials(tt)
        return (precession+angles[1]+I.point(_AYANAMSA_AT_J2000[self.system])*PI/180
                +((tt-2451545.)/36525)*_AYANAMSA_DRIFT_PER_CENTURY.get(self.system, 0.)*PI/180)

    def angles(self, tt, *, coarse=False):
        base = super().angles(tt, coarse=coarse)
        return (*base[:4], self.offset(tt, coarse))


class GocharaWindowAstronomy:
    """Reader-bound interval context with frozen clock and anchor identities."""
    def __init__(self, reader, meter, policy, start, end):
        self.reader, self.meter, self.policy = reader, meter, policy
        self.epoch = lru_cache(maxsize=4096)(lambda t: _bind_ephemeris_time(t, reader))
        identity = self.epoch(start).identity
        if any(v is None for v in (identity.planetary_ephemeris, identity.lunar_ephemeris,
                                    identity.lunar_tidal_acceleration_arcsec_per_cy2)):
            raise GocharaResourceError("Gochar requires a declared planetary/lunar time identity")
        self.frame_factory = lambda m: SiderealFrames(m, policy.ayanamsa_system)
        self.astro = AstronomyEnclosures(self)
        self.astro.clock = MarriageClockEnclosures(reader, identity)
        self.clock_signature = self._clock_signature()
        self.anchor_signature = repr(self.astro.frames.record)
        self.start, self.end = start, end
        # These endpoints are safe with respect to BOTH UT1 and rounded TT.
        lo, hi = self.astro.clock.minimum, self.astro.clock.maximum
        def lower_ok(u):
            return self.astro.clock.tt(u,u).lo >= lo
        def upper_ok(u):
            return self.astro.clock.tt(u,u).hi < hi
        import math
        lower = lo
        if not lower_ok(lower):
            a, b = lo, lo+1
            for _ in range(40):
                m = (a+b)/2
                if lower_ok(m):
                    b = m
                else:
                    a = m
            lower = b
        upper = math.nextafter(hi, -math.inf)
        if not upper_ok(upper):
            a, b = hi-1, upper
            for _ in range(40):
                m = (a+b)/2
                if upper_ok(m):
                    a = m
                else:
                    b = m
            upper = a
        self.effective_clock_bounds = (lower, upper)
        if start < lower or end > upper:
            raise GocharaWindowDomainError("UT1/TT clock-frame intersection", lower, math.nextafter(upper, math.inf))

    @staticmethod
    def _clock_signature():
        # Loaded immutable values, not a path or an unverified file name.
        return repr((julian._DELTA_T_HPIERS_2016, julian._DELTA_T_ANNUAL,
                     julian._delta_t_hpiers_annual_bridge(),
                     julian._delta_t_observation_boundary(), julian.EOPRegistry._ensure_loaded()))

    def assert_resources(self):
        if self._clock_signature() != self.clock_signature:
            raise GocharaResourceError("clock/EOP inputs changed during Gochar search")
        if _bind_ephemeris_time(self.start,self.reader).identity != self.astro.clock.identity:
            raise GocharaResourceError("serving time identity changed during Gochar search")
        anchor = self.astro.frames.anchor
        if anchor and repr(stars._resolve_star_record(anchor[0], stars.DEFAULT_FIXED_STAR_POLICY.lookup)[0]) != self.anchor_signature:
            raise GocharaResourceError("live anchor changed during Gochar search")

    def longitude(self, planet, a, b, coarse=False):
        """Unwrapped sidereal longitude and derivative with respect to UT1."""
        tt = self.astro.tt(a, b)
        vector = self.astro.coordinates_tt(planet, tt.lo, tt.hi, coarse)[2]
        reference = degrees(atan2(vector[1].center.lo+vector[1].center.hi,
                                  vector[0].center.lo+vector[0].center.hi))
        jet = longitude_differential(vector, reference)
        clock = self.astro.clock.jet(a,b)
        shift = clock.center-(tt.lo+tt.hi)/2
        return D(jet.value, jet.rate*clock.rate, jet.center+jet.rate*shift,
                 (I(a,b)-(a+b)/2).magnitude, jet.centered and clock.centered)

    def signal(self, planet, a, b, coarse=False):
        from ._event_search.isolation import Signal
        jet = self.longitude(planet,a,b,coarse)
        return Signal(jet.value, jet.rate, jet.center if jet.centered else None)

    def receipts(self):
        self.assert_resources()
        caches = []
        for prefix,owner in (("astronomy",self.astro),("frames",self.astro.frames),("clock",self.astro.clock)):
            for name in sorted(vars(owner)):
                item=getattr(owner,name)
                if callable(item) and hasattr(item,"cache_info"):
                    caches.append(("cache:"+prefix+"."+name,repr(item.cache_info())))
        return (
            ("clock_inputs_sha256", sha256(self.clock_signature.encode()).hexdigest()),
            ("anchor_record_sha256", sha256(self.anchor_signature.encode()).hexdigest()),
            ("anchor_record", self.anchor_signature),
            ("clock_identity", repr(self.astro.clock.identity)),
            ("effective_clock_start_jd_ut1", repr(self.effective_clock_bounds[0])),
            ("effective_clock_end_jd_ut1", repr(self.effective_clock_bounds[1])),
            ("arithmetic_model", "outward_binary64_RN_with_libm_at_most_4ulp"),
            *caches,
            *(("serving_source_sha256", digest) for digest in sorted(self.astro.records.sources)),
        )
