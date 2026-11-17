# Eclipse clock interval contracts

These private enclosures prepare clock inputs for later event-search work. They
are conditional bounds on represented outputs of the existing implementations;
they do not certify Earth rotation, ephemeris accuracy, or a complete eclipse
search. None attests source, native binaries, or floating-point environment.
Inputs and outputs use exact rational offsets from a represented JD anchor.

The NASA lunar catalog clock uses proleptic-Gregorian month midpoints and
includes every possible month across each input. Its forward and inverse bounds
cover successful values only. Monthly jumps can produce inverse gaps or
ambiguities; neither inverse success nor uniqueness is promised. Its cached
global inverse hull requires source and arithmetic stability from construction
through every use. Its finite calendar domain is separate from native clocks.
For forward conversion only, `require_totality=True` separately proves that
every represented input within the admitted calendar interval returns a
finite value, conditional on unchanged calendar, NASA-clock source, selected
backend and arithmetic. The proof enumerates every possible month and checks
its represented Delta-T value, including month, year and polynomial boundaries.
It neither authenticates those premises nor supplies an inverse, native-reader
clock, physical Delta-T or eclipse-search completeness claim. The independent
output enclosure continues to describe successful outputs.

The native forward provider bounds direct SPK-reader clock evaluations in
supported ancient polynomial, polynomial-to-HPIERS bridge, HPIERS table,
direct-EOP, outer EOP taper, and future-scenario branches. It hulls both sides
of the ancient/HPIERS seam. Annual and HPIERS-to-annual branches are supported
when the EOP dataset is empty. Internal EOP gaps support HPIERS, annual and future base products with
individually bounded source-owned endpoint tidal terms, including mixed
HPIERS/neutral endpoints. It composes the first
and last EOP knots and eligible gap boundaries using adjacent binary64 cuts;
unsupported base-model transitions fail closed. The provider records
branch choices and rejection reasons and is not wired into a complete search.

The native calendar enumerator admits a finite year range -15000 through 15000,
with day-neighbor guards and unchanged calendar and rounding assumptions. The
real DE441 UT controls at JD -1200954.75 and 6104045.25 are covered. Table and
EOP digests are snapshots, and the reader's kernel identity is an open-time
observation; these do not attest live files or physical model accuracy. The
source premise includes leap-second/TAI data, aggregate values, the reader's
identity, and all invoked Python and native dependencies. The future scenario
is declared through 2150; later values are deterministic extrapolations, not
validated Earth-rotation predictions.

Native TT-to-UT1 enclosures cover direct EOP, ancient polynomial and bridge,
pre-EOP HPIERS and its taper, and the post-EOP taper and future scenario. In
the model branches, the raw-year seed and all eight generic inverse passes are
enclosed before all twelve reader-bound updates. Direct EOP uses the source's
EOP inverse seed. All possible early-stop iterates remain in the hull, which
does not establish existence or uniqueness. The inverse dispatcher composes
outer EOP and eligible neutral-gap seed seams, splitting intermediate UT ranges
at their source knots.
The ancient-to-HPIERS inverse seam is covered by hulling both source branches.
The inverse also composes internal gaps with supported HPIERS, annual or
future base products, including mixed endpoint tidal bases. Base intervals
that cross an unsupported model transition remain unavailable. The
scalar inverse accepts a recovered-TT residual of four floating-point ULPs;
that residual alone does not bound its input, source changes, or iterations.

For a fully covered direct-EOP interval, callers can request a separate
conditional forward-totality proof from `bound_native_ut1_to_tt` with
`require_totality=True`. The provider verifies the UT1 domain and the
positive-span, half-open EOP cover, including neighboring row candidates
used by the production lookup. Direct EOP is basis-neutral, so the serving
UT1-to-TT path does not need an ephemeris-identity conversion on that branch.
This conclusion assumes the listed code, EOP and leap-second data and normal
binary64 arithmetic remain stable; the receipt does not attest them. Missing
rows, changed guarded dependencies, other clock branches and unsupported
seams are rejected. Default callers still receive successful-output-only
bounds; neither mode certifies physical Delta-T or later ephemeris evaluation.

The native phase gate uses the reader-bound clock even in a NASA catalog mode.
The catalog clock bounds must not be substituted for native clock bounds there.

The split TT-to-TDB successful-output envelope allows at most 0.02 seconds
of displacement under its explicit arithmetic and guarded-sine premises. A
separate opt-in checker can prove that its residual threshold is reached in
the existing iteration limit for some intervals. Its proof additionally
assumes finite, in-range libm sine within one ulp, exact IEEE remainder, and a
single remainder quotient across the requested interval. It bounds the
rounded periodic evaluation error and iterates a contraction-based bound on
successive correction differences; intervals with an insufficient error
budget or a remainder seam remain unresolved. These are conditional premises,
not runtime attestation, physical accuracy, or UT1 coverage. The checker is
not yet wired into an eclipse search. It can cover a Cartesian box of
represented first and second TT parts, retaining both the first-part offsets
and their combined offset in its receipt. Each original part must stay within
the converter domain, and the exact combined interval must stay at least
`2**-40` day inside each domain boundary to allow for normalization rounding.
The iteration proof bounds each intermediate correction directly using the
guarded sine and normalization premises; it does not infer convergence from
the successful-output-only envelope. A proved clock result alone does not
establish the success of any SPK route or a complete eclipse search.

The lunar route-obligation receipt can use that checker across a bounded TT
reception interval. It checks the reception clock and each of the ten possible
Sun-emission clocks using independent first-part and negative-delay intervals;
it also checks the corresponding light-time norm guards against the route's
bounded vectors. These remain conditional obligations. A receipt is unresolved
even if every clock and norm check succeeds, because the live route, kernel,
native build and arithmetic environment are not attested, and UT1 conversion
and eclipse-search completeness are outside its scope.

An optional copied-record check uses the same internally generated vector
bounds for all clock and norm obligations, freezes their fourteen native
record operations, and bounds the finite-cone geometry on those vectors. It
also checks that the light-speed constants used by the enclosure and the
light-time routine agree, and that cone radii agree with the model's defaults.
When every obligation succeeds it reports conditional numeric totality for
represented TT inputs on that copied-record route under the documented source,
rounding, libm, floating-point environment and resource assumptions. It does
not certify the live-mapped reader, a continuous interval, UT1, the physical
model, an eclipse classification or absence. The returned Python receipts
are replaceable data, not authenticated certificates; consumers must not
accept a caller-supplied receipt as proof.

The optional exhaustive-clock budget is shared across the reception and ten
possible emission inputs. Identical input boxes are cached within one call;
every enumerated normalized binary64 state is charged once. A zero budget is
the default. Insufficient budget, source changes, ambiguous normalization or
unsupported coverage remain unresolved. This enumeration concerns only the
represented inputs and the documented same-thread, unchanged-source and
floating-point assumptions; it is not a continuous-time or live-route proof.

### Historical diagnostic cost sample

On 2026-11-17 UTC, one warm-environment run of the opt-in finite-cone TT
interval API used DE441 (reader-open SHA-256
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`)
and the isolated checkout's native binary (SHA-256
`14312ce7e37fe89eea4947be9a0ba974b2cdea49abc9e74c78eb887c75f4f6dd`).
Python was 3.14.8 on Windows. Selected Python/native source files were
fingerprinted immediately before and after the call: both fingerprints were
`c866a44d05f6974295faceeb6a27036a7c7098b0b08009ec79fe53daa4350c72`
across 504 selected Python/C/C++ source and build files. This fingerprint
does not cover all build inputs or attest the running binary or mapped kernel.

For the single represented TT instant `1248813.457560655`, Earth-radius scale
`1.01`, and a budget of 3,000,000 states, the call took 7.947 seconds after
reader initialization. It checked 1,883,904 states with seven cache hits,
14 bounded routes, 11 clock checks and 11 norm checks. The frozen-record
finite-cone result was `conditionally_excluded`, with penumbral margin enclosed
by `[-0.6472012988974711, -0.6153957002838979]` km. This model is distinct
from the native angular 13.9-second grazing control at that era: the result
does **not** deny that event, establish continuous-time absence, or certify an
external catalog. A repeat using the repository script returned the same
numerical result and state counts in 12.096 seconds under concurrent test load.
These two elapsed-time samples are not a throughput benchmark.

The repository script `scripts/eclipse_catalog/stage2_historical_clock_probe.py`
records the same probe, checks the selected source fingerprint before and after,
and exclusively creates its optional JSON output. From the isolated checkout,
with the pinned DE441 installed and `MOIRA_NO_DOWNLOAD=1`, run
`.\.venv\Scripts\python.exe -B scripts\eclipse_catalog\stage2_historical_clock_probe.py --output <new-receipt.json>`.
The underlying calculation can also be invoked with the project's Python:

```python
from types import SimpleNamespace
from moira._kernel_paths import find_planetary_kernel
from moira.lunar_shadow_events import inspect_lunar_shadow_tt_interval
from moira.spk_reader import SpkReader

reader = SpkReader(find_planetary_kernel())
tt = 1248813.457560655
result = inspect_lunar_shadow_tt_interval(
    SimpleNamespace(_reader=reader), tt, tt, earth_radius_scale=1.01,
    max_exhaustive_clock_states=3_000_000,
)
print(result.status, result.penumbral_margin_lower_km, result.penumbral_margin_upper_km)
print(result.exhaustive_clock_states_checked, result.exhaustive_clock_cache_hits)
```
