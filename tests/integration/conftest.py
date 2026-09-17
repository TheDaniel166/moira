"""Integration-only resource fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def receipted_small_body_reader_pool(
    small_body_reader_pool,
    planetary_kernel_path,
):
    """Open the admitted resources through the production receipt loader.

    ``small_body_reader_pool`` first applies the repository's governed release
    admission checks.  This second pool deliberately exercises
    ``small_body_readers_from_manifest`` so strict orbital integration tests
    see the same catalog-bound source identities as production callers.
    """

    from moira._kernel_paths import find_all_small_body_manifests
    from moira._spk_body_kernel import small_body_readers_from_manifest
    from moira.spk_reader import KernelPool, SpkReader

    _ = small_body_reader_pool
    readers = []
    pool = None
    try:
        readers.append(SpkReader(planetary_kernel_path))
        for manifest_path in find_all_small_body_manifests():
            readers.extend(small_body_readers_from_manifest(manifest_path))
        if len(readers) == 1:
            pytest.skip("no admitted sovereign small-body release is installed")
        pool = KernelPool(tuple(readers))
        yield pool
    finally:
        if pool is not None:
            pool.close()
        else:
            for reader in reversed(readers):
                reader.close()
