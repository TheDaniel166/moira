# Moira Feature Audit — Design Specification

**Date:** 2026-05-15  
**Status:** Approved — ready for implementation  
**Author:** TheDaniel166

---

## 0. Purpose & Scope

This document specifies the design of a comprehensive feature audit comparing the Moira computational engine against professional astrology software. The audit produces a gap analysis document that identifies calculation features Moira is missing or implements at lesser depth than competitors, and prioritizes those gaps for implementation.

**What this audit covers:** Pure computational coverage — technique correctness, method variants, body/system breadth.  
**What this audit does not cover:** Interpretation layers, UI/UX features, content text, AI delineation, or anything not a direct calculation artifact.

---

## 1. Constraints & Decisions

| Decision | Value | Rationale |
|---|---|---|
| Moira's role | Computational engine / library | Not a product; interpretation layers are out of scope |
| Competitor tiers | Desktop suites, web platforms, consumer apps | All three tiers; full competitive landscape |
| Tradition coverage | All four equally | Hellenistic, Medieval/Arabic, Modern Western, Vedic |
| Audit structure | Domain-first | Aligns with Moira's wiki structure; gaps are domain-local then rolled up |
| Priority basis | Combined score (D + C + T) | Demand + competitive coverage + tractability, 1–3 each |
| Assessment method | Public documentation + code inspection | Competitors assessed from manuals/feature pages; Moira assessed from direct code inspection |

---

## 2. Competitor Set

### Tier 1 — Professional Desktop Suites

| App | Publisher | Why Included |
|---|---|---|
| Solar Fire | Esoteric Technologies | Western professional standard; definitive feature reference |
| Sirius | Cosmic Patterns | Most feature-complete desktop app; maximum coverage benchmark |
| Janus | AstroSoft | Strong Hellenistic/traditional depth; classical technique benchmark |

### Tier 2 — Web Platforms

| App | Publisher | Why Included |
|---|---|---|
| Astro.com (Astrodienst) | Astrodienst | Global reference standard for online calculation accuracy and breadth |
| Astro-Seek | Astro-Seek.com | Deep free-tool coverage; benchmark for what free tools now offer |
| Morinus | Open source | Specialized in primary directions and traditional methods |

### Tier 3 — Consumer Mobile Apps

| App | Publisher | Why Included |
|---|---|---|
| Co-Star | Co-Star Astrology | Highest-profile consumer app; JPL-backed engine; mass-market benchmark |
| TimePassages | Astrograph | Professional-grade calculations in consumer UX; bridge tier |

---

## 3. Cell Scoring Legend

| Symbol | Meaning |
|---|---|
| ✓ | Full — feature present and production-grade |
| ~ | Partial — present but limited in depth, method variants, or coverage |
| ✗ | Absent — feature not present |
| ? | Unclear — cannot be determined from available public documentation |

---

## 4. Gap Type Classification

- **Type A — Missing Feature:** A calculation technique or feature category Moira does not implement at all.  
- **Type B — Depth Gap:** A feature Moira has but at lesser depth, narrower method coverage, or fewer variants than competitors.

---

## 5. Priority Scoring Formula

Each gap is scored on three dimensions, each rated 1–3:

| Dimension | Symbol | 1 | 2 | 3 |
|---|---|---|---|---|
| Professional Demand | D | Niche / specialist use | Moderate use | Universally used by practitioners |
| Competitive Coverage | C | 1–2 competitors have it | 3–5 competitors have it | 6–8 competitors have it |
| Implementation Tractability | T | Significant new infrastructure required | Moderate effort; some foundations exist | Easy given Moira's existing code |

**Combined score = D + C + T**

| Score | Priority |
|---|---|
| 7–9 | **P1** — implement next |
| 5–6 | **P2** — important but not urgent |
| 3–4 | **P3** — low priority / niche |

---

## 6. Report Structure

The audit produces a single markdown document with the following sections:

```
0. Executive Summary
   - Overall coverage score per domain
   - Top 10 gaps by priority
   - Quick wins (P1, T=3)

1–12. Domain Chapters (one per domain)
   Each chapter contains:
   a. Domain description (2–3 sentences)
   b. Moira coverage summary — what's implemented and at what depth
   c. Competitor coverage matrix (rows = features, cols = competitors)
   d. Gap notes — per-gap observations, interactions, implementation hints

13. Master Gap List
   - All Type A and Type B gaps from all domains
   - Scored with D / C / T / Total / Priority
   - Cross-referenced to domain chapter
   - Sorted by priority tier, then by score descending

14. Depth & Accuracy Gap Supplement
   - Features Moira has but competitors implement more completely
   - Notes on known accuracy limitations vs. competitor claims

Appendix A. Competitor Profiles
   - Brief profile per app: feature highlights, notable strengths, limitation notes

Appendix B. Scoring Rationale
   - Full D/C/T justification for every gap in the master list
```

---

## 7. Feature Domains

### Domain 1 — Body Coverage
Planets (classical + modern), lunar/planetary nodes, fixed stars, variable stars, asteroids (main belt, families, classical), centaurs, TNOs, comets, multiple star systems, hypothetical/Uranian bodies.

### Domain 2 — House Systems & Chart Frames
All named house systems (Placidus, Koch, Regiomontanus, Campanus, Morinus, Porphyry, Equal, Whole Sign, Alcabitius, Meridian, Azimuthal, Vehlow, Huber, Gauquelin), derived houses, solar sign frames, relocated chart generation.

### Domain 3 — Aspects, Midpoints & Antiscia
Ptolemaic and modern aspects, parallel and contra-parallel (declination), out-of-bounds planets, aspect patterns (Grand Trine, T-Square, Grand Cross, Yod, Mystic Rectangle, etc.), midpoints (full tree + cosmobiology), antiscia, contra-antiscia.

### Domain 4 — Dignities, Strength & Rulership
Essential dignities (domicile, exaltation, detriment, fall), triplicity systems (Ptolemaic, Dorothean, etc.), Egyptian and Ptolemaic bounds, decanates/faces, almutens, peregrine status, mutual reception, simple and complex dispositor chains, accidental dignities (angular, direct motion, cazimi, visibility).

### Domain 5 — Lots, Parts & Special Points
Arabic/Hellenistic lots (full catalog depth), prenatal syzygy/eclipse degree, vertex, East Point, galactic center, super-galactic center, lunar mansions (Manazil), fixed degree axes.

### Domain 6 — Predictive: Transits & Returns
Transits to natal (ecliptic + equatorial + in-mundo), converse transits, solar returns, lunar returns, planetary returns (all bodies), diurnal charts, annual ingresses (Aries ingress + sign ingresses), eclipse hit lists against natal positions.

### Domain 7 — Predictive: Progressions & Directions
Secondary progressions (forward + converse), tertiary progressions, minor progressions, solar arc (forward + converse), Naibod arc, mean solar arc, one-degree arc, ascendant arc, vertex arc, declination progressions, primary directions (all method variants — Placidus semi-arc, Regiomontanus, Campanus, Topocentric, Morinus, Meridian, Porphyry, Ptolemy, zodiacal + mundane).

### Domain 8 — Predictive: Time Lord Systems
Annual profections, zodiacal releasing, firdaria, decennials, triacontaeteris, Hellenistic planetary distributions (aphesis), Lord of the Year / Lord of the Month, Dashas (all systems), Jaimini chara dasha.

### Domain 9 — Synastry & Relationship Charts
Cross-chart aspect comparison, house overlays (both directions), midpoint composite, reference-place composite, Davison chart (midpoint time + corrected MC-preserving), relationship transits (transit to composite/Davison), synastry progressions.

### Domain 10 — Astronomical Phenomena & Events
Solar and lunar eclipses (contacts, geometry, search, canon), heliacal rises and sets, occultations, retrograde stations, void-of-course Moon, planetary hours, cazimi/combust/under-the-beams thresholds, phase angles and lunar phases, planetary visibility windows.

### Domain 11 — Astrocartography & Spatial Techniques
ACG lines (MC/IC/ASC/DSC/Zenith/Nadir for all bodies), parans, local space charts, geodetic equivalents, in-mundo aspects, relocated chart generation.

### Domain 12 — Vedic / Jyotish Suite
Vargas (all 16+ divisional charts), yoga catalog, Panchanga (tithi, vara, nakshatra, yoga, karana), Jaimini techniques, Krishnamurti Paddhati (KP) system, Tajika annual return system, Ashtakavarga depth, Shadbala completeness.

---

## 8. Known High-Confidence Gaps (Pre-Audit)

These gaps were identified during design from direct code inspection. They appear in the audit with initial scores but are revised once the full matrix is complete.

| Gap | Type | Domain | Initial Priority | Notes |
|---|---|---|---|---|
| Zodiacal Releasing | A | 8 | P1 | High Hellenistic revival demand; Sirius, Janus, Astro-Seek have it; lot infrastructure exists |
| Firdaria | A | 8 | P1 | Persian time lords; Solar Fire, Sirius, Janus, Astro-Seek have it; timelord infrastructure exists |
| Converse Transits | A | 6 | P1 | Standard in all desktop suites; trivial to add given transit engine |
| Solar / Lunar / Planetary Returns | A/B | 6 | P1 | May exist partially; need to verify depth |
| Annual Ingresses | A | 6 | P1 | Aries ingress and sign ingresses; competitive standard |
| Diurnal Charts | A | 6 | P2 | Daily solar return; Solar Fire, Sirius have it |
| Lots catalog depth | B | 5 | P1 | lots.py exists but catalog size vs. Sirius (97+ lots) unverified |
| Almuten calculation | A/B | 4 | P1 | May be partial; high classical demand |
| Decennials | A | 8 | P2 | Hellenistic time lord; Sirius has it |
| KP System | A | 12 | P2 | Significant Vedic sub-system; requires new house + sub-lord dasha layer |
| Tajika system | A | 12 | P2 | Vedic annual return; Sirius has it |
| Yoga catalog | A/B | 12 | P2 | vedic.py exists; yoga catalog depth unknown |
| Synastry progressions | B | 9 | P2 | Cross-chart progressed positions; Solar Fire, Sirius have it |
| Eclipse hit lists | A | 6 | P2 | Scanning upcoming eclipses against natal; common feature |
| In-mundo aspects | A | 11 | P2 | Mundo aspect calculation in primary directions context |
| Dispositor chain analysis | B | 4 | P2 | Dispositorship module depth vs. Solar Fire chain visualization — complex mutual reception chains |
| OOB planet flagging | B | 3 | P2 | May exist; need to verify declination engine surfaces this |

---

## 9. Deliverable

The audit is produced as a single file:  
`wiki/07_audit/FEATURE_AUDIT_2026.md`

It is not a living document — it represents a snapshot. A version field in the header records the audit date and the commit hash of Moira at audit time.

---

## 10. Success Criteria

The audit is complete when:
1. All 12 domain chapters have a filled coverage matrix (no empty cells).
2. The master gap list contains every ✗ and ~ found for Moira across all domains.
3. Every gap in the master list has a D/C/T score and a priority tier.
4. The executive summary reflects the final gap list, not the pre-audit estimates above.
5. The depth/accuracy supplement covers all Type B gaps with a brief note on what's missing.
