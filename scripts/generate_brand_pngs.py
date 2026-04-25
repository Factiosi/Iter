"""Генерирует favicon/app icons из assets/brand/app-icon.png."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
SRC = BRAND / "app-icon.png"
PUBLIC = ROOT / "apps" / "web" / "public"


def main() -> None:
    im = Image.open(SRC).convert("RGBA")
    w, h = im.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    sq = im.crop((left, top, left + s, top + s))

    PUBLIC.mkdir(parents=True, exist_ok=True)

    def save(dst: Path, size: int) -> None:
        sq.resize((size, size), Image.Resampling.LANCZOS).save(dst, "PNG")

    save(PUBLIC / "favicon-16x16.png", 16)
    save(PUBLIC / "favicon-32x32.png", 32)
    save(PUBLIC / "apple-touch-icon.png", 180)
    save(PUBLIC / "icon-192.png", 192)
    save(PUBLIC / "icon-512.png", 512)
    save(BRAND / "mail-avatar-512.png", 512)
    print("Written:", PUBLIC, "+ assets/brand/mail-avatar-512.png")


if __name__ == "__main__":
    main()
