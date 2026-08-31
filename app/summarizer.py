from __future__ import annotations

import os

import anthropic
import trafilatura

MODEL = "claude-haiku-4-5-20251001"
MAX_ARTICLE_CHARS = 8000
MAX_SUMMARY_TOKENS = 400

PROMPT_TEMPLATE = """Résume cet article en français, en 4 à 6 phrases claires \
et accessibles, pour quelqu'un qui n'a pas le temps de le lire en entier. \
Va droit au but, sans préambule ni titre.

Titre : {title}

Contenu :
{article_text}"""


def _extract_article_text(url: str, fallback: str) -> str:
    """Tente de récupérer le texte intégral de l'article. Retombe sur le
    court résumé déjà stocké (RSS/arXiv) si l'extraction échoue."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 200:
                return text[:MAX_ARTICLE_CHARS]
    except Exception:
        pass
    return fallback


def generate_summary(title: str, url: str, fallback_text: str) -> str:
    """Génère un résumé en français via Claude Haiku. Lève une exception si
    ANTHROPIC_API_KEY est absent ou si l'appel échoue — à charge de
    l'appelant de gérer l'erreur côté UI."""
    article_text = _extract_article_text(url, fallback_text or title)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_SUMMARY_TOKENS,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(title=title, article_text=article_text)}],
    )
    return response.content[0].text.strip()
