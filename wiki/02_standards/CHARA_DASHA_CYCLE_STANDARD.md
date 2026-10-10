# Bounded Chara Dasha cycle standard

Date: 7 October 2026. Status: locally admitted existing Moira formulation;
source limits remain explicit. Owner: `moira.jaimini_extended`; VED-001.

## Object and source boundary

`chara_dasha` returns twelve or twenty-four consecutive mahadashas from a
caller-supplied sidereal chart and Julian-day epoch. The profile identifier is
`moira_kn_rao_existing_v1`. This identifies the retained implementation; it
does not certify every rule as a completely collated Rao edition.

K.N. Rao's [Chandrasekhar article](https://www.journalofastrology.com/article.php?article_id=315)
reports Aries two years and Taurus twelve years in the second cycle, matching
their first-cycle durations. It supports a partial repetition witness. The
local article compilation, PDF pages 13-14, was previously misattributed to
*Predicting Through Jaimini's Chara Dasa*. The correction and corpus identities
are in the [research packet](../06_roadmap/VEDIC_CHARA_D60_SOURCE_RESEARCH_2026-10-07.md).
Neither that example nor regression tests prove a universal complete repeated
cycle. Narayana Dasha rules are not imported into this profile.

## Inputs and arithmetic

`cycles` is an actual Python integer `1` or `2`, default `1`. Booleans, numeric
strings, integral floats, zero, negatives and later cycles fail explicitly.
REST exposes the same bound at `POST /v1/jaimini/extended/chara-dasha`; invalid
types/ranges return the standard HTTP 422 validation envelope.

The engine requires exactly Sun, Moon, Mars, Mercury, Jupiter, Venus and
Saturn. All longitudes, Lagna and the epoch must be finite Python integer or
float values without coercion. Longitudes retain existing circular reduction.
An omitted or `None` node map selects classical lords. A supplied map requires
exactly Rahu and Ketu with finite values; an empty or partial map fails before
period computation. The epoch remains a caller-owned Julian-day coordinate:
the helper does not infer civil date, timezone, UTC, UT1 or TT. A finite epoch
too large to represent strictly ordered intervals also fails explicitly.

The retained sequence direction uses the ninth sign from Lagna's savya group.
Duration counts from each dasha sign to its lord in the existing sign-owned
direction, minus one; an own-sign lord yields twelve years. There is no
exaltation/debilitation adjustment. Antardashas are twelve equal parts in the
sequence direction, starting after the dasha sign and ending with that sign.
All spans use the fixed Julian year of **365.25 days**.

With nodes supplied, Scorpio and Aquarius use the existing Moira co-lord
branch: both lords in the sign gives twelve years; one in the sign counts to
the other; neither in the sign selects by classical-body companions, then
dual over fixed over movable modality, then degree, with a primary-lord exact
tie. This complete chain remains an implementation convention awaiting full
source collation. Changing it requires a separately admitted formulation.

Cycle two repeats the first twelve sign/year/lord choices and follows cycle
one continuously in time. One/two is an admission bound, not a doctrine that
all traditions prohibit later cycles.

## Canonical receipt and compatibility

The frozen `CharaDashaComputation` records `cycle_count`, `lord_mode`,
`formulation_id`, `cycle_policy=repeat_first_cycle`, `year_basis=julian_365.25`,
`year_days=365.25` and `epoch_basis=caller_supplied_julian_day`.
`CharaDashaResult.period_count` derives from the actual period tuple. A supplied
receipt requires exactly twelve times its cycle count. Engine calls always
return the receipt; REST copies it without reconstructing doctrine.

The original five positional result-constructor fields remain valid;
`computation=None` means legacy/manual metadata is unknown. The original
default period arithmetic is retained. Strict invalid-input rejection,
corrected lineage/lord-note wording and additive JSON receipt fields are
intentional compatibility changes. Root, facade and `moira.vedic` expose the
same canonical metadata class.

## Evidence and remaining work

The [implementation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
records interval, direction, all retained co-lord branches, published-duration
scope, hostile-input, export and HTTP checks. These distinguish implementation
invariants from source authority. Full Rao book/complete-cycle collation,
alternate lineages, other year bases and later cycles remain separate research
work under VED-013/021. Predictive validity is not established by arithmetic.
