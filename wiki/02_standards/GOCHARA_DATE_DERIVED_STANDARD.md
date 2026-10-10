# Date-derived Gochar composition — VED-017

Implementation boundary: 6 October 2026. This product derives a complete
seven-classical-body snapshot from a birth instant and a transit instant.
The [Gochar snapshot standard](GOCHARA_BACKEND_STANDARD.md) continues to own
Phaladeepika baseline, indications, ordinary Vedha, exemptions and raw BAV
context. Dated windows and ingress searches remain a separate open product.

## Governing objects and authority

`moira/gochara_dated.py` owns astronomical input composition, immutable epoch
receipts and optional same-birth raw BAV derivation. It delegates judgment to
`gochara_from_positions` and `gochara_subsystem_profile`; it adds no verses,
planetary participants, alternative references or strength score.

The existing source-collated Phaladeepika fixture remains authoritative for
the judgment rules. Optional BAV reuses the existing Moira encoding of B. V.
Raman, *Ashtakavarga System of Prediction* (1981). This is a named additional
table convention, not a claim that the Phaladeepika scan establishes those
particular rekha rows. Edition reconciliation and treatment of four rekhas
remain outside this package. The owning
[Ashtakavarga standard](ASHTAKAVARGA_BACKEND_STANDARD.md) identifies that
encoding and its existing validation boundary.

Astronomy uses the installed planetary reader, Moira's canonical apparent
planetary pipeline and reader-bound clock reduction. JPL identifies planetary
ephemeris integration time as TDB in its
[export documentation](https://ssd.jpl.nasa.gov/planets/eph_export.html).
The [IERS time-scale reference](https://www.iers.org/iers/en/dataproducts/tools/timescales/timescales)
distinguishes civil UTC, Earth rotation UT1 and dynamical time coordinates.
No timestamp is silently used interchangeably across these scales.

## Policy and resource contract

| Choice | Default | Admitted boundary |
| --- | --- | --- |
| `ayanamsa_system` | `Lahiri` | All twelve named Moira systems. Each epoch has its own TT and offset. |
| Ayanamsa mode | `true`, fixed | Polynomial systems include nutation; live-star systems use the named catalogue anchor at TT. Missing anchors fail, without polynomial fallback. |
| Planetary origin/frame | Apparent geocentric / true ecliptic of date, fixed | Light time, annual aberration, gravitational deflection and nutation enabled. No topocentric or mean-frame switch. |
| `natal_bav_mode` | `OMIT` | `COMPUTE_RAW` requires `GocharaBirthLocation`; location without this selection is rejected. |
| `gochara_policy` | Existing Phaladeepika policy, complete observations required | Existing Vedha and BAV scope choices. Every successful dated calculation actually observes all seven bodies, even if retain-partial is selected. |

`COMPUTE_RAW` contradicts inner `GocharaBavMode.OMIT` and is rejected.
Inner `REQUIRE_ALL_RAW` requires `COMPUTE_RAW`. No caller BAV tables enter this
product. Without computation, the outer omission choice records that no natal
BAV was generated; the inner evaluator independently records the absence or
omission under its own policy.

The catalogue now has 32 records in the existing sixteen topics. Two new
engine-scope decisions, `astronomy.reader_epochs` and
`bav.natal_raw_raman_1981`, describe this compositor. Outer
`policy.selected_options` exposes the selected composition decisions. Inner
`gochara_policy.selected_options` still describes the supplied-position
evaluator receiving those derived inputs; its caller is the compositor.

Inputs and policy are checked before reader discovery. Both epochs use the
same reader argument or facade reader, with contextual binding restored on
success and failure. Readers must expose an admitted content-derived
planetary/lunar clock identity. Missing planetary segments, unknown time
identity or missing live anchor resources raise `GocharaResourceError`.
An uncovered epoch raises `GocharaCoverageError`. No successful partial
snapshot is substituted for resource failure. No download is performed.

## Derivation and provenance

1. Validate finite UT1 Julian dates in the bounded representable input domain
   `[-10000000, 10000000]`. Kernel coverage remains independently mandatory.
2. Bind each UT1 epoch to TT, TDB and its serving DE/LE identity using
   `_bind_ephemeris_time`. Preserve Delta-T source, historical tidal correction,
   TDB-minus-TT and identity labels.
3. Derive each true ayanamsa at that epoch's bound TT. Derive all seven tropical
   longitudes using the explicit reader and that same TT; subtract that epoch's
   ayanamsa. Preserve tropical input, offset, sidereal longitude and sign.
4. If selected, derive geometric birth Lagna using UT1 Earth rotation and TT
   precession, nutation and obliquity. Use mean obliquity in the equation of
   equinoxes and true obliquity in horizon/ecliptic geometry. Subtract the
   natal ayanamsa. Birth latitude excludes the poles; a coincident
   horizon/ecliptic has no unique Lagna and fails explicitly.
5. Accumulate each subject's own raw BAV from the seven natal signs and that
   Lagna with `bhinnashtakavarga`. Preserve eight named sign inputs, all raw
   tables and their source label. Apply neither shodhana nor a strength cutoff.
6. Evaluate transit signs against the natal Moon sign through the existing
   core and derive its local profiles, summary and directed network.

The private sidereal-time helper evaluates IAU 2006 GMST's equinox polynomial
at TT and ERA at UT1, following
[SOFA/ERFA gmst06](https://github.com/liberfa/erfa/blob/v2.0.1/src/gmst06.c).
Its equation of equinoxes uses mean obliquity as described by
[SOFA/ERFA ee00](https://github.com/liberfa/erfa/blob/v2.0.1/src/ee00.c).
It retains the existing Moira complementary-term approximation. Existing
public one-epoch sidereal-time behavior is preserved; this is a separate
private two-scale composition entry point.

`GocharaEpoch` and `GocharaDateResult` are frozen. Clock receipts, seven-body
cardinality, named frames, source labels and policy compatibility are checked;
all sidereal positions, BAV, judgments and profiles derive from their retained
inputs. Derived fields cannot be passed into constructors. Direct vessel
construction validates structural consistency, not binary SPK authenticity.
Use the factory or facade to derive reader-backed observations. Identity labels
identify the serving integration, not a cryptographic hash of every SPK leg.

## Public engine and facade

The following eleven names share object identity through `moira`,
`moira.facade` and `moira.vedic`:

| Surface | Meaning |
| --- | --- |
| `GocharaNatalBavMode` | Omit or compute raw natal BAV |
| `GocharaDatePolicy`, `DEFAULT_GOCHARA_DATE_POLICY` | Astronomical composition policy |
| `GocharaBirthLocation` | Finite geographic birth latitude/longitude |
| `GocharaDatedPosition`, `GocharaEpoch` | Retained tropical input, sidereal reduction and clock/frame receipt |
| `GocharaDateResult` | Natal/transit epochs, optional Lagna/BAV provenance and derived subsystem profile |
| `GocharaResourceError`, `GocharaCoverageError` | Distinct resource and epoch-coverage failures |
| `gochara_at`, `gochara_for_datetimes` | Explicit UT1 or aware civil-instant composition |

`Moira.gochara_at` and `Moira.gochara_for_datetimes` delegate with the instance
reader. Bare dates and naive civil times are rejected. Civil instants use
`jd_from_datetime` then `utc_to_ut1` exactly once per epoch, under the existing
Moira leap-second/Earth-rotation policy. Equivalent timezone offsets identify
the same instant. Returned epoch receipts preserve the astronomical coordinates
actually used. The original civil-zone representation is not retained.

```python
from datetime import datetime, timezone
from moira import Moira, GocharaDatePolicy, GocharaNatalBavMode, GocharaBirthLocation

m = Moira()  # Uses the installed kernel discovery contract.
r = m.gochara_for_datetimes(
    datetime(1990, 1, 1, tzinfo=timezone.utc),
    datetime(2026, 10, 6, tzinfo=timezone.utc),
    policy=GocharaDatePolicy(natal_bav_mode=GocharaNatalBavMode.COMPUTE_RAW),
    birth_location=GocharaBirthLocation(28.6139, 77.209),
)
assert r.profile.snapshot.missing_planets == ()
assert len(r.profile.snapshot.bhinna) == 7
```

An existing chart's birth instant can be used through the same epoch/civil
entry points. Arbitrary chart position dictionaries are not certified as
matching this frame or correction regime. A transit instant before birth is
allowed as a retrospective comparison; no forecast interpretation is inferred.

## REST and validation

`POST /v1/gochara/from-epochs` and `POST /v1/gochara/from-datetimes` expose the
same startup-bound facade and typed result. The
[REST standard](GOCHARA_REST_STANDARD.md) defines their request and failure
contracts. Five Gochar routes are discoverable under `classical-vedic`.

The [validation receipt](../03_validation/GOCHARA_DATE_DERIVED_VALIDATION_2026-10-06.md)
records the executed source-fixture, clock/oracle, reader-isolation, raw BAV,
frozen-vessel, REST and installed-DE441 checks. These prove bounded composition
and transport behavior. They do not certify every named ayanamsa against an
external tradition, independently re-audit Raman editions, demonstrate
predictive accuracy, or imply website adoption, release or deployment.
