"""
Moira — _kernel_paths.py
Centralised kernel-path resolution.

Search order for every BSP file:
  1. $MOIRA_KERNELS_DIR/         (env var — highest precedence; useful in containers)
  2. ~/.moira/kernels/           (user download location; works for pip installs)
  3. <package>/moira/kernels/    (files that ship inside the wheel)
  4. <repo_root>/kernels/        (developer working-tree fallback)

For the planetary kernel specifically, $MOIRA_KERNEL_PATH (a single file path)
is checked before the search-dir scan.

Public surface:
    find_kernel(filename)        -> Path        first existing path, else user-dir path
    find_planetary_kernel()      -> Path | None first installed planetary kernel, or None
    user_kernels_dir()           -> Path        ~/.moira/kernels
    kernel_search_dirs()         -> tuple[Path, ...] search roots in precedence order
    discover_kernels()           -> dict[str, Path] available .bsp files by precedence
    LARGE_KERNELS                -> list        names of kernels NOT shipped in the wheel
    PLANETARY_KERNELS            -> list        known JPL planetary ephemeris filenames
    KERNEL_PATH_ENV              -> str         name of the single-file env var
    KERNELS_DIR_ENV              -> str         name of the search-directory env var
"""

import os
from pathlib import Path

# Environment variable names — documented here so callers can reference them
# without hard-coding strings.
KERNEL_PATH_ENV = "MOIRA_KERNEL_PATH"   # absolute path to one planetary kernel file
KERNELS_DIR_ENV = "MOIRA_KERNELS_DIR"   # directory that contains kernel files

_PACKAGE_KERNELS_DIR = Path(__file__).parent / "kernels"
_DEV_KERNELS_DIR = Path(__file__).parent.parent / "kernels"


def user_kernels_dir() -> Path:
    return Path.home() / ".moira" / "kernels"


def kernel_search_dirs() -> tuple[Path, ...]:
    """Return kernel search roots in resolver precedence order."""
    dirs: list[Path] = []
    env_dir = os.environ.get(KERNELS_DIR_ENV)
    if env_dir:
        dirs.append(Path(env_dir))
    dirs.extend([user_kernels_dir(), _PACKAGE_KERNELS_DIR, _DEV_KERNELS_DIR])
    return tuple(dirs)


def find_kernel(filename: str) -> Path:
    """Return the first existing path for *filename*, else the user-dir path."""
    for root in kernel_search_dirs():
        candidate = root / filename
        if candidate.exists():
            return candidate
    return user_kernels_dir() / filename


def discover_kernels() -> dict[str, Path]:
    """
    Return discovered ``.bsp`` kernels as {filename: resolved_path}.

    If the same filename appears in multiple roots, the first one by
    kernel_search_dirs() precedence is retained.
    """
    found: dict[str, Path] = {}
    for root in kernel_search_dirs():
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.glob("*.bsp"), key=lambda p: p.name.lower()):
            found.setdefault(path.name, path)
    return found


# Known JPL planetary ephemeris kernels, checked in this order when no
# explicit kernel path has been configured.
PLANETARY_KERNELS: list[str] = [
    "de430.bsp",
    "de440.bsp",
    "de441.bsp",
    "de432.bsp",
    "de431.bsp",
]


def find_planetary_kernel() -> Path | None:
    """Return the path to the first installed planetary kernel, or None.

    Checks $MOIRA_KERNEL_PATH before scanning search directories, so
    containerised deployments can override discovery with a single env var.
    """
    env_path = os.environ.get(KERNEL_PATH_ENV)
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    for name in PLANETARY_KERNELS:
        path = find_kernel(name)
        if path.exists():
            return path
    return None


# BSP files too large to ship inside the wheel — users must download them.
LARGE_KERNELS: list[str] = [
    "de430.bsp", "de440.bsp", "de441.bsp",
    "asteroids.bsp", "sb441-n373s.bsp",
]
