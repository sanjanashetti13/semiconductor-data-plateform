"""
Legacy entry point — delegates to the modular AI Copilot.

Prefer running from the project root:

    python app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when launched as scripts/ai_copilot.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import main

if __name__ == "__main__":
    main()
