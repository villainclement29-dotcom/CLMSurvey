# Veille scientifique

Dashboard web pour suivre l'actualité sourcée en IA (au sens large, pas seulement
LLM), espace/exploration spatiale, astronomie et physique.

Sources : arXiv (par catégorie) + flux RSS de labs et agences officielles
(OpenAI, Anthropic, DeepMind, Meta AI, NASA, ESA). Voir [app/config.py](app/config.py)
pour la liste complète.

## Démarrer

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Ouvrir http://127.0.0.1:8000 puis cliquer sur "Rafraîchir" pour la première collecte.
