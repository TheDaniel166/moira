"""Shared transport models for composed profile-bundle endpoints."""

from __future__ import annotations

from .common import _StrictModel


class ProfileBundleProvenanceResponse(_StrictModel):
    """Composition provenance for convenience profile bundles."""

    source_surface: str
    composition_only: bool = True
    doctrine_boundary: str
    included_existing_surfaces: tuple[str, ...]
    stage_sequence: tuple[str, ...]


__all__ = ["ProfileBundleProvenanceResponse"]
