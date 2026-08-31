"""Script indépendant, appelé chaque jour par launchd pour collecter les
nouvelles publications sans que le serveur web soit lancé."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collector import run_collection  # noqa: E402

if __name__ == "__main__":
    new_count = run_collection()
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {new_count} nouvel(le/aux) article(s) ajouté(s).")
