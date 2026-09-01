"""Détection d'événements futurs annoncés dans les articles (lancement de
fusée, sortie spatiale, publication de résultats, conférence...) pour le
calendrier. Deux étapes pour maîtriser le coût :
1. Un pré-filtre gratuit (regex) qui repère les articles mentionnant une
   date — la grande majorité des articles n'en ont pas et sont écartés
   sans jamais appeler l'IA.
2. Pour ceux qui passent le pré-filtre, un appel IA (Groq) qui extrait la
   date exacte et le titre de l'événement, ou confirme qu'il n'y en a pas.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

from groq import Groq

from app.summarizer import MODEL, _extract_article_text

_MONTHS = (
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan\.|Feb\.|Mar\.|Apr\.|Jun\.|Jul\.|Aug\.|Sept?\.|Oct\.|Nov\.|Dec\."
)
DATE_MENTION_PATTERN = re.compile(rf"(?:{_MONTHS})\s+\d{{1,2}}", re.IGNORECASE)

MAX_EXTRACTIONS_PER_RUN = 8

EVENT_PROMPT = """Cet article mentionne-t-il un événement FUTUR à une date précise \
(lancement de fusée/mission, sortie spatiale, publication de résultats, conférence, \
lancement de modèle...) ? Ignore la date de publication de l'article elle-même et \
les événements déjà passés.

Réponds UNIQUEMENT avec un objet JSON, sans aucun texte autour :
- Si oui : {{"has_event": true, "date": "YYYY-MM-DD", "title": "titre court et clair de l'événement en français"}}
- Si non : {{"has_event": false}}

Date de publication de l'article (référence) : {published_at}
Titre : {title}

Contenu :
{article_text}"""


def looks_like_future_event(text: str) -> bool:
    """Pré-filtre gratuit : l'article mentionne-t-il une date au format
    'Month Day' ? Généreux volontairement — le tri fin se fait par l'IA."""
    return bool(DATE_MENTION_PATTERN.search(text or ""))


def extract_event(title: str, url: str, fallback_text: str, published_at: str) -> dict | None:
    """Retourne {"date": "YYYY-MM-DD", "title": ...} si un événement futur
    est détecté, sinon None. Best-effort : toute erreur (réseau, IA, JSON
    invalide, date passée) retourne simplement None."""
    try:
        article_text = _extract_article_text(url, fallback_text or title)
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=800,
            reasoning_effort="low",
            messages=[
                {
                    "role": "user",
                    "content": EVENT_PROMPT.format(
                        title=title, article_text=article_text, published_at=published_at
                    ),
                }
            ],
        )
        raw = response.choices[0].message.content.strip()
        print(f"[events] réponse brute pour {url!r}: {raw!r}")
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        if not data.get("has_event"):
            return None
        event_date = data.get("date")
        event_title = data.get("title")
        if not event_date or not event_title:
            return None
        if date.fromisoformat(event_date) < date.today():
            return None
        return {"date": event_date, "title": event_title}
    except Exception as exc:
        print(f"[events] échec extraction pour {url!r}: {type(exc).__name__}: {exc}")
        return None
