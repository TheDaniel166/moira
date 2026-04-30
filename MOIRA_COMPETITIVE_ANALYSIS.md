# Moira Computational API: Competitive Analysis & Gap Assessment

**Date:** April 28, 2026  
**Purpose:** Identify gaps, overlaps, and strategic opportunities for Moira as a computational core offering

---

## Executive Summary

Moira is **astronomically comprehensive** and **computationally transparent** in ways that professional astrology software is not. However, the market reveals several categories of features that Moira either lacks or could strengthen:

1. **Batch/Automation Operations** — Professional software excels at running hundreds of charts through predictive pipelines
2. **Interpretive Synthesis** — Moira computes; it doesn't interpret or synthesize across techniques
3. **Specialized Vedic Depth** — Vedic-specific software (Parashara's Light, Jagannatha Hora) has deeper Vedic technique coverage
4. **Observational/Practical Phenomena** — Occultation, eclipse, and heliacal event APIs are present but not as polished as specialized tools
5. **Relationship & Synastry Automation** — Limited batch synastry, composite, and Davison chart generation
6. **Research & Statistical Tools** — No built-in research database, chart filtering, or statistical analysis
7. **Report Generation & Templating** — No native report generation or customizable output formatting
8. **Mobile/API Service Layer** — No REST API or mobile-ready interface

---

## Moira's Computational Strengths

### Astronomy Foundation (Unmatched)
- **JPL DE441 kernel** with explicit light-time iteration, gravitational deflection, annual aberration
- **IAU 2006 frame bias, precession, nutation** with full 1365 lunisolar + 687 planetary terms
- **Topocentric parallax** (WGS-84) and atmospheric refraction
- **Validation against ERFA/SOFA** with documented residuals
- **Pure Python** with inspectable intermediate stages

### Planetary & Stellar Coverage
- **1,809 named fixed stars** with proper motion, parallax, epoch propagation
- **Classical asteroids** (Ceres, Pallas, Juno, Vesta) + **Centaurs** (Chiron, Pholus, Chariklo, Asbolus, Hylonome)
- **Trans-Neptunians** (Ixion, Quaoar, Varuna, Orcus)
- **Uranian/Hamburg bodies** (Cupido through Poseidon)
- **Lunar nodes, apsides, True/Mean Lilith**
- **Variable stars** (Algol phase engine)
- **Multiple star systems** (Sirius AB, Alpha Centauri AB)
- **User-supplied `.bsp` kernels** for 887,000+ numbered minor planets

### Chart Calculation
- **17 house systems** (Placidus, Koch, Regiomontanus, Campanus, Morinus, Porphyry, Whole Sign, Equal, APC, Sunshine, etc.)
- **22 zodiacal aspects** with applying/separating/stationary motion detection
- **Declination parallels & contra-parallels**
- **Antiscia & contra-antiscia**
- **21 aspect patterns** (T-Square, Grand Trine, Yod, Kite, Mystic Rectangle, Stellium, etc.)
- **Full midpoint matrix** with 90°/45°/22.5° dial projections
- **Traditional dignities** (domicile, exaltation, triplicity, terms, face, sect, hayz, Almuten Figuris)
- **499 Arabic Parts** with dependency graphs
- **36-decan system** with ruling stars

### Predictive Techniques
- **Progressions** (secondary, tertiary, minor, solar arc, Naibod, ascendant arc; direct & converse)
- **Primary directions** (Placidus semi-arc, mundane, speculum)
- **Returns** (solar, lunar, planetary)
- **Time lords** (profections, Firdaria, Zodiacal Releasing, Hyleg/Alcocoden)
- **Vedic techniques** (Vimshottari Dasha, sidereal positions, 27 nakshatras, Varga charts)

### Advanced Astronomy
- **Eclipses** (NASA-canon contact solver, Saros series, local circumstance)
- **Heliacal phenomena** (rising/setting, acronychal, elongation extremes)
- **Parans** (paranatellonta field analysis)
- **Occultations** (lunar occultation of stars/planets)
- **Retrograde stations** (precise stationary-point search)
- **Astrocartography** (ACG lines for all planets)
- **Local Space charts**
- **Gauquelin sectors**
- **Galactic coordinates** (equatorial-to-galactic transform)
- **Temporal systems** (28-mansion lunar stations, Sothic cycle, void-of-course Moon)
- **Harmonics** (harmonic charts, aspect-harmonic profiles)
- **Synastry** (inter-chart aspects, house overlays, composite, Davison)
- **Jones chart shapes** (7 temperament types)

---

## Professional Astrology Software Landscape

### Tier 1: Desktop Calculation Engines

#### **Swiss Ephemeris (Astro.com)**
- **Strength:** Industry standard; used by most professional software
- **API:** C/Fortran library; thin Python wrappers available
- **Coverage:** Planets, asteroids, fixed stars, nodes, Lilith
- **Techniques:** Basic aspects, houses, progressions, returns
- **Weakness:** Closed-source; limited transparency; no Vedic depth
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
- **Weakness:** Limited to Swiss Ephemeris; no Vedic; minimal techniques
- **Market Position:** Python developers wanting quick chart generation

#### **Kerykeion (Python)**
- **Strength:** Open-source; SVG chart generation; Python-native
- **Features:**
  - Birth charts, composite, transit charts
  - SVG output
  - Data extraction
- **Weakness:** Limited techniques; no Vedic; minimal validation
- **Market Position:** Python developers wanting chart visualization

---

## Gap Analysis: What Moira Lacks

### 1. **Batch & Automation Operations** (HIGH PRIORITY)
**Professional Need:** Run 100+ charts through predictive pipelines in one operation

**Moira Status:** Single-chart focus; no batch API
- ✗ No batch transit/progression/return generation
- ✗ No chart filtering or research queries
- ✗ No task automation or macro recording
- ✗ No scheduled/recurring chart generation

**Opportunity:** Add `batch_charts()`, `batch_transits()`, `batch_progressions()` methods with filtering

---

### 2. **Interpretive Synthesis** (MEDIUM PRIORITY)
**Professional Need:** Astrologers want computed facts + interpretive guidance

**Moira Status:** Pure computation; no interpretation
- ✗ No interpretive text generation
- ✗ No technique synthesis (e.g., "Mars in 8th + Pluto aspects = X")
- ✗ No report templates
- ✗ No client-facing output formatting

**Opportunity:** Create optional `moira-interpret` plugin layer (separate from core)

---

### 3. **Vedic Technique Depth** (MEDIUM PRIORITY)
**Professional Need:** Vedic practitioners need specialized tools

**Moira Status:** Good Vedic coverage; some gaps
- ✓ Vimshottari Dasha (present)
- ✓ Ashtakavarga (present)
- ✓ Shadbala (present)
- ✓ Jaimini Karakas (present)
- ✓ Panchanga (present)
- ✗ **Varshaphal (annual charts)** — not implemented
- ✗ **KP astrology** — not implemented
- ✗ **Muhurta (electional)** — not implemented
- ✗ **Birth time rectification** — not implemented
- ✗ **Nakshatra-specific techniques** — partial
- ✗ **Bhava Chalit** — not implemented

**Opportunity:** Implement varshaphal, KP astrology, muhurta, birth time rectification

---

### 4. **Observational/Practical Phenomena** (LOW PRIORITY)
**Professional Need:** Occultation, eclipse, heliacal event APIs

**Moira Status:** Present but not polished
- ✓ Eclipses (present)
- ✓ Heliacal phenomena (present)
- ✓ Occultations (present)
- ✓ Retrograde stations (present)
- ✗ **Lunar phases** — not exposed as a simple API
- ✗ **Planetary visibility** — partial (heliacal only)
- ✗ **Conjunction/opposition search** — not exposed
- ✗ **Ingress search** — not exposed

**Opportunity:** Expose simple `find_lunar_phases()`, `find_conjunctions()`, `find_ingresses()` APIs

---

### 5. **Relationship & Synastry Automation** (MEDIUM PRIORITY)
**Professional Need:** Batch synastry, composite, Davison for multiple chart pairs

**Moira Status:** Single-pair focus
- ✓ Synastry (present)
- ✓ Composite (present)
- ✓ Davison (present)
- ✗ **Batch synastry** — not implemented
- ✗ **Synastry filtering** (e.g., "show all Mars-Venus aspects")
- ✗ **Compatibility scoring** — not implemented
- ✗ **Synastry pattern detection** — not implemented

**Opportunity:** Add `batch_synastry()`, `synastry_filter()`, `compatibility_score()` methods

---

### 6. **Research & Statistical Tools** (MEDIUM PRIORITY)
**Professional Need:** Filter, aggregate, and analyze chart collections

**Moira Status:** No research layer
- ✗ No chart database
- ✗ No filtering (e.g., "all charts with Sun in 8th")
- ✗ No statistical aggregation
- ✗ No correlation analysis
- ✗ No chart comparison tools

**Opportunity:** Create optional `moira-research` module with chart filtering, aggregation, statistics

---

### 7. **Report Generation & Templating** (MEDIUM PRIORITY)
**Professional Need:** Generate client-facing reports in multiple formats

**Moira Status:** No report layer
- ✗ No HTML/PDF report generation
- ✗ No report templates
- ✗ No customizable output formatting
- ✗ No multi-chart report layouts (triwheel, quadwheel)

**Opportunity:** Create optional `moira-reports` module with Jinja2 templates, HTML/PDF output

---

### 8. **REST API / Service Layer** (HIGH PRIORITY)
**Professional Need:** Integrate Moira into web apps, mobile apps, third-party services

**Moira Status:** Python library only
- ✗ No REST API
- ✗ No Docker container
- ✗ No cloud deployment
- ✗ No rate limiting / auth
- ✗ No async/concurrent request handling

**Opportunity:** Create `moira-server` (FastAPI/Flask) with REST endpoints, Docker, deployment docs

---

### 9. **Mobile/Lightweight Interface** (LOW PRIORITY)
**Professional Need:** Astrologers want mobile access

**Moira Status:** Python library; not mobile-friendly
- ✗ No mobile app
- ✗ No lightweight web UI
- ✗ No offline-capable mobile library

**Opportunity:** Create optional `moira-mobile` (React Native or Flutter) consuming REST API

---

### 10. **Chart Data Persistence** (MEDIUM PRIORITY)
**Professional Need:** Store, retrieve, and manage chart collections

**Moira Status:** No persistence layer
- ✗ No chart storage format
- ✗ No database schema
- ✗ No import/export (except manual)
- ✗ No chart versioning

**Opportunity:** Define chart storage format (JSON/SQLite), create `moira-storage` module

---

## Moira's Unique Competitive Advantages

### 1. **Astronomical Transparency**
- Explicit computational pipeline with inspectable intermediate stages
- Documented residuals against ERFA/SOFA
- No hidden black boxes or undocumented corrections

### 2. **Pure Python**
- Auditable code; no compiled dependencies
- Easy to extend and customize
- No licensing restrictions from compiled libraries

### 3. **Modern Astronomical Standards**
- JPL DE441 (not older DE430)
- IAU 2006 (not IAU 1976)
- Full nutation model (1365 lunisolar + 687 planetary terms)
- Gravitational deflection (Sun, Jupiter, Saturn, Earth)

### 4. **Comprehensive Vedic Coverage**
- Vimshottari Dasha, Ashtakavarga, Shadbala, Jaimini Karakas, Panchanga
- Sidereal positions with multiple ayanamshas
- Nakshatra system (27 nakshatras)
- Divisional charts (Varga)

### 5. **Sovereign Fixed Star Registry**
- 1,809 named stars with proper motion, parallax, epoch propagation
- Audited against SOFA/ERFA (0.00048 arcseconds residual)
- License-independent (not tied to external star catalogs)

### 6. **Advanced Astronomy**
- Heliacal phenomena with visibility assessment
- Occultation detection
- Parans with contour extraction
- Astrocartography with ACG lines
- Galactic coordinates

### 7. **Explicit Policy Control**
- Every correction stage can be toggled independently
- Delta-T policy choices (IERS, polynomial, hybrid)
- Ayanamsa selection
- Topocentric parallax optional
- Atmospheric refraction optional

---

## Strategic Recommendations

### **Tier 1: Core Computational Gaps (Implement First)**

1. **Batch Operations API**
   - `batch_charts(dates, locations, bodies, techniques)`
   - `batch_transits(base_chart, transit_dates, techniques)`
   - `batch_progressions(base_chart, progression_dates, techniques)`
   - **Impact:** Enables professional workflow automation
   - **Effort:** Medium (2-3 weeks)

2. **REST API Service Layer**
   - FastAPI server with endpoints for all major Moira functions
   - Docker container for easy deployment
   - Rate limiting, auth, async request handling
   - **Impact:** Opens Moira to web/mobile developers
   - **Effort:** High (4-6 weeks)

3. **Vedic Technique Completeness**
   - Implement varshaphal (annual charts)
   - Implement KP astrology (Krishnamurti Paddhati)
   - Implement muhurta (electional astrology)
   - **Impact:** Competitive with Parashara's Light
   - **Effort:** High (6-8 weeks)

### **Tier 2: Professional Workflow Support (Implement Second)**

4. **Chart Persistence & Storage**
   - Define JSON chart format
   - SQLite schema for chart collections
   - Import/export utilities
   - **Impact:** Enables chart management workflows
   - **Effort:** Medium (2-3 weeks)

5. **Research & Filtering Tools**
   - Chart filtering (e.g., "all charts with Sun in 8th")
   - Statistical aggregation
   - Correlation analysis
   - **Impact:** Enables research workflows
   - **Effort:** Medium (3-4 weeks)

6. **Report Generation**
   - Jinja2 template system
   - HTML/PDF output
   - Multi-chart layouts (triwheel, quadwheel)
   - **Impact:** Enables client-facing deliverables
   - **Effort:** Medium (3-4 weeks)

### **Tier 3: Optional Enhancements (Implement Third)**

7. **Interpretive Synthesis Layer** (optional plugin)
   - Technique synthesis rules
   - Interpretive text generation
   - Client-facing narrative
   - **Impact:** Differentiates from pure computation
   - **Effort:** High (8-12 weeks)

8. **Mobile Interface** (optional)
   - React Native or Flutter app
   - Consumes REST API
   - Offline chart caching
   - **Impact:** Reaches mobile practitioners
   - **Effort:** High (6-8 weeks)

---

## Market Positioning Strategy

### **Current Position**
Moira is a **transparent, auditable, comprehensive computational engine** for developers and researchers who need visibility into astrological calculations.

### **Recommended Position**
Moira should position itself as:

1. **"The Computational Core for Professional Astrology"**
   - Offer Moira as a service layer (REST API) for app developers
   - Compete with Swiss Ephemeris on transparency + modern standards
   - Compete with Solar Fire on batch automation + research tools

2. **"The Vedic + Western Unified Engine"**
   - Implement missing Vedic techniques (varshaphal, KP, muhurta)
   - Offer both Western and Vedic practitioners a single, unified API
   - Differentiate on transparency + modern astronomy

3. **"The Auditable Alternative to Proprietary Software"**
   - Emphasize pure Python, inspectable code, documented residuals
   - Target researchers, educators, and practitioners who value transparency
   - Offer as open-source core + optional commercial services (hosting, support)

---

## Competitive Comparison Matrix

| Feature | Moira | Swiss Ephemeris | Solar Fire | Kepler | Parashara's Light |
|---------|-------|-----------------|-----------|--------|-------------------|
| **Astronomy** | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **Transparency** | ★★★★★ | ★☆☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ |
| **Pure Python** | ★★★★★ | ☆☆☆☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ |
| **Western Techniques** | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★☆☆☆ |
| **Vedic Techniques** | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★★★ |
| **Batch Operations** | ★☆☆☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **Report Generation** | ☆☆☆☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| **REST API** | ☆☆☆☆☆ | ★★★☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ | ☆☆☆☆☆ |
| **Research Tools** | ★☆☆☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ |
| **Mobile** | ☆☆☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★☆☆ |

---

## Conclusion

Moira's **computational foundation is unmatched** in transparency and astronomical rigor. The gaps are not in calculation accuracy but in **professional workflow support**:

1. **Batch operations** for automation
2. **REST API** for integration
3. **Vedic completeness** (varshaphal, KP, muhurta)
4. **Report generation** for client deliverables
5. **Research tools** for statistical analysis

By implementing these five areas, Moira would become a **credible alternative to Swiss Ephemeris + Solar Fire** for professional astrologers and developers, while maintaining its unique position as the **most transparent, auditable computational engine** in the market.

The opportunity is not to replace existing software but to **offer Moira as the computational core** that other applications can build upon—either as a library, a REST API, or a hosted service.
