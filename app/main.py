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
from app.config import CATEGORIES
from app.db import (
    add_favorite,
    add_push_subscription,
    assign_favorites_to_folder,
    count_favorites_by_folder,
    create_folder,
    delete_event,
    favorited_item_ids,
    get_conn,
    get_folder,
    get_item,
    init_db,
    insert_event,
    is_favorited,
    list_events_on,
    list_favorites,
    list_folders,
    list_items,
    list_push_subscriptions,
    list_upcoming_events,
    remove_favorite,
    remove_push_subscription,
    save_ai_summary,
    set_favorite_folder,
)
from app.formatting import (
    day_number,
    days_until,
    format_date,
    group_by_date,
    group_events_by_date,
    is_today_str,
    month_year_label,
    split_today,
    weekday_label,
)
from app.push import send_push
from app.relevance import rank_and_cap, rank_and_cap_single
from app.summarizer import generate_summary

BASE_DIR = Path(__file__).resolve().parent


class _CachedStaticFiles(StaticFiles):
    """StaticFiles standard, sans en-tête Cache-Control : le navigateur ne
    fait que de la mise en cache heuristique et revalide souvent, ce qui
    repasse par la fonction serverless pour du CSS/des icônes qui changent
    rarement. On ajoute un Cache-Control raisonnable (le CSS est de toute
    façon invalidé via ?v={ASSET_VERSION} à chaque déploiement, donc un
    cache plus long ne peut pas servir de version périmée)."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers.setdefault("cache-control", "public, max-age=3600")
        return response


app = FastAPI(title="Veille scientifique")
app.mount("/static", _CachedStaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Change à chaque déploiement Vercel (hash de commit) : sert à invalider le
# cache navigateur du CSS et du service worker sans action manuelle.
ASSET_VERSION = os.environ.get("VERCEL_GIT_COMMIT_SHA", "dev")[:7]
templates.env.globals["ASSET_VERSION"] = ASSET_VERSION
# Clé publique VAPID : sûre à exposer côté client, nécessaire pour
# PushManager.subscribe(). La clé privée reste uniquement dans app/push.py.
templates.env.globals["VAPID_PUBLIC_KEY"] = os.environ.get("VAPID_PUBLIC_KEY", "")


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
templates.env.filters["weekday"] = weekday_label
templates.env.filters["day_number"] = day_number
templates.env.filters["month_year"] = month_year_label
templates.env.filters["is_today"] = is_today_str

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
            "favorited_ids": favorited_ids,
            "folders": folders,
        },
    )


@app.get("/archives")
def archives(request: Request, category: str = "Toutes", q: str = "", limit: int = PAGE_SIZE):
    search = q.strip() or None
    with get_conn() as conn:
        items = list_items(conn, category, limit=limit + 1, search=search, exclude_today=not search)
        favorited_ids = favorited_item_ids(conn)
        folders = list_folders(conn)
    has_more = len(items) > limit
    items = items[:limit]
    if search:
        # Résultats de recherche : liste plate (toutes dates confondues),
        # pas de regroupement par jour ni de plafond de pertinence.
        groups = [(f"Résultats pour « {search} »", items, len(items))] if items else []
    else:
        groups = [g for g in rank_and_cap(group_by_date(items), max_per_group=MAX_PER_DAY) if g[1]]
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
        {"request": request, "groups": groups, "categories": CATEGORIES},
    )


@app.post("/calendar/events")
def create_event(
    title: str = Form(...),
    event_date: str = Form(...),
    category: str = Form(...),
):
    title = title.strip()
    if title and category in CATEGORIES:
        with get_conn() as conn:
            insert_event(conn, None, title, event_date, category)
    return RedirectResponse(url="/calendar", status_code=303)


@app.post("/calendar/events/{event_id}/delete")
def delete_event_route(event_id: int):
    with get_conn() as conn:
        delete_event(conn, event_id)
    return RedirectResponse(url="/calendar", status_code=303)


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
            "unclassified": True,
            "items": items,
            "folders": folders,
            "favorited_ids": favorited_ids,
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
    notified = _send_daily_event_digest()
    return {"new_items": new_count, "notified": notified}


def _send_daily_event_digest() -> int:
    """Envoie une notification push résumant les événements du jour à tous
    les appareils abonnés. Retourne le nombre de notifications envoyées
    avec succès. Best-effort : un abonnement expiré est nettoyé, une autre
    erreur d'envoi n'empêche pas les suivants."""
    today_iso = datetime.utcnow().date().isoformat()
    with get_conn() as conn:
        todays_events = list_events_on(conn, today_iso)
        if not todays_events:
            return 0
        subscriptions = list_push_subscriptions(conn)
        if not subscriptions:
            return 0
        if len(todays_events) == 1:
            body = todays_events[0]["title"]
        else:
            titles = ", ".join(ev["title"] for ev in todays_events[:3])
            body = f"{len(todays_events)} événements aujourd'hui : {titles}"
        sent = 0
        for sub in subscriptions:
            result = send_push(sub, "Événements du jour", body, "/calendar")
            if result == "ok":
                sent += 1
            elif result == "expired":
                remove_push_subscription(conn, sub["endpoint"])
        return sent


@app.get("/push/vapid-public-key")
def vapid_public_key():
    return {"key": templates.env.globals["VAPID_PUBLIC_KEY"]}


@app.post("/push/subscribe")
async def push_subscribe(request: Request):
    data = await request.json()
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        raise HTTPException(status_code=400, detail="Abonnement invalide")
    with get_conn() as conn:
        add_push_subscription(conn, endpoint, keys["p256dh"], keys["auth"])
    return {"ok": True}


@app.post("/push/unsubscribe")
async def push_unsubscribe(request: Request):
    data = await request.json()
    endpoint = data.get("endpoint")
    if endpoint:
        with get_conn() as conn:
            remove_push_subscription(conn, endpoint)
    return {"ok": True}
