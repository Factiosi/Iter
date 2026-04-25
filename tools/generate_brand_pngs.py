"""Из sources/Iter.Factiosi_icon_and_avatar.png делает PNG для сайта (web/public) и почты (sources)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "Iter.Factiosi_icon_and_avatar.png"
PUBLIC = ROOT / "web" / "public"


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
    save(ROOT / "sources" / "Iter.Factiosi_mail_avatar_512.png", 512)
    print("Written:", PUBLIC, "+ sources/Iter.Factiosi_mail_avatar_512.png")


if __name__ == "__main__":
    main()
