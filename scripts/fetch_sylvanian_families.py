#!/usr/bin/env python3
"""Fetch Sylvanian Families Blind Bags & Blind Boxes with studio photos.

Source:
  - store.kobeejapan.net/collections/blind-bag (individual confirmed figures across
    BB-01..BB-16 Blind Bag series and Doki Doki / FamilyMart / Lottery Blind Box series)

Writes src/data/sylvanian-families.json and downloads normalized 512x512 WebP photos into public/images/.
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import DATA_DIR, IMAGES_DIR, download_and_normalize_image, fetch_json, slugify

SKIP_PACK_PATTERNS = (
    "[used]",
    "one blind bag",
    "one blind box",
    "blind box contains",
    "complete set",
    "full set",
    "all 8",
    "all 6",
    "all 9",
    "set of ",
    "box of ",
    "assorted",
    "sealed",
    "random",
)

# Known Blind Box / Doki Doki / Lottery / FamilyMart sub-lines vs standard Blind Bags
BLIND_BOX_KEYWORDS = (
    "doki doki",
    "dokidoki",
    "familymart",
    "lottery",
    "happy sweets",
    "delicious parade",
    "starry sky",
    "cutie collectibles",
    "milky way",
    "hamburger shop",
    "tea time",
    "space costume",
)

# Ordered list of (regex_match, canonical_series_name, category, emoji)
KNOWN_SERIES = [
    (r"fairy forest friends", "Fairy Forest Friends", "blind-bag", "🧚"),
    (r"baby adventure", "Baby Adventure Series", "blind-bag", "🧭"),
    (r"flower garden friends|blooming baby", "Blooming Baby Friends", "blind-bag", "🌼"),
    (r"baby craft lovers", "Baby Craft Lovers", "blind-bag", "🎨"),
    (r"baby mysterious wizard|magical baby", "Baby Magical Series", "blind-bag", "🪄"),
    (r"secret forest|forest costume", "Baby Forest Costume", "blind-bag", "🍄"),
    (r"baby fruit party series 2|fruit party 2", "Baby Fruit Party 2", "blind-bag", "🍓"),
    (r"baby fruit party|fruity babies", "Baby Fruit Party", "blind-bag", "🍑"),
    (r"baby seashore|ocean babies", "Baby Seashore Friends", "blind-bag", "🐚"),
    (r"baby hair|fun hair", "Baby Fun Hair Series", "blind-bag", "🎀"),
    (r"baby treats|sweet treats", "Baby Treats Series", "blind-bag", "🍩"),
    (r"baking baby|baby baking", "Baby Baking Party", "blind-bag", "🧁"),
    (r"baby fairytale|fairytale", "Baby Fairytale Series", "blind-bag", "👑"),
    (r"baby camping", "Baby Camping Series", "blind-bag", "⛺"),
    (r"baby shopping", "Baby Shopping Series", "blind-bag", "🧺"),
    (r"baby band", "Baby Band Series", "blind-bag", "🎻"),
    (r"baby party", "Baby Party Series", "blind-bag", "🎂"),
    (r"baby outdoor", "Baby Outdoor Series", "blind-bag", "🎒"),
    (r"baby builder|construction", "Baby Builder Series", "blind-bag", "🔨"),
    (r"baby costume", "Baby Costume Series", "blind-bag", "👻"),
    (r"doki\s*doki.*milky way|milky way", "Doki Doki · Milky Way", "blind-box", "🌌"),
    (r"doki\s*doki.*tea time|baby tea time", "Doki Doki · Baby Tea Time", "blind-box", "🫖"),
    (r"doki\s*doki.*hamburger|hamburger shop", "Doki Doki · Hamburger Shop", "blind-box", "🍔"),
    (r"doki\s*doki.*space|baby space", "Doki Doki · Space Costumes", "blind-box", "🚀"),
    (r"delicious parade", "Delicious Parade (Blind Box)", "blind-box", "🍰"),
    (r"happy sweets", "Happy Sweets (Lottery Box)", "blind-box", "🍬"),
    (r"starry sky pajama", "Starry Sky Pajama Party", "blind-box", "🌙"),
    (r"colorful bunny|colourful bunn", "Colorful Bunny Babies", "blind-box", "🐰"),
    (r"very berry", "Very Berry Babies", "blind-box", "🫐"),
]

PALETTE = [
    ("#639A67", "#EDF6EE", "#356338"),
    ("#D98A4E", "#FDF2E8", "#915221"),
    ("#D46C8C", "#FCEEF3", "#8E2F4C"),
    ("#5C85B8", "#ECF2FA", "#315482"),
    ("#8F74B8", "#F2EEFA", "#533A7D"),
    ("#4F94A8", "#EAF5F8", "#2A6070"),
    ("#C97B63", "#FAF0EC", "#874532"),
    ("#85A85C", "#F1F7EA", "#4B6B28"),
]


def classify_product(title: str) -> tuple[str, str, str, str] | None:
    """Return (series_name, category, emoji, figure_name) or None if it's an unopened pack."""
    tl = title.lower()
    # Skip unopened pack / full box listings
    if any(p in tl for p in SKIP_PACK_PATTERNS):
        return None
    if re.search(r"\bblind bag\s+20\d\d\b", tl) and not re.search(r"\b(cat|rabbit|fox|bear|panda|husky|koala|deer|otter|mouse|squirrel|poodle|seal|sheep|giraffe|elephant|tiger|penguin|hamster|mole|bulldog|secret)\b", tl):
        return None

    # Clean trailing brand/year suffixes
    clean = re.sub(r"\s*Sylvanian Families.*$", "", title, flags=re.I)
    clean = re.sub(r"\s*Calico Critters.*$", "", clean, flags=re.I)
    clean = re.sub(r"\s*\bBB-\d+\b", "", clean, flags=re.I)
    clean = re.sub(r"\s*\b20\d\d\b", "", clean)
    clean = re.sub(r"\s*(?:Familymart|Lottery|Blind Bag|Blind Box)\b", "", clean, flags=re.I)
    clean = re.sub(r"\s+", " ", clean).strip(" -–|")

    for pattern, series_name, cat, emoji in KNOWN_SERIES:
        if re.search(pattern, tl, re.I):
            # Extract figure name by stripping the series prefix
            fig = re.sub(r"^Doki\s*Doki\s*(?:Collection)?\s*", "", clean, flags=re.I)
            fig = re.sub(r"^Baby\s+Collection\s*", "", fig, flags=re.I)
            fig = re.sub(pattern + r"(?:\s+Series)?(?:\s+\d)?\s*", "", fig, flags=re.I).strip(" -–|:")
            if not fig or len(fig) < 3:
                return None
            return series_name, cat, emoji, fig

    # Fallback: group remaining under Blind Box or Blind Bag Other
    cat = "blind-box" if any(k in tl for k in BLIND_BOX_KEYWORDS) else "blind-bag"
    series_name = "Other Blind Box Figures" if cat == "blind-box" else "Other Blind Bag Figures"
    emoji = "🎁" if cat == "blind-box" else "🌼"
    if not clean or len(clean) < 4:
        return None
    return series_name, cat, emoji, clean


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Sylvanian Families Blind Bags & Blind Boxes")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing WebP images")
    args = parser.parse_args()

    raw_products: list[dict] = []
    for page in range(1, 6):
        try:
            batch = fetch_json(
                f"https://store.kobeejapan.net/collections/blind-bag/products.json?limit=250&page={page}"
            ).get("products", [])
            if not batch:
                break
            raw_products.extend(batch)
        except Exception:
            break

    print(f"Fetched {len(raw_products)} KobeeJapan products")

    grouped: dict[str, dict] = {}
    tasks: list[tuple[str, str]] = []
    used_item_ids: set[str] = set()
    seen_fig_keys: set[str] = set()

    for p in raw_products:
        title = p.get("title", "").strip()
        imgs = p.get("images") or []
        if not imgs or not imgs[0].get("src"):
            continue
        res = classify_product(title)
        if not res:
            continue
        series_name, cat, emoji, fig_name = res
        col_id = f"sf-{'box' if cat == 'blind-box' else 'bag'}-{slugify(series_name)}"
        fig_key = f"{col_id}:{slugify(fig_name)}"
        if fig_key in seen_fig_keys:
            continue
        seen_fig_keys.add(fig_key)

        if col_id not in grouped:
            grouped[col_id] = {
                "series_name": series_name,
                "cat": cat,
                "emoji": emoji,
                "items": [],
            }

        base_id = f"{col_id}-{slugify(fig_name)}"
        iid = base_id
        k = 2
        while iid in used_item_ids:
            iid = f"{base_id}-{k}"
            k += 1
        used_item_ids.add(iid)

        rarity = "Secret" if "secret" in title.lower() else ("Special" if cat == "blind-box" else "Regular")
        handle = p.get("handle", "")
        tasks.append((iid, imgs[0]["src"]))
        grouped[col_id]["items"].append({
            "id": iid,
            "collectionId": col_id,
            "name": fig_name,
            "series": series_name,
            "rarity": rarity,
            "image": f"/images/{iid}.webp",
            "sourceUrl": f"https://store.kobeejapan.net/products/{handle}" if handle else "https://store.kobeejapan.net/collections/blind-bag",
            "imageSourceUrl": imgs[0]["src"],
        })

    collections: list[dict] = []
    items: list[dict] = []
    # Sort series by item count descending (keeping "Other" at the end)
    sorted_groups = sorted(
        grouped.items(),
        key=lambda kv: (kv[1]["series_name"].startswith("Other"), -len(kv[1]["items"]), kv[1]["series_name"]),
    )

    for idx, (col_id, info) in enumerate(sorted_groups):
        accent, accent_soft, accent_text = PALETTE[idx % len(PALETTE)]
        cnt = len(info["items"])
        kind_lbl = "Blind Box Series" if info["cat"] == "blind-box" else "Blind Bag Series"
        collections.append({
            "id": col_id,
            "name": f"Sylvanian Families · {info['series_name']}",
            "shortName": info["series_name"],
            "sylvanianCategory": info["cat"],
            "subtitle": f"{kind_lbl} ({cnt} figures)",
            "maker": "Sylvanian Families / Epoch",
            "accent": accent,
            "accentSoft": accent_soft,
            "accentText": accent_text,
            "emoji": info["emoji"],
        })
        items.extend(info["items"])

    print(f"Downloading {len(tasks)} Sylvanian Families photos across {len(collections)} series...")
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

    valid_items = [i for i in items if (IMAGES_DIR.parent / i["image"].lstrip("/")).is_file()]

    out_ts = DATA_DIR / "sylvanian-families.json"
    out_ts.write_text(
        "\n".join([
            "import type { CatalogItem, CollectionMeta } from '../types';",
            "",
            "export const SYLVANIAN_COLLECTIONS: CollectionMeta[] = " + json.dumps(collections, indent=2) + ";",
            "",
            "export const SYLVANIAN_ITEMS: CatalogItem[] = " + json.dumps(valid_items, indent=2) + ";",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts}: {len(collections)} series, {len(valid_items)} items (downloaded {ok}, failed {failed})")
    for c in collections:
        cnt = sum(1 for i in valid_items if i["collectionId"] == c["id"])
        print(f"  [{c['sylvanianCategory']:9s}] {c['shortName']:30s}: {cnt} figures")


if __name__ == "__main__":
    main()
