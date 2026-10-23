# Compatibility Notes - Moira 6.10.2

This patch preserves the 6.10.1 native substrate, dependencies, existing REST
request/response contracts, primary-direction geometry and time-key constants.

The additive `POST /v1/primary-directions/time-keys` request takes an aware natal
`dt` and `items` containing `id`, `arc_deg` (0 through 180 degrees) and explicit
unique `keys`. All six existing key names are supported. A zero arc returns the
natal origin; positive dynamic arcs require the planetary kernel.

The response contains `natal_jd_ut`, `natal_solar_rate_deg_per_day`, the governing
`engine_surface` and projections with `key`, `age_years`, `perfection_jd_ut` and
`perfection_iso`. Submitted arcs are converted as given; this route does not
validate their original geometry or make an astrological interpretation.

Natal Solar Rate timelines that previously failed while projecting distributor
boundaries now succeed with their actual natal Sun speed. Missing ephemeris or
invalid inputs still fail explicitly. Python 3.10 through 3.14 remain supported.
