"""Génère les icônes PWA (orbite + planète, dans les couleurs de l'app).
Script de build ponctuel — Pillow n'est pas une dépendance runtime."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BG = (15, 17, 21, 255)  # --bg
ACCENT = (91, 141, 239, 255)  # --accent
RING = (167, 139, 250, 200)  # --cat-ia, semi-transparent

OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    corner = size * 0.22
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=corner, fill=BG)

    cx, cy = size / 2, size / 2
    ring_w, ring_h = size * 0.62, size * 0.30
    draw.ellipse(
        [cx - ring_w / 2, cy - ring_h / 2, cx + ring_w / 2, cy + ring_h / 2],
        outline=RING,
        width=max(2, round(size * 0.022)),
    )

    planet_r = size * 0.16
    draw.ellipse([cx - planet_r, cy - planet_r, cx + planet_r, cy + planet_r], fill=ACCENT)

    sat_r = size * 0.045
    sat_x, sat_y = cx + ring_w / 2 - sat_r, cy - sat_r * 0.5
    draw.ellipse([sat_x - sat_r, sat_y - sat_r, sat_x + sat_r, sat_y + sat_r], fill=(255, 255, 255, 255))

    return img


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for size, name in [(192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")]:
        draw_icon(size).save(OUT_DIR / name)
        print(f"écrit {OUT_DIR / name}")
