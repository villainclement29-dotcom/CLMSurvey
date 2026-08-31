# Notes de déploiement & rollback

## Ce qui a changé le 2026-08-31 : passage en ligne (Vercel + Turso)

L'app tournait uniquement en local (SQLite + `launchd`). Elle est
maintenant aussi déployée en ligne sur Vercel, avec Turso comme base de
données de production. Le code reste **rétrocompatible** : sans les
variables d'environnement `TURSO_*`, l'app retombe automatiquement sur
SQLite local (voir `app/db.py`).

### Ressources créées

| Ressource | Détail |
|---|---|
| Site en ligne | https://clmsurvey.vercel.app |
| Projet Vercel | `clements-projects-94226e0d/clmsurvey` (compte `villainclement29-dotcom`) |
| Base Turso | `clmsurvey` (région `aws-eu-west-1`), URL `libsql://clmsurvey-clxm.aws-eu-west-1.turso.io` |
| Variables d'env Vercel (production) | `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `CRON_SECRET` |
| Repo GitHub ↔ Vercel | connecté : chaque `git push` sur `main` redéploie automatiquement |

### Fichiers ajoutés/modifiés pour le déploiement

- `api/index.py` (nouveau) — entrypoint serverless
- `vercel.json` (nouveau) — routage + Vercel Cron Job quotidien (`0 7 * * *` → `GET /cron`)
- `.vercelignore` (nouveau)
- `app/db.py` — bascule SQLite local ↔ Turso selon `TURSO_DATABASE_URL`
- `app/main.py` — chemins absolus pour static/templates (nécessaire en serverless) + route `GET /cron` protégée par `CRON_SECRET`
- `requirements.txt` — ajout de `libsql-client`

Commit correspondant : `563d867` — "Déploiement sur Vercel avec Turso".

## Tâche `launchd` locale — désactivée (pas supprimée)

La collecte quotidienne automatique en local (via `launchd`, 7h00, écrivant
dans `app/data.db`) a été **désactivée le 2026-08-31** car redondante avec
le Vercel Cron Job (qui, lui, alimente Turso — la base utilisée par le site
en ligne). La config n'a pas été supprimée, seulement déchargée.

- Label : `com.clementvillain.veillescientifique.fetch`
- Plist : `~/Library/LaunchAgents/com.clementvillain.veillescientifique.fetch.plist`
- Script : `scripts/daily_fetch.py` → écrit dans `app/data.db` (SQLite local)
- Logs : `logs/daily_fetch.log`, `logs/daily_fetch.err.log`

**Pour la réactiver** (ex: reprendre une collecte locale indépendante du site en ligne) :

```bash
launchctl load ~/Library/LaunchAgents/com.clementvillain.veillescientifique.fetch.plist
```

**Pour vérifier si elle est active :**

```bash
launchctl list | grep veillescientifique
```

## Rollback complet (abandonner Vercel/Turso, revenir 100% local)

1. Réactiver la tâche locale (commande ci-dessus).
2. Optionnel — supprimer les ressources cloud :
   ```bash
   vercel project rm clmsurvey
   turso db destroy clmsurvey
   ```
3. Le code n'a pas besoin d'être modifié : sans `TURSO_DATABASE_URL` défini,
   `app/db.py` utilise déjà SQLite local automatiquement. Si vous voulez
   quand même retirer le code lié à Vercel/Turso :
   ```bash
   git revert 563d867
   ```
