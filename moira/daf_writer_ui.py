"""
Moira - daf_writer_ui.py
Tkinter GUI for building custom SPK type 13 kernels using moira.daf_writer.

Launch:
    moira-daf-writer
    python -m moira.daf_writer_ui
    python moira/daf_writer_ui.py
"""

import csv
import json
import sys
import tkinter as tk
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    _THIS_FILE = Path(__file__).resolve()
    _PROJECT_ROOT = _THIS_FILE.parent.parent
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))

    from moira._kernel_paths import user_kernels_dir
    from moira.daf_writer import write_spk_type13
else:
    from ._kernel_paths import user_kernels_dir
    from .daf_writer import write_spk_type13


_REQUIRED_COLUMNS = (
    "naif_id",
    "jd_tdb",
    "x_km",
    "y_km",
    "z_km",
    "vx_km_s",
    "vy_km_s",
    "vz_km_s",
)

_OPTIONAL_COLUMNS = (
    "name",
    "center",
    "frame",
    "window_size",
)

_TEMPLATE_HEADER = list(_REQUIRED_COLUMNS + _OPTIONAL_COLUMNS)
_HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
_SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"

# Curated major bodies: planets, major moons, dwarf planets.
# These are not in SBDB so we keep them locally.
_MAJOR_BODIES: list[dict] = [
    {"full_name": "Sun", "name": "Sun", "pdes": "", "type": "Star", "naif": 10, "command": "10"},
    {"full_name": "Mercury", "name": "Mercury", "pdes": "", "type": "Planet", "naif": 199, "command": "199"},
    {"full_name": "Venus", "name": "Venus", "pdes": "", "type": "Planet", "naif": 299, "command": "299"},
    {"full_name": "Earth", "name": "Earth", "pdes": "", "type": "Planet", "naif": 399, "command": "399"},
    {"full_name": "Moon (Earth)", "name": "Moon", "pdes": "", "type": "Satellite", "naif": 301, "command": "301"},
    {"full_name": "Mars", "name": "Mars", "pdes": "", "type": "Planet", "naif": 499, "command": "499"},
    {"full_name": "Phobos", "name": "Phobos", "pdes": "", "type": "Satellite", "naif": 401, "command": "401"},
    {"full_name": "Deimos", "name": "Deimos", "pdes": "", "type": "Satellite", "naif": 402, "command": "402"},
    {"full_name": "Jupiter", "name": "Jupiter", "pdes": "", "type": "Planet", "naif": 599, "command": "599"},
    {"full_name": "Io", "name": "Io", "pdes": "", "type": "Satellite", "naif": 501, "command": "501"},
    {"full_name": "Europa", "name": "Europa", "pdes": "", "type": "Satellite", "naif": 502, "command": "502"},
    {"full_name": "Ganymede", "name": "Ganymede", "pdes": "", "type": "Satellite", "naif": 503, "command": "503"},
    {"full_name": "Callisto", "name": "Callisto", "pdes": "", "type": "Satellite", "naif": 504, "command": "504"},
    {"full_name": "Saturn", "name": "Saturn", "pdes": "", "type": "Planet", "naif": 699, "command": "699"},
    {"full_name": "Titan", "name": "Titan", "pdes": "", "type": "Satellite", "naif": 606, "command": "606"},
    {"full_name": "Enceladus", "name": "Enceladus", "pdes": "", "type": "Satellite", "naif": 602, "command": "602"},
    {"full_name": "Uranus", "name": "Uranus", "pdes": "", "type": "Planet", "naif": 799, "command": "799"},
    {"full_name": "Titania", "name": "Titania", "pdes": "", "type": "Satellite", "naif": 703, "command": "703"},
    {"full_name": "Oberon", "name": "Oberon", "pdes": "", "type": "Satellite", "naif": 704, "command": "704"},
    {"full_name": "Neptune", "name": "Neptune", "pdes": "", "type": "Planet", "naif": 899, "command": "899"},
    {"full_name": "Triton", "name": "Triton", "pdes": "", "type": "Satellite", "naif": 801, "command": "801"},
    {"full_name": "Pluto", "name": "Pluto", "pdes": "", "type": "Dwarf Planet", "naif": 999, "command": "999"},
    {"full_name": "Charon", "name": "Charon", "pdes": "", "type": "Satellite", "naif": 901, "command": "901"},
    {"full_name": "Ceres (1)", "name": "Ceres", "pdes": "1", "type": "Dwarf Planet", "naif": 2000001, "command": "2000001"},
    {"full_name": "Eris (136199)", "name": "Eris", "pdes": "136199", "type": "Dwarf Planet", "naif": 2136199, "command": "2136199"},
    {"full_name": "Makemake (136472)", "name": "Makemake", "pdes": "136472", "type": "Dwarf Planet", "naif": 2136472, "command": "2136472"},
    {"full_name": "Haumea (136108)", "name": "Haumea", "pdes": "136108", "type": "Dwarf Planet", "naif": 2136108, "command": "2136108"},
]


def _search_sbdb(query: str, kind: str = "all") -> list[dict]:
    """
    Search the JPL Small Body Database for asteroids and comets by name or designation.

    Returns a list of dicts with keys:
        full_name, name, pdes, type, naif (int), command (str)

    kind: 'all', 'asteroid', 'comet'
    """
    params: dict[str, str] = {
        "sb-name": query,
        "fuzzy": "1",
        "fields": "spkid,full_name,pdes,name,orbit_class",
        "limit": "80",
    }
    if kind == "asteroid":
        params["sb-kind"] = "a"
    elif kind == "comet":
        params["sb-kind"] = "c"

    url = _SBDB_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    fields: list[str] = data.get("fields", [])
    raw_rows: list = data.get("data") or []

    results: list[dict] = []
    for raw in raw_rows:
        rec = dict(zip(fields, raw))

        spkid_raw = str(rec.get("spkid") or "").strip()
        pdes = str(rec.get("pdes") or "").strip()
        name = str(rec.get("name") or "").strip()
        full_name = str(rec.get("full_name") or "").strip()

        oc = rec.get("orbit_class")
        body_type = (
            oc.get("name", "Small Body") if isinstance(oc, dict) else str(oc or "Small Body")
        )

        # Comets: pdes ends with P or contains P/
        is_comet = bool(pdes) and (
            pdes.endswith("P") or "P/" in pdes or "/P" in pdes or "C/" in pdes
        )

        try:
            naif = int(spkid_raw)
        except ValueError:
            naif = 0

        if is_comet:
            command = f"DES={pdes};NOFRAG;CAP"
        elif naif:
            command = str(naif)
        else:
            command = pdes or full_name

        results.append(
            {
                "full_name": full_name,
                "name": name or pdes or full_name,
                "pdes": pdes,
                "type": body_type,
                "naif": naif,
                "command": command,
            }
        )

    return results


@dataclass
class _KernelPreview:
    naif_id: int
    name: str
    center: int
    frame: int
    window_size: int
    rows: int
    jd_start: float
    jd_end: float


def _jd_to_cal(jd: float) -> str:
    """Convert JD to Horizons calendar string 'YYYY-MMM-DD'."""
    jd2 = jd + 0.5
    z = int(jd2)
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{year}-{months[month - 1]}-{day:02d}"


def _quoted_horizons_command(command: str) -> str:
    """Ensure Horizons COMMAND value is single-quoted for API requests."""
    cmd = command.strip()
    if not cmd:
        raise ValueError("Horizons COMMAND cannot be empty.")
    if cmd.startswith("'") and cmd.endswith("'") and len(cmd) >= 2:
        return cmd
    return f"'{cmd}'"


def _fetch_horizons_vectors(
    command: str,
    start_jd: float,
    end_jd: float,
    step_days: int,
) -> list[tuple[float, float, float, float, float, float, float]]:
    """
    Fetch vector rows from Horizons as tuples:
    (jd_tdb, x_km, y_km, z_km, vx_km_s, vy_km_s, vz_km_s)
    """
    params = {
        "format": "text",
        "COMMAND": _quoted_horizons_command(command),
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": "500@10",
        "REF_PLANE": "FRAME",
        "START_TIME": _jd_to_cal(start_jd),
        "STOP_TIME": _jd_to_cal(end_jd),
        "STEP_SIZE": f"{step_days}d",
        "OUT_UNITS": "KM-S",
        "VEC_TABLE": "2",
        "CSV_FORMAT": "YES",
        "TIME_DIGITS": "FRACSEC",
    }
    url = _HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    lines = raw.splitlines()
    try:
        soe = lines.index("$$SOE")
        eoe = lines.index("$$EOE")
    except ValueError as exc:
        raise ValueError(
            "Horizons response did not contain $$SOE/$$EOE; check COMMAND and date range."
        ) from exc

    rows: list[tuple[float, float, float, float, float, float, float]] = []
    for line in lines[soe + 1:eoe]:
        s = line.strip()
        if not s:
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) < 8:
            continue
        try:
            jd = float(parts[0])
            x = float(parts[2])
            y = float(parts[3])
            z = float(parts[4])
            vx = float(parts[5])
            vy = float(parts[6])
            vz = float(parts[7])
        except ValueError:
            continue
        rows.append((jd, x, y, z, vx, vy, vz))

    if not rows:
        raise ValueError("No vector rows were parsed from the Horizons response.")
    return rows


def _write_rows_to_csv(
    path: Path,
    *,
    naif_id: int,
    name: str,
    center: int,
    frame: int,
    window_size: int,
    rows: list[tuple[float, float, float, float, float, float, float]],
    append: bool,
) -> None:
    """Write Horizons rows to DAF-writer CSV format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    write_header = mode == "w" or path.stat().st_size == 0
    with path.open(mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_TEMPLATE_HEADER)
        if write_header:
            writer.writeheader()
        for jd, x, y, z, vx, vy, vz in rows:
            writer.writerow(
                {
                    "naif_id": naif_id,
                    "jd_tdb": f"{jd:.9f}",
                    "x_km": f"{x:.9f}",
                    "y_km": f"{y:.9f}",
                    "z_km": f"{z:.9f}",
                    "vx_km_s": f"{vx:.12f}",
                    "vy_km_s": f"{vy:.12f}",
                    "vz_km_s": f"{vz:.12f}",
                    "name": name,
                    "center": center,
                    "frame": frame,
                    "window_size": window_size,
                }
            )


def _write_template_csv(path: Path) -> None:
    rows = [
        {
            "naif_id": "20000001",
            "jd_tdb": "2460400.0",
            "x_km": "3200000000.0",
            "y_km": "-750000000.0",
            "z_km": "410000000.0",
            "vx_km_s": "659.722222",
            "vy_km_s": "219.907407",
            "vz_km_s": "-92.592593",
            "name": "CustomBodyA",
            "center": "10",
            "frame": "1",
            "window_size": "7",
        },
        {
            "naif_id": "20000001",
            "jd_tdb": "2460401.0",
            "x_km": "3257000000.0",
            "y_km": "-731000000.0",
            "z_km": "402000000.0",
            "vx_km_s": "659.722222",
            "vy_km_s": "219.907407",
            "vz_km_s": "-92.592593",
            "name": "CustomBodyA",
            "center": "10",
            "frame": "1",
            "window_size": "7",
        },
        {
            "naif_id": "20000002",
            "jd_tdb": "2460400.0",
            "x_km": "-2800000000.0",
            "y_km": "1600000000.0",
            "z_km": "900000000.0",
            "vx_km_s": "-509.259259",
            "vy_km_s": "266.203704",
            "vz_km_s": "127.314815",
            "name": "CustomBodyB",
            "center": "10",
            "frame": "1",
            "window_size": "7",
        },
        {
            "naif_id": "20000002",
            "jd_tdb": "2460401.0",
            "x_km": "-2844000000.0",
            "y_km": "1623000000.0",
            "z_km": "911000000.0",
            "vx_km_s": "-509.259259",
            "vy_km_s": "266.203704",
            "vz_km_s": "127.314815",
            "name": "CustomBodyB",
            "center": "10",
            "frame": "1",
            "window_size": "7",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_TEMPLATE_HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _parse_csv_to_bodies(path: Path) -> tuple[list[dict], list[_KernelPreview]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row.")
        headers = tuple(h.strip() for h in reader.fieldnames)
        missing = [c for c in _REQUIRED_COLUMNS if c not in headers]
        if missing:
            raise ValueError(f"CSV missing required column(s): {', '.join(missing)}")

        grouped: dict[int, dict] = {}
        line_no = 1
        for row in reader:
            line_no += 1
            if not any((v or "").strip() for v in row.values()):
                continue

            try:
                naif_id = int((row.get("naif_id") or "").strip())
                jd = float((row.get("jd_tdb") or "").strip())
                x = float((row.get("x_km") or "").strip())
                y = float((row.get("y_km") or "").strip())
                z = float((row.get("z_km") or "").strip())
                vx = float((row.get("vx_km_s") or "").strip())
                vy = float((row.get("vy_km_s") or "").strip())
                vz = float((row.get("vz_km_s") or "").strip())
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value at CSV line {line_no}: {exc}") from exc

            name = (row.get("name") or "").strip() or f"NAIF-{naif_id}"
            center_raw = (row.get("center") or "").strip()
            frame_raw = (row.get("frame") or "").strip()
            ws_raw = (row.get("window_size") or "").strip()
            center = int(center_raw) if center_raw else 10
            frame = int(frame_raw) if frame_raw else 1
            window_size = int(ws_raw) if ws_raw else 7

            entry = grouped.get(naif_id)
            if entry is None:
                entry = {
                    "naif_id": naif_id,
                    "name": name,
                    "center": center,
                    "frame": frame,
                    "window_size": window_size,
                    "rows": [],
                }
                grouped[naif_id] = entry
            else:
                if entry["name"] != name:
                    raise ValueError(
                        f"Body {naif_id} has inconsistent name at CSV line {line_no}."
                    )
                if entry["center"] != center:
                    raise ValueError(
                        f"Body {naif_id} has inconsistent center at CSV line {line_no}."
                    )
                if entry["frame"] != frame:
                    raise ValueError(
                        f"Body {naif_id} has inconsistent frame at CSV line {line_no}."
                    )
                if entry["window_size"] != window_size:
                    raise ValueError(
                        f"Body {naif_id} has inconsistent window_size at CSV line {line_no}."
                    )

            entry["rows"].append((jd, x, y, z, vx, vy, vz))

    if not grouped:
        raise ValueError("CSV contains no kernel data rows.")

    bodies: list[dict] = []
    previews: list[_KernelPreview] = []

    for naif_id in sorted(grouped):
        entry = grouped[naif_id]
        rows = sorted(entry["rows"], key=lambda r: r[0])

        for idx in range(len(rows) - 1):
            if rows[idx][0] >= rows[idx + 1][0]:
                raise ValueError(
                    f"Body {naif_id} has non-increasing jd_tdb values."
                )

        epochs_jd = [r[0] for r in rows]
        states = [[r[col] for r in rows] for col in range(1, 7)]

        body = {
            "naif_id": naif_id,
            "name": entry["name"],
            "center": entry["center"],
            "frame": entry["frame"],
            "window_size": entry["window_size"],
            "epochs_jd": epochs_jd,
            "states": states,
        }
        bodies.append(body)

        previews.append(
            _KernelPreview(
                naif_id=naif_id,
                name=entry["name"],
                center=entry["center"],
                frame=entry["frame"],
                window_size=entry["window_size"],
                rows=len(rows),
                jd_start=epochs_jd[0],
                jd_end=epochs_jd[-1],
            )
        )

    return bodies, previews


class DAFWriterApp(tk.Tk):
    """Tkinter app that guides users through building custom SPK type 13 kernels."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Moira DAF Writer")
        self.resizable(True, True)

        self._csv_path_var = tk.StringVar(value="")
        self._out_path_var = tk.StringVar(
            value=str(user_kernels_dir() / "custom_type13.bsp")
        )
        self._locifn_var = tk.StringVar(value="MOIRA CUSTOM TYPE13")
        self._append_var = tk.BooleanVar(value=True)

        # Search state
        self._search_var = tk.StringVar()
        self._search_kind_var = tk.StringVar(value="All")
        self._search_results: list[dict] = []
        self._search_tree: ttk.Treeview | None = None

        # Fetch parameters
        self._hz_start_var = tk.StringVar(value="2460400.0")
        self._hz_end_var = tk.StringVar(value="2460410.0")
        self._hz_step_var = tk.StringVar(value="1")
        self._hz_center_var = tk.StringVar(value="10")
        self._hz_frame_var = tk.StringVar(value="1")
        self._hz_ws_var = tk.StringVar(value="7")
        self._hz_batch_text: tk.Text | None = None

        self._bodies_cache: list[dict] = []

        self._build_widgets()
        self._log("Ready. Choose a CSV input and validate before writing.")

    def _build_widgets(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Custom Kernel Builder", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w"
        )
        ttk.Label(
            root,
            text=(
                "Guided workflow: 1) Use Horizons importer below (recommended), "
                "or save/edit template CSV, 2) Validate + Preview, 3) Build Kernel."
            ),
            foreground="#555555",
            wraplength=760,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))

        guide = ttk.Label(
            root,
            text=(
                "CSV format columns: " + ", ".join(_REQUIRED_COLUMNS)
                + " (plus optional: " + ", ".join(_OPTIONAL_COLUMNS) + ")"
            ),
            foreground="#666666",
            wraplength=760,
        )
        guide.grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 6))

        hz = ttk.LabelFrame(root, text="Horizons Import (guided)", padding=8)
        hz.grid(row=3, column=0, columnspan=4, sticky="we", pady=(0, 8))

        # --- Body search row ---
        ttk.Label(hz, text="Search bodies:").grid(row=0, column=0, sticky="w")
        srch_entry = ttk.Entry(hz, textvariable=self._search_var, width=34)
        srch_entry.grid(row=0, column=1, columnspan=2, sticky="we", padx=(6, 6))
        srch_entry.bind("<Return>", lambda _e: self._do_search())

        kind_combo = ttk.Combobox(
            hz,
            textvariable=self._search_kind_var,
            values=["All", "Asteroid", "Comet", "Planet / Moon"],
            state="readonly",
            width=14,
        )
        kind_combo.grid(row=0, column=3, sticky="w", padx=(0, 6))
        ttk.Button(hz, text="Search", command=self._do_search, width=10).grid(
            row=0, column=4, sticky="w"
        )
        ttk.Label(
            hz,
            text="type a name, designation, or number",
            foreground="#888888",
        ).grid(row=0, column=5, sticky="w")

        # --- Search results treeview ---
        srch_frame = ttk.Frame(hz)
        srch_frame.grid(row=1, column=0, columnspan=6, sticky="nswe", pady=(6, 0))
        srch_frame.columnconfigure(0, weight=1)

        self._search_tree = ttk.Treeview(
            srch_frame,
            columns=("name", "type", "designation", "naif", "command"),
            show="headings",
            height=5,
            selectmode="extended",
        )
        self._search_tree.heading("name", text="Name")
        self._search_tree.heading("type", text="Type")
        self._search_tree.heading("designation", text="Designation")
        self._search_tree.heading("naif", text="NAIF ID")
        self._search_tree.heading("command", text="Horizons COMMAND")
        self._search_tree.column("name", width=160, anchor="w")
        self._search_tree.column("type", width=130, anchor="w")
        self._search_tree.column("designation", width=100, anchor="w")
        self._search_tree.column("naif", width=90, anchor="e")
        self._search_tree.column("command", width=220, anchor="w")
        srch_sb = ttk.Scrollbar(srch_frame, orient="vertical", command=self._search_tree.yview)
        self._search_tree.configure(yscrollcommand=srch_sb.set)
        self._search_tree.pack(side="left", fill="both", expand=True)
        srch_sb.pack(side="right", fill="y")

        add_row = ttk.Frame(hz)
        add_row.grid(row=2, column=0, columnspan=6, sticky="we", pady=(6, 0))
        ttk.Button(
            add_row,
            text="Add selected → fetch list",
            command=self._add_selected_to_batch,
            width=22,
        ).pack(side="left")
        ttk.Label(
            add_row,
            text="Select one or more results (Ctrl/Shift for multi-select), then add.",
            foreground="#666666",
        ).pack(side="left", padx=(10, 0))

        ttk.Separator(hz, orient="horizontal").grid(
            row=3, column=0, columnspan=6, sticky="we", pady=(10, 6)
        )

        # --- Date / step / observer settings ---
        ttk.Label(hz, text="Start JD").grid(row=4, column=0, sticky="w")
        ttk.Entry(hz, textvariable=self._hz_start_var, width=14).grid(
            row=4, column=1, sticky="w", padx=(6, 10)
        )
        ttk.Label(hz, text="End JD").grid(row=4, column=2, sticky="w")
        ttk.Entry(hz, textvariable=self._hz_end_var, width=14).grid(
            row=4, column=3, sticky="w", padx=(6, 10)
        )
        ttk.Label(hz, text="Step (days)").grid(row=4, column=4, sticky="w")
        ttk.Entry(hz, textvariable=self._hz_step_var, width=10).grid(
            row=4, column=5, sticky="w", padx=(6, 0)
        )

        ttk.Label(hz, text="Center NAIF").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(hz, textvariable=self._hz_center_var, width=14).grid(
            row=5, column=1, sticky="w", padx=(6, 10), pady=(6, 0)
        )
        ttk.Label(hz, text="Frame").grid(row=5, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(hz, textvariable=self._hz_frame_var, width=14).grid(
            row=5, column=3, sticky="w", padx=(6, 10), pady=(6, 0)
        )
        ttk.Label(hz, text="Window size").grid(row=5, column=4, sticky="w", pady=(6, 0))
        ttk.Entry(hz, textvariable=self._hz_ws_var, width=10).grid(
            row=5, column=5, sticky="w", padx=(6, 0), pady=(6, 0)
        )
        ttk.Label(
            hz,
            text="Center: 10 = Sun  |  Frame: 1 = J2000  |  Window: interpolation nodes per segment",
            foreground="#888888",
        ).grid(row=6, column=0, columnspan=6, sticky="w", pady=(2, 0))

        ttk.Checkbutton(hz, text="Append to existing CSV", variable=self._append_var).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        # --- Fetch list textarea ---
        ttk.Label(
            hz,
            text="Fetch list  (COMMAND | NAIF ID | Name — populated by search above, or type manually):",
            foreground="#444444",
        ).grid(row=8, column=0, columnspan=6, sticky="w", pady=(8, 2))
        self._hz_batch_text = tk.Text(hz, width=90, height=4, wrap="none")
        self._hz_batch_text.grid(row=9, column=0, columnspan=6, sticky="we")

        btn_hz = ttk.Frame(hz)
        btn_hz.grid(row=10, column=0, columnspan=6, sticky="we", pady=(8, 0))
        ttk.Button(
            btn_hz,
            text="Fetch Horizons → CSV",
            command=self._fetch_horizons_to_csv,
            width=22,
        ).pack(side="left")
        ttk.Button(
            btn_hz,
            text="Fetch + Build BSP  ▶",
            command=self._fetch_horizons_and_build,
            width=20,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            btn_hz,
            text="Clear fetch list",
            command=lambda: self._hz_batch_text and self._hz_batch_text.delete("1.0", "end"),
            width=14,
        ).pack(side="left", padx=(6, 0))

        ttk.Label(root, text="Input CSV").grid(row=4, column=0, sticky="w")
        ttk.Entry(root, textvariable=self._csv_path_var, width=86).grid(
            row=4, column=1, columnspan=2, sticky="we", padx=(8, 8)
        )
        ttk.Button(root, text="Browse...", command=self._browse_csv, width=12).grid(
            row=4, column=3, sticky="e"
        )

        ttk.Label(root, text="Output BSP").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(root, textvariable=self._out_path_var, width=86).grid(
            row=5, column=1, columnspan=2, sticky="we", padx=(8, 8), pady=(6, 0)
        )
        ttk.Button(root, text="Browse...", command=self._browse_output, width=12).grid(
            row=5, column=3, sticky="e", pady=(6, 0)
        )

        ttk.Label(root, text="LOCIFN").grid(row=6, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(root, textvariable=self._locifn_var, width=40).grid(
            row=6, column=1, sticky="w", padx=(8, 8), pady=(6, 0)
        )
        ttk.Label(
            root,
            text="(Internal file label, max 60 chars)",
            foreground="#666666",
        ).grid(row=6, column=2, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Separator(root, orient="horizontal").grid(
            row=7, column=0, columnspan=4, sticky="we", pady=10
        )

        self._tree = ttk.Treeview(
            root,
            columns=("naif", "rows", "range", "center", "frame", "ws"),
            show="headings",
            height=8,
        )
        self._tree.heading("naif", text="NAIF")
        self._tree.heading("rows", text="Epoch rows")
        self._tree.heading("range", text="JD range")
        self._tree.heading("center", text="Center")
        self._tree.heading("frame", text="Frame")
        self._tree.heading("ws", text="Window")

        self._tree.column("naif", width=90, anchor="e")
        self._tree.column("rows", width=90, anchor="e")
        self._tree.column("range", width=280, anchor="w")
        self._tree.column("center", width=70, anchor="e")
        self._tree.column("frame", width=70, anchor="e")
        self._tree.column("ws", width=70, anchor="e")

        self._tree.grid(row=8, column=0, columnspan=4, sticky="we")

        self._log_text = tk.Text(root, height=10, wrap="word", state="disabled")
        self._log_text.grid(row=9, column=0, columnspan=4, sticky="we", pady=(8, 0))

        btns = ttk.Frame(root)
        btns.grid(row=10, column=0, columnspan=4, sticky="we", pady=(10, 0))

        ttk.Button(btns, text="Save Template CSV", command=self._save_template, width=18).pack(side="left")
        ttk.Button(btns, text="Validate + Preview", command=self._validate_preview, width=18).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="Build Kernel", command=self._build_kernel, width=14).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="Close", command=self.destroy, width=10).pack(side="right")

        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=1)

    def _log(self, text: str) -> None:
        self._log_text.config(state="normal")
        self._log_text.insert("end", text + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._csv_path_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Choose output BSP path",
            defaultextension=".bsp",
            filetypes=[("SPK kernels", "*.bsp"), ("All files", "*.*")],
            initialfile=Path(self._out_path_var.get()).name,
            initialdir=str(Path(self._out_path_var.get()).parent),
        )
        if path:
            self._out_path_var.set(path)

    def _save_template(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save CSV template",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="moira_type13_template.csv",
        )
        if not path:
            return
        try:
            _write_template_csv(Path(path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Template write failed", str(exc))
            return
        self._log(f"Template written: {path}")

    def _fetch_horizons_to_csv(self) -> None:
        self._run_horizons_pipeline(build_after=False)

    def _fetch_horizons_and_build(self) -> None:
        self._run_horizons_pipeline(build_after=True)

    def _parse_horizons_targets(self) -> list[tuple[str, int, str]]:
        targets: list[tuple[str, int, str]] = []
        if self._hz_batch_text is not None:
            raw = self._hz_batch_text.get("1.0", "end").strip()
        else:
            raw = ""

        for idx, line in enumerate(raw.splitlines(), start=1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = [p.strip() for p in s.split("|")]
            if len(parts) < 2:
                raise ValueError(
                    f"Fetch list line {idx} must be: COMMAND | NAIF ID | Name"
                )
            command = parts[0]
            try:
                naif_id = int(parts[1])
            except ValueError as exc:
                raise ValueError(
                    f"Fetch list line {idx} has invalid NAIF ID: {parts[1]!r}"
                ) from exc
            name = parts[2] if len(parts) >= 3 and parts[2] else f"NAIF-{naif_id}"
            targets.append((command, naif_id, name))

        if not targets:
            raise ValueError(
                "Fetch list is empty.\n\n"
                "Use the Search box to find bodies and click "
                "'Add selected → fetch list', or type entries directly as:\n"
                "  COMMAND | NAIF ID | Name"
            )
        return targets

    def _run_horizons_pipeline(self, *, build_after: bool) -> None:
        csv_path = self._csv_path_var.get().strip()
        if not csv_path:
            suggested = filedialog.asksaveasfilename(
                title="Choose CSV destination for Horizons data",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="moira_type13_data.csv",
            )
            if not suggested:
                return
            csv_path = suggested
            self._csv_path_var.set(csv_path)

        try:
            targets = self._parse_horizons_targets()
            start_jd = float(self._hz_start_var.get().strip())
            end_jd = float(self._hz_end_var.get().strip())
            step_days = int(self._hz_step_var.get().strip())
            center = int(self._hz_center_var.get().strip())
            frame = int(self._hz_frame_var.get().strip())
            window_size = int(self._hz_ws_var.get().strip())
        except ValueError as exc:
            messagebox.showerror("Invalid Horizons input", str(exc))
            return

        if end_jd <= start_jd:
            messagebox.showerror("Invalid JD range", "End JD must be greater than Start JD.")
            return
        if step_days <= 0:
            messagebox.showerror("Invalid step", "Step days must be positive.")
            return

        self._log(f"Horizons pipeline starting for {len(targets)} target(s).")
        total_rows = 0
        did_write = False
        try:
            csv_obj = Path(csv_path)
            for idx, (command, naif_id, name) in enumerate(targets):
                self._log(
                    f"Fetching [{idx + 1}/{len(targets)}] COMMAND={command!r} "
                    f"as NAIF {naif_id} ({name})..."
                )
                rows = _fetch_horizons_vectors(command, start_jd, end_jd, step_days)
                _write_rows_to_csv(
                    csv_obj,
                    naif_id=naif_id,
                    name=name,
                    center=center,
                    frame=frame,
                    window_size=window_size,
                    rows=rows,
                    append=bool(self._append_var.get()) if idx == 0 else True,
                )
                did_write = True
                total_rows += len(rows)
                self._log(
                    f"Fetched {len(rows)} rows for NAIF {naif_id} ({name})."
                )

            if build_after:
                self._build_from_csv(Path(csv_path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Horizons import failed", str(exc))
            self._log(f"Horizons import failed: {exc}")
            if did_write:
                self._log("Partial CSV data may have been written before the failure.")
            return

        if build_after:
            messagebox.showinfo(
                "Horizons fetch + build complete",
                f"Fetched {total_rows} total rows for {len(targets)} target(s).\n"
                f"CSV: {csv_path}\n"
                f"BSP: {self._out_path_var.get().strip()}",
            )
        else:
            self._log(
                f"Fetched {total_rows} total rows and wrote them to {csv_path} "
                f"for {len(targets)} target(s)."
            )
            messagebox.showinfo(
                "Horizons import complete",
                f"Wrote {total_rows} rows for {len(targets)} target(s) to:\n{csv_path}\n\n"
                "Next step: click Validate + Preview, or use Fetch + Build BSP.",
            )

    def _build_from_csv(self, csv_path: Path) -> None:
        try:
            bodies, preview = _parse_csv_to_bodies(csv_path)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"CSV validation failed before build: {exc}") from exc

        self._bodies_cache = bodies
        self._tree.delete(*self._tree.get_children())
        for p in preview:
            self._tree.insert(
                "",
                "end",
                values=(
                    p.naif_id,
                    p.rows,
                    f"{p.jd_start:.6f} - {p.jd_end:.6f}",
                    p.center,
                    p.frame,
                    p.window_size,
                ),
                text=p.name,
            )

        output_path = Path(self._out_path_var.get().strip())
        if not output_path.name:
            raise ValueError("Choose an output BSP path.")

        locifn = self._locifn_var.get().strip() or "MOIRA CUSTOM TYPE13"
        if len(locifn) > 60:
            raise ValueError("LOCIFN must be 60 characters or fewer.")

        write_spk_type13(output_path, self._bodies_cache, locifn=locifn)
        self._log(
            f"Kernel written: {output_path} ({output_path.stat().st_size:,} bytes)"
        )

    # ------------------------------------------------------------------
    # Body search helpers
    # ------------------------------------------------------------------

    def _do_search(self) -> None:
        query = self._search_var.get().strip()
        if not query:
            messagebox.showinfo("Empty search", "Enter a body name, designation, or number.")
            return

        kind_label = self._search_kind_var.get()
        sbdb_kind = {"Asteroid": "asteroid", "Comet": "comet"}.get(kind_label, "all")

        if self._search_tree is not None:
            self._search_tree.delete(*self._search_tree.get_children())
        self._search_results = []

        results: list[dict] = []

        # Major bodies from curated table (planets / moons / dwarf planets)
        if kind_label in ("All", "Planet / Moon"):
            q = query.lower()
            for body in _MAJOR_BODIES:
                if (
                    q in body["name"].lower()
                    or q in body["full_name"].lower()
                    or q == str(body["naif"])
                    or (body["pdes"] and q in body["pdes"].lower())
                ):
                    results.append(body)

        # SBDB small-body search (asteroids + comets)
        if kind_label != "Planet / Moon":
            try:
                results += _search_sbdb(query, kind=sbdb_kind)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Search failed", f"JPL SBDB query failed:\n{exc}")
                self._log(f"SBDB search error: {exc}")
                if not results:
                    return

        if not results:
            messagebox.showinfo("No results", f"No bodies found for {query!r}.")
            self._log(f"Search [{kind_label}] {query!r}: no results.")
            return

        self._search_results = results
        if self._search_tree is not None:
            for body in results:
                display_naif = body["naif"] if body["naif"] else "(assign manually)"
                self._search_tree.insert(
                    "",
                    "end",
                    values=(
                        body.get("name") or body.get("full_name", ""),
                        body["type"],
                        body.get("pdes", ""),
                        display_naif,
                        body["command"],
                    ),
                )

        self._log(f"Search [{kind_label}] {query!r}: {len(results)} result(s).")

    def _add_selected_to_batch(self) -> None:
        if self._search_tree is None or self._hz_batch_text is None:
            return
        selection = self._search_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Nothing selected",
                "Select one or more bodies from the search results first.\n"
                "(Hold Ctrl or Shift to select multiple.)",
            )
            return

        lines_to_add: list[str] = []
        for item_id in selection:
            row_idx = self._search_tree.index(item_id)
            if row_idx >= len(self._search_results):
                continue
            body = self._search_results[row_idx]
            naif = body.get("naif", 0)
            name = body.get("name") or body.get("full_name", f"NAIF-{naif}")
            command = body["command"]
            if not naif:
                lines_to_add.append(
                    f"{command} | 0 | {name}  # <-- replace 0 with a NAIF ID"
                )
            else:
                lines_to_add.append(f"{command} | {naif} | {name}")

        existing = self._hz_batch_text.get("1.0", "end").strip()
        combined = "\n".join([existing] + lines_to_add).strip() if existing else "\n".join(lines_to_add)
        self._hz_batch_text.delete("1.0", "end")
        self._hz_batch_text.insert("1.0", combined + "\n")
        self._log(f"Added {len(lines_to_add)} body/bodies to fetch list.")

    def _validate_preview(self) -> None:
        csv_path = self._csv_path_var.get().strip()
        if not csv_path:
            messagebox.showinfo("Missing input", "Choose an input CSV first.")
            return

        try:
            bodies, preview = _parse_csv_to_bodies(Path(csv_path))
        except Exception as exc:  # noqa: BLE001
            self._bodies_cache = []
            self._tree.delete(*self._tree.get_children())
            messagebox.showerror("CSV validation failed", str(exc))
            self._log(f"Validation failed: {exc}")
            return

        self._bodies_cache = bodies
        self._tree.delete(*self._tree.get_children())
        for p in preview:
            self._tree.insert(
                "",
                "end",
                values=(
                    p.naif_id,
                    p.rows,
                    f"{p.jd_start:.6f} - {p.jd_end:.6f}",
                    p.center,
                    p.frame,
                    p.window_size,
                ),
                text=p.name,
            )

        total_rows = sum(p.rows for p in preview)
        self._log(
            f"Validated {len(preview)} body segment(s), {total_rows} total epoch rows from {csv_path}."
        )

    def _build_kernel(self) -> None:
        if not self._bodies_cache:
            messagebox.showinfo(
                "No preview data",
                "Run Validate + Preview first so input is checked before writing.",
            )
            return

        output_path = Path(self._out_path_var.get().strip())
        if not output_path.name:
            messagebox.showinfo("Missing output", "Choose an output BSP path.")
            return

        locifn = self._locifn_var.get().strip() or "MOIRA CUSTOM TYPE13"
        if len(locifn) > 60:
            messagebox.showerror("Invalid LOCIFN", "LOCIFN must be 60 characters or fewer.")
            return

        try:
            write_spk_type13(output_path, self._bodies_cache, locifn=locifn)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Kernel build failed", str(exc))
            self._log(f"Build failed: {exc}")
            return

        self._log(f"Kernel written: {output_path} ({output_path.stat().st_size:,} bytes)")
        messagebox.showinfo("Build complete", f"Kernel written:\n{output_path}")


def main() -> None:
    app = DAFWriterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
