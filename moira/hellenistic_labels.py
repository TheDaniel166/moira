"""
Named convenience overlays for Hellenistic receipts.

These labels do not invent doctrine. They name facts the engine already
computes so callers can print revival vocabulary without collapsing truth.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "HellenisticOverlayLabels",
    "HELLENISTIC_OVERLAY_CAVEATS",
]


HELLENISTIC_OVERLAY_CAVEATS: tuple[str, ...] = (
    "detriment is a later named exile overlay, not an early Hellenistic atom",
    "hayz/halb is medieval al-Qabisi/Bonatti, not ancient Hellenistic sect",
    "activation_orb_deg=5 is a modern overlay; Hellenistic activation is the sign",
    "civil equal-twelfths months are a computational projection, not Valens IV.28",
)


@dataclass(frozen=True, slots=True)
class HellenisticOverlayLabels:
    """Closed flag names for optional revival print helpers."""

    detriment: str = "detriment"
    hayz: str = "hayz"
    activation_orb_deg: float = 5.0
    monthly_interval: str = "civil_twelfths"
    caveats: tuple[str, ...] = HELLENISTIC_OVERLAY_CAVEATS
