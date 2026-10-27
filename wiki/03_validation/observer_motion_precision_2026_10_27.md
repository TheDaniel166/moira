# Observer motion precision repair, 2026-10-27

This receipt concerns two Python observer stages on base commit
`690359d6085e09de89fbbacd7991be121af7a1d9`. It does not establish general
Moira/IOTA or Moira/GRAZPREP equivalence. Scientific validation preceded the
separately authorized source publication recorded below.

## Changed behavior

`moira.corrections._observer_position_icrf` now transposes the admitted polar
motion matrix for the terrestrial station's ITRS-to-TIRS transport. The public
`polar_motion_matrix` remains a CIP/TIRS-to-ITRS matrix, matching ERFA `pom00`.
The station transport follows ERFA `pvtob`, with the same WGS-84 ellipsoid,
GAST in place of ERA for true equator/equinox of date, and zero TIO locator s'.

`moira.occultations._star_topocentric_equatorial` now applies the existing
relativistic diurnal-aberration stage in true equatorial coordinates after
annual aberration and precession/nutation, before deriving RA, declination,
and altitude. This pairs the nominal apparent stellar ray with the Moon's
observer-apparent ray. The angle-only stellar API retains its infinite-distance
convention. The separately defined physical topographic contact rays retain
their no-aberration convention.

The pre-existing ERFA polar-motion test had repeated the incorrect forward
station transform. Its expectation now uses the transpose. Additional tests
compare directly with ERFA `pvtob` and `ab`; the stellar test independently
derives station velocity using ERFA position and Moira's admitted rotation rate.

References:

- [ERFA pom00: matrix direction](https://raw.githubusercontent.com/liberfa/erfa/master/src/pom00.c)
- [ERFA pvtob: station transport and GAST convention](https://raw.githubusercontent.com/liberfa/erfa/master/src/pvtob.c)
- [ERFA ab: relativistic aberration](https://raw.githubusercontent.com/liberfa/erfa/master/src/ab.c)

## Independent controls and focused tests

All executions use `C:\dev\moira\.venv\Scripts\python.exe` (Python 3.14.8).
The verified native binary from the base precision repair is reused unchanged:
SHA-256 `19c07caab59801a339143f3b023a86cb2cb83a9ba57fa054caafc96fad3299d4`.
No native build input changes in this repair. The bias-inclusive FW06
gamma-bar coefficient remains `10.556378`.

- 15 independent station cases: five stations times three zero/nonzero signed
  pole-coordinate pairs. True equator/equinox-of-date components agree with
  ERFA `pvtob` within 1e-11 km (10 nm), using zero s'.
- Four isolated apparent stellar cases agree with ERFA `ab` to 3e-16 per unit
  component. Altitude is checked from the corrected ray. Physical stellar
  coordinates remain unboosted in the same controls.
- The new 19-case regression file gives 14 failures and five passes against
  the unchanged pre-repair source, and 19 passes with the repairs.
- The actual matched-time Spica station discrepancy against ERFA `pvtob`
  falls from 21.3664774809 m to 1.3969838619e-9 m. This is numerical agreement
  for an identical orientation model, not an absolute station-position claim.
- 693 distinct affected offline tests pass; six explicit type-3 policy cases
  are skipped. This combines the main 526-case affected slice, the 141-case
  downstream slice, 14 eclipse visibility/global contract tests, six DE441
  lunar horizon checks, and six candidate-policy/overwrite-guard checks.
- Six selected live IOTA graze-product tests pass. The original tight nominal
  Spica and El Nath tests also pass without changing their respective 0.0015
  and 0.003 degree gates. Alcyone and Merope terrain-acquisition tests still
  fail; identical failures are reproduced against unchanged base source.
- Seven of eight additional live topocentric Horizons checks pass. The Spica
  south Moon row fails the 0.5 arcsec RA gate on both source versions (0.556
  arcsec before, 0.554 after). A scratch adapter preserving fractional request
  seconds reduces the repaired-source residual to 0.194 arcsec, within the
  same gate. The repository timestamp formatter is unchanged; this control
  isolates request precision and does not assert full model identity.
- The same 528-epoch, ten-body DE440s/XALEN/CSPICE comparison retains zero
  Moira component error in all 7,392 raw SPK cases. The largest frame-axis
  discrepancy against ERFA remains 8.0151225914e-11 arcsec.
- Direct-file DE441 exact-rational type-2 arithmetic controls: 42 cases,
  largest component residual 7.4505805969e-9 km. Six matched frame controls
  against ERFA bias-precession, holding nutation fixed, differ by at most
  1.1102230246e-16 per matrix entry. These do not validate the DE441 dynamics.
- Touched engine docstring preflight passes. Ruff reports no new diagnostics;
  three pre-existing diagnostics remain in untouched occultation code.

For four actual graze rows with exactly one UTC-to-UT1 conversion, reader-bound
TT, unchanged refraction and original observer heights, the latitude residuals
are approximately -143.172 m (Spica, -108 degrees), -64.868 m (Spica, -99),
-94.494 m (Spica, -90), and -49.446 m (El Nath, -97), using 111.32 km per degree
only as a reporting conversion. Every angular residual is within its unchanged
test gate. The unpublished IOTA atmosphere/catalogue/ephemeris recipe prevents
an attribution of every remaining metre.

## LOLA candidate review

Full profile/contact generation and review are complete. The admitted
observations and both frozen model sites remain untouched. Candidate generation
uses a separate atomic output tree through
`python -m tests.tools.generate_iota_spica_candidate --output <new-directory>`.
Saved profiles can be restored with `--profiles-from <previous-candidate-tree>`
only when recorded source, observation, model, kernel, and native identities
match. JSON restoration uses the ordinary immutable profile constructors.

The review retains the original 16 pinned terrain assets, finite Hipparcos
Spica target, physical contact convention, search windows, profile policy,
solver policy, required contact topology, and height intervals. The 0.5 s
envelope is a Moira-owned regression gate, not IOTA measurement uncertainty or
an external absolute-accuracy tolerance. Measured geometry, timestamps,
matching diagnostics, and height sensitivities are candidate characterizations.
Candidate generation does not promote or overwrite the original model fixture.

DE441 has 3,307,878,400 bytes and SHA-256
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`.
All 16 frozen terrain assets and both orientation-resource identities remain
admitted against the original bytes and hashes. Each new profile has 16 slices
and 3,488 bins per slice. The new starting/ending position angles are:

| Site | Start, degrees | End, degrees |
| --- | ---: | ---: |
| Dunham1 | 210.79456991435387 | 217.76856991435386 |
| Dunham2 | 210.79449365396474 | 217.76849365396473 |

The original per-site integration assertions pass against the computed
candidates, including all contact residual/bracket contracts, finite-target
identity, physical geometry provenance, asset-set identity, contact topology,
matching uniqueness and assignments, and both height endpoints. Persisted JSON
profiles reproduce the same geometry and timing results. Frozen original model
characterizations are not promoted and remain stale for the repaired source.

| Site | Old maximum timing residual, s | Candidate maximum, s | Old mean absolute, s | Candidate mean absolute, s | Maximum height shift, s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dunham1 | 0.381008 | 0.144276 | 0.137143 | 0.111663 | 0.033313 |
| Dunham2 | 0.337355 | 0.350793 | 0.156497 | 0.153474 | 0.030135 |

Both sites retain ten model contacts. Dunham1 matches all ten observations;
Dunham2 matches all eight observations with the same two leading model-only
contacts retained. The latter pair now lasts 0.0127136707 s, above the unchanged
0.001 s scan feature guarantee. Its duration, descriptive label, and second-best
matching costs are measured candidate characterizations, not new tolerances.
The largest solver clearance is 9.97544e-10 degrees (gate 1e-7 degrees), and
the largest bracket is 0.0000804663 s (gate 0.0001 s). Both height sensitivities
remain below the unchanged 0.04 s allowance.

The reviewed D2 baseline reservation becomes 0.351 s instead of 0.338 s; the
unused reporting/model-drift margin correspondingly becomes 0.1089 s instead
of 0.1219 s. The total remains 0.5 s, the height allowance remains 0.04 s,
and root polishing remains 0.0001 s. D1's allocation is unchanged. The original
fixture metadata assertions pass after this reporting review. No observed
timing, uncertainty, resource identity, solver tolerance, total residual gate,
required count, kind sequence, or observed-to-model assignment changes.

Importantly, 10/10 D1 and 7/8 D2 differences exceed their published observation
uncertainties. D1 contacts are all 0.077--0.144 s late; D2 residuals span about
-0.018--+0.351 s. Observation uncertainties do not include the Moira model's
uncertainty. These candidates pass the declared regression checks but do not
establish absolute agreement at the observations' precision.

Run artifacts are under
`C:\dev\outputs\moira-observer-repair-20261027-bb22f4f1`:
`candidate` contains the full first generation and its stale matching-statistic
failure; `reviewed-candidate` contains the serialized-profile replay with both
per-site contact reviews passing and the old D2 reporting-budget metadata
failure; `final-candidate` contains the reviewed reporting labels/allocation,
with all numerical results preserved and the metadata assertions passing.
Each tree remains separate. The final metadata review records its parent hashes
and scripts; it does not replace or rerun numerical results to improve a score.
The final tree is an unpromoted candidate, not a replacement authority fixture.

## Additional finding outside this repair

The unchanged eclipse helpers `_earth_fixed_lunar_reception_vector` and
`_earth_fixed_solar_shadow` also transpose `pom00` for the opposite,
TIRS-to-ITRF direction. A separate isolated comparison of the lunar helper
with ERFA `c2teqx`, using identical identity PN, 60 degree GAST, and a synthetic
lunar-distance vector, gives zero error with zero polar motion but 753.701 m
and 1,245.711 m with pole-coordinate pairs (0.3, -0.2) and (-0.4, 0.5) arcsec.
These are controlled synthetic vector errors, not measured eclipse-path errors.
Those helpers have not been changed; they need a separate scoped repair.

Subsequent matched-model research compared 20 actual DE441 epochs with identical
UT1/TT, retarded vectors, PN, GAST, pole coordinates, WGS-84 and zero s'. A
process-local corrected-direction control agrees with ERFA; sampled solar
centrelines move about 20--22 m. All 18 sampled LOLA geometries execute without
these eclipse helpers. The eclipse defect is confirmed and remains separate
from the unresolved LOLA timing-residual budget. No eclipse repair is included
in this changeset.

## Source publication boundary

The SPK/FW06 repair was already published as
`690359d6085e09de89fbbacd7991be121af7a1d9`. The observer follow-up is prepared on
`9383587ffca0350dcc6302f139f696119296b5e8`, retaining the intervening Hellenistic
changes. Publication includes only the two observer repairs, their independent
regressions, separate candidate-generation/policy tooling and this receipt.

Publication preflight on that base passes 693 affected offline tests with six
explicit type-3 skips and 42 external cases deselected. Both live nominal
Spica/El Nath tests pass. Touched engine docstrings pass; Ruff has no new
diagnostics, retaining three pre-existing warnings in untouched occultation
code. The combined command uses the repository's importlib test-import mode.

Native build inputs are identical to the verified SPK build; the same rebuilt
extension is used for publication checks. The canonical checkout, its index,
all pending files, nested wiki, and the original observer research checkout are
preserved independently. No original observation/model fixture, candidate
data, numerical gate, binary artifact, eclipse implementation, package release
or scientific-baseline promotion is included.
