"""Accès base de données.

En local (et pour le job launchd), on utilise un fichier SQLite classique.
En production sur Vercel, le système de fichiers est éphémère : on bascule
automatiquement sur Turso (SQLite hébergé) dès que TURSO_DATABASE_URL est
défini. Les deux backends exposent la même interface minimale
(execute/commit/close) pour que le reste du code (insert_item, list_items...)
soit écrit une seule fois, indépendamment du backend.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH

TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        summary TEXT,
        published_at TEXT,
        fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)",
    "CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at)",
]


class _SqliteConn:
    def __init__(self):
        self._conn = sqlite3.connect(DB_PATH)
        self._conn.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        return self._conn.execute(sql, params).fetchall()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


class _TursoConn:
    def __init__(self):
        import libsql_client

        self._client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

    def execute(self, sql, params=()):
        return self._client.execute(sql, list(params)).rows

    def commit(self):
        pass  # chaque execute() est déjà validé côté serveur Turso

    def close(self):
        self._client.close()


@contextmanager
def get_conn():
    conn = _TursoConn() if TURSO_URL else _SqliteConn()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        try:
            conn.execute("ALTER TABLE items ADD COLUMN ai_summary TEXT")
        except Exception:
            pass  # colonne déjà présente (migration idempotente)
        conn.commit()


def insert_item(conn, source: str, category: str, title: str, url: str, summary: str, published_at: str) -> bool:
    """Insère un article. Retourne False si l'URL existe déjà (dédup)."""
    if conn.execute("SELECT 1 FROM items WHERE url = ?", (url,)):
        return False
    conn.execute(
        "INSERT INTO items (source, category, title, url, summary, published_at) VALUES (?, ?, ?, ?, ?, ?)",
        (source, category, title, url, summary, published_at),
    )
    return True


def list_items(conn, category: str | None = None, limit: int = 60):
    if category and category != "Toutes":
        return conn.execute(
            "SELECT * FROM items WHERE category = ? ORDER BY published_at DESC LIMIT ?",
            (category, limit),
        )
    return conn.execute("SELECT * FROM items ORDER BY published_at DESC LIMIT ?", (limit,))


def count_by_category(conn) -> dict:
    """Retourne {catégorie: nombre d'articles}, plus la clé 'Toutes' pour le total."""
    rows = conn.execute("SELECT category, COUNT(*) AS n FROM items GROUP BY category")
    counts = {row["category"]: row["n"] for row in rows}
    counts["Toutes"] = sum(counts.values())
    return counts


def get_item(conn, item_id: int):
    rows = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    return rows[0] if rows else None


def save_ai_summary(conn, item_id: int, ai_summary: str):
    conn.execute("UPDATE items SET ai_summary = ? WHERE id = ?", (ai_summary, item_id))
    conn.commit()
