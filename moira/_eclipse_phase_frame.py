"""Fail-closed FW/Vondrak mean-frame interval dispatch."""
from __future__ import annotations

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_phase_pole import bound_fw_mean_ecliptic_pole
from ._eclipse_vondrak_bounds import bound_vondrak_mean_ecliptic_pole


class EclipsePhaseFrameUnavailable(EnclosureUnavailable):
    """The phase interval straddles or exceeds supported frame branches."""


def bound_mean_ecliptic_frame(tt_anchor_jd: float, tt_offset_days: I):
    """Choose one fully proved precession branch or return unavailable."""
    jd = _rounded(I.point(tt_anchor_jd) + tt_offset_days)
    centuries = _rounded(_rounded(jd - I.point(2451545.0)) / I.point(36525.0))
    if -50 <= centuries.lo and centuries.hi <= 50:
        return bound_fw_mean_ecliptic_pole(tt_anchor_jd, tt_offset_days)
    if (centuries.hi < -50 and centuries.lo >= -200) or (centuries.lo > 50 and centuries.hi <= 200):
        return bound_vondrak_mean_ecliptic_pole(tt_anchor_jd, tt_offset_days)
    raise EclipsePhaseFrameUnavailable("FW/Vondrak transition or long-term frame domain requires subdivision")
