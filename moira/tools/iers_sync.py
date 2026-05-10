"""
moira.tools.iers_sync — IERS Synchronization Engine
====================================================
Governs the automated ingestion of Earth Orientation Parameters (EOP) and
Leap Second announcements from the IERS (International Earth Rotation and
Reference Systems Service).

This tool ensures that Moira's "Truth-First" time scales remain synchronized
with institutional reality without requiring manual code edits when the
Earth's rotation changes.

Sources:
- Leap Seconds: https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat
- EOP (DUT1): https://datacenter.iers.org/products/eop/rapid/standard/csv/finals2000A.all.csv
"""

import urllib.request
import datetime
import re
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_LEAP_SECONDS_PY = _PACKAGE_ROOT / "data" / "leap_seconds.py"
_EOP_DATA_TXT = _PACKAGE_ROOT / "data" / "iers_eop.txt"
_POLAR_MOTION_TXT = _PACKAGE_ROOT / "data" / "iers_polar_motion.txt"

_URL_LEAP_SECONDS = "https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat"
_URL_FINALS_ALL = "https://datacenter.iers.org/products/eop/rapid/standard/csv/finals2000A.all.csv"

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Moira-Sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")

def update_leap_seconds():
    print(f"Syncing Leap Seconds from {_URL_LEAP_SECONDS}...")
    content = fetch_url(_URL_LEAP_SECONDS)
    
    # Extract entries: (MJD, Day, Month, Year, TAI-UTC)
    # Format: 41317.0    1  1 1972       10
    pattern = r"^\s*(\d+\.\d+)\s+\d+\s+\d+\s+\d+\s+(\d+)"
    matches = re.findall(pattern, content, re.MULTILINE)
    
    if not matches:
        raise ValueError("Could not find any leap second entries in the source data.")

    lines = [
        '"""',
        'Moira — leap_seconds.py',
        f'Last Synchronized: {datetime.datetime.now(datetime.timezone.utc).isoformat()}',
        f'Source: {_URL_LEAP_SECONDS}',
        '"""',
        '',
        'LEAP_SECONDS: list[tuple[float, float]] = ['
    ]
    
    for mjd_s, offset_s in matches:
        jd = float(mjd_s) + 2400000.5
        offset = float(offset_s)
        lines.append(f"    ({jd}, {offset}),")
    
    lines.append("]")
    
    with open(_LEAP_SECONDS_PY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Successfully updated {_LEAP_SECONDS_PY.relative_to(_PACKAGE_ROOT)}")

def update_eop_dut1():
    print(f"Syncing EOP (DUT1) from {_URL_FINALS_ALL}...")
    # Bulletin A/B Finals 2000A
    # Column 18: UT1-UTC (seconds)
    content = fetch_url(_URL_FINALS_ALL)
    rows = content.splitlines()
    
    # We take only a subset to keep the file size manageable (e.g., last 2 years + next 90 days predictions)
    # Format: MJD;Year;Month;Day;[type];x_pole;...;UT1-UTC;...
    header = rows[0].split(";")
    try:
        mjd_idx = header.index("MJD")
        dut1_idx = header.index("UT1-UTC")
    except ValueError:
        print("  Error: Could not find MJD or UT1-UTC columns in IERS CSV.")
        return

    extracted = []
    for row in rows[1:]:
        parts = row.split(";")
        if len(parts) <= dut1_idx: continue
        mjd_str = parts[mjd_idx].strip()
        dut1_str = parts[dut1_idx].strip()
        if mjd_str and dut1_str:
            extracted.append(f"{mjd_str} {dut1_str}")

    # Write as a simple MJD DUT1 space-delimited file
    with open(_EOP_DATA_TXT, "w", encoding="utf-8") as f:
        f.write(f"# IERS EOP DUT1 (UT1-UTC) Data\n")
        f.write(f"# Source: {_URL_FINALS_ALL}\n")
        f.write(f"# Updated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")
        f.write("\n".join(extracted) + "\n")
    print(f"  Successfully updated {_EOP_DATA_TXT.relative_to(_PACKAGE_ROOT)}")


def update_polar_motion():
    print(f"Syncing polar motion (x_p, y_p) from {_URL_FINALS_ALL}...")
    content = fetch_url(_URL_FINALS_ALL)
    rows = content.splitlines()

    header = rows[0].split(";")
    try:
        mjd_idx = header.index("MJD")
        x_idx = header.index("x_pole")
        y_idx = header.index("y_pole")
    except ValueError:
        print("  Error: Could not find MJD, x_pole, or y_pole columns in IERS CSV.")
        return

    extracted: list[tuple[float, float, float]] = []
    for row in rows[1:]:
        parts = row.split(";")
        if len(parts) <= max(mjd_idx, x_idx, y_idx):
            continue
        mjd_str = parts[mjd_idx].strip()
        x_str = parts[x_idx].strip()
        y_str = parts[y_idx].strip()
        if not mjd_str or not x_str or not y_str:
            continue
        try:
            extracted.append((float(mjd_str), float(x_str), float(y_str)))
        except ValueError:
            continue

    if not extracted:
        print("  Error: Could not parse any polar motion rows from IERS CSV.")
        return

    with open(_POLAR_MOTION_TXT, "w", encoding="utf-8") as f:
        f.write("# IERS polar motion data (x_p, y_p)\n")
        f.write(f"# Source: {_URL_FINALS_ALL}\n")
        f.write(f"# Updated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")
        f.write(
            f"# Data range (MJD): {extracted[0][0]:.1f} to {extracted[-1][0]:.1f}\n"
        )
        f.write(
            "# License: IERS Datacenter source terms apply; retain source provenance when redistributing.\n"
        )
        f.write("# Format: MJD x_p_arcsec y_p_arcsec\n")
        for mjd, x_p, y_p in extracted:
            f.write(f"{mjd:.1f} {x_p:.6f} {y_p:.6f}\n")
    print(f"  Successfully updated {_POLAR_MOTION_TXT.relative_to(_PACKAGE_ROOT)}")

def main():
    try:
        update_leap_seconds()
        update_eop_dut1()
        update_polar_motion()
        print("\nSynchronization complete. The engine is now anchored to current IERS truth.")
    except Exception as e:
        print(f"\nCritical Error during synchronization: {e}")

if __name__ == "__main__":
    main()
