# Moira 6.1.1 - 10,025-Body Asteroid Identity Catalog

**Release date:** 2026-08-13

**Public upgrade path:** 6.1.0 to 6.1.1

Moira 6.1.1 makes every body in the finalized `2026.08.12.1` asteroid
ephemeris release addressable by its released canonical name. The bundled
name-to-NAIF registry grows from 9,974 to 10,025 unique identities, matching
the 401-shard external ephemeris already published at
[moira-astro.com/ephemerides](https://moira-astro.com/ephemerides).

This is an identity, provenance, and discoverability patch. It does not
change planetary reduction, frame policy, REST schemas, or astrological
interpretation. It does not include later unreleased work on `main`.

## Complete Canonical Identity Coverage

`ASTEROID_NAIF` and its reverse lookup include all 10,025 bodies admitted by
the finalized release. This makes the complete installed catalog available to:

- `asteroid_at(...)` name resolution;
- `list_asteroids()` and related Python introspection;
- `GET /v1/asteroids/list?q=...` name and NAIF search; and
- downstream catalog consumers such as Urania Workspace.

Representative newly reachable identities include:

| Canonical name | MPC number | NAIF ID | Shard |
|---|---:|---:|---|
| `'Aylo'chaxnim` | 594913 | 2594913 | AST-399 |
| `Ka\`epaoka\`awela` | 514107 | 2514107 | AST-399 |

Shards 000 through 397 are reused byte-for-byte from `2026.07.27.1`. Shard
398 is rebuilt; shards 399 and 400 are new.

## Release-Bound Provenance

`moira/data/asteroid_catalog_naif.metadata.json` records the governing
release, source revision, identity policy, counts, and exact input/output
hashes.

## Exact Identity Receipts

| Artifact | SHA-256 |
|---|---|
| External release manifest `2026.08.12.1` | `c151348a9edd3620716da8849ceb239d0ab39688ead948ffecb592c13e068c64` |
| Admitted target ledger | `08927dcb994388902bea186c70d286d7e85334f863309123b194aafc8915ad91` |
| Unified build ledger | `72c0dd9a07ba2b2af610f8755b785d2f473a550b62d77aeaf4d45ac2d3ae185d` |
| Canonical name-to-NAIF registry | `1630b618b46706fa6a40011c6ef80c000e9fbe77d04204e1c7bc446af562d4d4` |

## Position-Capability Boundary

The Python wheel contains canonical identities, not the 401 BSP shards.
Calling a name successfully still requires a loaded external release whose
manifest covers that NAIF ID and whose corresponding shard is present and
nonempty.

Therefore:

- 10,025 names are known to Moira 6.1.1;
- a matching complete `2026.08.12.1` installation makes all 10,025
  position-capable within each body's manifest-declared coverage; and
- a missing, partial, or older external installation remains visible through
  readiness and loaded-kernel availability rather than being silently treated
  as complete.

Hosted production must point
`/srv/moira-data/kernels/asteroids` at
`asteroid-catalog-releases/2026.08.12.1` before or with the package upgrade.

## Install

```text
moira-astro==6.1.1
moira-astro[server]==6.1.1
```

Read `COMPATIBILITY_NOTES_6.1.1.md` before switching the external catalog
pointer.
