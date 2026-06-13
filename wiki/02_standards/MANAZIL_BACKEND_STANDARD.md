# Manazil Backend Standard

Version: 0.1
Date: 2026-06-13
Status: admitted backend standard for Phase 11 REST transport

## Scope

This standard governs Moira's Arabic lunar mansion surface:

- `moira.manazil`

It covers direct ecliptic-longitude mansion assignment, sidereal conversion
policy, bulk longitude assignment, the 28-mansion catalog, and textual
tradition attribution lookup.

It does not govern chart construction, Moon derivation, house systems,
nakshatra computation, or Vedic lunar mansion doctrine.

## Authority Layers

The computational mansion structure is:

- 28 equal stations
- span `360 / 28` degrees
- half-open boundary behavior
- tropical computation by direct longitude
- optional sidereal computation by explicit ayanamsa conversion

The default mansion table follows al-Biruni / Ibn Ezra as represented in
`moira.manazil.MANSIONS`.

Variant textual attributions are admitted for:

- al-Biruni
- Abenragel
- Ibn al-Arabi
- Agrippa
- Picatrix

The variant traditions change nature/signification text. They do not change the
28 equal computational boundaries.

## Governing Objects

The admitted backend objects are:

- `MANSIONS`: ordered catalog of 28 mansion records
- `MANSION_SPAN`: equal mansion span
- `MansionInfo`: static mansion definition
- `MansionPosition`: computed mansion assignment
- `MansionTradition`: textual attribution selector

The admitted computations are:

- `mansion_of(longitude)`
- `mansion_of_sidereal(tropical_longitude, jd, ayanamsa_system, ayanamsa_mode)`
- `all_mansions_at(positions)`
- `all_mansions_at_sidereal(positions, jd, ayanamsa_system, ayanamsa_mode)`
- `variant_nature(mansion_index, tradition)`
- `variant_signification(mansion_index, tradition)`

## Required Transport Invariants

REST transport must preserve:

- mansion index
- Arabic name
- Latin name
- ruling star
- nature
- signification
- degrees inside mansion
- original longitude
- computation longitude
- tropical vs sidereal mode
- sidereal ayanamsa system and mode when used
- tradition attribution selector
- stage sequence

REST transport must not:

- hide sidereal conversion behind defaults when sidereal mode is requested
- compute chart Moon longitude implicitly
- collapse Arabic Manazil into Vedic nakshatra
- claim published-table validation beyond the existing equal-station arithmetic
- treat variant textual traditions as changing the mansion boundaries

## Validation Requirements

Transport admission must verify:

- all 28 mansions are exposed
- `360 / 28` span is preserved
- final instant before a boundary remains in the prior mansion
- exact boundary advances to the next mansion
- `360` wraps to mansion 1
- sidereal mode requires `jd_ut`
- non-finite longitudes and JDs are rejected
- bulk inputs are non-empty and bounded
- bulk keys are non-empty
- mansion index lookup is restricted to `1..28`
- tradition names are restricted to the admitted set

## Non-Goals

This standard does not admit:

- chart-backed Moon mansion routes
- natal chart mansion profiles
- electional scoring
- mansion condition networks
- heliacal or fixed-star mansion variants
- Vedic nakshatra routes
- alternate non-equal mansion boundary systems
