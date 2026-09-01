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
    """
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL UNIQUE REFERENCES items(id),
        folder_id INTEGER REFERENCES folders(id),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES items(id),
        title TEXT NOT NULL,
        event_date TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)",
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


def insert_item(conn, source: str, category: str, title: str, url: str, summary: str, published_at: str):
    """Insère un article. Retourne son id, ou None si l'URL existe déjà (dédup)."""
    if conn.execute("SELECT 1 FROM items WHERE url = ?", (url,)):
        return None
    rows = conn.execute(
        "INSERT INTO items (source, category, title, url, summary, published_at) "
        "VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
        (source, category, title, url, summary, published_at),
    )
    return rows[0]["id"]


def list_items(conn, category: str | None = None, limit: int = 60, search: str | None = None):
    clauses, params = [], []
    if category and category != "Toutes":
        clauses.append("category = ?")
        params.append(category)
    if search:
        clauses.append("(title LIKE ? OR summary LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    return conn.execute(f"SELECT * FROM items {where} ORDER BY published_at DESC LIMIT ?", tuple(params))


def get_item(conn, item_id: int):
    rows = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    return rows[0] if rows else None


def save_ai_summary(conn, item_id: int, ai_summary: str):
    conn.execute("UPDATE items SET ai_summary = ? WHERE id = ?", (ai_summary, item_id))
    conn.commit()


def favorited_item_ids(conn) -> set:
    rows = conn.execute("SELECT item_id FROM favorites")
    return {row["item_id"] for row in rows}


def is_favorited(conn, item_id: int) -> bool:
    return bool(conn.execute("SELECT 1 FROM favorites WHERE item_id = ?", (item_id,)))


def add_favorite(conn, item_id: int):
    if not is_favorited(conn, item_id):
        conn.execute("INSERT INTO favorites (item_id) VALUES (?)", (item_id,))
    conn.commit()


def remove_favorite(conn, item_id: int):
    conn.execute("DELETE FROM favorites WHERE item_id = ?", (item_id,))
    conn.commit()


def set_favorite_folder(conn, item_id: int, folder_id: int | None):
    conn.execute("UPDATE favorites SET folder_id = ? WHERE item_id = ?", (folder_id, item_id))
    conn.commit()


def create_folder(conn, name: str) -> int:
    existing = conn.execute("SELECT id FROM folders WHERE name = ?", (name,))
    if existing:
        return existing[0]["id"]
    rows = conn.execute("INSERT INTO folders (name) VALUES (?) RETURNING id", (name,))
    conn.commit()
    return rows[0]["id"]


def get_folder(conn, folder_id: int):
    rows = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
    return rows[0] if rows else None


def list_folders(conn):
    return conn.execute("SELECT * FROM folders ORDER BY name")


def count_favorites_by_folder(conn) -> dict:
    """Retourne {folder_id: nombre d'articles}, avec la clé None pour les non classés."""
    rows = conn.execute("SELECT folder_id, COUNT(*) AS n FROM favorites GROUP BY folder_id")
    return {row["folder_id"]: row["n"] for row in rows}


def list_favorites(conn, folder_id: int | None = None, only_unclassified: bool = False):
    """Retourne les favoris (avec les infos de l'article), les plus récents en premier.
    Sans filtre : tous les favoris. folder_id : ceux de ce dossier.
    only_unclassified=True : ceux sans dossier."""
    query = """
        SELECT items.*, favorites.folder_id AS folder_id
        FROM favorites
        JOIN items ON items.id = favorites.item_id
    """
    if only_unclassified:
        query += " WHERE favorites.folder_id IS NULL"
        params = ()
    elif folder_id is not None:
        query += " WHERE favorites.folder_id = ?"
        params = (folder_id,)
    else:
        params = ()
    query += " ORDER BY favorites.created_at DESC"
    return conn.execute(query, params)


def assign_favorites_to_folder(conn, item_ids: list[int], folder_id: int):
    for item_id in item_ids:
        conn.execute("UPDATE favorites SET folder_id = ? WHERE item_id = ?", (folder_id, item_id))
    conn.commit()


def insert_event(conn, item_id: int, title: str, event_date: str, category: str):
    conn.execute(
        "INSERT INTO events (item_id, title, event_date, category) VALUES (?, ?, ?, ?)",
        (item_id, title, event_date, category),
    )
    conn.commit()


def list_upcoming_events(conn, today_iso: str):
    """Événements futurs (>= aujourd'hui), avec l'URL de l'article source, triés par date."""
    return conn.execute(
        """
        SELECT events.*, items.url AS item_url
        FROM events
        JOIN items ON items.id = events.item_id
        WHERE events.event_date >= ?
        ORDER BY events.event_date ASC
        """,
        (today_iso,),
    )
