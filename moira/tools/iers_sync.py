"""
moira.tools.iers_sync — IERS Synchronization Engine
====================================================
Governs the automated ingestion of Earth Orientation Parameters (EOP) and
Leap Second announcements from the IERS (International Earth Rotation and
Reference Systems Service).

This tool ensures that Moira's "Truth-First" time scales remain synchronized
with institutional reality without requiring manual code edits when the
Earth's rotation changes.

Sources (tried in order; the winning source and its SHA-256 are recorded in
every output header, and a non-primary source is labelled ``fallback``):
- Leap Seconds: https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat, then
  https://data.iana.org/time-zones/data/leap-seconds.list
- EOP: https://datacenter.iers.org/products/eop/rapid/standard/csv/finals2000A.all.csv,
  then https://maia.usno.navy.mil/ser7/finals2000A.all

Failure policy: a payload is accepted only if it parses, is strictly
increasing, and reaches today's epoch.  If every source fails, the existing
data files are left untouched and an error is raised; UT1 = UTC is never
substituted.  Files are written only after every product has been fetched and
validated, each via an atomic replace.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_LEAP_SECONDS_PY = _PACKAGE_ROOT / "data" / "leap_seconds.py"
_EOP_DATA_TXT = _PACKAGE_ROOT / "data" / "iers_eop.txt"
_POLAR_MOTION_TXT = _PACKAGE_ROOT / "data" / "iers_polar_motion.txt"

_URL_LEAP_SECONDS = "https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat"
_URL_LEAP_SECONDS_MIRROR = "https://data.iana.org/time-zones/data/leap-seconds.list"
_URL_FINALS_ALL = "https://datacenter.iers.org/products/eop/rapid/standard/csv/finals2000A.all.csv"
_URL_FINALS_ALL_MIRROR = "https://maia.usno.navy.mil/ser7/finals2000A.all"

LEAP_SOURCES: tuple[str, ...] = (_URL_LEAP_SECONDS, _URL_LEAP_SECONDS_MIRROR)
FINALS_SOURCES: tuple[str, ...] = (_URL_FINALS_ALL, _URL_FINALS_ALL_MIRROR)

# Rows needed for a plausible finals file (1973 onward is ~20k daily rows).
_MIN_EOP_ROWS = 10000
# |UT1-UTC| bound enforced by the packaged loader (moira.julian.EOPRegistry).
_MAX_ABS_DUT1_S = 1.0

Fetcher = Callable[[str], str]


class SyncError(RuntimeError):
    """Raised when no source yields a valid payload."""


@dataclass(frozen=True)
class Fetched:
    text: str
    url: str
    sha256: str
    status: str  # "primary" or "fallback"


@dataclass(frozen=True)
class EopRow:
    mjd: int
    x_pole: str | None
    y_pole: str | None
    dut1: str | None


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Moira-Sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _today_mjd(today: datetime.date | None = None) -> int:
    day = today or datetime.datetime.now(datetime.timezone.utc).date()
    return (day - datetime.date(1858, 11, 17)).days


def fetch_with_failover(
    sources: Sequence[str],
    parse: Callable[[str], object],
    fetch: Fetcher = fetch_url,
) -> tuple[Fetched, object]:
    """Return the first source whose payload both downloads and validates."""
    failures: list[str] = []
    for index, url in enumerate(sources):
        try:
            text = fetch(url)
            parsed = parse(text)
        except Exception as exc:  # noqa: BLE001 - every failure moves to the next mirror
            failures.append(f"{url}: {exc}")
            continue
        digest = hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
        status = "primary" if index == 0 else "fallback"
        return Fetched(text, url, digest, status), parsed
    raise SyncError("all sources failed: " + " | ".join(failures))


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------

def parse_leap_seconds(text: str) -> list[tuple[float, float]]:
    """Parse IERS ``Leap_Second.dat`` or the IANA/NTP ``leap-seconds.list``."""
    entries: list[tuple[float, float]] = []
    iers = re.findall(r"^\s*(\d+\.\d+)\s+\d+\s+\d+\s+\d+\s+(\d+)", text, re.MULTILINE)
    if iers:
        entries = [(float(m) + 2400000.5, float(o)) for m, o in iers]
    else:
        # NTP seconds since 1900-01-01; 2208988800 s to the Unix epoch, MJD 40587.
        for ntp, offset in re.findall(r"^\s*(\d{10})\s+(\d+)\b", text, re.MULTILINE):
            mjd = (int(ntp) - 2208988800) / 86400.0 + 40587.0
            entries.append((mjd + 2400000.5, float(offset)))
    if not entries:
        raise ValueError("no leap second entries found")
    jds = [jd for jd, _ in entries]
    if jds != sorted(set(jds)):
        raise ValueError("leap second epochs are not strictly increasing")
    if any(b < a for (_, a), (_, b) in zip(entries, entries[1:])):
        raise ValueError("TAI-UTC decreased between entries")
    return entries


def _mjd_key(text: str) -> int:
    value = float(text)
    if not value.is_integer():
        raise ValueError(f"non-integer MJD {text!r}")
    return int(value)


def parse_finals(
    text: str, *, today: datetime.date | None = None, require_current: bool = True
) -> list[EopRow]:
    """Parse the IERS CSV or the USNO fixed-width ``finals2000A.all``."""
    lines = text.splitlines()
    rows: list[EopRow] = []
    if lines and ";" in lines[0]:
        header = [h.strip() for h in lines[0].split(";")]
        try:
            mjd_i = header.index("MJD")
            x_i = header.index("x_pole")
            y_i = header.index("y_pole")
            d_i = header.index("UT1-UTC")
        except ValueError as exc:
            raise ValueError("IERS CSV lacks MJD/x_pole/y_pole/UT1-UTC columns") from exc
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(";")]
            if len(parts) <= max(mjd_i, x_i, y_i, d_i) or not parts[mjd_i]:
                continue
            rows.append(
                EopRow(_mjd_key(parts[mjd_i]), parts[x_i] or None, parts[y_i] or None, parts[d_i] or None)
            )
    else:
        for line in lines:
            if len(line) < 68:
                continue
            mjd_s = line[7:15].strip()
            if not mjd_s:
                continue
            rows.append(
                EopRow(
                    _mjd_key(mjd_s),
                    line[18:27].strip() or None,
                    line[37:46].strip() or None,
                    line[58:68].strip() or None,
                )
            )
    if len(rows) < _MIN_EOP_ROWS:
        raise ValueError(f"only {len(rows)} rows; expected at least {_MIN_EOP_ROWS}")
    mjds = [r.mjd for r in rows]
    if any(b <= a for a, b in zip(mjds, mjds[1:])):
        raise ValueError("MJD values are not strictly increasing")
    for r in rows:
        if r.dut1 is not None and abs(float(r.dut1)) > _MAX_ABS_DUT1_S:
            raise ValueError(f"MJD {r.mjd}: |UT1-UTC| exceeds {_MAX_ABS_DUT1_S} s")
    if require_current:
        covered = [r.mjd for r in rows if r.dut1 is not None]
        if not covered or covered[-1] < _today_mjd(today):
            raise ValueError("payload does not reach the current epoch (stale)")
    return rows


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------

def _stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def render_leap_seconds(entries: list[tuple[float, float]], src: Fetched) -> str:
    lines = [
        '"""',
        "Moira — leap_seconds.py",
        f"Last Synchronized: {_stamp()}",
        f"Source: {src.url} ({src.status}; sha256 {src.sha256})",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "LEAP_SECONDS: list[tuple[float, float]] = [",
    ]
    lines += [f"    ({jd}, {offset})," for jd, offset in entries]
    lines.append("]")
    return "\n".join(lines) + "\n"


def render_eop_dut1(rows: list[EopRow], src: Fetched) -> str:
    extracted = [f"{r.mjd} {r.dut1}" for r in rows if r.dut1 is not None]
    if not extracted:
        raise ValueError("no UT1-UTC rows")
    head = [
        "# IERS EOP DUT1 (UT1-UTC) Data",
        f"# Source: {src.url}",
        f"# Source status: {src.status}; sha256 {src.sha256}",
        f"# Updated: {_stamp()}",
    ]
    return "\n".join(head + extracted) + "\n"


def render_polar_motion(rows: list[EopRow], src: Fetched) -> str:
    extracted: list[tuple[float, float, float]] = []
    for r in rows:
        if r.x_pole is None or r.y_pole is None:
            continue
        try:
            extracted.append((float(r.mjd), float(r.x_pole), float(r.y_pole)))
        except ValueError:
            continue
    if not extracted:
        raise ValueError("no polar motion rows")
    out = [
        "# IERS polar motion data (x_p, y_p)",
        f"# Source: {src.url}",
        f"# Source status: {src.status}; sha256 {src.sha256}",
        f"# Updated: {_stamp()}",
        f"# Data range (MJD): {extracted[0][0]:.1f} to {extracted[-1][0]:.1f}",
        "# License: IERS Datacenter source terms apply; retain source provenance when redistributing.",
        "# Format: MJD x_p_arcsec y_p_arcsec",
    ]
    out += [f"{m:.1f} {x:.6f} {y:.6f}" for m, x, y in extracted]
    return "\n".join(out) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def sync_all(
    fetch: Fetcher = fetch_url,
    *,
    today: datetime.date | None = None,
    write: bool = True,
) -> dict[Path, str]:
    """Fetch and validate every product, then write all files together."""
    leap_src, leap = fetch_with_failover(LEAP_SOURCES, parse_leap_seconds, fetch)
    eop_src, eop = fetch_with_failover(
        FINALS_SOURCES, lambda t: parse_finals(t, today=today), fetch
    )
    outputs = {
        _LEAP_SECONDS_PY: render_leap_seconds(leap, leap_src),  # type: ignore[arg-type]
        _EOP_DATA_TXT: render_eop_dut1(eop, eop_src),  # type: ignore[arg-type]
        _POLAR_MOTION_TXT: render_polar_motion(eop, eop_src),  # type: ignore[arg-type]
    }
    if write:
        for path, content in outputs.items():
            _atomic_write(path, content)
            print(f"  Successfully updated {path.relative_to(_PACKAGE_ROOT)}")
        for label, src in (("leap seconds", leap_src), ("EOP", eop_src)):
            print(f"  {label}: {src.status} source {src.url}")
    return outputs


def update_leap_seconds() -> None:
    src, entries = fetch_with_failover(LEAP_SOURCES, parse_leap_seconds)
    _atomic_write(_LEAP_SECONDS_PY, render_leap_seconds(entries, src))  # type: ignore[arg-type]


def update_eop_dut1() -> None:
    src, rows = fetch_with_failover(FINALS_SOURCES, parse_finals)
    _atomic_write(_EOP_DATA_TXT, render_eop_dut1(rows, src))  # type: ignore[arg-type]


def update_polar_motion() -> None:
    src, rows = fetch_with_failover(FINALS_SOURCES, parse_finals)
    _atomic_write(_POLAR_MOTION_TXT, render_polar_motion(rows, src))  # type: ignore[arg-type]


def main() -> int:
    try:
        sync_all()
    except SyncError as exc:
        print(f"\nSynchronization failed; existing data left untouched: {exc}")
        return 1
    print("\nSynchronization complete. The engine is now anchored to current IERS truth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
