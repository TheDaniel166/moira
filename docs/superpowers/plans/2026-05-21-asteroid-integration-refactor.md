# Asteroid Integration Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the asteroid and planetary pipelines so `asteroid_at` routes through the same apparent-place computation as `planet_at`, with `KernelPool` as the sole center-resolution authority and `SmallBodyKernel` as a proper `KernelReader`.

**Architecture:** `KernelPool.position` gains two-phase dispatch — direct match then center-chain composition — eliminating all `isinstance` checks. `SmallBodyKernel` gains the missing `KernelReader` protocol methods. A new `_apparent_geocentric_ecliptic` function extracted from `planets.py` is shared by both planet and asteroid callers. `asteroid_at` is rewritten to call this shared pipeline; all duplicated correction logic and legacy shims in `asteroids.py` are deleted.

**Tech Stack:** Python 3.14, Moira native extension (`moira_native`), pytest, JPL SPK kernels.

---

## File Map

| File | Change |
|---|---|
| `moira/_spk_body_kernel.py` | Rename `_native_catalog_is_fully_supported`; add `position(center,target,jd)`, `position_and_velocity`, `has_segment`, `covered_bodies` to `SmallBodyKernel` |
| `moira/spk_reader.py` | Rename `_native_catalog_is_fully_supported`; add `vec_add` import; replace `KernelPool` isinstance branches with phase-1/phase-2 dispatch |
| `moira/planets.py` | Extract `_apparent_geocentric_ecliptic`; update `_planet_at_default_apparent_geocentric_ecliptic` to call it |
| `moira/asteroids.py` | Add `_asteroid_deflectors`; rewrite `asteroid_at`; delete 7 functions + dead state |
| `tests/unit/test_adversarial_native_daf_reader.py` | Add protocol-compliance tests for `SmallBodyKernel` |
| `tests/unit/test_kernel_pool_center_chaining.py` | New — tests for phase-2 center chaining |

---

## Task 1: Disambiguate `_native_catalog_is_fully_supported`

Two functions share this name with different behaviour. Rename both before any other change so grep results are unambiguous.

**Files:**
- Modify: `moira/_spk_body_kernel.py`
- Modify: `moira/spk_reader.py`

- [ ] **Step 1: Rename in `_spk_body_kernel.py`**

  In `moira/_spk_body_kernel.py`, rename the function definition at line 312 and its two call-sites:

  ```python
  # OLD (line 312)
  def _native_catalog_is_fully_supported(catalog: dict) -> bool:

  # NEW
  def _small_body_kernel_native_supported(catalog: dict) -> bool:
  ```

  Update the two callers in that file:
  - `SmallBodyKernel.__init__` (line ~350): `if not _native_catalog_is_fully_supported(catalog):` → `if not _small_body_kernel_native_supported(catalog):`
  - `_native_segment_for` is not a caller — only `SmallBodyKernel.__init__` calls it.

- [ ] **Step 2: Rename in `spk_reader.py`**

  In `moira/spk_reader.py`, rename the function definition at line 410 and its call-site in `_open_kernel`:

  ```python
  # OLD (line 410)
  def _native_catalog_is_fully_supported(catalog: dict) -> bool:

  # NEW
  def _planetary_kernel_native_supported(catalog: dict) -> bool:
  ```

  Update the caller in `_open_kernel` (line ~270):
  ```python
  # OLD
  if _native_catalog_is_fully_supported(catalog):
  # NEW
  if _planetary_kernel_native_supported(catalog):
  ```

- [ ] **Step 3: Run tests**

  ```
  cd "c:\Users\nilad\OneDrive\Desktop\Moira C++"
  .venv/Scripts/python.exe -m pytest tests/unit/test_adversarial_native_daf_reader.py -v
  ```

  Expected: 7 passed.

- [ ] **Step 4: Commit**

  ```
  git add moira/_spk_body_kernel.py moira/spk_reader.py
  git commit -m "refactor(spk): disambiguate _native_catalog_is_fully_supported names"
  ```

---

## Task 2: Complete SmallBodyKernel KernelReader compliance

Add the four missing protocol methods. The old `position(naif_id, jd)` signature becomes `position(center, target, jd)` with explicit validation.

**Files:**
- Modify: `moira/_spk_body_kernel.py`
- Modify: `tests/unit/test_adversarial_native_daf_reader.py`

- [ ] **Step 1: Write failing tests**

  Append to `tests/unit/test_adversarial_native_daf_reader.py`:

  ```python
  def test_small_body_kernel_position_validates_center_before_returning(
      tmp_path: Path,
  ) -> None:
      if not body_kernel._HAS_NATIVE_DAF:
          pytest.skip("native small-body DAF reader is unavailable")

      path = tmp_path / "center_check.bsp"
      _synthetic_type13_kernel(path)   # center=10 (heliocentric)

      kernel = SmallBodyKernel(path)
      try:
          jd = kernel.coverage()[(10, 2000433)][0]
          # correct center works
          pos = kernel.position(10, 2000433, jd)
          assert all(math.isfinite(v) for v in pos)
          # wrong center raises ValueError
          with pytest.raises(ValueError, match="center"):
              kernel.position(0, 2000433, jd)
          # unknown NAIF raises KeyError
          with pytest.raises(KeyError):
              kernel.position(10, 9999999, jd)
      finally:
          kernel.close()


  def test_small_body_kernel_position_and_velocity_raises_not_implemented(
      tmp_path: Path,
  ) -> None:
      if not body_kernel._HAS_NATIVE_DAF:
          pytest.skip("native small-body DAF reader is unavailable")

      path = tmp_path / "pv_check.bsp"
      _synthetic_type13_kernel(path)

      kernel = SmallBodyKernel(path)
      try:
          jd = kernel.coverage()[(10, 2000433)][0]
          with pytest.raises(NotImplementedError):
              kernel.position_and_velocity(10, 2000433, jd)
      finally:
          kernel.close()


  def test_small_body_kernel_has_segment_and_covered_bodies(
      tmp_path: Path,
  ) -> None:
      if not body_kernel._HAS_NATIVE_DAF:
          pytest.skip("native small-body DAF reader is unavailable")

      path = tmp_path / "protocol.bsp"
      _synthetic_type13_kernel(path)  # naif=2000433, center=10

      kernel = SmallBodyKernel(path)
      try:
          assert kernel.has_segment(10, 2000433) is True
          assert kernel.has_segment(0, 2000433) is False
          assert kernel.has_segment(10, 9999999) is False
          assert 2000433 in kernel.covered_bodies()
          assert isinstance(kernel.covered_bodies(), frozenset)
      finally:
          kernel.close()
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```
  .venv/Scripts/python.exe -m pytest tests/unit/test_adversarial_native_daf_reader.py -v -k "validates_center or not_implemented or has_segment_and_covered"
  ```

  Expected: 3 FAILED (AttributeError or wrong signature).

- [ ] **Step 3: Implement the four protocol methods in SmallBodyKernel**

  In `moira/_spk_body_kernel.py`, replace the existing `position` method and add three new ones:

  ```python
  def position(self, center: int, target: int, jd_tt: float) -> Vec3:
      if not self.has_body(target):
          raise KeyError(
              f"NAIF ID {target} not found in kernel {self._path.name}"
          )
      seg_center = self._center[target]
      if center != seg_center:
          raise ValueError(
              f"SmallBodyKernel serves NAIF {target} from center "
              f"{seg_center}, not center {center}"
          )
      for seg in self._kernel.segments:
          if seg.target == target and seg.start_jd <= jd_tt <= seg.end_jd:
              pos = seg.compute(jd_tt)
              return (float(pos[0]), float(pos[1]), float(pos[2]))
      raise KeyError(
          f"No segment covers NAIF {target} at JD {jd_tt:.2f}. "
          "The date may be outside the kernel's coverage."
      )

  def position_and_velocity(
      self, center: int, target: int, jd_tt: float
  ) -> tuple[Vec3, Vec3]:
      raise NotImplementedError(
          "SmallBodyKernel does not support position_and_velocity. "
          "Use KernelPool.position_and_velocity, which raises NotImplementedError "
          "for small-body targets."
      )

  def has_segment(self, center: int, target: int) -> bool:
      for seg in self._kernel.segments:
          if seg.target == target and seg.center == center:
              return True
      return False

  def covered_bodies(self) -> frozenset[int]:
      return frozenset(self._available)
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```
  .venv/Scripts/python.exe -m pytest tests/unit/test_adversarial_native_daf_reader.py -v
  ```

  Expected: 10 passed (7 original + 3 new).

- [ ] **Step 5: Commit**

  ```
  git add moira/_spk_body_kernel.py tests/unit/test_adversarial_native_daf_reader.py
  git commit -m "feat(spk): make SmallBodyKernel a proper KernelReader"
  ```

---

## Task 3: KernelPool phase-2 center chaining

Replace the `isinstance`-based dispatch in `KernelPool` with uniform protocol calls plus phase-2 center chaining. Add `vec_add` import.

**Files:**
- Modify: `moira/spk_reader.py`
- Create: `tests/unit/test_kernel_pool_center_chaining.py`

- [ ] **Step 1: Write failing tests**

  Create `tests/unit/test_kernel_pool_center_chaining.py`:

  ```python
  """
  Tests for KernelPool two-phase center-chain dispatch.

  Phase 1: reader serves (center, target) directly — no chaining.
  Phase 2: reader serves (X, target) where X != center — pool chains
           raw position + bridge position to yield the requested center.
  """
  from __future__ import annotations

  import math
  from unittest.mock import MagicMock

  import pytest

  from moira.spk_reader import KernelPool, OutOfRangeError


  def _make_reader(center: int, target: int, pos: tuple, *, jd: float = 2451545.0):
      """Return a minimal KernelReader mock serving one (center, target) pair."""
      r = MagicMock()
      r.has_segment_at.side_effect = (
          lambda c, t, j: c == center and t == target and abs(j - jd) < 1e-3
      )
      r.has_segment.side_effect = lambda c, t: c == center and t == target
      r.position.side_effect = (
          lambda c, t, j: pos if (c == center and t == target) else (_ for _ in ()).throw(KeyError)
      )
      r.coverage.return_value = {(center, target): (jd - 1.0, jd + 1.0)}
      r.covered_bodies.return_value = frozenset([target])
      return r


  def test_pool_phase1_direct_match_returns_without_chaining():
      """Phase 1: body served at requested center — one reader call, no recursion."""
      jd = 2451545.0
      ssb_reader = _make_reader(0, 10, (1.0, 2.0, 3.0), jd=jd)   # Sun at SSB
      pool = KernelPool([ssb_reader])

      result = pool.position(0, 10, jd)
      assert result == (1.0, 2.0, 3.0)
      ssb_reader.position.assert_called_once_with(0, 10, jd)


  def test_pool_phase2_heliocentric_body_chains_through_sun():
      """
      Phase 2: asteroid served heliocentric (center=10), caller wants SSB (center=0).
      Pool must fetch asteroid from heliocentric reader, Sun from planetary reader,
      and return vec_add(asteroid_helio, sun_ssb).
      """
      jd = 2451545.0
      helio_asteroid = (100.0, 200.0, 300.0)
      sun_ssb        = (10.0,  20.0,  30.0)
      expected_ssb   = (110.0, 220.0, 330.0)

      asteroid_reader = _make_reader(10, 2002060, helio_asteroid, jd=jd)
      sun_reader      = _make_reader(0, 10, sun_ssb, jd=jd)

      pool = KernelPool([asteroid_reader, sun_reader])

      result = pool.position(0, 2002060, jd)
      assert result == pytest.approx(expected_ssb)


  def test_pool_raises_out_of_range_when_no_reader_covers_target():
      """No reader covers the requested body — OutOfRangeError raised."""
      jd = 2451545.0
      reader = _make_reader(0, 10, (1.0, 2.0, 3.0), jd=jd)
      pool = KernelPool([reader])

      with pytest.raises(OutOfRangeError):
          pool.position(0, 9999999, jd)


  def test_pool_covered_bodies_union_across_readers():
      """covered_bodies() returns union of all reader covered_bodies."""
      r1 = MagicMock()
      r1.covered_bodies.return_value = frozenset([1, 2])
      r1.coverage.return_value = {}
      r2 = MagicMock()
      r2.covered_bodies.return_value = frozenset([3, 4])
      r2.coverage.return_value = {}

      pool = KernelPool([r1, r2])
      assert pool.covered_bodies() == frozenset([1, 2, 3, 4])
  ```

- [ ] **Step 2: Run to verify failures**

  ```
  .venv/Scripts/python.exe -m pytest tests/unit/test_kernel_pool_center_chaining.py -v
  ```

  Expected: `test_pool_phase2_heliocentric_body_chains_through_sun` FAILS (no chaining implemented yet). Others may pass or fail depending on current state.

- [ ] **Step 3: Add `vec_add` import to `spk_reader.py`**

  After the existing imports block in `moira/spk_reader.py`, add:

  ```python
  from .coordinates import vec_add
  ```

  Place it after `from ._kernel_paths import find_kernel, find_planetary_kernel, find_sovereign_small_body_manifest`.

- [ ] **Step 4: Replace `KernelPool.position` with phase-1/phase-2 dispatch**

  In `moira/spk_reader.py`, replace the entire `KernelPool.position` method body:

  ```python
  def position(self, center: int, target: int, jd: float) -> Vec3:
      # Phase 1: direct match
      for reader in self._readers:
          if reader.has_segment_at(center, target, jd):
              return reader.position(center, target, jd)
      # Phase 2: center chain — find a reader that serves (X, target) where X != center,
      # then compose: position(center, X) + position(X, target)
      for reader in self._readers:
          for (c, t), (seg_start, seg_end) in reader.coverage().items():
              if t == target and c != center and seg_start <= jd <= seg_end:
                  if reader.has_segment_at(c, target, jd):
                      raw = reader.position(c, target, jd)
                      bridge = self.position(center, c, jd)
                      return vec_add(raw, bridge)
      raise OutOfRangeError(
          f"No kernel covers center={center}, target={target} at JD {jd:.2f}",
          out_of_range_times=True,
      )
  ```

- [ ] **Step 5: Replace `KernelPool.covered_bodies` — remove isinstance**

  ```python
  def covered_bodies(self) -> frozenset[int]:
      bodies: set[int] = set()
      for reader in self._readers:
          bodies.update(reader.covered_bodies())
      return frozenset(bodies)
  ```

- [ ] **Step 6: Replace `KernelPool.has_segment` — remove isinstance**

  ```python
  def has_segment(self, center: int, target: int) -> bool:
      for reader in self._readers:
          if reader.has_segment(center, target):
              return True
      return False
  ```

- [ ] **Step 7: Remove `SmallBodyKernel` import from `KernelPool.__init__`**

  In `KernelPool.__init__`, delete these two lines:

  ```python
  # DELETE these lines from __init__:
  from ._spk_body_kernel import SmallBodyKernel as _SmallBodyKernel
  self._SmallBodyKernel = _SmallBodyKernel
  ```

  Also remove `self._SmallBodyKernel` from any remaining uses in the class. After Step 4–6 there should be none.

- [ ] **Step 8: Run new unit tests**

  ```
  .venv/Scripts/python.exe -m pytest tests/unit/test_kernel_pool_center_chaining.py -v
  ```

  Expected: 4 passed.

- [ ] **Step 9: Run full suite to verify planets unchanged**

  ```
  .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/integration/test_eclipse_occultation_where_reference.py
  ```

  Expected: all pass (the eclipse test is a pre-existing failure unrelated to this refactor).

- [ ] **Step 10: Commit**

  ```
  git add moira/spk_reader.py tests/unit/test_kernel_pool_center_chaining.py
  git commit -m "feat(pool): add phase-2 center chaining, remove isinstance dispatch"
  ```

---

## Task 4: Extract `_apparent_geocentric_ecliptic` from `planets.py`

This is the highest-risk task. Extract the shared pipeline function and immediately verify that the 42 killer tests produce identical results.

**Files:**
- Modify: `moira/planets.py`

- [ ] **Step 1: Write a baseline planet position snapshot before touching any code**

  Run the following and capture the output — this is your invariant:

  ```
  .venv/Scripts/python.exe -c "
  from moira import Moira
  m = Moira()
  c = m.chart(2451545.0)
  from moira.constants import Body
  for b in [Body.SUN, Body.MOON, Body.MARS, Body.JUPITER]:
      pd = c.planet(b)
      print(f'{b}: lon={pd.longitude:.8f} lat={pd.latitude:.8f} dist={pd.distance:.4f}')
  "
  ```

  Record the output. After the extraction, running the same script must produce byte-identical values.

- [ ] **Step 2: Add `_apparent_geocentric_ecliptic` to `planets.py`**

  Insert this function directly before `_planet_at_default_apparent_geocentric_ecliptic` (around line 1215):

  ```python
  def _apparent_geocentric_ecliptic(
      body_id,
      jd_tt: float,
      reader: KernelReader,
      *,
      barycentric_fn,
      deflectors,
      earth_ssb: Vec3,
      earth_vel: Vec3,
      obliquity: float,
      rot_mat,
  ) -> tuple[float, float, float]:
      """
      Shared apparent-place pipeline: light-time → deflection → aberration →
      frame bias → rotation (precession+nutation) → ecliptic projection.

      Parameters
      ----------
      body_id       : opaque body identifier passed through to barycentric_fn
      jd_tt         : Julian Day (TT)
      reader        : active KernelReader (passed to barycentric_fn and apply_light_time)
      barycentric_fn: callable(body_id, jd_tt, reader) → Vec3 — SSB position
      deflectors    : list of (geocentric_vec, schwarzschild_radius) pairs;
                      pass [] to skip deflection (Sun, Moon)
      earth_ssb     : Earth SSB position at jd_tt (km, ICRF)
      earth_vel     : Earth SSB velocity at jd_tt (km/day, ICRF)
      obliquity     : true obliquity in degrees
      rot_mat       : pre-composed M_nut @ M_prec rotation matrix

      Returns
      -------
      (longitude, latitude, distance) in degrees, degrees, km
      """
      xyz, _lt = apply_light_time(body_id, jd_tt, reader, earth_ssb, barycentric_fn)
      if deflectors:
          xyz = apply_deflection(xyz, deflectors)
      xyz = apply_aberration(xyz, earth_vel)
      xyz = apply_frame_bias(xyz)
      xyz = _apply_rotation_matrix(rot_mat, xyz)
      return icrf_to_ecliptic(xyz, obliquity)
  ```

- [ ] **Step 3: Update `_planet_at_default_apparent_geocentric_ecliptic` to use it**

  Replace the body of `_planet_at_default_apparent_geocentric_ecliptic` (lines 1228–1262):

  ```python
  def _planet_at_default_apparent_geocentric_ecliptic(
      body: str,
      *,
      jd_tt: float,
      reader: KernelReader,
      context: _ApparentContext,
  ) -> PlanetData:
      earth_ssb = context.earth_ssb
      earth_vel = context.earth_vel
      rot_mat = context.rot_mat
      if earth_ssb is None or earth_vel is None or rot_mat is None:
          raise RuntimeError("default apparent context is incomplete")

      deflectors = (
          []
          if body in (Body.SUN, Body.MOON)
          else _deflectors_for_body(body, jd_tt, reader, context)
      )

      lon, lat, dist = _apparent_geocentric_ecliptic(
          body, jd_tt, reader,
          barycentric_fn=lambda b, t, r: _barycentric(b, t, r, context.vector_cache),
          deflectors=deflectors,
          earth_ssb=earth_ssb,
          earth_vel=earth_vel,
          obliquity=context.obliquity,
          rot_mat=rot_mat,
      )

      xyz_rate, vel_rate = _geocentric_state(body, jd_tt, reader, context.vector_cache)
      speed = _longitude_rate(xyz_rate, vel_rate, context.obliquity)

      return PlanetData(
          name=body,
          longitude=lon,
          latitude=lat,
          distance=dist,
          speed=speed,
          retrograde=(speed < 0.0),
          is_topocentric=False,
      )
  ```

- [ ] **Step 4: Run the baseline comparison**

  Run the same script from Step 1. Output must be byte-identical.

- [ ] **Step 5: Run the killer suite**

  ```
  .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/integration/test_eclipse_occultation_where_reference.py
  ```

  Expected: all pass.

- [ ] **Step 6: Commit**

  ```
  git add moira/planets.py
  git commit -m "refactor(planets): extract _apparent_geocentric_ecliptic as shared pipeline"
  ```

---

## Task 5: Add `_asteroid_deflectors` helper

Extract the deflector computation from `_asteroid_apparent` into a named helper. No logic change.

**Files:**
- Modify: `moira/asteroids.py`

- [ ] **Step 1: Add `_asteroid_deflectors` to `asteroids.py`**

  Add this function immediately before `_asteroid_apparent` in `moira/asteroids.py`:

  ```python
  def _asteroid_deflectors(
      jd_tt: float,
      reader,
      earth_ssb: Vec3,
  ) -> list:
      """Return the three standard deflector tuples for asteroid apparent-place computation."""
      sun_geo = vec_sub(reader.position(0, 10, jd_tt), earth_ssb)
      jupiter_geo = vec_sub(_planet_barycentric(Body.JUPITER, jd_tt, reader), earth_ssb)
      saturn_geo = vec_sub(_planet_barycentric(Body.SATURN, jd_tt, reader), earth_ssb)
      return [
          (sun_geo, SCHWARZSCHILD_RADII["Sun"]),
          (jupiter_geo, SCHWARZSCHILD_RADII["Jupiter"]),
          (saturn_geo, SCHWARZSCHILD_RADII["Saturn"]),
      ]
  ```

- [ ] **Step 2: Update `_asteroid_apparent` to call `_asteroid_deflectors`**

  In `_asteroid_apparent`, replace the inline deflector block:

  ```python
  # DELETE this block in _asteroid_apparent:
  sun_geocentric = vec_sub(reader.position(0, 10, jd_tt), earth_ssb)
  jupiter_geocentric = _planet_barycentric(Body.JUPITER, jd_tt, reader)
  jupiter_geocentric = vec_sub(jupiter_geocentric, earth_ssb)
  saturn_geocentric = _planet_barycentric(Body.SATURN, jd_tt, reader)
  saturn_geocentric = vec_sub(saturn_geocentric, earth_ssb)
  xyz = apply_deflection(
      xyz,
      [
          (sun_geocentric, SCHWARZSCHILD_RADII["Sun"]),
          (jupiter_geocentric, SCHWARZSCHILD_RADII["Jupiter"]),
          (saturn_geocentric, SCHWARZSCHILD_RADII["Saturn"]),
      ],
  )

  # REPLACE WITH:
  xyz = apply_deflection(xyz, _asteroid_deflectors(jd_tt, reader, earth_ssb))
  ```

- [ ] **Step 3: Run the Horizons asteroid integration tests**

  ```
  .venv/Scripts/python.exe -m pytest tests/integration/test_horizons_asteroid_apparent.py -v
  ```

  Expected: all pass (pure extraction, no logic change).

- [ ] **Step 4: Commit**

  ```
  git add moira/asteroids.py
  git commit -m "refactor(asteroids): extract _asteroid_deflectors helper"
  ```

---

## Task 6: Rewrite `asteroid_at` through the shared pipeline

Replace the `_asteroid_apparent` call in `asteroid_at` with `_apparent_geocentric_ecliptic` from `planets.py`. The public signature of `asteroid_at` does not change.

**Files:**
- Modify: `moira/asteroids.py`

- [ ] **Step 1: Add required imports to `asteroids.py`**

  In the imports section of `moira/asteroids.py`, update the planets import line:

  ```python
  # OLD
  from .planets import _earth_barycentric, _barycentric as _planet_barycentric

  # NEW
  from .planets import (
      _apparent_geocentric_ecliptic,
      _compose_rotation_matrix,
      _earth_barycentric_state,
      _barycentric as _planet_barycentric,
  )
  ```

- [ ] **Step 2: Rewrite `asteroid_at`**

  Replace the body of `asteroid_at` in `moira/asteroids.py` (the part from `jd_tt = ut_to_tt(jd_ut)` through the `return AsteroidData(...)`) with:

  ```python
      jd_tt = ut_to_tt(jd_ut)

      # Resolve name → NAIF ID
      if isinstance(name_or_naif, str):
          key = name_or_naif.strip()
          if key not in ASTEROID_NAIF:
              lower = key.lower()
              match = next((v for k, v in ASTEROID_NAIF.items() if k.lower() == lower), None)
              if match is None:
                  raise KeyError(
                      f"Asteroid {name_or_naif!r} not in ASTEROID_NAIF. "
                      "Pass an integer NAIF ID directly, or use list_asteroids()."
                  )
              naif_id = match
          else:
              naif_id = ASTEROID_NAIF[key]
          name = key
      else:
          naif_id = int(name_or_naif)
          name    = _NAIF_TO_NAME.get(naif_id, f"NAIF-{naif_id}")

      obliquity            = true_obliquity(jd_tt)
      earth_ssb, earth_vel = _earth_barycentric_state(jd_tt, reader)
      rot_mat              = _compose_rotation_matrix(jd_tt)
      deflectors           = _asteroid_deflectors(jd_tt, reader, earth_ssb)

      def _bary_fn(b, t, r):
          return r.position(0, b, t)

      lon0, lat0, dist0 = _apparent_geocentric_ecliptic(
          naif_id, jd_tt, reader,
          barycentric_fn=_bary_fn,
          deflectors=deflectors,
          earth_ssb=earth_ssb,
          earth_vel=earth_vel,
          obliquity=obliquity,
          rot_mat=rot_mat,
      )

      # Speed via central finite difference; obliquity is fixed at jd_tt.
      def _lon_at(jd: float) -> float:
          ssb, vel = _earth_barycentric_state(jd, reader)
          rm = _compose_rotation_matrix(jd)
          dfl = _asteroid_deflectors(jd, reader, ssb)
          lon, _, _ = _apparent_geocentric_ecliptic(
              naif_id, jd, reader,
              barycentric_fn=_bary_fn,
              deflectors=dfl,
              earth_ssb=ssb,
              earth_vel=vel,
              obliquity=obliquity,
              rot_mat=rm,
          )
          return lon

      lon_m = _lon_at(jd_tt - _SPEED_STEP)
      lon_p = _lon_at(jd_tt + _SPEED_STEP)
      dlon  = (lon_p - lon_m + 540.0) % 360.0 - 180.0
      speed = dlon / (2.0 * _SPEED_STEP)

      return AsteroidData(
          name=name,
          naif_id=naif_id,
          longitude=lon0,
          latitude=lat0,
          distance=dist0,
          speed=speed,
          retrograde=(speed < 0.0),
      )
  ```

  Note: `_asteroid_barycentric`, `_asteroid_apparent`, and `_asteroid_geocentric` still exist in the file at this point — do not delete them yet. They will be removed in Task 7 after verification.

- [ ] **Step 3: Run the Horizons asteroid integration tests**

  ```
  .venv/Scripts/python.exe -m pytest tests/integration/test_horizons_asteroid_apparent.py -v
  ```

  Expected: all pass. If any longitude deviates by more than 1e-4°, investigate before proceeding — the refactored pipeline must match the old one within floating-point noise.

- [ ] **Step 4: Run the full suite**

  ```
  .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/integration/test_eclipse_occultation_where_reference.py
  ```

  Expected: all pass.

- [ ] **Step 5: Commit**

  ```
  git add moira/asteroids.py
  git commit -m "feat(asteroids): route asteroid_at through shared apparent-place pipeline"
  ```

---

## Task 7: Delete dead code

Remove everything that the new pipeline made redundant. No logic survives this task — only deletions.

**Files:**
- Modify: `moira/asteroids.py`

- [ ] **Step 1: Delete the seven obsolete functions**

  In `moira/asteroids.py`, delete the following complete function definitions:

  1. `_asteroid_barycentric` — superseded by `reader.position(0, naif_id, jd)` via pool
  2. `_asteroid_apparent` — superseded by `_apparent_geocentric_ecliptic`
  3. `_asteroid_geocentric` — no longer called
  4. `_kernel_for` — no longer called
  5. `load_secondary_kernel` — callers use `load_asteroid_kernel` directly
  6. `load_tertiary_kernel` — callers use `load_asteroid_kernel` directly
  7. `load_quaternary_kernel` — callers use `load_asteroid_kernel` directly
  8. `_ensure_primary_kernel` — legacy test-bootstrap shim
  9. `_ensure_secondary_kernel` — legacy test-bootstrap shim
  10. `_ensure_tertiary_kernel` — legacy test-bootstrap shim
  11. `_ensure_quaternary_kernel` — legacy test-bootstrap shim

- [ ] **Step 2: Delete dead module-level state**

  Remove these lines from the module body of `moira/asteroids.py`:

  ```python
  # DELETE all four of these:
  _primary_kernel    = None
  _secondary_kernel  = None
  _tertiary_kernel   = None
  _quaternary_kernel = None

  # DELETE this frozenset — defined but never wired:
  _SB441_PREFERRED: frozenset[int] = frozenset({...})

  # DELETE the second (mid-file) copy of these four path variables
  # (the first copy at the top of the file stays):
  _PRIMARY_KERNEL_PATH    = _fk("asteroids.bsp")
  _SECONDARY_KERNEL_PATH  = _fk("sb441-n373s.bsp")
  _TERTIARY_KERNEL_PATH   = _fk("centaurs.bsp")
  _QUATERNARY_KERNEL_PATH = _fk("minor_bodies.bsp")

  # DELETE the mid-file re-import alias (also redundant):
  from ._kernel_paths import find_kernel as _fk
  ```

- [ ] **Step 3: Remove now-unused imports from `asteroids.py`**

  Review the import block and remove any symbol no longer referenced in the file body:
  - `_earth_barycentric` — replaced by `_earth_barycentric_state`
  - `icrf_to_ecliptic` — now called inside `_apparent_geocentric_ecliptic` in planets.py
  - `mat_vec_mul`, `precession_matrix_equatorial`, `nutation_matrix_equatorial` — called inside deleted functions
  - `apply_light_time`, `apply_deflection`, `apply_aberration`, `apply_frame_bias` — called inside deleted functions
  - Keep: `vec_sub`, `vec_add`, `vec_norm`, `Vec3` (used in `_asteroid_deflectors` and type annotations), `_planet_barycentric` (used in `_asteroid_deflectors`)

  Verify by running `python -c "import moira.asteroids"` — any `ImportError` or `NameError` at import time means a used symbol was removed.

- [ ] **Step 4: Run the full suite**

  ```
  .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/integration/test_eclipse_occultation_where_reference.py
  ```

  Expected: all pass.

- [ ] **Step 5: Final Horizons check**

  ```
  .venv/Scripts/python.exe -m pytest tests/integration/test_horizons_asteroid_apparent.py -v
  ```

  Expected: all pass.

- [ ] **Step 6: Commit**

  ```
  git add moira/asteroids.py
  git commit -m "refactor(asteroids): delete obsolete functions, shims, and dead state"
  ```
