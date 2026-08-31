from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.config import ARXIV_API_URL, ARXIV_CATEGORIES, ARXIV_MAX_RESULTS_PER_CATEGORY

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def fetch_arxiv_items() -> list[dict]:
    """Interroge l'API arXiv pour chaque catégorie configurée et retourne une liste
    d'articles normalisés (source, category, title, url, summary, published_at)."""
    items = []
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for arxiv_cat, display_cat in ARXIV_CATEGORIES.items():
            params = {
                "search_query": f"cat:{arxiv_cat}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": ARXIV_MAX_RESULTS_PER_CATEGORY,
            }
            try:
                resp = client.get(ARXIV_API_URL, params=params)
                resp.raise_for_status()
            except httpx.HTTPError:
                continue
            items.extend(_parse_feed(resp.text, display_cat))
    return items


def _parse_feed(xml_text: str, display_cat: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    parsed = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        summary_el = entry.find(f"{ATOM_NS}summary")
        published_el = entry.find(f"{ATOM_NS}published")
        link = None
        for link_el in entry.findall(f"{ATOM_NS}link"):
            if link_el.get("rel") == "alternate" or link is None:
                link = link_el.get("href")
        if not (title_el is not None and link and published_el is not None):
            continue
        parsed.append(
            {
                "source": "arXiv",
                "category": display_cat,
                "title": " ".join(title_el.text.split()),
                "url": link,
                "summary": " ".join((summary_el.text or "").split())[:500] if summary_el is not None else "",
                "published_at": published_el.text,
            }
        )
    return parsed
