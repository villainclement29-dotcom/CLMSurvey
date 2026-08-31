from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.collector import run_collection
from app.config import CATEGORIES, CATEGORY_ICONS
from app.db import count_by_category, get_conn, get_item, init_db, list_items, save_ai_summary
from app.formatting import group_by_date
from app.summarizer import generate_summary

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Veille scientifique")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def favicon_url(article_url: str) -> str:
    domain = urlparse(article_url).netloc
    return f"https://www.google.com/s2/favicons?sz=32&domain={domain}"


templates.env.filters["favicon"] = favicon_url

init_db()

PAGE_SIZE = 60


@app.get("/")
def index(request: Request, category: str = "Toutes", refreshed: Optional[int] = None, limit: int = PAGE_SIZE):
    with get_conn() as conn:
        items = list_items(conn, category, limit=limit + 1)
        counts = count_by_category(conn)
    has_more = len(items) > limit
    items = items[:limit]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "groups": group_by_date(items),
            "categories": ["Toutes"] + CATEGORIES,
            "counts": counts,
            "selected": category,
            "refreshed": refreshed,
            "limit": limit,
            "page_size": PAGE_SIZE,
            "has_more": has_more,
            "cat_icons": CATEGORY_ICONS,
        },
    )


@app.post("/refresh")
def refresh():
    new_count = run_collection()
    return RedirectResponse(url=f"/?refreshed={new_count}", status_code=303)


@app.get("/article/{item_id}")
def article(request: Request, item_id: int):
    with get_conn() as conn:
        item = get_item(conn, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Article introuvable")
    return templates.TemplateResponse(
        "summary.html",
        {"request": request, "item": item, "cat_icons": CATEGORY_ICONS},
    )


@app.get("/api/summary/{item_id}")
def api_summary(item_id: int):
    with get_conn() as conn:
        item = get_item(conn, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Article introuvable")
        if item["ai_summary"]:
            return {"summary": item["ai_summary"]}
        try:
            summary = generate_summary(item["title"], item["url"], item["summary"] or "")
        except Exception as exc:
            print(f"[summary] échec pour item {item_id}: {type(exc).__name__}: {exc}")
            raise HTTPException(status_code=502, detail="Échec de la génération du résumé")
        save_ai_summary(conn, item_id, summary)
    return {"summary": summary}


@app.get("/cron")
def cron_refresh(authorization: Optional[str] = Header(default=None)):
    """Appelée quotidiennement par Vercel Cron (GET, header Authorization
    automatiquement injecté par Vercel à partir de la variable CRON_SECRET)."""
    secret = os.environ.get("CRON_SECRET")
    if secret and authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    new_count = run_collection()
    return {"new_items": new_count}
