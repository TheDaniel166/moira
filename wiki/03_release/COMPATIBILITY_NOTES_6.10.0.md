# Compatibility Notes - Moira 6.10.0

## Upgrade boundary

Moira 6.10.0 follows 6.9.9. Python 3.10 through 3.14 remain supported. The
required native extension and optional `server` extra retain their existing
ownership. No dependency on an external astrology engine is introduced.

Named IANA zones require an installed timezone database, provided by the OS or
`tzdata`. Windows installations commonly need the latter or an explicit
`PYTHONTZPATH`. Missing data fails explicitly; fixed UTC offsets remain usable
without an IANA database. See the daily Panchanga standard for that contract.

## Observable corrections

- Polynomial ayanamsas now use corrected IAU 2006 general precession.
  Recompute cached sidereal outputs, including vargas, strength and dates whose
  result depends on the corrected angles. Stored J2000 references and named
  mean/true choices remain unchanged.
- Personalized Muhurta uses the supplied natal Moon and the effective selected
  Panchanga ayanamsa. Old results produced with ignored natal inputs or
  contradictory frame settings are not a compatibility oracle.
- The selected Santhanam D60 deity names change from Kindar to Kinnara, Suddh
  to Sudha, Dhannayudh to Dandayudha, and Brahman to Bhramana. Compare stable
  source/ordinal identities rather than display spellings.
- Strict Vedic admission rejects booleans and numeric strings in numeric
  fields, incomplete body maps, inconsistent node pairs, nonfinite numbers,
  unsupported selectors and ambiguous datetime inputs. Supply aware ISO civil
  timestamps where requested. Valid legacy arithmetic is retained except for
  the documented source and astronomical corrections.
- Repaired Sayanadi, D9, Shadbala, dignity and result-provenance contracts can
  change previously incorrect results or reject malformed constructed vessels.
  The owning source and repair receipts are linked from the Vedic register.

## New policies are explicit

Existing harmonic varga defaults remain. `classical_derived_linear` is an
explicit D60 degree attribution, not a claim of a direct classical degree
prescription. Alternative Chara and Argala profiles do not silently replace
the legacy method.

Kalachakra requires `bphs_santhanam_longitude_row_cycle_v1`, supports levels 1
and 2, and returns nine major-period occurrences. Source-only supplied sidereal
calculation requires no kernel. Date composition requires the serving ephemeris;
calendar projection requires an explicit `savana_360` or `julian_365.25` clock.
The calendar uses `jd_utc`; astronomy separately records UT1, TT and TDB.
Positive source intervals that cannot be represented at the requested Julian
date fail explicitly instead of being rounded away. Active intervals are
half-open and lookup does not extend the declared coverage.

Exact source fractions are JSON objects containing decimal-string `numerator`
and `denominator` fields. Pre-birth antardashas remain in the full tree with a
null visible interval. Consumers must preserve occurrence paths, nullable
visibility, source decisions and eligibility status (`not_evaluated`).

REST reports malformed input and coverage/projection limits as 422, unavailable
required resources as 503, and internal generated-result defects as sanitized
500 responses. Read `error_code` and `request_id`; do not parse private messages.

## Resources and excluded work

Packaged asteroid/comet manifests identify external release `2026.10.10.1`.
The external catalogs are separately acquired resources; updating the Python
package does not download or delete them. Historical authority fixtures stay
bound to their historical release. See the
[catalog receipt](../03_validation/SMALL_BODY_CATALOG_RELEASE_2026_10_10_1.md).

The new products retain documented source, span, depth, node-count and search
budgets. Broader traditions, special Lagnas and festival rules are not implied
by profile discovery. Unfinished natal-discovery/light-box work and website
application deployment are excluded from this release.
