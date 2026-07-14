# Tier 2 Vedic Competitive Edge Work – Paused State

**Last active:** 2026-05-29 (second resumption push)  
**Status:** **Paused by user request** (new focus declared). Rich state captured for clean future resumption.

**Context:**  
Per [MOIRA_COMPETITIVE_ANALYSIS_2026-05-25.md](../07_audit/MOIRA_COMPETITIVE_ANALYSIS_2026-05-25.md), after Phase 8 the highest-leverage remaining work for competitive Vedic capability is in Tier 2 (practitioner workflow gaps). The user chose to prioritize closing these **before** moving into Phase 9 (Vedic transport surfaces).

---

## Current Overall State

- **Phase 8** is formally closed (see `MOIRA_SERVER_PHASE8_LEDGER.md` v1.9).
- Decision was made to focus on Tier 2 Vedic core work instead of immediately starting Phase 9.
- Primary vehicle: `moira/muhurta.py` (Muhurta / Electional doctrine layer).
- General infrastructure (`moira/electional.py` + `moira/panchanga.py`) is already strong.
- Work is research-driven only (BPHS, Muhurta Chintamani, Brihat Samhita, etc.) — no reliance on internal model memory.

---

## Muhurta Module – Present State (as of pause)

### What Has Been Implemented

**Baseline (pre-2026-05-29 resumption):**
- Core vessels: `MuhurtaPolicy`, `MuhurtaClassification`, `MuhurtaScore`
- Dagdha Yogas (BPHS Ch. 85), Vishti Karana
- Named Muhurtas (Abhijit, Brahma)
- Starter `ACTIVITY_MUHURTA_GUIDANCE`
- `muhurta_scorer` + `find_best_muhurta_windows` integration

**2026-05-29 Resumption Push (before second tabling):**
- **Panchanga Shuddhi Depth (High)**: Full Tara Bala (9 Taras + 3 Paryaya cycle nuance + proper 0-26 NakshatraPosition indexing). Basic Panchaka Rahita (mod-9 formula).
- **Dosha Detection + Parihara (High)**: `detect_muhurta_doshas()` fully implemented and wired — Vishanadi/Tyajya, Yamaghanta, expanded Gandanta (Nakshatra + Tithi). Heavy scoring penalties. Parihara notes. Time-data support for full detection in electional scans.
- **Lagna & Planetary Strength (High)**: New `evaluate_muhurta_lagna_strength(chart, activity=None)`. Jupiter in Kendra from Muhurta Lagna, benefics influencing Lagna, basic shuddhi factors. Foundation wired into scorer path. Activity-specific Lagna notes.
- **Activity-Specific Rules**: Incremental classical granularity (Kaulava for love/choosing bride, Gara for construction, etc.) + enhanced notes.
- All work strictly source-driven with explicit citations (Muhurta Chintamani, Kalaprakasika, Ernst Wilhelm *Classical Muhurta* Ch.10, 15, 17–18, B.V. Raman, K.K. Joshi, etc.).
- Rich `MuhurtaClassification` now carries tara, panchaka_rahita, doshas, dosha_severity, lagna strength data.
- Full integration through the electional scanner.

Exposed via `moira/__init__.py` and main `Moira` facade.

### What's Missing / Needs Expansion (Prioritized)

| Area | Current Maturity | What's Missing | Priority for Competitive Edge | Notes / Sources |
|------|------------------|----------------|-------------------------------|-----------------|
| **Panchanga Shuddhi Depth** | **Good progress (as of second pause)** | Full Tara Bala (9 Taras + cycles + proper indexing). Basic Panchaka Rahita. Chandra Bala skeleton + more granular Yoga/Karana still needed. | High (partially addressed) | Muhurta Chintamani, Kalaprakashika, Ernst Wilhelm *Classical Muhurta* Ch.10 |
| **Activity-Specific Rules** | Good starter + incremental | Classical Karana/activity mappings added (Kaulava for love/choosing bride, Gara for construction, etc.). Enhanced marriage notes. Still needs deeper purpose-specific variants (love vs arranged, Vastu subtypes, travel/business specifics). | High (solid incremental) | Ernst Wilhelm *Classical Muhurta* (Ch.22 + Karana chapter), Muhurta Chintamani |
| **Named & Special Muhurtas** | Basic (2 done) | Godhuli, Vijaya, Amrita, Ravi Yoga, Sarvarthasiddhi, etc. + exact windows | Medium | Muhurta Chintamani + traditional lists |
| **Dosha Detection + Parihara** | **Strong progress (as of second pause)** | `detect_muhurta_doshas()` fully wired (Vishanadi/Tyajya, Yamaghanta, Gandanta). Scoring penalties, parihara notes, time-data support in scanner. More doshas + complete neutralization logic still open. | High (major wiring complete) | Ernst Wilhelm *Classical Muhurta* Ch.17–18 + Vishanadi section, Muhurta Chintamani, Kalaprakasika |
| **Lagna & Planetary Strength** | **Foundation implemented (as of second pause)** | `evaluate_muhurta_lagna_strength(chart, activity=None)` delivered. Jupiter in Kendra, benefics on Lagna, basic shuddhi. Lightly wired. Deeper integration, Navamsha shuddhi, full chart strength rules still needed. | High (foundation complete) | Ernst Wilhelm *Classical Muhurta* Ch.15 "Lagna", Muhurta Chintamani |
| **Integration Helper Quality** | Good | True high-performance ranked search that computes full Panchanga + Muhurta score at scan time, activity-aware scoring, better handling of sidereal vs tropical | Medium | Currently works but can be tighter |
| **Validation & Testing** | None | Tests that match behavior of Jhora / Kala / Parashara's Light on real dates | High | Essential before claiming competitiveness |
| **Documentation** | Code-level only | Proper wiki/Muhurta standard document, usage examples, limitations | Medium | — |

---

## Other Tier 2 Vedic Items (from Competitive Analysis)

These are also flagged as remaining gaps but have received **zero work** yet:

| Item | Current Engine State | Priority | Notes |
|------|----------------------|----------|-------|
| **Jaimini Chara Dasha** | Karakas exist (good). Full time-lord calculation system does **not** exist. | High | Often requested by serious Jaimini practitioners |
| **Natal Yoga Catalog** | Some building blocks exist. No systematic named yoga catalog (Raja, Dhana, Nabhasa, etc.) | Medium | Big for interpretive depth |
| **Varshaphal / Tajika Refinement** | Already quite strong (P8-11/12/13). Remaining work is long-tail yogas and polish | Medium | Lower urgency than Muhurta |
| **Research & Filtering Tools** | Almost nonexistent | Medium | Would benefit all Vedic work |
| **KP Astrology** | Nothing | Low (per analysis) | Very specialized, high effort |

---

## Why This Is Being Tabled (Second Time)

- User declared a new focus.
- Work is in an excellent pausable state with rich, source-cited implementation and clear next steps.
- All doctrine added strictly from classical sources only (Muhurta Chintamani, Kalaprakasika, Ernst Wilhelm *Classical Muhurta*, etc.).

**This is the second deliberate pause.** Previous pause was 2026-05-29 initial; this resumption delivered major high-priority advances before tabling again.

---

## How to Resume

1. Read this file (`TIER2_VEDIC_WORK_TRACKER.md`) — it now contains the complete record of two resumption pushes.
2. Read the latest central memory (see below) and `.remember/remember.md`.
3. Start with the highest remaining priority in the updated "What's Missing" table.
4. Maintain the strict "research from source material only" rule with explicit citations.

**Key new surfaces from latest push** (ready for use):
- `detect_muhurta_doshas()`
- `evaluate_muhurta_lagna_strength(chart, activity=None)`
- Enhanced `MuhurtaClassification` (tara, doshas, dosha_severity, panchaka fields, etc.)
- Full wiring through `muhurta_scorer` and `find_best_muhurta_windows`

---

**Last updated:** 2026-05-29 (second pause — rich state captured after major high-priority advances)
