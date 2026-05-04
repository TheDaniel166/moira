import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import queue
import os
import re
import sys
import shlex
from pathlib import Path
from datetime import datetime

# --- Constants & Configuration ---
REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = sys.executable

# --- Premium Palette ---
CLR_VOID       = "#121212"  # Deepest Black
CLR_SURFACE    = "#1e1e1e"  # Dark Gray Surface
CLR_BORDER     = "#333333"  # Subtle Border
CLR_FG         = "#e0e0e0"  # Soft White Text
CLR_FG_DIM     = "#a0a0a0"  # Muted Gray Text
CLR_AZURE      = "#007acc"  # Primary Blue
CLR_EMERALD    = "#4ec9b0"  # Success Green
CLR_CRIMSON    = "#f44747"  # Failure Red
CLR_GOLD       = "#dcdcaa"  # Warning/Highlight
CLR_CONSOLE    = "#000000"  # Pure Console Void

class MoiraTestRunnerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Moira | Test Registry & Diagnostic Frame")
        self.root.geometry("1200x850")
        self.root.configure(bg=CLR_VOID)
        
        self.process = None
        self.output_queue = queue.Queue()
        self.is_running = False
        
        self._build_ui()
        self._start_queue_monitor()

    def _build_ui(self):
        # Main Container
        self.main_container = tk.Frame(self.root, bg=CLR_VOID, padx=20, pady=20)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Header
        header_frame = tk.Frame(self.main_container, bg=CLR_VOID)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header_frame, text="MOIRA TEST REGISTRY", 
                 font=("Segoe UI", 24, "bold"), bg=CLR_VOID, fg=CLR_AZURE).pack(side=tk.LEFT)
        
        self.status_label = tk.Label(header_frame, text="READY", 
                                    font=("Segoe UI", 10, "bold"), bg=CLR_VOID, fg=CLR_FG_DIM)
        self.status_label.pack(side=tk.RIGHT, pady=(10, 0))

        # 2. Configuration Grid
        config_frame = tk.Frame(self.main_container, bg=CLR_VOID)
        config_frame.pack(fill=tk.X, pady=10)
        config_frame.columnconfigure((0, 1, 2), weight=1, uniform="equal")

        # --- Section: Configuration ---
        cfg_sect = self._create_section(config_frame, " TEST CONFIGURATION ", 0, 0)
        
        # Marker Row
        self._label(cfg_sect, "Marker:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.marker_var = tk.StringVar(value="All")
        self.marker_combo = ttk.Combobox(cfg_sect, textvariable=self.marker_var, 
                                        values=["All", "unit", "integration", "property", "ui", "slow", "network"],
                                        state="readonly", width=15)
        self.marker_combo.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Target Row
        self._label(cfg_sect, "Target:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_var = tk.StringVar()
        target_frame = tk.Frame(cfg_sect, bg=CLR_SURFACE)
        target_frame.grid(row=1, column=1, sticky=tk.EW, padx=5)
        
        self.target_entry = tk.Entry(target_frame, textvariable=self.target_var, 
                                    bg="#2d2d2d", fg=CLR_FG, insertbackground="white",
                                    relief=tk.FLAT, font=("Consolas", 10), width=20)
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)
        
        tk.Button(target_frame, text="...", command=self._browse_target,
                  bg="#444444", fg=CLR_FG, relief=tk.FLAT, font=("Segoe UI", 8)).pack(side=tk.RIGHT)

        # Toggles Row
        toggles_frame = tk.Frame(cfg_sect, bg=CLR_SURFACE)
        toggles_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        self.failfast_var = tk.BooleanVar(value=False)
        self._check(toggles_frame, "Fail Fast (-x)", self.failfast_var).pack(side=tk.LEFT, padx=(0, 15))
        
        self.verbose_var = tk.BooleanVar(value=True)
        self._check(toggles_frame, "Verbose (-v)", self.verbose_var).pack(side=tk.LEFT)

        # --- Section: Execution ---
        exec_sect = self._create_section(config_frame, " EXECUTION POLICY ", 0, 1)
        
        self.parallel_var = tk.BooleanVar(value=False)
        self._check(exec_sect, "Parallel (pytest-xdist)", self.parallel_var, command=self._toggle_parallel).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self._label(exec_sect, "Workers:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.workers_var = tk.IntVar(value=0)
        self.workers_spin = tk.Spinbox(exec_sect, from_=0, to=16, textvariable=self.workers_var, 
                                      bg="#2d2d2d", fg=CLR_FG, buttonbackground="#444444",
                                      relief=tk.FLAT, width=5, state="disabled")
        self.workers_spin.grid(row=1, column=1, sticky=tk.W, padx=5)

        # --- Section: Liturgy ---
        lit_sect = self._create_section(config_frame, " LITURGICAL FLAGS ", 0, 2)
        
        self.experimental_var = tk.BooleanVar(value=False)
        self._check(lit_sect, "MOIRA_RUN_EXPERIMENTAL", self.experimental_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.templates_var = tk.BooleanVar(value=False)
        self._check(lit_sect, "MOIRA_RUN_TEMPLATES", self.templates_var).grid(row=1, column=0, sticky=tk.W, pady=5)

        # 3. Actions Row
        actions_frame = tk.Frame(self.main_container, bg=CLR_VOID)
        actions_frame.pack(fill=tk.X, pady=20)
        
        self.btn_run = self._action_btn(actions_frame, "RUN PYTEST", self.run_pytest, CLR_EMERALD, "white")
        self.btn_script = self._action_btn(actions_frame, "RUN SCRIPT", self.run_script, "#7b1fa2", "white")
        self.btn_val = self._action_btn(actions_frame, "VALIDATION", self.run_validation, CLR_AZURE, "white")
        self.btn_stop = self._action_btn(actions_frame, "STOP", self.stop_execution, CLR_CRIMSON, "white", state="disabled")
        
        # Secondary actions
        self._action_btn(actions_frame, "COPY SUMMARY", self.copy_summary, "#444444", CLR_FG)
        self._action_btn(actions_frame, "SAVE LOG", self.save_log, "#444444", CLR_FG)
        self._action_btn(actions_frame, "ARTIFACTS", self.open_artifacts, "#444444", CLR_FG)
        self._action_btn(actions_frame, "CLEAR", self.clear_output, "#444444", CLR_FG)

        # 4. Command Preview
        preview_frame = tk.Frame(self.main_container, bg=CLR_VOID)
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(preview_frame, text=" COMMAND PREVIEW ", font=("Segoe UI", 8, "bold"), bg=CLR_VOID, fg=CLR_FG_DIM).pack(side=tk.LEFT)
        self.cmd_preview = tk.Entry(preview_frame, bg=CLR_VOID, fg=CLR_GOLD, 
                                   font=("Consolas", 9), relief=tk.FLAT, insertbackground=CLR_VOID)
        self.cmd_preview.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.cmd_preview.insert(0, "pytest ...")

        # 5. Console
        console_frame = tk.Frame(self.main_container, bg=CLR_BORDER, padx=1, pady=1)
        console_frame.pack(fill=tk.BOTH, expand=True)
        
        self.console = scrolledtext.ScrolledText(console_frame, bg=CLR_CONSOLE, fg=CLR_FG, 
                                               font=("Consolas", 11), relief=tk.FLAT,
                                               insertbackground="white", borderwidth=0)
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Tags
        self.console.tag_config("passed", foreground=CLR_EMERALD)
        self.console.tag_config("failed", foreground=CLR_CRIMSON)
        self.console.tag_config("error", foreground=CLR_CRIMSON)
        self.console.tag_config("warning", foreground=CLR_GOLD)
        self.console.tag_config("marker", foreground=CLR_AZURE)
        self.console.tag_config("meta", foreground=CLR_FG_DIM)
        self.console.tag_config("oracle", foreground=CLR_GOLD, font=("Segoe UI", 11, "italic"))
        self.console.tag_config("oracle_header", foreground=CLR_AZURE, font=("Segoe UI", 12, "bold"))

    # --- Helper Methods ---
    def _create_section(self, parent, title, r, c):
        f = tk.Frame(parent, bg=CLR_SURFACE, highlightbackground=CLR_BORDER, highlightthickness=1, padx=15, pady=15)
        f.grid(row=r, column=c, sticky=tk.NSEW, padx=5)
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"), bg=CLR_SURFACE, fg=CLR_FG_DIM).place(x=10, y=-10)
        return f

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg=CLR_SURFACE, fg=CLR_FG, font=("Segoe UI", 10))

    def _check(self, parent, text, var, command=None):
        return tk.Checkbutton(parent, text=text, variable=var, command=command,
                             bg=CLR_SURFACE, fg=CLR_FG, selectcolor=CLR_VOID,
                             activebackground=CLR_SURFACE, activeforeground=CLR_FG,
                             font=("Segoe UI", 9))

    def _action_btn(self, parent, text, cmd, bg, fg, state="normal"):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, 
                     font=("Segoe UI", 10, "bold"), relief=tk.FLAT, 
                     padx=15, pady=5, state=state, activebackground=bg, activeforeground=fg)
        b.pack(side=tk.LEFT, padx=5)
        return b

    def _browse_target(self):
        path = filedialog.askopenfilename(initialdir=str(REPO_ROOT / "tests"), title="Select Test File")
        if path:
            rel_path = os.path.relpath(path, REPO_ROOT)
            self.target_var.set(rel_path)

    def _toggle_parallel(self):
        self.workers_spin.configure(state="normal" if self.parallel_var.get() else "disabled")

    # --- Execution Logic ---
    def log(self, message, newline=True, tag=None):
        self.console.configure(state="normal")
        if not tag:
            if "PASSED" in message: tag = "passed"
            elif "FAILED" in message: tag = "failed"
            elif "ERROR" in message: tag = "error"
            elif "WARNING" in message: tag = "warning"
            elif message.startswith("==>"): tag = "marker"
            elif message.startswith("===") or message.startswith("---"): tag = "meta"
        
        self.console.insert(tk.END, message + ("\n" if newline else ""), tag)
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def clear_output(self):
        self.console.configure(state="normal")
        self.console.delete(1.0, tk.END)
        self.console.configure(state="disabled")
        self.status_label.configure(text="READY", fg=CLR_FG_DIM)

    def _set_running_state(self, running: bool, status: str = "COMPLETED", color: str = CLR_EMERALD):
        self.is_running = running
        if running:
            self.btn_run.configure(state="disabled")
            self.btn_script.configure(state="disabled")
            self.btn_val.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.status_label.configure(text="RUNNING", fg=CLR_GOLD)
        else:
            self.btn_run.configure(state="normal")
            self.btn_script.configure(state="normal")
            self.btn_val.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.status_label.configure(text=status, fg=color)

    def _get_env(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        if self.experimental_var.get(): env["MOIRA_RUN_EXPERIMENTAL"] = "1"
        if self.templates_var.get(): env["MOIRA_RUN_TEMPLATES"] = "1"
        return env

    def run_pytest(self):
        args = [str(VENV_PYTHON), "-m", "pytest"]
        target = self.target_var.get().strip()
        if target:
            # On Windows, we must set posix=False to avoid backslash escaping
            args.extend(shlex.split(target, posix=(os.name != 'nt')))
        marker = self.marker_var.get()
        if marker != "All": args.extend(["-m", marker])
        if self.failfast_var.get(): args.append("-x")
        if self.verbose_var.get(): args.append("-v")
        else: args.append("-q")
        if self.parallel_var.get():
            args.append("-n")
            w = self.workers_var.get()
            args.append(str(w) if w > 0 else "auto")
        self._execute_command(args)

    def run_script(self):
        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning("No Target", "Please specify a script path in the Target field.")
            return
        
        # Ensure path is absolute or relative to REPO_ROOT
        path = Path(target)
        if not path.is_absolute():
            path = REPO_ROOT / path
            
        if not path.exists():
            messagebox.showerror("Not Found", f"The script was not found: {path}")
            return
            
        args = [str(VENV_PYTHON), str(path)]
        self._execute_command(args)

    def run_validation(self):
        p = REPO_ROOT / "scripts" / "run_validation.py"
        self._execute_command([str(VENV_PYTHON), str(p)])

    def _execute_command(self, args):
        if self.is_running: return
        self.clear_output()
        
        # Semantic Quoting for Preview
        if os.name == "nt":
            cmd_str = subprocess.list2cmdline(args)
        else:
            cmd_str = " ".join(shlex.quote(a) for a in args)
            
        self.cmd_preview.delete(0, tk.END)
        self.cmd_preview.insert(0, cmd_str)
        
        self.log(f"==> Initiating Ritual: {cmd_str}")
        self._set_running_state(True)
        threading.Thread(target=self._run_proc, args=(args,), daemon=True).start()

    def _run_proc(self, args):
        captured_output = []
        try:
            self.process = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", cwd=str(REPO_ROOT),
                env=self._get_env(), bufsize=1, universal_newlines=True
            )
            for line in iter(self.process.stdout.readline, ''):
                stripped = line.strip()
                captured_output.append(stripped)
                self.output_queue.put(stripped)
                
            self.process.stdout.close()
            rc = self.process.wait()
            self.output_queue.put(f"==> Process dissolved with code {rc}")
            
            # Pass captured output safely to the main thread for commentary
            full_text = "\n".join(captured_output)
            self.root.after(0, lambda: self._provide_commentary(full_text, rc, args))
            
            # Update status with truth
            if rc == 0:
                self.root.after(0, lambda: self._set_running_state(False, "PASSED", CLR_EMERALD))
            else:
                self.root.after(0, lambda: self._set_running_state(False, "FAILED", CLR_CRIMSON))
                
        except Exception as e:
            self.output_queue.put(f"==> Invocation Error: {e}")
            self.root.after(0, lambda: self._set_running_state(False, "ERROR", CLR_CRIMSON))

    def _provide_commentary(self, output, return_code, args):
        """Analyze the results and provide intelligent astrological commentary."""
        commentary = []
        
        # 1. Check for Deselection
        deselected_match = re.search(r"(\d+) deselected", output)
        collected_match = re.search(r"collected (\d+) items", output)
        selected_match = re.search(r"(\d+) selected", output)
        
        if deselected_match and (not selected_match or selected_match.group(1) == "0"):
            count = deselected_match.group(1)
            commentary.append(f"• OBSERVED: {count} tests were deselected. Your marker ritual (-m) or keyword filter (-k) is likely too restrictive for this file.")
            
        # 2. Check for 0 Collection
        if collected_match and collected_match.group(1) == "0":
            target_file = ""
            for arg in args:
                if arg.endswith(".py"): target_file = arg; break
            
            commentary.append(f"• OBSERVED: No tests were discovered.")
            if target_file:
                commentary.append(f"  - Ensure '{os.path.basename(target_file)}' follows the 'test_*.py' nomenclature.")
                commentary.append(f"  - Verify that the internal functions are anointed with the 'test_' prefix.")
            commentary.append("  - Consider using 'RUN SCRIPT' if this file is a standalone audit tool.")

        # 3. Check for specific script failures
        if "run_validation.py" in " ".join(args) and return_code != 0:
            commentary.append("• OBSERVED: Numerical validation failure. The engine's precision has diverged from the ERFA/SOFA canon.")
            commentary.append("  - Review the Delta (Δ) values in the console above to locate the divergence.")

        if commentary:
            self.log("\n" + "="*70, tag="meta")
            self.log(" MOIRA DIAGNOSTIC COMMENTARY ", tag="oracle_header")
            self.log("="*70, tag="meta")
            for line in commentary:
                self.log(line, tag="oracle")
            self.log("="*70 + "\n", tag="meta")

    def _start_queue_monitor(self):
        def m():
            try:
                while True:
                    item = self.output_queue.get_nowait()
                    self.log(item)
            except queue.Empty: pass
            self.root.after(100, m)
        self.root.after(100, m)

    def stop_execution(self):
        if self.process and self.process.poll() is None:
            self.log("==> Sending Termination Signal...")
            if os.name == 'nt': subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], capture_output=True, check=False)
            else: self.process.terminate()
            self._set_running_state(False, "STOPPED", CLR_GOLD)

    def save_log(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        f = filedialog.asksaveasfilename(defaultextension=".log", initialfile=f"moira_test_{ts}.log", title="Save Log")
        if f:
            try:
                with open(f, "w", encoding="utf-8") as file: file.write(self.console.get(1.0, tk.END))
                self.status_label.configure(text=f"SAVED: {os.path.basename(f)}", fg=CLR_EMERALD)
            except Exception as e: messagebox.showerror("Save Error", f"Could not save: {e}")

    def copy_summary(self):
        c = self.console.get(1.0, tk.END).strip().splitlines()
        if not c: return
        s = c[-1]
        for l in reversed(c):
            if any(k in l.lower() for k in ["passed", "failed", "verdict"]):
                s = l; break
        self.root.clipboard_clear()
        self.root.clipboard_append(s)
        self.status_label.configure(text="SUMMARY COPIED", fg=CLR_AZURE)

    def open_artifacts(self):
        p = REPO_ROOT / "tests" / "artifacts"
        if not p.exists(): messagebox.showinfo("Notice", "Artifacts directory not found."); return
        if os.name == 'nt': os.startfile(p)
        else: subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(p)])

if __name__ == "__main__":
    root = tk.Tk()
    # Apply a subtle dark theme to the underlying root components
    root.configure(bg=CLR_VOID)
    # Hide the ugly flash of white on startup
    root.withdraw()
    app = MoiraTestRunnerUI(root)
    root.deiconify()
    root.mainloop()
