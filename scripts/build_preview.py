#!/usr/bin/env python3
"""Build preview-standalone.html by inlining cards/*.svg into preview.html.

The standalone file shows every card with zero external requests, so it
renders even when preview.html is moved, copied, or opened in a viewer
that blocks relative local files. Re-run after regenerating the cards:

    python scripts/render_readme_cards.py
    python scripts/build_preview.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IMG_RE = re.compile(r'<img\s+src="\./cards/([a-z]+)\.svg"\s+alt="[^"]*"\s*/>')


def inline_img(match: re.Match[str]) -> str:
    name = match.group(1)
    svg = (ROOT / "cards" / f"{name}.svg").read_text(encoding="utf-8")
    return svg.strip()


def main() -> int:
    html = (ROOT / "preview.html").read_text(encoding="utf-8")
    names = IMG_RE.findall(html)
    if not names:
        print("No ./cards/*.svg images found in preview.html; nothing to inline.")
        return 1
    html = IMG_RE.sub(inline_img, html)
    html = html.replace(
        "<span>cards/ · live SVGs</span>",
        "<span>standalone · images inlined</span>",
    )
    html = html.replace(
        "<title>Profile README — Preview</title>",
        "<title>Profile README — Preview (standalone)</title>",
    )
    (ROOT / "preview-standalone.html").write_text(html, encoding="utf-8")
    print(f"Inlined {len(names)} cards ({', '.join(names)}) into preview-standalone.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
