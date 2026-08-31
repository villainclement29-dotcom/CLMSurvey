from __future__ import annotations

from app.db import get_conn, init_db, insert_item
from app.fetchers.arxiv import fetch_arxiv_items
from app.fetchers.rss import fetch_rss_items


def run_collection() -> int:
    """Récupère les nouvelles publications de toutes les sources et les insère
    en base. Retourne le nombre de nouveaux articles ajoutés (les doublons,
    déjà vus via leur URL, sont ignorés)."""
    init_db()
    new_count = 0
    with get_conn() as conn:
        for item in fetch_arxiv_items() + fetch_rss_items():
            if insert_item(
                conn,
                item["source"],
                item["category"],
                item["title"],
                item["url"],
                item["summary"],
                item["published_at"],
            ):
                new_count += 1
        conn.commit()
    return new_count
