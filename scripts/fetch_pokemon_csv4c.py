#!/usr/bin/env python3
"""Fetch Simplified Chinese Pokémon TCG 'Reward Round' (CSV4C / 嘉奖回合) Master Set list & prices.

Data sources:
  - Card checklist, Chinese-exclusive artwork, and ungraded market prices from PriceCharting
    (https://www.pricecharting.com/console/pokemon-chinese-csv4c?format=json)
  - Fallback Scarlet & Violet card artwork from local public/data/pokemon/sv*.json for common/uncommon
    cards where PriceCharting has no scan yet.

Master Set includes:
  - All 165 numbered cards (#001–#129 main set + #130–#165 AR/SR/SAR/UR)
  - Poké Ball Reverse Holo variants for all non-ex main set cards (#001–#129)
  - Master Ball Reverse Holo variants for all non-ex main set cards (#001–#129)

Outputs:
  - public/data/pokemon/csv4c.json
  - Inserts/updates 'pkmn-csv4c' in src/data/pokemonSets.ts and updates POKEMON_TOTAL_GM_CARDS
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT

POKEMON_DATA_DIR = PROJECT_ROOT / "public" / "data" / "pokemon"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

SET_ID = "csv4c"
COL_ID = f"pkmn-{SET_ID}"
SET_NAME = "Reward Round (CSV4C · Simplified Chinese)"
SHORT_NAME = "Reward Round (CN)"
ERA = "Simplified Chinese"
RELEASE_DATE = "2025/07/18"

# Rarity bands for CSV4C (#130-#165)
def classify_csv4c_rarity(num: int, name: str) -> tuple[str, str]:
    """Return (tcg_rarity_label, app_rarity)."""
    if 162 <= num <= 165:
        return "UR (Ultra Rare)", "Secret"
    if 153 <= num <= 161:
        return "SAR (Special Art Rare)", "Secret"
    if 138 <= num <= 152:
        return "SR (Super Rare)", "Secret"
    if 130 <= num <= 137:
        return "AR (Art Rare)", "Special"
    if re.search(r"\bex\b", name, re.I):
        return "RR (Double Rare)", "Special"
    return "Main Set", "Regular"


def parse_price(raw: str) -> float | None:
    if not raw:
        return None
    m = re.search(r"\$?([\d,]+\.\d+|\d+)", raw.replace(",", ""))
    if not m:
        return None
    val = float(m.group(1))
    return round(val, 2) if val > 0 else None


def norm_name(s: str) -> str:
    s = re.sub(r"\[[^\]]+\]", "", s)
    s = re.sub(r"#\d+.*$", "", s)
    s = s.lower().replace("é", "e").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def load_sv_fallback_images() -> dict[str, str]:
    """Build normalized card name -> image URL map from local Scarlet & Violet sets."""
    img_map: dict[str, str] = {}
    # Prefer Paradox Rift (sv4), Obsidian Flames (sv3), Paldea Evolved (sv2), SV Base (sv1), Paldean Fates (sv4pt5)
    for sid in ("sv4", "sv3", "sv2", "sv1", "sv4pt5", "sv5", "sv6", "sv7", "sv8"):
        p = POKEMON_DATA_DIR / f"{sid}.json"
        if not p.is_file():
            continue
        for c in json.loads(p.read_text(encoding="utf-8")):
            if c["id"].endswith(("-rev", "-mb", "-1ed")):
                continue
            cname = re.sub(r"^#\S+\s+", "", c["name"])
            key = norm_name(cname)
            if key and key not in img_map and c.get("image"):
                img_map[key] = c["image"]
    return img_map


def upgrade_pc_image(uri: str) -> str:
    if not uri or "no-image-available" in uri:
        return ""
    return re.sub(r"/60\.jpg$", "/240.jpg", uri)


def fetch_csv4c_products() -> list[dict[str, Any]]:
    prods: list[dict[str, Any]] = []
    for cursor in (0, 150, 300):
        url = f"https://www.pricecharting.com/console/pokemon-chinese-csv4c?sort=model-number&cursor={cursor}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            batch = json.loads(r.read().decode("utf-8")).get("products", [])
        if not batch:
            break
        prods.extend(batch)
    return prods


def main() -> None:
    print("Fetching Simplified Chinese 'Reward Round' (CSV4C) from PriceCharting...")
    prods = fetch_csv4c_products()
    fallback_imgs = load_sv_fallback_images()

    # Group products by card number (1..165)
    base_by_num: dict[int, dict[str, Any]] = {}
    pb_by_num: dict[int, dict[str, Any]] = {}
    mb_by_num: dict[int, dict[str, Any]] = {}

    for p in prods:
        if not p.get("isCard"):
            continue
        pname = p.get("productName", "")
        m = re.search(r"#(\d+)", pname)
        if not m:
            continue
        num = int(m.group(1))
        pl = pname.lower()
        if "[master ball]" in pl:
            mb_by_num[num] = p
        elif "[poke ball]" in pl or "[pokeball]" in pl:
            pb_by_num[num] = p
        else:
            if num not in base_by_num:
                base_by_num[num] = p

    cards_out: list[dict[str, Any]] = []
    est_total = 0.0
    priced_real = 0
    img_from_pc = 0
    img_from_sv = 0

    for num in sorted(base_by_num.keys()):
        p = base_by_num[num]
        raw_name = re.sub(r"\s*#\d+.*$", "", p["productName"]).strip()
        # Normalize capitalization of "Ex" -> "ex"
        clean_name = re.sub(r"\bEx\b", "ex", raw_name)
        tcg_rarity, app_rarity = classify_csv4c_rarity(num, clean_name)
        display_num = f"#{str(num).zfill(3)}"

        img = upgrade_pc_image(p.get("imageUri", ""))
        if img:
            img_from_pc += 1
        else:
            img = fallback_imgs.get(norm_name(clean_name), "")
            if img:
                img_from_sv += 1

        # Base card price
        pc_price = parse_price(p.get("price1", ""))
        if pc_price is not None:
            price = pc_price
            priced_real += 1
        else:
            price = 1.50 if "RR" in tcg_rarity else 0.25

        pc_url = f"https://www.pricecharting.com/game/pokemon-chinese-csv4c/{p['id']}" if p.get("id") else "https://www.pricecharting.com/console/pokemon-chinese-csv4c"
        cards_out.append({
            "id": f"pkmn-{SET_ID}-{num}",
            "collectionId": COL_ID,
            "name": f"{display_num} {clean_name}",
            "series": f"Reward Round (CSV4C) · {tcg_rarity}",
            "rarity": app_rarity,
            "image": img,
            "sourceUrl": pc_url,
            "imageSourceUrl": img,
            "priceSourceUrl": pc_url,
            "price": price,
        })
        est_total += price

        # Master Set variants: all non-ex main set cards (#1..#129) have Poké Ball & Master Ball reverse holos
        is_main_non_ex = num <= 129 and "RR" not in tcg_rarity
        if is_main_non_ex:
            # Poké Ball Reverse Holo
            pb_prod = pb_by_num.get(num)
            pb_img = upgrade_pc_image(pb_prod.get("imageUri", "")) if pb_prod else ""
            pb_price = parse_price(pb_prod.get("price1", "")) if pb_prod else None
            if pb_price is not None:
                priced_real += 1
            else:
                pb_price = 1.00
            cards_out.append({
                "id": f"pkmn-{SET_ID}-{num}-pb",
                "collectionId": COL_ID,
                "name": f"{display_num} {clean_name} (Poké Ball)",
                "series": "Reward Round (CSV4C) · Poké Ball Reverse",
                "rarity": "Regular",
                "image": pb_img or img,
                "price": pb_price,
            })
            est_total += pb_price

            # Master Ball Reverse Holo
            mb_prod = mb_by_num.get(num)
            mb_img = upgrade_pc_image(mb_prod.get("imageUri", "")) if mb_prod else ""
            mb_price = parse_price(mb_prod.get("price1", "")) if mb_prod else None
            if mb_price is not None:
                priced_real += 1
            else:
                mb_price = 4.50
            cards_out.append({
                "id": f"pkmn-{SET_ID}-{num}-mb",
                "collectionId": COL_ID,
                "name": f"{display_num} {clean_name} (Master Ball)",
                "series": "Reward Round (CSV4C) · Master Ball Reverse",
                "rarity": "Special",
                "image": mb_img or img,
                "price": mb_price,
            })
            est_total += mb_price

    # Write public/data/pokemon/csv4c.json
    POKEMON_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_json = POKEMON_DATA_DIR / f"{SET_ID}.json"
    out_json.write_text(json.dumps(cards_out, separators=(",", ":")), encoding="utf-8")

    # Use Maushold ex SAR (#158) or Booster Box image as visual logo on set card
    logo_img = ""
    if 158 in base_by_num:
        logo_img = upgrade_pc_image(base_by_num[158].get("imageUri", ""))

    # Update public/data/pokemon-sets.json
    sets_json_path = PROJECT_ROOT / "public" / "data" / "pokemon-sets.json"
    set_metas: list[dict[str, Any]] = json.loads(sets_json_path.read_text(encoding="utf-8"))

    new_meta = {
        "id": COL_ID,
        "setId": SET_ID,
        "name": f"Pokémon TCG · {SET_NAME}",
        "shortName": SHORT_NAME,
        "era": ERA,
        "releaseDate": RELEASE_DATE,
        "cardCount": len(base_by_num),
        "grandMasterCount": len(cards_out),
        "estimatedTotal": round(est_total, 2),
        "logo": logo_img,
        "symbol": "",
        "subtitle": f"Simplified Chinese (嘉奖回合) · 2025 · {len(cards_out)} Master cards",
        "maker": "Pokémon TCG (CN)",
        "accent": "#C83E3B",
        "accentSoft": "#FDECEB",
        "accentText": "#871F1D",
        "emoji": "🧧",
    }

    set_metas = [s for s in set_metas if s["setId"] != SET_ID]
    set_metas.append(new_meta)
    set_metas.sort(key=lambda s: s.get("releaseDate", ""), reverse=True)
    sets_json_path.write_text(json.dumps(set_metas), encoding="utf-8")

    missing_img = sum(1 for c in cards_out if not c["image"])
    print(
        f"Wrote {out_json}: {len(cards_out)} Master Set cards ({len(base_by_num)} base + Poké Ball & Master Ball), "
        f"est. ${est_total:,.2f}, {priced_real} live PriceCharting prices, "
        f"images: {img_from_pc} PriceCharting + {img_from_sv} SV fallback ({missing_img} missing)."
    )


if __name__ == "__main__":
    main()
