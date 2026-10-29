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
from ._stellar_space_motion import JULIAN_YEAR_DAYS, StellarArithmetic, space_motion
from . import stars, julian


def _interval_ra_rate(pmra_mas_yr, cos_dec):
    # The float owner switches to a zero right-ascension rate at a pole. An
    # enclosure straddling that switch has no certified value.
    if cos_dec.value.lo <= 1e-12 <= cos_dec.value.hi or cos_dec.value.lo <= -1e-12 <= cos_dec.value.hi:
        raise GocharaResourceError("live anchor polar branch is ambiguous")
    if cos_dec.value.magnitude <= 1e-12:
        return D.point(0.)
    return pmra_mas_yr * D.point(stars._MAS2RAD) / cos_dec


# Stage 1 of the fixed-star pipeline over certified interval differentials.
_INTERVAL_ARITHMETIC = StellarArithmetic(
    radians=lambda value: D.point(I.point(value)*PI/180),
    cos=lambda x: x.cos(),
    sin=lambda x: x.sin(),
    const=lambda value: D.point(value),
    mas_to_rad=D.point(stars._MAS2RAD),
    km_s_to_pc_per_year=D.point(31557600.)/(D.point(149597870.7)*206264.806247096355),
    ra_rate=_interval_ra_rate,
)


def _propagate(record, tt):
    """Interval enclosure of the fixed-star astrometric direction at ``tt``."""
    values = (record.ra_deg, record.dec_deg, record.pmra_mas_yr,
              record.pmdec_mas_yr, record.radial_velocity_km_s, record.ref_epoch_jd)
    if not all(isfinite(v) for v in values):
        raise GocharaResourceError("live anchor has nonfinite propagation inputs")
    dt = (tt-record.ref_epoch_jd)/JULIAN_YEAR_DAYS
    p, vector, _ = space_motion(
        record.ra_deg, record.dec_deg, record.pmra_mas_yr, record.pmdec_mas_yr,
        record.parallax_mas, record.radial_velocity_km_s, dt, _INTERVAL_ARITHMETIC,
    )
    normalized = unit(vector)
    if tt.value.lo <= record.ref_epoch_jd <= tt.value.hi:
        # The point owner returns p directly at the reference epoch, without
        # normalization. Retain that branch only at the point; no false
        # constant derivative.
        if tt.value.lo == tt.value.hi:
            return tuple(hull((x, y)) for x, y in zip(normalized, p))
    return normalized


class SiderealFrames(FrameEnclosures):
    """RITE: Request-bound sidereal frame enclosures

    THEOREM: The named ayanamsa policy selects either a propagated live-star
    anchor or the admitted precession, nutation, and secular-offset model.

    RITE OF PURPOSE:
        Extend FrameEnclosures with the requested sidereal offset; do not
        substitute a frozen offset or sampled speed for an interval enclosure.

    LAW OF OPERATION:
        Resolve the named anchor at construction when the policy requires one.
        Propagate that record using the serving star-owner inputs, or use the
        named ayanamsa tables, and return an angular differential in radians.
        Inherited frame tables, memoization, and work accounting remain owned
        by one request. An instance is not a cross-thread shared service.

    Canon: Moira sidereal policy, serving fixed-star propagation, and
        _event_search.frames.FrameEnclosures; not an external accuracy receipt.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._gochara_window_astronomy.SiderealFrames",
      "risk": "high",
      "api": {"frozen": [], "internal": ["__init__", "offset", "angles"]},
      "state": {"mutable": true, "owners": ["one Gochar window request"]},
      "effects": {"signals_emitted": [], "io": ["serving star records and frame tables"]},
      "concurrency": {
        "thread": "request_local",
        "cross_thread_calls": "forbidden",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "propagate resource, enclosure, lookup and work-budget failures; ambiguous or nonfinite live-anchor propagation raises GocharaResourceError"
      },
      "succession": {"stance": "internal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["frame or anchor doctrine"]}
    }
    [/MACHINE_CONTRACT]
    """
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
    """RITE: Reader-bound Gochar window astronomy

    THEOREM: Serving apparent-place and sidereal-frame differentials are
    composed with the declared clock to enclose longitude and its UT1 rate.

    RITE OF PURPOSE:
        Bind one search interval to its reader, policy, work meter, clock
        identity, and anchor evidence; expose signals and resource receipts
        without selecting transit windows or interpreting their astrology.

    LAW OF OPERATION:
        Require declared planetary, lunar, and tidal clock identities. Compute
        usable UT1 endpoints inside the admitted clock's rounded TT domain.
        Reject intervals outside that intersection. Resource assertions compare
        current clock inputs, serving identity, and any live anchor with the
        captured identities. Receipts run that assertion before reporting
        hashes and cache evidence. Reader access, caches, and accounting belong
        to this request; neither the instance nor its reader is made thread-safe
        by this wrapper. No resource ownership transfers.

    Canon: Moira serving-reader time binding, AstronomyEnclosures,
        MarriageClockEnclosures, and SiderealFrames; receipts are resource
        identity evidence, not independent astronomical validation.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._gochara_window_astronomy.GocharaWindowAstronomy",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": ["__init__", "_clock_signature", "assert_resources", "longitude", "signal", "receipts"]
      },
      "state": {"mutable": true, "owners": ["one Gochar window request"]},
      "effects": {
        "signals_emitted": [],
        "io": ["borrowed ephemeris reader, clock/EOP tables, and serving star records"]
      },
      "concurrency": {
        "thread": "request_local",
        "cross_thread_calls": "forbidden",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "raise GocharaResourceError for missing or changed identities, GocharaWindowDomainError for clock-domain exclusion; propagate serving reader, enclosure and work-budget failures"
      },
      "succession": {"stance": "internal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["clock, frame, enclosure or resource doctrine"]}
    }
    [/MACHINE_CONTRACT]
    """
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
