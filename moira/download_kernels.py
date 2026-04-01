"""
Moira — download_kernels.py
Downloads large JPL BSP kernel files that cannot ship inside the wheel.

Usage:
    python -m moira.download_kernels          # interactive, downloads all missing
    moira-download-kernels                    # same, via console script
    python -m moira.download_kernels --list   # show status of all kernels

Files are saved to ~/.moira/kernels/.

Kernels that already ship inside the moira wheel (centaurs.bsp,
minor_bodies.bsp) are skipped — they are always available after install.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from ._kernel_paths import find_kernel, user_kernels_dir

# ---------------------------------------------------------------------------
# Registry of downloadable kernels
# ---------------------------------------------------------------------------

_REGISTRY: list[dict] = [
    {
        "filename": "de441.bsp",
        "url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de441.bsp",
        "size_hint": "~3.1 GB",
        "description": "JPL DE441 planetary ephemeris (required for all charts)",
    },
    {
        "filename": "asteroids.bsp",
        "url": (
            "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/asteroids/"
            "codes_300ast_20100725.bsp"
        ),
        "size_hint": "~59 MB",
        "description": "300 classical asteroids (rename to asteroids.bsp after download)",
        "rename_from": "codes_300ast_20100725.bsp",
    },
    {
        "filename": "sb441-n373s.bsp",
        "url": "https://ssd.jpl.nasa.gov/ftp/eph/small_bodies/asteroids_de441/sb441-n373s.bsp",
        "size_hint": "~936 MB",
        "description": "Small bodies / TNOs (Ixion, Quaoar, Varuna, Orcus, …)",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_present(filename: str) -> bool:
    return find_kernel(filename).exists()


def _download(url: str, dest: Path, size_hint: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {dest.name} ({size_hint}) …")
    print(f"  Source : {url}")
    print(f"  Target : {dest}")

    def _report(block_count: int, block_size: int, total: int) -> None:
        downloaded = block_count * block_size
        if total > 0:
            pct = min(100, downloaded * 100 // total)
            bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct:3d}%", end="", flush=True)
        else:
            mb = downloaded / 1_048_576
            print(f"\r  {mb:.1f} MB downloaded", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, dest, reporthook=_report)
        print()  # newline after progress bar
    except Exception as exc:
        print()
        if dest.exists():
            dest.unlink()
        raise RuntimeError(f"Download failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_missing(interactive: bool = True) -> None:
    """Download all missing large kernels to ~/.moira/kernels/."""
    dest_dir = user_kernels_dir()
    missing = [k for k in _REGISTRY if not _is_present(k["filename"])]

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
            _download(k["url"], dest, k["size_hint"])
            print(f"  Saved to {dest}\n")
        except RuntimeError as exc:
            print(f"  ERROR: {exc}\n")
            print(f"  You can download it manually from:\n    {k['url']}\n"
                  f"  and place it in {dest_dir}\n")


def list_kernels() -> None:
    """Print the status of all kernels."""
    print(f"Kernel directory: {user_kernels_dir()}\n")
    print(f"{'Filename':<30}  {'Status':<12}  {'Location'}")
    print("-" * 80)
    for k in _REGISTRY:
        path = find_kernel(k["filename"])
        status = "OK" if path.exists() else "MISSING"
        loc = str(path) if path.exists() else "(not found)"
        print(f"  {k['filename']:<28}  {status:<12}  {loc}")

    # Also show bundled kernels
    bundled = ["centaurs.bsp", "minor_bodies.bsp"]
    for name in bundled:
        path = find_kernel(name)
        status = "OK (bundled)" if path.exists() else "MISSING"
        loc = str(path) if path.exists() else "(not found)"
        print(f"  {name:<28}  {status:<12}  {loc}")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="moira-download-kernels",
        description="Download JPL BSP kernel files required by Moira.",
    )
    parser.add_argument(
        "--list", action="store_true", help="Show kernel status and exit."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt."
    )
    args = parser.parse_args(argv)

    if args.list:
        list_kernels()
        return

    download_missing(interactive=not args.yes)


if __name__ == "__main__":
    main(sys.argv[1:])
