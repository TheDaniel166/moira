# Track B Mundane Source and Chart-Selection Dossier

Status: **source-locked; neutral atomic, Python, and REST admission verified in the Track B checkpoint**
Date: 2026-08-11
Baseline: `24e90f9fa4cdbe9692d6f70469df7863f4b15d36`
Implementation checkpoint: branch `codex/track-b-western-research-20260811`;
the admission commit containing this dossier is not a release, publication, or deployment

## 1. Purpose and boundary

Mundane v1 is a neutral composition of astronomical event receipts and an
explicitly selected local chart frame. It is not a prediction engine.

The contract may represent:

- the four tropical cardinal ingress roots;
- the strictly preceding primary syzygy;
- solar or lunar eclipse epochs whose meanings remain separately labeled;
- exact Jupiter-Saturn ecliptic-longitude conjunction roots; and
- an optional location projection with explicit coordinates, role, source,
  validity interval, house system, and failure state.

It must not emit political, economic, disaster, weather, conflict, national-fate,
or country-sign interpretations. Horary evidence and Mundane event charts do not
share a generic judgement layer.

## 2. Source hierarchy

### 2.1 Historical selection witnesses

#### Ptolemy quarterly/weather selector

Claudius Ptolemy, *Tetrabiblos*, Greek text edited and English translated by
Frank Egleston Robbins, Loeb Classical Library 435 (Cambridge, MA: Harvard
University Press; London: William Heinemann, 1940).

- Edition record: [Open Library OL182297M](https://openlibrary.org/books/OL182297M/Tetrabiblos)
- Public page-image corroboration: [Robbins 1940 scan](https://commons.wikimedia.org/wiki/File:Loeb_435_-_Ptolemy_-_Tetrabiblos_by_Robbins_(1940).pdf)
- Edition-identifying, page-preserving transcription:
  [LacusCurtius edition statement](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Ptolemy/Tetrabiblos/home.html)
- Exact section anchor: [Book II.12, printed p.207](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Ptolemy/Tetrabiblos/2C%2A.html#p207), continuing through p.209

Book II.10, printed pp.199-201, establishes the quarter starting points and the
new or full Moon most nearly preceding each equinoctial or solstitial point.
Book II.12, printed pp.207-209, repeats that selector and directs that angles be
disposed as for a nativity for each geographic latitude or clime investigated,
then distinguishes the subsequent monthly-lunation procedure. The geographic
latitude is not the Moon's ecliptic latitude mentioned later on p.209.

This source admits only a neutral quarterly **weather/season** chart selector
with an explicit target location. It does not authorize political, national,
economic, conflict, disaster, or generic Mundane interpretation, and it does not
choose a capital or other geopolitical subject.

#### Ramesey Aries-ingress cadence

William Ramesey, *Astrologia restaurata, or, Astrologie restored: being an
introduction to the general and chief part of the language of the stars, in four
books* (London: printed for Robert White, 1653); Book IV is *Astrologia Munda*.

- Original 1653 Wellcome scan and catalog record:
  [Internet Archive item b30323149](https://archive.org/details/b30323149)
- Book IV, section I, chapter I begins on [printed p.214](https://archive.org/details/b30323149/page/n19/mode/1up)
- Exact location and modality cadence are on [printed p.215](https://archive.org/details/b30323149/page/n20/mode/1up)
- [Printed p.216](https://archive.org/details/b30323149/page/n21/mode/1up) begins chapter II and confirms the rule's chapter boundary
- Searchable EEBO-TCP transcription/metadata aid:
  [A57689.0001.001](https://quod.lib.umich.edu/e/eebo2/A57689.0001.001)

Ramesey makes the Sun's entry into the first point of Aries the annual starting
point, requires the figure to be erected exactly for the region or place judged
using its pole elevation, and makes the number of charts depend on the
Aries-ingress Ascendant: movable/cardinal selects Aries, Cancer, Libra, and
Capricorn; common/mutable selects Aries and Libra; fixed selects Aries alone.
His own sign classification appears in Book II, printed pp.81-82; the printed
sign list governs despite the p.215 chapter-number cross-reference discrepancy.

This source admits only a neutral cadence and chart-selection receipt with an
explicit target location. It does not authorize automatic capital selection or
Ramesey's interpretive forecasts.

These are independent historical profiles. They must not be blended into a
single hidden default.

The Robbins/LacusCurtius text and EEBO-TCP are navigation or transcription
witnesses; the named edition and original page images govern. The modern
Birchfield revision is study material only and is not the Ramesey source lock.
Source admission does not prove that selectors, neutral event receipts,
validation fixtures, exports, serializers, REST models, or public APIs have been
implemented.

### 2.2 Astronomical definition and validation witnesses

- JPL Horizons defines Earth seasonal boundaries from the Sun's geocentric
  apparent ecliptic longitude: [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html).
- USNO seasonal anchors: [Earth's seasons](https://aa.usno.navy.mil/calculated/seasons).
- USNO phase anchors: [Moon phase API](https://aa.usno.navy.mil/api/moon/phases/year?year=2025).
- NASA/GSFC eclipse circumstances distinguish conjunction, greatest eclipse, and
  contact times: [2024 April 8 Besselian elements](https://eclipse.gsfc.nasa.gov/SEbeselm/SEbeselm2001/SE2024Apr08Tbeselm.html).
- IMCCE distinguishes right-ascension conjunction, ecliptic-longitude conjunction,
  and minimum elongation for Jupiter-Saturn:
  [2020 conjunction note](https://lettre-info-lte.obspm.fr/archives/174).

## 3. Finite event taxonomy

### 3.1 Cardinal ingress

The engine-authoritative ingress is an increasing root of Moira's
observer-centered geocentric apparent Sun longitude in the IAU 2006 P03 / IAU
2000A true ecliptic and equinox of date, at exactly:

- 0 degrees -- March equinox / Aries ingress;
- 90 degrees -- June solstice / Cancer ingress;
- 180 degrees -- September equinox / Libra ingress; or
- 270 degrees -- December solstice / Capricorn ingress.

This is Moira's existing, sovereign planetary product. JPL Horizons quantity 31
uses a distinct IAU76/80 ecliptic-of-date apparent product. Horizons is retained
as an independent cross-model comparator and must never be relabeled as Moira's
frame or as an exact-parity golden. USNO's minute-rounded season tables corroborate
event identity and chronology rather than sub-minute numerical identity.

Receipts must identify the longitude product, frame/equinox, timescales,
correction regime, content-derived active-reader identity, root residual, and
solver tolerance. An artifact digest is included only when an independently
verified install or release receipt owns it; the runtime must not hash a
multi-gigabyte planetary kernel per event. Seasonal labels are
hemisphere-neutral; zodiac labels remain aliases.

Two selection policies are allowed:

- `all_four_cardinal_ingresses_v1` -- the neutral default for event enumeration;
- `ramesey_1653_aries_ascendant_modality_v1` -- separately source-locked:
  cardinal rising selects four ingress charts, common/mutable rising selects Aries
  and Libra, and fixed rising selects Aries only.

The second policy is never silently applied to the first.
It requires an explicit provenance-bearing location and the Ascendant of the Aries
ingress at that location. Missing or ambiguous location makes Ramesey selection
`not_evaluable`. Angle computation and house computation remain separate so a
house-system failure cannot erase a successfully computed Ascendant receipt.
The original source for this cadence is Ramesey 1653, Book IV, section I,
chapter I, printed pp.214-215; it supplies no automatic capital or location-role
selection.

### 3.2 Strictly preceding primary syzygy

`strictly_preceding_primary_syzygy_v1` is a selection policy over already hardened
phase receipts. It selects the nearest exact Sun-Moon ecliptic-longitude difference
of 0 or 180 degrees whose event JD is strictly less than the anchor ingress JD.
Its engine-authoritative target function uses Moira's same apparent IAU 2006 P03 /
IAU 2000A true-of-date frame, while remaining a distinct Sun-Moon-difference
product from the ingress's solar-longitude product. Candidate phase receipts must
be homogeneous. Anchor and candidate receipts must agree on frame/equinox,
apparent/geometric correction regime, timescale, and content-derived reader
identity. Their individually admitted solver semantics and tolerances remain
explicit; the selector must not require the solar-ingress and lunar-phase solvers
to have the same method identifier.

The receipt includes:

- new/full phase;
- event JD in each exposed timescale;
- Sun-Moon longitude residual;
- longitude/frame definition; and
- no inferred eclipse association; a future association requires its own rule and
  provenance.

Following, nearest-on-either-side, and composite lunation policies are deferred.
Historical sources contain exceptions, so none may be introduced as an unnamed
fallback.

When this selector is exposed under the Ptolemy/Robbins named policy, its scope is
the quarterly weather/season procedure of *Tetrabiblos* II.10 and II.12, printed
pp.199-209. The receipt may preserve the ingress, selected preceding lunation,
explicit target location, local angles, and provenance, but it must not acquire a
generic Mundane interpretation layer.

### 3.3 Eclipse event

An eclipse is not represented by one unlabeled `eclipse_time`. The event receipt
may contain separately named:

- ecliptic syzygy;
- equatorial conjunction;
- greatest eclipse;
- global contact epochs.

Each field retains its owner and computational definition. Local eclipse
circumstances are deferred in v1 and surface as typed unavailable evidence;
their absence does not invalidate the global eclipse event.

Any local chart projection must provide an explicit `chart_epoch_kind` drawn from
the available named epochs. There is no default. A profile with eclipse epochs but
no selected chart epoch retains its global event and marks the local chart
`not_evaluable`.

### 3.4 Jupiter-Saturn conjunction

The v1 conjunction is every exact root of Jupiter and Saturn's geocentric apparent
ecliptic-longitude difference under one declared frame and correction regime.

- Each root is an independent event.
- Motion state for both bodies and the root residual are retained.
- Right-ascension conjunction and minimum elongation are different event types and
  must not be substituted.

Cluster identity is omitted from v1 because no source-owned grouping rule is yet
admitted. Mutation labels and 200/240/800/960-year interpretive doctrines are deferred.
Abu Ma'shar lineage work requires the edition-level authority of Yamamoto and
Burnett, Brill 2000, before admission.

## 4. Location and local chart selection

The astronomical instant is global. Location affects only angles, houses, and
local eclipse circumstances.

A local chart projection requires:

- latitude and east-positive longitude;
- a location label;
- a closed location role;
- a source identifier;
- a validity interval when the role is institutional; and
- an explicit house system and strict failure policy.

Admitted location roles are:

- `user_specified`;
- `seat_of_government`;
- `constitutional_capital`;
- `administrative_capital`; and
- `regional_center`.

The engine never chooses a capital. Modern states may have multiple functional
capitals; South Africa's official description is a clear counterexample:
[South African Government provinces](https://www.gov.za/about-sa/south-africas-provinces).

Neither Ptolemy nor Ramesey supplies a modern capital-selection rule. A named
historical selector therefore requires the caller's explicit target location.
Any institutional role is caller-owned metadata and must not be presented as a
fact inferred from either historical source.

Institutional validity uses a half-open `[valid_from, valid_until)` interval;
`valid_until=None` is open-ended. The caller owns the role assertion and its
source. The engine checks only whether the event epoch falls inside that asserted
interval; it does not certify a capital designation. For an eclipse chart, this
check uses the epoch selected by `chart_epoch_kind`, never an ambiguous event time.

If location is absent or ambiguous, the global event remains `evaluated` and the
local chart projection is `not_evaluable`. There is no universal historical house
system default for all Mundane lineages.

## 5. Neutral event-chart profile

The admitted `MundaneEventChartProfile` contains:

- one immutable anchor-event receipt as a tagged/discriminated union of cardinal
  ingress, primary syzygy, eclipse, or Jupiter-Saturn conjunction;
- typed strictly preceding syzygy evidence, including `not_evaluable`;
- typed explicit local projection evidence, including `not_evaluable`;
- chart geometry only when location and house policy are complete;
- source and engine provenance;
- included and excluded component ids; and
- typed not-evaluable issues.

It composes existing Moira event and chart primitives only after their receipts
satisfy this dossier. Global-event failure, missing location, angle failure,
house-system failure, and unavailable local eclipse circumstances remain different
states.

`moira.cycles.GreatConjunction` is not itself sufficient for this profile: it
lacks frame, correction regime, content-derived reader identity, residual, and
both motion states, while carrying a deferred mutation element. The admitted
Track B adapter therefore revalidates the underlying solver output, recomputes
the complete search interval, and preserves every root in a separate neutral
Jupiter-Saturn conjunction receipt. It does not embed the existing doctrinal
vessel as if that vessel alone satisfied this contract.

## 6. Ambiguity ledger

| Question | v1 decision |
|---|---|
| Which ingress matters? | named policy; neutral enumeration admits all four |
| Which lunation? | nearest strictly preceding exact new/full Moon |
| Which capital? | none is inferred |
| Does a capital role persist forever? | no; source and validity interval required |
| Which house system? | explicit caller selection |
| What is eclipse time? | several named epochs, never one ambiguous scalar |
| What is conjunction? | exact ecliptic-longitude root for this event type |
| Are triple Jupiter-Saturn roots one event? | no; v1 has no automatic cluster identity |
| Are historical and modern ephemerides interchangeable? | no; distinct provenance modes |
| Does the profile predict mundane outcomes? | no |

## 7. Independent validation fixtures

### 7.1 Ingress and preceding syzygy

- March equinox: 2025-03-20 09:01 UT, USNO seasonal table.
- Immediately preceding primary phase: full Moon, 2025-03-14 06:55 UT, USNO phase API.

The fixture checks event ordering, phase selection, and root residual. It does not
turn rounded almanac minutes into an exact numerical golden.

`tests/fixtures/mundane_track_b_reference.json` additionally freezes adjacent
one-second Horizons quantity-31 samples around both events. Those samples prove
the external IAU76/80 event identity and provide a cross-model timing comparison;
they do not redefine Moira's IAU 2006/2000A product. At the 2025 March equinox,
the derived Horizons crossing and Moira's existing ingress root differ by about
1.1 seconds. At the preceding full Moon, the derived crossings differ by less
than one tenth of a second. Both tolerances are declared comparison tolerances,
not claims that the frames are identical.

### 7.2 Eclipse epoch separation

NASA/GSFC's 2024-04-08 solar eclipse gives distinct published anchors:

- greatest eclipse: 18:17:18.3 UT;
- ecliptic conjunction: 18:20:49.7 UT; and
- equatorial conjunction: 18:36:07.6 UT.

This fixture rejects any serializer or model that collapses the three meanings.

### 7.3 Jupiter-Saturn anti-conflation

IMCCE publishes distinct 2020 anchors for:

- right-ascension conjunction: 13:31:56 UTC;
- ecliptic-longitude conjunction: 18:20:29 UTC; and
- minimum elongation: 18:22:30 UTC.

The v1 ecliptic-longitude event is compared with that anchor under the declared
model tolerance and rejects the other two as interchangeable labels.

## 8. Adversarial cases governing public admission

- an event exactly on a year/range boundary;
- the syzygy exactly equal to the anchor JD, which must not count as preceding;
- multiple syzygies in a search interval;
- a Jupiter-Saturn triple sequence with three retained roots;
- missing or stale location-role validity;
- two valid capital roles with no caller selection;
- high-latitude house failure without fallback;
- eclipse global event available but local circumstances unavailable;
- eclipse epochs available but no explicit local `chart_epoch_kind`;
- mixed TT/UT/UTC inputs with incomplete receipts;
- right-ascension conjunction supplied where ecliptic-longitude is required; and
- historical-table coordinates presented as if they were modern ephemeris output.
- a caller-asserted kernel digest presented as engine-verified content identity.

## 9. Research-gate decision

The Mundane research gate admits the finite neutral event/chart schema above.
Exact edition and page witnesses source-lock two separately named historical
selectors: Ptolemy/Robbins 1940 II.10 and II.12 for the neutral quarterly
weather/season preceding-syzygy and locality procedure, and Ramesey 1653 Book
IV, section I, chapter I, pp.214-215 for Aries-ingress cadence.

Both historical selectors require an explicit target location; the Ramesey
selector additionally requires an Aries-ingress Ascendant receipt. Missing or
invalid location evidence makes local selection/projection `not_evaluable`
without erasing evaluated global-event truth. The gate does not pass for
automatic national/capital selection, country-sign rulership, political or
economic prediction, markets, war, disaster, or any interpretive forecast.
Ptolemy's admitted selector remains weather/season scoped; weather
interpretation itself is excluded.

## 10. Executable admission receipt

The Track B checkpoint implements and verifies the admitted neutral surface
through:

- `moira.mundane` tagged ingress, primary-syzygy, eclipse, Jupiter-Saturn,
  location, local-projection, clock, provenance, and profile receipts;
- content-derived active-reader identity and coverage checks, explicit
  UT1/TT/Delta-T/UTC clock truth, and complete root/search revalidation;
- seven curated root/facade exports, with concrete event/search/location
  receipts remaining module-owned;
- four reader-bound `Moira` event-admission methods;
- one strict four-way-discriminated
  `POST /v1/mundane/event-chart-profile` transport that retains the complete
  selection context; and
- source-comparison, boundary, mismatch, forgery, public-contract, route, and
  OpenAPI tests.

The focused Mundane atomic file passed 63 tests with 13 DE441 resource receipts
and no skips or failures. The adjacent cycles/eclipse regression slice passed
121 tests, and the dedicated Mundane REST/OpenAPI slice passed 20 tests. The
2025 Horizons quantity-31 and USNO fixtures are deliberately independent-frame
comparators to Moira's IAU 2006 P03 / IAU 2000A apparent true-of-date product;
they are not relabeled as parity. NASA/GSFC governs eclipse epoch distinction,
and IMCCE supplies the 2020 conjunction anti-conflation anchor.

No interpretation, automatic capital choice, event clustering, country-sign
mapping, forecast, judgement, score, outcome, or advice was admitted.
