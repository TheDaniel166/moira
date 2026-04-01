"""
Moira — _kernel_paths.py
Centralised kernel-path resolution.

Search order for every BSP file:
  1. ~/.moira/kernels/          (user download location; works for pip installs)
  2. <package>/moira/kernels/   (files that ship inside the wheel)
  3. <repo_root>/kernels/       (developer working-tree fallback)

Public surface:
    find_kernel(filename)  -> Path   first existing path, else user-dir path
    user_kernels_dir()     -> Path   ~/.moira/kernels
    LARGE_KERNELS          -> list   names of kernels NOT shipped in the wheel
"""

from pathlib import Path

_PACKAGE_KERNELS_DIR = Path(__file__).parent / "kernels"
_DEV_KERNELS_DIR = Path(__file__).parent.parent / "kernels"


def user_kernels_dir() -> Path:
    return Path.home() / ".moira" / "kernels"


def find_kernel(filename: str) -> Path:
    """Return the first existing path for *filename*, else the user-dir path."""
    for candidate in (
        user_kernels_dir() / filename,
        _PACKAGE_KERNELS_DIR / filename,
        _DEV_KERNELS_DIR / filename,
    ):
        if candidate.exists():
            return candidate
    return user_kernels_dir() / filename


# BSP files too large to ship inside the wheel — users must download them.
LARGE_KERNELS: list[str] = ["de441.bsp", "asteroids.bsp", "sb441-n373s.bsp"]
