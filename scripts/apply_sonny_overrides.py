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
import io
import json
import urllib.request
from pathlib import Path

from PIL import Image
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
    # Harvest Series (2021) Secret (Happiness Hedgehog)
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-harvest-series-2021-secret",
        "Happiness (Secret)",
        "sonny-lim-harvest-series-2021-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/10_2eb369c7-c176-4d30-af42-49feabecc1d8.jpg?v=1699272605",
    ),
    # Bug's World Series (2022) Secret (Bumblebee) & Bee Robby Angel
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-bug-s-world-2022-secret",
        "Bumblebee",
        "sonny-lim-bug-s-world-2022-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/60_5ef78407-e045-463f-85d7-cd64e62d3323.jpg?v=1699159272",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-bug-s-world-2022-robby",
        "Bee Robby Angel",
        "sonny-lim-bug-s-world-2022-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/56_cdad5ed7-71e8-4593-977d-fe578a361ea0.jpg?v=1699159335",
    ),
    # Sonny Angel in Wonderland Series (2020) Drink Me Robby Angel
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-in-wonderland-series-2020-robby",
        "Drink Me Robby Angel",
        "sonny-lim-in-wonderland-series-2020-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/7_3e6f98b6-e771-4870-85df-1cd583aa108d.jpg?v=1699383370",
    ),
    # Cactus Series (2020) Secret Cactus & Cactus Robby Angel
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cactus-series-2020-secret",
        "Secret Cactus",
        "sonny-lim-cactus-series-2020-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_9680.jpg?v=1702391419",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cactus-series-2020-robby",
        "Cactus Robby Angel",
        "sonny-lim-cactus-series-2020-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_9701.jpg?v=1702393043",
    ),
    # Circus Series (2019) Secret Rabbit (distinct from 2022 Join the Circus Merry-Go-Round)
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-circus-series-secret",
        "Circus Rabbit (Secret)",
        "sonny-lim-circus-series-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/52_3fa39198-afc8-4b62-a8bd-28d3ab852e23.jpg?v=1699454395",
    ),
    # Cherry Blossom Series (2019, 2021 Night Version, 2022 Peaceful Spring) Secrets & Robbys
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cherry-blossom-series-secret",
        "Cherry Blossom Secret (2019)",
        "sonny-lim-cherry-blossom-series-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/31_70e455dc-1c0b-4f1d-8dd4-0b2c6ab7ea94.jpg?v=1699462207",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cherry-blossom-series-robby",
        "Cherry Blossom Robby Angel (2019)",
        "sonny-lim-cherry-blossom-series-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/48_c215d7ea-26ec-4a08-b0bf-ed31d7161147.jpg?v=1699462132",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cherry-blossom-night-version-2021-secret",
        "Cherry Blossom Secret (Night)",
        "sonny-lim-cherry-blossom-night-version-2021-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/9_28851dc7-f755-4546-b155-546fcfb47c3e.jpg?v=1699357760",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cherry-blossom-night-version-2021-robby",
        "Cherry Blossom Robby (Night)",
        "sonny-lim-cherry-blossom-night-version-2021-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/74_f9376c04-31d9-4014-8377-d67794c8f6de.jpg?v=1699357692",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cherry-blossom-peaceful-spring-edition-2022-secret",
        "Cherry Blossom Secret (Peaceful Spring)",
        "sonny-lim-cherry-blossom-peaceful-spring-edition-2022-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/33_3dcc2542-8b36-4faf-b80f-1110ee0d512d.jpg?v=1699163077",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-cherry-blossom-peaceful-spring-edition-2022-robby",
        "Cherry Blossom Robby (Peaceful Spring)",
        "sonny-lim-cherry-blossom-peaceful-spring-edition-2022-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_686ca813-c833-49f8-a183-c3b68ba60732.jpg?v=1699163029",
    ),
    # Valentine's Day Series 2019, 2018, 2017 Secrets & Robbys
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-valentine-s-day-series-2019-secret",
        "Secret Rabbit (Valentine 2019)",
        "sonny-lim-valentine-s-day-series-2019-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/11_7c32555e-d8c0-484d-9cac-5aa585ebc824.jpg?v=1699521747",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-valentine-s-day-series-2019-robby",
        "Valentine 2019 Robby Angel",
        "sonny-lim-valentine-s-day-series-2019-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/4_042cb6fc-4c18-4792-9108-7bfbc836ce0b.jpg?v=1699521683",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-valentine-s-day-series-2018-secret",
        "Secret Rose Bouquet",
        "sonny-lim-valentine-s-day-series-2018-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/19_83bccf1a-52fe-4ca6-a58e-c2ef84b54bad.jpg?v=1699662170",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-valentine-s-day-series-2018-robby",
        "Valentine 2018 Robby Angel",
        "sonny-lim-valentine-s-day-series-2018-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/18_ce2e17f7-d94a-4d45-ad75-161aedcdf708.jpg?v=1699661964",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-valentine-s-day-series-2017-secret",
        "Secret Pink Cat",
        "sonny-lim-valentine-s-day-series-2017-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/50_d00108a9-1cfe-4dea-b8c7-bd7afdba3de8.jpg?v=1699526933",
    ),
    (
        "sonny-limited.json",
        "items",
        "sonny-lim-valentine-s-day-series-2017-robby",
        "Valentine 2017 Robby Angel",
        "sonny-lim-valentine-s-day-series-2017-robby.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/51_b17ebf77-60da-495f-9857-fd96330eb039.jpg?v=1699526793",
    ),
    # Vintage: Valentine's Chocolate (2016) — all 6 real Toysez photos
    (
        "sonny-vintage.json",
        "items",
        "sonny-vin-valentine-s-chocolate-2016-strawberry-chocolate",
        None,
        "sonny-vin-valentine-s-chocolate-2016-strawberry-chocolate.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/3_1_7cf89990-64a7-4b7d-ba6e-53e0e2fd363e.jpg?v=1776156929",
    ),
    (
        "sonny-vintage.json",
        "items",
        "sonny-vin-valentine-s-chocolate-2016-kiwi-chocolate",
        None,
        "sonny-vin-valentine-s-chocolate-2016-kiwi-chocolate.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/4_2_cbad695a-e7f2-475a-9322-27347c6482e8.jpg?v=1776156929",
    ),
    (
        "sonny-vintage.json",
        "items",
        "sonny-vin-valentine-s-chocolate-2016-berry-chocolate",
        None,
        "sonny-vin-valentine-s-chocolate-2016-berry-chocolate.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/5_3_634cb801-67f1-42b0-b962-4603b30839b3.jpg?v=1776156929",
    ),
    (
        "sonny-vintage.json",
        "items",
        "sonny-vin-valentine-s-chocolate-2016-orange-chocolate",
        None,
        "sonny-vin-valentine-s-chocolate-2016-orange-chocolate.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_2_919d1030-0fb2-4a5c-828d-cb843ca18c1c.jpg?v=1776156929",
    ),
    (
        "sonny-vintage.json",
        "items",
        "sonny-vin-valentine-s-chocolate-2016-white-chocolate-secret",
        "Kiwi Chocolate Secret",
        "sonny-vin-valentine-s-chocolate-2016-white-chocolate-secret.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/6_2_2c6510cd-c003-4c5d-94dd-1893b33e5e39.jpg?v=1776156929",
    ),
    (
        "sonny-vintage.json",
        "items",
        "sonny-vin-valentine-s-chocolate-2016-chocolate-robby-angel",
        "Cherry Robby Angel",
        "sonny-vin-valentine-s-chocolate-2016-chocolate-robby-angel.webp",
        "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_8eeca6d6-4868-46eb-99c0-8c2dfbde6a8e.jpg?v=1701103506",
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
    "sonny-lim-summer-festival-series-2021-robby",
    "sonny-lim-harvest-series-2021-robby",
    "sonny-lim-valentine-s-day-series-2017-secret-3",
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
                it["imageSourceUrl"] = url

    # 2. Color-accurate base-less SVG placeholders for remaining Unrefined Robbys
    archive = get_json("sonny-archive.json")
    svg_map: dict[str, str] = {}
    for iid, svg_name, fill, shade, label in UNREFINED_ROBBY_SVGS:
        (IMAGES_DIR / svg_name).write_text(make_robby_svg(fill, shade, label), encoding="utf-8")
        svg_map[iid] = f"/images/{svg_name}"
    for it in archive.get("unrefinedItems", []):
        if it["id"] in svg_map:
            it["image"] = svg_map[it["id"]]

    # 3. Halloween (2021) 2022 re-release: 3 additional Secret & Robby colors (Purple, Green, Pink)
    hw_url = "https://www.sonnyangel.com/renewal/wp-content/uploads/2022/09/img_halloween2022_01.png"
    hw_source_page = "https://www.sonnyangel.com/en/2022/09/09/halloween2022/"
    hw_variants = [
        ("sonny-lim-halloween-series-2021-secret-purple", "Pumpkin Rabbit (Purple)", "sonny-lim-halloween-series-2021-secret-purple.webp", 0, "rabbit", 169.55),
        ("sonny-lim-halloween-series-2021-robby-purple", "Pumpkin Pants Robby (Purple)", "sonny-lim-halloween-series-2021-robby-purple.webp", 0, "robby", 537.31),
        ("sonny-lim-halloween-series-2021-secret-green", "Pumpkin Rabbit (Green)", "sonny-lim-halloween-series-2021-secret-green.webp", 1, "rabbit", 169.55),
        ("sonny-lim-halloween-series-2021-robby-green", "Pumpkin Pants Robby (Green)", "sonny-lim-halloween-series-2021-robby-green.webp", 1, "robby", 537.31),
        ("sonny-lim-halloween-series-2021-secret-pink", "Pumpkin Rabbit (Pink)", "sonny-lim-halloween-series-2021-secret-pink.webp", 2, "rabbit", 169.55),
        ("sonny-lim-halloween-series-2021-robby-pink", "Pumpkin Pants Robby (Pink)", "sonny-lim-halloween-series-2021-robby-pink.webp", 2, "robby", 537.31),
    ]
    need_hw_crop = force_download or any(not (IMAGES_DIR / v[2]).is_file() for v in hw_variants)
    if need_hw_crop:
        req = urllib.request.Request(hw_url, headers={"User-Agent": "Mozilla/5.0"})
        hw_img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read()))
        w, h = hw_img.size
        pw = w / 3.0
        for _, _, fname, panel, kind, _ in hw_variants:
            if kind == "rabbit":
                box = (int(panel * pw + 0.02 * pw), int(0.18 * h), int(panel * pw + 0.50 * pw), int(0.95 * h))
            else:
                box = (int(panel * pw + 0.51 * pw), int(0.32 * h), int(panel * pw + 0.99 * pw), int(0.95 * h))
            sub = hw_img.crop(box).convert("RGB")
            canvas = Image.new("RGB", (512, 512), (255, 255, 255))
            sub.thumbnail((476, 476), Image.Resampling.LANCZOS)
            canvas.paste(sub, ((512 - sub.width) // 2, (512 - sub.height) // 2))
            canvas.save(IMAGES_DIR / fname, "WEBP", quality=88)

    limited = get_json("sonny-limited.json")
    existing_lim_ids = {it["id"] for it in limited.get("items", [])}
    for it in limited.get("items", []):
        if it["id"] == "sonny-lim-halloween-series-2021-secret":
            it["name"] = "Pumpkin Rabbit (Orange)"
        elif it["id"] == "sonny-lim-halloween-series-2021-robby":
            it["name"] = "Pumpkin Pants Robby (Orange)"
    for iid, name, fname, _, _, _ in hw_variants:
        if iid not in existing_lim_ids:
            limited["items"].append({
                "id": iid,
                "collectionId": "sonny-lim-halloween-series-2021",
                "name": name,
                "series": "Halloween Series(2021)",
                "rarity": "Secret",
                "image": f"/images/{fname}",
                "sourceUrl": hw_source_page,
            })

    # 3b. Cactus Series (2020) 4 Lucky Color Variants (Monkey, Mouse, Parrot, Rabbit)
    cactus_lucky = [
        ("sonny-lim-cactus-series-2020-lucky-monkey", "Lucky Monkey", "sonny-lim-cactus-series-2020-lucky-monkey.webp", "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_9689.jpg?v=1702392330", 447.76),
        ("sonny-lim-cactus-series-2020-lucky-mouse", "Lucky Mouse", "sonny-lim-cactus-series-2020-lucky-mouse.webp", "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_9691.jpg?v=1702392499", 447.76),
        ("sonny-lim-cactus-series-2020-lucky-parrot", "Lucky Parrot", "sonny-lim-cactus-series-2020-lucky-parrot.webp", "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_9693.jpg?v=1702392698", 268.66),
        ("sonny-lim-cactus-series-2020-lucky-rabbit", "Lucky Rabbit", "sonny-lim-cactus-series-2020-lucky-rabbit.webp", "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/IMG_9696.jpg?v=1702392804", 298.51),
    ]
    for iid, name, fname, url, _ in cactus_lucky:
        out_path = IMAGES_DIR / fname
        if force_download or not out_path.is_file():
            if out_path.exists():
                out_path.unlink()
            download_and_normalize_image(url, out_path)
        if iid not in existing_lim_ids:
            limited["items"].append({
                "id": iid,
                "collectionId": "sonny-lim-cactus-series-2020",
                "name": name,
                "series": "Cactus Series (2020)",
                "rarity": "Lucky",
                "image": f"/images/{fname}",
                "imageSourceUrl": url,
            })

    # 3c. Extra Valentine's Day 2018 (2nd Secret) & 2017 (2nd & 3rd Secrets)
    valentine_extra = [
        (
            "sonny-lim-valentine-s-day-series-2018-secret-single-rose",
            "sonny-lim-valentine-s-day-series-2018",
            "Secret Single Rose",
            "Valentine's Day Series 2018",
            "sonny-lim-valentine-s-day-series-2018-secret-single-rose.webp",
            "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/47_8756ead4-c76e-4dd5-8549-fcebc031c60d.jpg?v=1699662094",
            53.73,
        ),
        (
            "sonny-lim-valentine-s-day-series-2017-secret-white-bear",
            "sonny-lim-valentine-s-day-series-2017",
            "Secret White Bear",
            "Valentine's Day Series 2017",
            "sonny-lim-valentine-s-day-series-2017-secret-white-bear.webp",
            "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/39_e2dd701a-0952-4124-854e-bc84f32c3fc4.jpg?v=1699526848",
            58.20,
        ),
    ]
    for iid, col_id, name, series, fname, url, _ in valentine_extra:
        out_path = IMAGES_DIR / fname
        if url:
            if force_download or not out_path.is_file():
                if out_path.exists():
                    out_path.unlink()
                download_and_normalize_image(url, out_path)
        elif not out_path.is_file():
            out_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
                '<rect width="512" height="512" fill="#FDF2F5"/>'
                '<circle cx="256" cy="220" r="96" fill="#E86A8D" opacity="0.18"/>'
                '<text x="256" y="242" text-anchor="middle" font-size="88">💝</text>'
                '<text x="256" y="388" text-anchor="middle" font-family="system-ui,sans-serif" font-size="20" font-weight="600" fill="#9E3A58">Valentine 2017 Secret #3</text>'
                '</svg>\n',
                encoding="utf-8",
            )
        if iid not in existing_lim_ids:
            entry = {
                "id": iid,
                "collectionId": col_id,
                "name": name,
                "series": series,
                "rarity": "Secret",
                "image": f"/images/{fname}",
            }
            if url:
                entry["imageSourceUrl"] = url
            limited["items"].append(entry)

    # 3d. Sky Color Series (2017 Special) Secret (Aurora 2017) & Sky Color Robby Angel (2017)
    sky_spc_extra = [
        (
            "sonny-spc-sky-color-series-secret",
            "Aurora (Secret)",
            "sonny-spc-sky-color-series-secret.webp",
            "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/2_2_018b61a0-fb21-4890-a61c-db1adf2dbe80.jpg?v=1776179439",
            185.07,
        ),
        (
            "sonny-spc-sky-color-series-robby",
            "Sky Color Robby Angel",
            "sonny-spc-sky-color-series-robby.webp",
            "https://cdn.shopify.com/s/files/1/0561/4606/7644/files/5_69271af6-37e4-473a-9965-7e9dcd8c2ed7.jpg?v=1701106572",
            298.51,
        ),
    ]
    for it in limited.get("items", []):
        if it["id"] == "sonny-lim-sky-color-series-2020-secret":
            it["name"] = "Aurora (Secret)"
        elif it["id"] == "sonny-lim-sky-color-series-2020-robby":
            it["name"] = "Sky Color Robby Angel"
    spc_by_id = {it["id"]: it for it in archive.get("specialItems", [])}
    for iid, name, fname, url, _ in sky_spc_extra:
        out_path = IMAGES_DIR / fname
        if force_download or not out_path.is_file():
            if out_path.exists():
                out_path.unlink()
            download_and_normalize_image(url, out_path)
        if iid in spc_by_id:
            spc_by_id[iid]["name"] = name
            spc_by_id[iid]["image"] = f"/images/{fname}"
            spc_by_id[iid]["imageSourceUrl"] = url
        else:
            archive["specialItems"].append({
                "id": iid,
                "collectionId": "sonny-spc-sky-color-series",
                "name": name,
                "series": "Sky Color Series",
                "rarity": "Secret",
                "image": f"/images/{fname}",
                "imageSourceUrl": url,
            })

    # 3e. Vintage: Caribbean Sea Summer (2016) & Dreamy Halloween (2018) cropped from official sonnyangel.com announcements
    vintage = get_json("sonny-vintage.json")
    vin_by_id = {it["id"]: it for it in vintage.get("items", [])}

    vintage_crops = [
        (
            "https://www.sonnyangel.com/renewal/wp-content/uploads/2018/10/news_sa_summer2016.png",
            "https://www.sonnyangel.com/en/2016/06/17/sonny-angel-summer-series-caribbean-sea-version-%e7%99%ba%e5%a3%b2%e6%b1%ba%e5%ae%9a%ef%bc%81/",
            [
                ("sonny-vin-caribbean-sea-summer-2016-orange-panama-hat", "sonny-vin-caribbean-sea-summer-2016-orange-panama-hat.webp", (0.01, 0.49, 0.175, 0.83)),
                ("sonny-vin-caribbean-sea-summer-2016-blue-straw-hat", "sonny-vin-caribbean-sea-summer-2016-blue-straw-hat.webp", (0.175, 0.50, 0.33, 0.83)),
                ("sonny-vin-caribbean-sea-summer-2016-tropical-beach", "sonny-vin-caribbean-sea-summer-2016-tropical-beach.webp", (0.33, 0.49, 0.485, 0.83)),
                ("sonny-vin-caribbean-sea-summer-2016-pink-panama-hat", "sonny-vin-caribbean-sea-summer-2016-pink-panama-hat.webp", (0.485, 0.50, 0.64, 0.83)),
                ("sonny-vin-caribbean-sea-summer-2016-sailor-panama-hat", "sonny-vin-caribbean-sea-summer-2016-sailor-panama-hat.webp", (0.64, 0.49, 0.795, 0.83)),
                ("sonny-vin-caribbean-sea-summer-2016-yellow-straw-hat", "sonny-vin-caribbean-sea-summer-2016-yellow-straw-hat.webp", (0.76, 0.36, 0.995, 0.84)),
            ],
        ),
        (
            "https://www.sonnyangel.com/renewal/wp-content/uploads/2018/10/news_sa_halloween.png",
            "https://www.sonnyangel.com/en/2018/08/30/sonny-angel-%e3%83%8f%e3%83%ad%e3%82%a6%e3%82%a3%e3%83%b3%e3%82%b7%e3%83%aa%e3%83%bc%e3%82%ba%e7%99%ba%e5%a3%b2%e6%b1%ba%e5%ae%9a%ef%bc%81/",
            [
                ("sonny-vin-dreamy-halloween-2018-pastel-witch", "sonny-vin-dreamy-halloween-2018-pastel-witch.webp", (0.04, 0.35, 0.285, 0.83)),
                ("sonny-vin-dreamy-halloween-2018-pastel-pumpkin", "sonny-vin-dreamy-halloween-2018-pastel-pumpkin.webp", (0.275, 0.39, 0.49, 0.83)),
                ("sonny-vin-dreamy-halloween-2018-pastel-ghost", "sonny-vin-dreamy-halloween-2018-pastel-ghost.webp", (0.485, 0.40, 0.735, 0.83)),
                ("sonny-vin-dreamy-halloween-2018-pastel-owl-witch", "sonny-vin-dreamy-halloween-2018-pastel-owl-witch.webp", (0.73, 0.37, 0.96, 0.83)),
            ],
        ),
    ]
    for sheet_url, src_page, specs in vintage_crops:
        need_sheet = force_download or any(not (IMAGES_DIR / s[1]).is_file() for s in specs)
        sheet_img = None
        if need_sheet:
            req = urllib.request.Request(sheet_url, headers={"User-Agent": "Mozilla/5.0"})
            sheet_img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read()))
        for iid, fname, (fx0, fy0, fx1, fy1) in specs:
            out_path = IMAGES_DIR / fname
            if sheet_img is not None and (force_download or not out_path.is_file()):
                sw, sh = sheet_img.size
                sub = sheet_img.crop((int(fx0 * sw), int(fy0 * sh), int(fx1 * sw), int(fy1 * sh))).convert("RGB")
                canvas = Image.new("RGB", (512, 512), (255, 255, 255))
                sub.thumbnail((476, 476), Image.Resampling.LANCZOS)
                canvas.paste(sub, ((512 - sub.width) // 2, (512 - sub.height) // 2))
                canvas.save(out_path, "WEBP", quality=88)
            if iid in vin_by_id:
                vin_by_id[iid]["image"] = f"/images/{fname}"
                vin_by_id[iid]["sourceUrl"] = src_page

    # Add the 2 missing Caribbean Sea (2016) Panama Hat figures & fix Pirate Captain Secret placeholder
    carib_src = "https://www.sonnyangel.com/en/2016/06/17/sonny-angel-summer-series-caribbean-sea-version-%e7%99%ba%e5%a3%b2%e6%b1%ba%e5%ae%9a%ef%bc%81/"
    carib_new = [
        ("sonny-vin-caribbean-sea-summer-2016-pink-panama-hat", "Pink Panama Hat", "sonny-vin-caribbean-sea-summer-2016-pink-panama-hat.webp", 35.0),
        ("sonny-vin-caribbean-sea-summer-2016-sailor-panama-hat", "Sailor Panama Hat", "sonny-vin-caribbean-sea-summer-2016-sailor-panama-hat.webp", 35.0),
    ]
    for iid, name, fname, _ in carib_new:
        if iid not in vin_by_id:
            item_obj = {
                "id": iid,
                "collectionId": "sonny-vin-caribbean-sea-summer-2016",
                "name": name,
                "series": "Caribbean Sea Summer (2016)",
                "rarity": "Special",
                "image": f"/images/{fname}",
                "sourceUrl": carib_src,
            }
            vintage["items"].append(item_obj)
            vin_by_id[iid] = item_obj

    # Dedicated Pirate Captain Secret SVG placeholder (not Sailor Panama Hat)
    pirate_svg = IMAGES_DIR / "sonny-vin-caribbean-sea-summer-2016-pirate-captain.svg"
    pirate_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
        '<rect width="512" height="512" fill="#F4F8FB"/>'
        '<ellipse cx="256" cy="414" rx="80" ry="14" fill="#1F2937" opacity="0.1"/>'
        '<path d="M138 190 Q256 82 374 190 Q316 214 256 208 Q196 214 138 190 Z" fill="#22272E" stroke="#111418" stroke-width="5"/>'
        '<path d="M168 184 Q256 140 344 184" fill="none" stroke="#E5B84B" stroke-width="6"/>'
        '<circle cx="256" cy="146" r="16" fill="#FAF8F5"/>'
        '<circle cx="256" cy="232" r="56" fill="#F0C6A0" stroke="#C9966B" stroke-width="4"/>'
        '<circle cx="236" cy="230" r="7" fill="#221E1C"/>'
        '<circle cx="276" cy="230" r="7" fill="#221E1C"/>'
        '<path d="M246 252 Q256 260 266 252" fill="none" stroke="#8C5B44" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M206 286 L306 286 L316 364 L196 364 Z" fill="#B9314F" stroke="#7A1D32" stroke-width="4" stroke-linejoin="round"/>'
        '<rect x="242" y="288" width="28" height="74" fill="#FAF8F5"/>'
        '<rect x="218" y="364" width="28" height="44" rx="12" fill="#F0C6A0" stroke="#C9966B" stroke-width="4"/>'
        '<rect x="266" y="364" width="28" height="44" rx="12" fill="#F0C6A0" stroke="#C9966B" stroke-width="4"/>'
        '<text x="256" y="458" text-anchor="middle" font-family="system-ui,sans-serif" font-size="18" font-weight="600" fill="#374151">Pirate Captain · Secret (2016)</text>'
        '</svg>\n',
        encoding="utf-8",
    )
    if "sonny-vin-caribbean-sea-summer-2016-pirate-captain" in vin_by_id:
        vin_by_id["sonny-vin-caribbean-sea-summer-2016-pirate-captain"]["image"] = "/images/sonny-vin-caribbean-sea-summer-2016-pirate-captain.svg"
        vin_by_id["sonny-vin-caribbean-sea-summer-2016-pirate-captain"].pop("sourceUrl", None)

    # 4. Strip non-existent items across all loaded Sonny JSON files
    for data in loaded.values():
        for k, v in list(data.items()):
            if k.lower().endswith("items") and isinstance(v, list):
                data[k] = [it for it in v if it["id"] not in REMOVED_ITEM_IDS]

    for fname, data in loaded.items():
        (PUBLIC_DATA_DIR / fname).write_text(json.dumps(data), encoding="utf-8")

    # Also clean removed IDs and add prices for added variants in prices.json
    prices_path = PUBLIC_DATA_DIR / "prices.json"
    if prices_path.is_file():
        prices = json.loads(prices_path.read_text(encoding="utf-8"))
        changed = False
        for rid in REMOVED_ITEM_IDS:
            if rid in prices:
                prices.pop(rid, None)
                changed = True
        for iid, _, _, _, _, default_p in hw_variants:
            if iid not in prices:
                prices[iid] = default_p
                changed = True
        for iid, _, _, _, default_p in cactus_lucky:
            if iid not in prices:
                prices[iid] = default_p
                changed = True
        prices["sonny-lim-cactus-series-2020-secret"] = 89.55
        prices["sonny-lim-cactus-series-2020-robby"] = 298.51
        prices["sonny-lim-circus-series-secret"] = 59.70
        prices["sonny-lim-cherry-blossom-series-secret"] = 202.99
        prices["sonny-lim-cherry-blossom-series-robby"] = 447.76
        prices["sonny-lim-cherry-blossom-night-version-2021-secret"] = 208.96
        prices["sonny-lim-cherry-blossom-night-version-2021-robby"] = 537.31
        prices["sonny-lim-cherry-blossom-peaceful-spring-edition-2022-secret"] = 238.81
        prices["sonny-lim-cherry-blossom-peaceful-spring-edition-2022-robby"] = 537.31
        prices["sonny-lim-valentine-s-day-series-2019-secret"] = 61.42
        prices["sonny-lim-valentine-s-day-series-2019-robby"] = 171.42
        prices["sonny-lim-valentine-s-day-series-2018-secret"] = 62.69
        prices["sonny-lim-valentine-s-day-series-2018-robby"] = 268.65
        prices["sonny-lim-valentine-s-day-series-2017-secret"] = 65.67
        prices["sonny-lim-valentine-s-day-series-2017-robby"] = 161.19
        for iid, _, _, _, _, _, default_p in valentine_extra:
            if iid not in prices:
                prices[iid] = default_p
        for iid, _, _, _, default_p in sky_spc_extra:
            prices[iid] = default_p
        for iid, _, _, default_p in carib_new:
            if iid not in prices:
                prices[iid] = default_p
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
