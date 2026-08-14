# Moira Small-Body Catalog Notice

This distribution contains DAF/SPK Type-13 kernel files generated and written
by Moira. The BSP files are not JPL-supplied kernels.

Moira obtains heliocentric Cartesian state-vector samples from the public JPL
Horizons `VECTORS` service and materializes those samples through Moira's own
Type-13 writer, interpolation layout, shard assembly, metadata, and manifest
pipeline. JPL Horizons remains the trajectory-sample authority. The manifest
records the requested coverage, sampling policy, and any admitted per-body
coverage exceptions.

The accompanying MIT license applies to Moira-authored software and packaging.
The JPL Horizons provenance remains visible and does not imply endorsement by
NASA, JPL, or Caltech.

Every released file is identified in `SHA256SUMS`. Kernel and per-shard
metadata identities are also embedded in `manifest.json`. A release version is
immutable: changed membership, metadata, policy, or file bytes require a new
catalog version and new checksums.

JPL Horizons API documentation:
<https://ssd-api.jpl.nasa.gov/doc/horizons.html>
