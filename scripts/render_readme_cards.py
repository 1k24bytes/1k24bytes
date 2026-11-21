#!/usr/bin/env python3
"""Render the GitHub profile as standalone SVG cards (white blocks)."""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from datetime import date, datetime
from html import escape
from io import BytesIO
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "contributions.json"
CARDS = ROOT / "cards"
STATIC = os.getenv("STATIC", "0") == "1"

CARD = "#ffffff"
INK = "#161616"
MUTED = "#6f6f6f"
BLUE = "#2447f5"
RED = "#e1332d"
YELLOW = "#ffc61a"
RULE = "#e6e6e6"
GRID = ["#e9ecfa", "#c3cdff", "#93a6ff", "#5f7dff", "#2447f5", "#1633c9"]
BAR = "#161616"
BAR_EMPTY = "#e7e7e7"


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {
        "username": "1k24bytes", "total_contributions": None, "days": [], "months": [],
        "active_days": None, "current_streak": None, "longest_streak": None, "busiest_day": None,
    }


def subset_font_from_css(family: str, weight: int = 400, italic: bool = False) -> str | None:
    """Fetch a Google Font, subset it to the characters we use, and return base64 WOFF."""
    try:
        if os.getenv("SKIP_FONT_DOWNLOAD") == "1":
            return None
        if family == "Instrument Serif":
            css_url = "https://fonts.googleapis.com/css2?family=Instrument+Serif&display=swap"
        else:
            style = "ital,wght@1,400" if italic else f"wght@{weight}"
            css_url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:{style}&display=swap"
        css = requests.get(
            css_url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"},
            timeout=15,
        ).text
        blocks = re.findall(r"@font-face\s*\{([^}]+)\}", css, re.IGNORECASE)
        source_url = None
        for block in blocks:
            if "U+0000-00FF" in block or "U+0000-00FF" in block.upper():
                match = re.search(r"url\((https://[^)]+)\)\s*format\(['\"]?woff2", block)
                if match:
                    source_url = match.group(1)
                    break
        if not source_url:
            return None

        font_response = requests.get(source_url, timeout=20)
        font_response.raise_for_status()
        from fontTools import subset
        from fontTools.ttLib import TTFont

        font = TTFont(BytesIO(font_response.content))
        options = subset.Options()
        options.layout_features = ["*"]
        options.name_IDs = [1, 2, 4, 6]
        options.name_legacy = True
        subsetter = subset.Subsetter(options=options)
        glyph_text = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
            ".,:;!?@#%&()[]{}+-=/\\_'\"→↗·•—–’“”"
        )
        subsetter.populate(text=glyph_text)
        subsetter.subset(font)
        font.flavor = "woff"
        output = BytesIO()
        font.save(output)
        return base64.b64encode(output.getvalue()).decode("ascii")
    except Exception as exc:
        print(f"Font embedding skipped for {family}: {exc}", file=sys.stderr)
        return None


def get_fonts_css() -> str:
    instrument = subset_font_from_css("Instrument Serif", 400, False)
    geist = subset_font_from_css("Geist", 400, False)
    faces = []
    if instrument:
        faces.append(f"@font-face{{font-family:'Instrument Serif';src:url(data:font/woff;base64,{instrument}) format('woff');font-weight:400;font-style:normal;}}")
    if geist:
        faces.append(f"@font-face{{font-family:'Geist';src:url(data:font/woff;base64,{geist}) format('woff');font-weight:400;}}")
    return "\n".join(faces)


FONTS_CSS = ""


def svg_start(width: int, height: int, title: str, animation_css: str = "") -> str:
    reduced_motion = """
    @media (prefers-reduced-motion: reduce) {
      .anim, .print-row, .bar, .tile-enter, .smil-motion, .arrow, .pulse { animation: none !important; }
      .anim, .print-row, .bar, .tile-enter { opacity: 1 !important; transform: none !important; }
      .smil-motion { display: none !important; }
    }
    """
    style = f"""
      {FONTS_CSS}
      text {{ fill: {INK}; }}
      .serif {{ font-family: 'Instrument Serif', Georgia, 'Times New Roman', serif; }}
      .sans {{ font-family: 'Geist', Arial, sans-serif; }}
      .mono {{ font-family: 'Geist', 'Courier New', monospace; }}
      .muted {{ fill: {MUTED}; }}
      .rule {{ stroke: {RULE}; stroke-width: 1; }}
      {animation_css}
      {reduced_motion}
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
        f'<title>{esc(title)}</title><style>{style}</style>'
    )


def svg_end(body: str) -> str:
    return body + "</svg>\n"


def anim_css() -> str:
    if STATIC:
        return ""
    return """
    @keyframes rise { 0% { opacity:0; transform:translateY(18px); } 100% { opacity:1; transform:translateY(0); } }
    @keyframes print { 0% { opacity:0; } 100% { opacity:1; } }
    @keyframes grow { 0% { transform:scaleY(.02); opacity:.5; } 100% { transform:scaleY(1); opacity:1; } }
    @keyframes tile-in { 0% { opacity:0; transform:translateY(25px) rotate(1.8deg); } 70% { opacity:1; transform:translateY(-3px) rotate(-.3deg); } 100% { opacity:1; transform:translateY(0) rotate(0); } }
    @keyframes pulse { 0%,100% { opacity:.18; } 50% { opacity:.7; } }
    @keyframes nudge { 0%,100% { transform:translateX(0); } 50% { transform:translateX(7px); } }
    .anim { animation:rise .75s cubic-bezier(.2,.75,.25,1) both; }
    .print-row { opacity:0; animation:print .2s linear forwards; }
    .bar { transform-box:fill-box; transform-origin:bottom; animation:grow .85s cubic-bezier(.2,.7,.2,1) both; }
    .tile-enter { animation:tile-in .8s cubic-bezier(.2,.8,.2,1) both; }
    .pulse { animation:pulse 2.6s ease-in-out infinite; }
    .arrow { animation:nudge 2.2s ease-in-out infinite; }
    """


def write_svg(filename: str, body: str) -> None:
    (CARDS / filename).write_text(body, encoding="utf-8")


def card_start(width: int, height: int, title: str) -> str:
    svg = svg_start(width, height, title, anim_css())
    svg += f'<rect width="{width}" height="{height}" rx="18" fill="{CARD}"/>'
    svg += f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="17" fill="none" stroke="{RULE}"/>'
    return svg


def portrait_data_uri() -> str | None:
    for candidate in (CARDS / "portrait.png", ROOT / "profile-ascii.png"):
        if candidate.exists():
            return "data:image/png;base64," + base64.b64encode(candidate.read_bytes()).decode("ascii")
    return None


def render_hero() -> None:
    svg = card_start(1200, 430, "Tawqeer Amin Dar — Full Stack Developer")
    svg += '<g class="anim" style="animation-delay:.08s">'
    svg += f'<rect x="48" y="48" width="9" height="9" fill="{BLUE}"/>'
    svg += '<text x="66" y="56" class="sans muted" font-size="13" letter-spacing="2.5">FULL STACK DEVELOPER</text>'
    svg += '<text x="44" y="198" class="serif" font-size="118" font-style="italic">Tawqeer</text>'
    svg += '<text x="44" y="308" class="serif" font-size="118" font-style="italic">Amin Dar</text>'
    svg += '<text x="48" y="354" class="sans" font-size="20">Building useful web, mobile and operational products.</text>'
    svg += f'<text x="48" y="390" class="mono" font-size="15" fill="{BLUE}">tawqeer.is-a.dev ↗</text></g>'
    portrait = portrait_data_uri()
    if portrait:
        svg += f'<image x="830" y="60" width="320" height="310" preserveAspectRatio="xMidYMid slice" href="{portrait}"/>'
    svg = svg_end(svg)
    write_svg("hero.svg", svg)


def contribution_color(count: int, maximum: int) -> str:
    if count <= 0:
        return GRID[0]
    if count <= 5:
        return GRID[1]
    if count <= 15:
        return GRID[2]
    if count <= 30:
        return GRID[3]
    if count <= 50:
        return GRID[4]
    return GRID[5]


def render_contributions(data: dict) -> None:
    W, H = 1200, 310
    svg = card_start(W, H, "GitHub contribution graph")
    svg += f'<text x="40" y="68" class="serif" font-size="36">Every day, <tspan font-style="italic" fill="{BLUE}">in blue</tspan></text>'
    svg += f'<text x="{W - 40}" y="60" text-anchor="end" class="sans muted" font-size="12" letter-spacing="2">REFRESHED DAILY</text>'

    days = data.get("days") or []
    counts = {str(item["date"]): int(item["count"]) for item in days}
    if days:
        start = date.fromisoformat(str(days[0]["date"]))
        end = date.fromisoformat(str(days[-1]["date"]))
    else:
        end = date.today()
        start = date.fromordinal(end.toordinal() - 364)
    grid_start = date.fromordinal(start.toordinal() - start.weekday())
    cell, gap = 15, 5
    grid_x, grid_y = 60, 106
    max_count = max(counts.values(), default=1)
    month_labels: list[tuple[int, str]] = []
    current_month = None
    for col in range(54):
        week_date = date.fromordinal(grid_start.toordinal() + col * 7)
        label = week_date.strftime("%b")
        key = (week_date.year, week_date.month)
        if key != current_month and week_date <= end and week_date >= start - __import__('datetime').timedelta(days=7):
            month_labels.append((col, label))
            current_month = key
        for row in range(7):
            day = date.fromordinal(grid_start.toordinal() + col * 7 + row)
            if day < start or day > end:
                continue
            count = counts.get(day.isoformat(), 0)
            color = contribution_color(count, max_count)
            idx = col * 7 + row
            style = "" if STATIC else f' style="animation-delay:{min(idx * .006, 2.8):.3f}s"'
            cls = "" if STATIC else "anim"
            svg += f'<rect x="{grid_x + col*(cell+gap)}" y="{grid_y + row*(cell+gap)}" width="{cell}" height="{cell}" rx="3" fill="{color}" class="{cls}"{style}><title>{day.isoformat()}: {count} contributions</title></rect>'
    for col, label in month_labels:
        if col < 53:
            svg += f'<text x="{grid_x + col*(cell+gap)}" y="{grid_y - 10}" class="mono muted" font-size="12">{label}</text>'
    legend_y = H - 28
    sw_x = W - 40 - 44 - len(GRID) * 17
    svg += f'<text x="{sw_x - 8}" y="{legend_y}" text-anchor="end" class="mono muted" font-size="11">less</text>'
    for i, color in enumerate(GRID):
        svg += f'<rect x="{sw_x + i*17}" y="{legend_y - 11}" width="14" height="12" rx="2.5" fill="{color}"/>'
    svg += f'<text x="{W - 40}" y="{legend_y}" text-anchor="end" class="mono muted" font-size="11">more</text>'
    if not days:
        svg += f'<text x="{W / 2:.0f}" y="{legend_y}" class="mono muted" font-size="12" text-anchor="middle">Daily detail appears after the first GitHub Actions refresh.</text>'
    svg = svg_end(svg)
    write_svg("contributions.svg", svg)


def fmt_stat(value: object, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{value}{suffix}"


def render_activity(data: dict) -> None:
    W, H = 1200, 380
    svg = card_start(W, H, "Monthly GitHub activity and statistics")
    total = data.get("total_contributions")
    total_str = f"{int(total):,}" if isinstance(total, (int, float)) else "—"
    svg += '<text x="40" y="54" class="sans muted" font-size="12" letter-spacing="2">THE LAST 12 MONTHS ON GITHUB</text>'
    svg += f'<text x="38" y="114" class="serif" font-size="46">{esc(total_str)} <tspan font-style="italic">contributions</tspan></text>'

    months = data.get("months") or []
    plot_x, plot_y, plot_w, plot_h = 40, 150, 700, 130
    values = [int(item.get("count", 0)) for item in months]
    max_value = max(values, default=0)
    if months:
        n = len(months)
        step = plot_w / n
        bar_w = min(42, step * .5)
        for i, item in enumerate(months):
            value = int(item.get("count", 0))
            height = (value / max(1, max_value)) * 110 if max_value else 0
            x = plot_x + i * step + (step - bar_w) / 2
            y = plot_y + plot_h - height
            delay = "" if STATIC else f' style="animation-delay:{i*.06:.2f}s"'
            cls = "" if STATIC else "bar"
            is_top = value == max_value and value > 0
            svg += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height:.1f}" rx="2" fill="{BLUE if is_top else BAR}" class="{cls}"{delay}><title>{esc(item.get("label", ""))}: {value} contributions</title></rect>'
            if is_top:
                svg += f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" class="sans" font-size="13" text-anchor="middle" fill="{BLUE}">{value:,}</text>'
            svg += f'<text x="{x + bar_w / 2:.1f}" y="{plot_y + plot_h + 24}" class="sans muted" font-size="12" text-anchor="middle">{esc(item.get("label", ""))}</text>'
    else:
        for i in range(12):
            x = plot_x + i * (plot_w / 12) + 13
            svg += f'<rect x="{x:.1f}" y="{plot_y + plot_h - 6}" width="32" height="6" rx="2" fill="{BAR_EMPTY}"/>'
            svg += f'<text x="{x + 16:.1f}" y="{plot_y + plot_h + 24}" class="sans muted" font-size="12" text-anchor="middle">—</text>'

    svg += f'<line x1="800" y1="60" x2="800" y2="{H - 60}" class="rule"/>'
    streak = data.get("current_streak")
    active = data.get("active_days")
    busiest = data.get("busiest_day") or {}
    stats = [
        (f"{streak} days" if isinstance(streak, int) else "—", "current streak"),
        (f"{active:,}" if isinstance(active, (int, float)) else "—", "days with a commit"),
        (str(busiest.get("count", busiest.get("label", "—"))), "on the busiest day"),
    ]
    for i, (value, label) in enumerate(stats):
        vy = 150 + i * 90
        if i:
            svg += f'<line x1="840" y1="{vy - 42}" x2="{W - 40}" y2="{vy - 42}" class="rule"/>'
        svg += f'<text x="840" y="{vy}" class="serif" font-size="40">{esc(value)}</text>'
        svg += f'<text x="840" y="{vy + 24}" class="sans muted" font-size="13">{esc(label)}</text>'
    svg = svg_end(svg)
    write_svg("activity.svg", svg)


def render_tile(filename: str, title: str, subtitle: str, color: str, text_color: str, eyebrow: str, index: int) -> None:
    W, H = 380, 230
    svg = svg_start(W, H, f"{title} — {subtitle}", anim_css())
    svg += f'<rect width="{W}" height="{H}" rx="18" fill="{color}"/>'
    cls = "" if STATIC else "tile-enter"
    delay = "" if STATIC else f' style="animation-delay:{.45 + index*.16:.2f}s"'
    svg += f'<g class="{cls}"{delay}>'
    svg += f'<text x="28" y="46" class="sans" font-size="12" letter-spacing="2" style="fill:{text_color}">{esc(eyebrow)}</text>'
    svg += f'<text x="{W - 28}" y="48" text-anchor="end" class="serif arrow" font-size="26" style="fill:{text_color}">→</text>'
    svg += f'<text x="26" y="140" class="serif" font-size="52" style="fill:{text_color}">{esc(title)}</text>'
    svg += f'<text x="28" y="178" class="sans" font-size="16" style="fill:{text_color}">{esc(subtitle)}</text></g>'
    # A fine moving highlight is intentionally native SVG SMIL, not JavaScript.
    if not STATIC:
        svg += '<rect x="-120" y="0" width="72" height="230" fill="#ffffff" opacity=".11" transform="skewX(-22)" class="smil-motion"><animate attributeName="x" from="-120" to="450" dur="5.5s" repeatCount="indefinite"/></rect>'
    svg = svg_end(svg)
    write_svg(filename, svg)


def main() -> int:
    CARDS.mkdir(parents=True, exist_ok=True)
    data = load_data()
    global FONTS_CSS
    FONTS_CSS = get_fonts_css()
    render_hero()
    render_contributions(data)
    render_activity(data)
    render_tile("build.svg", "10+ clients", "Products & systems", BLUE, "#ffffff", "01 / SHIP", 0)
    render_tile("brand.svg", "100K users", "Interfaces & design", RED, "#ffffff", "02 / CREATE", 1)
    render_tile("learn.svg", "3+ countries", "Experiments & notes", YELLOW, INK, "03 / EXPLORE", 2)
    print(f"Rendered 6 SVG cards into {CARDS} (STATIC={int(STATIC)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
