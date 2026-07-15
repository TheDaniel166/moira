from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.classical_perfection import ClassicalPerfectionEventKind, lilly_perfection_at
from moira.constants import Body
from moira.spk_reader import SpkReader


@pytest.mark.requires_ephemeris
def test_j2000_lilly_trace_uses_de441_and_preserves_event_chronology() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None and kernel.name == "de441.bsp"
    with SpkReader(kernel) as reader:
        result = lilly_perfection_at(
            2451545.0, 2451547.0, Body.MERCURY, Body.JUPITER,
            is_day_chart=True, reader=reader,
        )
    assert Path(result.reader_provenance).name == "de441.bsp"
    assert result.profile_id == "lilly_1647_perfection_v1"
    assert len(result.initial_states) == 7
    assert result.events == tuple(sorted(result.events, key=lambda item: (item.jd_ut, item.event_id)))
    assert len({item.event_id for item in result.events}) == len(result.events)
    assert result.policy.planetary_moiety_table == "lilly_1647_traditional_moieties"
    assert any(item.kind is ClassicalPerfectionEventKind.ASPECT_EXACT for item in result.events)
    assert any(item.kind is ClassicalPerfectionEventKind.SIGN_INGRESS for item in result.events)
    assert len(result.witnesses) == 6
    assert result.complete_electional_judgement is False
