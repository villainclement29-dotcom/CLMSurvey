from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from app.config import RSS_FEEDS, RSS_MAX_ITEMS_PER_FEED


def fetch_rss_items() -> list[dict]:
    items = []
    for feed_conf in RSS_FEEDS:
        parsed = feedparser.parse(feed_conf["url"])
        for entry in parsed.entries[:RSS_MAX_ITEMS_PER_FEED]:
            published_at = _extract_date(entry)
            items.append(
                {
                    "source": feed_conf["name"],
                    "category": feed_conf["category"],
                    "title": entry.get("title", "(sans titre)"),
                    "url": entry.get("link"),
                    "summary": _clean_summary(entry.get("summary", "")),
                    "published_at": published_at,
                }
            )
    return [i for i in items if i["url"]]


def _extract_date(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _clean_summary(raw: str) -> str:
    # Retire grossièrement les balises HTML des résumés RSS et décode les entités.
    import html
    import re

    text = re.sub("<[^<]+?>", "", raw)
    text = html.unescape(text)
    return " ".join(text.split())[:500]
