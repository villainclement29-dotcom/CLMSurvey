from __future__ import annotations

from datetime import date, datetime, timedelta

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _parse_date(published_at: str) -> date | None:
    if not published_at:
        return None
    try:
        return datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def date_label(published_at: str, today: date) -> str:
    d = _parse_date(published_at)
    if d is None:
        return "Date inconnue"
    if d == today:
        return "Aujourd'hui"
    if d == today - timedelta(days=1):
        return "Hier"
    if d >= today - timedelta(days=6):
        return "Cette semaine"
    return f"{d.day} {MONTHS_FR[d.month - 1]} {d.year}"


def format_date(published_at: str) -> str:
    """Formate une date pour l'affichage sur une carte article, ex: '31 août 2026'."""
    d = _parse_date(published_at)
    if d is None:
        return ""
    return f"{d.day} {MONTHS_FR[d.month - 1]} {d.year}"


def split_today(items, today: date | None = None) -> tuple[list, list]:
    """Sépare les articles en (ceux collectés aujourd'hui, les plus anciens).

    On se base sur fetched_at (date de collecte), pas published_at (date de
    publication d'origine) : les flux RSS/arXiv indexent souvent un article
    avec un published_at de la veille, même quand on le découvre pour la
    première fois aujourd'hui. Filtrer sur published_at faisait passer la
    quasi-totalité du contenu fraîchement collecté directement aux archives,
    sans jamais apparaître sur l'accueil."""
    today = today or datetime.utcnow().date()
    today_items, older_items = [], []
    for item in items:
        (today_items if _parse_date(item["fetched_at"]) == today else older_items).append(item)
    return today_items, older_items


def group_by_date(items, today: date | None = None) -> list[tuple[str, list]]:
    """Regroupe une liste d'articles (triée par date décroissante) en groupes
    (libellé, articles) en préservant l'ordre chronologique."""
    today = today or datetime.utcnow().date()
    groups: list[tuple[str, list]] = []
    current_label = None
    for item in items:
        label = date_label(item["published_at"], today)
        if label != current_label:
            groups.append((label, []))
            current_label = label
        groups[-1][1].append(item)
    return groups


def group_events_by_date(events) -> list[tuple[str, list]]:
    """Regroupe des événements (triés par event_date croissant) par date exacte."""
    groups: list[tuple[str, list]] = []
    current_date = None
    for ev in events:
        if ev["event_date"] != current_date:
            groups.append((ev["event_date"], []))
            current_date = ev["event_date"]
        groups[-1][1].append(ev)
    return groups


def days_until(event_date: str, today: date | None = None) -> int:
    today = today or datetime.utcnow().date()
    d = date.fromisoformat(event_date)
    return (d - today).days
