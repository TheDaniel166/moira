# Panchanga Shuddhi source-profile standard

**Date:** 9 October 2026. **Owner:** VED-008; `moira/panchanga_shuddhi.py`
and its private bounded-day composer. **Contract:** independent source
restrictions and exceptions, with typed Python and REST access.

The [approved research packet](../06_roadmap/VEDIC_PANCHANGA_SHUDDHI_SOURCE_RESEARCH_2026-10-08.md)
records the inspected editions, pages, private scan hashes, online witnesses
and unresolved readings. The [validation receipt](../03_validation/PANCHANGA_SHUDDHI_VALIDATION_2026-10-09.md)
states what was executed. Existing Tara/Chandra, legacy Yoga/Karana
classification, weighted scores and sampled searches retain their contracts.

## 1. Governing rules

| Profile | Implemented rule and attribution |
| --- | --- |
| `mypanchang_2025_panchaka_30_tithi.v1` | Sum month tithi 1–30, Sunday-first weekday 1–7, Ashwini-first star 1–27 and current Aries-first Lagna 1–12. Modulo 9: 1 Mrityu, 2 Agni, 4 Raja, 6 Chora, 8 Roga; 0/3/5/7 Rahita. Named modern thirty-tithi operational convention; Kalaprakasika offsets independently corroborate the arithmetic. |
| `mc_gochara_13_quarters.v1` | Chintamani Gochara 13 Sanskrit quarter reading: first-cycle Vipat/Pratyak/Naidhana restricted; second-cycle quarters 1/4/3 respectively; third-cycle restriction lifted. Janma remains separately unevaluated, retaining the existing base caution. |
| `ps_sastri_scientific_273_navaka.v1` | Alternative P. S. Sastri textbook p.273 reading: inclusive counts 1,7,12,16,23,25 restricted regardless of quarter. Never merged with the MC rule. |
| `mc_34_35_fixed_ghati_temporal_half.v1` | Initial fixed ghatis: Vishkumbha 3, Atiganda 6, Shula 5, Ganda 6, Vyaghata 9, Vajra 3. Vyatipata/Vaidhriti whole event; Parigha first temporal half. One fixed ghati is 24 minutes; temporal-half conversion is an explicit derived clock. |
| `bs_1946_100_karana_activity.v1` | All eleven Karanas carry historical activity tags from Brihat Samhita 100.1–5, Sastri/Bhat 1946. Vishti prohibits auspicious acts. Kimstughna supports auspicious acts; the fixed Karanas do not receive a universal adverse label. |
| `mc_43_45_bhadra_components.v1` | Chintamani occurrence, current Moon-sign residence and origin-half/day-night exceptions remain separate claims. |
| `mc_44_tithi_eighths_normalized.v1` | Derived mouth/tail clock from MC's eight tithi rows: normalize the full actual tithi to 60 nominal ghatis, intersect with the actual six-degree Vishti event, and retain raw and clipped intervals. |

The full mouth/tail and residence tables are in the source packet and the
independently transcribed test fixture. For tithi start A, duration D, mouth
eighth m and tail eighth q, mouth is `[A+(m−1)D/8, A+(m−1)D/8+D/12)`;
tail is `[A+qD/8−D/20, A+qD/8)`. These normalized ghatis differ from the
fixed Yoga ghatis. A true tithi's two angular halves need not have equal time.

Bhadra residence uses the current sidereal Moon: Earth in Cancer/Leo/Aquarius/
Pisces; heaven in Aries/Taurus/Gemini/Scorpio; underworld in Virgo/Libra/
Sagittarius/Capricorn. Its identity persists outside the Earth group. MC's
latter-half-origin/daytime and former-half-origin/nighttime exceptions use
the actual solar day/night. Neither exception deletes the Vishti prohibition.

## 2. Results and missing inputs

`PanchangaShuddhiAssessment` preserves policy, actual inputs, limb indices and
names, base Tara identity/polarity, Panchaka arithmetic, nine ordered findings,
applied profiles and `simultaneous_bhadra_claims`. Every finding has a rule ID,
source profile, citation, state, nullable `detected`, reasons and intervals.

States distinguish `restricted`, `clear`, `detected`, `exception_applies`,
`not_applicable`, `unavailable`, `not_evaluated` and `uncertain`. `clear` means
this particular restriction is absent. `detected` refers to the named rule:
for `bhadra_earth` it tests Earth residence; for the day/night exception it
tests the exception. Read the rule ID and state together. There is no overall
favorable boolean, universal exception precedence or calculated activity score.
All products carry `activity_suitability="not_evaluated"`.

Missing natal star disables only Tara. Missing weekday/current Lagna disables
only Panchaka. Partial-period Yoga needs a complete Yoga span and instant;
whole-event Yoga identity can be classified without times. Mouth/tail require
the full tithi and Karana spans. Missing daytime evidence disables only its
dependent exception. Selected policy and actually applied profiles are distinct.

Direct inputs are finite sidereal longitudes in `[0,360)`; there is no hidden
ayanamsa conversion. Weekday is **Sunday=0**, natal star **Ashwini=0**.
`panchaka_rahita()` alone deliberately accepts the source's **one-based**
numbers. Booleans, coerced strings, unknown profiles, invalid spans and dates
are rejected. Supplied spans must contain the instant; Karana bounds must lie
inside tithi bounds allowing declared numerical uncertainty. Their astronomical
identity remains caller-owned. Each span is positive and at most three days;
each boundary bracket contains its estimate and spans at most one hour.

## 3. Dated composition and numerical boundaries

`panchanga_shuddhi_for_date()` owns the requested local sunrise through the
following civil date's sunrise. Gregorian dates 2–9998, an explicit IANA or
supported fixed-offset timezone, latitude `(-90,90)` and longitude `[-180,180]`
are required. Skipped civil dates are rejected before reader discovery.

The facade borrows its existing reader. Sun/Moon and Lagna use the same true
ayanamsa policy, default Lahiri; the existing planetary reduction and local
angle engine own astronomy. No reader replacement, download or lifecycle
mutation occurs. The result includes the kernel identity and reader binding.
Day boundaries and all component times are explicitly **Julian UT1**. The
timezone owns the civil date; a UT1 JD must not be relabeled as a UTC timestamp.

The composer refines solar anchors using the selected sunrise convention,
then solves full preceding/following tithi, Karana and Yoga boundaries in
three-day margins around the owned day. Hourly phase discovery uses bounded
adaptive subdivision. Moon quarter crossings include every nakshatra and
Moon-sign change; three-minute adaptive Lagna discovery finds current sign
changes. Derived Yoga/mouth/tail endpoints further subdivide the day. Sampling
labels only intervals whose relevant transitions have already been solved.

Default root tolerance is 0.1 seconds, selectable 0.01–1 second. It bounds
numerical brackets, not source, ephemeris or atmospheric accuracy. Derived
endpoints propagate endpoint brackets using positive affine arithmetic.
Overlapping uncertainty bands merge and retain all boundary reasons.
Intervals own `[start,end)` outside those bands. `day.at(jd_ut1)` returns a
cell's representative assessment, or `None` inside a band/outside the day;
its stored longitudes are the sample's, not recalculated query longitudes.

No sunrise or next sunrise means the day product is `unavailable`; no fixed
24-hour replacement is invented. A missing sunset leaves independent cells
available and the day partial. At/above the ecliptic polar circle, continuous
Lagna timing is explicitly unavailable, while other components remain
available when solar anchors exist. A separately admitted discontinuous
polar-Lagna solver would be needed to widen that component. Ordinary
high-latitude forward motion below that circle is adaptively solved.

Bounds: owned day at most two days; full parent spans at most three days;
search envelope at most eight days; at most 16,384 phase calls per transition
family; 24 adaptive levels, 64 bisections per crossing, and 512 merged bands
(at most 511 cells). Invalid, backward or unresolved phase work fails closed.
The ordinary REST route is synchronous and one-day only; it is not a date-range
search or an unrestricted batch. Resource/coverage failures use existing
Muhurta errors; component absence uses typed successful partial/unavailable
results.

## 4. Python and REST

Sixteen identical owning objects are curated through `moira`, `moira.vedic`
and `moira.facade`: policy, boundary/interval/finding/input/value/assessment,
catalogue entry/catalogue, Panchaka arithmetic result, cell/day, and the four
functions. Three `Moira` methods expose catalogue, direct and reader-bound day.

```python
from moira import panchanga_shuddhi_from_longitudes, PanchangaShuddhiPolicy

assessment = panchanga_shuddhi_from_longitudes(
    0.0, 45.0, weekday=5, lagna_sidereal_longitude=10.0,
    natal_nakshatra_index=0,
    policy=PanchangaShuddhiPolicy(tara_profile="mc_gochara_13_quarters.v1"),
)
assert assessment.values.karana_name == "Vishti"
assert assessment.activity_suitability == "not_evaluated"
```

| Method and path | Contract |
| --- | --- |
| `GET /v1/muhurta/shuddhi/catalogue` | Seven profile receipts, eleven Karana entries and named excluded readings; no kernel needed. |
| `POST /v1/muhurta/shuddhi/direct` | Supplied-input assessment; nested typed boundary spans; no kernel needed. |
| `POST /v1/muhurta/shuddhi/day` | Date/location/timezone, optional natal star and policy; canonical reader-bound day cells. |

Strict requests forbid unknown fields and numeric coercion. Typed responses
preserve the complete canonical dataclass structure; the server performs no
rule or interval arithmetic. Admission classification: `admit_now` for these
bounded source-selected products following the approved research and completed
engine validation. Cancellation, strength and full purpose elections remain
VED-009/010/011. MC Hindi thirds, Raman 3-versus-7 initial ghatis, Sadhana
anatomical variants, ritual remedies and universal Bhadra precedence remain
explicitly excluded readings with source-specific research conditions.
