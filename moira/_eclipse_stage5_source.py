"""Bounded Stage 5 frame adapter over one frozen current-policy event domain."""
from ._eclipse_continuous_solar_stage3 import (
    prepare_continuous_solar_stage3,continuous_solar_stage3_provider,
)
from ._eclipse_central_region_bounds import central_frame_patch_bounds


def prepare_stage5_source(reader,anchor,domain, *, panel_count=16):
    """Return request-local frame and whole-product footprint providers.

    Preserve the source scope and counters for provenance and all joins.
    Cache only bounds for exactly the same closed time interval.
    """
    scope = prepare_continuous_solar_stage3(reader,anchor,domain,panel_count=panel_count)
    provider,stats = continuous_solar_stage3_provider(scope,frame_only=True)
    cache = {}

    def frame(interval):
        if interval not in cache:
            cache[interval] = provider(interval)
        return cache[interval]

    def footprint(interval,patch):
        return central_frame_patch_bounds(frame(interval),patch)

    return frame,footprint,scope,stats
