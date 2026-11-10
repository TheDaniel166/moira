# Historical small-body release manifests

These byte-exact manifest archives bind the small-body orbital-element and
node admissions and the November 2026 asteroid coverage rebuild. The
archives contain metadata. Download the BSP shards separately for positions.

Bound by the September 28, 2026 admission:

- `asteroids-2026.09.18.1.json`: SHA-256
  `1956b613f072a0dbd78c45d74552dbadb169fafc64fe4d28f02261752e3b667e`.
- `comets-2026.07.28.1.json`: SHA-256
  `31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1`.

Bound by the October 29, 2026 successor admissions:

- `asteroids-2026.10.10.1.json`: SHA-256
  `3d6ef5dee648dad240ef9db4dfcc460a3ecbf0f1cb4b103d1d99f1056878319d`.
- `comets-2026.10.10.1.json`: SHA-256
  `2c147176c66ea1b3c007bb779357c6afcc23ace6fbe9cc18ce169980b3198671`.

The November 10, 2026 coverage rebuild archives the following manifest.
[Coverage rebuild and Swiss comparison](../../../wiki/03_validation/SMALL_BODY_CATALOG_RELEASE_2026_11_10_2.md)

- `asteroids-2026.11.10.2.json` with SHA-256
  `0021b645f3db6847e1b3d6a120a8eb4a39cf60fb8298e391aef676affdd2ab4b`.

The packaged manifests live under `moira/kernels/asteroids/` and
`moira/kernels/comets/`. A historical oracle receipt must not be relabelled to
admit a different release or a different Horizons target solution. Git keeps
these JSON files LF-normalized so their recorded byte digests survive checkout.
