# Physical Heliacal Visibility Phase 4 Jones Source-Audit Checkpoint

Date: 2026-07-31
Status: source audit complete; runtime model not admitted
Candidate identifier:
`jones_paranal_scattered_moonlight_2013_v1`

## Outcome

The Jones et al. scattered-moonlight candidate now has a machine-checkable
source boundary and an independently specified artifact contract. This
checkpoint does not implement, admit, export, or select a new runtime
moonlight model.

The governing evidence is:

- Jones et al., “An advanced scattered moonlight model for Cerro Paranal,”
  A&A 560 (2013) A91,
  [DOI 10.1051/0004-6361/201322433](https://doi.org/10.1051/0004-6361/201322433);
- the official ESO Advanced Cerro Paranal Sky Model SM-01 release 1.0.0,
  inspected as external GPL source and regression evidence; and
- an explicitly versioned ESO SkyCalc 2.0.9 component-only operational
  capture, used as a source-owned comparison rather than an independent
  oracle.

No ESO source or binary data and no SkyCalc FITS file is redistributed in the
repository. The engine has no ESO, SkyCalc, libRadtran, network, or automatic
download dependency from this checkpoint.

## Frozen External Receipts

The official `SM-01.tar.gz` receipt is:

- bytes: `431651392`;
- SHA-256:
  `e09b1d62c8af212486f50097fe76d9dcbb242f4fbadf720a4a85be361cc9116b`;
- license: `GPL-2.0-or-later`; and
- disposition: external lineage inspection and source-owned regression only.

The audit independently locks all 18 required members, including the
scattering and component source, ROLO coefficient data, the default
`mie_m15s1.dat` aerosol phase function selected by `sm_filenames.dat`,
Paranal aerosol and scattering tables, solar and ozone inputs, parameter
files, and both official test FITS products. The complete member receipts are
recorded in
`phase4_jones_source_audit_spec.json` and the generated checkpoint artifact.

## Source-Owned Fixture Classification

The official package fixture is internally consistent and its optical
`flux_sml` component is checksum-locked over 0.36–0.89 micrometres:

- FITS rows: `11001`;
- optical signature rows: `2651`;
- component signature SHA-256:
  `ba33c681486a24b4703120c2dc5ab0cb7df3ed8201b44707629fa88f5a1a0b52`;
- derived lunar phase angle: `102.1` degrees.

Jones reports that the empirical ROLO phase observations cover 1.55–97
degrees, while the paper extends the formulation beyond that range. Because
the official package fixture is at 102.1 degrees, Moira classifies it as
official-implementation lineage evidence, not as an admission golden. The
first candidate domain rejects phase extrapolation instead of silently
inheriting it.

## Operational Comparison Receipt

The in-domain component-only SkyCalc comparison is fixed as:

- SkyCalc version: `2.0.9`;
- site: Cerro Paranal;
- lunar phase angle: `50.0` degrees, waxing;
- target altitude: `60.0` degrees;
- lunar altitude: `45.0` degrees;
- lunar-target separation: `60.0` degrees;
- wavelength grid: 380–780 nm at 1 nm;
- FITS bytes: `80640`;
- FITS SHA-256:
  `12d7625e1ec1afc718928d873fdb0001d3fd800b19d33a6c5dc2ce135dbbc230`;
- isolated `flux_sml` signature SHA-256:
  `8e15e62b5aa5cab32961f3be7ba300f46217d20614e91bdc131aa8ee8b2e1c29`.

All other emitted sky components are zero and the total flux equals
`flux_sml`. This proves the capture identity and component isolation. It does
not make the current SkyCalc service an independent oracle or a runtime
dependency.

## First Candidate Admission Boundary

The frozen first-candidate domain is intentionally narrow:

- Cerro Paranal only; no site transfer;
- lunar phase angle 1.55–97 degrees;
- Moon-Earth distance ratio 0.91–1.08;
- target true altitude 0.25–90 degrees;
- lunar true altitude 0–90 degrees;
- relative lunar azimuth 0–180 degrees;
- 380–780 nm spectral output; and
- waxing and waning retained as distinct states.

Geometry consistency is mandatory. Out-of-domain phase, substituted site, and
subhorizon lunar cases are typed `not_evaluable`; they are not extrapolated or
silently routed to the legacy model. The unchanged
`krisciunas_schaefer_1991` identifier remains the only existing named
moonlight implementation.

## Independent Artifact Gate

Runtime admission still requires a separately generated immutable spectral
artifact. Its contract requires:

- libRadtran 2.0.6 with MYSTIC as an external offline generator;
- all six geometry/phase/distance axes;
- exact site, pressure, molecular, aerosol, ozone, and ground receipts;
- source-locked solar, lunar-albedo, photopic, and scotopic inputs;
- spectral radiance plus photopic and scotopic products;
- numerical, interpolation, and storage error receipts; and
- repeatability, convergence, isolated-component, geometry-holdout,
  operational-comparison, and rejection tests.

Acceptance thresholds remain unset until a pilot artifact measures generator
noise and interpolation error. The ESO implementation is neither the
generator nor the independent oracle.

## Atmospheric Sensitivity Decision

The current runtime visibility pack has fixed atmospheric metadata, not
atmospheric coordinate axes. It therefore cannot truthfully produce an
atmospheric sensitivity envelope.

Future sensitivity requires separate immutable admitted scenario packs. Moira
must rerun the complete event search against every scenario and may form an
interval hull only when every scenario produces a comparable owned event.
Missing or noncomparable scenarios return typed `not_bounded`. Interpolation
between scenario packs and probabilistic-confidence language are prohibited.

## Machine-Checkable Files

- `scripts/visibility_reference_lab/phase4_jones_source_audit_spec.json`
- `scripts/audit_visibility_phase4_jones_source.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_source_audit_checkpoint_2026-07-31.json`
- `tests/unit/test_visibility_phase4_jones_source_audit.py`

With an operator-supplied official archive and the separately retained
comparison FITS file, reproduce the receipt with:

```powershell
.\.venv\Scripts\python.exe scripts\audit_visibility_phase4_jones_source.py `
  C:\path\to\SM-01.tar.gz `
  --skycalc-fits C:\path\to\skycalc-jones-g50-waxing.fits
```

The auditor verifies inputs but never downloads, extracts to disk, compiles,
or executes the external GPL package.

## Gate State

Closed by this checkpoint:

- primary paper and official implementation lineage;
- exact archive and governing-member identities;
- licensing and redistribution boundary;
- source-owned regression classification;
- first candidate domain and fail-closed extrapolation policy;
- independent artifact schema; and
- atmospheric sensitivity architecture.

Still open:

- independent MYSTIC pilot generation;
- measured acceptance-threshold freeze;
- immutable spectral artifact generation;
- independent in-domain geometry holdouts;
- engine implementation and typed component receipt;
- public-surface parity; and
- Phase 4 closure.
