"""Security-sensitive primitives shared by Moira pytest plugins."""

from __future__ import annotations

import stat


_WINDOWS_REPARSE_POINT_ATTRIBUTE = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)


_WINDOWS_NAME_SURROGATE_TAG_BIT = 0x20000000


def _is_name_surrogate_reparse(metadata) -> bool:
    has_reparse_flag = bool(
        getattr(metadata, "st_file_attributes", 0)
        & _WINDOWS_REPARSE_POINT_ATTRIBUTE
    )
    reparse_tag = getattr(metadata, "st_reparse_tag", None)
    return has_reparse_flag and (
        reparse_tag is None
        or bool(reparse_tag & _WINDOWS_NAME_SURROGATE_TAG_BIT)
    )


def _metadata_signature(metadata) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000)),
    )
