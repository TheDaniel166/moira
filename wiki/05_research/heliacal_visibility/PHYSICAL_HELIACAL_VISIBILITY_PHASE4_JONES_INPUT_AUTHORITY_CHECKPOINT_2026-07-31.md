# Physical Heliacal Visibility Phase 4 Jones Input-Authority Checkpoint

Date: 2026-07-31
Status: input-authority gate closed; MYSTIC pilot authorized; runtime model not admitted
Candidate identifier:
`jones_paranal_scattered_moonlight_2013_v1`

## Outcome

The Jones candidate's solar, lunar-reflectance, and aerosol phase-function
inputs now have separate, machine-checkable truth classifications:

- the solar spectrum is independently reconstructable over the first
  candidate's 380-780 nm domain;
- the ROLO lunar-reflectance coefficients are independently reconstructable
  inside the 1.55-97 degree empirical phase domain; and
- ESO's selected `mie_m15s1.dat` aerosol phase function is an exact,
  checksum-locked source-owned input, but its transformation from the
  published particle parameters is not reconstructable from the identified
  public sources.

That final result is not hidden or treated as a model failure. The exact
external ESO aerosol table may govern an offline independent
radiative-transfer pilot, with its receipt and source-owned role visible. The
pilot may claim independent radiative transfer, not independent aerosol
microphysics. No runtime model, API, data pack, dependency, network path, or
legacy behavior is admitted by this checkpoint.

## Solar Irradiance Authority

The official ESO `solspec_ext.dat` member is locked at:

- bytes: `141021`;
- SHA-256:
  `0f75353a72cfd7f1b314652f47aa9edff33434be5154bdfd590e2b5b2926933d`;
- rows: `1741`; and
- wavelength domain: 0.1195-30 micrometres.

Its first 1,467 rows were independently replayed against STScI CALSPEC
`sun_reference_stis_002.fits`, using the explicit conversions from angstroms
and `erg s-1 cm-2 angstrom-1` to micrometres and
`W m-2 micrometre-1`. The complete comparison produced:

- maximum wavelength delta: `5.48828125002121e-06` micrometres;
- maximum absolute flux delta:
  `0.0004998779297125111 W m-2 micrometre-1`; and
- maximum relative flux delta: `4.4698819115193814e-06`.

The 325 ESO samples inside the candidate response domain span
0.38061-0.77921 micrometres and have numeric signature SHA-256
`fcdb33a16166f8ee3e9f894371f3d79e14efddb063753104d547897071be9024`.
The NMSU Colina/Bohlin/Castelli reference is retained as a separate
bibliographic and low-wavelength crosscheck; it is not misrepresented as a
complete replacement for the STIS file because its public text contains a
blank flux interval.

The external STIS and NMSU bytes are not committed to the repository.

## Lunar Reflectance Authority

Kieffer and Stone's published ROLO coefficient table is independently bound
to the ESO `moonalbedo.dat` member:

- member bytes: `3365`;
- member SHA-256:
  `86b9f9860fabb283de6659aabee8959186dc03e9d081aaa7c2761c2869ff16cc`;
- four constant coefficients, numeric SHA-256:
  `6eb466a6c1d8fb4bca3f0dda99c4865a58a5c54e0c25fb782fc8358a2fe54e65`;
- 32 wavelength rows from 350.0 to 2383.6 nm; and
- Table 4 numeric SHA-256:
  `620b1ca086edda0221a1db7461d69602479c5c584aa403843084786b5608278e`.

The first candidate does not add the omitted libration terms. The paper's
1.55-97 degree empirical phase domain remains a hard boundary; cases outside
it are typed `not_evaluable` instead of extrapolated.

## Aerosol Reconstruction Falsification

The selected ESO phase table is locked at:

- bytes: `78231`;
- SHA-256:
  `dba01f9b49ddf9a547bccc7eaca013bec1e4b1d8e081ec5ec4dd284ea7ec425e`;
- 40 wavelengths from 0.3 to 30 micrometres; and
- 181 scattering angles from 0 to 180 degrees at 1-degree spacing.

At 0.55 micrometres, direct integration of the table gives a half-solid-angle
normalization of `1.0010108296057996` and an asymmetry parameter of
`0.680602583549528`.

The Jones 2013 nucleation, accumulation, coarse, and stratospheric particle
parameters were replayed with the identified Oxford Earth Observation Data
Group log-normal Mie implementation. The Oxford archive is locked at:

- bytes: `24542`; and
- SHA-256:
  `a026c570b2d39988e597fb7ce5b7bc3e451f650a8d6013670e68af5343cf9561`.

That replay produced an asymmetry parameter of `0.595268389115`, along with a
large systematic phase-function mismatch; for example, its zero-degree value
was about `103.904` versus ESO's `27.53286`. The mismatch survives the
identified integration bounds, trapezoidal quadrature, and documented
log-normal parameter semantics. The public paper, official package, and
identified Mie source do not disclose the extra `m15s1` transformation or
smoothing needed to reproduce the table.

Moira therefore records
`source_owned_checksum_locked_not_reconstructable`. It does not invent a
smoothing law, substitute the independently calculated curve for ESO's
selected table, or claim the source-owned table is an independent oracle.

## Pilot and Distribution Boundary

The next gate may use `mie_m15s1.dat` only as an explicit operator-supplied
external input to a separately receipted libRadtran 2.0.6 MYSTIC pilot. The
ESO source and data bytes remain outside the repository. Whether a generated
artifact based on that input may be distributed requires a separate release
disposition before packaging; this checkpoint makes no legal conclusion.

Acceptance thresholds remain unset until the pilot measures repeatability,
Monte Carlo convergence, and interpolation behavior. Production admission,
engine implementation, and public-surface work remain closed.

## Machine-Checkable Files

- `scripts/visibility_reference_lab/phase4_jones_input_authority_spec.json`
- `scripts/audit_visibility_phase4_jones_inputs.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_input_authority_checkpoint_2026-07-31.json`
- `tests/unit/test_visibility_phase4_jones_input_authority.py`

Reproduce the checkpoint with explicitly supplied external files:

```powershell
.\.venv\Scripts\python.exe scripts\audit_visibility_phase4_jones_inputs.py `
  C:\path\to\SM-01.tar.gz `
  --stis-solar C:\path\to\sun_reference_stis_002.fits `
  --nmsu-solar C:\path\to\solarspectra.txt `
  --eodg-archive C:\path\to\eodg_mie.tar.gz
```

The auditor reads and hashes the supplied files in place. It never downloads,
extracts to disk, compiles, executes, or redistributes them.

## Gate State

Closed by this checkpoint:

- independent solar-spectrum identity inside the candidate domain;
- primary-table ROLO coefficient identity and phase limit;
- exact ESO aerosol-table structure and numeric invariants;
- falsification of the claimed public aerosol reconstruction path;
- source-owned versus independent truth labels; and
- permission to proceed with a bounded external-input MYSTIC pilot.

Still open:

- frozen pilot geometry matrix and generation receipt;
- pilot execution, convergence, and repeatability;
- measured numerical and interpolation threshold freeze;
- independently generated immutable spectral artifact;
- independent in-domain geometry holdouts;
- release/distribution disposition for any derived artifact;
- engine implementation and typed component receipt;
- public-surface parity; and
- Phase 4 closure.
