"""
Moira — kernel_manager_ui.py
Tkinter GUI for downloading and configuring JPL planetary kernels.

No dependencies beyond the Python standard library and Moira itself.

Launch:
    moira-kernel-manager              (console entry point after pip install)
    python -m moira.kernel_manager_ui
"""

from __future__ import annotations

import queue
import threading
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from ._kernel_paths import find_kernel, find_planetary_kernel, user_kernels_dir
from .download_kernels import _REGISTRY


# ---------------------------------------------------------------------------
# Extended UI descriptions (augments _REGISTRY for display)
# ---------------------------------------------------------------------------

_KERNEL_DETAILS: dict[str, dict] = {
    "de430.bsp": {
        "title": "DE430 — Compact modern ephemeris",
        "detail": (
            "JPL DE430 is a widely-deployed planetary ephemeris covering 1550 BCE "
            "to 2650 CE. It is the predecessor to DE440 and remains broadly compatible "
            "with legacy toolchains. At approximately 128 MB it is compact and proven. "
            "Choose DE430 if you need a stable, well-understood baseline or compatibility "
            "with other software using the same kernel."
        ),
        "date_range": "1550 BCE – 2650 CE",
        "size": "~128 MB",
        "type": "planetary",
    },
    "de440.bsp": {
        "title": "DE440 — Current JPL standard (recommended)",
        "detail": (
            "JPL DE440 (released 2020) is the current operational planetary standard. "
            "It delivers improved accuracy over DE430 for the inner planets, the Moon, "
            "and the outer system, while covering the same date range (1550 BCE – 2650 CE). "
            "At ~114 MB it is the most compact option. Recommended for all users whose "
            "charts fall within the modern era."
        ),
        "date_range": "1550 BCE – 2650 CE",
        "size": "~114 MB",
        "type": "planetary",
    },
    "de441.bsp": {
        "title": "DE441 — Extended range (Moira original)",
        "detail": (
            "DE441 was Moira's original design kernel, chosen for its extreme date "
            "coverage: approximately 13,200 BCE to 17,200 CE. This range is essential "
            "for ancient and medieval horoscopy, long-span astrological cycles, and "
            "heliacal phenomena research. The trade-off is file size: at 3.1 GB it is "
            "roughly 27× larger than DE440. Choose DE441 when extended date range is "
            "required; prefer DE440 for modern-era work."
        ),
        "date_range": "~13 200 BCE – ~17 200 CE",
        "size": "~3.1 GB",
        "type": "planetary",
    },
    "asteroids.bsp": {
        "title": "Asteroids — 300 classical bodies",
        "detail": (
            "This kernel covers 300 numbered minor planets from the JPL asteroid catalog. "
            "It is required by Moira's asteroids module for bodies beyond the four "
            "classical asteroids (Ceres, Pallas, Juno, Vesta), which are embedded in "
            "the planetary kernel itself. Approximately 59 MB. Optional unless your "
            "work involves extended asteroid lists."
        ),
        "date_range": "—",
        "size": "~59 MB",
        "type": "supplemental",
    },
    "sb441-n373s.bsp": {
        "title": "Small bodies — TNOs and extended Centaurs",
        "detail": (
            "Covers 373 small bodies including trans-Neptunian objects (Ixion, Quaoar, "
            "Varuna, Orcus, Sedna, Eris, Makemake, Haumea) and Centaurs not included "
            "in the bundled centaurs.bsp fleet. This is a large optional file (~936 MB) "
            "for users who need full minor-body coverage beyond the bundled kernels."
        ),
        "date_range": "—",
        "size": "~936 MB",
        "type": "supplemental",
    },
}

_CHUNK_SIZE = 65_536  # 64 KB per read


# ---------------------------------------------------------------------------
# Background download worker (module-level — no self reference)
# ---------------------------------------------------------------------------

def _download_worker(
    url: str,
    dest: Path,
    progress_queue: "queue.Queue[tuple[str, object]]",
    cancel_event: threading.Event,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            with tmp.open("wb") as fh:
                while True:
                    if cancel_event.is_set():
                        progress_queue.put(("cancelled", None))
                        return
                    chunk = response.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    pct = int(downloaded * 100 / total) if total > 0 else 0
                    progress_queue.put(("progress", pct))
        tmp.rename(dest)
        progress_queue.put(("done", str(dest)))
    except Exception as exc:  # noqa: BLE001
        if tmp.exists():
            tmp.unlink()
        progress_queue.put(("error", str(exc)))


# ---------------------------------------------------------------------------
# Application window
# ---------------------------------------------------------------------------

class KernelManagerApp(tk.Tk):
    """Tkinter window for managing Moira planetary kernels."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Moira Kernel Manager")
        self.resizable(False, False)

        self._progress_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._cancel_event: threading.Event | None = None
        self._downloading = False

        self._build_widgets()
        self._refresh_tree()
        self._refresh_active_label()

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widgets(self) -> None:
        pad = dict(padx=12, pady=6)

        # ---- Active kernel banner ----
        banner = ttk.Frame(self, padding=(12, 10, 12, 6))
        banner.pack(fill="x")
        ttk.Label(banner, text="Active planetary kernel", font=("", 9, "bold")).pack(anchor="w")
        self._active_label = ttk.Label(banner, text="", font=("", 9))
        self._active_label.pack(anchor="w")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # ---- Kernel list ----
        tree_frame = ttk.Frame(self, padding=(12, 8, 12, 0))
        tree_frame.pack(fill="both")

        cols = ("size", "range", "status")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="tree headings",
            selectmode="browse",
            height=8,
        )
        self._tree.heading("#0",     text="Kernel",     anchor="w")
        self._tree.heading("size",   text="Size",       anchor="w")
        self._tree.heading("range",  text="Date range", anchor="w")
        self._tree.heading("status", text="Status",     anchor="w")

        self._tree.column("#0",     width=185, stretch=False)
        self._tree.column("size",   width=80,  stretch=False)
        self._tree.column("range",  width=170, stretch=False)
        self._tree.column("status", width=110, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)

        self._tree.tag_configure("installed",      foreground="#2a6e2a")
        self._tree.tag_configure("missing",        foreground="#8a2020")
        self._tree.tag_configure("section_heading", foreground="#777777",
                                 font=("", 8, "italic"))

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---- Detail panel ----
        detail_outer = ttk.Frame(self, padding=(12, 6, 12, 0))
        detail_outer.pack(fill="x")

        self._detail_text = tk.Text(
            detail_outer,
            height=5,
            wrap="word",
            state="disabled",
            relief="flat",
            background=self.cget("background"),
            font=("", 9),
            cursor="arrow",
        )
        self._detail_text.pack(fill="x")

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(8, 0))

        # ---- Progress area ----
        prog_frame = ttk.Frame(self, padding=(12, 6, 12, 2))
        prog_frame.pack(fill="x")

        self._progress_var = tk.IntVar(value=0)
        self._progress_bar = ttk.Progressbar(
            prog_frame, mode="determinate", maximum=100, variable=self._progress_var
        )
        # Hidden until a download starts; a label placeholder keeps the layout stable
        self._progress_bar_row = ttk.Frame(prog_frame)
        self._progress_bar_row.pack(fill="x")
        self._progress_bar = ttk.Progressbar(
            self._progress_bar_row,
            mode="determinate",
            maximum=100,
            variable=self._progress_var,
        )

        self._status_label = ttk.Label(prog_frame, text=" ", font=("", 8), foreground="#555555")
        self._status_label.pack(anchor="w")

        # ---- Button bar ----
        btn_frame = ttk.Frame(self, padding=(12, 6, 12, 10))
        btn_frame.pack(fill="x", side="bottom")

        self._btn_download = ttk.Button(btn_frame, text="Download selected", command=self._on_download, width=18)
        self._btn_download.pack(side="left", padx=(0, 4))

        self._btn_use = ttk.Button(btn_frame, text="Use selected", command=self._on_use, width=14)
        self._btn_use.pack(side="left", padx=(0, 4))

        self._btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self._on_cancel,
                                      state="disabled", width=10)
        self._btn_cancel.pack(side="left", padx=(0, 4))

        self._btn_browse = ttk.Button(btn_frame, text="Browse…", command=self._on_browse, width=10)
        self._btn_browse.pack(side="left", padx=(0, 4))

        self._btn_close = ttk.Button(btn_frame, text="Close", command=self.destroy, width=8)
        self._btn_close.pack(side="right")

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _refresh_tree(self) -> None:
        sel = self._tree.selection()
        prev_sel = sel[0] if sel else None

        for iid in self._tree.get_children():
            self._tree.delete(iid)

        self._insert_section("── Planetary kernels", "__planetary__", "planetary")
        self._insert_section("── Supplemental kernels", "__supplemental__", "supplemental")

        if prev_sel and self._tree.exists(prev_sel):
            self._tree.selection_set(prev_sel)

    def _insert_section(self, label: str, iid: str, section_type: str) -> None:
        self._tree.insert(
            "", "end",
            iid=iid,
            text=label,
            values=("", "", ""),
            tags=("section_heading",),
        )
        for entry in _REGISTRY:
            detail = _KERNEL_DETAILS.get(entry["filename"], {})
            if detail.get("type", "supplemental") != section_type:
                continue
            installed = find_kernel(entry["filename"]).exists()
            self._tree.insert(
                "", "end",
                iid=entry["filename"],
                text="  " + entry["filename"],
                values=(
                    detail.get("size", entry.get("size_hint", "—")),
                    detail.get("date_range", "—"),
                    "Installed" if installed else "Missing",
                ),
                tags=("installed" if installed else "missing",),
            )

    def _refresh_active_label(self) -> None:
        kernel = find_planetary_kernel()
        if kernel is not None:
            self._active_label.config(
                text=f"{kernel.name}   ·   {kernel}",
                foreground="#2a6e2a",
            )
        else:
            self._active_label.config(
                text="(none — download a planetary kernel or browse to an existing file)",
                foreground="#8a2020",
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("__"):
            return
        details = _KERNEL_DETAILS.get(iid)
        if details is None:
            return
        body = f"{details['title']}\n\n{details['detail']}"
        self._detail_text.config(state="normal")
        self._detail_text.delete("1.0", "end")
        self._detail_text.insert("end", body)
        self._detail_text.config(state="disabled")

    def _on_download(self) -> None:
        if self._downloading:
            return
        sel = self._tree.selection()
        if not sel or sel[0].startswith("__"):
            messagebox.showinfo("No selection", "Select a kernel row to download.")
            return
        filename = sel[0]
        entry = next((e for e in _REGISTRY if e["filename"] == filename), None)
        if entry is None:
            return

        if find_kernel(filename).exists():
            if not messagebox.askyesno(
                "Already installed",
                f"{filename} is already installed.\nRe-download and overwrite?",
            ):
                return

        dest = user_kernels_dir() / filename
        self._cancel_event = threading.Event()
        self._downloading = True
        self._progress_var.set(0)
        self._progress_bar.pack(fill="x")
        self._status_label.config(text=f"Downloading {filename}…")
        self._set_buttons_active(downloading=True)

        threading.Thread(
            target=_download_worker,
            args=(entry["url"], dest, self._progress_queue, self._cancel_event),
            daemon=True,
        ).start()
        self.after(100, self._poll_progress)

    def _poll_progress(self) -> None:
        try:
            while True:
                kind, value = self._progress_queue.get_nowait()
                if kind == "progress":
                    self._progress_var.set(int(value))
                    self._status_label.config(text=f"Downloading…  {value}%")
                elif kind == "done":
                    self._finish_download(success=True, message=f"Complete: {value}")
                    return
                elif kind == "cancelled":
                    self._finish_download(success=False, message="Download cancelled.")
                    return
                elif kind == "error":
                    self._finish_download(success=False, message=f"Error: {value}", error=str(value))
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_progress)

    def _finish_download(
        self,
        *,
        success: bool,
        message: str,
        error: str | None = None,
    ) -> None:
        self._downloading = False
        if not success:
            self._progress_bar.pack_forget()
        self._status_label.config(text=message)
        self._set_buttons_active(downloading=False)
        self._refresh_tree()
        self._refresh_active_label()
        if error:
            messagebox.showerror("Download failed", error)

    def _on_cancel(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    def _on_use(self) -> None:
        sel = self._tree.selection()
        if not sel or sel[0].startswith("__"):
            messagebox.showinfo("No selection", "Select an installed kernel to activate.")
            return
        filename = sel[0]
        path = find_kernel(filename)
        if not path.exists():
            messagebox.showwarning(
                "Not installed",
                f"{filename} is not present on disk.\nDownload it first.",
            )
            return
        try:
            from .spk_reader import set_kernel_path
            set_kernel_path(str(path))
        except RuntimeError as exc:
            messagebox.showerror("Cannot switch kernel", str(exc))
            return
        self._refresh_active_label()
        messagebox.showinfo(
            "Kernel activated",
            f"{filename} is now the active kernel.\n\n"
            "If a Moira() instance is already running, create a new one to pick up "
            "the change.",
        )

    def _on_browse(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Select a JPL SPK planetary kernel (.bsp)",
            filetypes=[("SPK Kernel", "*.bsp"), ("All files", "*.*")],
        )
        if not path_str:
            return
        try:
            from .spk_reader import set_kernel_path
            set_kernel_path(path_str)
        except RuntimeError as exc:
            messagebox.showerror("Cannot set kernel", str(exc))
            return
        self._refresh_active_label()
        messagebox.showinfo(
            "Custom kernel configured",
            f"Active kernel: {path_str}\n\n"
            "Note: this path is not in the standard search locations. "
            "To have it discovered automatically on next launch, place or symlink "
            f"the file under:\n\n  {user_kernels_dir()}",
        )

    # ------------------------------------------------------------------
    # Button state helper
    # ------------------------------------------------------------------

    def _set_buttons_active(self, *, downloading: bool) -> None:
        idle_state = "normal"
        busy_state = "disabled"
        self._btn_download.config(state=busy_state if downloading else idle_state)
        self._btn_use.config(state=busy_state if downloading else idle_state)
        self._btn_browse.config(state=busy_state if downloading else idle_state)
        self._btn_close.config(state=busy_state if downloading else idle_state)
        self._btn_cancel.config(state=idle_state if downloading else busy_state)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Open the Moira Kernel Manager window."""
    app = KernelManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
