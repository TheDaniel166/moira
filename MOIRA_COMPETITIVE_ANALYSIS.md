# Moira Computational API: Competitive Analysis & Gap Assessment

**Date:** May 25, 2026 (updated from April 28, 2026)
**Purpose:** Identify gaps, overlaps, and strategic opportunities for Moira as a computational core offering

---

## What Changed Since April 2026

Three major developments close or substantially narrow the gaps identified in the prior analysis:

1. **Batch Operations API implemented** — `moira/batch.py` ships 8 batch functions covering charts, events, transits, returns, progressions (40 techniques), ingresses, void-of-course, and time series. Gap #1 is closed.
2. **C++ native evaluation layer added** — A hybrid Python/C++ architecture now underpins SPK polynomial evaluation, fixed star propagation, topocentric correction, and event search, with AVX2 SIMD acceleration and thread-safe caching. This creates a new competitive advantage and changes the "Pure Python" positioning.
3. **Vedic depth expanded substantially** — Full Shadbala, Ashtakavarga, Panchanga, Jaimini Karakas, Vedic dignities, Ashtottari Dasha, and Yogini Dasha are now implemented. The remaining Vedic gap is now concentrated in specialized doctrine layers such as Tajika/Varshaphal, KP, natal yoga catalogs, Jaimini Chara Dasha, and Muhurta workflows.

---

## Executive Summary

Moira is **astronomically comprehensive**, **computationally transparent**, and now **batch-capable** in ways that professional astrology software is not. The remaining strategic gaps are:

1. **Vedic Completeness** — Core Jyotish infrastructure is strong, but Tajika/Varshaphal, KP, Jaimini Chara Dasha, natal yoga catalogs, Muhurta workflows, and birth time rectification remain absent
2. **REST API / Service Layer** — No HTTP interface; still Python-library-only
3. **Report Generation & Templating** — No HTML/PDF report output
4. **Research & Statistical Tools** — No chart database, filtering, or aggregation layer
5. **Relationship & Synastry Automation** — No batch synastry or compatibility scoring
6. **Chart Data Persistence** — No storage layer or chart versioning
7. **Interpretive Synthesis** — No text interpretation layer (intentional; see positioning)

---

## Moira's Computational Strengths

### Astronomy Foundation (Unmatched)
- **JPL DE441 kernel** with explicit light-time iteration, gravitational deflection, annual aberration
- **IAU 2006 frame bias, precession, nutation** with full 1365 lunisolar + 687 planetary terms
- **Topocentric parallax** (WGS-84) and atmospheric refraction
- **Validation against ERFA/SOFA** with documented residuals
- **Python-native API** with inspectable intermediate stages

### C++ Native Acceleration Layer (New)
- **Hybrid Python/C++ architecture** — Python surface backed by sovereign C++ computational core
- **AVX2/SIMD-accelerated Chebyshev evaluation** (SPK Type 2/3 segments)
- **Lagrange interpolation in C++** (SPK Type 13 segments — comet and irregular body orbits)
- **Native NAIF DAF/SPK reader** — Moira owns the file format parsing path
- **Native NAIF LSK parser and physical delta-T** — sovereign time conversion chain
- **Thread-safe evaluator hierarchy** with mutex-guarded single-element cache
- **Composite evaluator DAG** (RelativeEvaluator, SumEvaluator, TopocentricEvaluator) — center-chaining and topocentric correction in C++
- **FixedStarEvaluator** — proper motion, parallax, and radial velocity propagation in C++
- **Thread pool for parallel event search** — `search_pool.hpp`
- This architecture is superior to thin wrappers around an external C library (e.g., pyswisseph): Moira's Python API is backed by a fully sovereign C++ kernel, not delegated to a third-party binary

### Planetary & Stellar Coverage
- **1,809 named fixed stars** with proper motion, parallax, epoch propagation
- **Classical asteroids** (Ceres, Pallas, Juno, Vesta) + **Centaurs** (Chiron, Pholus, Chariklo, Asbolus, Hylonome)
- **Trans-Neptunians** (Ixion, Quaoar, Varuna, Orcus)
- **Uranian/Hamburg bodies** (Cupido through Poseidon)
- **Lunar nodes, apsides, True/Mean Lilith**
- **Variable stars** (Algol phase engine)
- **Multiple star systems** (Sirius AB, Alpha Centauri AB)
- **User-supplied `.bsp` kernels** for 887,000+ numbered minor planets
- **Comets** with native NAIF ID registry
- **Asteroid families** with resonance network mapping

### Chart Calculation
- **17 house systems** (Placidus, Koch, Regiomontanus, Campanus, Morinus, Porphyry, Whole Sign, Equal, APC, Sunshine, etc.)
- **22 zodiacal aspects** with applying/separating/stationary motion detection
- **Declination parallels & contra-parallels**
- **Antiscia & contra-antiscia**
- **21 aspect patterns** (T-Square, Grand Trine, Yod, Kite, Mystic Rectangle, Stellium, etc.)
- **Full midpoint matrix** with 90°/45°/22.5° dial projections
- **Traditional dignities** (domicile, exaltation, triplicity, terms, face, sect, hayz, Almuten Figuris)
- **499 Arabic Parts** with dependency graphs
- **36-decan system** with ruling stars and Hermetic decan hours
- **Galactic house system** with boundary profiles

### Predictive Techniques
- **Progressions** — 40 techniques covering secondary, tertiary, minor, solar arc, Naibod, ascendant arc, vertex arc, planetary arc, quotidian solar/lunar, plus full converse forms
- **Primary directions** (Placidus semi-arc, mundane, speculum)
- **Returns** (solar, lunar, planetary)
- **Time lords** (profections, Firdaria, Zodiacal Releasing, Hyleg/Alcocoden)
- **Vedic techniques** (Vimshottari Dasha, Ashtottari Dasha, Yogini Dasha, sidereal positions, 27 nakshatras, Varga charts)

### Vedic Depth (Substantially Expanded)
- **Vimshottari Dasha** with nakshatra balance
- **Ashtottari Dasha** and **Yogini Dasha** (alternate systems)
- **Ashtakavarga** — Bhinnashtakavarga (per-planet) and Sarvashtakavarga (chart-wide); sign strength profiles; transit strength
- **Shadbala** — full six-strength computation (Sthana Bala, Dig Bala, Kala Bala, Chesta Bala, Naisargika Bala, Drig Bala) with tier classification
- **Jaimini Karakas** — full 7-planet and 8-planet schemes with atmakaraka, karaka pairs, condition profiles
- **Panchanga** — Tithi, Yoga, Karana, Vara with condition profiles and policy control
- **Vedic Dignities** — exaltation, debilitation, Mula Trikona, own signs, natural friendship/enmity, compound relationships
- **Nakshatras** — 27-nakshatra system with `nakshatra_of()` and `all_nakshatras_at()`
- **Divisional charts (Varga)** via sidereal module

### Batch & Automation Operations (New — Gap #1 Closed)
- **`batch_charts()`** — multi-chart assembly across dates, locations, body sets
- **`batch_events()`** — general event search (transits, aspect transits, declination transits, ingresses, stations)
- **`batch_transits()`** — multi-body longitude transit search
- **`batch_returns()`** — solar, lunar, planetary return JDs in bulk
- **`batch_progressions()`** — 40 progression techniques in batch with per-request failure isolation
- **`find_all_ingresses()`** — chronologically merged ingresses for many bodies
- **`void_periods_all_planets()`** — void-of-course windows for any moving body across a range
- **`planet_time_series()`** — ephemeris sampling for one body across many epochs
- All batch functions use per-request `BatchFailure` isolation: one failed chart does not abort the run

### Observational & Practical Phenomena (Significantly Improved)
- **Eclipses** (NASA-canon contact solver, Saros series, local circumstance)
- **Heliacal phenomena V5** — generalized visibility engine: multi-criterion (naked eye/binoculars/telescope), light pollution classes (Bortle scale), atmospheric extinction models, moonlight policy, twilight model, lunar crescent visibility
- **Parans** (paranatellonta field analysis)
- **Occultations** (lunar occultation of stars/planets)
- **Retrograde stations** — `find_stations()` exposed in batch
- **Astrocartography** (ACG lines for all planets)
- **Local Space charts**
- **Gauquelin sectors**
- **Galactic coordinates** (equatorial-to-galactic transform)
- **Void-of-course Moon** — `void_of_course_window()`, `is_void_of_course()`, `next_void_of_course()`, `void_periods_in_range()`; generalized to any body via `void_periods_all_planets()`
- **Sign ingresses** — `find_ingresses()` and `find_all_ingresses()` (batch)
- **Proximity/conjunction events** — `proximity_events_in_range()` and `solar_condition_events_in_range()`
- **Planetary phenomena** — `planet_phenomena_at()`, `PlanetPhenomena`
- **Keplerian orbital elements** — `orbital_elements_at()`, `distance_extremes_at()`
- **Planetary nodes** — geometric orbital nodes via `planetary_node()`, `all_planetary_nodes()`

### Advanced Analytical Capabilities (New / Unique)
- **Harmogram analysis** — harmogram traces, intensity function spectra, zero-aries parts harmonic vectors, harmogram strength projection; no commercial competitor exposes this in an API
- **Dispositorship system** — full dispositorship chain calculation, condition network profiles, subsystem profiles, comparison bundles; research-grade analysis unavailable in any Python astrology library
- **Triplicity scoring** — configurable triplicity doctrine with participation rules
- **Asteroid family resonance** — family identification, resonant aspect detection, resonance network mapping

---

## Professional Astrology Software Landscape

### Tier 1: Desktop Calculation Engines

#### **Swiss Ephemeris (Astro.com)**
- **Strength:** Industry standard; used by most professional software
- **API:** C/Fortran library; thin Python wrappers available (pyswisseph)
- **Coverage:** Planets, asteroids, fixed stars, nodes, Lilith
- **Techniques:** Basic aspects, houses, progressions, returns
- **Weakness:** Closed-source; limited transparency; no Vedic depth; Python wrappers are thin bindings to a black box
- **Market Position:** De facto standard for Western astrology

#### **Solar Fire (Alabe Software)**
- **Strength:** Calculation-first; research-grade accuracy; batch automation
- **Features:**
  - Animated charts (real-time clock, time-step animation)
  - Astrologer's Assistant (task automation/macro recording)
  - Astro-Locality Mapping (eclipse paths, local space lines)
  - Batch processing for transits, progressions, returns
  - 1000+ asteroids
  - Extensive report generation
- **Weakness:** Proprietary; Windows-first; no API
- **Market Position:** Professional astrologer standard for research & batch work

#### **Kepler (Astro Software)**
- **Strength:** Research-grade; statistical analysis; AstroMaps
- **Features:**
  - AstroMaps (Treasure Maps, local space, horizon, geodetic, zodiac sign maps)
  - 90° dials (regular, biwheel, triwheel, quadwheel)
  - Antiscia/contra-antiscia charts
  - Arabic Parts wheels
  - Arc Transform charts
  - Asteroids (4 major + Chiron in wheel; 1000 in list; 38,000 optional)
  - Aspect listings with VOC
  - Assumptionless research tools
  - Batch processing
- **Weakness:** Proprietary; expensive; limited Vedic
- **Market Position:** Research & statistical analysis

#### **Astro Gold (Solar Fire for Mac/iOS)**
- **Strength:** Mobile-first; elegant UI; file compatibility with Solar Fire
- **Features:**
  - Transit reports with custom date conditions
  - Progressions, synastry, composite charts
  - Customizable reports
  - iOS/macOS native
- **Weakness:** Limited to Apple ecosystem; less powerful than Solar Fire desktop
- **Market Position:** Professional astrologers on Mac/iPad

### Tier 2: Vedic Astrology Specialists

#### **Parashara's Light**
- **Strength:** Comprehensive Vedic suite; accurate calculations
- **Features:**
  - Vimshottari Dasha with nakshatra balance
  - Varshaphal (annual charts)
  - Ashtakavarga
  - Divisional charts (Varga)
  - KP astrology
  - Muhurta (electional astrology)
  - Birth time rectification
  - Database/research tools
  - Customizable reports
- **Weakness:** Proprietary; limited Western techniques; no API
- **Market Position:** Vedic practitioners & researchers

#### **Jagannatha Hora**
- **Strength:** Free; Vedic-focused; active development
- **Features:**
  - Vimshottari Dasha
  - Varshaphal
  - Ashtakavarga
  - Divisional charts
  - KP astrology
  - Muhurta
  - Nakshatra analysis
- **Weakness:** Limited Western techniques; no API; smaller user base
- **Market Position:** Budget-conscious Vedic practitioners

### Tier 3: API/Service Layer

#### **AstroVisor API**
- **Strength:** Professional API; Swiss Ephemeris engine; 95+ tools
- **Features:**
  - Natal charts, BaZi, Jyotish
  - REST API
  - Batch processing
  - Custom calculations
- **Weakness:** Proprietary; closed-source; pricing model
- **Market Position:** Developers integrating astrology into apps

#### **Immanuel (Python)**
- **Strength:** Open-source Python wrapper; Swiss Ephemeris + Astro.com data
- **Features:**
  - JSON-formatted chart data
  - Human-readable output
  - Python-native
- **Weakness:** Limited to Swiss Ephemeris; no Vedic; minimal techniques; thin wrapper with no sovereign computation
- **Market Position:** Python developers wanting quick chart generation

#### **Kerykeion (Python)**
- **Strength:** Open-source; SVG chart generation; Python-native
- **Features:**
  - Birth charts, composite, transit charts
  - SVG output
  - Data extraction
- **Weakness:** Limited techniques; no Vedic; minimal validation; no batch or predictive API
- **Market Position:** Python developers wanting chart visualization

---

## Gap Analysis: Current State

### 1. **Batch & Automation Operations** — **CLOSED** ✓
**Status:** Fully implemented in `moira/batch.py`
- ✓ `batch_charts()` — multi-chart assembly
- ✓ `batch_events()` — transits, aspect transits, declination transits, ingresses, stations
- ✓ `batch_transits()` — longitude transit search
- ✓ `batch_returns()` — solar/lunar/planet returns
- ✓ `batch_progressions()` — 40 progression techniques with full converse forms
- ✓ `find_all_ingresses()` — multi-body ingress merge
- ✓ `void_periods_all_planets()` — VOC windows for any body
- ✓ `planet_time_series()` — ephemeris time series sampling
- ✓ Per-request `BatchFailure` isolation — one failure does not abort the run

**Remaining:** No macro recording or task automation (not needed for a library); no chart filtering or research queries (see Gap #6)

---

### 2. **Interpretive Synthesis** (MEDIUM PRIORITY — intentionally deferred)
**Professional Need:** Astrologers want computed facts + interpretive guidance

**Moira Status:** Pure computation; no interpretation
- ✗ No interpretive text generation
- ✗ No technique synthesis (e.g., "Mars in 8th + Pluto aspects = X")
- ✗ No report templates
- ✗ No client-facing output formatting

**Note:** This is the most natural application of an LLM layer over Moira's output. A `moira-interpret` plugin consuming the structured API would be a strong product rather than an engine feature.

---

### 3. **Vedic Technique Depth** (LOW–MEDIUM PRIORITY — substantially reduced)
**Professional Need:** Vedic practitioners need specialized tools

**Moira Status:** Deep Vedic core coverage; the remaining gap is primarily doctrinal and workflow-specific rather than substrate-level
- ✓ Vimshottari Dasha
- ✓ Ashtottari Dasha
- ✓ Yogini Dasha
- ✓ Ashtakavarga (Bhinna and Sarva)
- ✓ Shadbala (full six-strength: Sthana, Dig, Kala, Chesta, Naisargika, Drig)
- ✓ Jaimini Karakas (7 and 8-planet)
- ✓ Panchanga (Tithi, Yoga, Karana, Vara)
- ✓ Vedic dignities, compound relationships
- ✓ Nakshatras (27 lunar mansions)
- ✓ Divisional charts (Varga; Shodashvarga depth is present)
- ✗ **Tajika / Varshaphal annual-return doctrine** — no Muntha, Sahams, or Tajika aspect layer
- ✗ **KP astrology (Krishnamurti Paddhati)** — no KP cusp workflow, star-lord / sub-lord chain, ruling planets, or significator logic
- ✗ **Jaimini Chara Dasha** — Karakas are implemented, but the time-lord system itself is absent
- ✗ **Natal yoga catalog** — Panchanga nitya yogas exist, but named chart-yoga families (Raja, Dhana, Nabhasa, etc.) are not surfaced
- ✗ **Muhurta (electional astrology)** — no electional scoring or practitioner workflow layer over Panchanga and planetary conditions
- ✗ **Birth time rectification** — not implemented
- ✗ **Bhava Chalit** — not implemented

**Gap remaining:** Moira can now claim substantial Jyotish infrastructure, but it cannot yet claim parity with Parashara's Light or Sirius on specialized Vedic doctrine. The clearest remaining gaps are Tajika/Varshaphal, KP, Jaimini Chara Dasha, natal yoga catalogs, Muhurta workflow, and rectification.

---

### 4. **Observational/Practical Phenomena** — **SUBSTANTIALLY IMPROVED**
**Professional Need:** Simple, clean event-search APIs for common practical uses

**Moira Status:** Now largely complete; specific naming conventions could improve discoverability
- ✓ Eclipses (present)
- ✓ Heliacal phenomena V5 with full visibility policy (light pollution, extinction, moonlight, observer conditions)
- ✓ Occultations (present)
- ✓ Retrograde stations via `find_stations()` in batch
- ✓ Sign ingresses via `find_ingresses()` / `find_all_ingresses()`
- ✓ Proximity/conjunction events via `proximity_events_in_range()`
- ✓ Void-of-course Moon with dedicated API
- ✓ Planetary phenomena via `planet_phenomena_at()`
- ✗ **Lunar phases** — not exposed as a simple `find_lunar_phases()` API
- ✗ **Planetary visibility window** — "is planet visible tonight?" convenience API; `visibility_assessment()` exists but requires non-trivial setup

**Opportunity:** Expose `find_lunar_phases(jd_start, jd_end)` convenience function; add `visibility_tonight()` or similar convenience surface.

---

### 5. **Relationship & Synastry Automation** (MEDIUM PRIORITY)
**Professional Need:** Batch synastry, composite, Davison for multiple chart pairs

**Moira Status:** Single-pair focus
- ✓ Synastry (present)
- ✓ Composite (present)
- ✓ Davison (present)
- ✗ **Batch synastry** — not implemented
- ✗ **Synastry filtering** (e.g., "show all Mars-Venus aspects across 100 pairs")
- ✗ **Compatibility scoring** — not implemented

**Opportunity:** `batch_synastry(pairs, techniques)` analogous to `batch_progressions()` — low implementation cost given the batch pattern is already established.

---

### 6. **Research & Statistical Tools** (MEDIUM PRIORITY)
**Professional Need:** Filter, aggregate, and analyze chart collections

**Moira Status:** No research layer
- ✗ No chart database
- ✗ No filtering (e.g., "all charts with Sun in 8th")
- ✗ No statistical aggregation
- ✗ No correlation analysis
- ✗ No chart comparison tools

**Opportunity:** A `moira-research` module — even a simple in-memory chart collection with filter predicates — would unlock research workflows. The batch API is the computational foundation; persistence and filtering are the missing layer.

---

### 7. **Report Generation & Templating** (MEDIUM PRIORITY)
**Professional Need:** Generate client-facing reports in multiple formats

**Moira Status:** No report layer
- ✗ No HTML/PDF report generation
- ✗ No report templates
- ✗ No customizable output formatting
- ✗ No multi-chart report layouts (triwheel, quadwheel)

**Opportunity:** `moira-reports` module with Jinja2 templates for HTML output; PDF via wkhtmltopdf or weasyprint.

---

### 8. **REST API / Service Layer** (HIGH PRIORITY)
**Professional Need:** Integrate Moira into web apps, mobile apps, third-party services

**Moira Status:** Python library only
- ✗ No REST API
- ✗ No Docker container
- ✗ No cloud deployment
- ✗ No rate limiting / auth
- ✗ No async/concurrent request handling

**Note:** The C++ native layer makes this more viable: the hot computation paths are now fast enough for production HTTP latency budgets. A FastAPI server is the natural next step.

**Opportunity:** `moira-server` — FastAPI app with endpoints for chart, batch, event, and progression operations; Docker image; OpenAPI schema.

---

### 9. **Mobile/Lightweight Interface** (LOW PRIORITY)
**Professional Need:** Astrologers want mobile access

**Moira Status:** Python library; not mobile-friendly
- ✗ No mobile app
- ✗ No lightweight web UI
- ✗ No offline-capable mobile library

**Note:** This is a downstream product of the REST API; build the server first.

---

### 10. **Chart Data Persistence** (MEDIUM PRIORITY)
**Professional Need:** Store, retrieve, and manage chart collections

**Moira Status:** No persistence layer
- ✗ No chart storage format
- ✗ No database schema
- ✗ No import/export (except manual)
- ✗ No chart versioning

**Opportunity:** Define a canonical chart JSON schema; create `moira-storage` with SQLite backend.

---

### 11. **NEW: Concurrency & Thread Safety at Scale** (MEDIUM PRIORITY — newly identified)
**Professional Need:** Multi-threaded servers and parallel chart processing

**Moira Status:** Partially addressed; GIL constraints remain
- ✓ C++ evaluator layer uses mutex-guarded caching — thread-safe per evaluator
- ✓ `search_pool.hpp` — native thread pool for event searches
- ✗ Python-level `Moira()` session and `SpkReader` are not designed for concurrent access
- ✗ GIL release strategy for long-running C++ operations not yet formalized (audit in progress)
- ✗ No documented threading model for the public API

**Opportunity:** Formalize GIL release annotations for C++ extension calls; document thread-safety contract for `SpkReader` and the `Moira` facade; expose a `ThreadedMoira` or process-pool pattern for server deployments.

---

### 12. **NEW: Lunar Phase API** (LOW PRIORITY — newly identified)
**Professional Need:** Simple `find_lunar_phases()` call for phase calendars

**Moira Status:** Computable but not surfaced
- ✓ Sun–Moon angular separation computable via existing APIs
- ✗ No `find_lunar_phases()` convenience function
- ✗ No phase calendar output (new/crescent/first quarter/full/last quarter/balsamic)

**Opportunity:** Small addition; high discoverability value for practitioners.

---

### 13. **NEW: Chart Visualization / SVG Output** (LOW PRIORITY — newly identified)
**Professional Need:** Visual chart wheel output

**Moira Status:** No visualization layer
- ✗ No SVG or chart wheel output
- Competitors like Kerykeion (SVG) and Astro Gold (native iOS graphics) have visual output

**Note:** Moira's positioning as a computation core makes this a plugin concern, but chart SVG output would significantly broaden its appeal for developers.

---

## Moira's Unique Competitive Advantages

### 1. **Hybrid Python/C++ Architecture (New)**
- Sovereign C++ core with Python-native API — not a thin wrapper around an external binary
- AVX2-accelerated Chebyshev polynomial evaluation (outperforms pyswisseph hot path)
- Composable native evaluator DAG (RelativeEvaluator, SumEvaluator, TopocentricEvaluator)
- Native DAF/SPK reader — Moira owns the ephemeris file-format chain
- Thread pool for parallel event search
- Performance competitive with compiled libraries while maintaining Python transparency

### 2. **Astronomical Transparency**
- Explicit computational pipeline with inspectable intermediate stages
- Documented residuals against ERFA/SOFA
- No hidden black boxes or undocumented corrections
- Machine contract governance (MACHINE_CONTRACT v1 blocks) enforced by test suite

### 3. **Modern Astronomical Standards**
- JPL DE441 (not older DE430)
- IAU 2006 (not IAU 1976)
- Full nutation model (1365 lunisolar + 687 planetary terms)
- Gravitational deflection (Sun, Jupiter, Saturn, Earth)
- IERS delta-T with physical-model fallback

### 4. **Comprehensive Vedic Coverage**
- Vimshottari + Ashtottari + Yogini dasha systems
- Shadbala (full six-strength with tier classification)
- Ashtakavarga (Bhinna + Sarva + transit strength)
- Jaimini Karakas (7 and 8-planet schemes)
- Panchanga (Tithi, Yoga, Karana, Vara with condition profiles)
- Multiple ayanamshas with century-drift characterization

### 5. **Sovereign Fixed Star Registry**
- 1,809 named stars with proper motion, parallax, epoch propagation
- Evaluated in native C++ (`FixedStarEvaluator`)
- Audited against SOFA/ERFA (0.00048 arcseconds residual)
- License-independent

### 6. **Generalized Visibility Engine (V5 — Unique)**
- Multi-criterion observing conditions: naked eye, binoculars, telescope
- Bortle-scale light pollution classes
- Atmospheric extinction model
- Moonlight interference policy
- Twilight model selection
- Lunar crescent visibility criteria with IOTA-oriented authority
- No commercial Python library matches this depth

### 7. **Deep Dispositorship & Condition Profiling (Unique)**
- Full dispositorship chain calculation
- Condition network profiles across a chart
- Subsystem profiles and comparison bundles
- Research-grade dignities analysis not available in any other Python library

### 8. **Harmogram Analysis (Unique)**
- Harmogram traces with configurable domains
- Intensity function spectra
- Zero-aries parts harmonic vectors
- No commercial competitor exposes harmonic analysis at this level in an API

### 9. **Explicit Policy Control**
- Every correction stage can be toggled independently
- Delta-T policy choices (IERS, polynomial, hybrid)
- Ayanamsa selection
- Topocentric parallax optional
- Atmospheric refraction optional
- Dignity doctrine selection

---

## Strategic Recommendations

### **Tier 1: High-Impact Gaps (Implement Next)**

1. **REST API Service Layer**
   - FastAPI server with endpoints for all major Moira functions
   - OpenAPI schema for discoverability
   - Docker container for easy deployment
   - GIL release formalization as prerequisite
   - **Impact:** Opens Moira to web/mobile developers; enables hosted service revenue
   - **Effort:** Medium (3-4 weeks given C++ layer already handles hot path)

2. **Batch Synastry**
   - `batch_synastry(pairs, techniques)` following the established batch pattern
   - Synastry filtering helper
   - **Impact:** Closes a notable gap vs. Solar Fire batch workflows
   - **Effort:** Low (1 week — batch infrastructure already in place)

3. **Lunar Phase Convenience API**
   - `find_lunar_phases(jd_start, jd_end)` returning phase type + JD
   - **Impact:** High discoverability; fills practitioner calendar use case
   - **Effort:** Very low (2-3 days)

4. **Thread Safety Documentation & GIL Release Audit**
   - Document `SpkReader` and `Moira` facade threading contracts
   - Annotate C++ extension calls with GIL release where safe
   - **Impact:** Required before REST API deployment is production-safe
   - **Effort:** Low-medium (1-2 weeks)

### **Tier 2: Vedic & Professional Workflow (Implement Second)**

5. **Varshaphal (Annual Charts)**
   - Solar return for sidereal Sun return (Vedic annual chart)
   - **Impact:** Closes one of the most visible remaining Vedic doctrine gaps, especially if extended to Tajika objects like Muntha and Sahams
   - **Effort:** Medium (1-2 weeks; solar return machinery exists)

6. **Chart Persistence & Storage**
   - Canonical chart JSON schema
   - SQLite backend with `moira-storage` module
   - **Impact:** Enables research and client management workflows
   - **Effort:** Medium (2-3 weeks)

7. **Muhurta (Electional Astrology)**
   - Integrate Panchanga + planetary conditions into electional scoring
   - **Impact:** Closes an important practitioner workflow gap, but does not by itself complete Vedic parity without KP, Tajika depth, and yoga catalog work
   - **Effort:** High (4-6 weeks; domain-specific logic)

8. **Research & Filtering Tools**
   - In-memory chart collection with filter predicates
   - Statistical aggregation helpers
   - **Impact:** Enables research workflows on top of batch API
   - **Effort:** Medium (2-3 weeks)

### **Tier 3: Optional Enhancements (Implement Third)**

9. **KP Astrology (Krishnamurti Paddhati)**
   - Sub-lord system, KP significators
   - **Impact:** Specialized Vedic niche; not the primary gap
   - **Effort:** High (4-6 weeks; distinct sub-lord calculation chain)

10. **Report Generation**
    - Jinja2 template system for HTML/PDF
    - **Impact:** Enables client-facing deliverables
    - **Effort:** Medium (3-4 weeks)

11. **Chart Visualization / SVG Output**
    - Plugin module with wheel rendering
    - **Impact:** Widens developer appeal
    - **Effort:** Medium (3-4 weeks)

12. **Interpretive Synthesis Layer** (optional plugin)
    - LLM-backed technique synthesis over structured Moira output
    - **Impact:** Differentiates from pure computation; large practitioner market
    - **Effort:** High (8-12 weeks); best implemented as `moira-interpret` using Claude API

---

## Market Positioning Strategy

### **Current Position**
Moira is a **transparent, auditable, high-performance computational engine** with a Python-native API, sovereign C++ core, and comprehensive coverage of both Western and Vedic techniques. The batch API is now production-capable.

### **Recommended Positions**

1. **"The Computational Core for Professional Astrology"**
   - Offer Moira as a service layer (REST API) for app developers
   - Compete with Swiss Ephemeris on transparency + modern standards + Python-native accessibility
   - Compete with Solar Fire on batch automation (batch API is now equivalent in coverage if not UX polish)

2. **"The Unified Western + Vedic Engine with Performance"**
   - Deepest Vedic coverage of any Python library (Shadbala, Ashtakavarga, Jaimini, Panchanga, Ashtottari, Yogini)
   - Full Western technique suite in the same library
   - C++ core means it is not a convenience trade-off

3. **"The Auditable Alternative to Proprietary Software"**
   - Emphasize sovereign Python/C++ architecture, inspectable code, documented residuals
   - Machine contract governance for AI-assisted development
   - Target researchers, educators, and practitioners who value transparency
   - Open-source core + optional commercial services (hosting, support, `moira-interpret`)

---

## Competitive Comparison Matrix

| Feature | Moira | Swiss Ephemeris | Solar Fire | Kepler | Parashara's Light |
|---------|-------|-----------------|-----------|--------|-------------------|
| **Astronomy** | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **Transparency** | ★★★★★ | ★☆☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ |
| **Performance (C++ core)** | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **Python API** | ★★★★★ | ★★☆☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ |
| **Western Techniques** | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★☆☆☆ |
| **Vedic Techniques** | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★★★ |
| **Batch Operations** | ★★★★☆ | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **Observational Phenomena** | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★★★☆☆ | ★★☆☆☆ |
| **Report Generation** | ☆☆☆☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **REST API** | ☆☆☆☆☆ | ★★★☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ |
| **Research Tools** | ★☆☆☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ |
| **Harmogram / Advanced Analysis** | ★★★★★ | ☆☆☆☆☆ | ★★☆☆☆ | ★★★☆☆ | ☆☆☆☆☆ |
| **Visibility Engine** | ★★★★★ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ☆☆☆☆☆ |

*Note: "Performance (C++ core)" reflects computational throughput on SPK evaluation. Moira's Python surface adds overhead vs. direct C library calls, but the native evaluation layer is now competitive for hot-path operations.*

---

## Conclusion

Moira's foundation has materially strengthened since April 2026. The batch operations gap is closed. The Vedic depth gap is substantially reduced. The C++ native layer adds a competitive performance dimension that no other Python-native astrology library possesses.

The remaining strategic priorities in order are:

1. **REST API** — transforms Moira from a library into a platform
2. **Thread safety formalization** — required before server deployment
3. **Batch synastry** — low-effort gap closure using existing batch infrastructure
4. **Lunar phase convenience API** — small addition, high practitioner value
5. **Varshaphal / Tajika** — closes one of the most visible remaining Vedic doctrine gaps
6. **Chart persistence + research tools** — unlocks the research and data workflows that Solar Fire and Kepler own today

The opportunity is no longer solely to offer Moira as a Python library. The C++ layer, batch API, and comprehensive technique coverage now support positioning Moira as **a production computational platform** that application developers, researchers, and Vedic/Western practitioners can build on top of — either as a library, a REST service, or a hosted API.
