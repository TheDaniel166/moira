# D60 source, naming and positional admission

Date: 7 October 2026. Status: sign-only, modern composed and classical-derived
full-position profiles locally admitted. Direct classical D60 degree
prescription remains unestablished; it is not an implementation gate for the
explicit derived profile. Owner: `moira.varga`; VED-003 is `LOCAL_COMPLETE`
for the admitted engine/public/REST scope.

## Adjudication

The identified local source is R. Santhanam's *Brihat Parashara Hora Shastra*,
Vol. I, chapter 6, verses 33-41 and commentary, printed p.83 (one-based PDF
p.82). File: `Classics books/BPHS-Santhanam-Vol-1.pdf` within
`C:\dev\ASTROLOGY-BOOKS-DATABASE`; SHA-256
`13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f`.
The rendered page was visually inspected. Its worked example doubles
Capricorn 13 degrees 25 minutes, discards minutes, takes remainder two modulo
twelve and counts the third sign from Capricorn: Pisces. Even-sign reversal
applies to deity names. The passage supplies no continuous D60 degree law.

The [Sanskrit Documents transcription, chapter 6.33-41](https://sanskritdocuments.org/doc_z_misc_sociology_astrology/par0110.html)
corroborates the doubled-degree/remainder operations and named sequence.
Encoding credits name Ahto Jarve; proofreading credits name Ginda Lass and
Abhisyanta Tejaswi. Its exact printed base edition is unestablished, so it is
not treated as an independent critical edition. Verse 39 has a Dandabhrt
reading where the selected Santhanam English list has Dandayudha. This variant
is recorded rather than normalized away.

**Decision:** admit the Santhanam commentary's sign rule as
`bphs_santhanam_sign`. Its worked example and general counting prescription
support a sign algorithm, not a full positional object. Other fixture signs
are explicitly derived from that prescription; they are not additional
published examples. Software outputs provide no missing primary authority.
The [earlier research packet](../06_roadmap/VEDIC_CHARA_D60_SOURCE_RESEARCH_2026-10-07.md)
retains broader edition and Chara provenance.

## Explicit computational objects

For normalized sidereal longitude `L`, natal sign `s=floor(L/30)` and
degrees within sign `d=L-30*s`, the admitted source sign is:

```text
source_sign = (s + floor(2*d)) % 12
```

This is the inclusive count of `(remainder+1)` signs from the natal sign,
forward for both parities. Exact half-degree boundaries belong to the next
segment. The sign-only helper accepts strict finite numeric longitudes,
normalizes circularly and rejects unknown/non-enum Python methods. At the
floating-point corner where modulo of a tiny negative angle rounds to 360,
it uses the nearest representable longitude below 360 to preserve the left
circular limit. This is numerical boundary handling, not a new source rule.

`D60Method.HARMONIC` retains Moira's existing harmonic calculation. Generic
`calculate_varga(L,60)` and named `shashtiamsha(L)` keep their numerical
defaults and full `VargaPoint` results, with `d60_method=harmonic`. Generic D60
keeps `deity=None`; the named wrapper enriches it with the source name table.
Calling a generic result "Shashtiamsha" does not infer enrichment or change
its convention.

`d60_sign(L, method=D60Method.SANTHANAM_SIGN)` returns a frozen
`D60SignResult` with normalized input, sign index, sign/symbol properties,
applied method, `position_scope=sign_only` and the edition-owned source locator.
It has **no** `sign_degree` or `varga_longitude`. Its harmonic option is also
sign-only. Root, facade and Vedic module exports share canonical identities;
`Moira.d60_sign` delegates to the same helper.

`varga_sign_index(...,60,d60_method=...)` and both Vimshopaka helpers accept
the source sign method. A nondefault D60 method for another division or a
group without D60 fails explicitly. Named/full Shodashvarga facade methods
and `shashtiamsha` reject the source-only method before chart/resource work.
A `VargaPoint` receipt cannot label a full position with this sign-only method;
legacy manual results may retain `d60_method=None` as unknown.

## Transport

All eight existing Varga placement routes preserve canonical nullable `deity`
and `d60_method` fields through the shared serializer. Non-D60 points report
no applied D60 method. Seven named/full Shodashvarga request models accept
`d60_method=harmonic|pvr_textbook_linear|classical_derived_linear`; OpenAPI declares that enumeration. Generic requests retain
their original input contract.

`POST /v1/varga/d60/sign` accepts strict finite `sidereal_longitude` and
`method=harmonic|bphs_santhanam_sign|pvr_textbook_linear|classical_derived_linear`, returning a typed sign-only receipt.
`POST /v1/varga/vimshopaka` accepts `d60_method` and returns each planet's
actual applied method, or `null` in groups without D60. Invalid/unknown or
inapplicable selections return HTTP 422. The server does not borrow harmonic
degrees for source-labelled results.

## Four edition-owned name corrections

| One-based ordinal | Previous string | Admitted string |
| --- | --- | --- |
| 6 | `Kindar` | `Kinnara` |
| 37 | `Suddh` | `Sudha` |
| 52 | `Dhannayudh` | `Dandayudha` |
| 59 | `Brahman` | `Bhramana` |

These are substantive corrections against the selected printed list, not
established alternate names. No compatibility alias claims those previous
strings are valid source variants. Downstream exact-string consumers should
migrate these four values; positions and table order are retained. Repeated
names are intentional, so names are not unique ordinal identifiers. The
other entries are preserved; this package is not a critical-edition collation
of every spelling, deity meaning or interpretive effect.

## Strength consequences and closure criterion

D60 weights remain **5.0 in Dashavarga** and **4.0 in Shodashvarga**. Selecting
the source sign can change its lord, compound dignity, contribution and total.
Every other division entry, group weight and D1 friendship convention remains
unchanged. The [validation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
includes an independently calculated Venus example for both groups.

The **direct classical full-degree attribution** question requires an identified passage/edition that
defines continuous degree within the selected D60 sign, including endpoints,
wrap and parity, with source-owned numerical fixtures. A fractional doubled
degree or harmonic remainder is not automatically that law. Only after that
evidence is adjudicated may a method claim a direct classical D60 degree
prescription. This criterion is distinct from admitting the explicitly
classical-derived policy below. Sign admission, arithmetic
tests and deity transport do not close this question or establish predictive
validity.

## Bounded modern full-position profile

`D60Method.PVR_TEXTBOOK_LINEAR` (`pvr_textbook_linear`) composes two identified
primary author prescriptions. Rao's *Vedic Astrology: An Integrated Approach*
(2000), section 6.2.20, printed p.60/PDF p.72, supplies the natal-sign starting
sequence and half-degree partitions. His *Two Novel Transit Principles*,
31 December 2013 version 1, PDF p.2, supplies proportional advancement within
a division. Applying that general rule to these forward-counted equal D60
partitions is an explicit Moira inference and composed profile. It is not a
new reading of the Santhanam passage or a claim about current software settings.
The [research/admission record](../06_roadmap/D60_FULL_POSITION_SOURCE_RESEARCH_2026-10-07.md)
identifies hashes, author revision notices and an arithmetic error in the article.

For normalized sidereal `L`, natal sign `s=floor(L/30)`, `d=L-30*s`, and
zero-based half-degree segment `k=floor(2*d)`:

```text
selected_sign = (s + k) % 12
selected_degree = 60 * (d - 0.5*k)
mapped_longitude = 30*selected_sign + selected_degree
```

Both natal parities count forward for this textbook profile. Even-sign deity
reversal remains a separate Santhanam naming operation. The named point uses
the existing corrected Santhanam table; its positional authorities do not
claim that table is Rao's deity edition. The profile adds no frame conversion
and changes no ayanamsa defaults or other Varga doctrines.

Partitions are half-open: the exact start maps to zero degrees; the exact end
belongs to the next partition, with natal-sign and zodiac wrap. Python input
must be an actual finite int/float without bool/string coercion. Circular
normalization shares `d60_sign`'s left-limit handling. If adding the sign's
origin rounds a mapped left limit to its excluded upper bound, `nextafter`
keeps the mapped longitude inside the selected sign. No epsilon snap region
or source rounding to whole minutes is introduced.

The profile is available through `shashtiamsha`, `Moira.varga_named`,
`Moira.varga_for_chart`, `Moira.shodashvarga`, `Moira.shodashvarga_for_chart`,
and all seven corresponding named/batch/chart REST request shapes. Selection
for another named division fails before chart work. Shodashvarga applies the
choice only to D60. Generic `calculate_varga`/`Moira.varga`/generic REST remain
harmonic with their existing input contract. New-profile direct REST inputs
are strict finite numbers; harmonic input compatibility remains as before.

`VargaPoint.d60_source_references` and `VimshopakaBala.d60_source_references`
are canonical computed receipt properties copied to REST. They identify both
positional sources for this composed profile, `moira_generic_harmonic` for the
default, the Santhanam locator for source sign-based strength, and an empty
tuple/JSON array for non-D60 or unknown manual receipts. `d60_sign` can project
the profile to a sign-only result, whose existing `source_reference` identifies
the sign source alone. No degree is inferred in that sign-only product.

The [validation receipt](../03_validation/D60_FULL_POSITION_VALIDATION_2026-10-07.md)
separates the textbook's published Sagittarius sign, mathematically derived
D60 degrees, the article's conflicting D9 coordinate, its consistent D24
calculation, and unpaired published D60 coordinates. Named modern computation
and [broader computational validation](../03_validation/D60_CROSS_ENGINE_VALIDATION_2026-10-07.md)
are locally complete: 24,432 comparisons against pinned PyJHora full points
and compiled Maitreya sign/intermediate outputs agree within a predeclared
floating-point budget. Offline witnesses cover engine/facade/REST/strength.
This is secondary corroboration, not full-application parity or primary
classical proof. Exact primary-publication planetary D1-to-full-D60 pairs,
current JHora equivalence, a classical continuous-degree passage and predictive
validation are not established by this package. They are optional future
research outside the closed VED-003 implementation scope; its admitted
profiles are `LOCAL_COMPLETE`.

## Earlier bounded evidence review

This section records the earlier, narrower decision. The wider-library
reconciliation below supersedes its refusal to admit a classical-derived
profile; it does not overturn the finding about a direct D60 degree passage.

The [evidence adjudication](../06_roadmap/D60_EVIDENCE_ADJUDICATION_2026-10-07.md)
completes the agreed finite follow-up: Santhanam and Girish Chand Sharma's
identified BPHS editions/commentaries, named Raman/Rath treatments, additional
local chart material and public primary author publications. Sharma's 1999
reprint locates D60 at **7.33-41**, printed pp.130-136/PDF pp.138-144; this
numbering must not be replaced by Santhanam's chapter 6 locator. Its Gemini
26 degrees 31 minutes 54 seconds to Scorpio example and literal sign-table
rows corroborate the selected forward sign rule. The inspected classical
passages establish no continuous mapped-degree prescription.

Rao's 2010 *Padamsas and Transits*, version 2, PDF p.12, publishes an arudha
point at 16 Cancer 17 in D1 and 16 Pisces 37 in D60. The printed input's exact
mapping is 17 Pisces 00. Nearest-minute input/output intervals are compatible;
truncate-to-minute intervals are not. Because the source's rounding rule is
unknown, this is a **conditional rounded mathematical-point witness**, not
an exact planetary oracle, parity coverage or a new runtime tolerance.

The PVR composition remains explicitly Moira-owned and dated. The author's
2012 software change note establishes several alternative D60 definitions;
it does not confirm this composition as his current recommendation. Governing
canonical source references stay the two admitted positional prescriptions;
corroborating validation witnesses are not silently added as computational
authorities. The selected Santhanam deity list remains edition-owned.

**Admission decision:** retain the modern convention; admit no new classical
full-position method. The research pass is complete. Classical continuous
degrees and a qualified planetary full-position oracle are **not established
in the reviewed sources**. Reopening requires the evidence specified in the
adjudication, not additional arithmetic generated from the same chosen rule.

This historical admission decision does not leave computational validation
pending. The executed external corpus and rational checks validate the
declared modern mapping; attribution and exact printed-pair questions remain
distinct source-evidence frontiers.

## Classical-derived full-position profile

`D60Method.CLASSICAL_DERIVED_LINEAR` (`classical_derived_linear`) is admitted
as a complete full-position policy. The [source adjudication](../06_roadmap/D60_CLASSICAL_DERIVED_ADMISSION_2026-10-07.md)
records editions, pages, hashes, source roles and research coverage. Its chain
is BPHS Santhanam 6.33 for D60 partitions/signs; Saravali 3.18 for general
subdivision-coordinate arithmetic; Jataka Parijata III.43 for fractional
subdivision-to-sign correspondence in a D12 timing technique; and Raman's
Prasna Marga V.27-28 notes for explicit continuous Navamsa degrees.

These are not interchangeable authorities. No passage in that chain directly
instructs a continuous D60 degree calculation. **Moira explicitly generalises
proportional progress to the selected half-degree D60 subdivision.** The
resulting coordinates use the same formulas and half-open boundary policy
as the modern profile above, including forward counting in both natal
parities and the separate Santhanam deity reversal. Equal coordinates do not
erase the different attribution.

Admission of this derived category requires a reviewed, edition-labelled
source chain with each passage's actual computational scope, an explicit
derivation and ambiguity policy, independent arithmetic checks, bounded
external corroboration, and public receipts that disclose the derivation.
These requirements are fulfilled by the [execution receipt](../03_validation/D60_CLASSICAL_DERIVED_VALIDATION_2026-10-07.md).
The stricter direct-text attribution criterion above remains intact.

The profile works through scalar `shashtiamsha`, sign projection, all named
and Shodashvarga facade/chart methods, all seven named/batch/chart REST shapes,
and D60-containing Vimshopaka groups. Generic methods and omitted selectors
retain harmonic behavior. Both full source profiles reject bool, string and
nonfinite direct inputs; unknown or inapplicable selectors fail before chart
work. Sign-only `bphs_santhanam_sign` remains available as the source's bounded
computational object and cannot construct a full point.

`VargaPoint.d60_degree_attribution`, copied to REST, is `generic_harmonic`,
`modern_composed`, `classical_derived`, or null for non-D60/unknown manual
metadata. It describes the angular coordinate, not a strength calculation.
`d60_source_references` preserves the reviewed chain plus the explicit
`Moira:D60:classical-derived-proportional:v1` derivation locator. The PVR
profile retains exactly its two positional locators. The sign projection's
single source locator identifies BPHS Santhanam; it claims no degree.
Vimshopaka preserves the selected policy receipt while using only its sign.
Its strength weights are not the authority for proportional angular degrees.

The classical-derived implementation and its validation are complete locally.
Direct classical D60 prescription, an exact published planetary D1/full-D60
pair, and predictive validity are separate, unclaimed historical/empirical
questions, not unfinished engineering steps for this admitted policy.
