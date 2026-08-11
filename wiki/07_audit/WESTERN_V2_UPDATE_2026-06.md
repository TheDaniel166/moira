# Western V2 Update (2026-06)

**Document:** `wiki/07_audit/WESTERN_V2_UPDATE_2026-06.md`  
**Companion to:** [WESTERN_SYSTEMS_AUDIT.md](WESTERN_SYSTEMS_AUDIT.md)
**Purpose:** Narrow corrective update to the broad Western master audit. This document identifies the highest-signal remaining Western gaps after recent houses, spatial, REST-reduction, and small-body work, then proposes a staged roadmap.

> **Current prioritization:** Later implementation closed several gaps recorded
> here. Use the
> [Astrology Coverage Frontier Gap Audit (2026-08)](ASTROLOGY_COVERAGE_FRONTIER_AUDIT_2026-08.md)
> for the current cross-tradition frontier map at commit `c868fd0`.

---

## 1. Scope of This Update

This is not a full re-audit of every Western subsystem.

It is a V2 corrective pass focused on the gaps that remain materially incomplete even after recent closure work:

1. Horary
2. Doctrine-owned Western electional
3. Spatial REST/public exposure
4. Composite/Davison predictive extensions
5. Facade parity for deep primary directions
6. Fixed-star astrocartography parity

The standard for calling something a "gap" here is strict:

- not merely "could be nicer"
- not merely "docs are thin"
- but a real absence in doctrine, runtime surface, or usable public exposure

---

## 2. Method Basis

This update is based on direct repository inspection of:

- `moira/`
- `moira_server/`
- `wiki/`
- existing Western audit documents

No new mathematical or external-source claims are introduced here. This is a code-and-doctrine inventory update.

---

## 3. Corrected Gap Inventory

### A. Horary

**Status:** Major gap  
**Type:** Type A doctrine/runtime gap

**What exists now**

- Horary-tagged lots exist in [moira/lots.py](../../moira/lots.py).
- General tools useful to horary exist elsewhere: houses, dignity, receptions, void-of-course, perfection-like directional logic, etc.

**What is missing**

- No dedicated `moira.horary` subsystem.
- No horary chart judgement surface.
- No significator-assignment doctrine.
- No dedicated question/radicality/house-turning engine.
- No horary-specific facade or REST family.

**Why this is still a true gap**

- The repository has horary ingredients, but not horary as a first-class Western feature family.
- Research notes still explicitly record missing interrogational source acquisition in [LOTS_SOURCE_VERIFICATION.md](../05_research/lots/LOTS_SOURCE_VERIFICATION.md).

---

### B. Doctrine-Owned Western Electional

**Status:** Major gap  
**Type:** Type A/B mixed gap

**What exists now**

- A strong generic electional search engine exists in [moira/electional.py](../../moira/electional.py).
- The public facade exposes electional window search through [moira/_facade_special.py](../../moira/_facade_special.py).

**What is missing**

- No Western electional doctrine layer.
- No built-in Western electional ruleset/profile family.
- No first-class electional scoring/judgement surface comparable to Vedic `muhurta`.
- No REST route family for electional search.

**Why this is still a true gap**

- Current electional is a predicate engine, not a Western doctrine subsystem.
- The contrast with [moira/muhurta.py](../../moira/muhurta.py) is clear: Vedic has explicit classification/scoring, Western does not.

---

### C. Spatial REST/Public Exposure

**Status:** Major gap  
**Type:** Type B exposure gap

**What exists now**

- Strong spatial engine work exists in:
  - [moira/astrocartography.py](../../moira/astrocartography.py)
  - [moira/parans.py](../../moira/parans.py)
  - [moira/geodetic.py](../../moira/geodetic.py)
  - [moira/local_space.py](../../moira/local_space.py)
  - [moira/_facade_spatial.py](../../moira/_facade_spatial.py)

**What is missing**

- No dedicated REST family for astrocartography.
- No REST family for geodetic equivalents.
- No REST family for local-space positions.
- No REST family for relocated chart/spatial composite outputs.

**What is already exposed**

- Paran search is present under phenomena routes in [moira_server/routers/phenomena.py](../../moira_server/routers/phenomena.py).

**Why this is still a true gap**

- The engine/facade layer is materially ahead of the server surface.
- Spatial is now one of the clearest "math exists, public service lags" areas.

---

### D. Composite / Davison Predictive Extensions

**Status:** Major gap  
**Type:** Type A feature gap

**What exists now**

- Synastry core is strong in [moira/synastry.py](../../moira/synastry.py).
- Composite and Davison chart construction exist.
- Synastry condition profiles and network profiles exist.
- Relationship server routes exist in [moira_server/routers/relationship.py](../../moira_server/routers/relationship.py).

**What is missing**

- Transits to composite charts.
- Transits to Davison charts.
- Progression-style predictive families over relationship charts.
- Cross-chart pattern detection as a first-class subsystem.

**Why this is still a true gap**

- Relationship construction is no longer the weak point.
- Predictive relationship-chart work is.

---

### E. Facade Parity for Deep Primary Directions

**Status:** Medium-high gap  
**Type:** Type B public-surface gap

**What exists now**

- The primary-directions engine is deep and method-rich.
- The server now exposes richer route families and reduction surfaces.

**What is missing**

- The `Moira` instance facade still centers a narrow `primary_directions(...)` convenience wrapper in [moira/_facade_special.py](../../moira/_facade_special.py).
- It does not present the full breadth of method/policy families as clean first-class facade entry points.

**Why this is still a true gap**

- Runtime depth exists.
- Public facade ergonomics and doctrinal parity do not yet match that depth.

---

### F. Fixed-Star Astrocartography Parity

**Status:** Medium-high gap  
**Type:** Type A/B mixed gap

**What exists now**

- Fixed-star work is strong in its own domain.
- Paran work already treats named stars seriously in [moira/parans.py](../../moira/parans.py).
- Astrocartography now includes subplanetary points and strengthened small-body handling.

**What is missing**

- No full fixed-star parity across the astrocartography line family.
- Spatial star work is stronger in paran form than in ACG line form.

**Why this is still a true gap**

- Western locational practice often wants both star parans and star mapping.
- Moira currently has the first more strongly than the second.

---

## 4. Priority Ranking

### Tier 1

1. Horary
2. Doctrine-owned Western electional
3. Spatial REST/public exposure

### Tier 2

4. Composite/Davison predictive extensions
5. Facade parity for deep primary directions

### Tier 3

6. Fixed-star astrocartography parity

**Priority logic**

- Tier 1 combines either major doctrinal absence or major user-surface absence.
- Tier 2 has strong engine substrate already, so the work is narrower.
- Tier 3 is real, but depends on finishing the broader spatial and public-surface alignment first.

---

## 5. Western V2 Roadmap

### Wave 1 — Public-Surface Corrections

**Goal:** Close the easiest "engine exists, access lags" gaps.

**Targets**

1. Spatial REST family
   - add routes for astrocartography
   - add routes for geodetic equivalents
   - add routes for local-space outputs
   - decide whether relocated charts belong here or in chart/relationship families

2. Primary-directions facade parity
   - add explicit facade methods for advanced PD search/profile/network surfaces
   - keep current convenience wrapper for backward compatibility

**Why first**

- Lowest doctrinal risk
- High user impact
- Strong existing engine substrate

---

### Wave 2 — Western Electional Doctrine Layer

**Goal:** Convert generic electional search into a Western-owned subsystem.

**Targets**

1. Create doctrine note for Western electional scope
   - what is admitted
   - what is not admitted
   - source hierarchy

2. Add first-class Western electional profile surface
   - explicit rule bundle(s)
   - explicit judgement/profile vessel
   - optional score surface

3. Add REST route family
   - likely sibling to existing predictive/special surfaces

**Why before horary**

- The generic search engine already exists.
- This is a smaller doctrinal lift than full horary.

---

### Wave 3 — Composite / Davison Predictive Layer

**Goal:** Extend relationship charts into predictive Western use.

**Targets**

1. Composite transits
2. Davison transits
3. Relationship-chart predictive profiles
4. Cross-chart patterns, if doctrine can be stated clearly

**Why here**

- Relationship substrate is already mature.
- This is additive rather than foundational.

---

### Wave 4 — Horary Research Gate

**Goal:** Decide whether horary is admissible now, and under what doctrine.

**Required pre-phase work**

1. Source packet
   - significator doctrine
   - house-turning doctrine
   - radicality/admission doctrine
   - judgement scope boundary

2. Explicit admission note
   - what counts as "Moira horary"
   - what remains outside scope

3. Clean first subsystem target
   - likely chart judgement primitives, not a grand all-at-once horary engine

**Why late**

- Highest doctrine risk
- Most likely to drift into hand-wavy interpretation if not source-anchored first

---

### Wave 5 — Fixed-Star Astrocartography

**Goal:** Bring fixed stars into spatial parity where source/doctrine allows.

**Targets**

1. Decide governing object
   - star ACG line family
   - or a more limited admitted star-locational family

2. Align with existing star/paran doctrine
3. Expose through facade and REST only after doctrine is stable

**Why last**

- Depends on broader spatial public-surface cleanup
- Needs careful geometric and doctrinal framing

---

## 6. Recommended Next Actions

If work begins immediately, the clean order is:

1. Spatial REST/public exposure
2. Primary-directions facade parity
3. Western electional doctrine note
4. Composite/Davison predictive design note
5. Horary source packet

This order preserves the repository’s current strengths:

- public truth visibility first
- doctrine before interpretation-heavy admission
- no pretending that "ingredients" already equal a complete subsystem

---

## 7. Truthfulness Notes

- This update does **not** claim that Western coverage is weak overall.
- It claims that these six areas remain the most meaningful Western gaps after recent closure work.
- Several older broad audit concerns are now less urgent than they were when first written, especially in houses, synastry core, and small-body spatial handling.

---

## 8. Suggested Maintenance Rule

When one of the six V2 gaps closes materially:

1. update this file first
2. then reconcile the broader scoring language in `WESTERN_SYSTEMS_AUDIT.md`

This keeps the narrow corrective update from being lost inside the larger master audit.
