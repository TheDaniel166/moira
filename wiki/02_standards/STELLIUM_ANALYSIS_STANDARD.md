# Planet-first stellium analysis

Contract: `moira.stellium.v1`. Owner: `moira/stelliums.py`.

This is concentration evidence, not an aspect-edge pattern or a strength
score. Strict and Broad are named Moira policies, not historical universals.

## Eligibility and qualification

Only Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune and
Pluto satisfy the planetary count. Strict requires four; Broad requires three.
Nodes, Chiron, angles, lots, Lilith and explicitly selected other non-core
identities may annotate an already-qualified match. They never increase the
count, move a core arc, bridge groups, or confer an automatic strength bonus.

The criteria are independent:

| Criterion | Qualification | Associated-factor membership |
| --- | --- | --- |
| Sign | One half-open 30-degree sign in the declared zodiac | Same sign |
| House | One actual house via `assign_house` in an admitted same-frame house snapshot | Same actual house |
| Tight | Shortest enclosing circular arc is within the configured maximum total span | Inside the frozen closed core arc |

The default tight limit is **8 degrees total span**, not an eight-degree
centroid radius, and does not scale with aspect orb presets. Allowed limits
are finite numbers from zero inclusive to 180 exclusive. Exact limit equality
qualifies. Display rounding never decides membership.

Identical core membership merges criterion labels. Different memberships stay
distinct, including a tight subset of a wider sign grouping. Tight-only
subset suppression retains inclusion-maximal groups; overlapping maximal
groups remain when neither contains the other. Conjunction chaining is not
a substitute for a bounded total arc.

## Snapshot and frame contract

`analyze_stelliums(positions, *, policy=None, selection=None, context=None,
houses=None, house_unavailable_reason=None)` accepts already-computed
longitudes. It does not calculate a replacement chart, open an ephemeris,
or independently authenticate the caller's astronomy. Finite longitudes are
normalized modulo 360. Duplicate supported aliases, booleans, non-finite
numbers and invalid selections fail rather than being silently admitted.

Positions are already in `context.zodiac` (tropical, sidereal or draconic).
`zodiac_offset_degrees` is a receipt, never an instruction to subtract again.
House analysis needs `StelliumHouseContext(HouseCusps, longitude_frame)`.
Requested/effective system, fallback, policy, geometry and frame are admitted
through engine-owned validation. Bare client-assigned house integers are not
an accepted substitute. The twelve cusps must form one distinct circular
partition; exact cusp ownership follows the existing half-open house rule.

For sidereal Whole Sign, construct the figure in the selected zodiac with
`calculate_houses(..., ayanamsa_offset=offset)`. Do not blindly rotate the
tropical Whole Sign figure. Physical quadrant boundaries may be relabelled
with the same offset as the positions; ARMC is not rotated. Draconic physical
house rotation is a separate source-frame receipt. Unknown birth time or
missing location must not admit guessed house/angle evidence.

At most 256 supplied objects are admitted. Only the ten canonical planets
can be core; unknown non-core identities require explicit caller selection
and source context. Source identity must not encode associated visibility.

## Evidence and identity

`StelliumAnalysis` carries schema, input fingerprint, resolved policy, source
context, requested/computed/missing/excluded coverage, three criterion
evaluations, an optional house receipt and canonical groups. Every match owns
its sign, house or total arc evidence and its own associations. A factor may
share the group's sign without sharing its house.

Group IDs depend on schema, policy, source/frame context and core membership;
adding an associated factor cannot change them. Match IDs add criterion
evidence. The full input fingerprint additionally includes positions,
selection and house geometry. Callers must bind caches and asynchronous
results to the complete input, engine generation and policy, not just birth
datetime or a group ID.

`evaluated` with no group is a genuine negative. Missing selected positions
produce `partial`; missing house context produces criterion-level
`not_evaluable`; unrequested criteria are `not_requested`. Overall status is
`complete`, `partial` or `not_evaluable`. Execution/transport failure is not
a successful empty analysis. Selecting fewer core planets is distinct from
missing requested planet positions.

## Public surfaces and compatibility

The typed vessels, constants and analyzer are exported from `moira.stelliums`,
`moira` and `moira.facade`. `Moira.analyze_stelliums` delegates the supplied
snapshot without calculating astronomy.

`POST /v1/stelliums/analyze` uses the same engine owner. Its strict request
requires `schema_version`, `positions` and `context`; optional policy and
selection default to Strict, eight-degree total span, all criteria and the
ten core planets with no selected associations. REST house input extends the
full existing `HousesResponse` with `longitude_frame`; the adapter rebuilds
canonical vessels and rejects malformed/contradictory evidence with 422.
No datetime-based alternative or ephemeris dependency is introduced.

Legacy `moira.aspects.find_patterns` (mutual-conjunction clustering),
`moira.patterns.find_stelliums` (default three objects and centroid-radius
clustering), `find_all_patterns`, `Moira.patterns`, and `/v1/patterns/*` retain
their compatibility semantics. They do not adopt this planet-first policy.
Migrated consumers must use the new result separately and exclude legacy
Stellium entries from their migrated pattern displays and new packets. No
fallback to legacy strings, invented aspect contributions or `reinforced`
condition relabelling is permitted. Historical saved reports remain historical.

## Verification

`test_stelliums.py`, `test_stelliums_public_api.py` and
`test_server_stelliums.py` exercise count/point non-interference, independent
criteria, exact/wrap/coincident boundaries, deterministic IDs, coverage,
frame and malformed-input rejection, facade exports and HTTP/Python parity.
`test_house_sidereal_frame.py` checks selected-zodiac sign sectors and physical
rotation invariants. Synthetic expectations are the named product contract;
DE441 fixture checks are integration evidence, not a new external accuracy claim.
