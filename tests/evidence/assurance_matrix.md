# Moira test assurance matrix

This is a generated review surface. It gates declared evidence cells and exact coverage contexts; it does not treat line or branch coverage percentage as scientific proof.

| Cell | Product surface | Evidence | Claim | Expected items | Targets |
|---|---|---|---|---:|---|
| dorothean-triplicity-authority | Dorothean triplicity assignment doctrine | authority | MOIRA-DOROTHEAN-TRIPLICITY-PINGREE1976-V1 | 1 | moira/triplicity.py::triplicity_assignment_for (run) |
| house-coordinate-roundtrip-invariant | house projection equatorial/ecliptic direction helpers | invariant | MOIRA-HOUSE-EQUATORIAL-ECLIPTIC-ROUNDTRIP-V1 | 15 | moira/houses.py::_equatorial_ecliptic_direction (run)<br>moira/houses.py::_ecliptic_longitude_from_equatorial_vector (run) |
| hybrid-ut1-tt-inverse-invariant | public default hybrid UT1/TT clock transforms | invariant | MOIRA-TIMESCALE-HYBRID-UT1-TT-INVERSE-V1 | 8 | moira/julian.py::ut_to_tt (run)<br>moira/julian.py::tt_to_ut (run) |
| longitude-quotient-invariant | public longitude normalization quotient representative | invariant | MOIRA-COORD-LONGITUDE-QUOTIENT-V1 | 3 | moira/coordinates.py::normalize_degrees (run) |
| nutation-2000a-native-parity | packaged nutation scalar-series Python/native boundary | native_parity | MOIRA-NUTATION-2000A-PY-NATIVE-PARITY-V1 | 4 | moira/nutation_2000a.py::_nutation_python (run)<br>moira/nutation_2000a.py::nutation_2000a (run) |
| public-coordinate-sphere-inverse-invariant | public ecliptic/equatorial spherical coordinate transforms | invariant | MOIRA-COORD-ECLIPTIC-EQUATORIAL-SPHERE-INVERSE-V1 | 3 | moira/coordinates.py::ecliptic_to_equatorial (run)<br>moira/coordinates.py::equatorial_to_ecliptic (run) |
| spk-content-identity-invariant | SpkReader content-derived ephemeris identity | invariant | MOIRA-SPK-CONTENT-IDENTITY-V1 | 4 | moira/spk_reader.py::SpkReader.__init__ (run)<br>moira/spk_reader.py::_ephemeris_kernel_identity_from_catalog (run) |

## Claim boundaries

### dorothean-triplicity-authority

Proves:

- all twelve signs expose the source-owned element, day ruler, night ruler, and participating ruler
- sect selects the named day or night ruler for every admitted sign

Does not prove:

- translation authenticity, manuscript consensus, or superiority over another historical lineage
- birth-chart sect determination, dignity scoring, interpretation, or any other Hellenistic doctrine
- the correctness of source tables not named by this claim

### house-coordinate-roundtrip-invariant

Proves:

- the two named house-geometry helpers are inverse within the declared circular tolerance for the admitted longitude/obliquity grid
- recovered longitude remains in the canonical [0, 360) degree range

Does not prove:

- the public moira.coordinates API or latitude-bearing three-dimensional transforms
- the astronomical truth of any obliquity model, epoch, house cusp, or frame realization
- conditioning outside the five longitudes and three obliquities in the admitted grid

### hybrid-ut1-tt-inverse-invariant

Proves:

- default hybrid UT1 to TT to UT1 closes within two maximum binary64 coordinate ULPs over the admitted proleptic-year interval
- omitted and explicit DeltaTPolicy(model='hybrid') spellings are bit-identical in both directions
- the exact and nextafter calendar-policy boundary atlas retains the same inverse and default-equivalence properties
- both public clock transforms reject nonfinite and grossly unrepresentable JD coordinates with ValueError
- a finite one-second post-observation bias is rejected by the exact production predicate

Does not prove:

- historical or future Delta-T accuracy, EOP authenticity, or agreement with an external time authority
- calendar/JD conversion bijection or calendar input-refusal semantics
- NASA-canon, fixed, or physical Delta-T policy behavior
- sub-ULP preservation near JD zero or correctness outside proleptic years -1000 through 5000

### longitude-quotient-invariant

Proves:

- normalization returns a finite representative in [0, 360) and is idempotent over the admitted domain
- adding an admitted integer multiple of 360 degrees preserves the represented longitude within the declared circular bound
- a normalized zero owns the positive IEEE-754 zero sign
- a finite zero-to-360 post-observation mutation is rejected by the exact half-open predicate

Does not prove:

- accuracy of any coordinate transform or astronomical longitude
- bit-identical periodicity after arbitrary unbounded floating-point additions
- public rejection semantics for NaN, infinity, or non-real arguments

### nutation-2000a-native-parity

Proves:

- native and governing Python series evaluations agree for delta psi and delta epsilon at four admitted TT epochs
- the admitted parser output contains exactly 1,358 luni-solar terms and 1,056 planetary terms, every term has 16 fields, and the j=0 partitions end at 1,320 and 1,037 respectively
- both evaluations consume those same admitted parsed sequences

Does not prove:

- IERS coefficient authenticity, completeness against the published tables, or ERFA/SOFA authority agreement
- the parser's acceptance or rejection semantics, row-to-source transcription fidelity, or authenticity of the packaged files
- accuracy outside the four epochs or universal Python/native parity
- precession, Earth-orientation, frame, or downstream apparent-position correctness

### public-coordinate-sphere-inverse-invariant

Proves:

- both public transform directions close on the same unit-sphere direction over the admitted interior property domain
- the explicit seam and polar atlas closes under the separately declared conditioning tolerance
- returned right ascensions and longitudes are finite canonical representatives and returned latitudes remain finite spherical coordinates
- a finite one-degree post-observation latitude bias is rejected by the exact production predicate

Does not prove:

- external frame authority, epoch-dependent obliquity accuracy, or any astronomical body position
- correctness of a coordinated but mutually inverse wrong rotation
- the equatorial/horizontal transforms, whose current inverse has a separately recorded counterexample
- public rejection semantics for nonfinite or out-of-domain arguments

### spk-content-identity-invariant

Proves:

- recognized coherent DE/LE summary labels determine the published identity rather than the filename
- the resulting identity vessel is immutable
- mixed recognized identities fail closed and release the opened kernel

Does not prove:

- real BSP byte parsing or file authenticity
- JPL trajectory accuracy, segment coverage, frame correctness, or native support
- identity semantics for unexamined summary-label families
