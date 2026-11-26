#!/usr/bin/env python3
"""Reproducible Sonny Angel Secret & Robby image/catalog overrides.

Applies all verified manual corrections so the catalog can be cleanly reconstructed:
  1. Refined Regular Series Robby Angels (with matching pedestal base):
     Fruit, Vegetable, Marine, Flower.
  2. Unrefined Robby Angels (no base):
     - Real base-less photos for Fruit, Vegetable, Marine, Flower, Animal 4.
     - Color-accurate base-less SVG placeholders for Animal 1 (dark pink),
       Animal 2 (mustard yellow), and Animal 3 (olive green).
     - Removes non-existent Unrefined Sweets Robby (`sonny-unr-sweets-series-2018-robby`).
  3. Santa's Little Helper Series:
     Pins verified non-swapped photos & names for Santa Claus Sheep (Secret)
     and Reindeer Robby Angel.
  4. Dinosaur Series (2024):
     Pins verified Dinosaur Egg Secret and Robby Angel Egg photos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import IMAGES_DIR, PROJECT_ROOT, download_and_normalize_image

PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"

# (json_file, array_key, item_id, new_name_or_None, target_filename, source_url)
PINNED_PHOTO_OVERRIDES: list[tuple[str, str, str, str | None, str, str]] = [
    # Refined Regular Series Robby Angels (with Sonny Angel pedestal base)
    (
        "sonny-regular.json",
        "items",
        "sonny-fruit-robby",
        None,
        "sonny-fruit-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_4818.jpg?v=1698303353",
    ),
    (
        "sonny-regular.json",
        "items",
        "sonny-vegetable-robby",
        None,
        "sonny-vegetable-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_4838.jpg?v=1698304835",
    ),
    (
        "sonny-regular.json",
        "items",
        "sonny-marine-robby",
        None,
        "sonny-marine-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_dafd8f8c-bb65-4ce7-9a26-0f3b940a1844.jpg?v=1698206301",
    ),
    (
        "sonny-regular.json",
        "items",
        "sonny-flower-robby",
        None,
        "sonny-flower-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/1_e0f34702-2516-4f28-b98d-0ab4bb727d84.jpg?v=1698215111",
    ),
    # Unrefined Robby Angels (no base)
    (
        "sonny-archive.json",
        "unrefinedItems",
        "sonny-unr-fruit-series-2019-robby",
        None,
        "sonny-unr-fruit-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/1_b5f32d29-906c-4d31-95ec-86a38c6bc7de.jpg?v=1701104425",
    ),
    (
        "sonny-archive.json",
        "unrefinedItems",
        "sonny-unr-vegetable-series-2019-robby",
        None,
        "sonny-unr-vegetable-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_8ed4c7ac-2e99-4874-b6ff-53894ef6c42f.jpg?v=1701108688",
    ),
    (
        "sonny-archive.json",
        "unrefinedItems",
        "sonny-unr-marine-series-2019-robby",
        None,
        "sonny-unr-marine-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/3_f2de61dc-f0df-4069-bb0f-95387e00af40.jpg?v=1701105824",
    ),
    (
        "sonny-archive.json",
        "unrefinedItems",
        "sonny-unr-flower-series-2019-robby",
        None,
        "sonny-unr-flower-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/4_5e65aa5a-8339-45c2-b2ab-c33f88b5b8ae.jpg?v=1701104972",
    ),
    (
        "sonny-archive.json",
        "unrefinedItems",
        "sonny-unr-animal-series-4-2018-robby",
        None,
        "sonny-unr-animal-4-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/1_88724459-52ff-40c1-b1f3-267e8fb449b0.jpg?v=1701106877",
    ),
    # Santa's Little Helper Series (note: Toysez had 7_1 and 8_ swapped on their store)
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-santa-s-little-helper-series-secret",
        "Santa Claus Sheep (Secret)",
        "sonny-lim-santa-s-little-helper-series-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/7_1_7063f3c3-68b1-49cb-b799-0dd38e73a10c.jpg?v=1764316245",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-santa-s-little-helper-series-robby",
        "Reindeer Robby Angel",
        "sonny-lim-santa-s-little-helper-series-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/8_2128ee23-6067-4d97-8f69-4af2317b3c34.jpg?v=1764316246",
    ),
    # Dinosaur Series (2024)
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-dinosaur-2024-secret",
        "Newborn Baby Brachiosaurus",
        "sonny-lim-dinosaur-2024-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/4_e074244c-aa88-4bf7-82e0-6005e4b55642.jpg?v=1726207583",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-dinosaur-2024-robby",
        "Robby Angel Egg",
        "sonny-lim-dinosaur-2024-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_52ea886f-55da-4c31-8b24-e7dd7e2891c4.jpg?v=1726207508",
    ),
    # Cat Life Series (2023) Secret (Happy Pink Lucky Cat)
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cat-life-2023-secret",
        "Lucky Cat Secret",
        "sonny-lim-cat-life-2023-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/15_d478d699-f0e5-48c5-a1bd-860571f633ff.jpg?v=1698777015",
    ),
    # Creatures Series (2022) Secret (Donna Wilson Peanut)
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-creatures-series-2022-secret",
        "Peanut (Secret)",
        "sonny-lim-creatures-series-2022-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/1_1f3a9e43-7250-4fb4-a745-55e771fdaa21.jpg?v=1698215319",
    ),
]

# Color-accurate base-less SVG placeholders for Unrefined Robbys without public store photos
UNREFINED_ROBBY_SVGS = [
    ("sonny-unr-animal-series-1-2018-robby", "sonny-unr-animal-1-robby.svg", "#D65482", "#B83D68", "Animal 1 Unrefined"),
    ("sonny-unr-animal-series-2-2018-robby", "sonny-unr-animal-2-robby.svg", "#D9B03C", "#B58E24", "Animal 2 Unrefined"),
    ("sonny-unr-animal-series-3-2018-robby", "sonny-unr-animal-3-robby.svg", "#7D8E4E", "#607038", "Animal 3 Unrefined"),
]

# Non-existent items to strip if regenerated
REMOVED_ITEM_IDS = {
    "sonny-unr-sweets-series-2018-robby",
    "sonny-lim-creatures-series-2022-robby",
}


def make_robby_svg(fill: str, shade: str, label: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#FAF8F5"/>
  <ellipse cx="256" cy="412" rx="86" ry="14" fill="#000000" opacity="0.08"/>
  <ellipse cx="222" cy="112" rx="22" ry="48" transform="rotate(-8 222 112)" fill="{fill}" stroke="{shade}" stroke-width="5"/>
  <ellipse cx="290" cy="112" rx="22" ry="48" transform="rotate(8 290 112)" fill="{fill}" stroke="{shade}" stroke-width="5"/>
  <path d="M198 260 C168 278 152 302 160 314 C168 324 190 314 206 296 Z" fill="{fill}" stroke="{shade}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M314 260 C344 278 360 302 352 314 C344 324 322 314 306 296 Z" fill="{fill}" stroke="{shade}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M200 250 C194 306 196 350 206 392 C209 404 224 408 238 408 C246 408 250 400 252 384 L260 384 C262 400 266 408 274 408 C288 408 303 404 306 392 C316 350 318 306 312 250 Z" fill="{fill}" stroke="{shade}" stroke-width="5" stroke-linejoin="round"/>
  <ellipse cx="256" cy="196" rx="66" ry="72" fill="{fill}" stroke="{shade}" stroke-width="5"/>
  <ellipse cx="256" cy="226" rx="34" ry="24" fill="#FFFFFF" opacity="0.12"/>
  <ellipse cx="226" cy="184" rx="18" ry="21" fill="#FFFFFF" stroke="#221E1C" stroke-width="3"/>
  <circle cx="230" cy="186" r="11" fill="#1E1B1A"/>
  <circle cx="234" cy="181" r="3.5" fill="#FFFFFF"/>
  <path d="M210 172 L203 166 M215 166 L211 159" stroke="#1E1B1A" stroke-width="3" stroke-linecap="round"/>
  <ellipse cx="286" cy="184" rx="18" ry="21" fill="#FFFFFF" stroke="#221E1C" stroke-width="3"/>
  <circle cx="290" cy="186" r="11" fill="#1E1B1A"/>
  <circle cx="294" cy="181" r="3.5" fill="#FFFFFF"/>
  <path d="M302 172 L309 166 M297 166 L301 159" stroke="#1E1B1A" stroke-width="3" stroke-linecap="round"/>
  <ellipse cx="256" cy="234" rx="13" ry="10" fill="#1E1B1A"/>
  <ellipse cx="253" cy="231" rx="4" ry="2.5" fill="#FFFFFF" opacity="0.45"/>
  <text x="256" y="456" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="600" fill="#6B6058">{label} · No Base</text>
</svg>
'''


def main(force_download: bool = False) -> None:
    loaded: dict[str, dict] = {}

    def get_json(fname: str) -> dict:
        if fname not in loaded:
            loaded[fname] = json.loads((PUBLIC_DATA_DIR / fname).read_text(encoding="utf-8"))
        return loaded[fname]

    # 1. Pinned photo overrides
    for fname, arr_key, iid, new_name, img_name, url in PINNED_PHOTO_OVERRIDES:
        out_path = IMAGES_DIR / img_name
        if force_download or not out_path.is_file():
            if out_path.exists():
                out_path.unlink()
            download_and_normalize_image(url, out_path)
        data = get_json(fname)
        for it in data.get(arr_key, []):
            if it["id"] == iid:
                if new_name:
                    it["name"] = new_name
                it["image"] = f"/images/{img_name}"

    # 2. Color-accurate base-less SVG placeholders for remaining Unrefined Robbys
    archive = get_json("sonny-archive.json")
    svg_map: dict[str, str] = {}
    for iid, svg_name, fill, shade, label in UNREFINED_ROBBY_SVGS:
        (IMAGES_DIR / svg_name).write_text(make_robby_svg(fill, shade, label), encoding="utf-8")
        svg_map[iid] = f"/images/{svg_name}"
    for it in archive.get("unrefinedItems", []):
        if it["id"] in svg_map:
            it["image"] = svg_map[it["id"]]

    # 3. Strip non-existent items across all loaded Sonny JSON files
    for data in loaded.values():
        for k, v in list(data.items()):
            if k.lower().endswith("items") and isinstance(v, list):
                data[k] = [it for it in v if it["id"] not in REMOVED_ITEM_IDS]

    for fname, data in loaded.items():
        (PUBLIC_DATA_DIR / fname).write_text(json.dumps(data), encoding="utf-8")

    # Also clean removed IDs from prices.json
    prices_path = PUBLIC_DATA_DIR / "prices.json"
    if prices_path.is_file():
        prices = json.loads(prices_path.read_text(encoding="utf-8"))
        changed = False
        for rid in REMOVED_ITEM_IDS:
            if rid in prices:
                prices.pop(rid, None)
                changed = True
        if changed:
            prices_path.write_text(json.dumps(prices, indent=2) + "\n", encoding="utf-8")

    print(
        f"Applied {len(PINNED_PHOTO_OVERRIDES)} pinned Sonny Angel photo overrides, "
        f"{len(UNREFINED_ROBBY_SVGS)} base-less Unrefined Robby SVGs, "
        f"and {len(REMOVED_ITEM_IDS)} item removals."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply reproducible Sonny Angel Secret & Robby overrides.")
    parser.add_argument("--force", action="store_true", help="Re-download all pinned photos even if present locally.")
    args = parser.parse_args()
    main(force_download=args.force)
