from __future__ import annotations

from app.db import get_conn, init_db, insert_event, insert_item
from app.events import MAX_EXTRACTIONS_PER_RUN, extract_event, looks_like_future_event
from app.fetchers.arxiv import fetch_arxiv_items
from app.fetchers.rss import fetch_rss_items


def run_collection() -> int:
    """Récupère les nouvelles publications de toutes les sources et les insère
    en base. Retourne le nombre de nouveaux articles ajoutés (les doublons,
    déjà vus via leur URL, sont ignorés).

    Pour chaque article réellement nouveau qui semble mentionner une date
    (pré-filtre gratuit), tente d'en extraire un événement futur pour le
    calendrier — plafonné par appel pour maîtriser le coût/la durée."""
    init_db()
    new_count = 0
    extractions_left = MAX_EXTRACTIONS_PER_RUN
    with get_conn() as conn:
        for item in fetch_arxiv_items() + fetch_rss_items():
            item_id = insert_item(
                conn,
                item["source"],
                item["category"],
                item["title"],
                item["url"],
                item["summary"],
                item["published_at"],
            )
            if item_id is None:
                continue
            new_count += 1
            if extractions_left > 0 and looks_like_future_event(f"{item['title']} {item['summary']}"):
                extractions_left -= 1
                event = extract_event(item["title"], item["url"], item["summary"], item["published_at"])
                if event:
                    insert_event(conn, item_id, event["title"], event["date"], item["category"])
        conn.commit()
    return new_count
