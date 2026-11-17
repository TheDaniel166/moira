# Eclipse diagnostic API

The following `/v1` endpoints are opt-in evidence products. Existing eclipse
search, path, footprint, and width-availability response shapes are unchanged.
Epochs named `jd_ut1` are UT1 Julian days, including for ancient dates; they
are not UTC civil timestamps. Numeric brackets describe numerical resolution,
not physical prediction accuracy. The reported ephemeris label for the hybrid
and lunar products applies at the stated reference epoch and does not establish
the identity of every state in a pooled reader.

- `POST /eclipses/solar/central-path-diagnostic` selects the next or previous
  native solar event using `jd_start_ut1` and `backward`, then checks its
  central axis for opposite-sign daylight witnesses. `hybrid` is positive
  evidence; `unresolved` is not proof of a total-only or annular-only path.
  Transition brackets are sampled candidates and `subtype` remains null.
  `max_evaluations` bounds diagnostic evaluations, while the central-axis
  interval solver has its own limit. `instantaneous_type` preserves the
  existing greatest-epoch classification rather than presenting it as a
  path-wide answer. Selection delegates to the same core next/previous solar
  search as the existing API. That search checks the neighboring New Moon when
  its maximum could lie on the requested side of `jd_start_ut1`, including
  the backward 2024-04-08 phase-straddle case. Next and previous are strict
  relative to the represented maximum. Where the required neighboring window
  extends outside available kernel coverage, a coverage error may be returned;
  the bounded search does not certify event discovery over unexamined times.
- `POST /eclipses/lunar/shadow-candidate` inspects a supplied full-moon
  neighborhood under the requested `danjon_angular` or `static_finite_cone`
  model. Margins carry their native units, and the maximum is the model's
  penumbral-overlap maximum, not NASA's greatest-eclipse epoch. A missing
  contact in an incomplete candidate does not certify a phase's absence.
- `POST /eclipses/solar/visibility-site` evaluates one geometric observer
  site. `POST /eclipses/solar/visibility-refinement` runs a bounded local
  numerical search from a supplied seed. A found common-ray witness is
  positive evidence under the stated spherical-limb, native-vector and
  geometric horizon conventions; a failed local search is unresolved.
  Any supplied lunation is caller metadata, not an independently verified
  event identity.
- `POST /eclipses/solar/central-cap-diagnostic` returns a numerical candidate
  for an instantaneous central cone/horizon boundary, or unresolved. Its
  sampled cone and horizon arcs are not a complete swept path or a published
  path-width calculation. The ephemeris filename is descriptive, not a hash.
- `POST /eclipses/solar/swept-interior-witness` checks one site at supplied
  times in a closed UT1 interval. A strict witness establishes interior
  membership of the spatial union over that interval under the stated model.
  No witness leaves the location unresolved; it does not establish boundary
  membership or non-membership.

Each endpoint enforces finite, bounded request parameters. Unsupported or
unresolved geometry retains its own status, while ephemeris coverage and other
provider failures are reported as errors. See the generated OpenAPI schema
for the exact request fields, bounds, and response models.
