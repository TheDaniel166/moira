# Vedic Jyotish — Phase 2 Gap Register

**Audit date:** 2026-07-08
**Method:** code inspection of every Vedic-family module (`sidereal`, `varga`,
`vedic_dignities`, `jaimini`, `panchanga`, `muhurta`, `dasha`, `dasha_systems`,
`ashtakavarga`, `shadbala`, `varshaphal`, `timelords`) plus keyword sweep for
classical techniques with no implementation anywhere in `moira/`.
**Impetus:** the Bhava Bala omission (closed 2026-07-08) was traced to an
explicit out-of-scope note in the Phase-1 roadmap that nothing ever revisited.
This register exists so no further gap survives by silence.

**Gap types:** A = technique absent | B = depth gap in an existing subsystem
**Effort:** S (small, days) | M (medium, ~a week) | L (large, multi-week)

---

## 0. Current-State Map (what Phase 1 delivered)

| Subsystem | State |
|---|---|
| Panchanga | Complete — 5 limbs, sankranti bisection, condition/chart profiles |
| Sidereal / nakshatra | Complete — 34 ayanamsas; nakshatra + pada + lord |
| Varga | Complete — 17 divisions incl. full Shodashavarga + D6/D8 |
| Vedic dignities | Complete — full Panchadha Maitri |
| Shadbala | Complete — 6 balas, Bhava Bala, Ishta/Kashta Phala, Graha Yuddha with transfer disclosure |
| Ashtakavarga | Strong — bhinna + sarva, Trikona & Ekadhipatya Shodhana, sign-level transit strength |
| Dashas | Strong — Vimshottari to L5 (Sookshma), Ashtottari, Yogini |
| Jaimini | Karakas only (7/8 scheme, Rahu inversion, tie detection) |
| Muhurta | Generic scoring — tithi/vara/nakshatra/karana classification, Abhijit/Brahma, window search |
| Varshaphal (Tajika) | Deep — muntha, sahams, mudda dasha, panchavargi, varshesha, judgement layer |

---

## 1. Yoga Engine — planetary combinations

**Gap type:** A (entire technique family absent)
**Effort:** L
**Priority: 1 — the largest user-visible gap in the Vedic layer.**

No yoga detection exists anywhere: no Pancha Mahapurusha (Ruchaka/Bhadra/
Hamsa/Malavya/Sasa), no Chandra yogas (Gajakesari, Sunapha/Anapha/Durudhara,
Kemadruma), no solar yogas (Vesi/Vosi/Ubhayachari, Budhaditya), no Nabhasa
yogas (32: 3 Ashraya, 2 Dala, 20 Akriti, 7 Sankhya), no raja/dhana-yoga
foundations (kendra-trikona lordship links, Viparita Raja).

- **Primary authority:** BPHS yoga adhyayas; Mantreswara, *Phaladeepika*
  Ch. 6–7; Raman, *Three Hundred Important Combinations* (1947) — the
  natural engineering reference with per-yoga conditions.
- **Design note:** each yoga = a named rule with the conditions it met/failed
  made visible (transparency doctrine), plus strength context from the
  already-computed Shadbala.  Cancellation (bhanga) conditions must be
  first-class, not bolted on — Kemadruma and Neecha Bhanga are defined as
  much by their cancellations as their formations.
- **Dependencies:** all satisfied — dignities, houses, shadbala, vargas exist.
- **Validation:** Jhora yoga list; Raman's worked combinations.

## 2. Jaimini expansion — beyond karakas

**Gap type:** A (four sub-techniques absent)
**Effort:** L (as a family; each piece is M or smaller)
**Priority: 2.**

Present: karakas only.  Missing, in dependency order:

1. **Rasi drishti** (sign aspects: movable↔fixed skipping adjacent, dual↔dual)
   — the aspect doctrine every other Jaimini technique consumes.
2. **Arudha padas** (AL, A1–A12, UL) with the exception rules (pada falling in
   1st/7th from its bhava reflects to the 10th/4th).
3. **Argala** (intervention: 2/4/11 primary, 5 secondary; obstruction from
   3/10/12) — consumes rasi drishti.
4. **Karakamsa** (Atmakaraka's navamsha sign read as lagna in D1/D9) — trivial
   once karakas + vargas are joined.
5. **Chara Dasha** (sign-based dasha; the most-requested Jaimini item after
   karakas).  Note: multiple lineages (Raths's vs. Irangati's vs. classical
   K.N. Rao) differ on period computation — the implementation must name its
   lineage explicitly, per the Policy Explicitness law.

- **Primary authority:** Jaimini, *Upadesa Sutras* (Adhyaya 1); Sanjay Rath,
  *Jaimini Maharishi's Upadesa Sutras* (2002); K.N. Rao on Chara Dasha.
- **Validation:** Jhora (which exposes lineage choices explicitly — mirror that).

## 3. Upagrahas — Gulika, Mandi, and the kalavelas

**Gap type:** A
**Effort:** M
**Priority: 3.**

No upagraha computation exists.  Needed: Gulika/Mandi (Saturn's portion of
the day-eighths), plus the remaining kalavelas (Kala, Mrityu, Yamaghantaka,
Ardhaprahara) and optionally the Sun-derived sub-planets (Dhooma, Vyatipata,
Parivesha, Indrachapa, Upaketu — pure longitude arithmetic).

- **Primary authority:** BPHS Ch. 3 (Grahopadesa); day/night eighth-division
  rule with lords ordered from the weekday lord.
- **Dependencies:** `moira.rise_set` already provides sunrise/sunset — the
  day-division substrate exists.
- **Policy note:** Gulika vs. Mandi definitions differ by school (start vs.
  middle of Saturn's portion; some equate them).  Both conventions must be
  explicit policy options, not a hidden default.
- **Validation:** Jhora, Kala (both expose the convention choice).

## 4. Avasthas — planetary states

**Gap type:** A
**Effort:** M
**Priority: 4 — pairs naturally with the Shadbala drill-down.**

None of the classical state systems exist: Baladi (5 age states by degree in
odd/even sign), Jagradadi (3 awareness states from dignity), Deeptadi (7–9
mood states from dignity/combustion/war), Lajjitadi (6 conditional states —
needs conjunction/aspect context).

- **Primary authority:** BPHS Ch. 45 (Avasthadhyaya); Saravali.
- **Design note:** mostly table-driven; Lajjitadi is the only one requiring
  aspect machinery (exists).  Combustion state needs Sun-proximity orbs —
  present in `moira.phenomena`.
- **Validation:** Jhora avastha display.

## 5. Tara Bala + Chandra Bala — natal-personalized muhurta

**Gap type:** B (muhurta exists but is impersonal)
**Effort:** S
**Priority: 5 — the highest value-per-effort item in this register.**
> **CLOSED 2026-07-08.** `moira.muhurta`: `tara_bala` / `chandra_bala` /
> `personal_muhurta_score` (+ the long-dormant Tara placeholder in
> `_classify_nakshatra` now computes); served at
> `POST /v1/muhurta/personal/score`.

`muhurta.py` scores a moment generically; classical practice always overlays
**Tara Bala** (count from janma nakshatra → 9-tara cycle: Janma/Sampat/
Vipat/Kshema/Pratyari/Sadhaka/Vadha/Mitra/Parama Mitra, with favorable/
unfavorable polarity) and **Chandra Bala** (transit Moon's house from natal
Moon; 1/3/6/7/10/11 favorable, 4/8/12 unfavorable — with 8th strongest
affliction).

- **Primary authority:** Muhurta classics (Muhurta Chintamani); Raman,
  *Muhurtha* (1936).
- **Dependencies:** all present — nakshatra_of, natal chart context.
- **Surface:** extend `MuhurtaScore` with tara/chandra components (sub-parts
  visible, per transparency doctrine) and add natal-aware variants of the
  scorer/window functions.

## 6. Vimshopaka Bala + Vargottama

**Gap type:** B (all 17 vargas computed; nobody aggregates them)
**Effort:** S
**Priority: 6.**
> **CLOSED 2026-07-08.** `moira.varga`: `vimshopaka_bala` / `vimshopaka_all`
> (all four BPHS groups, per-division breakdown with vargavishwa fractions)
> + `is_vargottama` / `vargottama_planets`; served at
> `POST /v1/varga/vimshopaka`.

- **Vimshopaka Bala:** the classical 20-point weighted dignity score across
  the four varga groups (Shadvarga 6 / Saptavarga 7 / Dashavarga 10 /
  Shodashavarga 16), each group with its own BPHS weight table.
- **Vargottama:** flag planets occupying the same sign in D1 and D9 —
  a one-line derivation the public surface simply never exposed.
- **Primary authority:** BPHS Shodashavarga Adhyaya (vimshopaka weight
  tables).
- **Dependencies:** none — pure aggregation over `moira.varga`.
- **Validation:** Jhora vimshopaka display.

## 7. Ashtakavarga polish — Kakshya + Shodhya Pinda

**Gap type:** B
**Effort:** S–M
**Priority: 7.**

- **Kakshya-level transit:** each sign divides into 8 kakshyas (3°45' each,
  lords Saturn→Jupiter→Mars→Sun→Venus→Mercury→Moon→Lagna); a transit scores
  only when the transited kakshya's lord contributed a rekha.  Refines the
  existing sign-level `transit_strength`.
- **Shodhya Pinda:** Rasi Pinda + Graha Pinda multipliers applied after the
  two Shodhanas (which already exist) — the predictive quantity classical
  ashtakavarga actually uses for transit results and longevity work.
- **Primary authority:** BPHS Ashtakavarga Adhyaya; Raman, *Ashtakavarga
  System of Prediction* (1981) — already the committed table source.

## 8. Sade Sati

**Gap type:** B (derivable from `transits` but not a named product)
**Effort:** S
**Priority: 8.**
> **CLOSED 2026-07-08.** New `moira.sade_sati`: `sade_sati_status`
> (phase + Ashtama/Kantaka flags) and `sade_sati_windows` (kernel-timed
> sign-ingress bisection, retrograde re-entries as separate windows);
> served at `POST /v1/sade-sati/status` and `POST /v1/sade-sati/windows`.

Saturn's transit through the 12th/1st/2nd from natal Moon, with phase
boundaries (rising/peak/setting) and exact ingress timestamps from the
existing transit search.  Optionally Kantaka Shani / Ashtama Shani flags.
Pure composition of existing machinery into the named product users ask for.

## 9. Kalachakra Dasha — recorded deferral

**Gap type:** A (explicitly deferred since Phase 1)
**Effort:** L
**Priority: 9 — remains deferred.**

`dasha_systems.py` documents the deferral (navamsha-based Savya/Apasavya
traversal, variable cycle length, lineage disputes).  Kept in the register so
the deferral stays a decision, not an accident.  Precondition: a committed
lineage choice (Jhora's implementation notes are the practical cross-check).

---

## Recommended sequencing

| Wave | Items | Rationale |
|---|---|---|
| Quick wins | #5 Tara/Chandra Bala, #6 Vimshopaka+Vargottama, #8 Sade Sati | Days each; all substrate exists; immediate site value |
| Flagship | #1 Yoga engine | Largest gap; modular (ship family-by-family: Mahapurusha → Chandra/solar → Nabhasa → raja/dhana) |
| Deepening | #3 Upagrahas, #4 Avasthas, #7 Ashtakavarga polish | Medium; each closes a classical-completeness hole |
| Expansion | #2 Jaimini family | Large; internally ordered (rasi drishti first) |
| Deferred | #9 Kalachakra | Revisit after the above |

Every implementation follows the Phase-1 pattern: primary authority named,
engineering reference committed, sub-components exposed with their parts and
totals (transparency doctrine), policy choices explicit where schools differ,
validation against Jhora/Kala plus source-owned invariants.
