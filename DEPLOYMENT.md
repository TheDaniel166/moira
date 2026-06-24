# Deployment — production environment

Two engine services run on the production box (loopback only), each a separate
process with its own systemd `EnvironmentFile`:

| service | port | EnvironmentFile | ephemeris |
|---|---|---|---|
| `moira-engine` | 127.0.0.1:8765 | `/etc/moira/moira-engine.env` | **DE440** (consumer website) |
| `moira-api` (Urania Workspace) | 127.0.0.1:8745 | `/etc/moira/moira-api.env` | **DE441** (full span) |

These env files live on the box and persist across engine package rebuilds (a
`pip`/`.so` rebuild replaces the package, not `/etc/moira/*.env`). They DO need to
be recreated on a fresh box / re-provision — hence this reference.

## Required env vars

`/etc/moira/moira-engine.env` (consumer site → DE440):

    MOIRA_KERNELS_DIR=/srv/moira-data/kernels
    MOIRA_KERNEL_PATH=/srv/moira-data/kernels/de440.bsp
    MOIRA_NATIVE_SEGMENT_CACHE_MAX=256
    # (plus DATABASE_URL and the other existing secrets)

`/etc/moira/moira-api.env` (Workspace → DE441, exclusively):

    MOIRA_KERNELS_DIR=/srv/moira-data/kernels
    MOIRA_KERNEL_PATH=/srv/moira-data/kernels/de441.bsp
    # (plus DATABASE_URL and the other existing secrets)

## Kernels

Both live in `/srv/moira-data/kernels/`:

- `de441.bsp` (~3.3 GB) — Workspace, full 13201 BCE–17191 CE range
- `de440.bsp` (~114 MB) — consumer site, 1550–2650 CE

## Why these matter

- **`MOIRA_NATIVE_SEGMENT_CACHE_MAX`** bounds the native SPK segment LRU (added in
  "Bound native SPK segment cache"). Unbounded, it grew to ~4.8 GB RSS; but the
  **default of 16 is below the per-date-era working set (~12–15 segments)** and
  thrashes — each cold segment load is ~1.1s, so time-search endpoints (next-ingress,
  void-of-course, lunar-phases, eclipses) hang for 20–70s and pile up. **Keep it ≥ 256.**
- **DE440 vs DE441** are the same JPL solution for 1550–2650 CE (identical to
  ~0.0002 arcsec for any real chart), but DE440 is ~114 MB vs DE441's ~3.3 GB. So the
  high-traffic consumer engine runs DE440 (~240 MB RSS) while the Workspace keeps the
  full-span DE441 (~1.66 GB RSS, loaded on demand). Set per-service via the explicit
  `MOIRA_KERNEL_PATH` above (the default planetary-kernel scan would otherwise pick
  DE441 for both, since DE441 precedes DE440 in the search order).
