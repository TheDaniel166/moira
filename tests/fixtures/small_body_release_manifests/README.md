# Historical small-body release manifests

These are byte-exact archives of the manifests bound by the September 28,
2026 orbital-element/node admission receipt. They are not the current packaged
catalog manifests and are not installed ephemeris kernels.

- `asteroids-2026.09.18.1.json`: SHA-256
  `1956b613f072a0dbd78c45d74552dbadb169fafc64fe4d28f02261752e3b667e`.
- `comets-2026.07.28.1.json`: SHA-256
  `31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1`.

The current manifests live under `moira/kernels/asteroids/` and
`moira/kernels/comets/`. A historical oracle receipt must not be relabelled to
admit a different release or a different Horizons target solution. Git keeps
these JSON files LF-normalized so their recorded byte digests survive checkout.
