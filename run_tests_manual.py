import subprocess
import sys
import os

def run():
    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        # try unix path just in case
        venv_python = os.path.join(".venv", "bin", "python")
        
    print(f"Using python: {venv_python}")
    
    # Run a simple test first
    cmd = [venv_python, "-m", "pytest", "tests/unit/test_julian_delta_t.py", "-v"]
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    with open("test_results.txt", "w", encoding="utf-8") as f:
        f.write("--- STDOUT ---\n")
        f.write(result.stdout)
        f.write("\n--- STDERR ---\n")
        f.write(result.stderr)
    
    print("Done. Output written to test_results.txt")

if __name__ == "__main__":
    run()
