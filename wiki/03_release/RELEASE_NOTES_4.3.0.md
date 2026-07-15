# Moira 4.3.0 — Source-Owned Western Electional Profiles

Moira 4.3.0 expands Western electional astrology from one bounded Moon
condition into three independent historical lineages, a shared Dorothean
root-and-matter context, source-complete Dorothean and Sahl matter profiles, and a
bounded profile-status scanner. It also adds the first source-owned classical
perfection event profile. Every admitted object is public through the
engine, `Moira` facade, and typed REST API.

## Sahl and Dorotheus Moon conditions

The release adds two Moon-condition profiles beside the existing Ramesey
profile:

- `sahl_moon_condition_v1`, following Sahl bin Bishr's ten impediments in
  *On Elections* section 22;
- `dorotheus_moon_condition_v1`, following the eleven corruption clauses in
  Dorotheus, *Carmen Astrologicum* V.6.3-14 and preserving V.6.15 as a separate
  remedy instruction.

Public REST routes are:

- `POST /v1/electional/western/sahl-moon-condition`
- `POST /v1/electional/western/dorotheus-moon-condition`

Sahl's unstated burnt-path endpoints and conflicting Arabic/Latin eighth-rule
readings remain named policies. Burnt-path policy is required: callers may
select source-faithful indeterminacy, the Dykes glossary/fall-degree interval
`[199, 213)`, or the later fifteen-degree interval `[195, 225)`. Dorotheus's
underdetermined southern-descending and longitude-or-latitude disengagement
clauses remain measured but `not_evaluable`; later orbs and modern proxies are
not imported silently.

## Six Sahl fourth-house matter profiles

Sahl's fourth-house sequence in *On Elections* §§43-55 is now public as six
distinct profiles rather than one generic fourth-house election:

- `sahl_building_v1`
- `sahl_demolition_v1`
- `sahl_land_v1`
- `sahl_wells_and_rivers_v1`
- `sahl_planting_v1`
- `sahl_sowing_v1`

They are available through `sahl_matter_profile_at(...)`,
`Moira.sahl_matter_profile_at(...)`, and
`POST /v1/electional/western/sahl-matter-profile`. Every response embeds the
general Sahl Moon-condition layer and preserves the selected matter's clauses
in source order. Sign class, explicit houses, dignity, bounds, lunar light,
bodily joining, and whole-sign configuration compute where the source closes
them. "In number," eastern/ascending, circle motion, cleansing, open
adaptation, and unstated separation windows remain visible `not_evaluable`
clauses with their measurements and source notes. No later convention is
silently treated as Sahl's own rule.

## Neutral lunar ecliptic direction

Phase 3 adds a first-class astronomical witness for the Moon's ecliptic
latitude direction:

- `lunar_ecliptic_direction_at(...)`
- `Moira.lunar_ecliptic_direction_at(...)`
- `POST /v1/electional/western/lunar-ecliptic-direction`

The immutable result separates north/south position from northward/southward
motion and reports the previous, next, and nearest exact sign-changing node
crossings with direction, longitude, UT1 time, latitude residual, and hours
from the query. Its tolerances are numerical root policy, not an astrological
node orb.

Dorotheus V.6 southern descent and V.7 northward crossing now consume this same
neutral witness under distinct source policies. The solar-disengagement clause
also exposes canonical instantaneous conjunction motion plus independent
latitude evidence. The historical texts do not define a crossing interval or
a longitude/latitude combination law, so those doctrine states remain
indeterminate despite the now-complete measurable geometry.

## Dorothean root, outcome, and matter context

`dorotheus_rooted_context_v1` makes the shared V.6/V.31 structure explicit:

- the Moon is the root of the work;
- the lord of the Moon's sign describes the outcome;
- the first exact traditional Moon connection is searched only until sign
  exit;
- six matter-significator families remain distinct;
- ephemeral elections reject natal inputs, while radical elections require a
  complete natal moment, location, and house-system bundle.

It is available through `Moira.dorotheus_rooted_context_at(...)` and
`POST /v1/electional/western/dorotheus-rooted-context`. V.31 bad-place truth is
now computed from Dorotheus's explicit whole-sign set: places 3, 6, 8, and 12,
with the Moon's rejoicing in the third preserved as the named exception.
Broader "made unfortunate" semantics remain a visible unresolved source gate;
the edition glossary says they are *usually* conjunction, square, or opposition
with an infortune, which is not an exclusive closed rule.

Phase 4 makes that boundary machine-readable. Each V.31 significator now
returns separate under-rays, made-unfortunate, Ascendant-relation, and
bad-place testimonies with an explicit combination law. “Made unfortunate” is
`not_evaluable`; observed malefic configurations remain evidence rather than
an invented closed definition.

V.6.29 also returns three distinct supplementary indicators. The
Lot-of-Fortune lord is computed through Moira's sect-aware Lots engine for the
inception, and the next Moon connection remains an outcome supplement. The
editorial ninth-part lord is a visible source gate because the edition supplies
no division scheme. None replaces the Moon-sign lord as the primary outcome
indicator.

## Ramesey urgent-time remedy fulfillment

The existing non-erasing remedy witness now reports clause-level fulfillment
through the engine, facade, and REST response. Moon cadence and whole-sign
relation to the Ascendant are evaluated; Jupiter or Venus is tested for
first-house placement or whole-sign sextile/trine; and the planetary-hour lord
is identified. The three commands to fortify the Ascendant cusp, Ascendant
lord, and hour lord remain typed `indeterminate` clauses because the source
does not define a closed fortification predicate. Aggregate fulfillment is
`fulfilled`, `not_fulfilled`, or `indeterminate` and remains separate from
urgent applicability and the ten Moon impediments.

## First source-complete matter profile

`dorotheus_construction_v1` composes Dorotheus V.2-V.6, V.31, and every V.7
construction clause. It exposes sign tempo, convertible and twin-sign effects,
sect fit, Moon condition, root/outcome evidence, matter significators, lunar
light, and benefic/malefic strong-place witnesses.

Public access is available through:

- `dorotheus_construction_at(...)`
- `Moira.dorotheus_construction_at(...)`
- `POST /v1/electional/western/dorotheus-construction`

The result distinguishes completeness precisely:

- `source_complete: true`
- `complete_matter_profile: true`
- `numerically_complete: false`
- `complete_electional_judgement: false`

Increasing in calculation now uses the source-defined equation sign: Moira
compares the Moon's true orbital longitude in the mean ecliptic and equinox of
date with the IERS 2010 TT mean lunar longitude. The REST clause witness exposes
both longitudes, the signed equation, and whether it was added or subtracted.
The independent "on the ecliptic, rising north" clause still lacks a
source-defined crossing region or tolerance, so it remains `not_evaluable`
rather than importing a modern orb.

## Bounded profile-status windows

The three Moon-condition profiles can now be scanned through:

- `scan_western_electional_profile(...)`
- `Moira.western_electional_profile_windows(...)`
- `POST /v1/electional/western/profile-windows`

Callers must explicitly select one or more qualifying statuses:

- `clear_of_profile_impediments`
- `one_or_more_profile_impediments`
- `indeterminate`

Every sampled instant reports its status, qualification truth, triggered rule
IDs, and not-evaluable rule IDs. Adjacent qualifying samples may be merged
under an explicit gap policy, but the result makes no claim that truth is
continuous between samples or that an exact transition boundary was solved.

REST scanning is limited to 256 points with a minimum one-hour cadence.
Ramesey and Sahl reuse range-level void-of-course windows rather than repeating
the same sign-level search at every point. A local DE441 performance smoke at
the 256-point cap completed in approximately 1.2 seconds for each of those two
profiles on the release workstation; this is operational performance evidence,
not scientific validation or a cross-platform guarantee.

## Dorothean demolition, leasing, and land profiles

Three additional source-closed matter layers are available through one named
public contract:

- `dorotheus_demolition_v1` preserves the Moon's southward latitude motion
  and the separate strengths of Jupiter, Venus, Mars, and Saturn;
- `dorotheus_leasing_v1` preserves the hiring party, owner/provider,
  amount/price, and outcome as distinct whole-sign angular topics;
- `dorotheus_land_purchase_v1` preserves land, trees, vegetation, cultivation,
  and the watery/twin terrain testimonies of the fourth place.

Public access is available through:

- `dorotheus_matter_profile_at(...)`
- `Moira.dorotheus_matter_profile_at(...)`
- `POST /v1/electional/western/dorotheus-matter-profile`

The V.9 lunar-flow geometry is now complete and first-class. Callers explicitly
select a current-sign or bounded fixed-lookback previous-event window, and the
result preserves the exact previous separation, current signed motion, next
sign-bounded connection, event times, signed residuals, sign bounds, and
no-event reasons. It is public through:

- `moon_connection_flow_at(...)`
- `Moira.moon_connection_flow_at(...)`
- `POST /v1/aspects/moon-connection-flow`

Leasing requests require that explicit window policy and embed the same flow
in their REST response. The V.9 clause nevertheless remains `not_evaluable`:
the surviving V.9 text requires flow-away and connection but does not assign
them to its four leasing stakes. These profiles do not score, rank, advise, or
recommend. Sahl's fourth-house profiles now preserve their unresolved
computational language as explicit typed policy rather than deferring the
entire source layer or fabricating a closed predicate.

## First-class signed aspect motion

Phase 2A of the Western electional implementation program adds an immutable,
kernel-free motion witness for one selected longitude aspect:

- `aspect_motion_witness(...)`
- `Moira.aspect_motion_witness(...)`
- `POST /v1/aspects/motion-witness`

The witness exposes the selected positive, negative, conjunction, or ambiguous
branch; signed error; relative longitude speed; orb rate; exact and rate
tolerances; canonical scaled-orb admission; body station thresholds and
reasons; and caller-declared reference frame and timescale. Its state is
`applying`, `exact`, `separating`, `stationary`, or `indeterminate`.

This is instantaneous geometry only. Missing speeds, relative standstill, and
equidistant branches remain explicit, and the surface does not claim to locate
a future perfection, station, prohibition, or Dorothean root/outcome event.

## Lilly 1647 classical perfection

The full 1647 *Christian Astrology* facsimile closes a named, bounded
perfection profile at printed pp. 110-113 and 125-126:

- `lilly_perfection_at(...)`
- `Moira.lilly_perfection_at(...)`
- `POST /v1/electional/western/classical-perfection`

`lilly_1647_perfection_v1` traces exact Ptolemaic aspects, stations, and sign
ingresses for the seven traditional planets over an interval of at most 31
days. It returns separate source-referenced witnesses for direct perfection,
translation of light, collection of light, bodily/aspectual prohibition,
refranation, and frustration.

The exposed fixed policy names UT1 input with internal TT conversion, apparent
geocentric true-ecliptic-of-date longitudes, and astrometric geocentric
longitude rates; those distinct products are not collapsed into one vague
position claim.

The profile uses Moira's canonical Lilly planetary moieties. Translation
requires reception by house, active triplicity, or Egyptian term and no prior
intervening planetary contact. Collection requires two significators that do
not behold one another by sign, application to one slower collector, and the
collector's reception by each significator in an essential dignity.
Prohibition requires the same swifter third planet to perfect successively
with both significators before their intended union; a single unrelated
contact is not enough.

Every result exposes its initial states, deterministic event chronology,
supporting event ids, reception bases, reader provenance, and typed
`present`/`absent`/`indeterminate` states. Exact ties and prior sign ingresses
remain indeterminate under the fixed v1 policy. This is not a score,
recommendation, or complete electional judgement. Sahl and Bonatti perfection
profiles, abscission, and reflection remain explicitly unadmitted.

## Bounds-table correctness

The previously advertised Ptolemaic bounds constant duplicated the Egyptian
table, while the advertised Chaldaean table implemented neither Ptolemy's
stated triplicity sequence nor its sect-dependent Saturn/Mercury ordering.
Version 4.3.0 corrects both defects from *Tetrabiblos* I.20/I.21 in the F. E.
Robbins translation.

The admitted doctrine values are now:

- `egyptian`
- `ptolemaic`
- `chaldean_day`
- `chaldean_night`

The Ptolemaic table preserves the transmitted planetary totals of Saturn 57°,
Jupiter 79°, Mars 66°, Venus 82°, and Mercury 76°. The Chaldaean variants use
the source-stated 8°-7°-6°-5°-4° widths and explicitly reverse Saturn and
Mercury precedence between day and night.

`GET /v1/egyptian-bounds/table` and every bound-truth REST envelope now expose
the selected table's primary-source citation. The ambiguous former value
`chaldean` is rejected; callers must choose the day or night doctrine.

## Compatibility

All electional engine, facade, and REST entry points are additive relative to
4.2.1. The provisional Sahl 4.3.0 request now requires explicit burnt-path
policy and uses source-distinguishing enum names; no downstream consumer is
known. The profile-window surface was not present in a released version, so its
explicit `qualification_statuses` requirement does not break a published
contract.

The Ramesey profile now reports version `1.1.0`; its remedy vessel changes from
instruction-only metadata to typed tri-state fulfillment. The electional
surface currently has no downstream consumers, so this provisional contract is
corrected directly without a compatibility shim. The previously unreleased
Dorotheus rooted context now reports version `1.2.0` and adds its fortification
and supplementary-indicator witnesses.

The matter-profile surface was likewise unreleased. Its V.9 leasing request
now requires `moon_flow_policy`; this prevents an undocumented prior-event
window from becoming an accidental public default.

Bounds callers using `chaldean` must migrate to `chaldean_day` or
`chaldean_night`. Ptolemaic and Chaldaean lookup results change because the
former tables were not valid implementations of their labels. Direct module
callers must replace `CHALDEAN_BOUNDS` with `CHALDEAN_DAY_BOUNDS` or
`CHALDEAN_NIGHT_BOUNDS`.

No existing generic electional predicate, numeric-fit scorer, relationship
route, or response envelope is removed or renamed. Version 4.3.0 does not
introduce electional scores, rankings, recommendations, source-unsupported
definite fortification claims, or empirical claims for astrological doctrine.

## Validation

Release evidence uses the project `.venv` on Python 3.14 with downloads
disabled, strict known-issue expiry, and the discovered DE441 kernel. It
includes:

- source-order, threshold, boundary, variant, and indeterminacy tests for the
  Ramesey, Sahl, and Dorotheus Moon profiles;
- synthetic periodic-root and DE441 sign-change tests for the neutral lunar
  latitude-direction witness, plus facade, REST, OpenAPI, and Dorotheus-clause
  integration coverage;
- rooted-context, natal-contract, next-connection, and matter-significator
  tests;
- V.2-V.7 construction invariants, ERFA/SOFA mean-lunar-longitude authority
  comparison, DE441 equation-sign evidence, and explicit unresolved-crossing
  tests;
- V.31 whole-sign bad-place membership and REST serialization tests;
- V.8/V.9/V.11 source order, angular-topic, latitude-direction, Pisces dual-
  testimony, DE441, facade, REST, and OpenAPI tests;
- exact public-export and facade-method governance;
- signed aspect-motion wrap, exactness, station, missing-speed,
  branch-ambiguity, facade, REST, and OpenAPI invariants;
- Lilly direct/translation/collection/prohibition/refranation/frustration
  isolation, canonical-moiety and reception-policy boundaries, DE441 event
  chronology, facade binding, REST round trip, and OpenAPI invariants;
- exact previous/next lunar-event ordering, caller-selected previous windows,
  signed residual and motion preservation, no-event reasons, DE441 fixed-epoch
  traces, leasing embedding, REST, and OpenAPI invariants;
- typed REST serialization and OpenAPI schema checks for every route;
- DE441 parity between optimized profile scans and independent single-moment
  evaluations;
- documentation consistency and release-version alignment.
- all 60 Ptolemaic segments, global planetary totals, Chaldaean day/night
  totals, boundary ownership, REST serialization, and rejection of the former
  ambiguous Chaldaean identifier.

These checks establish source fidelity, computational invariants, regression
protection, and transport visibility for the stated products. They do not
establish empirical validity for astrological claims.
