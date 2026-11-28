#!/usr/bin/env python3
"""Fetch POP MART Zsiga series (Blind Box, Plush, Mixed Sets, Standalone) & photos.

Sources:
  - arttoyfamilia.com/collections/zsiga (dedicated Zsiga multi-variant series)
  - toysez.com/collections/zsiga (additional series, mixed-IP sets & standalone figures)

Writes src/data/zsiga.ts and downloads normalized 512x512 WebP photos into public/images/.
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import DATA_DIR, IMAGES_DIR, download_and_normalize_image, fetch_json, slugify

SKIP_VARIANT_KEYWORDS = (
    "full set",
    "fullset",
    "whole set",
    "confirmed figures",
    "blind box",
    "single box",
    "assorted",
    "random",
    "sealed",
    "complete set",
    "display",
    "case",
)

SKIP_PRODUCT_KEYWORDS = (
    "pop bean",
    "phone",
    "case",
    "bag",
    "tote",
    "cable",
    "badge",
    "pin",
    "magnet",
    "earphone",
    "greeting card",
    "ring box",
    "cup",
    "mug",
    "mirror",
    "pillow",
    "blanket",
    "400%",
    "1000%",
    "mega",
    "protective",
    "acrylic",
)

PALETTE = [
    ("#C97B63", "#FAF0EC", "#874532"),
    ("#D98A4E", "#FDF2E8", "#915221"),
    ("#6B9E78", "#EEF6F0", "#346340"),
    ("#5C85B8", "#ECF2FA", "#315482"),
    ("#9B6BB8", "#F4EEFA", "#5E3478"),
    ("#D46C8C", "#FCEEF3", "#8E2F4C"),
    ("#4F94A8", "#EAF5F8", "#2A6070"),
    ("#B88B4A", "#FAF4EA", "#7A5724"),
]


def fetch_paginated(base_url: str, max_pages: int = 6) -> list[dict]:
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        try:
            batch = fetch_json(base_url.format(page)).get("products", [])
            if not batch:
                break
            out.extend(batch)
        except Exception:
            break
    return out


def is_skip_variant(title: str) -> bool:
    tl = title.lower()
    return tl == "default title" or any(k in tl for k in SKIP_VARIANT_KEYWORDS)


def is_skip_product(title: str) -> bool:
    tl = title.lower()
    return any(k in tl for k in SKIP_PRODUCT_KEYWORDS)


def pick_emoji(title: str, category: str) -> str:
    t = title.lower()
    if category == "mixed":
        return "🎠"
    if category == "standalone":
        return "✨"
    if "forest" in t:
        return "🦊"
    if "winter" in t or "gift" in t:
        return "🎁"
    if "sun" in t:
        return "☀️"
    if "slow" in t:
        return "🌿"
    if "care bear" in t:
        return "🧸"
    if "kids" in t or "cute" in t:
        return "🎈"
    if "twins" in t:
        return "👯"
    if "drifter" in t:
        return "🎒"
    if "let it be" in t:
        return "☔"
    if "show" in t:
        return "🎭"
    return "🐾"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Zsiga series and individual photos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing WebP images")
    args = parser.parse_args()

    atf_products = fetch_paginated(
        "https://arttoyfamilia.com/collections/zsiga/products.json?limit=250&page={}",
        max_pages=4,
    )
    tz_products = fetch_paginated(
        "https://toysez.com/collections/zsiga/products.json?limit=250&page={}",
        max_pages=6,
    )
    print(f"Fetched {len(atf_products)} ATF products and {len(tz_products)} Toysez products")

    collections: list[dict] = []
    items: list[dict] = []
    tasks: list[tuple[str, str]] = []
    seen_series_slugs: set[str] = set()
    used_item_ids: set[str] = set()

    def add_item(
        col_id: str,
        name: str,
        series_name: str,
        rarity: str,
        img_url: str | None,
        source_url: str | None = None,
    ) -> bool:
        if not img_url:
            return False
        base = f"{col_id}-{slugify(name)}"
        iid = base
        k = 2
        while iid in used_item_ids:
            iid = f"{base}-{k}"
            k += 1
        used_item_ids.add(iid)
        tasks.append((iid, img_url))
        item: dict = {
            "id": iid,
            "collectionId": col_id,
            "name": name,
            "series": series_name,
            "rarity": rarity,
            "image": f"/images/{iid}.webp",
            "imageSourceUrl": img_url,
        }
        if source_url:
            item["sourceUrl"] = source_url
        items.append(item)
        return True

    # 1. Dedicated Zsiga multi-variant series from Art Toy Familia
    for p in atf_products:
        raw_title = p.get("title", "").strip()
        tl = raw_title.lower()
        if "zsiga" not in tl or is_skip_product(raw_title):
            continue

        img_map = {im["id"]: im["src"] for im in p.get("images", [])}
        fallback_img = p["images"][0]["src"] if p.get("images") else None
        valid_vars = [v for v in p.get("variants", []) if not is_skip_variant(v.get("title", ""))]
        if len(valid_vars) < 5:
            continue

        clean_series = re.sub(r"^Zsiga\s*[×x]?\s*", "", raw_title, flags=re.I)
        clean_series = re.sub(r"\s*Blind Box.*$", "", clean_series, flags=re.I)
        clean_series = re.sub(r"\s*Figures?$", "", clean_series, flags=re.I).strip()
        s_slug = slugify(clean_series)
        if not s_slug or s_slug in seen_series_slugs:
            continue
        seen_series_slugs.add(s_slug)

        col_id = f"zs-series-{s_slug}"
        accent, accent_soft, accent_text = PALETTE[len(collections) % len(PALETTE)]

        added = 0
        for v in valid_vars:
            vt = v.get("title", "").strip()
            vimg = (
                (v.get("featured_image") or {}).get("src")
                or img_map.get(v.get("image_id"))
                or fallback_img
            )
            is_sec = "secret" in vt.lower() or "hidden" in vt.lower()
            clean_name = re.sub(r"\s*\((?:secret|hidden|super secret)[^)]*\)", "", vt, flags=re.I).strip()
            if clean_name and add_item(col_id, clean_name, clean_series, "Secret" if is_sec else "Regular", vimg):
                added += 1

        if added > 0:
            sec_cnt = sum(1 for i in items if i["collectionId"] == col_id and i["rarity"] == "Secret")
            reg_cnt = added - sec_cnt
            collections.append({
                "id": col_id,
                "name": f"Zsiga · {clean_series}",
                "shortName": clean_series,
                "subtitle": f"Blind Box Series ({reg_cnt}" + (f" + {sec_cnt} Secret)" if sec_cnt else " figures)"),
                "maker": "POP MART",
                "accent": accent,
                "accentSoft": accent_soft,
                "accentText": accent_text,
                "emoji": pick_emoji(clean_series, "series"),
            })

    # 2. Additional Zsiga series, Mixed-IP sets, and Standalone figures from Toysez
    tz_grouped: dict[str, list[tuple[str, str, str]]] = {}
    mixed_items: list[tuple[str, str, str, str]] = []
    standalone_items: list[tuple[str, str, str]] = []
    seen_standalone: set[str] = set()

    for p in tz_products:
        title = p.get("title", "").strip()
        tl = title.lower()
        img = p["images"][0]["src"] if p.get("images") else None
        if not img or is_skip_product(title) or "complete set" in tl or "whole set" in tl:
            continue

        # Pattern A: "Zsiga <Series> Series <Figure>" or "Zsiga <Series> Blind Box Series: <Figure>"
        m = re.match(r"^Zsiga\s+(.+?\s+Series)(?:\s*:\s*|\s+)(.+)$", title, re.I)
        if m:
            ser_raw = re.sub(r"\s*Blind Box\s*", " ", m.group(1), flags=re.I).strip()
            fig_raw = m.group(2).strip()
            fig_clean = re.sub(r"\s*\((?:Confirmed Style|Secret[^)]*|1/\d+)\)", "", fig_raw, flags=re.I).strip()
            fig_clean = re.sub(r"^Secret\s+", "", fig_clean, flags=re.I).strip()
            rarity = "Secret" if "secret" in tl else ("Special" if "special" in tl else "Regular")

            # Check if it's a Mixed-IP POP MART series (e.g., Wealthy Snake, Golden Gallop, Hand in Hand)
            if any(
                kw in ser_raw.lower()
                for kw in ("wealthy snake", "golden gallop", "hand in hand", "anniversary", "celebrat", "attic", "good run", "pop mart")
            ):
                mixed_items.append((fig_clean, ser_raw, rarity, img))
            else:
                s_slug = slugify(ser_raw)
                if not any(s_slug in ex or ex in s_slug for ex in seen_series_slugs):
                    tz_grouped.setdefault(ser_raw, []).append((fig_clean, rarity, img))
            continue

        # Pattern B: Standalone / Limited Art Figures
        if "limited" in tl or "figurine" in tl or "figure" in tl or "plush" in tl:
            clean = re.sub(r"^Zsiga\s+", "", title, flags=re.I)
            clean = re.sub(r"\s*(?:Art Toy|Limited Edition|Limited)$", "", clean, flags=re.I).strip()
            key = slugify(clean)
            if clean and key not in seen_standalone:
                seen_standalone.add(key)
                standalone_items.append((clean, "Special", img))

    for ser_raw, figs in tz_grouped.items():
        if len(figs) < 3:
            continue
        s_slug = slugify(ser_raw)
        seen_series_slugs.add(s_slug)
        col_id = f"zs-series-{s_slug}"
        accent, accent_soft, accent_text = PALETTE[len(collections) % len(PALETTE)]
        for fig_name, rarity, img in figs:
            add_item(col_id, fig_name, ser_raw, rarity, img)
        sec_cnt = sum(1 for _, r, _ in figs if r == "Secret")
        reg_cnt = len(figs) - sec_cnt
        collections.append({
            "id": col_id,
            "name": f"Zsiga · {ser_raw}",
            "shortName": ser_raw,
            "subtitle": f"Series ({reg_cnt}" + (f" + {sec_cnt} Secret)" if sec_cnt else " figures)"),
            "maker": "POP MART",
            "accent": accent,
            "accentSoft": accent_soft,
            "accentText": accent_text,
            "emoji": pick_emoji(ser_raw, "series"),
        })

    # Also pull Zsiga figures from Mixed Sets on Art Toy Familia
    seen_mixed: set[str] = {slugify(f"{s}-{n}") for n, s, _, _ in mixed_items}
    for p in atf_products:
        title = p.get("title", "").strip()
        if "zsiga" in title.lower() or is_skip_product(title):
            continue
        img_map = {im["id"]: im["src"] for im in p.get("images", [])}
        fallback_img = p["images"][0]["src"] if p.get("images") else None
        for v in p.get("variants", []):
            vt = v.get("title", "").strip()
            if "zsiga" in vt.lower():
                vimg = (
                    (v.get("featured_image") or {}).get("src")
                    or img_map.get(v.get("image_id"))
                    or fallback_img
                )
                key = slugify(f"{title}-{vt}")
                if vimg and key not in seen_mixed:
                    seen_mixed.add(key)
                    rarity = "Secret" if "secret" in vt.lower() else ("Special" if "special" in vt.lower() else "Regular")
                    mixed_items.append((vt, title, rarity, vimg))

    if mixed_items:
        col_id = "zs-mixed-sets"
        for fig_name, ser_name, rarity, img in mixed_items:
            add_item(col_id, fig_name, ser_name, rarity, img)
        cnt = sum(1 for i in items if i["collectionId"] == col_id)
        collections.append({
            "id": col_id,
            "name": "Zsiga · Mixed-IP Sets",
            "shortName": "Mixed-IP Sets",
            "subtitle": f"POP MART Crossover & Holiday Sets ({cnt} figures)",
            "maker": "POP MART",
            "accent": "#D4943A",
            "accentSoft": "#FDF4E6",
            "accentText": "#8A5812",
            "emoji": "🎠",
        })

    if standalone_items:
        col_id = "zs-standalone"
        for fig_name, rarity, img in standalone_items:
            add_item(col_id, fig_name, "Standalone / Limited Edition", rarity, img)
        cnt = sum(1 for i in items if i["collectionId"] == col_id)
        collections.append({
            "id": col_id,
            "name": "Zsiga · Standalone Figures",
            "shortName": "Standalone Figures",
            "subtitle": f"Limited Art Figurines & Plush ({cnt} figures)",
            "maker": "POP MART",
            "accent": "#7A6BB8",
            "accentSoft": "#F1EEFA",
            "accentText": "#4A3A85",
            "emoji": "✨",
        })

    print(f"Downloading {len(tasks)} Zsiga photos across {len(collections)} series...")
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

    out_ts = DATA_DIR / "zsiga.ts"
    out_ts.write_text(
        "\n".join([
            "import type { CatalogItem, CollectionMeta } from '../types';",
            "",
            "export const ZSIGA_COLLECTIONS: CollectionMeta[] = " + json.dumps(collections, indent=2) + ";",
            "",
            "export const ZSIGA_ITEMS: CatalogItem[] = " + json.dumps(items, indent=2) + ";",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts}: {len(collections)} series, {len(items)} items (downloaded {ok}, failed {failed})")
    for c in collections:
        cnt = sum(1 for i in items if i["collectionId"] == c["id"])
        print(f"  {c['shortName']:30s}: {cnt} figures")


if __name__ == "__main__":
    main()
