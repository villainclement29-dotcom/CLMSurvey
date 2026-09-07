"""Liste des sources suivies, regroupées par catégorie."""

# Catégories affichées dans l'UI (icônes SVG dans app/templates/_icons.html,
# couleurs associées dans app/static/style.css — indexées par ce même nom).
CATEGORIES = ["IA", "Espace", "Astronomie", "Physique"]

# arXiv : on interroge l'API par catégorie, chaque catégorie arXiv est
# mappée vers une catégorie affichée. cs.AI/cs.LG/cs.CV/cs.RO/cs.CL couvrent
# l'IA au sens large (pas seulement les LLM).
# Astronomie/Espace/Physique ne passent plus par arXiv (papiers de recherche
# bruts, peu accessibles pour de la veille) : couverts uniquement par de la
# presse spécialisée/agrégateurs ci-dessous (NASA, ESA, Phys.org, Universe
# Today...).
ARXIV_CATEGORIES = {
    "cs.AI": "IA",
    "cs.LG": "IA",
    "cs.CV": "IA",
    "cs.RO": "IA",
    "cs.CL": "IA",
}

# Flux RSS de labs/agences officielles, complétés par de la presse tech
# généraliste pour la catégorie IA : les blogs officiels (OpenAI, DeepMind)
# ne couvrent pas toujours les annonces de façon détaillée/rapide, et les
# gros lancements de modèles se retrouvaient noyés sous les papiers arXiv.
# Anthropic, Meta AI et Mistral AI ne publient pas de flux RSS public (testé :
# 404 sur les chemins habituels), et CNES/SpaceNews ont un flux technique mais
# inexploitable (menus de navigation ou actus trop corporate/B2B, pas de
# vraies actus grand public) — retirés pour l'instant.
RSS_FEEDS = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "category": "IA"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "category": "IA"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "IA"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "IA"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": "IA"},
    {"name": "The Gradient", "url": "https://thegradient.pub/rss/", "category": "IA"},
    {"name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "category": "IA"},
    {"name": "NVIDIA Developer", "url": "https://developer.nvidia.com/blog/feed/", "category": "IA"},
    {"name": "ActuIA", "url": "https://www.actuia.com/feed/", "category": "IA"},
    {"name": "NASA", "url": "https://www.nasa.gov/news-release/feed/", "category": "Espace"},
    {"name": "ESA", "url": "https://www.esa.int/rssfeed/Our_Activities/Space_News", "category": "Espace"},
    {"name": "Space.com", "url": "https://www.space.com/feeds/all", "category": "Espace"},
    {"name": "Phys.org Espace", "url": "https://phys.org/rss-feed/space-news/", "category": "Espace"},
    {"name": "NASA Science", "url": "https://science.nasa.gov/feed/", "category": "Astronomie"},
    {"name": "Universe Today", "url": "https://www.universetoday.com/feed/", "category": "Astronomie"},
    {"name": "EarthSky", "url": "https://earthsky.org/feed/", "category": "Astronomie"},
    {"name": "Phys.org Astronomie", "url": "https://phys.org/rss-feed/space-news/astronomy/", "category": "Astronomie"},
    {"name": "Physics World", "url": "https://physicsworld.com/feed/", "category": "Physique"},
    {"name": "Quanta Magazine", "url": "https://api.quantamagazine.org/feed/", "category": "Physique"},
    {"name": "Phys.org Physique", "url": "https://phys.org/rss-feed/physics-news/", "category": "Physique"},
]

# Certains flux (ex: OpenAI) renvoient tout leur historique plutôt que les
# dernières publications : on ne garde que les N plus récentes entrées.
RSS_MAX_ITEMS_PER_FEED = 25

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_MAX_RESULTS_PER_CATEGORY = 15

DB_PATH = "app/data.db"
