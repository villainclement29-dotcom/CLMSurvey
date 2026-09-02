"""Score de pertinence des articles pour le profil de l'utilisateur :
étudiant sortant d'un BUT MMI (dev web, IA appliquée), poursuivant un
master de recherche en IA au JAIST (Japon), visant une carrière dans la
recherche spatiale. On priorise le contenu technique/recherche (papiers
arXiv, IA appliquée à l'espace) et on déprioritise le contenu
promotionnel, grand public ou éducatif (K-12) qui passe les filtres de
catégorie mais n'a pas de valeur pour ce profil.
"""
from __future__ import annotations

SPACE_KEYWORDS = [
    "satellite", "spacecraft", "rocket", "orbit", "orbital", "launch",
    "mission", "mars", "lunar", "moon", "exoplanet", "astrophysics",
    "cosmology", "telescope", "jaxa", "esa", "nasa", "iss", "astronaut",
    "planetary", "interstellar", "cosmic", "galaxy", "black hole",
    "gravitational", "rover", "probe", "space exploration", "deep space",
    "asteroid", "comet", "spacewalk", "propulsion", "artemis",
]

AI_RESEARCH_KEYWORDS = [
    "machine learning", "deep learning", "neural network",
    "reinforcement learning", "transformer", "llm", "large language model",
    "robotics", "autonomous", "model architecture", "training",
    "benchmark", "dataset", "generative", "computer vision", "nlp",
    "agent", "diffusion", "fine-tun", "inference",
]

# Contenu qui passe le filtre de catégorie mais n'a pas de valeur pour un
# profil recherche (communication grand public, contenu pédagogique K-12).
NEGATIVE_KEYWORDS = [
    "for teachers", "for students", "grades", "k-5", "k-8", "educator",
    "lesson", "stem curricula", "math problems", "space math",
    "problem set", "accelerator", "startups", "expanding access",
    "ads reaches", "revenue", "school district", "for kids",
]

INTERSECTION_BONUS = 6  # le point de rencontre IA + espace : le profil idéal
ARXIV_BONUS = 3  # papier de recherche plutôt que communication
NEGATIVE_PENALTY = 8
MIN_SCORE = 0  # en-dessous, l'article est écarté même si la journée est peu fournie


def _count_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def score_item(item) -> float:
    title = (item["title"] or "").lower()
    summary = (item["summary"] or "").lower()
    combined = f"{title} {summary}"

    space_hits = _count_hits(combined, SPACE_KEYWORDS)
    ai_hits = _count_hits(combined, AI_RESEARCH_KEYWORDS)
    negative_hits = _count_hits(combined, NEGATIVE_KEYWORDS)

    score = 1.0  # déjà dans une des 4 catégories suivies (IA/Espace/Astro/Physique)
    score += min(space_hits, 4) * 1.5
    score += min(ai_hits, 4) * 1.5
    if space_hits and ai_hits:
        score += INTERSECTION_BONUS
    if item["source"] == "arXiv":
        score += ARXIV_BONUS
    score -= negative_hits * NEGATIVE_PENALTY
    return score


def rank_and_cap_single(items, max_items: int = 10):
    """Trie une liste d'articles par pertinence, écarte ceux en-dessous de
    MIN_SCORE (même si ça laisse peu d'articles), et retourne
    (articles_conservés, total_avant_filtrage).

    Chaque score n'est calculé qu'une fois par article (au lieu d'une fois
    pour le tri puis une seconde fois pour le filtrage)."""
    scored = sorted(
        ((score_item(it), it) for it in items),
        key=lambda pair: pair[0],
        reverse=True,
    )
    relevant = [it for score, it in scored if score > MIN_SCORE]
    return relevant[:max_items], len(items)


def rank_and_cap(groups, max_per_group: int = 10):
    """Applique rank_and_cap_single à chaque groupe de group_by_date.
    Retourne une liste de (label, articles_conservés, total_avant_plafond)."""
    return [(label, *rank_and_cap_single(items, max_per_group)) for label, items in groups]
