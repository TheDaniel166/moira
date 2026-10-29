# Historical small-body release manifests

These are byte-exact archives of the manifests bound by the small-body
orbital-element/node admission receipts in `tests/artifacts/oracle/`. They are
not installed ephemeris kernels, and the older ones are not the current
packaged catalog manifests.

Bound by the September 28, 2026 admission:

- `asteroids-2026.09.18.1.json`: SHA-256
  `1956b613f072a0dbd78c45d74552dbadb169fafc64fe4d28f02261752e3b667e`.
- `comets-2026.07.28.1.json`: SHA-256
  `31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1`.

Bound by the October 29, 2026 successor admission (asteroids only):

- `asteroids-2026.10.10.1.json`: SHA-256
  `3d6ef5dee648dad240ef9db4dfcc460a3ecbf0f1cb4b103d1d99f1056878319d`.

The current manifests live under `moira/kernels/asteroids/` and
`moira/kernels/comets/`. A historical oracle receipt must not be relabelled to
admit a different release or a different Horizons target solution. Git keeps
these JSON files LF-normalized so their recorded byte digests survive checkout.
