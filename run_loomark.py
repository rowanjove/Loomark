import os
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run():
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = Path(sys.executable)

    print("==================================================")
    print("        Loomark - Web Intelligence Engine         ")
    print("==================================================")
    print(f"[*] Python Runtime: {venv_python}")
    print("[*] Starting Backend Server on http://127.0.0.1:8765 ...")

    backend_proc = subprocess.Popen(
        [str(venv_python), "-m", "engine.main", "--port", "8765"],
        cwd=str(BASE_DIR)
    )

    time.sleep(1.5)

    print("[*] Starting Frontend Dev Server on http://localhost:1420 ...")
    try:
        frontend_proc = subprocess.run(
            ["pnpm", "dev"],
            cwd=str(BASE_DIR),
            shell=True
        )
    except KeyboardInterrupt:
        pass
    finally:
        print("[*] Shutting down backend engine...")
        backend_proc.terminate()
        backend_proc.wait()

if __name__ == "__main__":
    run()
