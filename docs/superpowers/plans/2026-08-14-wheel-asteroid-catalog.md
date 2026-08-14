# Wheel Asteroid Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a complete 25-body Type-13 catalog inside the `moira-astro` wheel so Chiron and the locked roster compute after `pip install` plus a planetary kernel, and close the `centaurs.bsp` install lie in #17.

**Architecture:** A second complete small-body catalog (`moira-asteroids-wheel` / `2026.08.14.1`) lives at `moira/kernels/asteroids_wheel/` with one shard. Discovery already walks `<root>/<subdir>/manifest.json`. The 10,025-body package manifest stays metadata-only. `KernelPool` first-match leaves a higher-precedence full catalog in charge when both are present.

**Tech Stack:** Python 3.10+, existing `scripts/build_unified_asteroid_catalog.py` Horizons/Type-13 writer, `moira.small_body_catalog_release`, setuptools package-data, pytest.

**Spec:** `docs/superpowers/specs/2026-08-14-wheel-asteroid-catalog-design.md`

## Global Constraints

- Roster is exactly the 25 NAIF IDs and names in the spec table. Hidalgo is not included.
- `catalog_id` is `moira-asteroids-wheel`. First `catalog_version` is `2026.08.14.1`.
- One shard only: `asteroid_shard_000.bsp`. `shard_count == 1`, `body_count == 25`.
- Do not put wheel BSP files under `moira/kernels/asteroids/`.
- Do not revive, host, or auto-load `centaurs.bsp` or `minor_bodies.bsp`.
- Do not download the 10,025-body catalog from `moira-download-kernels`.
- Do not change interpolation, light-time, or `asteroid_at` math.
- Do not add a second PyPI data package.
- Do not change website free/Enhanced entitlement lists.
- Same Horizons writer policy as the unified catalog: `CENTER=500@10`, `REF_PLANE=FRAME`, `OUT_UNITS=KM-S`, `STEP_SIZE=10d`, window `1600-01-01`–`2500-01-01`, Type-13 `window_size=7`.
- Published `2026.08.14.1` bytes are never rewritten. Wheel/sdist builds must not call Horizons.
- Ship as `moira-astro` `6.2.1`. No public function signature changes.
- Author in `C:\dev\moira` on a feature branch, not on leftover worktrees.

---

## File map

**Create**

- `moira/_wheel_asteroid_catalog.py` — identity constants and paths
- `moira/kernels/asteroids_wheel/targets.json` — frozen 25-row roster
- `scripts/build_wheel_asteroid_catalog.py` — one-time Horizons builder
- `tests/unit/test_wheel_asteroid_catalog.py` — roster, verify, package files
- `tests/unit/test_download_kernels_honesty.py` — no ghost bundled kernels
- `tests/unit/test_asteroid_missing_segment_message.py` — full-catalog error
- `tests/integration/test_wheel_asteroid_catalog_positions.py` — Chiron/Ceres/Eris/Amor

**Generate once and commit** (Task 3)

- `moira/kernels/asteroids_wheel/asteroid_shard_000.bsp`
- `moira/kernels/asteroids_wheel/asteroid_shard_000.metadata.json`
- `moira/kernels/asteroids_wheel/manifest.json`
- `moira/kernels/asteroids_wheel/SHA256SUMS`
- `moira/kernels/asteroids_wheel/LICENSE`
- `moira/kernels/asteroids_wheel/NOTICE.md`

**Modify**

- `pyproject.toml` — package-data globs and `version = "6.2.1"`
- `moira/facade.py` — `__version__ = "6.2.1"`
- `moira/download_kernels.py` — drop bundled lie, report wheel catalog, fix JPL blurbs
- `moira/asteroids.py` — wrap known-identity miss with catalog install text
- `moira/centaurs.py`, `moira/tno.py`, `moira/classical_asteroids.py` — module docs
- `moira/constants.py` — `Body.CHIRON` comment
- `README.md` — wheel catalog vs 10,025-body archive
- `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md` — Chiron row
- `CHANGELOG.md` — 6.2.1 notes

---

### Task 1: Frozen roster and identity helper

**Files:**
- Create: `moira/_wheel_asteroid_catalog.py`
- Create: `moira/kernels/asteroids_wheel/targets.json`
- Test: `tests/unit/test_wheel_asteroid_catalog.py`

**Interfaces:**
- Consumes: spec roster table
- Produces: `CATALOG_ID`, `CATALOG_VERSION`, `CATALOG_DIR`, `TARGETS_PATH`, `FULL_CATALOG_VERSION`, `EPHEMERIDES_URL`, `load_targets() -> list[dict]`

- [ ] **Step 1: Write the failing roster test**

```python
from __future__ import annotations

from moira._wheel_asteroid_catalog import (
    CATALOG_DIR,
    CATALOG_ID,
    CATALOG_VERSION,
    TARGETS_PATH,
    load_targets,
)

LOCKED = [
    (1, "Ceres", 2000001),
    (2, "Pallas", 2000002),
    (3, "Juno", 2000003),
    (4, "Vesta", 2000004),
    (5, "Astraea", 2000005),
    (7, "Iris", 2000007),
    (10, "Hygiea", 2000010),
    (16, "Psyche", 2000016),
    (433, "Eros", 2000433),
    (1181, "Lilith", 2001181),
    (1221, "Amor", 2001221),
    (2060, "Chiron", 2002060),
    (5145, "Pholus", 2005145),
    (7066, "Nessus", 2007066),
    (8405, "Asbolus", 2008405),
    (10199, "Chariklo", 2010199),
    (10370, "Hylonome", 2010370),
    (20000, "Varuna", 2020000),
    (28978, "Ixion", 2028978),
    (50000, "Quaoar", 2050000),
    (90377, "Sedna", 2090377),
    (90482, "Orcus", 2090482),
    (136108, "Haumea", 2136108),
    (136199, "Eris", 2136199),
    (136472, "Makemake", 2136472),
]


def test_locked_roster_is_exactly_twenty_five_naif_ordered_bodies() -> None:
    rows = load_targets()
    assert CATALOG_ID == "moira-asteroids-wheel"
    assert CATALOG_VERSION == "2026.08.14.1"
    assert TARGETS_PATH == CATALOG_DIR / "targets.json"
    assert [(row["number"], row["name"], row["naif_id"]) for row in rows] == LOCKED
    assert [row["naif_id"] for row in rows] == sorted(row["naif_id"] for row in rows)
    assert "Hidalgo" not in {row["name"] for row in rows}
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_locked_roster_is_exactly_twenty_five_naif_ordered_bodies -v`

Expected: FAIL with `ModuleNotFoundError: moira._wheel_asteroid_catalog`

- [ ] **Step 3: Add the helper and frozen targets file**

`moira/_wheel_asteroid_catalog.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

CATALOG_ID = "moira-asteroids-wheel"
CATALOG_VERSION = "2026.08.14.1"
FULL_CATALOG_VERSION = "2026.08.12.1"
EPHEMERIDES_URL = "https://moira-astro.com/ephemerides"
CATALOG_DIR = Path(__file__).resolve().parent / "kernels" / "asteroids_wheel"
TARGETS_PATH = CATALOG_DIR / "targets.json"


def load_targets() -> list[dict]:
    payload = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 25:
        raise ValueError(f"{TARGETS_PATH} must contain exactly 25 objects")
    rows: list[dict] = []
    for item in payload:
        number = int(item["number"])
        name = str(item["name"])
        naif_id = int(item["naif_id"])
        if naif_id != 2_000_000 + number:
            raise ValueError(f"{name}: naif_id {naif_id} != {2_000_000 + number}")
        rows.append({"number": number, "name": name, "naif_id": naif_id})
    return rows
```

`moira/kernels/asteroids_wheel/targets.json` is a JSON array of 25 objects in NAIF order. Each object is `{"number": N, "name": "...", "naif_id": 2000000+N}` using the LOCKED table above.

- [ ] **Step 4: Re-run the roster test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_locked_roster_is_exactly_twenty_five_naif_ordered_bodies -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add moira/_wheel_asteroid_catalog.py moira/kernels/asteroids_wheel/targets.json tests/unit/test_wheel_asteroid_catalog.py
git commit -m "feat(kernels): freeze 25-body wheel asteroid roster"
```

---

### Task 2: Horizons builder that refuses a short catalog

**Files:**
- Create: `scripts/build_wheel_asteroid_catalog.py`
- Test: `tests/unit/test_wheel_asteroid_catalog.py`

**Interfaces:**
- Consumes: `load_targets()`, `write_spk_type13`, fetch helpers from `scripts/build_unified_asteroid_catalog.py`
- Produces: `build_pre_release(output_dir: Path) -> Path` writing `asteroid_shard_000.bsp`, `asteroid_shard_000.metadata.json`, pre-release `manifest.json` (`catalog_id` = `moira-asteroids-wheel`, no `release` key), and a copy of `targets.json`

- [ ] **Step 1: Write failing tests for target validation and short-build refusal**

Add to `tests/unit/test_wheel_asteroid_catalog.py`:

```python
import importlib.util
from pathlib import Path

import pytest

from moira._wheel_asteroid_catalog import CATALOG_ID


def _load_builder():
    path = Path(__file__).resolve().parents[2] / "scripts" / "build_wheel_asteroid_catalog.py"
    spec = importlib.util.spec_from_file_location("build_wheel_asteroid_catalog", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_rejects_horizons_name_mismatch(tmp_path: Path, monkeypatch) -> None:
    builder = _load_builder()

    def fake_fetch(number: int) -> dict:
        return {
            "number": number,
            "naif_id": 2_000_000 + number,
            "name": "NotCeres" if number == 1 else f"Body{number}",
            "center": 10,
            "frame": 1,
            "states": [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0]],
            "epochs_jd": [2451545.0],
            "window_size": 7,
            "clamped": False,
            "start": "1600-01-01",
            "stop": "2500-01-01",
        }

    monkeypatch.setattr(builder, "_fetch_body", fake_fetch)
    with pytest.raises(RuntimeError, match="Ceres"):
        builder.build_pre_release(tmp_path)


def test_builder_refuses_to_write_when_a_body_fails(tmp_path: Path, monkeypatch) -> None:
    builder = _load_builder()

    def fake_fetch(number: int) -> dict:
        if number == 2060:
            raise RuntimeError("horizons down")
        return {
            "number": number,
            "naif_id": 2_000_000 + number,
            "name": next(
                row["name"]
                for row in __import__(
                    "moira._wheel_asteroid_catalog", fromlist=["load_targets"]
                ).load_targets()
                if row["number"] == number
            ),
            "center": 10,
            "frame": 1,
            "states": [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0]],
            "epochs_jd": [2451545.0],
            "window_size": 7,
            "clamped": False,
            "start": "1600-01-01",
            "stop": "2500-01-01",
        }

    monkeypatch.setattr(builder, "_fetch_body", fake_fetch)
    with pytest.raises(RuntimeError, match="2060"):
        builder.build_pre_release(tmp_path)
    assert not (tmp_path / "asteroid_shard_000.bsp").exists()
    assert CATALOG_ID == "moira-asteroids-wheel"
```

- [ ] **Step 2: Run those two tests and confirm they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_builder_rejects_horizons_name_mismatch tests/unit/test_wheel_asteroid_catalog.py::test_builder_refuses_to_write_when_a_body_fails -v`

Expected: FAIL because `scripts/build_wheel_asteroid_catalog.py` does not exist.

- [ ] **Step 3: Implement the builder**

`scripts/build_wheel_asteroid_catalog.py` must:

1. Add repo root to `sys.path`.
2. Load `scripts/build_unified_asteroid_catalog.py` via `importlib` and reuse `_fetch_body`, `_verify`, `WINDOW`, `STEP_DAYS`, `WINDOW_SIZE`, `CENTER`, `FRAME`, `THROTTLE_S`, `HORIZONS_URL`.
3. Import `write_spk_type13` from `moira.daf_writer`.
4. Import `load_targets`, `CATALOG_ID`, `TARGETS_PATH` from `moira._wheel_asteroid_catalog`.
5. `build_pre_release(output_dir: Path) -> Path`:
   - `output_dir.mkdir(parents=True, exist_ok=True)`
   - Fetch every roster body. If Horizons `name` does not contain the frozen name casefold, raise `RuntimeError`.
   - If any fetch fails, raise `RuntimeError` listing the failed MPC numbers. Do **not** write a shard.
   - Write one kernel with `write_spk_type13(output_dir / "asteroid_shard_000.bsp", bodies=writable, locifn="MOIRA WHEEL ASTEROID CATALOG")`.
   - Verify node round-trip with `_verify`.
   - Write `asteroid_shard_000.metadata.json` in the same record shape the unified builder uses (`shard`, `kernel`, `kernel_bytes`, `window`, `step_days`, `window_size`, `records`, `failures`, `naif_map`).
   - Write pre-release `manifest.json` with `catalog_id` = `moira-asteroids-wheel`, `source` = `MOIRA WHEEL ASTEROID CATALOG (JPL Horizons)`, same provenance/sampling keys as the unified manifest, `body_count` 25, `shard_count` 1, one shard entry `index` 0 / `path` `asteroid_shard_000.bsp` / `bodies` in NAIF order. **Do not** write `release` or `catalog_version` (prepare adds those).
   - Copy `TARGETS_PATH` to `output_dir / "targets.json"`.
   - Sleep `THROTTLE_S` between Horizons calls.
6. CLI: `python scripts/build_wheel_asteroid_catalog.py --out DIR` (default `build/asteroids-wheel-src`).

- [ ] **Step 4: Re-run the builder unit tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py -v`

Expected: PASS for roster + both builder tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_wheel_asteroid_catalog.py tests/unit/test_wheel_asteroid_catalog.py
git commit -m "feat(kernels): add wheel asteroid catalog builder"
```

---

### Task 3: Build, finalize, and commit catalog `2026.08.14.1`

**Files:**
- Create: the six generated files under `moira/kernels/asteroids_wheel/` listed in the file map
- Test: `tests/unit/test_wheel_asteroid_catalog.py`

**Interfaces:**
- Consumes: `build_pre_release`, `moira.small_body_catalog_release.prepare_release` / CLI
- Produces: committed release directory that `verify_release` accepts

- [ ] **Step 1: Add the verify_release test (it will fail until artifacts exist)**

```python
from moira._wheel_asteroid_catalog import CATALOG_DIR, CATALOG_ID, CATALOG_VERSION
from moira.small_body_catalog_release import verify_release


def test_committed_wheel_catalog_verifies() -> None:
    verification = verify_release(CATALOG_DIR)
    assert verification.catalog_id == CATALOG_ID
    assert verification.catalog_version == CATALOG_VERSION
    assert verification.shard_count == 1
    assert verification.body_count == 25
    assert (CATALOG_DIR / "asteroid_shard_000.bsp").is_file()
```

- [ ] **Step 2: Run it and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_committed_wheel_catalog_verifies -v`

Expected: FAIL (`verify_release` cannot find a finalized manifest / shard).

- [ ] **Step 3: Build the pre-release from Horizons**

This is the one network step. From `C:\dev\moira`:

```bash
.\.venv\Scripts\python.exe scripts/build_wheel_asteroid_catalog.py --out build/asteroids-wheel-src
```

Expected: 25 `[OK]` lines, `asteroid_shard_000.bsp` about 46,090,240 bytes, pre-release `manifest.json` with `catalog_id` `moira-asteroids-wheel` and no `release` key. If any body fails, stop and fix; do not commit a 24-body shard.

- [ ] **Step 4: Finalize the release**

```bash
.\.venv\Scripts\python.exe -m moira.small_body_catalog_release prepare build/asteroids-wheel-src build/asteroids-wheel-2026.08.14.1 --catalog-id moira-asteroids-wheel --catalog-version 2026.08.14.1 --license LICENSE --notice moira/kernels/SMALL_BODY_CATALOG_NOTICE.md --support-file targets.json
```

Then copy every file from `build/asteroids-wheel-2026.08.14.1/` into `moira/kernels/asteroids_wheel/`, replacing generated files but keeping the same `targets.json` bytes (they must match the support file).

- [ ] **Step 5: Re-run verify test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_committed_wheel_catalog_verifies -v`

Expected: PASS

- [ ] **Step 6: Commit the immutable catalog**

```bash
git add moira/kernels/asteroids_wheel tests/unit/test_wheel_asteroid_catalog.py
git commit -m "feat(kernels): commit moira-asteroids-wheel 2026.08.14.1"
```

Do not add `build/` .

---

### Task 4: Package the wheel catalog in the distribution

**Files:**
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]`)
- Test: `tests/unit/test_wheel_asteroid_catalog.py`

**Interfaces:**
- Consumes: committed `asteroids_wheel` files
- Produces: setuptools includes json, bsp, SHA256SUMS, LICENSE, NOTICE.md from that directory only

- [ ] **Step 1: Write the package-data test**

```python
from importlib.resources import files

from moira._wheel_asteroid_catalog import CATALOG_ID
from moira.small_body_catalog_release import verify_release


def test_package_data_exposes_wheel_catalog_bsp() -> None:
    root = files("moira") / "kernels" / "asteroids_wheel"
    assert (root / "asteroid_shard_000.bsp").is_file()
    assert (root / "SHA256SUMS").is_file()
    verification = verify_release(root)
    assert verification.catalog_id == CATALOG_ID
```

If `importlib.resources.files` returns a traversable that `verify_release` cannot take, resolve with `Path(str(root))` only when that path exists on disk (editable install). That is the local/dev case this test covers.

- [ ] **Step 2: Run it**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_package_data_exposes_wheel_catalog_bsp -v`

Expected: may already PASS on an editable tree because files are on disk. Still add the globs so a real wheel includes them.

- [ ] **Step 3: Update package-data**

In `pyproject.toml` keep `"kernels/**/*.json"` and add:

```toml
"kernels/asteroids_wheel/*.json",
"kernels/asteroids_wheel/*.bsp",
"kernels/asteroids_wheel/SHA256SUMS",
"kernels/asteroids_wheel/LICENSE",
"kernels/asteroids_wheel/NOTICE.md",
```

Do not add `kernels/**/*.bsp`.

- [ ] **Step 4: Re-run the package-data test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_package_data_exposes_wheel_catalog_bsp -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/unit/test_wheel_asteroid_catalog.py
git commit -m "build: include asteroids_wheel catalog in package data"
```

---

### Task 5: Discovery admits the wheel catalog and still skips the 10,025 metadata manifest

**Files:**
- Test: `tests/unit/test_wheel_asteroid_catalog.py`
- Modify: none unless a test fixture hard-codes “no package manifests”

**Interfaces:**
- Consumes: `find_all_small_body_manifests`, `CATALOG_DIR`
- Produces: no API change

- [ ] **Step 1: Write the discovery test**

```python
from pathlib import Path

import moira._kernel_paths as kernel_paths
from moira._wheel_asteroid_catalog import CATALOG_DIR


def test_package_search_root_admits_wheel_catalog_and_skips_metadata_only_10025(
    monkeypatch,
) -> None:
    package_kernels = Path(__file__).resolve().parents[2] / "moira" / "kernels"
    monkeypatch.setattr(kernel_paths, "kernel_search_dirs", lambda: (package_kernels,))
    monkeypatch.delenv(kernel_paths.SOVEREIGN_SMALL_BODY_MANIFEST_ENV, raising=False)

    found = kernel_paths.find_all_small_body_manifests()
    assert CATALOG_DIR / "manifest.json" in found
    assert package_kernels / "asteroids" / "manifest.json" not in found
```

- [ ] **Step 2: Run it**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py::test_package_search_root_admits_wheel_catalog_and_skips_metadata_only_10025 -v`

Expected: PASS with no code change if Task 3 artifacts are present. If it fails because the 10,025 manifest is admitted, stop: a shard was placed in `moira/kernels/asteroids/` and must be removed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_wheel_asteroid_catalog.py
git commit -m "test(kernels): admit wheel catalog without the 10025 metadata manifest"
```

---

### Task 6: Honest `moira-download-kernels`

**Files:**
- Modify: `moira/download_kernels.py`
- Test: `tests/unit/test_download_kernels_honesty.py`

**Interfaces:**
- Consumes: `verify_release`, `CATALOG_DIR`, `CATALOG_ID`, `CATALOG_VERSION`
- Produces: `list_kernels()` prints the wheel catalog and never prints `centaurs.bsp` / `minor_bodies.bsp` as bundled

- [ ] **Step 1: Write the failing honesty tests**

```python
from __future__ import annotations

from moira.download_kernels import _REGISTRY, list_kernels
from moira._wheel_asteroid_catalog import CATALOG_ID, CATALOG_VERSION


def test_registry_does_not_offer_centaurs_or_minor_bodies() -> None:
    names = {entry["filename"] for entry in _REGISTRY}
    assert "centaurs.bsp" not in names
    assert "minor_bodies.bsp" not in names


def test_jpl_small_body_entries_do_not_claim_chiron(capsys) -> None:
    asteroids = next(entry for entry in _REGISTRY if entry["filename"] == "asteroids.bsp")
    sb441 = next(entry for entry in _REGISTRY if entry["filename"] == "sb441-n373s.bsp")
    for entry in (asteroids, sb441):
        blob = f"{entry['description']} {entry.get('filename', '')}".lower()
        assert "do not install chiron" in blob or "does not install chiron" in blob
        assert "not a substitute" in blob


def test_list_kernels_reports_wheel_catalog_and_omits_ghost_bundled(capsys) -> None:
    list_kernels()
    text = capsys.readouterr().out
    assert CATALOG_ID in text
    assert CATALOG_VERSION in text
    assert "OK (wheel)" in text
    assert "centaurs.bsp" not in text
    assert "minor_bodies.bsp" not in text
```

- [ ] **Step 2: Run them and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_download_kernels_honesty.py -v`

Expected: FAIL on `list_kernels` still printing `centaurs.bsp` and on JPL blurbs.

- [ ] **Step 3: Edit `moira/download_kernels.py`**

- Replace the module docstring so it no longer says `centaurs.bsp` / `minor_bodies.bsp` ship in the wheel.
- Change the `asteroids.bsp` description to: `Generic JPL 300-asteroid kernel. Does not install Chiron and is not a substitute for either Moira catalog.`
- Change the `sb441-n373s.bsp` description to: `Optional JPL small-body kernel. Does not install Chiron and is not a substitute for either Moira catalog.`
- Delete the `bundled = ["centaurs.bsp", "minor_bodies.bsp"]` loop in `list_kernels`.
- After the registry rows, verify `CATALOG_DIR` with `verify_release` and print:

```
  moira-asteroids-wheel 2026.08.14.1  OK (wheel)    <path>
```

or `MISSING` if verification fails. Import `CATALOG_DIR`, `CATALOG_ID`, `CATALOG_VERSION` from `moira._wheel_asteroid_catalog`.

- [ ] **Step 4: Re-run the honesty tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_download_kernels_honesty.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add moira/download_kernels.py tests/unit/test_download_kernels_honesty.py
git commit -m "fix(kernels): stop advertising missing bundled centaur kernels"
```

---

### Task 7: Missing-segment error names the full catalog

**Files:**
- Modify: `moira/asteroids.py` (`asteroid_at`)
- Test: `tests/unit/test_asteroid_missing_segment_message.py`

**Interfaces:**
- Consumes: `FULL_CATALOG_VERSION`, `EPHEMERIDES_URL`, asteroid identity map
- Produces: `asteroid_at` still raises `KeyError`; message for a known catalog identity names `2026.08.12.1` and the ephemerides URL and does not mention `centaurs.bsp`

- [ ] **Step 1: Write the failing test**

Use a reader that has Earth/Sun if needed but no small-body segments. The cheapest path is to mock `_asteroid_apparent_equatorial_vector` to raise the current `KeyError`.

```python
import pytest

from moira.asteroids import asteroid_at
from moira._wheel_asteroid_catalog import EPHEMERIDES_URL, FULL_CATALOG_VERSION


def test_known_catalog_miss_names_full_archive(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise KeyError("No segment found for center=0, target=2307261")

    monkeypatch.setattr("moira.asteroids._asteroid_apparent_equatorial_vector", boom)
    monkeypatch.setattr(
        "moira.asteroids.get_active_reader",
        lambda: object(),
    )
    with pytest.raises(KeyError, match=FULL_CATALOG_VERSION) as captured:
        asteroid_at("Mani", 2448058.0, reader=object())
    text = str(captured.value)
    assert EPHEMERIDES_URL in text
    assert "centaurs.bsp" not in text
    assert "2307261" in text or "Mani" in text
```

`Mani` is merged into `ASTEROID_NAIF` from `moira/data/asteroid_catalog_naif.json` (`2307261`) and is not in the wheel roster.

- [ ] **Step 2: Run the test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_asteroid_missing_segment_message.py -v`

Expected: FAIL because the re-raised message is still `No segment found for center=0, target=...`.

- [ ] **Step 3: Wrap the KeyError in `asteroid_at`**

In `moira/asteroids.py`, after resolving `name` / `naif_id`, wrap the apparent-vector call:

```python
from ._wheel_asteroid_catalog import EPHEMERIDES_URL, FULL_CATALOG_VERSION

try:
    xyz = _asteroid_apparent_equatorial_vector(...)
except KeyError as exc:
    raise KeyError(
        f"No loaded small-body kernel has {name} (NAIF {naif_id}). "
        f"Install asteroid catalog {FULL_CATALOG_VERSION} from {EPHEMERIDES_URL}"
    ) from exc
```

Do not change `_segments_for_pair` in `spk_reader.py` (that would rewrite planetary misses). Optionally refresh the four-kernel module docstring in `asteroids.py` if you are already in the file; do not delete `_TERTIARY_KERNEL_PATH`.

- [ ] **Step 4: Re-run the test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_asteroid_missing_segment_message.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add moira/asteroids.py tests/unit/test_asteroid_missing_segment_message.py
git commit -m "fix(asteroids): name the 10025 catalog when a body is not loaded"
```

---

### Task 8: Positions work from the wheel catalog alone

**Files:**
- Test: `tests/integration/test_wheel_asteroid_catalog_positions.py`

**Interfaces:**
- Consumes: committed wheel catalog + whatever planetary kernel the suite already uses
- Produces: no production API change

- [ ] **Step 1: Write the integration test**

```python
from __future__ import annotations

import datetime as dt

import pytest

from moira.asteroids import asteroid_at
from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import KernelPool, SpkReader, reset_singleton, set_kernel_path
from moira._spk_body_kernel import small_body_readers_from_manifest
from moira._wheel_asteroid_catalog import CATALOG_DIR


pytestmark = pytest.mark.skipif(
    find_planetary_kernel() is None,
    reason="planetary kernel required",
)


def test_wheel_catalog_computes_chiron_ceres_eris_amor() -> None:
    reset_singleton()
    planetary = find_planetary_kernel()
    assert planetary is not None
    set_kernel_path(str(planetary))
    pool = KernelPool()
    pool.add(SpkReader(planetary))
    for reader in small_body_readers_from_manifest(CATALOG_DIR / "manifest.json"):
        pool.add(reader)
    when = dt.datetime(1990, 6, 15, 12, 0, tzinfo=dt.timezone.utc)
    # asteroid_at wants jd_ut; use the same instant the issue used.
    from moira.julian import jd_from_datetime

    jd_ut = jd_from_datetime(when)
    for name in ("Chiron", "Ceres", "Eris", "Amor"):
        pos = asteroid_at(name, jd_ut, reader=pool)
        assert pos.name == name
        assert 0.0 <= pos.longitude < 360.0
```

`jd_from_datetime` is the canonical helper in `moira/julian.py`. Building an explicit `KernelPool` keeps this test independent of whatever other catalogs the developer machine has under `~/.moira/kernels/`.

- [ ] **Step 2: Run the test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/integration/test_wheel_asteroid_catalog_positions.py -v`

Expected: PASS when a planetary kernel is installed. SKIP is acceptable in kernel-free CI only if existing asteroid integration tests also skip; do not skip when the kernel is present.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_wheel_asteroid_catalog_positions.py
git commit -m "test(kernels): compute Chiron from the wheel catalog"
```

---

### Task 9: Documentation

**Files:**
- Modify: `README.md`
- Modify: `moira/centaurs.py`
- Modify: `moira/tno.py`
- Modify: `moira/classical_asteroids.py`
- Modify: `moira/constants.py` (line with `CHIRON     = "Chiron"          # requires separate kernel`)
- Modify: `wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md` (the `SE_CHIRON` row)

**Interfaces:**
- Consumes: catalog identity strings
- Produces: no runtime change

- [ ] **Step 1: Edit the docs**

`README.md` small-body section: the wheel ships `moira-asteroids-wheel` `2026.08.14.1` (25 named bodies, including Chiron). `moira-download-kernels` still does not fetch the 10,025-body catalog. The GUI/JPL files still do not substitute for either catalog.

`moira/centaurs.py`: delete “`centaurs.bsp` must be present (generated by `scripts/build_centaur_kernel.py`)”. Say positions come from any admitted small-body reader that has the NAIF ID; the wheel catalog is sufficient.

`moira/tno.py`: delete the `sb441-n373s.bsp` requirement sentence. Same admission rule.

`moira/classical_asteroids.py`: delete the `asteroids.bsp` / `sb441-n373s.bsp` requirement sentence.

`moira/constants.py`: change the Chiron comment to `# named centaur; wheel catalog or 2026.08.12.1`.

`wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md`: `SE_CHIRON` → `Body.CHIRON` (included in the wheel catalog). Do not edit `moira.wiki/` generated copies.

- [ ] **Step 2: Grep for leftover bundled-kernel claims**

Run: search the repo (not `docs/superpowers`, not `scripts/archive`) for `already ship inside the moira wheel` and `OK (bundled)`.

Expected: no remaining hits in `moira/` or `README.md`.

- [ ] **Step 3: Commit**

```bash
git add README.md moira/centaurs.py moira/tno.py moira/classical_asteroids.py moira/constants.py wiki/02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md
git commit -m "docs: describe the wheel asteroid catalog and retire centaurs.bsp"
```

---

### Task 10: Version 6.2.1 and changelog

**Files:**
- Modify: `pyproject.toml` (`version = "6.2.0"` → `6.2.1`)
- Modify: `moira/facade.py` (`__version__ = "6.2.0"` → `6.2.1`)
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: none
- Produces: package version `6.2.1`

- [ ] **Step 1: Add the changelog section under `## [Unreleased]`**

Insert a new `## [6.2.1] - 2026-08-14` (use the actual ship date if later) with:

```markdown
## [6.2.1] - 2026-08-14

### Added
- Wheel catalog `moira-asteroids-wheel` `2026.08.14.1`: 25 named small bodies
  (classicals, six centaurs including Chiron, named TNOs, Eris/Sedna/Haumea/Makemake)
  as one Type-13 shard shipped in the `moira-astro` wheel.

### Fixed
- Clean `pip install` can compute Chiron without `centaurs.bsp`.
- `moira-download-kernels` no longer lists `centaurs.bsp` and `minor_bodies.bsp`
  as bundled wheel files.

### Changed
- Missing-segment errors for known asteroid identities name catalog
  `2026.08.12.1` and https://moira-astro.com/ephemerides.
```

- [ ] **Step 2: Bump both version strings to `6.2.1`**

- [ ] **Step 3: Confirm the import version**

Run: `.\.venv\Scripts\python.exe -c "from moira.facade import __version__; print(__version__)"`

Expected: `6.2.1`

- [ ] **Step 4: Run the focused suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_wheel_asteroid_catalog.py tests/unit/test_download_kernels_honesty.py tests/unit/test_asteroid_missing_segment_message.py tests/integration/test_wheel_asteroid_catalog_positions.py tests/unit/test_kernel_paths_small_body_manifests.py tests/unit/test_small_body_catalog_release.py -v`

Expected: all PASS (integration may SKIP without a planetary kernel).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml moira/facade.py CHANGELOG.md
git commit -m "release: moira-astro 6.2.1 wheel asteroid catalog"
```

---

### Task 11: Issue #17 close text (after PyPI publish)

**Files:** none in-repo

**Interfaces:**
- Consumes: published `moira-astro==6.2.1`
- Produces: GitHub comment + close on TheDaniel166/moira#17

Do **not** close the issue until 6.2.1 is on PyPI. This task is the last human/release step.

- [ ] **Step 1: Confirm the published wheel contains the catalog**

```bash
python -m venv %TEMP%\moira-621 && %TEMP%\moira-621\Scripts\pip install moira-astro==6.2.1
%TEMP%\moira-621\Scripts\python -c "from importlib.resources import files; print((files('moira')/'kernels'/'asteroids_wheel'/'asteroid_shard_000.bsp').is_file())"
```

Expected: `True`

- [ ] **Step 2: Comment and close #17**

Comment body:

```markdown
Fixed in `moira-astro==6.2.1`.

`centaurs.bsp` was a leftover from the pre-4.0.0 four-kernel layout. It never
shipped in the wheel and is not coming back. Chiron and 24 other named bodies
now ship as catalog `moira-asteroids-wheel` `2026.08.14.1` (one Type-13 shard
inside the wheel). After `pip install moira-astro` and a planetary kernel:

```python
from datetime import datetime, timezone
from moira import Moira, Body
print(Moira().chart(datetime(1990, 6, 15, 12, tzinfo=timezone.utc), bodies=[Body.CHIRON]))
```

The 10,025-body catalog `2026.08.12.1` remains the full source:
https://moira-astro.com/ephemerides
```

State: closed / completed.

---

## Spec coverage

| Spec section | Task |
| --- | --- |
| Locked roster | 1 |
| Builder + same Horizons policy + refuse short catalog | 2 |
| Finalize, commit, never call Horizons from wheel build | 3 |
| Package-data globs, no `kernels/**/*.bsp` | 4 |
| Second complete catalog; 10,025 metadata not admitted | 5 |
| download_kernels honesty + JPL blurbs | 6 |
| Missing-segment names `2026.08.12.1` | 7 |
| Chiron/Ceres/Eris/Amor compute | 8 |
| README, oracle module docs, CHIRON comment, Swiss map | 9 |
| Version 6.2.1 | 10 |
| Close #17 after publish | 11 |
| Do not revive `centaurs.bsp` | 6, 11 |
| Do not rewrite `_TERTIARY_KERNEL_PATH` | 7 (explicit) |
