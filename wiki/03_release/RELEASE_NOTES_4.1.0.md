# Moira 4.1.0 — Astrodynes and Native Heliacal Parity

Moira 4.1.0 adds a complete public Church of Light astrodynes system and
admits the corrected native fixed-star heliacal engine. It also includes the
paran performance work completed after 4.0.1.

## Highlights

### Church of Light natal astrodynes

The natal system now exposes source-owned computation for:

- essential dignity and house power;
- aspect and parallel power;
- harmony and discord;
- mutual reception;
- planet, sign, house, and chart aggregation;
- summaries and relationship networks.

The doctrine remains explicit about Church of Light dignities rather than
silently substituting traditional essential-dignity tables. Three captured
Church of Light reports provide the worked-chart validation corpus.

### Progressed astrodynes

The progressed system adds:

- Limiting Date and major/Minor Ephemeris Date derivation;
- progressed M.C. and Ascendant geometry;
- radical, major, minor, and transit terminals;
- fixed carry, aspect power, practical distribution, reenforcement, and total
  influence;
- bounded contact entry, perfection, closest-approach, and exit search;
- explicitly Moira-owned variable-rate numerical integration.

Exact formula results and manual-staged arithmetic remain separate. Six dated
rows and three aggregate statements in the worked source are recorded as
publication inconsistencies; executable results follow the declared formulas
rather than reproducing arithmetic errors.

Public access includes the facade and strict REST/OpenAPI products, including:

- `POST /v1/astrodynes/geometry`
- `POST /v1/astrodynes/chart`
- `POST /v1/astrodynes/progressed/chart`
- `POST /v1/astrodynes/progressed/search`
- `POST /v1/astrodynes/progressed/integrate`

### Native fixed-star heliacal parity

The former native visibility path used a defective five-term nutation
approximation and did not implement the complete Python setting doctrine.
Version 4.1.0 replaces it with the packaged IERS 2000_R06 series and aligns:

- signed stellar elongation;
- apparent solar corrections;
- geometric stellar altitude and twilight roots;
- full apparent sidereal time;
- rising and setting thresholds and metadata;
- custom setting eligibility and disappearance factors;
- bounded Delta-T drift over the search interval.

Python continues to own policy and public result semantics. Native code is the
default fixed-star accelerator, while `use_native_heliacal=False` retains the
visible Python manuscript as an independent differential oracle.

Catalogue searches use a request-scoped nutation cache and an explicit
`native_heliacal_workers` policy, defaulting to eight workers. Local validation
measured a five-star setting search at 0.97 seconds natively versus 5.31 seconds
in Python. A 175-star native search completed in 20.69 seconds; the Python
comparator exceeded 120 seconds.

### Paran performance

Paran computation now avoids repeated nutation, duplicate meridian solves, and
unbounded repeated crossing work. Verified Newton estimates, analytic
rise/set brackets, exact-signal refinement, scan fallback, and request-scoped
crossing reuse preserve the existing event doctrine while materially reducing
field and packet latency.

The native heliacal work also benefits the optional heliacal section of the
Urania Workspace paran packet.

## Compatibility

- Existing natal and progressed astrodynes result vessels remain explicit and
  typed.
- Existing paran event, field, contour, path, and packet contracts are
  unchanged.
- `find_parans()` and `natal_parans()` retain their established meanings.
- Fixed-star heliacal results retain the Python-owned public vessel and policy
  semantics regardless of native availability.
- Planetary, lunar-crescent, acronychal, and other generalized visibility
  products retain their existing implementation and validation status.

## Validation

Validation used the project `.venv` on Python 3.14 with strict known-issue
expiry. Release evidence includes:

- Church of Light natal/progressed formula, worked-report, facade, search,
  integration, REST, and OpenAPI acceptance slices;
- independent Python-versus-native fixed-star heliacal comparison across both
  event kinds, multiple latitudes, custom setting policy, 1900/2024/2100
  epochs, and not-found cases;
- scalar-table and ERFA `nut06a` checks for the shared native IERS series;
- cold initialization, concurrent-reader, adversarial native-runtime, packet,
  server, documentation-consistency, compilation, and build checks.

The wider historical visibility corpus continues to report out-of-scope
Babylonian Venus and Yallop lunar validation failures. Those planet and Moon
branches do not use the admitted fixed-star native search and are not counted
as passing evidence for this release.
