# Moira House Engine — Divergence from Swiss Ephemeris

*A derivation-and-divergence reference for Moira's house systems, grounded in `moira/houses.py`.*

---

## Why this document exists, and what "divergence" honestly means

House geometry is **forced-convergent**. Each named house system has a single mathematical definition, and any correct implementation of that definition — Moira's, Swiss Ephemeris's, or anyone else's — must produce the same cusps at admissible latitudes, to arcsecond precision. There is only one way to trisect a semi-arc.

That means **the cusp values are not where divergence can honestly be claimed.** At normal latitudes Moira agrees with any correct engine *by mathematical necessity, not by derivation* — and resemblance in that layer is not evidence of copying. To assert that Moira's core geometry "diverges" from Swiss would be both false and a misunderstanding of the mathematics.

Where Moira genuinely and demonstrably diverges is the **discretionary layer** — the band of choices the mathematics does *not* force:

1. **Derivation path** — Moira derives each system from its primary geometric definition (spherical trigonometry, vector cross-products, the system's own defining equation), not from a reference implementation used as a template.
2. **High-latitude / polar domain behavior** — where the geometry breaks down, every implementation must *choose* what to do. Moira's choices are explicit, typed, and in several cases more capable than the conventional fallback.
3. **Numerical method** — how a non-closed-form system is actually solved.
4. **Error semantics** — what happens when a value is undefined.
5. **Architecture** — how the engine preserves the distinction between what was requested and what was computed.

This document records those divergences per system. Where it references Swiss Ephemeris behavior, it does so only at the level of Swiss's *publicly documented* conventions; exact numerical comparison belongs in the validation layer, where Swiss is used as a regression anchor and never as the definition of correctness.

---

## Engine-wide divergences (apply across all 22 systems)

These are properties of the engine, not of any single system, and they are where Moira departs most clearly from a conventional implementation.

### 1. Critical latitude is computed from the chart's actual obliquity

Moira's polar threshold is `90° − ε(JD)` — the true geometric Arctic Circle for the chart's own epoch, recomputed from the obliquity in force at call time (≈ 66.56° at J2000, but genuinely different for ancient or future charts). It is **not** a hardcoded constant.

> The header records that an earlier fixed `75.0°` threshold "was wrong: it silently passed garbage results from ≈66.6° to 74.9°." Replacing a fixed cutoff with an obliquity-derived one is a deliberate correctness divergence from the common practice of pinning a single latitude.

### 2. No silent `arccos` clamp — explicit failure instead of plausible garbage

The standard high-latitude failure mode is to clamp the argument of `arccos(−tan φ · tan δ)` to `[−1, 1]` and return a value that *looks* valid (a 90° semi-arc) but is physically meaningless. Moira refuses this. `_placidus_semi_arc_event` states it directly:

> "No repair-shaped clamp. High-lat domain cases are owned by the branch search … Domain error will surface from acos if ever reached (explicit failure, not silent 90°)."

Surfacing the undefined case rather than masking it is a divergence in **error semantics**: Moira never silently presents a corrupted cusp as a real one.

### 3. Typed, explicit polar fallback policy

Polar fallback is a first-class, configurable `PolarFallbackPolicy` (`FALLBACK_TO_PORPHYRY`, `FALLBACK_TO_EQUAL`, `FALLBACK_TO_WHOLE_SIGN`, `RAISE`, or `EXPERIMENTAL_SEARCH`), carried on the result via `HousePolicy`. Swiss Ephemeris's documented behavior above the polar circle is to fall back to Porphyry; Moira makes that decision **explicit, selectable, and recorded**, rather than a hidden default.

### 4. Branch-search admissibility before fallback (Placidus, Alcabitius)

For Placidus and Alcabitius, Moira does not fall back the moment the simple formula fails. It first runs an integrated **branch search** for a unique, ordered, admissible figure (Placidus: ordered semi-arc cycles; Alcabitius: a direct zero-pole ordered-figure doctrine), and returns that real figure when one exists. Both are therefore classified `polar_capable = True`. This is strictly more capable than immediate fallback, and it is original work, not conventional behavior. (Koch, Campanus, Regiomontanus, and Topocentric remain in the outer polar guard, honestly flagged, because their branch doctrine is not yet integrated.)

### 5. Truth preservation: requested vs. effective system

Every result carries `system` (what was requested, never mutated), `effective_system` (what actually ran), `fallback`, and `fallback_reason`. A polar fallback is therefore **never** silently presented as the requested system — the substitution is always visible and explained. This is an architectural divergence from engines that quietly return Porphyry cusps under a Placidus label.

### 6. Structural invariant guards

Cusp assembly is checked at construction: the quadrant builders assert that H4/H7/H10 anchor to IC/DSC/MC within `1e-8°`, and `HouseCusps.__post_init__` raises on any inconsistent figure before a caller can see it. Correctness is enforced, not assumed.

### 7. Derivation from primary definitions, with documented model-basis differences

Throughout, the executable path is built from spherical-trig identities and vector geometry tied to each system's definition, with model-basis differences (frame conventions, Δt branch, event semantics) **documented rather than tuned away**. A derived implementation cannot knowingly diverge from its source and publish the reasons; Moira does.

---

## Per-system reference

For each system: **Basis** = Moira's derivation; **Divergence** = where Moira departs from conventional/Swiss behavior. Numerical agreement at admissible latitudes is assumed throughout and is not itself a divergence.

### Equal family — ecliptic

**Whole Sign** — *Basis:* H1 is the 30° sign boundary containing the Ascendant; cusps step 30°. *Divergence:* none meaningful; the definition is arithmetic and admits no discretion. Moira derives it directly (`floor(asc/30)·30`) rather than via any library call.

**Equal** — *Basis:* 30° steps measured forward from the Ascendant. *Divergence:* none meaningful; pure arithmetic from the definition.

**Equal-MC** — *Basis:* 30° steps with House 10 anchored to the MC (`mc + 90 + 30·i`). *Divergence:* a distinct, explicitly provided variant; the choice of MC anchoring vs. ASC anchoring is doctrinal and is exposed as its own system rather than folded into Equal.

**Vehlow** — *Basis:* equal houses shifted so the Ascendant sits at the *midpoint* of House 1 (offset half a house). *Divergence:* provided as a first-class system; the half-house centering is a doctrinal choice made explicit.

### Equal family — equatorial

**Morinus** — *Basis:* uniform 30° steps in right ascension from `ARMC + 90°`, projected to the ecliptic through the Morinus inverse relation (`_project_ra_morinus`). *Divergence:* derived from the equatorial-division definition; the projector is the defining Morinus relation, kept distinct from the plain equatorial projector used by Meridian.

**Meridian (Axial Rotation)** — *Basis:* same equatorial 30° division cycle as Morinus, but projected with the straight equatorial-plane projector (`_project_ra_equatorial`). *Divergence:* Moira separates Meridian and Morinus by *projector*, making explicit a distinction that is often blurred.

**Zariel** — *Basis:* equal 30° RA steps anchored at the Ascendant's RA, equatorial projection. *Divergence:* the equatorial RA-equal member anchored at RA(ASC) rather than ARMC+90° — provided as a separate, clearly-anchored system.

### Quadrant trisection — ecliptic

**Porphyry** — *Basis:* each of the four ecliptic quadrants (ASC→IC→DSC→MC) is trisected directly on the ecliptic. *Divergence:* none meaningful; this is the all-latitude fallback target precisely because it requires only the angles. Moira derives it as plain quadrant trisection with invariant checks on the cardinal cusps.

### Sinusoidal

**Pullen SD (Sinusoidal Delta)** — *Basis:* the compressed quadrant size `q` is measured from the Asc/MC arcs; house widths follow Pullen's **arithmetic-difference** progression (`n = (90−q)/4`, `x = (q−30)/2`), with the sub-30° degenerate case (compressed middle collapses to zero) handled from the definition. *Divergence:* derived entirely from Pullen's own width law; the degenerate-quadrant handling is a documented discretionary choice, not a borrowed clamp.

**Pullen SR (Sinusoidal Ratio)** — *Basis:* Pullen's **geometric-ratio** progression, with the ratio `r` solved *directly from its defining equation*, `x·r³·(r+2) = 180 − q` with `x = q/(2r+1)`, by bracketed bisection. *Divergence:* this is the function that was at the center of the Swiss provenance challenge; it now exists as a re-derivation straight from the defining equation — you cannot reconstruct the ratio root by copying output, you must solve the definition. The closed-form derivation *is* the independence.

### Semi-arc

**Placidus** — *Basis:* the governing event is the diurnal/nocturnal semi-arc; a cusp at fraction `frac` is the ecliptic point that has traversed exactly `frac` of its semi-arc from the meridian (`RA(λ) − ARMC = frac · DSA(λ)`). Solved by **Newton–Raphson with an analytic derivative** `dDSA/dλ` (not numerical differencing), seeded from the exact `DSA(ASC)` rather than the equatorial `≈ 90°` approximation. *Divergence:* (a) analytic-derivative Newton solve vs. plain fixed-point iteration; (b) **no silent clamp** — the semi-arc event raises rather than fabricating a 90° arc; (c) **integrated branch search at high latitude**, returning real ordered figures where they exist instead of falling back immediately (`polar_capable = True`); (d) ASC-seeded initial guess, which is strictly better than the conventional seed.

**Alcabitius** — *Basis:* the Ascendant and Descendant semi-arcs are divided into equal temporal parts, then projected to the ecliptic through a **direct zero-pole** construction. *Divergence:* the zero-pole ordered-figure doctrine is integrated for high latitude (`polar_capable = True`), where the conventional treatment fails or falls back.

**Koch** — *Basis:* the ascensional arc from MC to ASC is divided into equal temporal steps on the equator, projected back via **graduated pole-height** specs (`_koch_pole_height_specs`). *Divergence:* explicit per-cusp pole-height doctrine; honestly flagged as still polar-guarded (`polar_capable = False`) because its branch doctrine is not yet integrated — Moira does not pretend a capability it has not built.

### Projection (great-circle / pole-height)

**Campanus** — *Basis:* the prime vertical is divided into equal sectors; each sector's great-circle **plane normal** is built from the local east and zenith vectors, intersected with the ecliptic via cross-product, and the correct intersection is chosen by an explicit **horizon-branch selector**. *Divergence:* the construction is the historical prime-vertical / vector definition with explicit above/below-horizon branch resolution — not the simplified celestial-pole projection that diverges at high latitude.
*Polar status:* currently outer-guarded at the critical latitude (`polar_capable = False`) because its integrated polar branch doctrine is not yet admitted.

**Regiomontanus** — *Basis:* the equator is divided into equal sectors from ARMC, projected with **graduated pole heights** `atan(tan φ · sin 30°)` and `atan(tan φ · sin 60°)`. *Divergence:* Moira uses the **historical pole-height (great-circle) construction**, explicitly *not* the simplified `tan λ = sin θ / (cos θ·cos ε − sin ε·tan φ)` celestial-pole formula that differs by degrees at high latitude. (This is the exact distinction independent analyses of the Meeus Ch. 24 "simplified" form have flagged.)
*Polar status:* currently outer-guarded at the critical latitude (`polar_capable = False`) because its integrated polar branch doctrine is not yet admitted.

**Topocentric (Polich–Page)** — *Basis:* equatorial poles spaced from ARMC, projected with the doctrinal Polich–Page pole heights `atan(⅓·tan φ)` and `atan(⅔·tan φ)`, resolved by antipodal-branch selection. *Divergence:* explicit graduated-pole-height doctrine with MC-swap handling for the wrong-hemisphere case.
*Polar status:* currently outer-guarded at the critical latitude (`polar_capable = False`) because its integrated polar branch doctrine is not yet admitted.

**Krusinski–Pisa** — *Basis:* the great circle through the **Ascendant and the Zenith** is divided into equal sectors and projected back through a rotated frame (composed x-axis rotations). *Divergence:* derived from the Asc–Zenith great-circle definition in an explicit rotated frame; classified `polar_capable = True`.

**APC** — *Basis:* the APC formula construction with branch candidates and explicit sheet selection (`_apc_project_candidates`, `_apc_select_branch`). *Divergence:* explicit candidate/branch resolution plus a strict ordered-cycle admission check; at supra-critical latitudes an unordered projection is governed by the caller's declared polar policy rather than published as a valid figure. Classified `polar_capable = True` conditionally on that admitted cycle.

### Equatorial-stepped quadrant

**Carter (Poli-Equatorial)** — *Basis:* the complete equatorial cycle is divided uniformly from RA(ASC) and projected back to the ecliptic. *Divergence:* the Ascendant is the Carter cycle anchor; MC and IC remain chart angles rather than being inserted into the cusp cycle. This avoids mixing two incompatible assembly doctrines.

### Horizon

**Azimuthal (Horizontal)** — *Basis:* the prime vertical is divided by azimuth; each cusp's plane normal is `zenith × horizon_direction`, intersected with the ecliptic and resolved by an azimuth-branch selector. *Divergence:* both lawful north- and south-oriented horizon sequences are assembled, and exactly one must form a strictly ordered ecliptic cycle. An exact projection collapse raises a named geometry error instead of publishing overlapping houses; classified `polar_capable = True`.

### Solar

**Sunshine** — *Basis:* a solar-position construction parameterized by the Sun's longitude, latitude, and obliquity. *Divergence:* a SOLAR-family system computed from solar geometry rather than the Asc/MC frame.

**Solar Sign** — *Basis:* sign-based houses anchored to the Sun's sign (ecliptic). *Divergence:* a doctrinal SOLAR variant, provided explicitly.

---

## The honest bottom line

- At admissible latitudes, Moira's cusps converge with any correct engine, including Swiss Ephemeris, **because the mathematics forces it** — that convergence is expected and is not evidence of derivation.
- Moira's real, documentable divergences are in the **discretionary layer**: obliquity-derived critical latitude, refusal to silently clamp undefined `arccos`, typed and recorded polar fallback, integrated branch-search admissibility for Placidus and Alcabitius, requested-vs-effective truth preservation, structural invariant guards, and derivation from each system's primary definition rather than from a reference implementation.
- Where Moira is *not* yet more capable than convention (Koch, Campanus, Regiomontanus, Topocentric at the poles), it says so plainly rather than overclaiming.

The engine converges where the math demands it and diverges where doctrine and engineering judgment enter — and it documents which is which. That is the difference between an independent derivation and a copy.
