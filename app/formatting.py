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
