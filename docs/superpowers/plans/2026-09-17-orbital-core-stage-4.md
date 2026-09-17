# Orbital Core Stage 4 Implementation Plan & Checkpoint

> **Execution boundary:** Implement and validate Stage 4 on top of the
> uncommitted Stage 1, Stage 2, and Stage 3 worktree. This plan does not
> authorize an unreviewed commit, version tag, package publication, push, or
> deployment.

**Date:** 2026-09-17

**Status:** Implementation complete and review-ready

**Baseline:** `orbital-core-stage1` at committed base
`dfad306f47901596e9edc254116ac3c6d47a3764`, plus the preserved uncommitted
Stage 1, Stage 2, and Stage 3 implementation.

**Governing spec:**
`docs/superpowers/specs/2026-09-15-orbital-core-design.md`, SHA-256
`fba918c2755181f5d467ed957891278fb249bfde19931ecd310baf6019329a38`.

**Goal:** Execute Stage 4 (the source-correct Shadbala Chesta Bala doctrinal
redesign) by retiring the legacy apsidal shortcuts, implementing the primary-source
formulations from B. V. Raman's *Graha and Bhava Balas* (13th edition, 1992),
eradicating all inapplicable "Raman Ch. 9" Chesta citations, and sealing the
validation receipt.

---

## 1. Doctrinal and Astronomical Authority

Primary-source inspection of B. V. Raman's authoritative treatise,
*Graha and Bhava Balas* (Thirteenth Edition, preface dated 1 February 1992,
UBS Publishers' Distributors Ltd. / Raman Publications, Bangalore):

### Luminaries (Sun & Moon)
Governed by **Chapter X (§§136–137, pp. 101–103)**:
- **Sun (§136)**:
  $$\text{Arc} = (\lambda_{\text{sayana}} + 90^\circ) \pmod{360^\circ}$$
  $$\text{Reduced Arc} = 360^\circ - \text{Arc} \quad \text{if } \text{Arc} > 180^\circ \text{ else } \text{Arc}$$
  $$\text{Chesta Bala}_{\text{Sun}} = \frac{\text{Reduced Arc}}{3} \quad \in [0, 60] \text{ Virupas (Sha)}$$
  *Astrological Meaning*: Motional/Ayana proxy: 60 Virupas at northern solstice / Cancer ingress,
  0 Virupas at southern solstice / Capricorn ingress, 30 Virupas at equinoxes.
- **Moon (§137)**:
  $$\text{Elongation} = |\lambda_{\text{Moon}} - \lambda_{\text{Sun}}| \pmod{360^\circ}$$
  $$\text{Reduced Elongation} = 360^\circ - \text{Elongation} \quad \text{if } \text{Elongation} > 180^\circ \text{ else } \text{Elongation}$$
  $$\text{Chesta Bala}_{\text{Moon}} = \frac{\text{Reduced Elongation}}{3} \quad \in [0, 60] \text{ Virupas (Sha)}$$
  *Astrological Meaning*: Motional/Paksha proxy: 0 Virupas at New Moon / conjunction,
  60 Virupas at Full Moon / opposition, 30 Virupas at quarter Moons.

### Five Non-Luminaries (Mars, Mercury, Jupiter, Venus, Saturn)
Governed by **Chapter VI (*Chesta Bala or Motional Strength*, pp. 64–79)**:
- Governed by the **Chesta Kendra** arc:
  $$\text{Chesta Kendra} = \left(\text{Seeghrochcha} - \frac{\bar{\lambda} + \lambda}{2}\right) \pmod{360^\circ}$$
  $$\text{Reduced Kendra} = 360^\circ - \text{Chesta Kendra} \quad \text{if } \text{Chesta Kendra} > 180^\circ \text{ else } \text{Chesta Kendra}$$
  $$\text{Chesta Bala} = \frac{\text{Reduced Kendra}}{3} \quad \in [0, 60] \text{ Virupas (Sha)}$$
- For **Superior Planets (Mars, Jupiter, Saturn)**: Seeghrochcha is the Sun's longitude;
  mean longitude $\bar{\lambda}$ is the planet's mean orbital longitude evaluated from
  Moira's strict orbital core (`osculating_elements` in `TRUE_ECLIPTIC_OF_DATE`).
- For **Inferior Planets (Mercury, Venus)**: Seeghrochcha is the planet's heliocentric
  longitude; mean longitude $\bar{\lambda}$ is the Sun's longitude.

---

## 2. Retired Legacy Mechanisms

1. `_sun_mandoccha_lon`: deleted from `moira.shadbala`.
2. `_moon_mandoccha_lon`: deleted from `moira.shadbala`.
3. Inapplicable orbit-helper imports (`orbital_elements_at`, `_keplerian_from_state`, `_rot_eq_to_ecl`): removed.
4. Erroneous "Raman Ch. 9" citations for Chesta Bala: eradicated across docstrings, code, and standards.
5. Speed-ratio heuristic: demoted to backward-compatible fallback when position coordinates and ephemeris context are omitted.

---

## 3. Measured Shifts (J2000 Baseline)

Evaluated at $JD = 2451545.0$ UT1, Lahiri Ayanamsa:

| Planet | Legacy Chesta (Sha) | Stage 4 Chesta (Sha) | Shift $\Delta$ (Sha) | Primary Doctrine Mechanism |
|---|---|---|---|---|
| **Sun** | 59.5200 | 3.4563 | -56.0637 | Sayana longitude $+ 90^\circ$ / 3 |
| **Moon** | 12.0229 | 19.0151 | +6.9922 | Sun–Moon elongation / 3 |
| **Mars** | 41.2214 | 20.4463 | -20.7751 | Chesta Kendra from Sun Seeghrochcha & orbital core $\bar{\lambda}$ / 3 |
| **Mercury** | 33.6153 | 7.3943 | -26.2210 | Chesta Kendra from heliocentric Seeghrochcha & Sun $\bar{\lambda}$ / 3 |
| **Jupiter** | 43.3213 | 36.4813 | -6.8400 | Chesta Kendra from Sun Seeghrochcha & orbital core $\bar{\lambda}$ / 3 |
| **Venus** | 31.2500 | 26.1308 | -5.1192 | Chesta Kendra from heliocentric Seeghrochcha & Sun $\bar{\lambda}$ / 3 |
| **Saturn** | 35.8209 | 41.6093 | +5.7884 | Chesta Kendra from Sun Seeghrochcha & orbital core $\bar{\lambda}$ / 3 |

---

## 4. Verification Evidence

1. `tests/unit/test_shadbala.py`: 166 passed (includes 12 dedicated Raman Ch. VI & X mathematical tests).
2. `tests/server/test_server_shadbala_routes.py`: 15 passed (complete server contract match).
3. `tests/unit/test_orbital_stage4_validation_receipt.py`: 3 passed (path-free governance).
4. `wiki/02_standards/SHADBALA_BACKEND_STANDARD.md`: updated and synchronized with `moira.wiki`.
