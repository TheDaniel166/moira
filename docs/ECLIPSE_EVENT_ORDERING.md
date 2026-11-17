# Eclipse search ordering

Global solar, native lunar, and NASA-compatible lunar searches use the
represented eclipse maximum, not the time of the associated New Moon or
Full Moon, to decide whether an event is next or previous. `next` requires a
maximum strictly greater than the requested UT1 Julian day; `previous`
requires one strictly smaller. The location-specific solar search applies
the same strict rule to the **local** maximum. An eclipse that is still in
progress but whose relevant maximum has already passed is not returned as
the next maximum.

The searches test a nearby phase on the other side of the request whenever
the existing event-refinement window can place that phase's maximum in the
requested direction. Candidate phase crossings are numerically refined using
the same phase observable so results do not depend on the direction or
starting bracket used by the initial phase search. The native solar and
lunar maximum solvers' 0.125-day windows, the canon 0.2-day TT window and
its month-stepped Delta-T conversion, and the local solar search window are
implementation bounds. They are not proofs of physical completeness. The
legacy season screen, local 12-minute scan and event refinement remain
sampled algorithms; short or otherwise unisolated events can remain missed.

For a request near kernel coverage, a neighboring phase window needed to
exclude a closer maximum can extend outside available ephemeris coverage.
In that case the search may raise `OutOfRangeError`; it does not silently
skip the unexamined interval. The behavior does not certify which event would
be found with a wider kernel. Separate model, time-scale and horizon policies
for native, NASA-compatible and local calculations are unchanged.

When supplied, `max_lunations` still bounds the ordinary directional scan.
An opposite-side neighboring phase that does not yield an eligible maximum
is a lookback/lookahead check and does not consume that scan budget. An
unresolved phase bracket or provider failure is not an absent eclipse. Once
the budget is exhausted, the search does not fetch an additional phase and
reports that no matching event was found within the declared budget.

The diagnostic endpoint delegates to the same public solar selector as the
Python API. Its hybrid evidence and path results remain incomplete numerical
products; see [Eclipse diagnostic API](eclipse-diagnostic-api.md).

Native bulk ranges use native-discovered separation minima as candidates,
then bracket the same New or Full Moon observable used by the Python selector
before computing the event maximum. This makes inclusive range boundaries
consistent with a maximum returned by next/previous search. If a candidate's
local phase bracket is unavailable or unresolved, the range falls back to the
Python selector; provider coverage errors still propagate. The bracket is an
implementation aid, not a proof that the native candidate scan is exhaustive.
