# Lunar Direction and Sahl Burnt-Path Validation — 2026-07-15

## Scope

This record validates the Phase 3 computational boundaries for Western
electional issues 2, 3, 4, and 7:

- the source-neutral lunar ecliptic direction and exact node-crossing witness;
- Dorotheus V.6 southern descent;
- Dorotheus V.6 solar disengagement in longitude or latitude;
- Dorotheus V.7 northward latitude motion;
- Sahl section 22d burnt-path policy selection and endpoints.

The astronomical witness is a measurable product. The Dorothean and Sahl
clauses are historical-doctrine interpretations of that product. Passing these
tests is not empirical validation of astrological claims.

## Authorities and source boundary

The Dorotheus authority is *Carmen Astrologicum*, Umar al-Tabari translation,
2nd edition, Benjamin Dykes translator/editor, V.6.7, V.6.10, note 15, and
V.7.1-3, printed pp. 234 and 238. V.6 identifies the ecliptic and names
disengagement in longitude or latitude, but supplies neither a before/after
crossing interval nor a longitude/latitude combination law.

The secondary transmission witness is Hephaistion of Thebes,
*Apotelesmatics* III.7.10, translated by Benjamin Dykes. It describes the Moon
as advancing in latitude toward the north, and the translator's note identifies
north/south as ecliptic latitude. It likewise supplies no numerical crossing
region. This corroborates direction; it does not authorize a node orb.

The Sahl authority is *On Elections* section 22d in Benjamin Dykes,
*Choices & Inceptions*, printed p. 100. The text says only the end of Libra and
the beginning of Scorpio. The same edition's glossary distinguishes the
fall-degree and later Via Combusta conventions, but neither is silently
relabeled as Sahl's missing numeric endpoints.

## Governing astronomical object

`LunarEclipticDirectionWitness` is governed by the Moon's apparent geocentric
ecliptic latitude of date, beta(t):

1. hemisphere derives from the sign of beta at the query instant;
2. northward/southward motion derives independently from a centered latitude
   rate;
3. a node crossing is a sign-changing root beta(t) = 0;
4. the sign of the latitude rate at the root determines ascending or
   descending direction;
5. fixed scanning brackets and deterministic bisection locate the previous and
   next exact roots;
6. the returned numerical tolerances are root policy, not historical doctrine.

The result exposes UT1 event times, root longitude, residual latitude, latitude
rate, hours from query, nearest-root relation, frame, timescale, provenance,
and the explicit scope `astronomical_witness_only_no_doctrinal_region`.

## Doctrine decisions

- Dorotheus V.6 southern descent consumes the exact witness but remains
  `NOT_EVALUABLE`: no source-owned interval around the descending root exists.
- Dorotheus V.7 northward crossing consumes the same geometry under a separate
  policy and remains `NOT_EVALUABLE` for the same missing interval.
- V.6 solar disengagement exposes instantaneous signed conjunction motion and
  independent latitude evidence. It remains `NOT_EVALUABLE` because the source
  does not define whether either branch is sufficient or give either interval.
- Sahl public moment and scan calls require an explicit burnt-path policy. The
  source-faithful selection performs no interval test. The Dykes glossary/fall
  degree interpretation is `[199, 213)` and the later fifteen-degree convention
  is `[195, 225)`, both in tropical longitude with inclusive start and exclusive
  end.

## Evidence classes

- **Invariant testing:** synthetic periodic latitude verifies adjacent root
  order, sign-changing direction, exact-query classification, deterministic
  bisection, and immutable result semantics.
- **Substrate integration:** DE441 verifies that returned prior and next events
  bracket the query and that direct `planet_at` latitude changes sign across
  each returned root with sub-nanodegree residual.
- **Doctrine regression:** Dorotheus witnesses preserve the measured geometry
  while retaining indeterminate states; Sahl endpoint tests exercise both
  half-open boundaries exactly.
- **Public-contract validation:** root exports, facade delegation, REST request
  requirements, response serialization, registered route, and OpenAPI schemas
  are tested together.

## Known limits

No test establishes a historical duration around a node crossing, a physical
visibility threshold for Dorotheus's solar disengagement wording, or a numeric
Sahl endpoint absent from section 22d. Those omissions are preserved as source
boundaries rather than filled by modern convention.
