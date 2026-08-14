# Compatibility Notes - Moira 6.2.1

## Upgrade Boundary

Moira 6.2.1 is backward-compatible from 6.2.0, 6.1.1, and 6.1.0.

- Existing 6.2.0 function signatures, REST paths, and response models remain.
- The 10,025-name asteroid registry and external catalog `2026.08.12.1`
  contract are unchanged.
- Planetary reduction, Track A, Track B, and physical visibility are
  unchanged.
- This release adds a packaged 25-body position catalog and install-path
  honesty. No public signatures change.

## Wheel catalog vs full catalog

Identity is still not availability.

| What | 6.2.0 clean pip install | 6.2.1 clean pip install |
|---|---|---|
| Canonical names | 10,025 known | 10,025 known |
| Chiron / 24 named bodies | no segment unless shards installed | positions from wheel catalog |
| Full 10,025 positions | needs `2026.08.12.1` | still needs `2026.08.12.1` |
| `centaurs.bsp` | advertised, not shipped | not advertised |

Applications should still distinguish known identity, loaded availability,
and position capability. Bodies outside the 25 still require the full
archive.

## Installer

`moira-download-kernels` no longer treats `centaurs.bsp` or
`minor_bodies.bsp` as bundled. Generic JPL `asteroids.bsp` and
`sb441-n373s.bsp` remain optional and do not install Chiron.

Missing-segment errors for known asteroid identities now name
`2026.08.12.1` and https://moira-astro.com/ephemerides. Low-level SPK
`KeyError` text for planetary misses is unchanged.

## Recommended Migration Sequence

1. Install `moira-astro==6.2.1` in staging.
2. Keep the existing `2026.08.12.1` asteroid pointer if the host already
   has the full catalog.
3. Confirm `moira-download-kernels --list` shows
   `moira-asteroids-wheel 2026.08.14.1  OK (wheel)`.
4. Compute Chiron with only a planetary kernel present.
5. If the host serves the full catalog, verify a 10,025-only body such as
   `Mani` still resolves from the higher-precedence shards.
6. Promote the exact staged artifact.

No database migration is required. Restart processes that import `moira`
so discovery sees the packaged catalog.

## Upgrade Pin

```text
moira-astro==6.2.1
moira-astro[server]==6.2.1
```

## Rollback

Pin back to `moira-astro==6.2.0` to drop the wheel catalog and restore
the previous installer wording. Full-catalog hosts keep `2026.08.12.1`.
Chiron on a clean pip install without shards will fail again, which is
the 6.2.0 behavior reported in issue #17.
