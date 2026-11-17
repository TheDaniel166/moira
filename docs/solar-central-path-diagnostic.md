# Solar central-path hybrid diagnostic

`moira.solar_eclipse_hybrid.classify_solar_central_path(calc, event)` is an
opt-in diagnostic. It does not alter `calculate_jd`, `EclipseEvent.data`,
existing search filters, or their instantaneous eclipse types.

The diagnostic uses the native ephemeris and the calculator's policies. It
searches the WGS-84 zero-elevation central-axis interval for points where the
geometric, unrefracted Sun center is above the horizon. The signed central-cone
radius and the independently evaluated topocentric angular-radius ordering
must agree. If daylight witnesses of both signs are found, `status` is
`"hybrid"`; the two witness records expose their times, locations, cone radii,
solar altitudes, and angular-radius ratios.

`status="unresolved"` means the diagnostic could not establish both phases.
It does not establish that the path is total-only, annular-only, noncentral,
or absent. A missing central-axis point at greatest eclipse cannot establish
that no such point exists at another time. The bounded search uses endpoint
ladders and a grid to find candidates, so an unwitnessed sign change or
tangency remains possible. `max_evaluations` limits diagnostic shadow
evaluations; the existing interval solver has its own limit. Ephemeris or
time-data errors propagate to the caller.

Observed sign-change brackets carry a direction and are refined in UT1
binary64 Julian days. They are not an exhaustive list of path transitions,
and a narrow bracket is not a bound on physical eclipse prediction accuracy.
The `subtype` is `None`: a sampled path does not establish the complete
topology and path-end behavior required to claim H2 or H3. The geometric
horizon convention and native physical model can differ from published
catalogs, so a diagnostic result is not an assertion of NASA agreement.

```python
from moira.solar_eclipse_hybrid import classify_solar_central_path

event = calculator.next_solar_eclipse(start_jd_ut)
evidence = classify_solar_central_path(calculator, event)
if evidence.status == "hybrid":
    print(evidence.annular_witness, evidence.total_witness)
else:
    print(evidence.reason)
```
