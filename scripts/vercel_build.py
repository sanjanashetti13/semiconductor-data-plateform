"""
Build the React frontend for Vercel and copy artifacts where FastAPI can serve them.

Outputs:
  public/         — Vercel CDN static files
  backend/static/ — bundled with the Python serverless function
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"
TARGETS = (ROOT / "public", ROOT / "backend" / "static")


def main() -> int:
    if not FRONTEND.exists():
        print(f"Frontend directory missing: {FRONTEND}", file=sys.stderr)
        return 1

    print("npm install...")
    subprocess.check_call(["npm", "install"], cwd=FRONTEND, shell=(sys.platform == "win32"))
    print("npm run build...")
    subprocess.check_call(["npm", "run", "build"], cwd=FRONTEND, shell=(sys.platform == "win32"))

    if not (DIST / "index.html").exists():
        print(f"Build failed — missing {DIST / 'index.html'}", file=sys.stderr)
        return 1

    for dest in TARGETS:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(DIST, dest)
        print(f"Copied frontend dist → {dest}")

    print("Vercel frontend build complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
