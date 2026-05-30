# Tier 2 Vedic Competitive Edge Work – Paused State

**Last active:** 2026-05-29  
**Status:** Paused by user request (other priorities to address first)

**Context:**  
Per `MOIRA_COMPETITIVE_ANALYSIS.md`, after Phase 8 the highest-leverage remaining work for competitive Vedic capability is in Tier 2 (practitioner workflow gaps). The user chose to prioritize closing these **before** moving into Phase 9 (Vedic transport surfaces).

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

- Core vessels: `MuhurtaPolicy`, `MuhurtaClassification`, `MuhurtaScore`
- Basic classification & scoring on top of Panchanga (using researched rules)
- Dagdha Yogas table (from BPHS Ch. 85)
- Vishti/Bhadra Karana detection
- Initial Tithi / Vara / Nakshatra / Karana classification functions
- Named Muhurtas:
  - `is_abhijit_muhurta()`
  - `is_brahma_muhurta()`
- Activity-specific guidance table (`ACTIVITY_MUHURTA_GUIDANCE`) covering:
  - Marriage (Vivaha)
  - House Construction (Griharambha)
  - House Entry (Grihapravesh)
  - Travel (Yatra)
- `muhurta_scorer(chart, ...)`
- Significantly improved `find_best_muhurta_windows(...)` — now actually scores and returns filtered results using the electional scanner
- Proper source citations in docstrings (Muhurta Chintamani, BPHS Santhanam translation, etc.)
- Exposed via `moira/__init__.py` and main `Moira` facade

### What's Missing / Needs Expansion (Prioritized)

| Area | Current Maturity | What's Missing | Priority for Competitive Edge | Notes / Sources |
|------|------------------|----------------|-------------------------------|-----------------|
| **Panchanga Shuddhi Depth** | Partial | Full Tara Bala (with proper indexing), Chandra Bala, all Panchaka doshas, more granular Yoga classifications beyond the 5 Ashubha, detailed Karana preferences (not just Vishti) | High | Muhurta Chintamani, Kalaprakashika, BPHS |
| **Activity-Specific Rules** | Good starter | Much more granular + purpose-specific rules (e.g. different rules for love vs arranged marriage, different Vastu rules for different house types, long-distance vs short travel, business opening vs partnership, etc.) | High | Muhurta Chintamani has extensive activity-specific guidance |
| **Named & Special Muhurtas** | Basic (2 done) | Godhuli Muhurta, Vijaya Muhurta, Amrita Muhurta, Ravi Yoga, Sarvarthasiddhi Yoga, and many others + their exact windows and conditions | Medium | Muhurta Chintamani + traditional lists |
| **Dosha Detection + Parihara** | Almost none | Systematic detection of common Muhurta doshas (Gandanta in Muhurta, Yamaghanta, Visha Ghati, etc.) + suggested remedies/pariharas | High | Critical for practitioner usability |
| **Lagna & Planetary Strength** | None | Lagna shuddhi checks, Jupiter in Kendra, benefic aspects on Muhurta Lagna/Moon, overall chart strength evaluation for the Muhurta | High | Standard in classical Muhurta |
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

## Why This Is Being Tabled

- User has other priorities to address first.
- Muhurta work is in a good "pausable" state with clear next steps documented.
- All research has been source-driven (no memory-based rules added).

---

## How to Resume

1. Read this file (`TIER2_VEDIC_WORK_TRACKER.md`).
2. Read the latest `.remember/remember.md` for overall project context.
3. Start with the highest remaining priority in the "What's Missing" table above.
4. Continue the strict "research from source material only" discipline (Muhurta Chintamani, BPHS, Brihat Samhita, etc.).

---

**Last updated:** 2026-05-29 (paused)