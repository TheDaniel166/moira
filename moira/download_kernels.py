"""
Moira — download_kernels.py
Downloads large JPL BSP kernel files that cannot ship inside the wheel.

Usage:
    python -m moira.download_kernels          # interactive, downloads all missing
    moira-download-kernels                    # same, via console script
    python -m moira.download_kernels --list   # show status of all kernels

Files are saved to ~/.moira/kernels/.

The moira-astro wheel ships the moira-asteroids-wheel small-body catalog
(25 named bodies). JPL optional kernels listed here do not substitute for
either Moira small-body catalog, and this tool does not download the
11,223-body archive.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from urllib.request import urlopen
from pathlib import Path

from ._kernel_paths import find_kernel, user_kernels_dir
from ._wheel_asteroid_catalog import CATALOG_DIR, CATALOG_ID, CATALOG_VERSION
from .small_body_catalog_release import CatalogReleaseError, verify_release

# ---------------------------------------------------------------------------
# Registry of downloadable kernels
# ---------------------------------------------------------------------------

_REGISTRY: list[dict] = [
    {
        "filename": "de430.bsp",
        "url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de430.bsp",
        "size_hint": "~128 MB",
        "description": "JPL DE430 planetary ephemeris (1550 BCE – 2650 CE)",
    },
    {
        "filename": "de440.bsp",
        "url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp",
        "size_hint": "~114 MB",
        "description": "JPL DE440 planetary ephemeris (1550 BCE – 2650 CE, improved accuracy)",
    },
    {
        "filename": "de441.bsp",
        "url": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de441.bsp",
        "size_hint": "~3.1 GB",
        "description": "JPL DE441 planetary ephemeris (extended range: ~13 200 BCE – ~17 200 CE)",
    },
    {
        "filename": "moon_pa_de440_200625.bpc",
        "url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de440_200625.bpc",
        "size_hint": "~12.3 MB",
        "description": "JPL DE440 lunar principal-axis orientation (binary PCK)",
        "byte_length": 12_863_488,
        "sha256": "60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f",
    },
    {
        "filename": "moon_de440_250416.tf",
        "url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_de440_250416.tf",
        "size_hint": "~19 KB",
        "description": "DE440 lunar PA-to-ME frame definition (text FK)",
        "byte_length": 19_478,
        "sha256": "a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768",
    },
    {
        "filename": "asteroids.bsp",
        "url": (
            "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/asteroids/"
            "codes_300ast_20100725.bsp"
        ),
        "size_hint": "~59 MB",
        "description": (
            "Generic JPL 300-asteroid kernel. Does not install Chiron and is "
            "not a substitute for either Moira catalog."
        ),
        "rename_from": "codes_300ast_20100725.bsp",
    },
    {
        "filename": "sb441-n373s.bsp",
        "url": "https://ssd.jpl.nasa.gov/ftp/eph/small_bodies/asteroids_de441/sb441-n373s.bsp",
        "size_hint": "~936 MB",
        "description": (
            "Optional JPL small-body kernel. Does not install Chiron and is "
            "not a substitute for either Moira catalog."
        ),
    },
]

_LUNAR_ORIENTATION_FILENAMES = frozenset(
    {"moon_pa_de440_200625.bpc", "moon_de440_250416.tf"}
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry_status(entry: dict) -> tuple[str, Path]:
    path = find_kernel(entry["filename"])
    if not path.is_file():
        return "MISSING", path
    expected_bytes = entry.get("byte_length")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        return "MISMATCH", path
    expected_sha256 = entry.get("sha256")
    if expected_sha256 is not None:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected_sha256:
            return "MISMATCH", path
    return "OK", path


_CHUNK_SIZE = 65_536  # 64 KiB
_CONNECT_TIMEOUT = 30  # seconds — applies to connection and each socket read


def _check_registry_urls() -> None:
    """Abort at import time if any registry URL is not https://."""
    for entry in _REGISTRY:
        if not entry["url"].startswith("https://"):
            raise ValueError(
                f"Registry URL must use https://: {entry['url']!r}"
            )


_check_registry_urls()


def _download(
    url: str,
    dest: Path,
    size_hint: str,
    *,
    expected_bytes: int | None = None,
    expected_sha256: str | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {dest.name} ({size_hint}) …")
    print(f"  Source : {url}")
    print(f"  Target : {dest}")

    # Write to a .part file; rename into place only after full verified write.
    part = dest.with_suffix(dest.suffix + ".part")
    if part.exists():
        part.unlink()  # remove any stale partial download

    progress_started = False
    newline_printed = False
    try:
        with urlopen(url, timeout=_CONNECT_TIMEOUT) as response:  # noqa: S310 — hardcoded https:// constants
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} from {url}")
            expected = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            digest = hashlib.sha256()
            with part.open("wb") as fh:
                while True:
                    chunk = response.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    fh.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    progress_started = True
                    if expected > 0:
                        pct = min(100, downloaded * 100 // expected)
                        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                        print(f"\r  [{bar}] {pct:3d}%", end="", flush=True)
                    else:
                        mb = downloaded / 1_048_576
                        print(f"\r  {mb:.1f} MB downloaded", end="", flush=True)

        if progress_started:
            print()  # newline after progress bar
            newline_printed = True

        if expected and downloaded != expected:
            raise RuntimeError(
                f"Incomplete download: received {downloaded} of {expected} bytes"
            )
        if expected_bytes is not None and downloaded != expected_bytes:
            raise RuntimeError(
                f"Resource identity mismatch: received {downloaded} bytes, "
                f"expected {expected_bytes}"
            )
        if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
            raise RuntimeError("Resource identity mismatch: SHA-256 differs from manifest")

        # Atomic promotion: dest replaced only after full verified write.
        if dest.exists():
            dest.unlink()
        part.rename(dest)

    except Exception as exc:
        if progress_started and not newline_printed:
            print()
        if part.exists():
            part.unlink()
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"Download failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_missing(
    interactive: bool = True,
    *,
    filenames: frozenset[str] | None = None,
) -> None:
    """Download missing selected kernels to ~/.moira/kernels/.

    Only one planetary kernel is required (de430, de440, or de441).
    Asteroid, small-body, and lunar-orientation kernels are optional.
    When ``filenames`` is omitted the historical all-registry behavior is
    preserved.
    """
    dest_dir = user_kernels_dir()
    selected = (
        _REGISTRY
        if filenames is None
        else [entry for entry in _REGISTRY if entry["filename"] in filenames]
    )
    missing = [entry for entry in selected if _entry_status(entry)[0] != "OK"]

    if not missing:
        print("All required kernels are already present.")
        return

    print(f"Kernel directory: {dest_dir}\n")
    print("Missing kernels:")
    for k in missing:
        print(f"  {k['filename']:30s}  {k['size_hint']:10s}  {k['description']}")

    if interactive:
        answer = input("\nDownload now? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            return

    for k in missing:
        dest = dest_dir / k["filename"]
        try:
            _download(
                k["url"],
                dest,
                k["size_hint"],
                expected_bytes=k.get("byte_length"),
                expected_sha256=k.get("sha256"),
            )
            print(f"  Saved to {dest}\n")
        except RuntimeError as exc:
            print(f"  ERROR: {exc}\n")
            print(f"  You can download it manually from:\n    {k['url']}\n"
                  f"  and place it in {dest_dir}\n")


def list_kernels() -> None:
    """Print the status of all kernels and the wheel small-body catalog."""
    print(f"Kernel directory: {user_kernels_dir()}\n")
    print(f"{'Filename':<30}  {'Status':<12}  {'Location'}")
    print("-" * 80)
    for k in _REGISTRY:
        status, path = _entry_status(k)
        loc = str(path) if path.exists() else "(not found)"
        print(f"  {k['filename']:<28}  {status:<12}  {loc}")

    try:
        verify_release(CATALOG_DIR)
        status = "OK (wheel)"
        loc = str(CATALOG_DIR)
    except (CatalogReleaseError, OSError, ValueError):
        status = "MISSING"
        loc = str(CATALOG_DIR) if CATALOG_DIR.is_dir() else "(not found)"
    label = f"{CATALOG_ID} {CATALOG_VERSION}"
    print(f"  {label:<28}  {status:<12}  {loc}")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="moira-download-kernels",
        description="Download JPL/NAIF kernel files used by Moira.",
    )
    parser.add_argument(
        "--list", action="store_true", help="Show kernel status and exit."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt."
    )
    parser.add_argument(
        "--lunar-orientation",
        action="store_true",
        help="Download only the pinned lunar-orientation PCK and frame kernel.",
    )
    args = parser.parse_args(argv)

    if args.list:
        list_kernels()
        return

    download_missing(
        interactive=not args.yes,
        filenames=(
            _LUNAR_ORIENTATION_FILENAMES if args.lunar_orientation else None
        ),
    )


if __name__ == "__main__":
    main(sys.argv[1:])
