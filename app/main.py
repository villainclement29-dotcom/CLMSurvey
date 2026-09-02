from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.collector import run_collection
from app.config import CATEGORIES, CATEGORY_ICONS
from app.db import (
    add_favorite,
    assign_favorites_to_folder,
    count_favorites_by_folder,
    create_folder,
    favorited_item_ids,
    get_conn,
    get_folder,
    get_item,
    init_db,
    is_favorited,
    list_favorites,
    list_folders,
    list_items,
    list_upcoming_events,
    remove_favorite,
    save_ai_summary,
    set_favorite_folder,
)
from app.formatting import days_until, format_date, group_by_date, group_events_by_date, split_today
from app.relevance import rank_and_cap, rank_and_cap_single
from app.summarizer import generate_summary

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Veille scientifique")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Change à chaque déploiement Vercel (hash de commit) : sert à invalider le
# cache navigateur du CSS et du service worker sans action manuelle.
ASSET_VERSION = os.environ.get("VERCEL_GIT_COMMIT_SHA", "dev")[:7]
templates.env.globals["ASSET_VERSION"] = ASSET_VERSION


@app.get("/sw.js")
def service_worker():
    """Servi à la racine (pas sous /static) pour que le scope du service
    worker couvre tout le site, pas seulement /static/. Le CACHE_NAME est
    tagué avec ASSET_VERSION pour forcer un rafraîchissement du cache du
    service worker à chaque déploiement."""
    content = (BASE_DIR / "static" / "sw.js").read_text()
    content = content.replace("veille-static-v1", f"veille-static-{ASSET_VERSION}")
    return Response(content=content, media_type="application/javascript")


def favicon_url(article_url: str) -> str:
    domain = urlparse(article_url).netloc
    return f"https://www.google.com/s2/favicons?sz=32&domain={domain}"


templates.env.filters["favicon"] = favicon_url
templates.env.filters["date"] = format_date
templates.env.filters["days_until"] = days_until

init_db()

PAGE_SIZE = 60
MAX_PER_DAY = 10
HOME_POOL_LIMIT = 300  # large pool à filtrer pour retrouver les articles du jour


@app.get("/")
def index(request: Request, category: str = "Toutes", refreshed: Optional[int] = None):
    with get_conn() as conn:
        items = list_items(conn, category, limit=HOME_POOL_LIMIT)
        favorited_ids = favorited_item_ids(conn)
        folders = list_folders(conn)
    today_items, _ = split_today(items)
    kept_items, total_today = rank_and_cap_single(today_items, max_items=MAX_PER_DAY)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "items": kept_items,
            "total_today": total_today,
            "categories": ["Toutes"] + CATEGORIES,
            "selected": category,
            "refreshed": refreshed,
            "cat_icons": CATEGORY_ICONS,
            "favorited_ids": favorited_ids,
            "folders": folders,
        },
    )


@app.get("/archives")
def archives(request: Request, category: str = "Toutes", q: str = "", limit: int = PAGE_SIZE):
    search = q.strip() or None
    with get_conn() as conn:
        items = list_items(conn, category, limit=limit + 1, search=search)
        favorited_ids = favorited_item_ids(conn)
        folders = list_folders(conn)
    has_more = len(items) > limit
    items = items[:limit]
    if search:
        # Résultats de recherche : liste plate (toutes dates confondues),
        # pas de regroupement par jour ni de plafond de pertinence.
        groups = [(f"Résultats pour « {search} »", items, len(items))] if items else []
    else:
        _, older_items = split_today(items)
        groups = [g for g in rank_and_cap(group_by_date(older_items), max_per_group=MAX_PER_DAY) if g[1]]
    return templates.TemplateResponse(
        "archives.html",
        {
            "request": request,
            "groups": groups,
            "categories": ["Toutes"] + CATEGORIES,
            "selected": category,
            "search": q,
            "limit": limit,
            "page_size": PAGE_SIZE,
            "has_more": has_more,
            "cat_icons": CATEGORY_ICONS,
            "favorited_ids": favorited_ids,
            "folders": folders,
        },
    )


@app.get("/calendar")
def calendar_page(request: Request):
    today_iso = datetime.utcnow().date().isoformat()
    with get_conn() as conn:
        events = list_upcoming_events(conn, today_iso)
    groups = group_events_by_date(events)
    return templates.TemplateResponse(
        "calendar.html",
        {"request": request, "groups": groups, "cat_icons": CATEGORY_ICONS},
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
        favorited = is_favorited(conn, item_id)
        folders = list_folders(conn)
    return templates.TemplateResponse(
        "summary.html",
        {
            "request": request,
            "item": item,
            "cat_icons": CATEGORY_ICONS,
            "favorited": favorited,
            "folders": folders,
        },
    )


@app.post("/favorites/{item_id}/toggle")
def toggle_favorite(item_id: int, next: str = Form("/")):
    with get_conn() as conn:
        if get_item(conn, item_id) is None:
            raise HTTPException(status_code=404, detail="Article introuvable")
        if is_favorited(conn, item_id):
            remove_favorite(conn, item_id)
        else:
            add_favorite(conn, item_id)
    return RedirectResponse(url=next, status_code=303)


@app.get("/favorites")
def favorites_page(request: Request):
    """Page de listing des dossiers (façon appli Notes)."""
    with get_conn() as conn:
        folders = list_folders(conn)
        counts = count_favorites_by_folder(conn)
        unclassified_items = list_favorites(conn, only_unclassified=True)
    return templates.TemplateResponse(
        "favorites.html",
        {
            "request": request,
            "folders": folders,
            "counts": counts,
            "unclassified_items": unclassified_items,
        },
    )


@app.get("/favorites/unclassified")
def favorites_unclassified(request: Request):
    with get_conn() as conn:
        items = list_favorites(conn, only_unclassified=True)
        folders = list_folders(conn)
        favorited_ids = favorited_item_ids(conn)
    return templates.TemplateResponse(
        "favorites_list.html",
        {
            "request": request,
            "title": "Non classés",
            "items": items,
            "folders": folders,
            "favorited_ids": favorited_ids,
            "cat_icons": CATEGORY_ICONS,
            "next": "/favorites/unclassified",
        },
    )


@app.get("/favorites/folder/{folder_id}")
def favorites_folder(request: Request, folder_id: int):
    with get_conn() as conn:
        folder = get_folder(conn, folder_id)
        if folder is None:
            raise HTTPException(status_code=404, detail="Dossier introuvable")
        items = list_favorites(conn, folder_id=folder_id)
        folders = list_folders(conn)
        favorited_ids = favorited_item_ids(conn)
    return templates.TemplateResponse(
        "favorites_list.html",
        {
            "request": request,
            "title": folder["name"],
            "items": items,
            "folders": folders,
            "favorited_ids": favorited_ids,
            "cat_icons": CATEGORY_ICONS,
            "next": f"/favorites/folder/{folder_id}",
        },
    )


@app.post("/folders")
def create_folder_route(name: str = Form(...), item_ids: list[int] = Form(default=[])):
    name = name.strip()
    if not name:
        return RedirectResponse(url="/favorites", status_code=303)
    with get_conn() as conn:
        folder_id = create_folder(conn, name)
        if item_ids:
            assign_favorites_to_folder(conn, item_ids, folder_id)
    return RedirectResponse(url=f"/favorites/folder/{folder_id}", status_code=303)


@app.post("/favorites/{item_id}/folder")
def assign_favorite_folder(item_id: int, folder_id: str = Form(...), next: str = Form("/favorites")):
    fid = int(folder_id) if folder_id and folder_id != "none" else None
    with get_conn() as conn:
        if get_item(conn, item_id) is None:
            raise HTTPException(status_code=404, detail="Article introuvable")
        if not is_favorited(conn, item_id):
            add_favorite(conn, item_id)
        set_favorite_folder(conn, item_id, fid)
    return RedirectResponse(url=next, status_code=303)


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
