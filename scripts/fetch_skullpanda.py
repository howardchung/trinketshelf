#!/usr/bin/env python3
"""Fetch POP MART Skullpanda series (Blind Box, Plush Pendants, Mixed Sets) & photos.

Sources:
  - arttoyfamilia.com/collections/skullpanda (dedicated Skullpanda multi-variant series)
  - toysez.com/collections/skullpanda (newest series + Skullpanda figures in Mixed-IP sets)

Writes src/data/skullpanda.ts and downloads normalized 512x512 WebP photos into public/images/.
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
    "all ",
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
    "charger",
    "badge",
    "pin",
    "magnet",
    "earphone",
    "keychain",
    "coaster",
    "cup",
    "mug",
    "mirror",
    "pillow",
    "blanket",
    "umbrella",
    "400%",
    "1000%",
    "mega",
    "secret figurines",
    "protective",
    "acrylic",
)

PALETTE = [
    ("#7C65B8", "#F1EEFA", "#4D3885"),
    ("#9B5DE5", "#F5EEFD", "#5E2B97"),
    ("#5C7AEA", "#EDF1FD", "#2E47A3"),
    ("#C85A82", "#FCEEF3", "#852A4B"),
    ("#4F94A8", "#EAF5F8", "#2A6070"),
    ("#B86B5C", "#FAF0EE", "#7A382C"),
    ("#6A8CAF", "#EEF3F8", "#355575"),
    ("#8B6F9E", "#F3EFF6", "#543B66"),
]


def is_skip_variant(title: str) -> bool:
    tl = title.lower()
    if tl == "default title":
        return True
    return any(k in tl for k in SKIP_VARIANT_KEYWORDS)


def is_skip_product(title: str) -> bool:
    tl = title.lower()
    return any(k in tl for k in SKIP_PRODUCT_KEYWORDS)


def fetch_paginated(base_url: str, max_pages: int = 8) -> list[dict]:
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


def pick_emoji(title: str, category: str) -> str:
    t = title.lower()
    if category == "plush":
        return "🧸"
    if category == "mixed":
        return "🎠"
    if "winter" in t or "snow" in t:
        return "❄️"
    if "warmth" in t or "feast" in t:
        return "🕯️"
    if "night" in t or "castle" in t or "addams" in t or "mare" in t:
        return "🦇"
    if "plum" in t or "petal" in t or "flower" in t or "impression" in t:
        return "🌸"
    if "sound" in t or "paradox" in t:
        return "🎧"
    if "wonderland" in t or "reality" in t:
        return "🪞"
    if "hype" in t or "online" in t or "connect" in t:
        return "⚡"
    return "🌙"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Skullpanda series and studio photos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing WebP images")
    args = parser.parse_args()

    atf_products = fetch_paginated(
        "https://arttoyfamilia.com/collections/skullpanda/products.json?limit=250&page={}",
        max_pages=4,
    )
    tz_products = fetch_paginated(
        "https://toysez.com/collections/skullpanda/products.json?limit=250&page={}",
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

    # 1. Dedicated Skullpanda Blind Box & Plush Pendant Series from Art Toy Familia
    for p in atf_products:
        raw_title = p.get("title", "").strip()
        tl = raw_title.lower()
        if "skullpanda" not in tl or is_skip_product(raw_title):
            continue

        img_map = {im["id"]: im["src"] for im in p.get("images", [])}
        fallback_img = p["images"][0]["src"] if p.get("images") else None
        valid_vars = [v for v in p.get("variants", []) if not is_skip_variant(v.get("title", ""))]
        if len(valid_vars) < 6:
            # Skip single standalone items here (we only want full series with >= 6 figures)
            continue

        clean_series = re.sub(r"^[θ\s]*Skullpanda\s*[×x]?\s*", "", raw_title, flags=re.I)
        clean_series = re.sub(r"\s*Blind Box.*$", "", clean_series, flags=re.I)
        clean_series = re.sub(r"\s*Figures?$", "", clean_series, flags=re.I).strip()
        s_slug = slugify(clean_series)
        if not s_slug or s_slug in seen_series_slugs:
            continue
        seen_series_slugs.add(s_slug)

        is_plush = "plush" in tl
        cat = "plush" if is_plush else "blind-box"
        col_id = f"sp-{'plush' if is_plush else 'series'}-{s_slug}"
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
            sub_lbl = f"{'Plush Pendant' if is_plush else 'Blind Box'} Series ({reg_cnt}" + (
                f" + {sec_cnt} Secret)" if sec_cnt else " figures)"
            )
            collections.append({
                "id": col_id,
                "name": f"Skullpanda · {clean_series}",
                "shortName": clean_series,
                "skullpandaCategory": cat,
                "subtitle": sub_lbl,
                "maker": "POP MART",
                "accent": accent,
                "accentSoft": accent_soft,
                "accentText": accent_text,
                "emoji": pick_emoji(clean_series, cat),
            })

    # 2. Additional newest Skullpanda series + Mixed-IP POP MART sets from Toysez
    tz_grouped: dict[str, list[tuple[str, str, str]]] = {}
    mixed_items: list[tuple[str, str, str, str]] = []  # (name, series, rarity, img)

    for p in tz_products:
        title = p.get("title", "").strip()
        tl = title.lower()
        img = p["images"][0]["src"] if p.get("images") else None
        if not img or is_skip_product(title) or "complete set" in tl or "whole set" in tl:
            continue

        # Newest dedicated series formatted "Skullpanda <Series> Blind Box Series: <Figure>"
        m = re.match(
            r"^Skullpanda\s+(.+?)\s+(?:Plush Doll Pendant\s+)?Blind Box Series:\s*(.+)$",
            title,
            re.I,
        )
        if m:
            ser_raw, fig_raw = m.group(1).strip(), m.group(2).strip()
            s_slug = slugify(ser_raw)
            # Only add if not already captured from Art Toy Familia
            if not any(s_slug in existing or existing in s_slug for existing in seen_series_slugs):
                is_sec = "secret" in fig_raw.lower()
                fig_clean = re.sub(r"\s*\((?:Confirmed Style|Secret[^)]*)\)", "", fig_raw, flags=re.I).strip()
                tz_grouped.setdefault(ser_raw, []).append((fig_clean, "Secret" if is_sec else "Regular", img))
            continue

        # Mixed-IP POP MART series appearances (titles mentioning Pop Mart + Series)
        if "pop mart" in tl and "series" in tl:
            m2 = re.match(r"^Skullpanda\s+Pop Mart\s+(.+?Series)\s*(?::|\s)\s*(.+)$", title, re.I)
            if m2:
                ser_name = m2.group(1).strip()
                fig_name = re.sub(r"\s*\((?:Confirmed Style|Secret[^)]*)\)", "", m2.group(2), flags=re.I).strip()
                rarity = "Secret" if "secret" in tl else ("Special" if "special" in tl else "Regular")
                mixed_items.append((fig_name, ser_name, rarity, img))

    for ser_raw, figs in tz_grouped.items():
        if len(figs) < 4:
            continue
        is_plush = "plush" in ser_raw.lower() or "online" in ser_raw.lower()
        cat = "plush" if is_plush else "blind-box"
        s_slug = slugify(ser_raw)
        col_id = f"sp-{'plush' if is_plush else 'series'}-{s_slug}"
        accent, accent_soft, accent_text = PALETTE[len(collections) % len(PALETTE)]
        for fig_name, rarity, img in figs:
            add_item(col_id, fig_name, ser_raw, rarity, img)
        sec_cnt = sum(1 for _, r, _ in figs if r == "Secret")
        reg_cnt = len(figs) - sec_cnt
        collections.append({
            "id": col_id,
            "name": f"Skullpanda · {ser_raw}",
            "shortName": ser_raw,
            "skullpandaCategory": cat,
            "subtitle": f"{'Plush Pendant' if is_plush else 'Blind Box'} Series ({reg_cnt}" + (
                f" + {sec_cnt} Secret)" if sec_cnt else " figures)"
            ),
            "maker": "POP MART",
            "accent": accent,
            "accentSoft": accent_soft,
            "accentText": accent_text,
            "emoji": pick_emoji(ser_raw, cat),
        })

    # Also pull Skullpanda-specific figures from Mixed Sets on Art Toy Familia
    seen_mixed_keys: set[str] = {slugify(f"{s}-{n}") for n, s, _, _ in mixed_items}
    for p in atf_products:
        title = p.get("title", "").strip()
        tl = title.lower()
        if "skullpanda" in tl or is_skip_product(title):
            continue
        img_map = {im["id"]: im["src"] for im in p.get("images", [])}
        fallback_img = p["images"][0]["src"] if p.get("images") else None
        for v in p.get("variants", []):
            vt = v.get("title", "").strip()
            if "skullpanda" in vt.lower() or "sp " in vt.lower():
                vimg = (
                    (v.get("featured_image") or {}).get("src")
                    or img_map.get(v.get("image_id"))
                    or fallback_img
                )
                key = slugify(f"{title}-{vt}")
                if vimg and key not in seen_mixed_keys:
                    seen_mixed_keys.add(key)
                    rarity = "Secret" if "secret" in vt.lower() else ("Special" if "special" in vt.lower() else "Regular")
                    mixed_items.append((vt, title, rarity, vimg))

    if mixed_items:
        col_id = "sp-mixed-sets"
        for fig_name, ser_name, rarity, img in mixed_items:
            add_item(col_id, fig_name, ser_name, rarity, img)
        cnt = sum(1 for i in items if i["collectionId"] == col_id)
        collections.append({
            "id": col_id,
            "name": "Skullpanda · Mixed-IP Sets",
            "shortName": "Mixed-IP Sets",
            "skullpandaCategory": "mixed",
            "subtitle": f"POP MART Crossover & Anniversary Sets ({cnt} figures)",
            "maker": "POP MART",
            "accent": "#D4943A",
            "accentSoft": "#FDF4E6",
            "accentText": "#8A5812",
            "emoji": "🎠",
        })

    print(f"Downloading {len(tasks)} Skullpanda photos across {len(collections)} series...")
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

    out_ts = DATA_DIR / "skullpanda.ts"
    out_ts.write_text(
        "\n".join([
            "import type { CatalogItem, CollectionMeta } from '../types';",
            "",
            "export const SKULLPANDA_COLLECTIONS: CollectionMeta[] = " + json.dumps(collections, indent=2) + ";",
            "",
            "export const SKULLPANDA_ITEMS: CatalogItem[] = " + json.dumps(items, indent=2) + ";",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts}: {len(collections)} series, {len(items)} items (downloaded {ok}, failed {failed})")
    for c in collections:
        cnt = sum(1 for i in items if i["collectionId"] == c["id"])
        print(f"  [{c['skullpandaCategory']:9s}] {c['shortName']} ({cnt})")


if __name__ == "__main__":
    main()
