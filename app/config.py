"""Liste des sources suivies, regroupées par catégorie."""

# Catégories affichées dans l'UI, avec leur icône (les couleurs associées
# vivent dans app/static/style.css, indexées par le même nom de catégorie).
CATEGORIES = ["IA", "Espace", "Astronomie", "Physique"]

CATEGORY_ICONS = {"IA": "🤖", "Espace": "🚀", "Astronomie": "🔭", "Physique": "⚛️"}

# arXiv : on interroge l'API par catégorie, chaque catégorie arXiv est
# mappée vers une catégorie affichée. cs.AI/cs.LG/cs.CV/cs.RO/cs.CL couvrent
# l'IA au sens large (pas seulement les LLM).
ARXIV_CATEGORIES = {
    "cs.AI": "IA",
    "cs.LG": "IA",
    "cs.CV": "IA",
    "cs.RO": "IA",
    "cs.CL": "IA",
    "astro-ph.GA": "Astronomie",
    "astro-ph.CO": "Astronomie",
    "astro-ph.EP": "Astronomie",
    "astro-ph.SR": "Astronomie",
    "physics.space-ph": "Espace",
    "gr-qc": "Physique",
    "hep-th": "Physique",
    "quant-ph": "Physique",
}

# Flux RSS de labs/agences officielles.
# Anthropic et Meta AI ne publient pas de flux RSS public (testé : 404 sur les
# chemins habituels) — retirés pour l'instant, à remplacer par du scraping
# dédié si besoin plus tard.
RSS_FEEDS = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "category": "IA"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "category": "IA"},
    {"name": "NASA", "url": "https://www.nasa.gov/news-release/feed/", "category": "Espace"},
    {"name": "ESA", "url": "https://www.esa.int/rssfeed/Our_Activities/Space_News", "category": "Espace"},
    {"name": "NASA Science", "url": "https://science.nasa.gov/feed/", "category": "Astronomie"},
]

# Certains flux (ex: OpenAI) renvoient tout leur historique plutôt que les
# dernières publications : on ne garde que les N plus récentes entrées.
RSS_MAX_ITEMS_PER_FEED = 25

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_MAX_RESULTS_PER_CATEGORY = 15

DB_PATH = "app/data.db"
