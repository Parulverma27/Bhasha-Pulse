"""Run this after setup to confirm your machine is ready:

    python scripts/check_env.py
"""
import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ok = True


def check(label: str, passed: bool, hint: str = "") -> None:
    global ok
    print(f"[{'PASS' if passed else 'FAIL'}] {label}" + (f"  -> {hint}" if not passed and hint else ""))
    ok = ok and passed


check("Python >= 3.10", sys.version_info >= (3, 10), "Install Python 3.10 or newer")
check("git installed", shutil.which("git") is not None, "Install Git")
check("node installed (needed for frontend)", shutil.which("node") is not None, "Install Node.js LTS")

for pkg in ("yaml", "dotenv", "fastapi", "uvicorn"):
    try:
        importlib.import_module(pkg)
        check(f"python package '{pkg}'", True)
    except ImportError:
        check(f"python package '{pkg}'", False, "Run: pip install -r requirements-dev.txt")

check(".env file exists", (ROOT / ".env").exists(), "Copy .env.example to .env")

try:
    from newsintel.config import get_settings

    s = get_settings()
    check(f"outlets.yaml loads ({len(s.outlets)} outlets)", len(s.outlets) > 0)
except Exception as e:  # noqa: BLE001
    check("outlets.yaml loads", False, str(e))

print("\nAll good! Ready for Milestone 1." if ok else "\nFix the FAIL items above, then run again.")
sys.exit(0 if ok else 1)
