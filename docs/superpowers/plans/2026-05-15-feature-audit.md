# Moira Feature Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `wiki/07_audit/FEATURE_AUDIT_2026.md` — a comprehensive feature coverage matrix and prioritized gap list comparing Moira against 8 professional astrology apps across 12 domains.

**Architecture:** Domain-first structure. Each of the 12 domain tasks inspects the relevant Moira Python files directly, assesses each competitor from public documentation, fills a ✓/~/✗/? matrix, and writes gap notes. All gaps roll up to a master list with D+C+T priority scoring.

**Tech Stack:** Read-only codebase inspection (Python source + wiki markdown) + public web research. Output is pure markdown. No code changes to Moira itself.

---

## Pre-Task: Orientation

Before starting any task, read the design spec in full:
`docs/superpowers/specs/2026-05-15-feature-audit-design.md`

Cell scoring: ✓ = full, ~ = partial, ✗ = absent, ? = unclear from docs.  
Gap types: A = missing feature, B = depth gap.  
Priority: score = D + C + T (each 1–3). P1=7–9, P2=5–6, P3=3–4.  
Competitors (columns in every matrix): Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages

**Important discoveries from pre-plan code inspection:**
- `timelords.py` already has **Firdaria** (`firdaria()`) and **Zodiacal Releasing** (`zodiacal_releasing()`) — these are NOT gaps
- `transits.py` already has `solar_return()`, `lunar_return()`, `planet_return()`, `prenatal_syzygy()`, `find_ingresses()` — NOT gaps
- `lots.py` covers ~430 named lots — exceeds competitor catalogs
- No `converse` mode found in `transits.py` — **converse transits ARE a gap**

---

## Task 0: Create Audit File Skeleton

**Files:**
- Create: `wiki/07_audit/FEATURE_AUDIT_2026.md`

- [ ] **Step 1: Write the skeleton**

Write `wiki/07_audit/FEATURE_AUDIT_2026.md` with this exact content:

```markdown
# Moira Feature Audit 2026

**Audit date:** 2026-05-15  
**Moira commit:** <!-- fill: git rev-parse HEAD -->  
**Auditor:** TheDaniel166  
**Method:** 12-domain coverage matrix. Moira assessed from code inspection; competitors from public documentation (manuals, feature pages, tutorials).

**Cell scoring:** ✓ full | ~ partial | ✗ absent | ? unclear  
**Gap types:** A = missing feature | B = depth gap  
**Priority:** D + C + T score → P1 (7–9) | P2 (5–6) | P3 (3–4)

---

## 0. Executive Summary

*Written last — after all domain chapters are complete.*

---

## 1. Body Coverage
<!-- Task 1 -->

## 2. House Systems & Chart Frames
<!-- Task 2 -->

## 3. Aspects, Midpoints & Antiscia
<!-- Task 3 -->

## 4. Dignities, Strength & Rulership
<!-- Task 4 -->

## 5. Lots, Parts & Special Points
<!-- Task 5 -->

## 6. Predictive — Transits & Returns
<!-- Task 6 -->

## 7. Predictive — Progressions & Directions
<!-- Task 7 -->

## 8. Predictive — Time Lord Systems
<!-- Task 8 -->

## 9. Synastry & Relationship Charts
<!-- Task 9 -->

## 10. Astronomical Phenomena & Events
<!-- Task 10 -->

## 11. Astrocartography & Spatial Techniques
<!-- Task 11 -->

## 12. Vedic / Jyotish Suite
<!-- Task 12 -->

---

## 13. Master Gap List
<!-- Task 13 -->

---

## 14. Depth & Accuracy Gap Supplement
<!-- Task 14 -->

---

## 15. Executive Summary
<!-- Task 15 — written last -->

---

## Appendix A: Competitor Profiles
<!-- Task 16 -->

## Appendix B: Scoring Rationale
<!-- Task 16 -->
```

- [ ] **Step 2: Fill the commit hash**

Run: `git rev-parse HEAD`  
Copy the output into the `<!-- fill: ... -->` placeholder on line 4.

- [ ] **Step 3: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: create FEATURE_AUDIT_2026 skeleton"
```

---

## Task 1: Domain 1 — Body Coverage

**Files:**
- Inspect: `moira/planets.py`, `moira/nodes.py`, `moira/asteroids.py`, `moira/asteroid_families.py`, `moira/classical_asteroids.py`, `moira/main_belt.py`, `moira/centaurs.py`, `moira/tno.py`, `moira/comets.py`, `moira/stars.py`, `moira/variable_stars.py`, `moira/royal_stars.py`, `moira/behenian_stars.py`, `moira/multiple_stars.py`, `moira/planetary_nodes.py`, `moira/uranian.py`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 1)

- [ ] **Step 1: Inspect Moira's body coverage**

Read the `__all__` export list and docstring of each file above. For each, note:
- Which bodies are enumerated in `moira/constants.py` `Body` enum
- How many asteroids are accessible (check `ASTEROID_NAIF` dict size in `asteroids.py`)
- Whether Uranian/hypothetical bodies (Cupido, Hades, Zeus, Kronos, Apollon, Admetos, Vulkanus, Poseidon) are in `uranian.py`
- Whether fixed star catalog size is documented in `stars.py` docstring
- Whether comets include periodic comets (Halley, etc.)

- [ ] **Step 2: Replace `<!-- Task 1 -->` with the filled domain chapter**

```markdown
## 1. Body Coverage

Moira's body coverage spans the full solar system: all classical and modern planets,
mean and true nodes (lunar + planetary), a fixed-star catalog (check size from stars.py),
Behenian and Royal stars, variable stars, ~430 asteroid lots catalog, classical asteroids
(Ceres, Pallas, Juno, Vesta), centaurs (Chiron, Pholus, Nessus, Chariklo), TNOs
(Eris, Sedna, Quaoar, Makemake, Haumea), comets, multiple star systems, and
Uranian/Hamburg hypothetical bodies.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Classical planets (Sun–Saturn) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Modern outer planets (Uranus–Pluto) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| True & mean lunar nodes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Black Moon Lilith (mean & true) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✓ |
| Planetary nodes | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Fixed stars (large catalog) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Variable stars | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Classical asteroids (Ceres, Pallas, Juno, Vesta) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Chiron & centaurs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Extended centaurs (Pholus, Nessus, Chariklo) | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |
| TNOs (Eris, Sedna, Quaoar, Makemake, Haumea) | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |
| Main belt / extended asteroid catalog | ✓ | ~ | ✓ | ~ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Comets | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Uranian / Hamburg hypotheticals | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✗ | ✗ | ✗ |
| Multiple star systems | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Solar System Barycenter | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's body coverage is exceptional — it exceeds all 8 competitors in catalog breadth. No Type A gaps identified. Possible Type B: verify exact fixed star count vs. Sirius (which claims the largest commercial catalog). Variable stars, comets, multiple star systems, and SSB are unique to Moira among this competitor set.
```

- [ ] **Step 3: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 1 — body coverage matrix complete"
```

---

## Task 2: Domain 2 — House Systems & Chart Frames

**Files:**
- Inspect: `moira/houses.py` (check `_KNOWN_SYSTEMS` frozenset and `HouseSystem` enum in `moira/constants.py`), `moira/huber.py`, `moira/galactic_houses.py`, `moira/geodetic.py`, `moira/local_space.py`, `moira/gauquelin.py`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 2)

- [ ] **Step 1: Enumerate all implemented house systems**

Read `moira/constants.py` and find the `HouseSystem` enum. List every member. Then check `moira/houses.py` `_KNOWN_SYSTEMS` to confirm which are fully operational vs. fallback. Also check if `moira/houses.py` has Alcabitius, Meridian/Axial Rotation, Azimuthal/Horizontal, Vehlow Equal, and Krusinski systems.

- [ ] **Step 2: Check for derived/relocated chart generation**

Search `moira/synastry.py` and `moira/transits.py` for any function that recasts a chart at a different location. Check `moira/astrocartography.py` for relocated chart generation.

- [ ] **Step 3: Replace `<!-- Task 2 -->` with the filled domain chapter**

```markdown
## 2. House Systems & Chart Frames

Moira implements house cusps via `houses.py` using ARMC, obliquity, and geographic
coordinates. The engine supports fallback from polar-incompatible systems (Placidus,
Koch) to Porphyry above the critical latitude (~66.56°). Huber houses are in a
separate module. Galactic, geodetic, local space, and Gauquelin sectors are also
separate specialized modules.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Placidus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Koch | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Regiomontanus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Campanus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Equal (ASC-based) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Whole Sign | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Porphyry | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Morinus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Alcabitius | <!-- verify in constants.py --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Meridian / Axial Rotation | <!-- verify --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Azimuthal / Horizontal | <!-- verify --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Vehlow Equal | <!-- verify --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Krusinski / Poli-Goeldi | <!-- verify --> | ✓ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Huber / age progressions | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Gauquelin sectors | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Galactic houses | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Geodetic houses | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Local space frame | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Solar sign frame (Sun on cusp 1) | <!-- verify --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Derived houses (from any cusp) | <!-- verify --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |

**Gap notes:**  
Replace all `<!-- verify -->` cells by inspecting `moira/constants.py` HouseSystem enum. Any system listed there as present in competitors but absent in Moira's enum is a gap. Likely gaps: Alcabitius (check), solar sign frame (check), derived houses. Galactic houses are a unique Moira strength.
```

- [ ] **Step 4: Replace all `<!-- verify -->` cells**

After inspecting `moira/constants.py`, update each `<!-- verify -->` cell with ✓, ~, or ✗.

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 2 — house systems matrix complete"
```

---

## Task 3: Domain 3 — Aspects, Midpoints & Antiscia

**Files:**
- Inspect: `moira/aspects.py`, `moira/midpoints.py`, `moira/antiscia.py`, `moira/patterns.py`, `moira/transits_equatorial.py`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 3)

- [ ] **Step 1: Check OOB planet detection**

Search `moira/transits_equatorial.py` and `moira/aspects.py` for any reference to `out_of_bounds`, `oob`, or declination > 23.5. If absent, this is a gap.

- [ ] **Step 2: Check contra-parallel and parallel detection**

Search `moira/aspects.py` and `moira/transits_equatorial.py` for `parallel` and `contra_parallel`. Verify they produce aspect events, not just longitudinal crossings.

- [ ] **Step 3: Replace `<!-- Task 3 -->` with the filled domain chapter**

```markdown
## 3. Aspects, Midpoints & Antiscia

`aspects.py` handles longitudinal aspect detection. `midpoints.py` covers midpoint
trees and cosmobiology. `antiscia.py` covers solstice points and contra-antiscia.
`patterns.py` identifies aspect patterns (Grand Trine, T-Square, Grand Cross, Yod,
Mystic Rectangle, Kite, etc.). `transits_equatorial.py` covers declination-based
aspects (parallel, contra-parallel).

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Ptolemaic aspects (conjunction–opposition) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Modern aspects (quintile, septile, novile, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Parallel (declination) | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Contra-parallel | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Out-of-bounds planet flagging | <!-- verify step 1 --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ~ |
| Antiscia (solstice points) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Contra-antiscia | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Midpoints (full 45° sort) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Cosmobiology (midpoint trees, pictures) | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Aspect patterns (Grand Trine, T-Square, etc.) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ~ | ✓ |
| Yod / Finger of God | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ |
| Declination aspect search (transit parallels) | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |

**Gap notes:**  
Replace `<!-- verify -->` cells from step 1 and step 2 findings. Key gap to confirm: OOB planet flagging. If `transits_equatorial.py` does not flag OOB (declination > obliquity), this is a Type A gap, D=2, C=5, T=3 → P1 (score 8... but only if absent).
```

- [ ] **Step 4: Replace all `<!-- verify -->` cells and write final gap notes**

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 3 — aspects matrix complete"
```

---

## Task 4: Domain 4 — Dignities, Strength & Rulership

**Files:**
- Inspect: `moira/dignities.py`, `moira/dignities_types.py`, `moira/triplicity.py`, `moira/egyptian_bounds.py`, `moira/decanates.py`, `moira/hermetic_decans.py`, `wiki/02_standards/DIGNITIES_BACKEND_STANDARD.md`, `wiki/02_standards/DISPOSITORSHIP_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 4)

- [ ] **Step 1: Check almuten calculation**

Search `moira/dignities.py` for `almuten` or `almutem`. If absent, this is a gap.

- [ ] **Step 2: Check peregrine flagging**

Search `moira/dignities.py` for `peregrine`. If absent, this is a gap.

- [ ] **Step 3: Check mutual reception and dispositor chains**

Search `moira/dispatch.py` (dispositorship module) for `mutual_reception`, `dispositor_chain`, and `final_dispositor`. Note the depth: simple 1-step mutual reception vs. complex chain tracing.

- [ ] **Step 4: Replace `<!-- Task 4 -->` with the filled domain chapter**

```markdown
## 4. Dignities, Strength & Rulership

`dignities.py` covers essential dignities (domicile, exaltation, detriment, fall).
`triplicity.py` covers triplicity lords across multiple systems (Ptolemaic, Dorothean,
Lilly). `egyptian_bounds.py` covers Egyptian and Ptolemaic bounds. `decanates.py`
and `hermetic_decans.py` cover decans/faces. The dispositorship module covers rulership
chains. `wiki/02_standards/DIGNITIES_BACKEND_STANDARD.md` is authoritative.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Domicile / rulership | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exaltation / fall | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Detriment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Triplicity lords (Ptolemaic) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Triplicity lords (Dorothean / Lilly) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ✗ |
| Egyptian / Ptolemaic bounds | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Decanates / faces | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Hermetic decanates | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Almuten calculation | <!-- verify step 1 --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Peregrine status | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Mutual reception | <!-- verify step 3 --> | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |
| Dispositor chain / final dispositor | <!-- verify step 3 --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Accidental dignities (angularity, direct motion) | <!-- check dignities.py --> | ✓ | ✓ | ✓ | ~ | ~ | ~ | ✗ | ~ |
| Cazimi / combust / under beams | <!-- check dignities.py or phenomena.py --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Sect (diurnal/nocturnal) | <!-- check dignities.py --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
Replace all `<!-- verify -->` cells. Almuten is P1 if absent (D=3, C=6, T=3 → score 9). Peregrine and sect are similarly high-value classical features. Dispositorship depth (chain vs. simple step) may be a Type B gap even if present.
```

- [ ] **Step 5: Replace all `<!-- verify -->` cells and finalize gap notes**

- [ ] **Step 6: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 4 — dignities matrix complete"
```

---

## Task 5: Domain 5 — Lots, Parts & Special Points

**Files:**
- Inspect: `moira/lots.py` (catalog size from docstring), `moira/nine_parts.py`, `moira/manazil.py`, `moira/nodes.py` (prenatal syzygy already in transits.py), `wiki/02_standards/LOTS_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 5)

- [ ] **Step 1: Confirm lot catalog size**

Read `moira/lots.py` docstring — it says "~430 named lots." Confirm this is correct by checking if the catalog is defined in lots.py or imported from a data file. Also check: does Moira compute lots for sect (day/night reversal)? Does it handle derived lot references (lots whose formula references another lot)?

- [ ] **Step 2: Check Vertex and East Point**

Search `moira/houses.py` or `moira/constants.py` for `vertex`, `east_point`, `equatorial_asc`. Note which are computed.

- [ ] **Step 3: Check prenatal eclipse degree**

`transits.py` has `prenatal_syzygy()`. Verify it returns a degree position usable as a sensitive point, not just a date.

- [ ] **Step 4: Replace `<!-- Task 5 -->` with the filled domain chapter**

```markdown
## 5. Lots, Parts & Special Points

`lots.py` implements ~430 named Arabic/Hellenistic lots using ASC + Add − Subtract
with automatic day/night reversal and support for derived lot references. `nine_parts.py`
covers the novenaria (ninth-parts). `manazil.py` covers the 28 Arabic lunar mansions.
`transits.py` computes the prenatal syzygy (last new/full moon before birth).

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Lot of Fortune | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Lot of Spirit | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Full Arabic lots catalog (100+) | ✓ (~430) | ~ (~50) | ✓ (~97) | ~ (~40) | ~ | ✓ | ✗ | ✗ | ✗ |
| Day/night sect reversal for lots | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✗ | ✗ |
| Derived lot references | ✓ | ~ | ✓ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| Nine Parts / Novenaria | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Lunar Mansions (Manazil) | ✓ | ~ | ✓ | ~ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Vertex | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| East Point / Equatorial ASC | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Prenatal syzygy degree | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Galactic Center as sensitive point | ✓ | ~ | ✓ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| Super-Galactic Center | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's lot catalog (430+) exceeds all competitors. Verify Vertex and East Point presence. If Vertex is absent, that is a Type A gap, D=3, C=7 → likely P1. East Point similarly.
```

- [ ] **Step 5: Replace all `<!-- verify -->` cells and finalize**

- [ ] **Step 6: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 5 — lots and special points matrix complete"
```

---

## Task 6: Domain 6 — Predictive: Transits & Returns

**Files:**
- Inspect: `moira/transits.py` (read full `__all__` and docstring carefully), `moira/transits_aspects.py`, `moira/transits_equatorial.py`, `moira/transits_houses.py`, `wiki/02_standards/TRANSITS_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 6)

- [ ] **Step 1: Confirm what's in transits.py**

Already confirmed from pre-plan inspection: `solar_return()`, `lunar_return()`, `planet_return()`, `prenatal_syzygy()`, `find_ingresses()`, `find_transits()`, `next_transit()`. Verify: does `find_transits()` support a `direction=-1` or `converse=True` parameter for converse transits? If not, converse transits are a gap.

- [ ] **Step 2: Check eclipse hit lists**

Search `moira/eclipse_search.py` or `moira/transits.py` for any function that scans upcoming eclipses and returns which natal positions they hit. This is different from finding eclipses; it's matching eclipses to natal chart.

- [ ] **Step 3: Check diurnal charts**

Search across all moira files for `diurnal`. A diurnal chart is the solar return for the current day (Sun returns to its natal position each day at the observer's location).

- [ ] **Step 4: Replace `<!-- Task 6 -->` with the filled domain chapter**

```markdown
## 6. Predictive — Transits & Returns

`transits.py` owns longitude-crossing detection, sign ingress search, solar/lunar/
planetary return computation, and prenatal syzygy. `transits_aspects.py` handles
transit-to-natal aspect events. `transits_equatorial.py` handles equatorial transits
including declination parallels. `transits_houses.py` handles transit-through-house events.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Transits to natal (ecliptic) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Transits through houses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Transit aspects (aspect search) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Equatorial / declination transits | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |
| Converse transits | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Sign ingresses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Annual ingresses (Aries ingress, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Solar return | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Lunar return | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Planetary returns (all bodies) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ~ |
| Diurnal chart (daily solar return) | <!-- verify step 3 --> | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Eclipse hit list (upcoming eclipses to natal) | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prenatal syzygy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
**Converse transits** confirmed absent — Type A, D=3, C=5, T=3, score=9 → **P1**.  
Diurnal chart: verify from step 3. If absent, Type A, D=2, C=4, T=3, score=7 → P1.  
Eclipse hit list: verify from step 2. If absent, Type A, D=2, C=4, T=2, score=6 → P2.
```

- [ ] **Step 5: Replace all `<!-- verify -->` cells and finalize**

- [ ] **Step 6: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 6 — transits and returns matrix complete"
```

---

## Task 7: Domain 7 — Predictive: Progressions & Directions

**Files:**
- Inspect: `moira/progressions.py` (read full docstring), `wiki/02_standards/PROGRESSIONS_BACKEND_STANDARD.md`, `wiki/02_standards/PRIMARY_DIRECTIONS_BACKEND_STANDARD.md`, `wiki/01_doctrines/primary_directions/`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 7)

- [ ] **Step 1: Enumerate all progression types from progressions.py docstring**

The docstring lists all implemented techniques. Copy them into the matrix. Confirmed from pre-plan: secondary, tertiary, tertiary II, minor, solar arc, Naibod, mean solar arc, one-degree, ascendant arc, vertex arc, declination progressions — all in forward and converse forms.

- [ ] **Step 2: Enumerate primary direction methods**

Read `wiki/02_standards/PRIMARY_DIRECTIONS_BACKEND_STANDARD.md` for the list of methods (Placidus semi-arc, Ptolemy, Regiomontanus, Campanus, Topocentric, Morinus, Meridian, Porphyry + zodiacal + mundane + parallels + antiscia). List which are fully implemented vs. experimental.

- [ ] **Step 3: Replace `<!-- Task 7 -->` with the filled domain chapter**

```markdown
## 7. Predictive — Progressions & Directions

`progressions.py` implements the full progression engine. Primary directions are
governed by their own backend standard and wiki doctrine. Both forward and converse
forms are available for all progression families.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Secondary progressions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Converse secondary progressions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Tertiary progressions | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Minor progressions | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Solar arc directions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Naibod arc | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Mean solar arc | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| One-degree arc | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Ascendant arc | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Vertex arc | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Declination progressions (Jayne) | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Progressed house frames (daily houses) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✗ | ✓ |
| Primary directions — Placidus semi-arc | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Regiomontanus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Campanus | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Topocentric | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Morinus | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Zodiacal | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Mundane | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Parallels | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Fixed stars as promissors | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Converse primary directions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
Moira's progression and primary directions coverage is exceptional — matches or exceeds all competitors. No Type A gaps anticipated. Review primary directions wiki doctrine for any methods marked experimental or incomplete; those are Type B candidates.
```

- [ ] **Step 4: Update any cells marked uncertain after reading the primary directions standard**

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 7 — progressions and directions matrix complete"
```

---

## Task 8: Domain 8 — Predictive: Time Lord Systems

**Files:**
- Inspect: `moira/timelords.py` (read full `__all__` and docstring), `moira/profections.py`, `moira/lord_of_the_orb.py`, `moira/lord_of_the_turn.py`, `moira/dasha.py`, `moira/dasha_systems.py`, `wiki/02_standards/TIMELORDS_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 8)

- [ ] **Step 1: Enumerate timelord systems from timelords.py**

Confirmed from pre-plan: Firdaria (diurnal, nocturnal, Bonatti variant) and Zodiacal Releasing are both in `timelords.py`. Also verify: are Decennials and Triacontaeteris present? Check for `decennials`, `triacontaeteris`, or `distribution` (Hellenistic aphesis) in the file.

- [ ] **Step 2: Check Lord of the Year / Lord of the Month**

Read `moira/lord_of_the_orb.py` and `moira/lord_of_the_turn.py` docstrings. Verify these are distinct from Firdaria lords and represent the solar return / monthly time lord systems.

- [ ] **Step 3: Replace `<!-- Task 8 -->` with the filled domain chapter**

```markdown
## 8. Predictive — Time Lord Systems

`timelords.py` implements Firdaria (three sequence variants: diurnal, nocturnal,
Bonatti) and Zodiacal Releasing (with angularity classification). `profections.py`
governs annual profections. `lord_of_the_orb.py` and `lord_of_the_turn.py` implement
their respective Hellenistic time lord techniques. `dasha.py` and `dasha_systems.py`
govern the Vedic dasha family.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Annual profections | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ~ |
| Monthly profections | <!-- check profections.py --> | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Firdaria (diurnal) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Firdaria (nocturnal) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Firdaria (Bonatti variant) | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Zodiacal Releasing | ✓ | ✗ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Lord of the Orb | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Lord of the Turn | ✓ | ~ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Decennials | <!-- verify step 1 --> | ✗ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Triacontaeteris (30-yr periods) | <!-- verify step 1 --> | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Hellenistic aphesis / distributions | <!-- verify step 1 --> | ✗ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vimshottari dasha | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Multiple Vedic dasha systems | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Jaimini Chara Dasha | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira has an outstanding time lord suite. Verify Decennials, Triacontaeteris, and Aphesis from step 1. If Decennials are absent: Type A, D=2, C=3, T=3, score=8 → P1. If Triacontaeteris absent: Type A, D=1, C=2, T=3, score=6 → P2.
```

- [ ] **Step 4: Replace all `<!-- verify -->` cells**

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 8 — time lord systems matrix complete"
```

---

## Task 9: Domain 9 — Synastry & Relationship Charts

**Files:**
- Inspect: `moira/synastry.py`, `wiki/02_standards/SYNASTRY_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 9)

- [ ] **Step 1: Check synastry progressions**

Search `moira/synastry.py` for any function that takes a progressed chart as input for cross-chart comparison. Solar Fire and Sirius support "progressed chart vs. natal" synastry. If absent, this is a Type B gap.

- [ ] **Step 2: Check relationship transits**

Search for any function that transits a third chart (composite or Davison) rather than a natal chart. If absent, this is a Type B gap.

- [ ] **Step 3: Replace `<!-- Task 9 -->` with the filled domain chapter**

```markdown
## 9. Synastry & Relationship Charts

`synastry.py` implements cross-chart aspects, house overlays (both directions),
midpoint composite, reference-place composite, Davison chart (midpoint time +
corrected MC-preserving search). Governed by `wiki/02_standards/SYNASTRY_BACKEND_STANDARD.md`.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Cross-chart aspects (synastry grid) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| House overlays (A→B and B→A) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Midpoint composite chart | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Reference-place composite | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Davison chart (midpoint time) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Davison chart (MC-corrected) | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Progressed synastry (prog. chart vs. natal) | <!-- verify step 1 --> | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ~ |
| Transits to composite / Davison | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Synastry aspect patterns | <!-- check synastry.py --> | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |

**Gap notes:**  
Core synastry is strong. Key depth gap candidates: progressed synastry and transits to composite. If absent, progressed synastry is Type B, D=2, C=4, T=2, score=8 → P1.
```

- [ ] **Step 4: Replace all `<!-- verify -->` cells**

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 9 — synastry matrix complete"
```

---

## Task 10: Domain 10 — Astronomical Phenomena & Events

**Files:**
- Inspect: `moira/eclipse.py`, `moira/eclipse_search.py`, `moira/eclipse_contacts.py`, `moira/heliacal.py`, `moira/occultations.py`, `moira/rise_set.py`, `moira/phenomena.py`, `moira/phase.py`, `moira/planetary_hours.py`, `moira/void_of_course.py`, `moira/stations.py`, `wiki/02_standards/ECLIPSE_MODEL_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 10)

- [ ] **Step 1: Verify cazimi / combust / under beams**

If not confirmed in Task 4 step 5, search `moira/phenomena.py` and `moira/dignities.py` for `cazimi`, `combust`, `under_beams`, `beams`. Note the degree thresholds used.

- [ ] **Step 2: Check planetary visibility windows**

Search `moira/visibility.py` and `moira/heliacal.py` for whether Moira can return a date range during which a planet is visible above the horizon before dawn / after dusk — not just the heliacal rising event itself.

- [ ] **Step 3: Replace `<!-- Task 10 -->` with the filled domain chapter**

```markdown
## 10. Astronomical Phenomena & Events

Eclipse suite: `eclipse.py` (contacts), `eclipse_geometry.py` (geometry), `eclipse_search.py`
(event search), `eclipse_canon.py` (historical catalog). Heliacal rises/sets: `heliacal.py`
(C++ native LOLA backend). Occultations: `occultations.py`. Station detection: `stations.py`.
Void of course: `void_of_course.py`. Planetary hours: `planetary_hours.py`. Phase angles:
`phase.py`. General phenomena: `phenomena.py`.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Solar eclipses (search + contacts + geometry) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Lunar eclipses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Eclipse canon (historical catalog) | ✓ | ~ | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ |
| Heliacal rises and sets | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Occultations | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Retrograde stations (Rx / Direct) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Void of course Moon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Planetary hours | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ~ |
| Cazimi / combust / under beams | <!-- verify step 1 --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Phase angles (elongation, illumination %) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ~ |
| Lunar phase (new, crescent, quarter, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Planetary visibility windows | <!-- verify step 2 --> | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Rise / set / culmination times | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |

**Gap notes:**  
Eclipse suite is comprehensive. Fill cazimi/combust from step 1 (likely ✓ from phenomena.py). Planetary visibility windows: if step 2 shows only the event (not a range), mark as ~ (partial) — depth gap Type B.
```

- [ ] **Step 4: Replace all `<!-- verify -->` cells**

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 10 — phenomena matrix complete"
```

---

## Task 11: Domain 11 — Astrocartography & Spatial Techniques

**Files:**
- Inspect: `moira/astrocartography.py`, `moira/parans.py`, `moira/geodetic.py`, `moira/local_space.py`, `wiki/02_standards/PARANS_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 11)

- [ ] **Step 1: Check in-mundo aspects**

Search `moira/astrocartography.py` and `src/native/include/cartography.hpp` for `in_mundo` or `mundo_aspect`. In-mundo aspects are angular relationships computed in the sphere of the houses rather than the ecliptic, used in primary directions and ACG analysis.

- [ ] **Step 2: Check whether all bodies get ACG lines**

Read `moira/astrocartography.py` docstring or function signatures. Verify it handles asteroids, fixed stars, and nodes — not just planets.

- [ ] **Step 3: Replace `<!-- Task 11 -->` with the filled domain chapter**

```markdown
## 11. Astrocartography & Spatial Techniques

`astrocartography.py` computes MC/IC/ASC/DSC/Zenith/Nadir lines with topocentric support.
`parans.py` covers latitude-based paran crossings. `geodetic.py` provides geodetic
equivalents. `local_space.py` provides azimuth-based local space charts. The C++ native
backend (`cartography.hpp`) provides the low-level computation.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ACG lines (MC / IC / ASC / DSC) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| ACG Zenith / Nadir lines | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✗ | ✗ | ✗ |
| ACG for asteroids / fixed stars | <!-- verify step 2 --> | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Parans | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Local space charts | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Geodetic equivalents | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| In-mundo aspects | <!-- verify step 1 --> | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Relocated chart generation | <!-- check if any module recasts a chart at new coords --> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Gap notes:**  
Core ACG and parans are solid. In-mundo aspects: if absent, Type A, D=2, C=4, T=2, score=8 → P1. Relocated chart: verify whether Moira exposes a single function to recast a natal chart at a new location or requires manual assembly.
```

- [ ] **Step 4: Replace all `<!-- verify -->` cells**

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 11 — astrocartography matrix complete"
```

---

## Task 12: Domain 12 — Vedic / Jyotish Suite

**Files:**
- Inspect: `moira/vedic.py`, `moira/vedic_dignities.py`, `moira/shadbala.py`, `moira/ashtakavarga.py`, `moira/jaimini.py`, `moira/panchanga.py`, `moira/dasha.py`, `moira/dasha_systems.py`, `moira/varga.py`, `wiki/02_standards/SHADBALA_BACKEND_STANDARD.md`, `wiki/02_standards/JAIMINI_BACKEND_STANDARD.md`, `wiki/02_standards/PANCHANGA_BACKEND_STANDARD.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 12)

- [ ] **Step 1: Count vargas in varga.py**

Read `moira/varga.py` docstring or `__all__`. Count how many divisional charts are implemented (D-1 through D-60). Professional apps typically have D-1 through D-12; Sirius claims all 16 standard vargas. Moira should match or exceed this.

- [ ] **Step 2: Check yoga catalog**

Search `moira/vedic.py` for `yoga` definitions. Count how many named yogas are implemented. Sirius claims 100+ yogas. If Moira's catalog is substantially smaller, this is a Type B gap.

- [ ] **Step 3: Check KP System**

Search all moira files for `kp`, `krishnamurti`, `sub_lord`, `sublord`. If absent, this is a Type A gap.

- [ ] **Step 4: Check Tajika**

Search all moira files for `tajika`. If absent, this is a Type A gap.

- [ ] **Step 5: Replace `<!-- Task 12 -->` with the filled domain chapter**

```markdown
## 12. Vedic / Jyotish Suite

`vedic.py` provides the main Vedic calculation surface. `varga.py` implements
divisional charts. `shadbala.py` implements the six-fold strength system.
`ashtakavarga.py` implements the eight-source point contribution system.
`jaimini.py` implements Jaimini-specific techniques. `panchanga.py` implements
the five Vedic calendar elements. `dasha.py` and `dasha_systems.py` implement
the full dasha family.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Vedic natal chart (sidereal) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| Vargas / divisional charts (D-1 to D-12) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ~ |
| Extended vargas (D-16 to D-60) | <!-- verify step 1 --> | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vimshottari dasha | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| Multiple dasha systems | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Jaimini Chara Dasha | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Jaimini other techniques | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Shadbala (six-fold strength) | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Ashtakavarga | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Panchanga (all 5 elements) | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |
| Yoga catalog | <!-- verify step 2 --> | ~ | ✓ (~100+) | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vedic dignities (uccha, neecha, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| KP System (Krishnamurti Paddhati) | <!-- verify step 3 --> | ✓ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Tajika (Vedic annual return) | <!-- verify step 4 --> | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's Vedic suite is deep. Key gaps to confirm: KP System (if absent: Type A, D=2, C=2, T=1, score=5 → P2), Tajika (if absent: Type A, D=2, C=2, T=2, score=6 → P2), yoga catalog depth (if shallow: Type B). Replace all `<!-- verify -->` cells from steps 1–4.
```

- [ ] **Step 6: Replace all `<!-- verify -->` cells**

- [ ] **Step 7: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: domain 12 — vedic suite matrix complete"
```

---

## Task 13: Master Gap List

**Files:**
- Read: all 12 domain chapters in `wiki/07_audit/FEATURE_AUDIT_2026.md`
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 13)

- [ ] **Step 1: Collect all gaps**

Scan every domain chapter. For every cell in the Moira column that is ✗ or ~, create a gap entry. Type A = ✗, Type B = ~. Also include any depth gaps called out in the gap notes sections.

- [ ] **Step 2: Score each gap**

For each gap, assign D (1–3), C (1–3), T (1–3) and compute the total. Use these guidelines:

**D (Professional Demand):**
- 3 = used by most practising astrologers (profections, solar arc, transits)
- 2 = used by specialists (decennials, in-mundo aspects, yoga catalog)
- 1 = niche (triacontaeteris, super-galactic center, Tajika)

**C (Competitive Coverage — out of 8 competitors):**
- 3 = 6–8 competitors have it
- 2 = 3–5 competitors have it
- 1 = 1–2 competitors have it (map to 1 even if only Sirius)

**T (Tractability):**
- 3 = direct extension of existing code (add a parameter, add a catalog entry)
- 2 = new module but existing infrastructure covers the math
- 1 = requires new foundational subsystem

- [ ] **Step 3: Replace `<!-- Task 13 -->` with the master gap list table**

Format:

```markdown
## 13. Master Gap List

| # | Gap | Type | Domain | D | C | T | Score | Priority | Note |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 1 | Converse transits | A | 6 | 3 | 5→2 | 3 | 8 | **P1** | No converse mode in find_transits(). Add direction=-1 parameter. |
| … | … | … | … | … | … | … | … | … | … |
```

List all gaps sorted by: P1 first (score desc), then P2 (score desc), then P3 (score desc).

- [ ] **Step 4: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: master gap list complete with D/C/T scoring"
```

---

## Task 14: Depth & Accuracy Gap Supplement

**Files:**
- Read: all domain chapters, particularly gap notes mentioning Type B
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 14)

- [ ] **Step 1: Collect all Type B gaps from domain chapters**

List every feature where Moira has ~ (partial) in its column. For each, write 2–3 sentences explaining:
- What Moira currently provides
- What competitors provide that Moira doesn't reach
- What would close the gap (specific addition needed)

- [ ] **Step 2: Replace `<!-- Task 14 -->` with the supplement**

```markdown
## 14. Depth & Accuracy Gap Supplement

These are features Moira implements but at lesser depth, narrower method coverage,
or fewer variants than the leading competitors.

### B1 — [Feature name]
**Current state:** Moira provides [X].  
**Competitor standard:** Sirius / Solar Fire provide [Y].  
**Gap:** [What's missing].

### B2 — …
```

- [ ] **Step 3: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: depth and accuracy gap supplement complete"
```

---

## Task 15: Executive Summary

**Files:**
- Read: master gap list (Task 13), all domain chapters
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (section 0)

- [ ] **Step 1: Compute domain coverage scores**

For each of the 12 domains, count: (a) features where Moira = ✓, (b) features where Moira = ~, (c) features where Moira = ✗. Express as a coverage percentage: (✓ + 0.5×~) / total rows.

- [ ] **Step 2: Identify top 10 gaps**

Take the top 10 entries from the master gap list by score (P1 first, then by score descending within each tier).

- [ ] **Step 3: Identify quick wins**

From the master gap list, select all P1 gaps where T=3 (tractable with existing infrastructure). These are the quick wins.

- [ ] **Step 4: Replace the `*Written last*` placeholder in section 0 with the executive summary**

```markdown
## 0. Executive Summary

**Overall assessment:** Moira is among the most computationally comprehensive astrology
engines available. Coverage is exceptional in body catalog, progressions/directions,
lots, and the Vedic suite. Primary gaps concentrate in [summary of top domains with gaps].

### Domain Coverage Scores

| Domain | ✓ | ~ | ✗ | Score |
|---|:---:|:---:|:---:|:---:|
| 1. Body Coverage | N | N | N | XX% |
| … | | | | |

### Top 10 Gaps by Priority

1. [Gap name] — P1, score N — [one-line description]
2. …

### Quick Wins (P1, T=3)

- [Gap name]: [one sentence on what to add]
- …
```

- [ ] **Step 5: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: executive summary complete"
```

---

## Task 16: Competitor Profiles & Scoring Rationale Appendix

**Files:**
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md` (Appendix A and B)

- [ ] **Step 1: Write Appendix A — Competitor Profiles**

For each of the 8 competitors, write a brief profile (6–10 lines):

```markdown
### Solar Fire (Esoteric Technologies)
**Tier:** Professional desktop  
**Strengths:** [2–3 key strengths from the matrix — where it scores ✓ most consistently]  
**Notable gaps vs. Moira:** [features where Solar Fire scored ✗ but Moira ✓]  
**Reference:** Solar Fire v9 feature list, user manual (public PDF)
```

Repeat for all 8 competitors.

- [ ] **Step 2: Write Appendix B — Scoring Rationale**

For every gap in the master gap list, write a one-line D/C/T justification:

```markdown
| Gap | D rationale | C rationale | T rationale |
|---|---|---|---|
| Converse transits | D=3: used by nearly all practitioners doing predictive work | C=2: Solar Fire, Sirius, Janus, Astro-Seek, Morinus have it (5 of 8) | T=3: add `direction` param to existing `find_transits()` |
```

- [ ] **Step 3: Commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md
git commit -m "audit: competitor profiles and scoring rationale appendix complete"
```

---

## Task 17: Final Self-Review and Polish

**Files:**
- Read: `wiki/07_audit/FEATURE_AUDIT_2026.md` in full
- Modify: `wiki/07_audit/FEATURE_AUDIT_2026.md`

- [ ] **Step 1: Completeness check**

Scan every `<!-- -->` comment left in the file. There should be none. If any remain, fill them now.

- [ ] **Step 2: Internal consistency check**

Pick 5 gaps from the master gap list and verify their cells in the corresponding domain matrix match. If a gap is listed as Type A (missing from Moira), the Moira column in that domain should show ✗.

- [ ] **Step 3: Scoring spot-check**

Pick 3 P1 gaps and re-verify the D, C, T values add up to the listed score. Fix any arithmetic errors.

- [ ] **Step 4: Update the spec's pre-audit section**

Edit `docs/superpowers/specs/2026-05-15-feature-audit-design.md` section 8 to correct the pre-audit estimates that proved wrong (Firdaria and Zodiacal Releasing are NOT gaps, lots catalog is NOT a gap).

- [ ] **Step 5: Final commit**

```
git add wiki/07_audit/FEATURE_AUDIT_2026.md docs/superpowers/specs/2026-05-15-feature-audit-design.md
git commit -m "audit: final review complete — FEATURE_AUDIT_2026 ready"
```
