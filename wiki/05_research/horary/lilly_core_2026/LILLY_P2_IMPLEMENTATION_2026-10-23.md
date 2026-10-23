# Lilly P2 essential condition and reception evidence

Date: 2026-10-23. Governing specification:
[the collated dignity, orb and reception decisions](LILLY_CORE_DECISIONS_2026-10-23.md).

Status: **implemented as an additive Python module**. The finite evidence API
is in [moira.horary_reception](../../../../moira/horary_reception.py), with
[production regression tests](../../../../tests/unit/test_horary_reception.py).
The existing horary/perfection v1 composition, constants, result meaning and
consumers remain unchanged. Facade/REST expansion and complete judgement
admission are separate gates.

## Profile and ownership

The immutable profile `lilly_1647_condition_reception_v1` identifies the p.104
dignity table, sect-active Lilly triplicity, p.115 positive dignity magnitudes,
and p.107's second full-orb table. Its source contract is
`lilly_1647_core_candidate_2026_10_23`. This version number belongs to the new
condition/reception evidence surface; it does not replace
`lilly_1647_perfection_v1` or `lilly_1647_horary_v1`.

Runtime data reuse the existing source-owned dignity/bounds, triplicity and
Chaldean-face tables. The fixture JSON remains an independent test oracle and
historical admission record, not runtime configuration. Node exaltations remain
documentary data; operational hosts and guests are the classical seven planets.

The module owns no kernel access, astronomical event search, question-time
selection or chronology. Sign/degree data and chart sect are caller-supplied.
The longitude convenience function normalizes finite tropical longitude modulo
360. A sign-local degree is separately validated in `[0,30)` and retains its
stated sign, including immediately adjacent to a terminal boundary.

## Inputs and evidence

`LillySnapshotContext` requires an explicit epoch label and chart sect, which
may be `None`. An optional `jd_ut` records a supplied UT1 Julian date. A label
such as `didactic_unspecified` supplies no historical date. Combining snapshots
requires equality of the complete context, including sect, label and optional
JD. No reception evidence is silently transported to another epoch.
The caller owns snapshot identity: use a case-specific label for an undated
teaching example rather than assigning unrelated examples the same identity.

`LillyPlanetPosition` requires a classical body and tropical sign; degree may
remain unknown. `lilly_condition_snapshot` derives each positive dignity basis,
detriment, fall and peregrinity. Positive dignity membership uses
`present`, `absent` or `not_evaluable`. Detriment and fall remain independent
sign-based facts; they do not create negative reception or a willingness claim.
The printed point magnitudes remain individually visible without a combined
strength, success or confidence score.

| Missing information | Preserved result |
|---|---|
| Degree | Known domicile/exaltation and triplicity remain available; term/face membership is unknown only for hosts that could rule them in that sign |
| Sect | Triplicity is unknown where the two possible rulers differ and include the host; Mars's water triplicity remains known |
| Some positive dignity bases | Known positive dignity establishes non-peregrinity even when other bases are unresolved |
| No positive dignity, but unresolved possibilities | Peregrinity remains unknown |
| Epoch label | Invalid input; no question-time or contact-time default is invented |

## Directed and mutual reception

`LillyDirectedReception(host, guest_snapshot)` means that the host rules a
positive dignity at the guest's supplied position. It reports all five bases,
their possible rulers and affected missing inputs. An aspect is not required
to report this raw membership. Self dignity is excluded from reception.

`lilly_reception_evidence` evaluates every ordered pair among supplied snapshots,
including absent and unknown relations. Output order is deterministic. Unlisted
planets receive no invented positions or relations. Each mutual record retains
both independently evaluated directions, established same-basis witnesses and
established mixed-basis pairs. These witness lists are not exclusive labels;
unresolved bases remain visible in their underlying directional evidence.

```python
from moira.horary_reception import (
    LillyPlanetPosition, LillySnapshotContext,
    lilly_condition_snapshot, lilly_reception_evidence,
)

epoch = LillySnapshotContext("D05-TERM:didactic_unspecified", is_day_chart=None)
venus = lilly_condition_snapshot(
    LillyPlanetPosition("Venus", "Aries", 24), context=epoch,
)
mars = lilly_condition_snapshot(
    LillyPlanetPosition("Mars", "Gemini", 16), context=epoch,
)
relations = lilly_reception_evidence((venus, mars))
# Each receives the other by term. No date, speed or aspect was invented.
```

`adapt_generic_lilly_reception` explicitly converts the existing generic
vocabulary: its `host_planet` is the Lilly host, while its `receiving_planet`
is the Lilly guest. The caller binds the generic relation's context, and the
declared domicile/exaltation basis must be verified at the supplied guest
snapshot. Generic mutual metadata never manufactures a reverse witness.
The mutable generic record is not retained by the new evidence.

## Mechanism prerequisites and orbs

`lilly_translation_reception(source, translator)` requires the source to receive
the translator by domicile, triplicity or term. Exaltation or face alone is
insufficient for this particular p.126 requirement.

`lilly_collection_reception(principal_a, principal_b, collector)` requires each
principal to receive the collector in a positive essential dignity. The
collector is the guest of both edges. Both requirements must hold; one failed
leg makes the prerequisite absent, while an unresolved required leg keeps it
unknown unless another leg already fails.

These outputs have the fixed scope `reception_prerequisites_only`. They do not
establish relative planetary weight, application, separation history, both
contacts, lack of interruption or complete perfection. The evaluation snapshot
is supplied by the caller. Choosing mechanism epochs and event precedence
remains part of the later chronology specification.

`lilly_orb_evidence` evaluates a supplied signed aspect residual in degrees. It
exposes both full planetary orbs and their half-sum, then distinguishes strict
interior, exact boundary and exterior. This is snapshot orb evidence and does
not infer applying or separating motion. Saturn/Jupiter has a nine-degree
allowance in this new profile; v1 retains eleven degrees. No shared constant or
old policy constructor changes.

## Verification and admission limits

The regression suite checks production functions against the pre-existing
photographed table, source reception examples, all dignity boundaries and both
sects. It also checks partial inputs, all supplied pair directions, permutation
stability, context mismatches, changed dignity at a later snapshot, the generic
adapter, mechanism role reversal/allowed bases, all planetary orb pairs and
immutable serializable receipts. The existing v1 suites remain compatibility
checks. The acceptance workflow selects the P2 suite alongside them.

The two contradictory printed numerical assertions remain quarantined. The
source fixture's `runtime_admitted` field remains a historical checkpoint;
this implementation does not promote all teaching narratives into complete
perfection or predictive goldens. No historical event time, speed or outcome
has been reconstructed. Moon/VOC, complete candidate chronology, symbolic
timing, and source-conditioned topic judgement remain later packages.

Local implementation verification passed **756 tests with zero skips**, including
274 new P2 cases. The combined run selected the new P2 tests, the existing
source-fixture/packet/doctrine/perfection/horary suites, and the horary public
API, dignity public API and dignity scoring suites. Ruff passed for the two
new Python files; the engine docstring preflight passed all 383 files. The
new module also parsed with Python 3.10 grammar; actual local execution used
the project `.venv` on Python 3.14.8. This grammar check is not a claim of
execution under a second interpreter.
