# Compatibility Notes - Moira 5.2.3

## Public API

Moira 5.2.3 introduces no public Python or REST signature changes. Existing
5.2.2 callers can upgrade without code changes.

## Kernel Discovery

Automatic small-body discovery now requires evidence that a manifest has
installed shard data. Packaged metadata-only manifests are no longer treated as
installed asteroid or comet ephemerides.

Two fail-visible policies are preserved:

1. a manifest named by `MOIRA_SOVEREIGN_SMALL_BODY_MANIFEST` remains an explicit
   operator instruction and is passed to the loader even when its shards are
   missing; and
2. an automatically discovered manifest with any referenced shard present is
   admitted so the loader can reject an incomplete installation.

Applications that intentionally relied on automatic discovery of a manifest
with no installed BSP shards were relying on metadata presence rather than a
usable ephemeris. Configure the manifest explicitly if that diagnostic behavior
is required.

## Data And Numerical Behavior

This patch does not modify:

- planetary, asteroid, or comet calculations;
- asteroid-family metadata;
- manifests or BSP shards;
- kernel coverage;
- public result vessels; or
- correction and frame policy.

## Upgrade

```text
moira-astro==5.2.3
```
