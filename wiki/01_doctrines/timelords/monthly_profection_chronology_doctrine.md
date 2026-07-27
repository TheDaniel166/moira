# Monthly Profection Chronology Doctrine

**Status:** Admitted computational projection

**Engine owner:** `moira/profections.py`

**Admitted policy:** `equal_twelfths_of_civil_anniversary_year`
**Historical method not implemented here:** Valens IV.28 luminary-distance

## 1. Problem boundary

Moira already admits the twelve-sign monthly profection sequence: Month 0
starts in the annual profected sign and Months 1 through 11 advance one sign
at a time. That sequence alone does not identify dated start and end instants.

Vettius Valens, *Anthologies* IV.28, describes locating the month through a
different astronomical procedure: for a day nativity, the current Sun's
distance from the natal Sun; for a night nativity, the corresponding lunar
distance. That evidence does not establish that twelve equal dated intervals
are Valens' method.

Moira therefore keeps two claims separate:

1. the twelve-sign lord sequence is admitted astrological doctrine; and
2. dated product intervals are an explicit Moira computational projection.

The projection must never be labelled as a reconstruction of the Valens
luminary-distance technique.

Primary source:

- Vettius Valens, *Anthologies*, book IV, chapter 28, Mark T. Riley
  translation, PDF pp. 402-403:
  <https://www.skyscript.co.uk/pdf/pubs/texts/valens/griscti/docs/Valens-Anthologies.pdf>

## 2. Admitted projection

`MonthlyProfectionIntervalPolicy.
EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR` means:

1. resolve the exact civil-anniversary start and following anniversary in the
   selected IANA timezone;
2. convert both anchors to UTC instants;
3. divide the exact elapsed UTC duration into twelve integer-microsecond
   partitions;
4. assign monthly sequence index 0 through 11 to those partitions; and
5. expose every interval as `[start, end)`.

For a total duration of `D` microseconds, boundary `i` is:

`start + floor(D * i / 12) microseconds`, for `i` in `0..12`.

This guarantees:

- the first boundary is the exact current civil anniversary;
- the final boundary is the exact following civil anniversary;
- adjacent intervals share the same boundary;
- there are no gaps or overlaps;
- interval durations differ by at most one microsecond; and
- an instant exactly on a boundary belongs to the interval that starts there.

The projection is not:

- twelve fixed 30-day periods;
- a 365.25-day quotient;
- twelve civil-calendar months;
- a silent local-time approximation; or
- the Valens IV.28 luminary-distance method.

## 3. Civil-time policy

REST callers should supply `civil_timezone` as the authoritative IANA
timezone even when `natal_dt` has been normalized to UTC. Direct Python
callers may omit it to retain the timezone attached to `natal_dt`, but that
compatibility path is identified as caller-supplied timezone data.

Explicit IANA requests are resolved through Python's standard-library
`zoneinfo` interface. Moira does not silently download or substitute timezone
data; the request fails closed when the host has no matching IANA entry. The
chronology receipt therefore identifies `stdlib_zoneinfo` as the data source
without claiming a database version that the host did not expose. It also
preserves:

- `civil_timezone`;
- `timezone_data_source`;
- `timezone_data_version`;
- `ambiguous_time_policy`;
- `ambiguous_time_resolution_applied`;
- the exact UTC and Julian Day annual boundaries; and
- the exact UTC and Julian Day query instant.

Civil anniversaries preserve the natal local wall clock. Moira does not
silently move an anniversary that falls in a daylight-saving gap. Such a
query fails closed. If a repeated local wall time makes an anniversary
ambiguous, the caller must explicitly choose `earlier_occurrence` or
`later_occurrence`; Moira never guesses a fold. The receipt records the chosen
policy and whether ambiguity resolution was actually required. The exact
natal instant remains the age-zero anchor.

A February 29 nativity still requires the explicit `february_28` or
`march_1` anniversary policy. The selected policy appears in both the annual
result and chronology receipt.

## 4. Typed contract

`profection_chronology()` returns `ProfectionChronology`, containing twelve
`MonthlyProfectionInterval` values and one `active_month_index`.

The receipt fixes:

- `method="computational_projection"`;
- `interval_policy="equal_twelfths_of_civil_anniversary_year"`;
- `boundary_semantics="start_inclusive_end_exclusive"`;
- ordered indices `0..11`;
- exact sign, lord, longitude, UTC, and Julian boundaries; and
- exactly one interval active at the query instant.

`profection_schedule()` attaches this receipt to
`ProfectionResult.chronology`. `annual_profection()` has no query chronology
and therefore returns `chronology=None`.

The same typed policy and receipt must survive root, `moira.classical`,
facade, `Moira`, serializer, REST response, and OpenAPI surfaces. A website
may format these instants in the saved display timezone, but it may not
recompute, round, replace, or relabel the interval boundaries.

## 5. Historical method outside this contract

An implementation of Valens IV.28 would require a separate method identifier,
day/night dependency handling, current luminary positions, boundary
resolution, source-owned examples, and comparison fixtures. It must not be
introduced as another spelling of the equal-twelfths projection and is not
unfinished work for this contract.
