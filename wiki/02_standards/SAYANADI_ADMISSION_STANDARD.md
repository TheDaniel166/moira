# Sayanadi admission and birth-clock standard

**Status:** Locally implemented for the selected BPHS Navamsa-ordinal profile, Moira 6.9.9, 8 October 2026.
**Authority:** [edition collation and source decision](../06_roadmap/VEDIC_SAYANADI_SOURCE_RESEARCH_2026-10-08.md).
**Execution:** [implementation plan](../06_roadmap/VEDIC_SAYANADI_IMPLEMENTATION_PLAN_2026-10-08.md) and [validation receipt](../03_validation/SAYANADI_VALIDATION_2026-10-08.md).

## 1. Governing object and source policy

Sayanadi reports twelve planetary states and three substates. The executing
`SayanadiPolicy.formulation` is `bphs_navamsa_ordinal`, with source profile
`santhanam_collated_sharma`: Santhanam BPHS volume 1 chapter 45, printed
454-456, collated with Sharma's 1999 reprint, chapter 47, printed 623-626.
The name table uses Sharma and Rao's independently readable tables. Source
IDs, locators and canonical legacy state-label policy appear in every
engine-produced calculation trace.

For planet star `N`, source planet multiplier `P`, within-natal-sign Navamsa
ordinal `V`, Moon star `J`, birth-ghati ordinal `G`, and Lagna sign `L`:

```text
total = N * P * V + J + G + L
state remainder = total mod 12
state index A = 12 if remainder is 0, otherwise remainder
first remainder = (A * A + name value) mod 12
second remainder = (first remainder + planet addend) mod 3
1 -> Drishti; 2 -> Cheshta; 0 -> Vicheshta
```

`V` is ordinal 1-9 within the natal sign. D9 sign numbers, continuous D9
positions and degree-within-sign multipliers are different objects. The
documented Sanketanidhi/Hora Ratnam degree reading is not an executable
option. Unknown policy identities fail; an unimplemented variant cannot be
selected silently. This is a complete bounded calculation contract, not a
claim to resolve all classical textual variants.

The partition uses exact rational ownership of the admitted binary64 input:
modulo 360, equal half-open nakshatra/Navamsa cells, without an epsilon. The
displayed normalized float is capped at the adjacent interior value if an
extremely small negative wrap would otherwise display 360; integer ownership
comes from the rational input, never from that rounded display.

## 2. Strict body, name and clock contracts

Standalone subjects are Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
Rahu and Ketu. Require the subject and Moon in the position map; reject
unknown keys, missing inputs, booleans, numeric strings and nonfinite values.
The longitude frame is supplied by the caller and must be common to the
positions and Lagna. No Moon/body fallback or inferred frame exists.

`SayanadiName` admits exactly one numeric value (strict integer 1-5) or one
canonical Devanagari sound. There is no automatic transliteration, Unicode
normalization or extraction from a personal name. The caller selects the
personal-name convention. Resolved value, selected sound and mapping basis
remain in the trace. The [research table](../06_roadmap/VEDIC_SAYANADI_SOURCE_RESEARCH_2026-10-08.md#34-name-and-planet-tables-can-be-made-explicit)
contains all 35 tokens: in particular, `स` is 4, `श` is 2, `ष` is 3 and
`ह` is 5. A full name or ambiguous English `sa`/`sha` fails admission.

Direct `birth_ghati` is a strict positive integer ordinal. The adapter
`sayanadi_ghati_from_elapsed` accepts mutually exclusive finite nonnegative
elapsed seconds or nonnegative integer whole-ghatis plus integer vighatis
0-59. One ghati is 1,440 seconds; one vighati is 24 seconds. The ordinal is
the ceiling of positive elapsed ghatis; zero elapsed selects the first ghati
as an explicit Moira boundary decision. Santhanam's 30 ghatis 33 vighatis
becomes ordinal 31; Rao's 42.5 elapsed ghatis becomes ordinal 43. These clocks
cannot be replaced with civil hours since midnight or floored decimal ghatis.
No unexplained maximum of 60 is imposed on an actual sunrise interval.

`SayanadiContext` combines typed ghati, name and policy, with a strict boolean
chart node-evaluation control. Positional name/ghati inputs and typed context
are mutually exclusive. The standalone helper still returns one explicitly
selected subject; HTTP reserves `evaluate_nodes` for chart requests.

## 3. Chart and birth composition

`evaluate_avasthas(..., sayanadi_context=None)` preserves the existing four
families and returns Sayanadi status `omitted`, explicit null planet slots
and an empty node collection. Complete typed context selects `evaluated` and
requires exactly seven finite classical-body positions. An invalid/partial
context is an error, not omission. A selected node evaluation requires exactly
Rahu/Ketu and returns their Sayanadi results in `sayanadi_nodes`; it does not
invent node Baladi, dignity or other seven-body family results.

`avasthas_for_datetime` composes an aware birth instant, explicit latitude in
(-90, 90), longitude in [-180, 180], name and typed birth/avastha policies.
Naive/numeric civil timestamps, nonexistent ZoneInfo wall times and invalid
inputs fail before ephemeris work. The year range [2, 9998] permits adjacent
civil dates. An optional validated timezone name controls local civil-date
ownership; otherwise the supplied aware datetime's zone/offset owns it.

`SayanadiBirthPolicy` fixes apparent geocentric planetary longitudes in the
true ecliptic/equinox of date and named true ayanamsa, using the admitted
reader-bound Gochar epoch composer. Lagna reuses house geometry with that
epoch's TT. Node composition, when selected, is the existing true geometric
node of date; mean nodes are not an executable birth-policy switch. The two
node controls are independent: `evaluate_nodes` adds Sayanadi node subjects;
`lajjitadi_nodes` selects node afflictors in that existing family.

Sunrise discovery reuses daily Panchanga's preceding/current/following local
civil dates and rise/set signal. The finite product bound is three civil
dates, not an assumed 72 equal clock hours. Named horizon definitions are
Rashtriya upper limb (-47/60 degrees), USNO upper limb (-50/60 degrees) and
geometric center (0 degrees); the model is a level horizon at zero elevation
with no terrain. Local refinement over that same altitude signal retains a
root bracket at the selected 0.01-1 second stopping tolerance. This is
numerical root uncertainty, not observational/model sunrise accuracy.

The previous sunrise owns pre-sunrise/night births. The birth must fall
between the previous and next solved roots. If root uncertainty changes
sunrise ownership or the ghati ordinal, return `unavailable` with a reason,
clock brackets/candidate ordinals where resolved, and no epoch/chart. Absent
or multiple sunrises and unresolved local root brackets likewise remain
unavailable. No fixed sunrise, previous distant seasonal sunrise, civil
midnight, location or clock fallback is admitted. The daily civil-date
owner's skipped-date errors remain explicit input/composition errors.

The epoch retains UT1, TT/TDB, Delta-T source, planetary/lunar kernel identity
and ayanamsa method. A serving reader is installed for the whole composition;
borrowed readers are never closed, and the prior reader override is restored
on return or failure. Reader/clock/anchor failures raise `SayanadiResourceError`;
out-of-range epochs raise `SayanadiCoverageError`.

## 4. Public and REST surfaces

The nine Sayanadi core symbols and six birth-composition symbols share owning
object identity through `moira`, `moira.facade` and `moira.vedic`. `Moira`
provides `sayanadi_avastha`, `evaluate_avasthas` and `avasthas_for_datetime`.
The last method uses that facade's reader rather than a separate server engine.

| Route | Contract |
| --- | --- |
| `POST /v1/avasthas/evaluate` | Existing seven-body evaluator plus optional complete `sayanadi_context`, nullable per-planet results, status/context and separate node results. |
| `POST /v1/avasthas/sayanadi` | One explicitly selected source-defined subject with supplied positions/Lagna and typed clock/name/context. No ephemeris is needed. |
| `POST /v1/avasthas/from-datetime` | Startup-reader birth composition, date/frame/time policies, sunrise brackets, candidate ghati, epoch and evaluated or unavailable chart. |

HTTP clocks use a `kind` discriminator: `ordinal`, `elapsed_seconds` or
`ghati_vighati`. Unknown/extra fields, coercions, conflicting clocks/names,
unknown bodies/policies and incomplete selected node pairs fail preflight
with the normal `422 validation_error` envelope. Astronomical unavailability
is a typed 200 result, distinct from `503 sayanadi_resource_unavailable` or
`422 sayanadi_date_outside_coverage`. Serializers copy canonical engine
receipts and values; the server contains no state/name/clock algorithm.

Example supplied-input request:

```json
{
  "planet": "Sun",
  "sidereal_longitudes": {"Sun": 37.2, "Moon": 37.2},
  "lagna_sidereal_lon": 225,
  "context": {
    "clock": {"kind": "ghati_vighati", "whole_ghatis": 30, "vighatis": 33},
    "name": {"sound": "स"}
  }
}
```

The Sun is source-specified; the exact Moon/Lagna longitudes here are
representatives of the source's specified star/sign. The result is Netrapani,
Vicheshta, total 51, first remainder 1, final remainder 0.

## 5. Compatibility and historical prose

Valid positional helper calls retain their argument order and legacy `effect`
string. Formerly accepted coercions, missing Moon/unknown-body fallbacks,
negative ghati and invalid name values now fail. State/substate values at
affected partition boundaries intentionally change to the source-defined
cells. The other four avastha families retain their valid-call doctrine.

Legacy five-field `SayanadiAvastha` construction has null trace/provenance;
legacy two-field `AvasthaChartResult` construction has unknown/null Sayanadi
status. Engine-produced results explicitly distinguish omitted/evaluated and
supply consistent trace/context. Additional JSON fields are observable;
strict clients and saved calculations may need migration.

The existing effect summaries remain compatibility prose with provenance
`moira.sayanadi_effects.legacy_summary`, audit status `not_source_certified`
and `conditions_evaluated=false`. No response presents them as certified
quotes or evaluated health, house, dignity, lunar-phase or outcome rules.
Their full textual catalogue certification is outside this numeric/state
admission. No predictive effectiveness, generic interpretation or new score
is claimed. Source publication, package release, deployed REST and website
adoption remain separate from this local implementation.
