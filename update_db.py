#!/usr/bin/env python3
"""
Copy the latest SQLite DB from the main project and rebuild views.

Usage:
    python update_db.py /path/to/music_league.db

This script:
1. Copies the source DB into data/music_league.db
2. Re-creates all SQL views from data/views.sql
3. Verifies the views exist

Run this after a fresh scrape to update the deployed dashboard data.
Then commit + push to update the live Streamlit app.
"""

import shutil
import sqlite3
import sys
from pathlib import Path

DEPLOY_DIR = Path(__file__).parent
DB_DEST = DEPLOY_DIR / "data" / "music_league.db"
VIEWS_SQL = DEPLOY_DIR / "data" / "views.sql"


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} /path/to/music_league.db")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"Source DB not found: {src}")
        sys.exit(1)

    # 1. Copy DB
    DB_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, DB_DEST)
    print(f"Copied {src} → {DB_DEST}")

    # 2. Rebuild views
    if VIEWS_SQL.exists():
        conn = sqlite3.connect(str(DB_DEST))
        views_sql = VIEWS_SQL.read_text()
        conn.executescript(views_sql)
        conn.close()
        print("Views rebuilt from views.sql")
    else:
        print("Warning: views.sql not found — views may be missing")

    # 3. Verify
    conn = sqlite3.connect(str(DB_DEST))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    )
    views = [row[0] for row in cursor.fetchall()]
    conn.close()
    print(f"DB has {len(views)} views: {', '.join(views)}")
    print("Done. Commit and push to update the live app.")


if __name__ == "__main__":
    main()
