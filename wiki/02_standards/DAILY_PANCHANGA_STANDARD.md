# Daily Panchanga standard — VED-015

**Status:** Implemented and validated locally on 6 October 2026; publication and deployment are separate.
**Owners:** [daily engine](../../moira/daily_panchanga.py), [facade](../../moira/_facade_vedic.py), [REST models](../../moira_server/models/daily_panchanga.py), [service](../../moira_server/services/daily_panchanga.py), [serializer](../../moira_server/serializers/daily_panchanga.py), [router](../../moira_server/routers/panchanga.py).
**Baseline:** engine 6.9.9, parent commit `838756f1916f879c6f0cfe048e11c88a1bcef47c` plus local VED-015 changes.

## Governing object and source review

The product is the half-open interval from the requested local date's sunrise
to the following local date's sunrise, with complete coverage by four angular
limbs and a weekday owned by the opening sunrise.

[IMD/PAC's Rashtriya Panchang explanation](https://packolkata.imd.gov.in/panchang/en/explanation)
defines Tithi and Karana by Moon–Sun elongation spans of 12 and 6 degrees,
Nakshatra by 27 equal nirayana lunar sectors, and Yoga by the nirayana solar
and lunar sum. It gives geocentric limb ending moments and uses an upper-limb
solar convention with 31 arcminutes refraction plus 16 arcminutes radius.
[USNO's definitions](https://aa.usno.navy.mil/faq/RST_defs) instead use a
50-arcminute center depression. These are distinct numerical conventions.

Local corpus evidence was visually inspected with the PDF skill: B. V. Raman,
*A Manual of Hindu Astrology*, section 65, printed page 45 / PDF page 74,
describes the sunrise-to-next-sunrise day. Section 56, printed page 30 / PDF
page 59, discusses a center-disc convention and refraction without supplying
the same fixed threshold as PAC. Section 70, printed page 52 / PDF page 81,
discusses almanac use. These passages support distinguishing conventions; no
Raman numerical sunrise preset is inferred from them.

Local file: `C:\dev\ASTROLOGY-BOOKS-DATABASE\Books by Authors\BV Raman\A Manual of Hindu Astrology by BV Raman.pdf`.
SHA-256: `439f877fd4a52f309f67e9e427a912daff7241cfdfb180605e6e6eba9af5b60a`.
The scan begins with dedication/contents and does not establish an edition date;
the citation is therefore section/page-specific, with edition unresolved.
No book scan or third-party executable formula was copied into the package.

This is an astronomical daily almanac. Festival precedence, lunar months,
regional calendar dates, ritual-day selection, Muhurta judgement and historical
mean-motion/Vakya implementations require separate admissions.

## Public engine and policy

```python
from datetime import date
from moira import Moira, DailyPanchangaPolicy, PanchangaSunriseDefinition

engine = Moira()
day = engine.daily_panchanga(
    date(2026, 9, 22), 23 + 11 / 60, 82.5,
    timezone="UTC+05:30",
    policy=DailyPanchangaPolicy(
        ayanamsa_system="Lahiri",
        sunrise_definition=PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB,
    ),
)
assert day.status == "available"
assert day.at_sunrise.vara_lord == "Mars"
assert day.limbs[0].intervals[0].name == "Ekadashi"
```

The module function is
`daily_panchanga(local_date, latitude, longitude, *, timezone, policy=None, reader=None)`.
The facade binds its own reader. All nine module exports share identity through
`moira`, `moira.facade` and `moira.vedic`. The module function requires an explicit
or already-active reader; it does not acquire/download a kernel or close it.
The server uses its initialized facade, without process reader mutation.

| Policy | Meaning |
| --- | --- |
| `ayanamsa_system` | Existing named Moira systems; enum-style aliases normalize to their canonical name. Default Lahiri. |
| `rashtriya_upper_limb` | Default; fixed geometric solar-center altitude −47/60 degrees. |
| `usno_upper_limb` | Fixed altitude −50/60 degrees. |
| `geometric_center` | Center at zero geometric altitude, refraction excluded. An explicit geometry option, not an inferred Raman tradition. |
| `solver_tolerance_seconds` | Finite numeric value in [0.01, 1], default 0.1; upper bound on each angular root bracket. |

Positions are apparent geocentric ecliptic longitudes of date from Moira's
planetary path. Sidereal conversion uses the existing true mode. Solar events
use the existing topocentric geometric altitude substrate and the selected
fixed threshold. Horizon elevation, weather, terrain and arbitrary custom
thresholds are not inputs. No alternate astronomical reduction is selected
implicitly to match a table.

## Dates, clocks and assembly

The date is Gregorian; the timezone is explicit and is never inferred from
coordinates. `UTC` and `UTC+/-HH:MM` fixed offsets work without an IANA database.
IANA keys such as `Asia/Kolkata` use stdlib `zoneinfo` and require installed
system or `tzdata` zone data. Missing data/key fails explicitly; UTC is never
substituted. The base engine adds no dependency.

Civil midnight bounds convert through `moira.julian.utc_to_ut1`. DST dates can
contain 23 or 25 civil hours. Fold 0 selects a repeated midnight; a nonexistent
midnight starts at its normalized post-gap instant. Wholly skipped dates and
skipped adjacent dates are rejected. Dates must allow adjacent civil bounds
and the 72-hour limb search (currently 0001-01-02 through 9999-12-27); actual
astronomical support still depends on the bound kernel and clock substrate.

All numerical event JDs are **UT1**, explicitly named `jd_ut1`. UTC display
uses Moira's inverse conversion, then applies the selected timezone. Exact
civil anchors retain their original datetimes, avoiding a JD float round trip
landing a few microseconds before midnight. Astronomical root displays retain
their computed instants; no presentation rounding changes boundary ownership.
Pre-1972 civil UTC retains Moira's historical UT1-proxy convention.

Opening-sunrise Vara uses the weekday of the requested local civil date.
`at_sunrise.jd` is UT1. Only this daily snapshot's Vara is replaced; existing
instant and chart/profile products retain their current clock conventions.
The four angular limbs delegate names and instant identity to `panchanga_at`.

## Result contract and boundaries

`DailyPanchangaResult` carries requested date/zone/location, actual policy and
provenance, both civil dates' solar crossings, status/reasons, the opening
sunrise snapshot, and four ordered `PanchangaLimbDay` records.

Each limb interval carries canonical index/number/name, `coverage_start`,
`coverage_end` and **`ending`**. Coverage is clipped to the day. Ending is the
actual next angular boundary, including when it occurs after next sunrise.
The first coverage start is sunrise, not a fabricated limb commencement time.
Entered limbs own exact boundaries; next sunrise belongs to the following day.
Each moment exposes the UT1 JD plus aware UTC/local datetimes.

`index_at_sunrise` and `index_at_next_sunrise` make repetition inspectable.
`repeated_at_next_sunrise` means the same limb spans both sunrises.
`skipped_at_sunrise_indices` names intermediate limbs which occurred between
sunrises but were present at neither endpoint. It applies to each angular
cycle, including the 60 Karana positions; it does not claim ritual festival
classification. Multiple intra-day changes remain separate ordered intervals.

Exactly one sunrise is required on each date. Absent or multiple sunrises
produce `status="unavailable"`, explicit reasons, no snapshot and no fabricated
limb coverage. Solar crossings already found are retained. Sunset absence
does not prevent a sunrise-owned angular day; an empty sunset tuple is explicit.
Resource/coverage errors and numerical search failures propagate, rather than
being mislabeled as polar absence or turned into approximate timings.

The search follows continuous forward angular phase, brackets hourly and
bisects each actual crossing. A step must advance less than half a limb span;
violation fails. A hard 72-hour cap prevents unbounded requests. The entered
side of the bracket owns the returned root. Output vessels guard cycle bounds,
ordered contiguous coverage and repeated/skipped evidence. Per-call caches
and the context-bound reader are discarded/restored when the call ends.

## REST admission

Evaluation: `defer_for_engine_completion` for the old instant-only family;
`admit_now` for the completed local daily composition described here. One
bounded synchronous request computes one civil date; there is no range/batch
or background job contract. Pure read-only computation, typed canonical truth,
no route-owned doctrine, no reader lifecycle mutation.

`POST /v1/panchanga/day`, tag `panchanga`, family `classical-vedic`:

```json
{
  "local_date": "2026-09-22",
  "timezone": "UTC+05:30",
  "latitude": 23.183333333333334,
  "longitude": 82.5,
  "policy": {
    "ayanamsa_system": "Lahiri",
    "sunrise_definition": "rashtriya_upper_limb",
    "solver_tolerance_seconds": 0.1
  }
}
```

Coordinates and tolerance accept finite JSON numbers, including integers,
and reject booleans/numeric strings. Date accepts a calendar-only ISO date,
not a timestamp or epoch number. Latitude/longitude bounds are ±90/±180.
Unknown fields and unsupported policy values fail. Standard HTTP validation
errors retain request IDs; a legitimate unavailable solar day is a typed 200
response. The service calls `Moira.daily_panchanga`; the serializer reads
explicit response-model fields from the canonical dataclasses, preserving
all nested truth, enum values and optional fields.

## Verification receipt

Project runtime: Python 3.14.3, engine 6.9.9; native
`moira/_moira_native.cp314-win_amd64.pyd`; discovered DE441 at
`C:\Users\nilad\.moira\kernels\de441.bsp`, downloads disabled. No native,
planetary reduction, horizon solver, clock, source table, golden/oracle fixture
or website code was changed.

Primary numerical check: PAC 1948 SE, 31 Bhadra / **22 September 2026**, central
station 23°11′ N / 82°30′ E, IST. The dated row is available in
[the Bhadra table](https://packolkata.imd.gov.in/panchang/bn/bhadra) and
[the English landing page](https://packolkata.imd.gov.in/panchang/en).
Seven published minute-resolution timings (two solar crossings and five limb
endings) pass a **60-second** acceptance band; the measured maximum residual
is 33.003 seconds. This is one institutional date comparison, not all-date,
all-ayanamsa or observational sunrise accuracy. The 0.1-second root stopping
tolerance is a computational bound, not a physical accuracy claim.

The dedicated unit slice independently exercises linear and quadratic angular
trajectories, wraps, exact sunrise boundaries, repetition, skipped intermediate
limbs, contiguous coverage, bad inputs, DST/midnight gaps, search-cap failures,
reader restoration and export identity. The real-kernel slice checks boundary
identity on either side of roots, New York DST dates, Auckland local date,
polar summer/winter, geometric-center policy and an all-day Nakshatra. HTTP
checks preserve the complete canonical result for all three sunrise choices,
strict validation, polar unavailability and OpenAPI discovery.

Final commands, from `C:\dev\moira`:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_daily_panchanga.py tests/integration/test_daily_panchanga.py tests/server/test_server_daily_panchanga.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_panchanga.py tests/unit/test_vedic_surface_completeness.py tests/unit/test_vedic_facade.py tests/unit/test_api_surface_adversarial_audit.py tests/server/test_server_panchanga_routes.py tests/server/test_server_panchanga_service.py tests/server/test_server_profile_bundle_routes.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
.\.venv\Scripts\ruff.exe check moira/daily_panchanga.py moira/_facade_vedic.py moira/vedic.py moira/panchanga.py moira_server/models/daily_panchanga.py moira_server/services/daily_panchanga.py moira_server/serializers/daily_panchanga.py moira_server/routers/panchanga.py moira_server/openapi.py moira_server/services/__init__.py moira_server/serializers/__init__.py tests/unit/test_daily_panchanga.py tests/integration/test_daily_panchanga.py tests/server/test_server_daily_panchanga.py tests/unit/test_api_surface_adversarial_audit.py tests/unit/test_vedic_facade.py --no-fix
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
git diff --check
```

- Dedicated slice: **105 passed**, 17.40 seconds, no failures/skips; 24 DE441
  resource receipts ran, with one content probe. 56 unit / 15 integration /
  34 server cases; the resource receipt count is not a unique numerical-case count.
- Neighbor slice: **372 passed**, 149.54 seconds, no failures/skips; 20 DE441
  resource receipts ran. It covers current instant semantics, curated public
  APIs, facade delegation and composed profile transport, not every REST route.
- Both ran deterministic `moira-ci` Hypothesis policy, default network deny,
  marked loopback only, external network disabled, strict known issues (empty).
- Ruff on the listed paths, documentation consistency, generated REST inventory
  check and whitespace check passed. The reference now records **477** registered
  operations (37 GET / 440 POST), including five `panchanga` routes.
- A source-aware Ruff diagnostic comparison through stdin against committed
  `HEAD` showed no newly introduced `(code, message)` findings in the remaining
  touched curation files: root 59 existing findings, facade 5, server models
  curation 1. This is preserved lint debt, not a repository-wide green lint claim.
- The standard's Python example and the JSON service/serializer path were
  executed with the real project runtime and DE441; assertions passed.
- An in-memory canonical-wiki rendering/link preview is checked separately;
  generated `moira.wiki` remains unchanged pending publication.

The first neighbor run exposed an existing test defect: the direct Shadbala
oracle was invoked outside a reader scope. An isolated `git archive HEAD`
baseline (engine and the same test, using the same native extension/runtime and
local kernel) reproduced `MissingKernelError` at the same call. The test now
binds `engine._reader` with `use_reader_override`; Shadbala computation is
unchanged. The final neighbor command above passes without an exclusion.
An initial daily test run also exposed JD-to-datetime midnight display drift;
the exact civil-anchor fix is part of this package, not a clock-substrate change.

Changed paths in this package:

| Paths | Change |
| --- | --- |
| `moira/daily_panchanga.py` | Source-owned daily composition, named policy, guarded typed vessels, bounded angular solver and explicit solar unavailability. |
| `moira/__init__.py`, `moira/facade.py`, `moira/vedic.py` | Nine canonical exports; root/Vedic totals are 1178/441 unique names. |
| `moira/_facade_vedic.py` | Caller-owned reader convenience method and method contract declaration. |
| `moira/panchanga.py` | Header scope clarification; instant calculations unchanged. |
| `moira_server/models/daily_panchanga.py`, `models/__init__.py` | Eight typed transport models and curated bindings. |
| `moira_server/services/daily_panchanga.py`, `services/__init__.py` | Public-facade adapter and curation. |
| `moira_server/serializers/daily_panchanga.py`, `serializers/__init__.py` | Complete canonical result serialization and curation. |
| `moira_server/routers/panchanga.py`, `moira_server/openapi.py` | One daily route and discovery description. |
| Three dedicated daily test files | Analytic, institutional/real-kernel and HTTP/adversarial proof. |
| `tests/unit/test_api_surface_adversarial_audit.py` | Explicit public export/method admission expectations. |
| `tests/unit/test_vedic_facade.py` | Correct reader binding in the existing Shadbala comparison. |
| This standard, `PANCHANGA_BACKEND_STANDARD.md`, `API_REFERENCE.md`, `wiki/Home.md` | Public scope, source, policy and discovery. |
| `wiki/02_services/REST_API_REFERENCE.md` | Daily contract and regenerated registered-route inventory. |
| `docs/architecture/P9-01_PANCHANGA_TRANSPORT_DESIGN.md`, `MOIRA_SERVER_PHASE9_LEDGER.md` | Daily family evaluation/admission and actual transport stance. |
| `wiki/06_roadmap/VEDIC_REMAINING_WORK_REGISTER.md` | Stable VED-015 ID marked locally complete; 21 numbered packages still open. |

The earlier eight-path backlog reconciliation remains preserved. Five historical
roadmap/audit edits were not expanded in this package. Index, commits, remotes,
version, dependencies, generated wiki, other repositories/worktrees and website
remain unchanged. No release, predictive-validity claim, all-tradition Panchanga
certification or broad numerical/native parity claim is made.
