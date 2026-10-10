# Muhurta dosha and Parihara standard

**Date:** 9 October 2026. **Owner:** VED-009, `moira/muhurta_dosha.py`
and its private dated composer. This contract admits six source-selected
restrictions and three opt-in exceptions across Python and REST.

The [source record](../06_roadmap/VEDIC_DOSHA_PARIHARA_SOURCE_AND_PLAN_2026-10-09.md)
identifies inspected editions, printed/file pages, scan hashes, table
disagreements and derived interpretations. The
[validation receipt](../03_validation/MUHURTA_DOSHA_VALIDATION_2026-10-09.md)
separates textual, numerical and transport evidence.

## 1. Finite source policy

| Policy field / profile | Admitted meaning |
| --- | --- |
| `vishanadi_profile="mc_vivaha_49_51.v1"` (default) | MC Avasthi 2004, Vivaha 49-51, all 27 stellar offsets; Mula 56, Purva Bhadrapada 16. |
| `kp_185_single_mula.v1` | Kalaprakasika, Iyer 1982, printed 185 main table; Mula 20, Purva Bhadrapada 6. Other offsets agree with MC. |
| `kp_185_dual_mula.v1` | KP main table plus its separately stated Mula alternative: retain both windows at 20 and 56. |
| `vishanadi_clock="mc_avasthi_scaled_start_fixed_width.v1"` (default) | Avasthi's commentary and worked Rohini example: scale the start by the actual star duration; retain four fixed ghatis of width. |
| `normalized_nakshatra_sixtieths.v1` | Explicit derived alternative: scale both start and width by the actual duration. It is not attributed to Avasthi's worked example. |
| `gandanta_profile="mc_vivaha_43_fixed_ghati.v1"` (default) | Each side of the selected join: nakshatra 2 ghatis, tithi 1 ghati, Lagna 0.5 ghati. |
| `bphs_santhanam_92_fixed_ghati.v1` | Santhanam II 92.2-4: nakshatra 2 ghatis, tithi 2 ghatis, Lagna 0.5 ghati on each side. |
| `mc_shubhashubha_9_yamaghanta.v1` | Weekday/nakshatra pair; Sunday-first one-based stars 10,16,6,19,3,4,13. |
| `mc_shubhashubha_37_sixteenths.v1` | Daytime Yamaghanta, distinct from the weekday/star yoga. Sunday-first one-based daylight sixteenths 10,8,6,4,2,14,12. No nighttime extension. |

One fixed ghati is 1,440 seconds (24 minutes). For parent start A, duration D
in UT1 days and table offset q, Vishanadi starts at `A+q*D/60`. The default
ends four fixed ghatis later (`+4/60` days); the alternative ends at
`A+(q+4)*D/60`. Fixed-width windows may continue into the next star; they
retain their original parent identity and are never clipped to that star.
All offsets are elapsed ghatis, not one-based ordinal numbers.

Gandanta joins are Ashlesha/Magha, Jyeshtha/Mula, Revati/Ashwini;
Cancer/Leo, Scorpio/Sagittarius, Pisces/Aries for Lagna; and the last/first
portions around every fifth tithi. Both full- and new-moon joins are included.
Temporal windows use solved parent events, never a fixed-degree substitute.
Clip to the parent when it is shorter than the declared width, retaining both
`window` and `unclipped_window` as evidence.

## 2. Cancellation is a separate, opt-in finding

`parihara_profiles=()` is the default. Selecting a profile never deletes the
restriction, alters its source, or implies overall suitability.

| Optional profile | Exact scope and prerequisites |
| --- | --- |
| `kp_195_seven_star_tyajya_exemption.v1` | KP tables only. Witness parent is Ardra, Shravana, Mrigashira, Swati, Uttara Ashadha, Rohini or Anuradha. Parent identity survives any carryover. The same exception is excluded for the MC table. |
| `mc_shubhashubha_37_necessary_first_half.v1` | Daytime Yamaghanta only. Caller explicitly declares `necessary_activity=True`, and instant is within the first temporal half of that sixteenth. Missing necessity is unknown, not affirmative. It never cancels weekday/star Yamaghanta. |
| `mc_avasthi_vivaha_43_abhijit.v1` | Avasthi's **commentary**, not the Sanskrit verse. MC Gandanta only, during `[sunrise+7*daylight/15, sunrise+8*daylight/15)`. It is excluded for the BPHS profile. This geometric exception does not alter the existing named-Abhijit Wednesday eligibility rule. |

Each `PariharaEvidence` carries its profile, retained witness index, source
citations, optional window and named nullable prerequisites. Its state is
`not_selected`, `excluded`, `not_applicable`, `not_satisfied`, `unavailable`,
`uncertain` or `applied`. All prerequisites and the restriction witness must
be affirmative before it can be `applied`. `uncertain` retains numerical-band
ambiguity; `unavailable` identifies missing prerequisites. Both retain nullable
truth values and their supporting evidence. An explicitly false prerequisite
establishes `not_satisfied` even when another prerequisite is unknown.

## 3. Input and result ownership

`detect_muhurta_doshas(sun_sidereal_longitude, moon_sidereal_longitude, *,
jd_ut1, weekday=None, lagna_sidereal_longitude=None, phase_spans=(),
sunrise_day=None, sunset=None, necessary_activity=None, policy=None)` is
kernel-free. Longitudes are finite sidereal degrees in `[0,360)`; the direct
method does not convert frames. Indices are zero-based: Sunday=0, Ashwini=0,
month tithi=0..29, Aries=0. The weekday belongs to the owning sunrise date.

Optional `DoshaPhaseSpan(kind, index, interval)` accepts nakshatra, tithi or
Lagna full parents with immutable `ShuddhiInterval`/`ShuddhiBoundary` UT1
endpoints. Per-family spans must be ordered, contiguous and consecutive,
cover the instant and include its supplied longitude's possible parent.
Endpoint brackets must be separated. Astronomical identity remains
caller-owned: structural checks cannot certify supplied roots. At most 64
spans are accepted, each at most three days, with at most one hour of
uncertainty per boundary. The sunrise interval is at most two days, contains
the instant and strictly encloses the sunset brackets when sunset is supplied.

Fixed-width Vishanadi requires enough preceding parent context to exclude
96-minute carryover. Missing context makes absence unknown. A currently
affirmative witness can still establish detection, while incomplete coverage
prevents an unwarranted affirmative neutralization. Missing temporal Gandanta
evidence disables that restriction if the current identity is relevant;
an unrelated star/tithi/sign can still establish its absence. Missing Lagna
longitude leaves Lagna Gandanta unavailable.

Every assessment contains six ordered `MuhurtaDoshaFinding` results,
policy, actual inputs, source/clock citations and excluded rule identifiers.
`detected` and `neutralized` are independent nullable booleans:

- `clear`: the selected restriction is absent; both booleans are false.
- `detected`: at least one raw witness is affirmative; neutralization is
  false or unknown according to the separate exception evidence.
- `neutralized`: detected remains true and every potentially active witness
  has an affirmative in-scope exception, with no missing coverage.
- `uncertain` / `unavailable`: detection is unknown because of numerical
  bands or missing required evidence respectively; neutralization is unknown.

All products carry `activity_suitability="not_evaluated"`. The package does
not replace existing legacy Gandanta, Tara/Chandra, Shuddhi, weighted-score
or sampled-search contracts.

## 4. Reader-bound sunrise day

`muhurta_doshas_for_date(local_date, latitude, longitude, *, timezone,
necessary_activity=None, policy=None, reader=None)` accepts Gregorian years
2..9998, latitude `(-90,90)`, longitude `[-180,180]` and an explicit supported
timezone. Invalid/skipped civil dates fail before reader discovery. The
facade borrows its existing reader; standalone calls require an explicit
reader or active reader context. Caller readers are never closed or replaced.

Policy admits the existing named ayanamsa registry (default Lahiri), the
existing three sunrise conventions (default Rashtriya upper limb), and root
tolerance 0.01..1 seconds (default 0.1). True sidereal Sun/Moon and local
Lagna use the same frame. Solar anchors reuse the named-Muhurta owner.
The requested local sunrise through the next civil date's sunrise owns the
product; no missing-sunrise 24-hour fallback is invented.

Full Moon/tithi parents are searched within three days on either side;
Lagna parents within one day. Discovery steps are one hour and three minutes
respectively, with at most 24 adaptive subdivisions, 64 bisections per root
and 16,384 phase evaluations per family. Invalid/nonmonotonic signals or
unresolved full events fail rather than publishing sampled boundaries.
Cells split at all astronomical, restriction and selected exception edges.
At most 512 merged transition bands and 511 cells are returned.

Root endpoints retain numerical lower/upper brackets. Exact endpoints obey
`[start,end)`; nonzero uncertainty bands make no categorical claim.
`day.at(jd_ut1)` returns a **representative cell assessment**, whose input
instant remains its original interior sample, or `None` outside coverage/in
an uncertainty band. It does not recompute positions at the query instant.
Membership states are constant within the cell outside the boundary bands.

Day status is `available`, `partial` or `unavailable` with explicit reasons.
Missing owned sunrise(s) prevents a day. Missing sunset disables dependent
windows. At/above the ecliptic polar circle, Lagna timing is unavailable while
other components remain evaluated. Selecting the necessary-work exception
without declaring necessity produces a partial result. Kernel identity and
reader binding are retained. UT1 JDs are not relabeled as UTC timestamps.

## 5. Public and REST contracts

Fifteen identical owning exports are curated through `moira`, `moira.vedic`
and `moira.facade`: twelve policy/evidence/day vessels plus the catalogue,
direct and dated functions. `Moira` exposes those same three operations.

| Route | Contract |
| --- | --- |
| `GET /v1/muhurta/doshas/catalogue` | Twelve named profile records, six detectors and explicit exclusions; kernel-free. |
| `POST /v1/muhurta/doshas/direct` | Pure supplied-input assessment. |
| `POST /v1/muhurta/doshas/day` | Synchronous read-only one-day composition using the serving engine's reader. |

Models reject unknown fields, unnamed/duplicate profiles, numeric booleans,
coerced numeric strings, non-finite numbers, malformed dates and contradictory
nested spans before resource work. Typed responses preserve every engine
witness, predicate and nullable field. Serializers project dataclasses and
do not recompute astrology. Invalid inputs return the canonical 422 envelope;
coverage failures use `muhurta_date_outside_coverage`, missing resources use
503 `muhurta_resource_unavailable`, with the existing request-ID contract.

This minimal example intentionally omits temporal evidence; it demonstrates
identity detection without claiming that every component was evaluated:

```python
from moira import detect_muhurta_doshas, muhurta_dosha_catalogue

catalogue = muhurta_dosha_catalogue()
assert len(catalogue.profiles) == 12
result = detect_muhurta_doshas(0.0, 45.0, jd_ut1=2451545.0, weekday=5)
yama = next(f for f in result.findings if f.rule_id == "yamaghanta_yoga")
assert yama.detected is True and yama.neutralized is False
assert result.activity_suitability == "not_evaluated"
```

## 6. Explicit remaining scope

This admission completes the finite six-detector/three-exception package.
Weekday/tithi/sign Tyajya, Abhukta Mula, angular Gandanta variants, the full
twenty-one-dosha catalogue and universal auspicious-yoga precedence remain
research extensions. Planetary strength/aspect/Navamsa-dependent exceptions
belong to VED-010; complete purpose elections belong to VED-011. Ritual
performance and predictive efficacy are not inferred from computed windows.
These exclusions do not assert that classical sources are unavailable.
