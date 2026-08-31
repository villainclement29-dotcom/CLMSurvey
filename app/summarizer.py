from __future__ import annotations

import os
import time

import trafilatura
from google import genai
from google.genai import errors as genai_errors

MODEL = "gemini-flash-latest"
MAX_ARTICLE_CHARS = 8000
MAX_SUMMARY_TOKENS = 400
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1

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
    """Génère un résumé en français via Gemini Flash (gratuit). Retente
    quelques fois en cas de surcharge temporaire (503) côté Google. Lève une
    exception si GOOGLE_API_KEY est absent ou si tous les essais échouent —
    à charge de l'appelant de gérer l'erreur côté UI."""
    article_text = _extract_article_text(url, fallback_text or title)
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    prompt = PROMPT_TEMPLATE.format(title=title, article_text=article_text)

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={"max_output_tokens": MAX_SUMMARY_TOKENS},
            )
            return response.text.strip()
        except genai_errors.ServerError as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
    raise last_error
