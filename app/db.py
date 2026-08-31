from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    summary TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def insert_item(conn, source: str, category: str, title: str, url: str, summary: str, published_at: str) -> bool:
    """Insère un article. Retourne False si l'URL existe déjà (dédup)."""
    try:
        conn.execute(
            "INSERT INTO items (source, category, title, url, summary, published_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (source, category, title, url, summary, published_at),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def list_items(conn, category: str | None = None, limit: int = 60):
    if category and category != "Toutes":
        rows = conn.execute(
            "SELECT * FROM items WHERE category = ? ORDER BY published_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM items ORDER BY published_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return rows


def count_by_category(conn) -> dict:
    """Retourne {catégorie: nombre d'articles}, plus la clé 'Toutes' pour le total."""
    rows = conn.execute("SELECT category, COUNT(*) AS n FROM items GROUP BY category").fetchall()
    counts = {row["category"]: row["n"] for row in rows}
    counts["Toutes"] = sum(counts.values())
    return counts
