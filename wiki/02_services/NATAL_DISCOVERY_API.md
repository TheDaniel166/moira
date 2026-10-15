# Natal discovery evidence packets

Three `POST /v1/natal-discovery/` routes compose existing engine products for the
free natal page. They do not add astrology algorithms or modify their defaults.
All responses are structured transport data; consumer interfaces must render
domain labels, units, values and explanations rather than dump these objects.

## Accepted request and source

Each route accepts `dt` (a timezone-aware ISO instant), `longitudes` (only the
selected planets Sun through Pluto, finite degrees in `[0, 360)`), `zodiac`
(`Tropical` or `Sidereal`), `ayanamsa_system`, and `time_unknown`. Sidereal requires
a named system in `Ayanamsa.ALL`; Tropical forbids a supplied ayanamsa. Nonzero
sub-microsecond digits are rejected. Numerically equivalent trailing fractional
zeros are admitted. Birth-time uncertainty remains an explicit boolean.

The source receipt preserves the original instant string and separately exposes
the normalized UTC datetime at Python microsecond resolution and the resolved
UT1 Julian Day. `longitude_basis` identifies caller-supplied accepted geometry.
The website's unknown-time convention supplies a nominal noon reference;
`reference_kind=noon_reference` names that convention, not a recorded birth time.
No route fills omitted selected subjects from defaults.

## `/dispositors`

Delegates to `calculate_dispositorship` with its admitted default
`DispositorshipComputationPolicy`: classic-seven subjects, traditional domicile
rulers, self-domicile final stops, terminal cycles and visible unsupported
subjects. Modern dignity co-rulership is a different doctrine and is not admitted
as a dispositorship option here. Selected Uranus, Neptune and Pluto are reported
as out of scope, not assigned invented chains.

Returned links name their source subject, source sign and sign ruler. The packet
distinguishes `final_dispositor`, `terminal_cycle`, `missing_selected_ruler` and
`out_of_scope`. Several final sinks are preserved as several sinks. A missing
selected ruler is named without inventing its placement. Zero-degree placements,
empty results and cycles remain meaningful values.

## `/shape`

Delegates to `classify_chart_shape` only when every one of the ten Jones planets
is selected. Otherwise `insufficient_selection` returns the missing bodies and
supplied positions without a classification. Nodes, angles and added bodies are
outside the request contract.

Authority and branch policy remain in `moira/chart_shape.py`: Marc Edmund Jones,
*Essentials of Astrological Analysis* (1960), chapters 1 and 2; the authorized
Sabian Publishing Society text; Moira's declared priority order and borderline
Splash residual. There is no new confidence score.

The full-chart circular gap list uses the engine's existing gap helpers. A
Bucket's returned occupied arc and largest gap describe its nine-planet Bowl
core with the singleton handle removed. `metrics_scope=nine_planet_bowl_core`
preserves this distinction from the separately returned ten-planet gap list.
Other classifications use `metrics_scope=all_ten`.

## `/lunar-context`

Unknown-time and missing-luminary requests return explicit uncalculated statuses,
with no phase, events, contacts or source-consistency claim. No nominal-noon
syzygy is advertised as definitely prenatal.

For a recorded time, the packet first witnesses every supplied selected planet
against `Moira.chart(dt, bodies=selected, include_nodes=False)`, geocentric
apparent ecliptic geometry. Sidereal uses the named true-mode ayanamsa at the
resolved UT1 instant. A circular discrepancy greater than `1e-6` degree rejects
the packet. This tolerance admits decimal serialization and microsecond input;
it is not an external-accuracy claim. The accepted caller values remain the
returned natal values after this independent witness.

The forward Sun-to-Moon ecliptic angle and existing `synodic_phase_state` retain
their declared convention. Coarse state labels use 45-degree quadrant boundaries;
waxing is the directed angle below 180 degrees, waning the other half-cycle.
They are distinct from the physical Sun–Moon–Earth angle and physical illuminated
fraction calculated by `phase_angle` and `illuminated_fraction`. Every lunar
ephemeris product is bound with `use_reader_override(engine._reader)` to the
startup-owned kernel reader. No ecliptic illumination approximation is used.

`last_new_moon` and `last_full_moon` find the strictly preceding geocentric
conjunction and opposition. The latest is marked as prenatal syzygy. Returned
event longitudes use the requested zodiac and event-specific true-mode ayanamsa.
Event Julian Days are UT1; UTC display strings use the engine's admitted inverse
UT1-to-civil-UTC conversion, including its historical proxy policy.

Each event Moon longitude is compared with the selected natal planets through
`aspects_between(tier=0, orb_factor=1)`: the existing five major aspect definitions
and default orbs. Contacts preserve target angle, actual separation, deviation
and applied orb ceiling. No speeds or applying/separating claims are fabricated.
The policy is independent of the natal wheel's aspect display settings.

## Verification scope

`tests/server/test_server_natal_discovery.py` covers direct request admission,
selected-only chains, cycles and multiple sinks, missing ruler stops, Bucket
metric scope, partial selection, unknown time, source timestamp preservation,
real-kernel Tropical/Sidereal lunar composition and strict preceding selection at
a solved event. These are transport, policy and geometric invariant checks;
they do not independently revalidate the existing substrate against an external
astronomical authority.
