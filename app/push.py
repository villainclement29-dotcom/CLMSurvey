"""Envoi de notifications push (Web Push standard) aux appareils abonnés.
Best-effort : un abonnement expiré/révoqué ne doit jamais faire échouer
l'envoi aux autres — on le signale pour nettoyage plutôt que de lever."""
from __future__ import annotations

import json
import os

from pywebpush import WebPushException, webpush

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:contact@example.com")


def send_push(subscription_row, title: str, body: str, url: str = "/calendar") -> str:
    """Retourne "ok", "expired" (abonnement à supprimer), "error" ou
    "no_key" (VAPID_PRIVATE_KEY absent, notifications pas configurées)."""
    if not VAPID_PRIVATE_KEY:
        return "no_key"
    subscription_info = {
        "endpoint": subscription_row["endpoint"],
        "keys": {"p256dh": subscription_row["p256dh"], "auth": subscription_row["auth"]},
    }
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIM_EMAIL},
        )
        return "ok"
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        return "expired" if status in (404, 410) else "error"
    except Exception:
        # Best-effort : une clé mal formée, un timeout réseau ou toute
        # autre erreur inattendue ne doit jamais faire planter l'envoi
        # groupé aux autres abonnés.
        return "error"
