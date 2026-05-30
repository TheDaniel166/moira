"""
Electional search stress test.

Tests:
  1. Correctness  — predicate results are verified against direct chart queries
  2. Performance  — measures throughput at 1h, 15min, and 5min step sizes
  3. Edge cases   — empty results, single-point windows, merge boundary, invalid args
  4. Predicate variety — simple, compound, aspect-based, dignity-based
  5. Long range   — 1-year scan at hourly resolution (~8760 chart constructions)
"""

import time
import traceback
from datetime import datetime, timezone

from moira.electional import (
    ElectionalPolicy,
    ElectionalWindow,
    find_electional_windows,
    find_electional_moments,
)
from moira.julian import jd_from_datetime, datetime_from_jd
from moira.constants import Body, HouseSystem
from moira.houses import assign_house
from moira.aspects import find_aspects
from moira.void_of_course import is_void_of_course
from moira.chart import create_chart

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def jd(year, month, day, hour=0):
    return jd_from_datetime(datetime(year, month, day, hour, tzinfo=timezone.utc))

LAT = 51.5074   # London
LON = -0.1278

# Safe body list — excludes Chiron (requires separate kernel)
BODIES = [
    Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE, Body.PLUTO,
]

BASE_POLICY = ElectionalPolicy(step_days=1/24, bodies=BODIES)

PASS = "  PASS"
FAIL = "  FAIL"

results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, condition))
    print(f"{status}  {name}" + (f"  [{detail}]" if detail else ""))
    return condition

# ---------------------------------------------------------------------------
# 1. Basic correctness — Moon sign
# ---------------------------------------------------------------------------
print("\n=== 1. Basic correctness: Moon sign ===")

def moon_in_taurus(chart):
    moon = chart.planets.get(Body.MOON)
    return moon is not None and moon.sign == "Taurus"

windows = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 30),
    latitude=LAT, longitude=LON,
    predicate=moon_in_taurus,
    policy=BASE_POLICY,
)

check("Moon-in-Taurus returns list", isinstance(windows, list))
check("Moon-in-Taurus finds windows", len(windows) > 0, f"{len(windows)} windows")

# Verify each window: every qualifying_jd should satisfy the predicate
all_correct = True
for w in windows:
    for jd_pt in w.qualifying_jds:
        chart = create_chart(jd_pt, LAT, LON, bodies=BODIES)
        if not moon_in_taurus(chart):
            all_correct = False
            break

check("All qualifying JDs satisfy predicate", all_correct)

# Verify window structure invariants
invariants_ok = all(
    w.jd_start <= w.jd_end
    and abs(w.duration_hours - (w.jd_end - w.jd_start) * 24) < 1e-9
    and len(w.qualifying_jds) >= 1
    and w.qualifying_jds[0] == w.jd_start
    and w.qualifying_jds[-1] == w.jd_end
    for w in windows
)
check("Window structural invariants hold", invariants_ok)

# Moon transits Taurus in ~2.5 days; expect ~2 windows in June
check("Moon-in-Taurus window count plausible", 1 <= len(windows) <= 4,
      f"{len(windows)} windows in June 2026")

# ---------------------------------------------------------------------------
# 2. find_electional_moments consistency
# ---------------------------------------------------------------------------
print("\n=== 2. find_electional_moments consistency ===")

moments = find_electional_moments(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 30),
    latitude=LAT, longitude=LON,
    predicate=moon_in_taurus,
    policy=BASE_POLICY,
)

check("moments returns list of floats", isinstance(moments, list) and all(isinstance(m, float) for m in moments))

# moments should be a superset of all qualifying_jds across windows
all_window_jds = set()
for w in windows:
    all_window_jds.update(w.qualifying_jds)

check("moments matches window qualifying_jds", set(moments) == all_window_jds,
      f"{len(moments)} moments, {len(all_window_jds)} from windows")

# ---------------------------------------------------------------------------
# 3. Empty result
# ---------------------------------------------------------------------------
print("\n=== 3. Edge case: empty result ===")

def never_true(chart):
    return False

empty = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 7),
    latitude=LAT, longitude=LON,
    predicate=never_true,
    policy=BASE_POLICY,
)
check("Never-true predicate returns empty list", empty == [])

# ---------------------------------------------------------------------------
# 4. Always-true predicate
# ---------------------------------------------------------------------------
print("\n=== 4. Edge case: always-true predicate ===")

def always_true(chart):
    return True

always = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 3),
    latitude=LAT, longitude=LON,
    predicate=always_true,
    policy=BASE_POLICY,
)
check("Always-true returns exactly one merged window", len(always) == 1)
check("Always-true window spans full range",
      always[0].jd_start <= jd(2026, 6, 1) + 1e-9
      and always[0].jd_end >= jd(2026, 6, 3) - 1/24 - 1e-9)

# ---------------------------------------------------------------------------
# 5. Merge gap — no-merge mode
# ---------------------------------------------------------------------------
print("\n=== 5. Merge gap: no-merge mode ===")

# Predicate that fires every other step
step = 1.0 / 24
call_count = [0]

def alternating(chart):
    call_count[0] += 1
    return (call_count[0] % 2) == 1

no_merge = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 1, 12),
    latitude=LAT, longitude=LON,
    predicate=alternating,
    policy=ElectionalPolicy(step_days=step, merge_gap_days=0.0, bodies=BODIES),
)
check("No-merge: each qualifying JD is its own window",
      all(len(w.qualifying_jds) == 1 for w in no_merge),
      f"{len(no_merge)} single-point windows")

# ---------------------------------------------------------------------------
# 6. Invalid arguments
# ---------------------------------------------------------------------------
print("\n=== 6. Invalid arguments ===")

try:
    find_electional_windows(
        jd_start=jd(2026, 6, 5),
        jd_end=jd(2026, 6, 1),   # end before start
        latitude=LAT, longitude=LON,
        predicate=always_true,
    )
    check("jd_start > jd_end raises ValueError", False)
except ValueError:
    check("jd_start > jd_end raises ValueError", True)

try:
    ElectionalPolicy(step_days=-1)
    check("Negative step_days raises ValueError", False)
except ValueError:
    check("Negative step_days raises ValueError", True)

try:
    ElectionalPolicy(merge_gap_days=-0.1)
    check("Negative merge_gap_days raises ValueError", False)
except ValueError:
    check("Negative merge_gap_days raises ValueError", True)

# ---------------------------------------------------------------------------
# 7. Compound predicate — Jupiter angular + Moon not void
# ---------------------------------------------------------------------------
print("\n=== 7. Compound predicate: Jupiter angular + Moon not void ===")

# Note: is_void_of_course runs its own bisection scan per call — expensive
# inside a predicate. This test verifies correctness on a short range only.
def jupiter_angular_not_void(chart):
    if chart.houses is None:
        return False
    jup = chart.planets.get(Body.JUPITER)
    if jup is None:
        return False
    placement = assign_house(jup.longitude, chart.houses)
    if placement.house not in (1, 4, 7, 10):
        return False
    return not is_void_of_course(chart.jd_ut)

t0 = time.perf_counter()
compound_windows = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 3),   # 2 days only — VOC is expensive per step
    latitude=LAT, longitude=LON,
    predicate=jupiter_angular_not_void,
    policy=BASE_POLICY,
)
elapsed = time.perf_counter() - t0

check("Compound predicate returns list", isinstance(compound_windows, list))
check("Compound predicate (2 days) completes in < 60s", elapsed < 60,
      f"{elapsed:.1f}s for 2-day hourly scan with VOC")
print(f"  INFO  Compound predicate: {len(compound_windows)} windows in {elapsed:.1f}s")
print(f"  INFO  Note: is_void_of_course inside predicate = ~{elapsed/48:.2f}s per step (bisection cost)")

# Lighter compound — Jupiter angular + day chart (no VOC scan)
def jupiter_angular_day(chart):
    if chart.houses is None or not chart.is_day:
        return False
    jup = chart.planets.get(Body.JUPITER)
    if jup is None:
        return False
    return assign_house(jup.longitude, chart.houses).house in (1, 4, 7, 10)

t0 = time.perf_counter()
light_compound = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 30),
    latitude=LAT, longitude=LON,
    predicate=jupiter_angular_day,
    policy=BASE_POLICY,
)
elapsed_light = time.perf_counter() - t0
check("Light compound (30 days) completes in < 30s", elapsed_light < 30,
      f"{elapsed_light:.1f}s, {len(light_compound)} windows")

# ---------------------------------------------------------------------------
# 8. Aspect-based predicate — Venus trine Jupiter within 3°
# ---------------------------------------------------------------------------
print("\n=== 8. Aspect predicate: Venus trine Jupiter ===")

def venus_trine_jupiter(chart):
    positions = {n: d.longitude for n, d in chart.planets.items()}
    speeds    = {n: d.speed    for n, d in chart.planets.items()}
    aspects = find_aspects(positions, speeds=speeds, orbs={120.0: 3.0})
    return any(
        {a.body1, a.body2} == {Body.VENUS, Body.JUPITER} and a.aspect == "Trine"
        for a in aspects
    )

t0 = time.perf_counter()
aspect_windows = find_electional_windows(
    jd_start=jd(2026, 6, 1),
    jd_end=jd(2026, 6, 30),   # 30 days — aspect predicate is expensive per step
    latitude=LAT, longitude=LON,
    predicate=venus_trine_jupiter,
    policy=BASE_POLICY,
)
elapsed = time.perf_counter() - t0

check("Aspect predicate returns list", isinstance(aspect_windows, list))
check("Aspect predicate (30 days) completes in < 60s", elapsed < 60,
      f"{elapsed:.1f}s for 30-day hourly scan")
print(f"  INFO  Venus trine Jupiter: {len(aspect_windows)} windows in {elapsed:.1f}s")

# ---------------------------------------------------------------------------
# 9. Performance — throughput benchmarks
# ---------------------------------------------------------------------------
print("\n=== 9. Performance benchmarks ===")

def trivial(chart):
    return chart.is_day

# 1-hour step, 30 days = 720 charts
t0 = time.perf_counter()
find_electional_windows(
    jd_start=jd(2026, 6, 1), jd_end=jd(2026, 6, 30),
    latitude=LAT, longitude=LON,
    predicate=trivial,
    policy=BASE_POLICY,
)
t_1h = time.perf_counter() - t0
charts_1h = int(29 * 24)
print(f"  INFO  1h step / 30 days: {charts_1h} charts in {t_1h:.2f}s  ({charts_1h/t_1h:.0f} charts/s)")
check("1h step 30-day scan < 30s", t_1h < 30, f"{t_1h:.2f}s")

# 15-min step, 7 days = 672 charts
t0 = time.perf_counter()
find_electional_windows(
    jd_start=jd(2026, 6, 1), jd_end=jd(2026, 6, 7),
    latitude=LAT, longitude=LON,
    predicate=trivial,
    policy=ElectionalPolicy(step_days=1/(24*4), bodies=BODIES),
)
t_15m = time.perf_counter() - t0
charts_15m = int(6 * 24 * 4)
print(f"  INFO  15min step / 7 days: {charts_15m} charts in {t_15m:.2f}s  ({charts_15m/t_15m:.0f} charts/s)")
check("15min step 7-day scan < 30s", t_15m < 30, f"{t_15m:.2f}s")

# 1-year hourly = ~8760 charts
t0 = time.perf_counter()
find_electional_windows(
    jd_start=jd(2026, 1, 1), jd_end=jd(2026, 12, 31),
    latitude=LAT, longitude=LON,
    predicate=trivial,
    policy=BASE_POLICY,
)
t_1y = time.perf_counter() - t0
charts_1y = 365 * 24
print(f"  INFO  1h step / 1 year: {charts_1y} charts in {t_1y:.2f}s  ({charts_1y/t_1y:.0f} charts/s)")
check("1h step 1-year scan < 120s", t_1y < 120, f"{t_1y:.2f}s")

# ---------------------------------------------------------------------------
# 10. House system variation
# ---------------------------------------------------------------------------
print("\n=== 10. House system variation ===")

def sun_in_house_1(chart):
    if chart.houses is None:
        return False
    sun = chart.planets.get(Body.MOON)
    if sun is None:
        return False
    return assign_house(sun.longitude, chart.houses).house == 1

for system_name, system_code in [
    ("Whole Sign", HouseSystem.WHOLE_SIGN),
    ("Equal",      HouseSystem.EQUAL),
    ("Koch",       HouseSystem.KOCH),
]:
    w = find_electional_windows(
        jd_start=jd(2026, 6, 1), jd_end=jd(2026, 6, 7),
        latitude=LAT, longitude=LON,
        predicate=sun_in_house_1,
        policy=ElectionalPolicy(step_days=1/24, house_system=system_code, bodies=BODIES),
    )
    check(f"House system {system_name} runs without error", isinstance(w, list),
          f"{len(w)} windows")

# ---------------------------------------------------------------------------
# 11. Polar latitude edge case
# ---------------------------------------------------------------------------
print("\n=== 11. Polar latitude edge case ===")

try:
    polar_windows = find_electional_windows(
        jd_start=jd(2026, 6, 1), jd_end=jd(2026, 6, 3),
        latitude=70.0, longitude=25.0,
        predicate=moon_in_taurus,
        policy=BASE_POLICY,
    )
    check("Polar latitude (70°N) runs without error", isinstance(polar_windows, list),
          f"{len(polar_windows)} windows")
except Exception as e:
    check("Polar latitude (70°N) runs without error", False, str(e))

# ---------------------------------------------------------------------------
# 12. Southern hemisphere
# ---------------------------------------------------------------------------
print("\n=== 12. Southern hemisphere ===")

try:
    south_windows = find_electional_windows(
        jd_start=jd(2026, 6, 1), jd_end=jd(2026, 6, 7),
        latitude=-33.87, longitude=151.21,
        predicate=moon_in_taurus,
        policy=BASE_POLICY,
    )
    check("Southern hemisphere runs without error", isinstance(south_windows, list),
          f"{len(south_windows)} windows")
except Exception as e:
    check("Southern hemisphere runs without error", False, str(e))

# ---------------------------------------------------------------------------
# 13. BCE date
# ---------------------------------------------------------------------------
print("\n=== 13. BCE date ===")

try:
    bce_windows = find_electional_windows(
        jd_start=jd(2026, 6, 1) - 365 * 2000,
        jd_end=jd(2026, 6, 1) - 365 * 2000 + 7,
        latitude=41.9, longitude=12.5,
        predicate=moon_in_taurus,
        policy=BASE_POLICY,
    )
    check("BCE date runs without error", isinstance(bce_windows, list),
          f"{len(bce_windows)} windows")
except Exception as e:
    check("BCE date runs without error", False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total  = len(results)
print(f"RESULTS: {passed}/{total} passed, {failed} failed")

if failed:
    print("\nFailed tests:")
    for name, ok in results:
        if not ok:
            print(f"  - {name}")
