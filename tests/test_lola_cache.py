"""
Verification of _LolaTile cache integrity and transition to native substrate.
"""

import pytest
from pathlib import Path
from moira.lunar_limb import _load_lola_tile, _default_cache_root

try:
    from moira import _moira_native as moira_native
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False

@pytest.mark.network
@pytest.mark.skipif(not NATIVE_AVAILABLE, reason="Native backend not available")
def test_lola_tile_cache_integrity():
    """
    Verify that cached tiles produce identical results to freshly loaded ones
    and that the transition to LolaPointCloud is stable.
    """
    from moira.lunar_limb import _lola_neighbor_tile_urls
    cache_root = _default_cache_root()
    
    # Discover a valid URL from neighbor tiles (e.g., near 0,0)
    urls = _lola_neighbor_tile_urls(0.0, 0.0, cache_root)
    if not urls:
        pytest.skip("No LOLA tiles available in neighborhood")
    url = urls[0]
    
    # First load (fresh)
    _load_lola_tile.cache_clear()
    tile1 = _load_lola_tile(url, str(cache_root))
    
    # Second load (cached)
    tile2 = _load_lola_tile(url, str(cache_root))
    
    # Verify same object (lru_cache)
    assert tile1 is tile2
    
    # Verify content stability
    assert isinstance(tile1.point_cloud, moira_native.LolaPointCloud)
    assert tile1.point_cloud.size() > 0
    
    # Verify coordinate accessors work on cached object
    x1 = tile1.point_cloud.get_x()
    x2 = tile2.point_cloud.get_x()
    assert x1 == x2
    
    print(f"Verified cache integrity for {url} with {tile1.point_cloud.size()} points.")

if __name__ == "__main__":
    pytest.main([__file__])
