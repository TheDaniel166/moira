# P13-U1 — Western Electional Doctrine Research Dossier

Version: 0.14 (first complete matter profile admitted)
Date: 2026-07-15
Status: research inventory for the Western electional doctrine layer. The
companion materials admit distinct `ramesey_moon_condition_v1` and
`sahl_moon_condition_v1` and `dorotheus_moon_condition_v1` objects through the
engine module, package root, facade, `Moira` convenience methods, and bounded
single-moment REST routes.
The shared `dorotheus_rooted_context_v1` object is also public through engine,
facade, and `POST /v1/electional/western/dorotheus-rooted-context`.
`dorotheus_construction_v1` composes the V.2-V.6, V.31, and V.7 construction
layers through the same public ladder and
`POST /v1/electional/western/dorotheus-construction`. It is complete as a
source-layer matter profile, but not numerically complete: the primary text
does not supply enough semantics to compute increasing-in-calculation or an
ecliptic-crossing region/tolerance. Generic search, scoring, website, advice,
and recommendation surfaces remain deferred.

Changelog:
- 0.14 - page-confirmed Dorotheus V.2-5, V.7, and the edition glossary entry
  for increasing/decreasing in calculation; admitted the non-scored
  `dorotheus_construction_v1` matter profile through engine, facade, and REST.
  The lunar equation and ecliptic-crossing clauses remain visible and
  `not_evaluable`, so source completeness is not mislabeled as numerical
  completeness.
- 0.13 - page-confirmed Dorotheus V.6.21-31 and V.31.1-11, admitted the
  non-scored rooted context preserving Moon-as-root, Moon-sign-lord-as-outcome,
  sign-bounded next connection, six matter-significator families, and explicit
  ephemeral/radical natal contracts. V.31's undefined "bad place" and broader
  "made unfortunate" semantics remain visible uncomputed requirements.
- 0.12 - re-rendered Dorotheus V.6.3-15 and the edition glossary, admitted the
  distinct eleven-rule `dorotheus_moon_condition_v1` engine/facade/REST
  profile, and preserved the southern-descending and longitude-or-latitude
  disengagement clauses as measured but `not_evaluable` rather than importing
  later node or connection orbs.
- 0.11 - page-confirmed Sahl section 22 and the supporting glossary mechanics,
  admitted a distinct non-scored `sahl_moon_condition_v1` engine/facade/REST
  profile, and preserved the burnt-path and Latin/Arabic eighth-rule
  divergences as visible named policies rather than merging them into Ramesey.
- 0.10 - admitted the bounded first-profile public moment surface through the
  curated root, facade, `Moira.ramesey_moon_condition_at(...)`, and
  `POST /v1/electional/western/ramesey-moon-condition`. The transport preserves
  every rule/remedy witness and explicitly provides no score, search
  integration, advice, recommendation, or remedy-fulfillment assessment.
- 0.9 - page-confirmed the p. 127-128 urgent-time contingency, added a
  separate non-erasing remedy instruction witness, full-zodiac generative and
  sign-boundary invariants, and an independent DE441 forward-VOC geometry
  covenant. The five-axis audit passes for module admission. Wider transport
  and publication remain separately deferred.
- 0.8 — resolved the nine Ramesey profile policies from the original 1654
  facsimile (Book II planetary orbs, terms, nodes, aspects/houses/VOC; Book III
  p. 127 checklist), admitted the non-scored module-level engine profile, and
  added source-bound boundary and compound-rule tests. The generic electional
  search transport remains unchanged.
- 0.7 — created `P13-U1_WESTERN_ELECTIONAL_DOCTRINE_PACKET.md` and visually
  page-confirmed the first profile against Ramesey's original facsimile,
  Book III, Chapter II, printed pp. 126–127. Corrected the former blended
  Ramesey/Robson checklist to Ramesey's actual order and compound rules.
  Visually confirmed the comparison lists in Sahl §22, printed pp. 99–101,
  and Dorotheus V.6, printed pp. 234–235. Corrected the false claim that the
  three lineages share one via-combusta boundary and separated Dorotheus's
  under-rays condition from his distinct slow-Moon rule.
- 0.6 — both primary-lineage rule inventories now complete companions:
  `P13-U1_DOROTHEUS_BOOK_V_RULE_INVENTORY.md` (Book V, all chapters) and
  `P13-U1_SAHL_ON_ELECTIONS_RULE_INVENTORY.md` (Dykes §§1–143, houses 2–12 +
  §143). §12 updated: Sahl is no longer transcription-pending; remaining thin
  item is conditional term-table reproduction only. Named Sahl variants
  captured (slow Moon 12°/day; beams 12°; burnt path end-Lib/begin-Sco; VOC as
  10th impediment).
- 0.5 — closed the last true acquisition gap: Dykes *Choices & Inceptions:
  Traditional Electional Astrology* is on disk and contains **Sahl bin Bishr,
  On Elections** (complete elections, house-by-house from printed p. 91), plus
  al-Kindī / Bethen / al-ʿImrānī / al-Rijāl electional material. §12 rewritten:
  no remaining source-acquisition blockers; Sahl per-chapter rules are now a
  transcription task against the text in hand (parallel to remaining Dorotheus
  Book V topics). Citation home for Sahl elections is this anthology, not only
  *Astrology of Sahl b. Bishr, Vol. I*.
- 0.4 — transcribed the **complete** Dorotheus Book V (all 44 chapters) at rule
  level into the companion `P13-U1_DOROTHEUS_BOOK_V_RULE_INVENTORY.md`: general
  doctrine (sign-nature V.2–5, corruption-of-the-Moon V.6, significator-of-
  matter V.31) plus every matter chapter with gates/fortifiers/sign-tables,
  election-vs-horary flags, and an engine-mapping synthesis that surfaces 6 NEW
  substrate needs beyond the §10 unlocks (ascensional-sign computation,
  twelfth-parts, bound/term tables, node longitudes+latitude, melothesia table,
  besiegement, and the natal-overlay/rootedness upgrade). Corrected the §8.1
  chapter map (V.10–13, V.19, V.25 were missing). Captured the Dorothean named
  variants: slow-Moon **12°/day**, via combusta = **whole Libra+Scorpio**.
- 0.3 — corrected a false gap claim: the Dykes ʿUmar al-Tabarī *Carmen
  Astrologicum* (2nd ed.) is held on disk, so Dorotheus Book V (the full
  matter-specific inception corpus, pp. 231–330) is a PRIMARY SOURCE IN HAND,
  not a "source unavailable" gap. Added the Book V chapter map and the
  surgery/medical rule set (§8.1), a primary-texts-on-disk register (Appendix),
  and rewrote §12: only Sahl's *On Choices* remains a true acquisition gap.
- 0.2 — closed the §12 research gaps via a targeted primary/secondary follow-up
  pass: full Lilly debility + accidental-dignity point table (§B.2, §B.4),
  oriental/occidental parameters (§B.3), the five aspect-perfection doctrines
  with mechanics (§C.2), the almuten figuris algorithm (§B.4), Bonatti
  consideration count resolved to 146 (§1), and the Lilly combustion/under-beams/
  cazimi reconciliation (§B.1). Remaining thin spots narrowed in §12.
- 0.1 — initial synthesis from the recovered deep-research corpus.

## 0. Purpose And Standing

This dossier is the primary-source research foundation used by the Phase 13
doctrine packet and its first bounded engine profile. The original ledger
named the missing pieces explicitly: "doctrine note for
Western electional scope, rule/profile vocabulary, judgement boundaries and
public-language policy, validation strategy for any built-in score, separation
between search infrastructure and electional doctrine."

This document supplies the **rule/profile vocabulary** and the **named-lineage
citation base** for that packet. Admission authority and current boundaries
live in the packet; this dossier defines no public score.

It is organized as an *implementable rule inventory*: each rule carries its
authority, citation, exact parameters, its variants across lineages, its
implementation shape (boolean gate / weighted factor / matter-specific / classifier),
and a research-confidence tier. It deliberately preserves doctrinal divergences
as distinct named variants rather than collapsing them — per the Moira Law of
Semantic Honesty and Part V sovereignty law, competing definitions are the
product, not noise to be averaged away.

## 0.1 Provenance And Confidence Discipline

This dossier was produced by a fan-out deep-research pass (5 search angles, 23
fetched sources, 101 extracted claims with verbatim quotes). An adversarial
3-vote verification stage began but was interrupted by an account spend limit
after 25 of 101 claims. Confidence tiers below reflect that honestly:

- **[V+]** — verified by the adversarial panel (2–3 confirming votes).
- **[V-]** — one claim was panel-*refuted* as stated; retained only as a
  corrected/annotated entry, never as a flat rule.
- **[Q]** — extracted with a direct primary/secondary-source quote but the
  verification vote could not run (spend limit). Quote-grounded, not yet
  panel-checked.
- **[S]** — secondary/tertiary synthesis (blog, podcast transcript, forum) with
  a quote but weaker source authority.

No rule here should enter a doctrine packet on this dossier alone. Every rule
destined for implementation must be confirmed against the **named primary text
at the cited page** before it becomes doctrine. Where a value is safety- or
score-critical (orbs, thresholds, point weights), the primary-text check is
mandatory, not optional. This is research scaffolding, not a validation
receipt.

---

## 1. The Named Lineage Chain

The electional corpus is a single transmission chain, and the implementation's
vocabulary should name the link each rule comes from rather than flattening
everything to "traditional."

| Lineage node | Authority | Work / citation base | Role in the chain | Citable modern edition |
|---|---|---|---|---|
| Hellenistic root | Dorotheus of Sidon (1st c. CE) | *Carmen Astrologicum*, Book V (elections/inceptions), pp. 231–330 | Oldest electional treatise; general + matter-specific split | Dykes trans. from ʿUmar al-Tabarī's Arabic, 2nd ed. — **held on disk** [V+]; supersedes Pingree 1976 |
| Hellenistic parallel | Hephaistion, Antiochus, Porphyry, Rhetorius, Firmicus | — | Applying-aspect void doctrine; solar-proximity thresholds | Schmidt / secondary [S] |
| Persian/Arabic transmission | Sahl ibn Bishr (early 9th c., Baghdad) | *On Choices* (= On Elections) | Adds void-of-course; whole-sign aspect + moiety-conjunction doctrine | Dykes, *Choices & Inceptions* (On Elections, from p. 91); also *Astrology of Sahl b. Bishr, Vol. I* [V+] |
| Medieval synthesis | Guido Bonatti (13th c.) | *Liber Astronomiae* / *146 Considerations* / *On Elections* | Consideration-level rule corpus; asymmetric combustion orbs | Dykes trans.; Lilly/Coley trans. of Considerations [Q] |
| Early-modern English | William Lilly (1647) | *Christian Astrology*, Books II & III | Sign-bounded void; radicality; dignity point scores | astrologiahumana.com CA facsimile PDF [Q] |
| Early-modern English | William Ramesey (1653) | *Astrologia Restaurata*, Book 3 (elections) | Ten-impediment Moon checklist; the most systematic electional gate list | renaissanceastrology.com (Warnock transcription) [V+] |
| Modern synthesis | Vivian Robson (1937) | *Electional Astrology* | Consolidates the whole tradition; radical/mundane/ephemeral taxonomy | iapsop.com full PDF [Q] |
| Modern practitioner | Christopher Warnock; Benjamin Dykes | Renaissance Astrology; translations | Warnock organizes matter-specific elections around Ramesey + Lilly | renaissanceastrology.com [Q] |

Primary-source key quote for the chain (Dorotheus → Sahl): Dorotheus "formed
the basis of many works on nativities, inceptions or elections, and questions,
such as … the books of Sahl b. Bishr." [Q]

---

## 2. The Three-Class Electional Taxonomy

Robson's top-level classification is the natural top of the profile vocabulary,
because it determines *whether the natal chart is even in scope*:

| Class | Definition | Natal chart required? | Implementation shape |
|---|---|---|---|
| **Radical election** | Elected against the elector's natal chart | Yes — rootedness mandatory | Requires natal input; two-chart evaluation |
| **Mundane election** | Conditioned on prevailing mundane/ingress charts | No (uses world charts) | Out of current engine scope |
| **Ephemeral election** | Chosen purely from event-moment positions (future-dated horary) | No | **Maps directly to the existing scan engine** |

Key consequence for Moira: **the current `moira.electional` scan engine is an
ephemeral-election engine.** It evaluates event-moment chart states with no
natal chart. That is a legitimate, named, self-sufficient electional class —
not a deficiency. Radical elections are a *superset* feature (add a natal
chart + rootedness gate), not a correction. This lets the suite ship ephemeral
doctrine first and add radical rootedness as a bounded extension. [Q, S]

---

## 3. Rule Family A — Moon Condition (the core of electional judgement)

The Moon is the primary electional significator across every authority. Ramesey
and Robson both present a **canonical ten-item impediment checklist**, which is
the single best skeleton for a Moira "Moon condition" profile family. The two
lists agree closely, giving strong cross-lineage corroboration.

### A.1 Ramesey's ten impediments, page-confirmed

Ramesey (*Astrologia Restaurata*, Book III, Chapter II, printed pp. 126–127)
says there are ten ways the Moon may be impedited. The original 1654 facsimile
was rendered and visually checked on 2026-07-14 (PDF pp. 184–185). Printed
p. 127 gives this order and wording [V+]:

| # | Impediment | Source-faithful parameter | Shape |
|---|---|---|---|
| 1 | Combust the Sun | Within **12°** of the Sun before or after conjunction; applying is worse than separating | Gate + directional modifier |
| 2 | Degree of fall | The **third degree of Scorpio** | Gate; admitted ordinal interval `[2°, 3°)` |
| 3 | Opposition of the Sun | Opposition; Ramesey gives **no 12° opposition orb here** | Gate; admitted Ramesey combined moieties |
| 4 | Joined with infortunes or in quartile/opposition to them | Conjunction, square, or opposition with Saturn or Mars | Compound gate; admitted Ramesey combined moieties |
| 5 | Near the lunar nodes | Within **12°** of the Head or Tail of the Dragon | Gate; admitted true ecliptic-crossing node + opposition |
| 6 | Latter degrees with an infortune | In the terminal malefic term printed in Book II pp. 71–72; Leo excepted | Gate; admitted profile-local terminal-term table |
| 7 | Cadent **or** via combusta | Cadent from angles **OR** last 15° Libra / first 15° Scorpio; the latter is called the worst, especially for marriage, women's matters, buying/selling, and travel | Compound gate + matter metadata |
| 8 | Detriment **or** not beholding her house suitably | Capricorn, **OR** quartile to her own house, **OR** not beholding it by sextile/trine | Compound gate; admitted whole-sign relationship to Cancer |
| 9 | Slow in motion | Less than **13°10′36″ per 24 hours** | Strict numeric gate |
| 10 | Void of course | In a sign and “beholds not any Planet till she enter another sign” | Admitted traditional-planet, exact-perfection, sign-bounded gate |

Robson (1937) supplies a close later checklist [Q], but it is a named
corroborating variant rather than permission to rewrite Ramesey's list. The
previous dossier table did exactly that: it reordered the rules, separated
Ramesey's compound clauses, omitted his latter-degrees rule, and attached a
12° opposition orb not stated on the governing page. The doctrine packet now
uses the page-confirmed Ramesey list.

The companion packet v0.2 records the Book II derivation that closes the orb,
node, degree-label, house/cadency, latter-degree, speed-product, endpoint, and
VOC policies for `ramesey_moon_condition_v1`. Those decisions belong to that
named profile and do not silently change the variants below.

### A.2 Void of Course — the central doctrinal divergence

This is the rule an implementation **must not collapse**. There are at least
three (arguably four) historically distinct, individually citable definitions.
They produce wildly different frequencies (Hellenistic: ~1–2×/year; sign-bounded:
several×/month), so they are not interchangeable.

| Variant name | Definition | Sign boundary? | Orb? | Lineage / citation | Tier |
|---|---|---|---|---|---|
| **Hellenistic** | Moon completes no exact Ptolemaic aspect within the **next 30°** of motion | Ignored | No | Antiochus, Porphyry, Rhetorius, Firmicus [S] |
| **Medieval / sign-bounded perfection** | Moon completes no aspect **before leaving its current sign** | Yes | No (perfection-based) | Named interpretive family across medieval and later authorities; source-specific mechanics still require confirmation [Q/S] |
| **Ramesey sign-bounded beholding** | No exact Ptolemaic aspect perfection to a traditional planet before the Moon leaves its sign | Yes | No (perfection-based) | Ramesey, Book II p. 111 and Book III p. 127; admitted profile policy [V+] |
| **Lilly (moiety-applying)** | Moon is separated and **applies to no planet within joint moieties while in the sign** (application, not perfection) | Yes | Yes (summed moieties) | Lilly CA; Sue Ward's reading traces it to Sahl [Q/S] |
| **Sue Ward modern** | Moon not **within orb (~≤10°)** of its next applying major aspect, sign boundary ignored | No | Yes | Ward 1995 reinterpretation [S] |

Companion distinctions that must remain separate flags, not folded into VOC:

- **Feral / "Desart"** (Bonatti): Moon makes *no* contact throughout the entire
  sign — distinct from void, which is only "separated and not yet applying." [Q]
- **Lilly's four exception signs**: a void Moon "yet somewhat she performs" in
  **Taurus, Cancer, Sagittarius, Pisces** — a *mitigation* clause, so in the
  Lilly variant VOC is a graded penalty, not a hard kill. Houlding traces this
  mitigation to **Bonatti's 64th consideration**. [V+ for the four signs / Q for lineage]
- **Purpose inversion**: modern electional practice deliberately elects a void
  Moon for matters meant to "come to nothing." So VOC is a *signed* factor whose
  desired direction depends on the election's intent. [S]

**Doctrine implication:** VOC must be a named-variant parameter
(`void_of_course_variant ∈ {hellenistic, medieval_sign_bound,
ramesey_sign_bound_beholding, lilly_moiety, ward_orb}`),
never a single boolean. This is the flagship example of Part-V variant
preservation for the whole suite.

### A.3 Via Combusta

The primary texts do **not** establish one cross-lineage boundary:

- **Ramesey:** last 15° Libra through first 15° Scorpio (printed p. 127) [V+].
- **Sahl:** “the end of Libra and the beginning of Scorpio,” without numeric
  endpoints in §22d (printed p. 100) [V+].
- **Dorotheus:** “Libra and Scorpio” in V.6.12 (printed p. 234), which the
  inventory preserves as a whole-sign Dorothean reading [V+].
- **Bonatti/Robson:** retain their own cited variants until their governing
  pages are confirmed.

Ramesey calls the via-combusta clause the worst impediment, especially for
**marriage, women's matters, buying/selling, and travel/journeys**. This is
matter-specific severity metadata, not a numeric weight. Ramesey's node and
third-degree-of-Scorpio rules are separate numbered impediments; they are not
part of the via-combusta boundary.

Some later sources give via combusta as a flat 15–15 band;
Lilly separately warns against the Moon "in the later degrees of any sign,
especially Gemini, Scorpio, Capricorn" as a distinct rule. [Q]

### A.4 Lunation-cycle / "Combust Hours" (Robson)

A time-since-syzygy rule, distinct from body-combustion:

- First **12 hours** after exact New Moon = "Combust Hours," unfortunate to
  begin anything.
- Next **72 hours** fortunate (conditional on Moon strong + well-aspected at
  the start of the 13th hour).
- Then 12 combust hours again, alternating through the month.
- New Moon itself unfavourable except for matters requiring secrecy. [Q]

Shape: matter-general weighted factor keyed on elapsed hours since the exact
Sun–Moon conjunction. Directly computable from the existing substrate.

---

## 4. Rule Family B — Planetary Condition (solar proximity, dignity, motion)

### B.1 Solar-proximity orbs — the second major divergence

"Combustion," "under the beams," and "cazimi" have **authority-divergent orbs**
that must be preserved as named variants. This is the second flagship
divergence after VOC. The single panel-refutation in this research was exactly
here: the claim "Lilly = 12° under-beams / 16′ cazimi" was refuted **not because
it is false but because Lilly is internally inconsistent** — he gives different
values on different pages. That nuance is the finding.

| Condition | Authority | Orb | Notes | Tier |
|---|---|---|---|---|
| Combustion | Common "moiety" tradition | **8°30′** (half of Sun's 17° orb) | The familiar symmetric value | [S] |
| Combustion (Moon) | Ramesey | **12°** either side; applying > separating | Moon-specific | [V+] |
| Combustion (Moon) | Bonatti (Consid. 5) | **15° applying / 12° separating**; "escaped" at 5° sep. | **Asymmetric** — a genuine Bonatti variant | [Q] |
| Combustion (Moon) | Dorotheus | corrupted when decreasing speed & <12°/day (motion, not orb) | different axis entirely | [S] |
| Under the Beams | Lilly CA p.300 (aphorism 26) | **12°** | conflicts with his own p.113 | [Q, part-refuted] |
| Under the Beams | Lilly CA p.113 | **17°** (full Sun orb) | the other Lilly value | [Q] |
| Under the Beams | Early Arabic standard | **15°** | Abu Maʿshar, Sahl, Masha'allah, Alcabitius, Al-Biruni, Ibn Ezra, Bonatti all use the *smaller* list | [Q] |
| Under the Beams | Morin (Astrologia Gallica) | **18°** either side | derived from 18°-below-horizon visibility | [Q] |
| Cazimi | Lilly p.300 | **16′** | follows Ibn Ezra's solar-disc-radius derivation (Sun diameter ~31′) | [Q] |
| Cazimi | Lilly p.113 | **17′** | the other Lilly value | [Q] |
| Cazimi | Bonatti (Consid. 13) | "heart of the Sun" — exemption stated, no numeric orb on this source | [Q] |

Cross-cutting facts an implementation needs:

- **Traditional planetary orb list** (early Arabic standard, radii): Saturn 9°,
  Jupiter 9°, Mars 8°, **Sun 15°**, Venus 7°, Mercury 7°, **Moon 12°**. [Q]
- **Moiety method**: aspect/combustion allowance = half the sum of the two
  bodies' orbs (e.g. Sun–Mercury within (15+7)/2 = 11°). [Q]
- Houlding: **no source older than the 12th c. uses the larger (Sun 17°+) list**;
  the Ptolemy-Almagest attribution for the larger list is false (the Almagest
  contains no planetary orbs). So "smaller list" is the historically correct
  default for medieval-lineage profiles. [Q]
- Lilly's **same-sign requirement**: a planet conjunct the Sun but in a
  *different sign* is **not** combust (a contested variant — some hold combustion
  crosses sign boundaries; Sahl-via-Dykes says conjunction/combustion *does*
  cross the boundary while aspects are whole-sign). [Q]
- Cazimi is a strong *fortification* (positive), the inverse polarity of
  combustion — the scoring model must treat the near-Sun zone as sign-flipping,
  not monotonic. [Q]

**Lilly internal reconciliation (resolves the one panel-refutation).** Lilly's
apparently contradictory solar-proximity figures are three *distinct
conditions*, not conflicting values for one condition:
- **Combustion** = within the Sun's **moiety, 8°30′** (the value used in his own
  accidental-debility scoring table, −5). [S, cross-confirmed]
- **Under the Sun's beams** = within the Sun's **full orb, 17°** (CA p.113); the
  "12°" of aphorism 26 (p.300) is a looser statement of the same beams
  condition, not a combustion orb.
- **Cazimi** = **17′** (p.113) / **16′** (p.300, following Ibn Ezra's
  solar-disc-radius derivation).
So the correct model is three nested zones around the Sun: cazimi (≈17′, strong
+) ⊂ combustion (8°30′, strong −) ⊂ under-beams (17°, mild −). The panel refuted
"Lilly = 12°/16′" only because it flattened these into one orb.

### B.2 Essential dignity point scheme — the citable weighted-scoring lineage

This answers research item 5 (does any weighted scheme have a primary lineage?):
**yes — Lilly's essential dignity points.**

- **Lilly (Christian Astrology 1659, pp. 101–102):** domicile **+5**,
  exaltation **+4**, triplicity **+3**, terms/bounds **+2**, decan/face **+1**. [Q]
- **Essential debilities (now sourced):** detriment **−5**, fall **−4**,
  peregrine **−5** (a planet with no essential dignity). [S, multiple
  reproductions of Lilly's table; confirm against CA p.104/115]
- **Peregrine** = a planet with no essential dignity at all; a malefic
  condition. Face's only function (per Lilly) is to keep a planet from being
  *entirely* peregrine. → boolean planetary-affliction gate. [Q]
- **Competing term/bound schemes are named variants:** Egyptian (most commonly
  accepted; Babylonian origin) vs. Ptolemaic (Ptolemy criticized the Egyptian
  set's consistency). Must not be collapsed. [Q]

This is the backbone of any Moira electional *scorer* profile with a defensible
lineage: it is a published, citable, integer-weight dignity table, not an
invented weighting. The existing `find_scored_windows` + scorer-profile
transport is the natural home, but the doctrine packet must decide the debility
side and the term-scheme variant explicitly.

### B.3 Retrogradation, motion & orientality

- **Retrograde = −5** in Lilly's accidental scoring (a major debility). Speed
  sign is numeric. [S]
- **Direct = +4; swift (faster than mean daily motion) = +2; slow = −2.** [S]
- Slow-in-motion threshold: see A.1 #9 (Moon 13°10′36″/day Ramesey, 13°11′
  Robson, 12°/day Dorotheus — three named numeric variants).
- **Oriental/occidental (now sourced), ±2 by planet class** — orientality =
  rising before the Sun:
  - **Superiors (Saturn, Jupiter, Mars):** oriental **+2**, occidental **−2**.
  - **Inferiors (Mercury, Venus):** occidental **+2**, oriental **−2**.
  - **Moon:** increasing in light (waxing/occidental) **+2**, decreasing
    (waning/oriental) **−2**. [S; Lilly CA — confirm at p.115]

### B.4 The full Lilly accidental dignity/debility table & almuten

Lilly's accidental table (CA Vol. I, p.115) is the most-reproduced traditional
scoring artifact and the natural basis for a Moira "planetary strength" scorer.
Values below are from multiple concordant secondary reproductions [S] and must
be confirmed against the CA facsimile before admission.

**Accidental dignities (+):**
| Value | Condition |
|---|---|
| **+6** | Conjunct Regulus (Cor Leonis) |
| **+5** | In 1st or 10th house; free from combustion & the Sun's beams; cazimi; partile conjunct Jupiter or Venus; conjunct Spica |
| **+4** | In 4th/7th/11th house; direct; partile conjunct North Node (☊); partile trine Jupiter or Venus |
| **+3** | In 2nd or 5th house; partile sextile Jupiter or Venus |
| **+2** | In 9th house; swift in motion |
| **+1** | In 3rd house |

**Accidental debilities (−):**
| Value | Condition |
|---|---|
| **−5** | In 12th house; retrograde; combust (within 8°30′); partile conjunct Mars or Saturn; besieged by Mars & Saturn; within 5° of Algol |
| **−4** | Under the Sun's beams (within 17°); partile conjunct South Node (☋); partile opposition Mars or Saturn |
| **−3** | Partile square Mars or Saturn |
| **−2** | In 6th or 8th house; slow in motion |

(Note the essential debilities detriment −5 / fall −4 / peregrine −5 from §B.2
sit in the *essential* column of the same combined table.)

**Almuten figuris (the weighted "victor" algorithm)** — answers whether a
composite point score has a citable lineage: **yes, via Ibn Ezra → Bonatti.**
Ibn Ezra (12th c., *Book of Nativities*) codified it; Bonatti transmitted it to
the Latin tradition (Lilly, Morin). Method:
- Evaluate essential dignity at **five hylegiacal places**: degree of the Sun,
  degree of the Moon, Ascendant, Part of Fortune, prenatal Syzygy.
- Essential weights (Bonatti, *Liber Astronomiae*): domicile **5**, exaltation
  **4**, sect-correct triplicity **3**, term **2**, face **1** — the same
  vector as Lilly's essential dignities.
- Sum the five per-place score vectors element-wise, then add accidental
  bonuses (Ibn Ezra): angular **+5** / succedent **+4** / cadent **+3** house;
  in-sect luminary bonus **+5**; own-sect-hemisphere **+3**.
- The planet with the highest total is the almuten figuris. [S]

For an *electional* scorer, the almuten machinery is reusable as a
per-significator strength score, but note: the almuten's five *hylegiacal
places* are a natal construct (needs a Syzygy and Part of Fortune). An
ephemeral election has these from the event chart itself, so the algorithm
ports, but the doctrine packet must state that a Moira electional almuten score
is Moira-owned numeric fit, not inherited electional judgement.

---

## 5. Rule Family C — House, Angle & Aspect Rules

### C.1 House / angle

- **Fortify the Ascendant and its lord**, and the lord of the house ruling the
  elected matter — Ramesey's general electional aphorism (via Warnock). [Q]
- **Malefics off the angles**; benefics angular. [general, confirm in primary]
- The **house of the matter** governs which significators must be strong
  (2nd = wealth, 7th = marriage/partners, etc.) — this is the mechanism by which
  general rules become matter-specific. [Q]
- Angularity of the Moon and the angles is the practitioner's final fine-tuning
  factor (mirrored in Solar Fire's electional workflow). [Q]

### C.2 Aspect doctrine

- **Applying vs. separating** is load-bearing throughout (applying combustion
  worse than separating; applying aspects perfect, separating ones are spent).
  Requires signed elongation / speed — the engine's `_short_arc_distance`
  currently folds to [0,180] and cannot express it. **Known engine limitation.**
- **The aspect-perfection doctrines (now sourced).** These govern *whether a
  connection actually completes* — the mechanism by which an election "comes to
  perfection." Each is a computable relation over three bodies, applying/
  separating status, and speed order. Sourced from Lilly, Sahl, Bonatti,
  Masha'allah [S; confirm definitions in Sahl's *Introduction* + CA pp.111–113]:
  - **Translation of light** — a *faster* third planet separates from one
    significator and applies to the other, carrying light between two that do
    not directly connect. Outcome: matter completes **via an intermediary**
    (go-between, letter, messenger). Requires: translator faster than both;
    separating-from-A + applying-to-B.
  - **Collection of light** — two significators that do not aspect each other
    both apply to a *heavier (slower)* third planet that **receives** them (by
    rulership/triplicity). Outcome: completed **through an authority/arbiter**.
    Requires: both significators applying to the collector; collector receives.
  - **Prohibition** — two significators are applying to perfect an aspect, but a
    third planet interposes (by body or aspect) and **perfects with one first**,
    cutting off the union. Two sub-types: bodily (conjunction) and by aspect.
    Outcome: matter **hindered/denied**.
  - **Frustration** — a near-synonym/companion of prohibition: a third planet
    conjoins one significator before the two significators complete, so the
    expected union **fails**. (Some lineages treat frustration and prohibition
    as one family; preserve the distinction where the source does.)
  - **Refranation** — while two significators apply, one **stations and turns
    retrograde before perfection**, withdrawing the connection. Outcome: matter
    **definitely does not finish**. Requires: applying aspect + station of one
    body before exactitude.
  - **Reflection of light** (Masha'allah) — the Moon (or a mediator), not
    separated from either, **applies to both** and reflects light between two
    that cannot meet. Outcome: indirect communication.
  All five/six reduce to: a signed-elongation + relative-speed + station test
  over a forward window — the same substrate unlock (§10) that void-of-course
  and applying/separating need. They are the aspect engine's "perfection
  classifier."
- **Whole-sign vs. in-orb aspects**: Sahl-via-Dykes holds aspects are whole-sign
  while only conjunctions use moieties and cross sign boundaries; Houlding
  disputes this reading. A named-variant divergence for the aspect engine. [Q]

---

## 6. Rule Family D — Planetary Days & Hours

- **Computation (Robson):** daylight (sunrise→sunset) split into 12 equal
  "hours"; first hour of the day ruled by the day's planet; succession in
  **Chaldean order** (Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon). Night
  hours continue the sequence. A modern variant divides sunrise-noon-sunset-
  midnight into sixes. [Q]
- **Named lineage:** Henry Coley (17th c.), *Elections with Planetary Hours* —
  Warnock's cited authority. [Q]
- **Doctrinal weight:** Robson explicitly demotes planetary hours to a
  **supplementary weighted factor of little reliability — never a gate, never a
  replacement for a properly made election.** The doctrine packet must encode
  this as a low-weight optional factor, not a filter. [Q]
- Delphic Oracle models an hour-ruler vs. sect-ruler distinction — an optional
  refinement. [Q]

Moira already has a `muhurta` subsystem and time-of-day machinery; planetary
hours are computable from existing substrate without new astronomy.

---

## 7. Rule Family E — Radicality / Rootedness

Answers research item 6. The authorities **split**, so this too is a named
variant, not a universal:

- **Robson: effectively mandatory.** "Every writer upon the subject of
  Elections agrees that the birth horoscope … is of paramount importance." Cites
  Ptolemy's Centiloquy aphorism 6: an election against the nativity's
  indications "will in no respect avail." → for **radical** elections, rootedness
  is a hard precondition. [Q]
- **Ramesey: self-sufficient elections.** Held elections in such high regard he
  considered natal/horary "beneath the dignity of the subject" — his electional
  rules stand alone. [Q]
- **Ephemeral class: rootedness not applicable** (no natal chart by definition).
  Warnock's own client intake asks only for location + date range, **not** the
  natal chart. [Q]
- **Lilly's radicality test** (a horary gate, electionally echoed): chart is
  "radical, or fit to be judged" when the **Lord of the Ascendant and the Lord
  of the planetary hour are of one nature or triplicity**; plus don't judge when
  **0–3° or 27–29°** ascend. Boolean gates with exact conditions. [Q]

**Doctrine implication:** rootedness is a property of the *election class*
(§2), not a global switch. Ephemeral profiles omit it; radical profiles require
a natal chart and add the Ptolemy/Robson gate.

---

## 8. Rule Family F — Matter-Specific Rule Sets

Every authority separates **general** Moon/planet/angle rules from
**matter-specific** overlays. Carmen Astrologicum Book V is literally structured
this way (chs. 7–44 are per-topic: construction, sales, marriage, sickness,
travel, etc.). [Q] The matter-specific layer is where the "house of the matter"
and targeted significators enter.

| Matter | Governing house / significators | Distinctive rules captured | Authority |
|---|---|---|---|
| Marriage | 7th house; Venus, Moon | Via combusta especially forbidden; Lilly's marriage rules; women's-matters weighting | Ramesey, Lilly, Robson [Q] |
| Journeys / travel | 3rd/9th; Moon | Via combusta forbidden; **moveable signs for short journeys** (Lilly) | Lilly, Ramesey [Q] |
| Building / foundations | 4th; Saturn (endurance) | **Fixed signs** for foundations of houses & towns (Lilly); **use fixed stars for founding cities, planets for houses** (Bonatti — durability match) | Lilly, Bonatti [Q] |
| Commerce / buying-selling | 2nd; Mercury | Via combusta forbidden; Ramesey's 2nd-house elections | Ramesey [Q] |
| Sickness / surgery | 6th; Moon, malefics | Dorotheus Book V.30/32/39/40/41/42 — full rule detail now in hand (see §8.1) | Dorotheus [V+, primary text] |
| Children | 5th | Ramesey's children elections | Ramesey [Q] |
| Career | 10th | Ramesey's career rules | Ramesey [Q] |

Sign-**modality** matching is a compact, general, matter-parameterized rule
(Lilly): **fixed** = permanence (foundations), **cardinal/moveable** = speed
(short journeys), **mutable/common** = a middle/mediocre outcome. [Q] A clean
early matter-aware profile.

Fixed-star rule (Bonatti): match the *durability of the celestial cause to the
durability of the elected matter* — fixed stars (slow) for long-lived things,
planets for shorter-lived. A rare captured fixed-star electional rule. [Q]

### 8.1 Dorotheus Book V — matter-specific corpus (primary text in hand)

Source: Dorotheus of Sidon, *Carmen Astrologicum*, the ʿUmar al-Tabarī
translation, 2nd ed., trans. & ed. Benjamin N. Dykes (Cazimi Press). Book V
"On Questions or Inceptions," pp. 231–330. This is the full matter-specific
inception corpus, cited by chapter/sentence (V.ch,sent).

> **The complete chapter-by-chapter rule inventory** — all 44 chapters,
> general doctrine (V.2–V.6, V.31) plus every matter chapter with gates,
> fortifiers, sign-tables, election-vs-horary flags, and an engine-mapping
> synthesis — is transcribed in the companion document
> [`P13-U1_DOROTHEUS_BOOK_V_RULE_INVENTORY.md`](P13-U1_DOROTHEUS_BOOK_V_RULE_INVENTORY.md).
> The summary below is the surgery exemplar only.

Chapter map (corrected — V.10–13, V.19, V.25 were absent from the v0.3 map):

| Ch. | Topic | Ch. | Topic |
|---|---|---|---|
| V.2–V.6 | General judgment + corruption of the Moon | V.24 | Buying/commissioning a ship |
| V.7 | Building a building | V.25 | Building (constructing) a ship |
| V.8 | Demolishing a building | V.26 | Launching a ship |
| V.9 | Leasing | V.27 | Arrival of a letter *(horary)* |
| V.10 | Buying & selling | V.28 | Bondage & fetters *(horary)* |
| V.11 | Buying land | V.29 | What will not come to be *(horary)* |
| V.12 | Buying a slave (Moon-in-sign) | V.30 | Sick person *(decumbiture)* |
| V.13 | Buying an animal | V.31 | The inception in all things (general) |
| V.14 | Emancipating a slave | V.32 | Condition of the sick person |
| V.15 | Seeking a need/gift from a ruler | V.33 | Native's assets *(time-lord)* |
| V.16 | Writing to / teaching a man | V.34 | Two opponents (lawsuit) |
| V.17 | Marriage & sex | V.35 | Leaving one's land *(horary)* |
| V.18 | Betrothal / a wife's return | V.36 | Theft *(horary)* |
| V.19 | Extracting a dead fetus (obstetric) | V.37 | The runaway *(horary)* |
| V.20 | Entering a partnership | V.38 | Treatment of spirits |
| V.21 | Debt & its payment | V.39 | Preserving health (purgatives) |
| V.22 | Travel / departure | V.40 | Surgery (cutting with iron) |
| V.23 | Return from the journey | V.41 | Eye / iron treatment |
| | | V.42 | Illnesses (Qitrinus) *(decumbiture)* |
| | | V.43–44 | Wills; lunar phases & Nodes |

**Surgery — V.40 ("cutting something from the body with an iron tool or
scalpel, or bloodletting"), pp. 312–313** (implementable rule set, primary
text): [V+]

- **Sign taboo:** avoid if the Ascendant or Moon is in Taurus, Virgo,
  Capricorn, or Pisces (V.40,1).
- **Solar-proximity taboo:** avoid at the New Moon until the Moon is >13° from
  the Sun's rays (V.40,2); avoid when the Moon is waning and moving from the
  Sun toward opposition (V.40,3).
- **Mars taboo:** avoid Mars in the Ascendant, conjunct the Moon, or aspecting
  the Ascendant or Moon (V.40,4). Mars **with Saturn** aspecting the Ascendant
  or Moon → the patient scarcely survives, or the cutting must be repeated
  (V.40,5).
- **Fortifiers:** prefer the Moon decreasing in light with the infortunes
  **not** in the sign rising *after* the Moon (the 2nd sign from her) (V.40,6);
  Moon and Ascendant with Venus or Jupiter, or Venus aspecting the Ascendant
  with the Moon in it, cleansed of the infortunes (V.40,7).
- **Melothesia rule:** avoid cutting the limb over which the sign of the Moon
  or Ascendant has authority (V.40,8) — the sign→body-part correspondence must
  be a lookup table the surgery profile owns.
- **Modality caution:** Moon in a convertible (cardinal) or bicorporeal sign is
  unsuitable unless the fortunes are with her or aspect her (V.40,9).

**Related medical chapters:** V.39,2 — laxatives/enemas favor the Moon in
Libra or Scorpio ("the lower region") with fortunes aspecting the Moon. V.41 —
eye/iron treatment favors the Moon **increasing** in light and calculation
with Jupiter or Venus, Mars not aspecting. V.42 (Qitrinus al-Sadwali) — illness
prognosis reads the Ascendant, Moon, lord of the Ascendant, lord of the Moon's
sign, the Moon's next connection, and the twelfth-part of the Moon.

These chapters give the medical/surgical profile family its gates (sign taboos,
Mars/Saturn taboos, solar-proximity taboo) and its fortifiers directly from the
oldest electional authority. The remaining Book V topics (marriage, building,
ships, partnership, lawsuit, theft, runaway) are transcription-pending but
present at the same rule depth — this is now a reading task, not a search task.

---

## 9. Software & Scoring Precedent (research item 5)

What existing tools actually do — important because it tells us what is *novel*
vs. *table stakes*, and what has real lineage:

- **Solar Fire (8):** electional search = **boolean criteria filtering** with
  And/Or/Not connectors over aspect/sign/other conditions. **No numeric scoring
  at all.** Supplementary tools are lookup tables (VOC listings, Moon phases,
  planetary-hours table, ingresses, returns). Saveable named criteria sets =
  reusable profiles. Dignity/almuten scoring is a *separate* user-editable `.alm`
  feature (§below). [Q]
  - **Takeaway:** Moira's existing predicate-scan + And/Or (composite) design is
    *the same architecture Solar Fire ships*. Moira is not behind here; the gap
    is the classical rule *vocabulary*, not the search mechanism.
- **Delphic Oracle WL:** implements dignity/almuten **weight tabulations** and
  the **almuten figuris** (per Ibn Ezra weights), plus Bonatti degree
  attributions and sect-aware planetary hours. But it is **natal-framed** — no
  dedicated electional module. So a citable dignity-*scoring* codification
  exists; an electional-scoring one does not. [Q]
- **Solar Fire `.alm` editor:** users build a **Lilly-point dignity scheme**
  (+5/+4/+3/+2/+1) themselves; traditional rulerships must sit in the 2nd config
  slot or the program silently scores with modern rulers (Uranus→Aquarius,
  Neptune→Pisces) while the UI still says "traditional" — a real correctness
  footgun worth designing against. Outer planets are displayed but score 0 and
  are excluded from almutens. [Q]
- **Christopher Warnock (leading modern traditional practitioner):**
  **explicitly rejects** software/automated electional analysis — "Renaissance
  astrology is too complex to be produced by a computer program." Publishes **no
  weighting scheme** and denies one is feasible. [Q]

**Net finding for research item 5:** The only weighted scheme with a clean
citable primary lineage is **Lilly's essential-dignity integer points**
(§B.2). Almuten weighting has software precedent (Delphic Oracle) and an Ibn
Ezra lineage. There is **no published, citable, primary-source *composite
electional* score** — electional weighting in the wild is either (a) boolean
filtering (Solar Fire) or (b) practitioner judgement (Warnock). This is
directly relevant to Moira's Part-V posture: **any composite electional score
Moira emits is Moira-owned numeric fit, and must be labelled as such — there is
no external doctrine to inherit or hide behind.** The P13-03 packet's existing
stance ("scores are numeric fit, not electional judgement") is exactly right and
should govern here too.

---

## 10. Implementation Mapping To The Existing Engine

How each family lands against the generic `moira.electional` transport and REST
predicate/scorer catalogues. This table is about transport exposure, not the
separate module-level `ramesey_moon_condition_v1` evaluator admitted on
2026-07-14.

| Rule family | Shape | Fits existing engine? | New capability required |
|---|---|---|---|
| Via combusta (A.3) | Boolean gate | Yes — `body_longitude_range` on the Moon over 195°–225° | None (expressible today) |
| Moon in fall / detriment (A.1 #5,6) | Gate | Yes — longitude-range | None |
| Moon near nodes (A.1 #4) | Gate | Partly — needs nodes as subjects | Nodes exist in `ChartContext` and the Ramesey evaluator; generic predicate catalogue still needs admission |
| Combustion / cazimi / under-beams (B.1) | Signed gate, variant orbs | Partly | Ramesey evaluator now owns its 12° Moon gate and source orbs; other variants and generic transport remain separate |
| Void of course (A.2) | Variant classifier | Not in generic transport | Existing `void_of_course` supplies the admitted Ramesey exact-perfection/sign-bound product; other variants remain unimplemented |
| Moon speed / slow (A.1 #9) | Numeric gate | Not in generic transport | `PlanetData.speed` supplies the admitted Ramesey profile; generic scan payload still lacks exposure |
| Retrograde (B.3) | Gate | **No** | Needs speed sign in payload |
| Applying vs separating (C.2) | Directional modifier | Not in generic transport | Implemented visibly for Ramesey Rule 1; generic transport and other lineages remain separate |
| Dignity points (B.2) | Weighted scorer | Partly | Needs dignity tables (domicile/exalt/triplicity/term/face) + term-scheme variant |
| Composite ten-impediment Moon gate (A.1) | Source-ordered profile | Public single-moment evaluation admitted | `moira.western_electional`, package root, facade, `Moira`, and bounded REST return ten witnesses; no generic `all_of`, scan, or score admission |
| Planetary hours (D) | Low-weight factor | Yes (computable) | Chaldean-order hour ruler from sunrise/sunset |
| Radicality (E) | Class-gated evidence | Shared context admitted | `ephemeral` rejects natal input; `radical` requires a complete natal moment/location/house-system bundle; no success gate is invented |
| Matter-specific overlays (F) | Profile family | Shared context admitted, complete profiles pending | Six V.31 matter families and their planets are typed; chapter-owned houses and complete matter judgement remain future profile work |

Three cross-cutting transport capabilities still unlock most wider exposure:
1. **Body speed in the scan payload** → generic slow-Moon, retrograde, applying/separating predicates.
2. **Signed solar elongation + variant orb tables** → the entire combustion/
   cazimi/under-beams family with lineage variants.
3. **Variant-aware forward next-aspect search** → VOC definitions beyond the
   admitted Ramesey sign-bound product and the aspect-perfection doctrines
   (translation/collection/prohibition).

These are the same substrate gaps I flagged in the initial survey (Tier-2/3),
now grounded in exactly which doctrine each one buys.

---

## 11. The Divergences Moira Must Preserve (Part-V register)

The non-negotiable variant list — each is a named parameter, never a collapsed
default:

1. **Void-of-course**: `{hellenistic_30deg, medieval_sign_bound,
   ramesey_sign_bound_beholding, lilly_moiety, ward_orb}` + feral flag +
   four-sign mitigation + purpose-inversion sign.
2. **Moon/Sun condition**: `{ramesey_moon_12, sahl_moon_12,
   dorotheus_under_rays_unquantified}` plus separately sourced general
   combustion systems. Dorotheus's `<12°/day` rule is slow motion, not a
   combustion orb.
3. **Under-the-beams orb**: `{arabic_15, lilly_17, lilly_ap26_12, morin_18}`.
4. **Cazimi orb**: `{lilly_16min, lilly_17min}` (+ Bonatti exemption, no numeric).
5. **Planetary orb list**: `{smaller_arabic (Sun 15), larger_12thc (Sun 17)}` — smaller is the historically correct medieval default.
6. **Terms/bounds scheme**: `{egyptian, ptolemaic}`.
7. **Slow-motion threshold**: `{ramesey_13d10m36s, robson_13d11m,
   sahl_12d, dorotheus_12d}`.
8. **Aspect scope**: `{whole_sign (Sahl/Dykes), in_orb (Houlding/Lilly)}`.
9. **Combustion sign-boundary**: `{same_sign_only (Lilly), crosses_boundary (Sahl)}`.
10. **Via combusta**: `{ramesey_15lib_15sco, sahl_end_lib_begin_sco,
    dorotheus_libra_and_scorpio}` until each later lineage is page-confirmed.
11. **Election class / rootedness**: `{ephemeral (no natal), radical (natal required), mundane}`.

Averaging or silently defaulting any of these would be a Semantic-Honesty and
Part-V violation. The doctrine packet's central job is to name them and pick
*explicit, cited defaults per named profile* (e.g. a "Lilly" profile vs. a
"Bonatti" profile vs. a "Robson" profile each bind these differently).

---

## 12. Research Gaps — Status After Follow-Up Pass

The research pass inventoried the main parameter families. The first-profile
page audit showed why inventory is not admission: several historical phrases
still require explicit computational policy. Every closed item carries the
standing rule: **confirm against the named primary text at the cited page
before admission.**

### Closed in v0.2

| Gap | Resolution | Location |
|---|---|---|
| Aspect-perfection doctrines | Translation, collection, prohibition, frustration, refranation, reflection — full mechanics | §C.2 |
| Debility point values | detriment −5, fall −4, peregrine −5 | §B.2 |
| Full accidental dignity/debility table | Complete +6…−5 table (houses, motion, star conjunctions, besieging) | §B.4 |
| Oriental/occidental parameters | ±2 by planet class; Moon by light | §B.3 |
| Almuten figuris algorithm | Ibn Ezra 5 hylegiacal places + Bonatti weights + accidental bonuses | §B.4 |
| Bonatti considerations count | **146** (Tractatus Quintus, *Liber Astronomiae*); the "123" was a secondary miscount | §1 |
| Combustion / under-beams / cazimi reconciliation | Three nested zones: cazimi 17′ ⊂ combustion 8°30′ ⊂ under-beams 17° | §B.1 |

### Now in hand (primary texts + rule inventories)

- **Dorotheus Book V** — RESOLVED (acquisition + rule inventory). Dykes ʿUmar
  al-Tabarī *Carmen Astrologicum* (2nd ed.) on disk; Book V pp. 231–330.
  Complete companion: `P13-U1_DOROTHEUS_BOOK_V_RULE_INVENTORY.md` (v1.0) —
  general layers V.2–V.6 / V.31 plus every matter chapter V.7–V.44 with
  election/horary flags, named Dorothean variants, and engine-mapping.
- **Sahl *On Elections*** — RESOLVED (acquisition + rule inventory). Dykes
  *Choices & Inceptions* on disk (449 pp.); Sahl Part III printed pp. 91–133.
  Complete companion: `P13-U1_SAHL_ON_ELECTIONS_RULE_INVENTORY.md` (v1.0) —
  rootedness §§1–9, sign-nature §§10–20, ten Moon impediments §22, matter
  significators §21, house-by-house §§29–142, letter §143, named Sahl variants,
  and engine-mapping. Same volume also holds al-Kindī, Bethen, al-ʿImrānī, and
  al-Rijāl VII (not yet inventoried as separate companions).

### Still thin (not acquisition blockers — conditional only)

- **Ptolemaic vs Egyptian term tables (actual degree boundaries)**: both schemes
  named and their divergence documented (§B.2), but Moira's existing
  `PTOLEMAIC_BOUNDS` constant currently duplicates the Egyptian table despite
  its label. The Ramesey profile therefore carries only its source-required
  terminal malefic segments locally. A general Ptolemaic term product requires
  a separate correction and validation task.
- **Page re-confirmation** of ⚠-marked readings in both inventories (standing
  Moira law before doctrine admission) — not a missing-source problem.
- **Ramesey remedy fulfillment**: the p. 127-128 instruction and its
  urgent/unavoidable applicability are now preserved as a separate non-erasing
  witness. Actual fulfillment remains deliberately uncomputed until
  source-specific angle-aspect, benefic-placement, Ascendant-ruler, hour-lord,
  and fortification policies are admitted.

**No remaining true acquisition gaps.** Both Dorotheus and Sahl electional
rule inventories exist as companions. The general Moon/planet/angle/aspect
architecture is inventoried, and the admitted Ramesey, Sahl, and Dorotheus
bounded public-moment profiles preserve distinct source derivations and policy
choices.

---

## 13. Recommended Next Steps

1. **Treat the Ramesey profile closure as complete** for the bounded
   `ramesey_moon_condition_v1` object. Do not expand its ten gates, score them,
   or claim remedy fulfillment without a new source-backed doctrine decision.
2. **Treat the Sahl Moon-profile closure as bounded and explicit**: section 22
   is admitted through REST, but the default burnt-path clause remains
   indeterminate because Sahl gives no endpoints. Do not silently promote a
   selectable glossary span into source text.
3. **Treat the Dorotheus V.6 closure as bounded and explicit**: all eleven
   clauses and the V.6.15 remedy are public through REST, but V.6.7 and V.6.10
   remain indeterminate until primary evidence supplies lawful computational
   regions or intervals. Do not expand this into root/outcome or a complete
   matter judgement implicitly.
4. **Treat the shared rooted/matter-significator vessel as bounded and
   complete** for `dorotheus_rooted_context_v1`: it preserves the Moon as root,
   the Moon-sign lord as outcome, the first sign-bounded exact connection, six
   V.31 matter families, and explicit natal evidence. It is not a complete
   matter judgement and does not resolve V.31's undefined bad-place set.
5. **Generic search transport remains deferred by explicit decision**: the
   single-moment facade and REST vessel are admitted, but variant-aware
   forward-aspect provenance, remedy applicability versus fulfillment, and a
   forward-VOC caching/performance contract must be defined before proposing
   any scan-payload, predicate, or scoring admission.
6. **Profile-first rollout**: the next admission is the first complete
   matter-specific profile built on the rooted vessel, not a blended universal
   election. Each additional profile, generic search adapter, scoring product,
   and website surface requires its own admission decision.
7. **Validation strategy**: per Moira law, each numeric rule (orbs, thresholds,
   points) is verified against its **named primary text at the cited page**
   before admission; each variant carries its citation in the profile metadata.

---

## Appendix — Source Register

**Primary texts held on disk** (highest authority; supersede web excerpts for
their material — confirm citations against these before admission):

| Text | File | Covers |
|---|---|---|
| Dorotheus, *Carmen Astrologicum*, ʿUmar al-Tabarī trans., 2nd ed. (Dykes) | `~/Downloads/…Umar-Al-Tabari…Dorotheus….pdf` (412 pp.) | **Book V elections, pp. 231–330** (§8.1); dignities, terms, Moon phases; glossary (via combusta) |
| Dorotheus, *Carmen* Books I–III (Pingree 1976, Houlding repro) | `~/Downloads/dorotheus1–3.pdf` | Books I–III only — nativity material, not elections |
| Dykes, *Choices & Inceptions: Traditional Electional Astrology* | `~/Downloads/pdfcoffee.com_choices-and-inceptions-traditional-electional-astrology--pdf-free.pdf` (449 pp.) | **Sahl *On Elections* (pp. 91–133)** → companion `P13-U1_SAHL_ON_ELECTIONS_RULE_INVENTORY.md`; also al-Kindī; Bethen hours; al-ʿImrānī *Book of Choices*; al-Rijāl VII |
| Bonatti, *146 Considerations* | `~/Downloads/bonatti146.pdf` | §1, A.2, A.3, B.1 (Bonatti combustion orbs & considerations) |
| Bonatti, *Book of Astronomy* — translator's introduction (Dykes) | `~/Downloads/Translator's introduction to_ The Book of Astronomy…pdf` | Bonatti lineage & method context |

Full 101-claim web extraction with verbatim quotes is preserved at
`scratchpad/electional_claims.md` (session artifact). Principal web sources:

| Source | Authority tier | Used for |
|---|---|---|
| [Internet Archive `b30323149_0001`](https://archive.org/download/b30323149_0001/b30323149_0001.pdf) — Ramesey, *Astrologia Restaurata* (1654) original facsimile | primary | A.1, A.3; visually confirmed printed pp. 126–127 on 2026-07-14 |
| iapsop.com — Robson, *Electional Astrology* (1937), full PDF | primary | §2, A.1, A.3, A.4, D, E |
| renaissanceastrology.com — Ramesey electional intro & Moon (Warnock transcription) | secondary transcription of primary text | readable witness for A.1, A.3, §8 |
| astrologiahumana.com — Lilly, *Christian Astrology* Book II facsimile | primary | A.2, B.1, B.2, E, F |
| skyscript.co.uk — considerations.pdf; rev_ram; forums (orbs, Solar Fire config) | primary/secondary/forum | B.1, radicality, software |
| bendykes.com — Sahl vol. I; Dorotheus *Carmen* | primary/secondary | §1 lineage, C.2 citation homes |
| renaissanceastrology.com — bonatti146considerations.html | secondary | A.2, A.3, B.1 (Bonatti orbs) |
| theastrologypodcast.com — ep. 292 (VOC definitions) | secondary | A.2 |
| tonylouis.wordpress.com; medievalastrologyguide.com | blog | A.2 (Lilly VOC nuance) |
| classicalastrologer.com — combustion | blog | B.1 |
| en.wikipedia.org — Essential dignity; Electional astrology | secondary | B.2, §2 |
| astrology-x-files.com — Delphic Oracle WL | primary (vendor) | §9 |
| astrologysoftware.co.uk — Solar Fire electional | secondary (vendor) | §9 |

v0.2 follow-up sources (all [S] unless noted; confirm parameters in primaries):

| Source | Used for |
|---|---|
| tonylouis.wordpress.com — Lilly on Prohibition | §C.2 prohibition mechanics |
| sirauysal.com — horary techniques | §C.2 translation/collection/frustration/refranation/reflection |
| kerykeion.net — Almuten Figuris; oriental/occidental | §B.3, §B.4 |
| astrologysoftware.com — Astro*Dictionary (accidental) | §B.4 full accidental table |
| astrogrammar.com — Lilly's Scoring System (PDF, 403 on fetch; values via search excerpt) | §B.2, §B.4 |
| skyscript.co.uk/guido146.html — Anima Astrologiae | §1 Bonatti = 146 considerations |
| sevenstarsastrology.com — Elections series (Dorothean) | §8, §12 Dorotheus per-matter |
| theastrologypodcast.com — Sahl (Dykes) | §12 Sahl rule shape |

Verification status: 7 claims panel-confirmed [V+], 1 panel-refuted as-stated
(retained corrected) [V-], 17 quote-grounded but unverified due to spend limit
[Q], remainder secondary synthesis [S]. **No rule herein is validated for
implementation; all require primary-text confirmation at the cited page before
entering doctrine.**
