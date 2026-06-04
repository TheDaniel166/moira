# Savard-A Houses Source Packet

Status: research packet only, not admitted

Purpose:
- collect the currently available modern source chain for the house system now
  labeled `Savard-A`
- separate source-backed geometric claims from naming/provenance uncertainty
- decide whether the system is ready for a formal admission doctrine

## Scope

This note does not admit `Savard-A` into Moira.

It records what can currently be established from accessible modern sources:
- external software documentation
- Astrodienst / Swiss Ephemeris public-facing materials
- Astrolog documentation and change log
- provenance notes about the renaming away from `Albategnius`

## Modern Source Packet

### 1. Astrolog 7.30 change log

Source:
- https://www.astrolog.org/ftp/updat730.htm

Relevant modern claim:
- Astrolog added `Savard-A houses`
- the system is named after `John Savard`
- it uses Savard's description of what he called `Albategnus` houses
- the label was changed because later research concluded that Albategnius did
  not describe this particular house system

Implication:
- this is a modern software-era naming settlement, not a clean classical
  transmission

### 2. Astrolog 7.80 documentation

Source:
- https://www.astrolog.org/ftp/astrolog.htm

Relevant modern claim:
- `Savard-A` is treated as a distinct selectable house system
- Astrolog lists it separately from:
  - Campanus
  - Horizon
  - APC
  - Carter
  - Sunshine
  - Pullen SD / SR

Extracted geometric summary from the Astrolog docs:
- it divides the prime vertical like Campanus
- but instead of direct prime-vertical trisection, it uses parallels of
  declination at one-third / 30 degree intervals

Implication:
- the modern software ecosystem treats `Savard-A` as a real distinct system,
  not merely an alias

### 3. Astrodienst forum archive on naming

Source:
- https://www.astro.com/forarch/pdf/1626054202.pdf

Relevant modern claims:
- Astrodienst users asked what `Savard-A` means
- the response states that `Savard-A` uses John Savard's description of what
  he called `Albategnius` houses
- `Savard-A` naming came out of a Swiss Ephemeris mailing-list discussion
- the renaming away from `Albategnius` was deliberate because historical
  research did not support the old attribution

Implication:
- provenance honesty requires treating `Savard-A` as a modern reconstructed or
  software-transmitted doctrine, not as a securely classical Albategnius
  method

### 4. Swiss Ephemeris tables of houses

Sources:
- https://www.astro.com/swisseph/ae/hts_J_e.pdf
- https://www.astro.com/swisseph/ae/hcs_J_e.pdf
- https://www.astro.com/swisseph/ae/htn_J_e.pdf
- https://www.astro.com/swisseph/ae/hcn_J_e.pdf

Relevant modern claims:
- Swiss publishes operational tables for `System Savard-A`
- tables are provided for northern and southern hemispheres
- tables explicitly include polar latitudes

Implication:
- `Savard-A` is not just an experimental side label; it is operationalized in
  major software
- however, tables alone are not a governing derivation

### 5. John Savard original exposition recovered

Direct source:
- http://www.quadibloc.com/other/as01.htm

Recovered findings:
- the page is titled `Astrological House Systems`
- it is a survey-style exposition by John J. G. Savard
- it includes a dedicated section labeled `Albategnus`
- Savard describes the system as:
  - using parallels of declination
  - dividing the prime vertical into parts by thirds of the declination
    difference between the east/west points and the zenith
  - then using great circles from the north point to the south point to divide
    the sky and intersect the ecliptic

Critical limitation:
- Savard's wording is brief and partially hedged
- his text includes an `apparently` qualifier in the projection description
- the page is explanatory and comparative, not a formal mathematical doctrine
  note

Implication:
- this is better than software-only summaries because it gives us the original
  Savard-side geometric intent directly
- however, it still does not supply a precise enough derivation to admit the
  system cleanly without further reconstruction work

## Provisional Governing Geometry

What the current packet now supports:

1. `Savard-A` belongs to the broad prime-vertical / horizon-projection family.
2. It is Campanus-like in family resemblance, but not identical to Campanus.
3. The distinguishing law appears to be:
   - use declination-parallel structure rather than direct Campanus equal
     segmentation of the prime vertical
   - divide the declination difference from east/west to zenith in thirds
   - use horizon-anchored great circles through those derived points to obtain
     cusp intersections on the ecliptic

What the packet does not yet support strongly enough:

- a precise Moira-owned object formulation with exact branch doctrine
- a trustworthy historical claim connecting the system to Albategnius
- an unambiguous mathematical construction sequence free of interpretive gaps

## Provenance and Naming Findings

These points are now source-backed enough to treat as settled:

- `Savard-A` is the modern honest label.
- `Albategnius` is not a trustworthy canonical name for this system.
- Any Moira admission must preserve that honesty and must not present the
  method as a securely medieval Albategnius doctrine unless stronger evidence
  appears.

## Admission Gate Assessment

### What is strong enough

- distinct modern system identity
- modern operational support in Astrolog and Swiss/Astrodienst
- enough geometric separation from Campanus to justify further study
- direct recovery of Savard's own comparative exposition page

### What is not strong enough yet

- explicit governing equations or construction sequence from source
- stable branch/singularity doctrine
- independent validation source beyond software summaries and tables

## Swiss-Smell Risk

This candidate is high-risk for lineage leakage if implemented too early.

Why:
- the available packet is software-mediated
- the modern naming itself arose from software-forum correction
- absent a direct source text, the implementation could easily collapse into
  "whatever Swiss/Astrolog do for Savard-A"

Therefore:
- numerical replication of external tables would not be enough
- a Moira implementation would need a fresh governing-object derivation note
  before code

## Current Decision

`Savard-A` is a plausible future admission candidate, but not yet ready for
implementation.

Required before admission:
1. restate the recovered Savard geometry in exact Moira terms
2. resolve the ambiguities left by Savard's terse comparative wording
3. declare polar and branch doctrine explicitly
4. only then draft a formal admission doctrine

## Sources

- Astrolog 7.30 change log:
  - https://www.astrolog.org/ftp/updat730.htm
- Astrolog documentation:
  - https://www.astrolog.org/ftp/astrolog.htm
- Astrodienst forum archive on `Savard-A` naming:
  - https://www.astro.com/forarch/pdf/1626054202.pdf
- John Savard original exposition:
  - http://www.quadibloc.com/other/as01.htm
- Swiss Ephemeris Savard-A tables:
  - https://www.astro.com/swisseph/ae/hts_J_e.pdf
  - https://www.astro.com/swisseph/ae/hcs_J_e.pdf
  - https://www.astro.com/swisseph/ae/htn_J_e.pdf
  - https://www.astro.com/swisseph/ae/hcn_J_e.pdf
