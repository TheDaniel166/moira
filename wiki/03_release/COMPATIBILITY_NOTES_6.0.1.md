# Compatibility Notes - Moira 6.0.1

## Upgrade Boundary

Moira 6.0.1 is a backward-compatible patch from 6.0.0. It adds canonical
asteroid identities and provenance without changing public function
signatures, REST request/response models, planetary computation, or kernel
file formats.

## Canonical Name Change

The identity for MPC number 20395 is exposed as `Jacquet` rather than the
numeric placeholder `Asteroid20395`.

| Before | After | NAIF ID |
|---|---|---:|
| `Asteroid20395` | `Jacquet` | 2020395 |

Callers that persisted the placeholder string should migrate it to `Jacquet`
or persist the stable numerical identity `2020395`. The placeholder is not
retained as a second canonical alias because canonical names are unique and
release-derived.

## Identity Is Not Ephemeris Availability

`list_asteroids()` returns 9,974 known canonical names. This does not mean that
every installation has all 399 external BSP shards.

Applications should distinguish:

- **known identity** — present in the bundled canonical registry;
- **loaded availability** — present in the active reader's covered-body set;
- **position capability** — the required nonempty BSP shard is installed and
  the requested time is inside the manifest-declared coverage.

For REST consumers, `GET /v1/asteroids/list` continues to intersect canonical
identities with the loaded small-body reader. An older or partial external
catalog therefore returns only the bodies it actually covers.

## Deployment Guidance

1. Upgrade the engine and optional server environment to
   `moira-astro==6.0.1`.
2. Install or retain the matching external release `2026.07.27.1`.
3. Restart processes that import `moira.asteroids`; the registry is loaded at
   module import time.
4. Verify readiness and the resolved manifest before serving positions.
5. Search representative names such as `Limburgia`, `Jacquet`, and `Mani`.
6. Perform at least one position call through the same service path used by
   the application.

No database migration is required.

## Rollback

The package can be rolled back to `moira-astro==6.0.0` without changing the
external kernel release. On rollback, the extra canonical names are no longer
searchable by name, although the external BSP files remain intact and can
still be addressed where numerical NAIF input is supported.
