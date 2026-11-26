#!/usr/bin/env python3
"""Apply all curated non-Sonny catalog fixes & deduplications idempotently.

Ensures that re-running any discovery or refresh script can never re-introduce
removed duplicates, multi-box bundle variants, or broken items across:
  - Skullpanda (public/data/skullpanda.json)
  - Zsiga (public/data/zsiga.json)
  - Jellycat (public/data/jellycat.json)
  - Sylvanian Families (public/data/sylvanian-families.json)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"
IMAGES_DIR = ROOT / "public" / "images"
PRICES_PATH = DATA_DIR / "prices.json"

BUNDLE_NAME_RE = re.compile(
    r"(?:\b1\s*blind\s*box\b|\bone\s+blind\s*box\b|\bwhole\s+set\b|\bfull\s*set\b|"
    r"\bsealed\s+(?:fullset|happiness|set|box)\b|\b\d+\s+confirmed\s+(?:figures|styles)\b|"
    r"\bseries\s+16\s+bags\b)",
    re.I,
)

# Duplicate collection IDs / names that must never be present
SKULLPANDA_REMOVE_SERIES = {
    "pop attach θ skullpanda off mode series",
    "off mode series plush doll pendant",
}

ZSIGA_REMOVE_SERIES = {
    "life is a show mini action figure series",
    "life is a show series mini action figure",
    "i'm zsiga series vinyl plush pendant",
}

JELLYCAT_REMOVE_NAMES = {
    "Amuseables Carole Canel",
    "Amuseables Mireille St. Honor",
    "Amuseables Mirielle St. Honor",
    "Amuseables Mullover Spiced",
    "Amuseables Sports Ski Goggles",
    "Amuseables Shamrock Bag Charm",
    "Amuseables Birthday Cake Clip-On Charm",
    "Amuseables Disco Ball Clip-On Charm",
    "Bartholomew Bear 'Alpine' Outfit",
    "Jack ‘Alpine’ Outfit",
    "Munro Scottie Dog Plush 'Winter Jumper'",
    "Rufferty Puppy Wizard",
    "Strutton Pigeon",
    "Amuseables Pink and White Marshmallow",
    "Amuseables Pink and White Marshmallows - 5x4 Inch",
    "Amuseables Cloud - Medium/Large",
    "Amuseables Moon - Medium/Large",
    "Amuseables Sports Tennis Ball - 4 Inch",
    "Amuseables Sports Badminton - 6 Inch",
    "Amuseables Sports Baseball - 4 Inch",
    "Large Sky Dragon",
    "Bashful Lion Original",
    "Franilla Luxe Bunny Original",
    "Bashful Luxe Bunny",
    "Bartholomew Bear Fluffleshade Hat L/XL",
    "Amuseables Rainbow Gigantic",
    "Amuseables Sun Gigantic",
    "Bashful Beige Bunny Gigantic",
    "Gilbert The Great Blue Whale Gigantic",
}

JELLYCAT_SIZE_SUFFIX_RE = re.compile(
    r"^(.+?)\s*[-–]?\s*(?:\d+(?:x\d+)?\s*(?:inch|in|\"|cm)|medium/large|small/medium|gigantic)$",
    re.I,
)


def remove_item_assets(item: dict, prices: dict) -> None:
    prices.pop(item["id"], None)
    img_rel = item.get("image", "").lstrip("/")
    if img_rel:
        img_p = ROOT / "public" / img_rel
        if img_p.exists():
            img_p.unlink()


def clean_shelf(
    filename: str,
    remove_series_lower: set[str],
    remove_names: set[str] | None = None,
    prices: dict | None = None,
    jellycat_size_dedup: bool = False,
) -> int:
    path = DATA_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    prices = prices if prices is not None else {}
    remove_names = remove_names or set()

    drop_cids = {
        c["id"]
        for c in data["collections"]
        if (c.get("shortName") or c["name"]).strip().lower() in remove_series_lower
    }

    existing_names_lower = {it["name"].lower() for it in data["items"]}
    kept_items = []
    removed = 0
    for it in data["items"]:
        nm = it["name"]
        drop = (
            it["collectionId"] in drop_cids
            or nm in remove_names
            or bool(BUNDLE_NAME_RE.search(nm))
        )
        if not drop and jellycat_size_dedup:
            m = JELLYCAT_SIZE_SUFFIX_RE.match(nm)
            if m and m.group(1).strip().lower() in existing_names_lower:
                drop = True
        if drop:
            remove_item_assets(it, prices)
            removed += 1
        else:
            kept_items.append(it)

    if removed or drop_cids:
        data["collections"] = [c for c in data["collections"] if c["id"] not in drop_cids]
        data["items"] = kept_items
        for c in data["collections"]:
            cnt = sum(1 for it in kept_items if it["collectionId"] == c["id"])
            c["subtitle"] = re.sub(r"\(\d+\)$", f"({cnt})", c["subtitle"])
            c["subtitle"] = re.sub(r"\(\d+ figures\)", f"({cnt} figures)", c["subtitle"])
        path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    return removed


def main() -> None:
    prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))

    r_sp = clean_shelf("skullpanda.json", SKULLPANDA_REMOVE_SERIES, prices=prices)
    r_zs = clean_shelf("zsiga.json", ZSIGA_REMOVE_SERIES, prices=prices)
    r_jc = clean_shelf("jellycat.json", set(), JELLYCAT_REMOVE_NAMES, prices=prices, jellycat_size_dedup=True)
    r_sf = clean_shelf("sylvanian-families.json", set(), prices=prices)

    total = r_sp + r_zs + r_jc + r_sf
    if total:
        PRICES_PATH.write_text(json.dumps(prices, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    print(
        f"Catalog overrides applied: removed {total} unwanted/duplicate items "
        f"(Skullpanda -{r_sp}, Zsiga -{r_zs}, Jellycat -{r_jc}, Sylvanian -{r_sf})"
    )


if __name__ == "__main__":
    main()
