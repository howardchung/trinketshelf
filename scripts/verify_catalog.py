#!/usr/bin/env python3
"""Verify that every catalog item image referenced in public/data/*.json exists on disk."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"


def extract_items(data: object) -> list[dict]:
    if isinstance(data, dict):
        items: list[dict] = []
        for k, v in data.items():
            if k.lower().endswith("items") and isinstance(v, list):
                items.extend(v)
        return items
    return []


def main() -> None:
    json_files = sorted(PUBLIC_DATA_DIR.glob("*.json"))
    all_imgs: list[str] = []
    for path in json_files:
        if path.name in ("prices.json", "pokemon-sets.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        items = extract_items(data)
        found = [it["image"] for it in items if isinstance(it.get("image"), str) and it["image"].startswith("/images/")]
        all_imgs.extend(found)
        print(f"  {path.name:26s}: {len(found):4d} items")

    missing = [
        img
        for img in all_imgs
        if not (PROJECT_ROOT / "public" / img.lstrip("/")).is_file()
        or (PROJECT_ROOT / "public" / img.lstrip("/")).stat().st_size == 0
    ]
    svgs = [img for img in all_imgs if img.endswith(".svg")]

    print(
        f"\nTotal catalog items: {len(all_imgs)} | "
        f"WebP photos: {len(all_imgs) - len(svgs)} | "
        f"SVG portraits: {len(svgs)} | "
        f"Missing: {len(missing)}"
    )
    if missing:
        print("Missing files:", missing[:20])
        sys.exit(1)


if __name__ == "__main__":
    main()
