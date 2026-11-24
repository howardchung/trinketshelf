#!/usr/bin/env python3
"""Fetch official Jellycat plushies organized by series and regenerate src/data/jellycat.ts.

Sources (authorized Jellycat stockists with official studio photos):
  - babycubby.com/collections/jellycat
  - pacifierkids.com/collections/jellycat
  - faoschwarz.com/collections/jellycat

Organizes plushies into Jellycat's signature series:
  - Amuseables
  - Bashful Bunnies
  - Blossom Bunnies
  - Bashful Animals
  - Bears & Bartholomew
  - Dragons
  - Smudge
  - Bag Charms & Keychains
  - Animals & Friends
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import DATA_DIR, IMAGES_DIR, download_and_normalize_image, fetch_json, slugify

SKIP_KEYWORDS = (
    "book",
    "board book",
    "blanket",
    "soother",
    "rattle",
    "ring rattle",
    "musical pull",
    "chime",
    "stroller",
    "bib",
    "booties",
    "socks",
    "tote",
    "bum bag",
    "crossbody",
    "backpack",
    "pouch",
    "gift bag",
    "notebook",
    "journal",
    "decoration",
    "ornament",
)

SERIES_META = [
    {
        "id": "jc-amuseables",
        "name": "Jellycat · Amuseables",
        "shortName": "Amuseables",
        "subtitle": "Food, Drinks, Plants & Everyday Cuties",
        "maker": "Jellycat London",
        "accent": "#D98A4E",
        "accentSoft": "#FDF2E8",
        "accentText": "#915221",
        "emoji": "🥐",
    },
    {
        "id": "jc-bashful-bunnies",
        "name": "Jellycat · Bashful Bunnies",
        "shortName": "Bashful Bunnies",
        "subtitle": "Classic & Luxe Floppy-Eared Bunnies",
        "maker": "Jellycat London",
        "accent": "#C9897B",
        "accentSoft": "#FBF1EF",
        "accentText": "#854A3E",
        "emoji": "🐰",
    },
    {
        "id": "jc-blossom-bunnies",
        "name": "Jellycat · Blossom Bunnies",
        "shortName": "Blossom Bunnies",
        "subtitle": "Floral-Ear Cotton Print Bunnies",
        "maker": "Jellycat London",
        "accent": "#D97B9A",
        "accentSoft": "#FCEFF4",
        "accentText": "#8E3856",
        "emoji": "🌷",
    },
    {
        "id": "jc-bashful-animals",
        "name": "Jellycat · Bashful Animals",
        "shortName": "Bashful Animals",
        "subtitle": "Classic Bashful Woodland & Zoo Friends",
        "maker": "Jellycat London",
        "accent": "#7A9E7E",
        "accentSoft": "#EEF6EF",
        "accentText": "#3E6342",
        "emoji": "🐶",
    },
    {
        "id": "jc-bears",
        "name": "Jellycat · Bears & Bartholomew",
        "shortName": "Bears & Bartholomew",
        "subtitle": "Bartholomew Bear, Outfits & Classic Bears",
        "maker": "Jellycat London",
        "accent": "#A67653",
        "accentSoft": "#F8F0EA",
        "accentText": "#6B4529",
        "emoji": "🧸",
    },
    {
        "id": "jc-dragons",
        "name": "Jellycat · Dragons",
        "shortName": "Dragons",
        "subtitle": "Snow, Sage, Rose, Sky & Mythical Dragons",
        "maker": "Jellycat London",
        "accent": "#5C85B8",
        "accentSoft": "#ECF2FA",
        "accentText": "#315482",
        "emoji": "🐉",
    },
    {
        "id": "jc-smudge",
        "name": "Jellycat · Smudge",
        "shortName": "Smudge",
        "subtitle": "Ultra-Soft Lying-Down Smudge Plushies",
        "maker": "Jellycat London",
        "accent": "#8F7FB8",
        "accentSoft": "#F2EFFA",
        "accentText": "#554482",
        "emoji": "🐘",
    },
    {
        "id": "jc-bag-charms",
        "name": "Jellycat · Bag Charms",
        "shortName": "Bag Charms",
        "subtitle": "Clip-On Keychain & Bag Charm Plushies",
        "maker": "Jellycat London",
        "accent": "#E07A8E",
        "accentSoft": "#FDEFF2",
        "accentText": "#96384B",
        "emoji": "🔑",
    },
    {
        "id": "jc-animals",
        "name": "Jellycat · Animals & Friends",
        "shortName": "Animals & Friends",
        "subtitle": "Timmy Turtle, Ricky Rain Frog, Penguins & More",
        "maker": "Jellycat London",
        "accent": "#58948C",
        "accentSoft": "#EBF6F4",
        "accentText": "#2B5E57",
        "emoji": "🐢",
    },
]

SERIES_LABEL_BY_ID = {m["id"]: m["shortName"] for m in SERIES_META}

# Guaranteed iconic core Jellycats (already cached locally from official Jellycat CDN)
CORE_JELLYCATS = [
    ("jc-bashful-bunny", "jc-bashful-bunnies", "Bashful Beige Bunny", "Regular", "/images/jc-bashful-bunny.webp"),
    ("jc-croissant", "jc-amuseables", "Amuseables Croissant", "Regular", "/images/jc-croissant.webp"),
    ("jc-avocado", "jc-amuseables", "Amuseables Avocado", "Regular", "/images/jc-avocado.webp"),
    ("jc-bartholomew", "jc-bears", "Bartholomew Bear", "Regular", "/images/jc-bartholomew.webp"),
    ("jc-espresso-cup", "jc-amuseables", "Amuseables Espresso Cup", "Special", "/images/jc-espresso-cup.webp"),
    ("jc-blossom-bunny", "jc-blossom-bunnies", "Blossom Tulip Pink Bunny", "Special", "/images/jc-blossom-bunny.webp"),
    ("jc-cloud", "jc-amuseables", "Amuseables Cloud", "Regular", "/images/jc-cloud.webp"),
    ("jc-timmy-turtle", "jc-animals", "Timmy Turtle", "Special", "/images/jc-timmy-turtle.webp"),
]


def clean_title(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^Jellycat\s+", "", s, flags=re.I)
    s = re.sub(r"\s+by\s+Jellycat$", "", s, flags=re.I)
    s = re.sub(r"\s*\((?:202\d|Small|Medium|Large|Huge|Big|Little|Tiny|Original|Really Big)\)\s*", " ", s, flags=re.I)
    s = re.sub(r"\s+(?:Small|Medium|Large|Huge|Big|Little|Tiny|Original|Plush\s+Toy|Plush|Stuffed\s+Animal)$", "", s, flags=re.I)
    s = re.sub(r"\s+Key\s*Chain\s+Bag\s+Charm$", " Bag Charm", s, flags=re.I)
    s = re.sub(r"\s+Keychain$", " Bag Charm", s, flags=re.I)
    s = re.sub(r"^Amuseable\s+", "Amuseables ", s)
    s = re.sub(r"\s+", " ", s).strip(" -–|")
    return s


def classify_series(name: str, product_type: str) -> str:
    tl = name.lower()
    pt = (product_type or "").lower()
    if "bag charm" in tl or "key chain" in tl or "keychain" in tl or "bag charm" in pt:
        return "jc-bag-charms"
    if "amuseable" in tl:
        return "jc-amuseables"
    if "blossom" in tl and "bunny" in tl:
        return "jc-blossom-bunnies"
    if "smudge" in tl:
        return "jc-smudge"
    if "dragon" in tl:
        return "jc-dragons"
    if "bashful" in tl and "bunny" in tl:
        return "jc-bashful-bunnies"
    if "bashful" in tl:
        return "jc-bashful-animals"
    if "bartholomew" in tl or " bear" in tl or tl.endswith("bear"):
        return "jc-bears"
    return "jc-animals"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Jellycat series and official photos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing WebP images")
    args = parser.parse_args()

    stores = [
        "https://www.babycubby.com/collections/jellycat/products.json?limit=250&page={}",
        "https://pacifierkids.com/collections/jellycat/products.json?limit=250&page={}",
        "https://faoschwarz.com/collections/jellycat/products.json?limit=250&page={}",
    ]

    raw_products: list[dict] = []
    for base in stores:
        for page in range(1, 5):
            try:
                batch = fetch_json(base.format(page)).get("products", [])
                if not batch:
                    break
                raw_products.extend(batch)
            except Exception:
                break

    items: list[dict] = []
    tasks: list[tuple[str, str]] = []
    seen_name_keys: set[str] = set()
    used_ids: set[str] = set()

    # Seed the 8 guaranteed core Jellycats first
    for iid, col_id, name, rarity, img_path in CORE_JELLYCATS:
        used_ids.add(iid)
        seen_name_keys.add(slugify(name))
        items.append({
            "id": iid,
            "collectionId": col_id,
            "name": name,
            "series": SERIES_LABEL_BY_ID[col_id],
            "rarity": rarity,
            "image": img_path,
        })

    for p in raw_products:
        title = p.get("title", "").strip()
        tl = title.lower()
        if any(bad in tl for bad in SKIP_KEYWORDS):
            continue
        imgs = p.get("images") or []
        if not imgs or not imgs[0].get("src"):
            continue
        name = clean_title(title)
        if not name or len(name) < 3:
            continue
        name_key = slugify(name)
        if name_key in seen_name_keys:
            continue
        seen_name_keys.add(name_key)

        col_id = classify_series(name, p.get("product_type", ""))
        base_id = f"{col_id}-{name_key}"
        iid = base_id
        k = 2
        while iid in used_ids:
            iid = f"{base_id}-{k}"
            k += 1
        used_ids.add(iid)

        rarity = "Special" if any(w in tl for w in ("luxe", "limited", "christmas", "valentine", "halloween")) else "Regular"
        tasks.append((iid, imgs[0]["src"]))
        items.append({
            "id": iid,
            "collectionId": col_id,
            "name": name,
            "series": SERIES_LABEL_BY_ID[col_id],
            "rarity": rarity,
            "image": f"/images/{iid}.webp",
        })

    # Keep only non-empty series and update subtitles with counts
    collections = []
    for meta in SERIES_META:
        cnt = sum(1 for i in items if i["collectionId"] == meta["id"])
        if cnt == 0:
            continue
        c = dict(meta)
        c["subtitle"] = f"{meta['subtitle']} ({cnt})"
        collections.append(c)

    print(f"Downloading {len(tasks)} Jellycat photos across {len(collections)} series...")
    ok = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = {
            pool.submit(
                download_and_normalize_image,
                url,
                IMAGES_DIR / f"{iid}.webp",
                overwrite=args.overwrite,
            ): iid
            for iid, url in tasks
        }
        for fut in as_completed(futs):
            try:
                fut.result()
                ok += 1
            except Exception as exc:
                failed += 1
                print(f"  FAIL {futs[fut]}: {exc}")

    # Drop any items whose image download failed
    valid_items = [
        i for i in items
        if (IMAGES_DIR.parent / i["image"].lstrip("/")).is_file()
    ]

    out_ts = DATA_DIR / "jellycat.ts"
    out_ts.write_text(
        "\n".join([
            "import type { CatalogItem, CollectionMeta } from '../types';",
            "",
            "export const JELLYCAT_COLLECTIONS: CollectionMeta[] = " + json.dumps(collections, indent=2) + ";",
            "",
            "export const JELLYCAT_ITEMS: CatalogItem[] = " + json.dumps(valid_items, indent=2) + ";",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts}: {len(collections)} series, {len(valid_items)} items (downloaded {ok}, failed {failed})")
    for c in collections:
        cnt = sum(1 for i in valid_items if i["collectionId"] == c["id"])
        print(f"  {c['shortName']:22s}: {cnt} plushies")


if __name__ == "__main__":
    main()
