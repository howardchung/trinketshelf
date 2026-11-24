#!/usr/bin/env python3
"""Fetch POP MART TinyTiny catalog & studio photos and regenerate src/data/tinytiny.ts.

Fetches:
  - Series 1: Prologue Series (12 + Secret)
  - Series 2: Act I: Sugar Therapy Room (12 + Secret)
  - Mixed Series: The Golden Gallop, Pop Bean Island Vacation
  - Standalone Figures: Hanging Cards & Limited Art Editions
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import DATA_DIR, IMAGES_DIR, download_and_normalize_image, fetch_json, slugify


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch TinyTiny series and photos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing WebP images")
    args = parser.parse_args()

    sugg = fetch_json(
        "https://arttoyfamilia.com/search/suggest.json?q=tinytiny&resources[type]=product&resources[limit]=50"
    )
    atf_by_title: dict[str, dict] = {}
    for p in sugg.get("resources", {}).get("results", {}).get("products", []):
        if any(skip in p["title"].lower() for skip in ("dimoo", "pop bean")):
            continue
        handle = urllib.parse.quote(p["handle"])
        pj = fetch_json(f"https://arttoyfamilia.com/products/{handle}.json")["product"]
        img_map = {im["id"]: im["src"] for im in pj.get("images", [])}
        variants = [
            {
                "title": v["title"],
                "img": img_map.get(v.get("image_id")) or (pj["images"][0]["src"] if pj.get("images") else None),
            }
            for v in pj.get("variants", [])
        ]
        atf_by_title[pj["title"]] = {"title": pj["title"], "variants": variants}

    tz_products: list[dict] = []
    for page in range(1, 5):
        try:
            batch = fetch_json(f"https://toysez.com/collections/tinytiny/products.json?limit=250&page={page}").get(
                "products", []
            )
            if not batch:
                break
            for p in batch:
                tz_products.append({
                    "title": p["title"],
                    "img": p["images"][0]["src"] if p.get("images") else None,
                })
        except Exception:
            break

    collections = [
        {
            "id": "tinytiny-prologue",
            "name": "Tinytiny · Prologue Series",
            "shortName": "Prologue Series",
            "subtitle": "Series 1 (12 + Secret)",
            "maker": "POP MART",
            "accent": "#4F94A8",
            "accentSoft": "#EAF5F8",
            "accentText": "#2A6070",
            "emoji": "🔑",
        },
        {
            "id": "tinytiny-sugar-therapy",
            "name": "Tinytiny · Act I: Sugar Therapy Room",
            "shortName": "Act I: Sugar Therapy Room",
            "subtitle": "Series 2 (12 + Secret)",
            "maker": "POP MART",
            "accent": "#D97B9A",
            "accentSoft": "#FCEFF4",
            "accentText": "#8E3856",
            "emoji": "🍬",
        },
        {
            "id": "tinytiny-mixed",
            "name": "Tinytiny · Mixed Series",
            "shortName": "Mixed Series",
            "subtitle": "POP MART Mixed-IP Appearances",
            "maker": "POP MART",
            "accent": "#D4943A",
            "accentSoft": "#FDF4E6",
            "accentText": "#8A5812",
            "emoji": "🎠",
        },
        {
            "id": "tinytiny-standalone",
            "name": "Tinytiny · Standalone Figures",
            "shortName": "Standalone Figures",
            "subtitle": "Hanging Cards & Limited Art Editions",
            "maker": "POP MART / CJ",
            "accent": "#7A6BB8",
            "accentSoft": "#F1EEFA",
            "accentText": "#4A3A85",
            "emoji": "✨",
        },
    ]

    items: list[dict] = []
    tasks: list[tuple[str, str]] = []
    used_ids: set[str] = set()

    def add_item(col_id: str, name: str, series: str, rarity: str, img_url: str | None) -> None:
        if not img_url:
            return
        base = f"{col_id}-{slugify(name)}"
        iid = base
        k = 2
        while iid in used_ids:
            iid = f"{base}-{k}"
            k += 1
        used_ids.add(iid)
        tasks.append((iid, img_url))
        items.append({
            "id": iid,
            "collectionId": col_id,
            "name": name,
            "series": series,
            "rarity": rarity,
            "image": f"/images/{iid}.webp",
        })

    for title, col_id, series_label in [
        ("Tinytiny Prologue Series", "tinytiny-prologue", "Prologue Series"),
        ("TinyTiny Act I: Sugar Therapy Room Series Figures", "tinytiny-sugar-therapy", "Act I: Sugar Therapy Room"),
    ]:
        if title not in atf_by_title:
            continue
        for v in atf_by_title[title]["variants"]:
            vt = v["title"]
            if any(skip in vt.lower() for skip in ("confirmed figures", "fullset", "full set", "blind box")):
                continue
            is_sec = "secret" in vt.lower()
            clean = re.sub(r"\s*\(secret\)", "", vt, flags=re.I).strip()
            add_item(col_id, clean, series_label, "Secret" if is_sec else "Regular", v["img"])

    seen_standalone: set[str] = set()
    if "Tinytiny Sugar Theater Series Hanging Card" in atf_by_title:
        for v in atf_by_title["Tinytiny Sugar Theater Series Hanging Card"]["variants"]:
            clean = v["title"].strip()
            seen_standalone.add(slugify(clean))
            add_item("tinytiny-standalone", clean, "Sugar Theater Hanging Card", "Special", v["img"])

    for p in tz_products:
        t = p["title"]
        tl = t.lower()
        img = p["img"]
        if not img:
            continue
        if "golden gallop" in tl:
            name = re.sub(r"^TINYTINY\s+Pop Mart\s+The Golden Gallop Series\s*", "", t, flags=re.I).strip()
            add_item("tinytiny-mixed", name, "The Golden Gallop Series", "Special" if "special" in tl else "Regular", img)
        elif "pop bean" in tl:
            name = re.sub(r"^TINYTINY\s+Pop Bean\s+Island Vacation\s+Blind Box Series:\s*", "", t, flags=re.I)
            name = re.sub(r"\s*\(Confirmed Style\)", "", name, flags=re.I).strip()
            add_item("tinytiny-mixed", name, "Pop Bean Island Vacation", "Regular", img)
        elif not any(skip in tl for skip in ("prologue", "sugar therapy", "whole set", "complete set")):
            clean = re.sub(r"^TINYTINY\s+", "", t, flags=re.I)
            clean = re.sub(r"\s+Limited Edition$", "", clean, flags=re.I)
            clean = clean.replace("Null Frequengy", "Null Frequency").strip()
            key = slugify(re.sub(r"\b20\d\d\b", "", clean))
            if key not in seen_standalone:
                seen_standalone.add(key)
                add_item("tinytiny-standalone", clean, "Standalone / Limited Edition", "Special", img)

    for c in collections:
        cnt = sum(1 for i in items if i["collectionId"] == c["id"])
        if c["id"] == "tinytiny-mixed":
            c["subtitle"] = f"POP MART Mixed-IP Appearances ({cnt} figures)"
        elif c["id"] == "tinytiny-standalone":
            c["subtitle"] = f"Hanging Cards & Limited Editions ({cnt} figures)"

    with ThreadPoolExecutor(max_workers=14) as pool:
        futs = [
            pool.submit(
                download_and_normalize_image,
                url,
                IMAGES_DIR / f"{iid}.webp",
                overwrite=args.overwrite,
            )
            for iid, url in tasks
        ]
        for fut in as_completed(futs):
            fut.result()

    out_ts = DATA_DIR / "tinytiny.ts"
    out_ts.write_text(
        "\n".join([
            "import type { CatalogItem, CollectionMeta } from '../types';",
            "",
            "export const TINYTINY_COLLECTIONS: CollectionMeta[] = " + json.dumps(collections, indent=2) + ";",
            "",
            "export const TINYTINY_ITEMS: CatalogItem[] = " + json.dumps(items, indent=2) + ";",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts} ({len(collections)} collections, {len(items)} items)")


if __name__ == "__main__":
    main()
