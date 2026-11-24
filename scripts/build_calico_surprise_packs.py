#!/usr/bin/env python3
"""Build Calico Critters Surprise Pack series (Series 1-15 + Classic Packs) from downloaded local photos.

Maps the official North American Calico Critters Baby Collectibles / Surprise Packs
to the verified studio WebP photos already cached in public/images/ and writes src/data/calicoCritters.ts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from common import DATA_DIR, slugify

SURPRISE_PACKS = [
    ("cc-sp-01-baby-band", "Series 1 · Baby Band", r"baby recital", "🎻", "#D98A4E", "#FDF2E8", "#915221"),
    ("cc-sp-02-baby-shopping", "Series 2 · Baby Shopping", r"baby shopping", "🧺", "#639A67", "#EDF6EE", "#356338"),
    ("cc-sp-03-baby-party", "Series 3 · Baby Party", r"baby party", "🎂", "#D46C8C", "#FCEEF3", "#8E2F4C"),
    ("cc-sp-04-baby-costume", "Series 4 · Baby Costume", r"baby transform costume", "👻", "#8F74B8", "#F2EEFA", "#533A7D"),
    ("cc-sp-05-baby-treats", "Series 5 · Baby Treats", r"baby sweets", "🍩", "#E07A8E", "#FDEFF2", "#96384B"),
    ("cc-sp-06-baby-camping", "Series 6 · Baby Camping", r"baby camping", "⛺", "#5C9E62", "#ECF6ED", "#2F6634"),
    ("cc-sp-07-magical-baby", "Series 7 · Magical Baby", r"baby magical|mysterious wizard", "🪄", "#7C65B8", "#F1EEFA", "#4D3885"),
    ("cc-sp-08-baby-fun-hair", "Series 8 · Baby Fun Hair", r"baby stylish hair", "🎀", "#D97B9A", "#FCEFF4", "#8E3856"),
    ("cc-sp-09-baby-seashore", "Series 9 · Baby Seashore Friends", r"baby sea friends|dreamy marine", "🐚", "#4F94A8", "#EAF5F8", "#2A6070"),
    ("cc-sp-10-baby-fairytale", "Series 10 · Baby Fairytale", r"baby fairy tale", "👑", "#C46DA3", "#FCEEF6", "#853165"),
    ("cc-sp-11-baby-forest", "Series 11 · Baby Forest Costume", r"lets play in the forest|baby forest costume", "🍄", "#6B9E78", "#EEF6F0", "#346340"),
    ("cc-sp-12-baking-party", "Series 12 · Baking Baby Party", r"baby cake party", "🧁", "#C97B63", "#FAF0EC", "#874532"),
    ("cc-sp-13-blooming-friends", "Series 13 · Blooming Baby Friends", r"blooming baby friends", "🌼", "#85A85C", "#F1F7EA", "#4B6B28"),
    ("cc-sp-14-fairy-forest", "Series 14 · Fairy Forest Friends", r"fairy forest friends", "🧚", "#5C85B8", "#ECF2FA", "#315482"),
    ("cc-sp-15-baby-adventure", "Series 15 · Baby Adventure", r"baby adventure|baby explorers", "🧭", "#B88B4A", "#FAF4EA", "#7A5724"),
    ("cc-sp-milky-way-friends", "Milky Way Friends", r"milky way", "🌌", "#5C6BC0", "#ECEEFB", "#2F3D8F"),
    ("cc-sp-tea-party-friends", "Tea Party Friends", r"tea time|tea party", "🫖", "#D47A96", "#FCEEF3", "#8E3854"),
    ("cc-sp-hamburger-friends", "Hamburger Shop Friends", r"hamburger shop", "🍔", "#D98A4E", "#FDF2E8", "#915221"),
    ("cc-sp-very-berry-friends", "Very Berry Friends", r"very berry", "🫐", "#8E5EA2", "#F4ECF8", "#58316B"),
    ("cc-sp-delicious-parade", "Delicious Parade Friends", r"delicious parade", "🍰", "#E07A6B", "#FDEFEB", "#963B2E"),
    ("cc-sp-happy-sweets", "Happy Sweets Friends", r"happy sweets", "🍬", "#E089B0", "#FDEFF6", "#964068"),
    ("cc-sp-starry-pajama", "Starry Sky Pajama Friends", r"starry sky pajama", "🌙", "#647BB8", "#EDF1FA", "#32477D"),
    ("cc-sp-classic-packs", "Classic Surprise Packs", r"baby and stroller|rocking horse|baby craft lovers|baby fruit party", "🍼", "#A67653", "#F8F0EA", "#6B4529"),
]

# Also preserve the 8 original Calico Critter studio items in their matching Surprise Pack series
ORIGINAL_CC = [
    ("cc-creme-rabbit", "cc-sp-01-baby-band", "Crème Chocolate Rabbit (Violin)", "Regular", "/images/cc-creme-rabbit.webp"),
    ("cc-ryan-persian", "cc-sp-14-fairy-forest", "Ryan Persian Cat (Fairy)", "Special", "/images/cc-ryan-persian.webp"),
    ("cc-albert-mouse", "cc-sp-05-baby-treats", "Albert Marshmallow Mouse (Donut)", "Regular", "/images/cc-albert-mouse.webp"),
    ("cc-ambrose-squirrel", "cc-sp-15-baby-adventure", "Ambrose Walnut Squirrel (Explorer)", "Regular", "/images/cc-ambrose-squirrel.webp"),
    ("cc-lily-tuxedo", "cc-sp-08-baby-fun-hair", "Lily Tuxedo Cat (Ribbon Bow)", "Regular", "/images/cc-lily-tuxedo.webp"),
    ("cc-sandy-otter", "cc-sp-09-baby-seashore", "Sandy Otter (Seashell)", "Regular", "/images/cc-sandy-otter.webp"),
    ("cc-gilly-silk-cat", "cc-sp-04-baby-costume", "Gilly Silk Cat (Ghost)", "Special", "/images/cc-gilly-silk-cat.webp"),
    ("cc-milo-poodle", "cc-sp-12-baking-party", "Milo Toy Poodle (Chef)", "Secret", "/images/cc-milo-poodle.webp"),
]


def clean_fig_name(raw_name: str, pattern: str) -> str:
    s = re.sub(pattern + r"(?:\s+series)?(?:\s+\d+)?\s*", "", raw_name, flags=re.I)
    s = re.sub(r"^\d+\s+", "", s).strip(" -–|:")
    s = s.replace("Biolin", "Violin").replace("Lobstar", "Lobster")
    return s or raw_name


def main() -> None:
    sf_txt = (DATA_DIR / "sullivanFamily.ts").read_text(encoding="utf-8")
    sf_items = json.loads(re.search(r"SULLIVAN_ITEMS: CatalogItem\[\] = (\[.*?\]);", sf_txt, re.S).group(1))

    items_by_col: dict[str, list[dict]] = {row[0]: [] for row in SURPRISE_PACKS}
    label_by_col = {row[0]: row[1] for row in SURPRISE_PACKS}
    used_ids: set[str] = set()
    seen_keys: set[str] = set()

    for iid, col_id, name, rarity, img in ORIGINAL_CC:
        used_ids.add(iid)
        seen_keys.add(f"{col_id}:{slugify(name)}")
        items_by_col[col_id].append({
            "id": iid,
            "collectionId": col_id,
            "name": name,
            "series": label_by_col[col_id],
            "rarity": rarity,
            "image": img,
        })

    for item in sf_items:
        hay = f"{item['series']} {item['name']}".lower()
        for col_id, label, pattern, *_ in SURPRISE_PACKS:
            if re.search(pattern, hay, re.I):
                fig_name = clean_fig_name(item["name"], pattern)
                key = f"{col_id}:{slugify(fig_name)}"
                if key in seen_keys:
                    break
                seen_keys.add(key)
                base = f"{col_id}-{slugify(fig_name)}"
                iid = base
                k = 2
                while iid in used_ids:
                    iid = f"{base}-{k}"
                    k += 1
                used_ids.add(iid)
                rarity = "Secret" if "secret" in fig_name.lower() else item["rarity"]
                items_by_col[col_id].append({
                    "id": iid,
                    "collectionId": col_id,
                    "name": fig_name,
                    "series": label,
                    "rarity": rarity,
                    "image": item["image"],
                })
                break

    collections: list[dict] = []
    all_items: list[dict] = []
    for col_id, label, _, emoji, accent, accent_soft, accent_text in SURPRISE_PACKS:
        col_items = items_by_col[col_id]
        if not col_items:
            continue
        collections.append({
            "id": col_id,
            "name": f"Calico Critters · {label}",
            "shortName": label,
            "subtitle": f"Surprise Pack Series ({len(col_items)} figures)",
            "maker": "Epoch",
            "accent": accent,
            "accentSoft": accent_soft,
            "accentText": accent_text,
            "emoji": emoji,
        })
        all_items.extend(col_items)

    out_ts = DATA_DIR / "calicoCritters.ts"
    out_ts.write_text(
        "\n".join([
            "import type { CatalogItem, CollectionMeta } from '../types';",
            "",
            "export const CALICO_COLLECTIONS: CollectionMeta[] = " + json.dumps(collections, indent=2) + ";",
            "",
            "export const CALICO_ITEMS: CatalogItem[] = " + json.dumps(all_items, indent=2) + ";",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts}: {len(collections)} Surprise Pack series, {len(all_items)} items")
    for c in collections:
        cnt = sum(1 for i in all_items if i["collectionId"] == c["id"])
        print(f"  {c['shortName']:34s}: {cnt} figures")


if __name__ == "__main__":
    main()
