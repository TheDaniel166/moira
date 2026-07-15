# Western Electional Phase 4 Validation — 2026-07-15

## Scope

This record covers implementation-plan issues 5, 6, and 9 only:

- Dorotheus V.31 matter-significator fortification testimonies;
- Dorotheus V.6.29 supplementary inception/outcome indicators;
- Ramesey Book III, chapter II urgent-time remedy fulfillment.

It does not validate astrological efficacy, create a score, or establish a
complete electional judgement.

## Primary authority and source decisions

Dorotheus was checked against *Carmen Astrologicum*, the Umar al-Tabari
translation, Benjamin Dykes translation and edition, Book V.6.21-31 (printed
pp. 236-237) and V.31.1-11 (printed pp. 276-277).

V.31 names four separate conditions: under the rays, made unfortunate, not
looking at the Ascendant, and in a bad place. The first, third, and fourth are
computed under explicit Moira policies. “Made unfortunate” remains
`not_evaluable`: the primary passage does not define an exclusive closed set.

V.6.22 retains the Moon-sign lord as the primary outcome indicator. V.6.29
does not authorize interchangeable outcome rulers. It adds the editorial
ninth-part lord, the Lot-of-Fortune lord for inception, and the Moon's next
connection for outcome. Edition note 31 identifies the ninth-parts phrase as a
Persian editorial insertion and provides no division scheme, so that witness
is `not_evaluable`. The Fortune witness reuses Moira's sect-aware Lots engine.

Ramesey was checked against *Astrologia Restaurata* (1654), Book III, chapter
II, printed pp. 127-128. The Moon/Ascendant and fortune/Ascendant instructions
are evaluated under visible whole-sign and quadrant-house policies. The
planetary-hour lord is resolved. The three fortification commands remain typed
`indeterminate` source gates because the cited passage supplies no closed
fortification predicate.

## Public contract

The following existing routes carry the Phase 4 witnesses:

- `POST /v1/electional/western/dorotheus-rooted-context`
- `POST /v1/electional/western/ramesey-moon-condition`

The same vessels are available from the engine module, package root, facade,
and `Moira` methods. Dorotheus rooted context reports profile version `1.2.0`;
Ramesey Moon condition reports profile version `1.1.0`.

## Verification receipt

Runtime: project `.venv`, Python 3.14.3. Downloads were disabled. Strict known
issue expiry was enabled; `tests/KNOWN_ISSUES.yml` contained no entries. The
planetary kernel resolved through `moira._kernel_paths` to the local DE441
resource.

Commands and results:

```text
python -m pytest tests/unit/test_western_electional.py \
  tests/unit/test_dorotheus_rooted_context.py -q
97 passed

python -m pytest tests/server/test_server_western_electional_routes.py \
  tests/server/test_server_dorotheus_rooted_context_routes.py -q
11 passed

python -m pytest <all Western/Dorotheus/Sahl/lunar-direction electional files> -q
205 passed

python -m pytest tests/unit/test_api_surface_adversarial_audit.py \
  -q -k "not built_wheel"
9 passed

python scripts/check_doc_consistency.py
passed
```

The governance run deliberately excluded the local wheel-build test. No wheel
was built, published, or present in the repository.

## DE441 evidence

At JD 2451545.0, London, Regiomontanus houses:

- the Ramesey hour lord resolved to Mercury;
- the Moon cadence/no-Ascendant-relation clause was `not_fulfilled`;
- the Jupiter/Venus fortune clause was `fulfilled`;
- aggregate remedy fulfillment was `not_fulfilled`, without changing any Moon
  impediment state;
- the Lot of Fortune was 326.9694195743265 degrees tropical longitude,
  Aquarius, ruled by Saturn;
- the sign-bounded next Moon connection remained the independently checked
  Mars square.

These are regression and geometric-invariant evidence under the named
products, not empirical validation of electional doctrine.

## Remaining source gates

- Dorotheus V.31 “made unfortunate” lacks an exclusive predicate set.
- Dorotheus V.6.29's editorial ninth-part lacks a source-owned division and
  boundary scheme.
- Ramesey's Ascendant-cusp, Ascendant-lord, and hour-lord fortification
  commands lack closed predicates in pp. 127-128.

Phase 4 is complete at those source boundaries: each gap is a typed,
machine-visible indeterminate witness rather than free text or hidden policy.
