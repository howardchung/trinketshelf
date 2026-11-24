"""Shared helpers for TrinketShelf catalog data-fetching scripts."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from html import unescape
from io import BytesIO
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJECT_ROOT / "public" / "images"
DATA_DIR = PROJECT_ROOT / "src" / "data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def fetch_json(url: str, timeout: int = 20):
    return json.loads(fetch_text(url, timeout=timeout))


def download_and_normalize_image(
    url: str,
    dest_path: Path,
    size: int = 512,
    inner_size: int = 480,
    quality: int = 88,
    overwrite: bool = False,
) -> Path:
    """Download an image, composite alpha onto pure white, center in a square WebP."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and dest_path.is_file() and dest_path.stat().st_size > 0:
        return dest_path

    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()

    src = Image.open(BytesIO(raw)).convert("RGBA")
    bg = Image.new("RGBA", src.size, (255, 255, 255, 255))
    comp = Image.alpha_composite(bg, src).convert("RGB")

    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    scale = min(inner_size / comp.width, inner_size / comp.height)
    nw, nh = max(1, int(comp.width * scale)), max(1, int(comp.height * scale))
    resized = comp.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2))
    canvas.save(dest_path, "WEBP", quality=quality)
    return dest_path


def scrape_sonnyangel_tabs(url: str) -> dict[str, list[tuple[str, str]]]:
    """Parse FooGallery tab sections from an official sonnyangel.com products page."""
    html = fetch_text(url)
    body = html[html.find("<body") :]
    parts = re.split(r'(<h2[^>]*class="tabtitle"[^>]*>.*?</h2>)', body, flags=re.S | re.I)

    result: dict[str, list[tuple[str, str]]] = {}
    current_tab: str | None = None
    for part in parts:
        hm = re.match(r'<h2[^>]*class="tabtitle"[^>]*>(.*?)</h2>', part, re.S | re.I)
        if hm:
            current_tab = unescape(re.sub(r"<[^>]+>", "", hm.group(1))).strip()
            result[current_tab] = []
            continue
        if current_tab is None:
            continue
        for m in re.finditer(
            r'<a[^>]+href="(https://www\.sonnyangel\.com/[^"]+\.(?:jpg|jpeg|png|webp))"[^>]*>',
            part,
            re.I,
        ):
            tag = m.group(0)
            img_url = m.group(1)
            tm = re.search(r'data-caption-title="([^"]+)"|title="([^"]+)"', tag)
            name = unescape((tm.group(1) or tm.group(2)).strip()) if tm else ""
            if img_url not in [u for _, u in result[current_tab]]:
                result[current_tab].append((name, img_url))
    return result
