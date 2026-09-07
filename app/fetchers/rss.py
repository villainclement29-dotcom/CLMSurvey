from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from app.config import RSS_FEEDS, RSS_MAX_ITEMS_PER_FEED

# Certains sites (ex: presse tech hébergée sur des CDN anti-bot) bloquent le
# user-agent par défaut de feedparser, qui s'identifie explicitement comme
# tel ("Python-feedparser/x.x.x") ; un user-agent de navigateur classique
# passe leurs filtres sans rien changer d'autre au comportement du flux.
_USER_AGENT = "Mozilla/5.0 (compatible; CLMSurveyBot/1.0)"


def fetch_rss_items() -> list[dict]:
    items = []
    for feed_conf in RSS_FEEDS:
        parsed = feedparser.parse(feed_conf["url"], agent=_USER_AGENT)
        if not parsed.entries:
            print(
                f"[rss] 0 entrée pour {feed_conf['name']} ({feed_conf['url']}): "
                f"status={parsed.get('status')} bozo_exception={parsed.get('bozo_exception')}"
            )
        for entry in parsed.entries[:RSS_MAX_ITEMS_PER_FEED]:
            published_at = _extract_date(entry)
            items.append(
                {
                    "source": feed_conf["name"],
                    "category": feed_conf["category"],
                    "title": _clean_title(entry.get("title", "(sans titre)")),
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


def _clean_title(raw: str) -> str:
    # Certains flux (ex: The Verge) renvoient des titres avec des entités
    # HTML échappées deux fois (ex: "&#8216;" au lieu de l'apostrophe
    # courbe) : feedparser ne les décode pas, il faut le faire nous-mêmes.
    import html

    return html.unescape(raw)


def _clean_summary(raw: str) -> str:
    # Retire grossièrement les balises HTML des résumés RSS et décode les entités.
    import html
    import re

    text = re.sub("<[^<]+?>", "", raw)
    text = html.unescape(text)
    return " ".join(text.split())[:500]
