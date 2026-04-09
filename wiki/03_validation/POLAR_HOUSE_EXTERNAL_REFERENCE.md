# Polar House External Reference

Status: verified against the cached Swiss `setest/t.exp` fixture in the project `.venv`

Purpose
-------
This page records the high-latitude external oracle slice for house validation.

It complements the internal polar-house gauntlets.
It does not replace them.

What the oracle covers
----------------------

| Metric | Measured value | Notes |
| --- | ---: | --- |
| Supra-critical Swiss fixture cases | `936` | Filtered from the cached `t.exp` house fixture |
| Latitude samples | `+89.9 deg`, `-89.9 deg` | Both polar extremes are present |
| JD range | `2456334.5` to `2456335.4166666665` | 2013 polar slice in the fixture |
| Supported systems represented | `13` | `O`, `R`, `C`, `E`, `V`, `W`, `X`, `H`, `T`, `B`, `M`, `U`, `Y` |
| Failures above `0.001 deg` | `0` | Same threshold as the main Swiss house validation |

System names represented
------------------------
- Porphyry
- Regiomontanus
- Campanus
- Equal
- Vehlow
- Whole Sign
- Meridian
- Azimuthal
- Topocentric
- Alcabitius
- Morinus
- Krusinski-Pisa
- APC

What this proves
----------------
- Moira matches the cached Swiss external oracle for supported house systems even when the observer is deep inside the polar cap.
- High-latitude support is not limited to one forgiving system; it spans 13 distinct system families in the current oracle slice.

What this does not prove
------------------------
- It does not validate Placidus, Koch, or Pullen SD above the critical latitude as direct Swiss cusp outputs, because the relevant truth question in Moira is fallback doctrine, not unsupported cusp generation.
- That fallback doctrine is covered separately by [tests/unit/test_polar_house_breadth_gauntlet.py](../../tests/unit/test_polar_house_breadth_gauntlet.py) and [tests/unit/test_polar_chart_public_gauntlet.py](../../tests/unit/test_polar_chart_public_gauntlet.py).

Proof artifact
--------------
- [tests/integration/test_houses_polar_external_reference.py](../../tests/integration/test_houses_polar_external_reference.py)
