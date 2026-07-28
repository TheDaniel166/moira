"""Python 3.10-compatible import boundary for :class:`enum.StrEnum`."""

from __future__ import annotations

try:
    from enum import StrEnum as StrEnum
except ImportError:  # pragma: no cover - exercised by the Python 3.10 wheel job
    from enum import Enum

    class StrEnum(str, Enum):
        """Minimal stdlib-compatible StrEnum fallback for Python 3.10."""

        @staticmethod
        def _generate_next_value_(
            name: str,
            start: int,
            count: int,
            last_values: list[object],
        ) -> str:
            return name.lower()

        def __str__(self) -> str:
            return str(self.value)

        def __format__(self, format_spec: str) -> str:
            return format(str(self), format_spec)


__all__ = ["StrEnum"]
