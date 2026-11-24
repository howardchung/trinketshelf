#!/usr/bin/env python3
"""Fetch all English Pokémon TCG sets & Grand Master card lists from PokemonTCG/pokemon-tcg-data.

Generates:
  - src/data/pokemonSets.ts         (lightweight metadata for all English sets, grouped by era)
  - public/data/pokemon/<id>.json   (lazy-loaded per-set Grand Master card lists with prices & image URLs)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from common import DATA_DIR, PROJECT_ROOT

POKEMON_DATA_DIR = PROJECT_ROOT / "public" / "data" / "pokemon"

ERA_COLORS = {
    "Mega Evolution": ("#D94862", "#FDECEF", "#8F2237", "⚡"),
    "Scarlet & Violet": ("#C84B5A", "#FDECEF", "#872633", "✨"),
    "Sword & Shield": ("#4A7EC7", "#EBF2FC", "#244B85", "⚔️"),
    "Sun & Moon": ("#E08A3C", "#FDF3E7", "#945214", "☀️"),
    "XY": ("#5B6BC0", "#ECEEFB", "#313E85", "💎"),
    "Black & White": ("#4D5566", "#EEF0F4", "#272C36", "☯️"),
    "HeartGold & SoulSilver": ("#C99A3B", "#FCF6E6", "#825E16", "💛"),
    "Platinum": ("#6D8399", "#EFF3F7", "#3A4E61", "🪙"),
    "Diamond & Pearl": ("#5A8FB8", "#ECF4F8", "#2B5B7D", "💠"),
    "EX": ("#B85C4A", "#FBF0ED", "#7A3224", "🔥"),
    "E-Card": ("#5C9E62", "#ECF6ED", "#2F6634", "🃏"),
    "Neo": ("#7C65B8", "#F1EEFA", "#4D3885", "🌙"),
    "Gym": ("#C97B63", "#FAF0EC", "#874532", "🏟️"),
    "Base": ("#D4A034", "#FDF7E6", "#876110", "👑"),
    "POP": ("#4F94A8", "#EAF5F8", "#2A6070", "🎁"),
    "NP": ("#6B8E78", "#EEF5F0", "#355440", "⭐"),
    "Other": ("#7A7485", "#F2F1F5", "#474252", "🎴"),
}

WOTC_FIRST_ED_SETS = {
    "base1", "base2", "base3", "base5", "gym1", "gym2", "neo1", "neo2", "neo3", "neo4"
}

REVERSE_HOLO_ERAS = {
    "Mega Evolution", "Scarlet & Violet", "Sword & Shield", "Sun & Moon",
    "XY", "Black & White", "HeartGold & SoulSilver", "Platinum",
    "Diamond & Pearl", "EX", "E-Card",
}

REVERSE_ELIGIBLE_RARITIES = {
    "Common", "Uncommon", "Rare", "Rare Holo",
}


def map_app_rarity(tcg_rarity: str, card_num: str, printed_total: int) -> str:
    r = (tcg_rarity or "").lower()
    if any(
        k in r
        for k in (
            "secret",
            "special illustration",
            "hyper rare",
            "rainbow",
            "gold",
            "shiny rare",
            "amazing rare",
            "mega hyper",
        )
    ):
        return "Secret"
    if card_num.isdigit() and printed_total > 0 and int(card_num) > printed_total:
        return "Secret"
    if any(
        k in r
        for k in (
            "illustration",
            "ultra rare",
            "double rare",
            "ace spec",
            "holo",
            "vmax",
            "vstar",
            "gx",
            "ex",
            "v",
            "radiant",
            "promo",
            "trainer gallery",
            "shining",
            "prism",
            "break",
            "legend",
            "prime",
        )
    ):
        return "Special"
    return "Regular"


def estimate_card_price(tcg_rarity: str, era: str, variant_kind: str, card_num: str, printed_total: int) -> float:
    r = (tcg_rarity or "").lower()
    is_vintage = era in ("Base", "Gym", "Neo", "E-Card")
    is_mid = era in ("EX", "Diamond & Pearl", "Platinum", "HeartGold & SoulSilver", "Black & White")

    if "special illustration" in r or "mega hyper" in r:
        base = 55.0
    elif "hyper rare" in r or "rainbow" in r or "secret" in r:
        base = 28.0
    elif "illustration rare" in r:
        base = 12.0
    elif "ultra rare" in r or "ace spec" in r or "vmax" in r or "vstar" in r or "gx" in r:
        base = 7.5
    elif "double rare" in r or r.endswith(" ex") or r == "rare holo v":
        base = 2.5
    elif "holo" in r or "shining" in r or "prime" in r or "legend" in r:
        base = 18.0 if is_vintage else (8.0 if is_mid else 0.75)
    elif "promo" in r:
        base = 4.0
    elif "rare" in r:
        base = 3.5 if is_vintage else (1.5 if is_mid else 0.45)
    elif "uncommon" in r:
        base = 1.0 if is_vintage else 0.2
    else:
        base = 0.5 if is_vintage else 0.12

    if card_num.isdigit() and printed_total > 0 and int(card_num) > printed_total and base < 15.0:
        base = 22.0

    if variant_kind == "1st Edition":
        return round(base * 3.5, 2)
    if variant_kind == "Reverse Holo":
        return round(max(0.35, base * 1.6), 2)
    if variant_kind == "Master Ball":
        return round(max(12.0, base * 25.0), 2)
    return round(base, 2)


def main() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="pkmn_tcg_"))
    try:
        print("Cloning PokemonTCG/pokemon-tcg-data (shallow)...")
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/PokemonTCG/pokemon-tcg-data.git", str(tmp_dir)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        sets_raw = json.loads((tmp_dir / "sets" / "en.json").read_text(encoding="utf-8"))
        # Sort newest first so modern sets appear at the top
        sets_raw.sort(key=lambda s: s.get("releaseDate", ""), reverse=True)

        if POKEMON_DATA_DIR.exists():
            shutil.rmtree(POKEMON_DATA_DIR)
        POKEMON_DATA_DIR.mkdir(parents=True, exist_ok=True)

        set_metas = []
        total_gm_cards = 0

        for s in sets_raw:
            sid = s["id"]
            cards_file = tmp_dir / "cards" / "en" / f"{sid}.json"
            if not cards_file.is_file():
                continue
            cards_raw = json.loads(cards_file.read_text(encoding="utf-8"))
            if not cards_raw:
                continue

            era = s.get("series", "Other")
            set_name = s.get("name", sid)
            printed_total = int(s.get("printedTotal") or s.get("total") or len(cards_raw))
            release_date = s.get("releaseDate", "")
            accent, accent_soft, accent_text, emoji = ERA_COLORS.get(era, ERA_COLORS["Other"])
            col_id = f"pkmn-{sid}"

            has_first_ed = sid in WOTC_FIRST_ED_SETS
            has_rev_holo = era in REVERSE_HOLO_ERAS and "promo" not in set_name.lower() and "gallery" not in set_name.lower()
            has_master_ball = sid == "sv8pt5"  # Prismatic Evolutions Master Ball pattern

            gm_cards = []
            set_est_total = 0.0

            for c in cards_raw:
                cid = c["id"]
                num = str(c.get("number", ""))
                cname = c.get("name", cid)
                tcg_rarity = c.get("rarity", "Common")
                app_rarity = map_app_rarity(tcg_rarity, num, printed_total)
                imgs = c.get("images") or {}
                img_url = imgs.get("small") or imgs.get("large") or ""
                if not img_url:
                    continue

                display_num = f"#{num.zfill(3)}" if num.isdigit() else f"#{num}"
                series_lbl = f"{set_name} · {tcg_rarity}"

                # Base / Unlimited card
                base_price = estimate_card_price(tcg_rarity, era, "Standard", num, printed_total)
                gm_cards.append({
                    "id": f"pkmn-{cid}",
                    "collectionId": col_id,
                    "name": f"{display_num} {cname}",
                    "series": series_lbl,
                    "rarity": app_rarity,
                    "image": img_url,
                    "price": base_price,
                })
                set_est_total += base_price

                # Grand Master finish variants
                if has_first_ed:
                    p1 = estimate_card_price(tcg_rarity, era, "1st Edition", num, printed_total)
                    gm_cards.append({
                        "id": f"pkmn-{cid}-1ed",
                        "collectionId": col_id,
                        "name": f"{display_num} {cname} (1st Ed.)",
                        "series": f"{set_name} · 1st Edition",
                        "rarity": "Secret" if app_rarity == "Secret" else "Special",
                        "image": img_url,
                        "price": p1,
                    })
                    set_est_total += p1
                elif has_rev_holo and tcg_rarity in REVERSE_ELIGIBLE_RARITIES:
                    pr = estimate_card_price(tcg_rarity, era, "Reverse Holo", num, printed_total)
                    gm_cards.append({
                        "id": f"pkmn-{cid}-rev",
                        "collectionId": col_id,
                        "name": f"{display_num} {cname} (Reverse Holo)",
                        "series": f"{set_name} · Reverse Holo",
                        "rarity": "Regular",
                        "image": img_url,
                        "price": pr,
                    })
                    set_est_total += pr
                    if has_master_ball:
                        pmb = estimate_card_price(tcg_rarity, era, "Master Ball", num, printed_total)
                        gm_cards.append({
                            "id": f"pkmn-{cid}-mb",
                            "collectionId": col_id,
                            "name": f"{display_num} {cname} (Master Ball)",
                            "series": f"{set_name} · Master Ball Reverse",
                            "rarity": "Special",
                            "image": img_url,
                            "price": pmb,
                        })
                        set_est_total += pmb

            (POKEMON_DATA_DIR / f"{sid}.json").write_text(
                json.dumps(gm_cards, separators=(",", ":")),
                encoding="utf-8",
            )
            total_gm_cards += len(gm_cards)

            logo = (s.get("images") or {}).get("logo") or ""
            symbol = (s.get("images") or {}).get("symbol") or ""
            set_metas.append({
                "id": col_id,
                "setId": sid,
                "name": f"Pokémon TCG · {set_name}",
                "shortName": set_name,
                "era": era,
                "releaseDate": release_date,
                "cardCount": len(cards_raw),
                "grandMasterCount": len(gm_cards),
                "estimatedTotal": round(set_est_total, 2),
                "logo": logo,
                "symbol": symbol,
                "subtitle": f"{era} · {release_date[:4]} · {len(gm_cards)} GM cards",
                "maker": "Pokémon TCG",
                "accent": accent,
                "accentSoft": accent_soft,
                "accentText": accent_text,
                "emoji": emoji,
            })

        out_ts = DATA_DIR / "pokemonSets.ts"
        out_ts.write_text(
            "\n".join([
                "import type { CollectionId } from '../types';",
                "",
                "export interface PokemonSetMeta {",
                "  id: CollectionId;",
                "  setId: string;",
                "  name: string;",
                "  shortName: string;",
                "  era: string;",
                "  releaseDate: string;",
                "  cardCount: number;",
                "  grandMasterCount: number;",
                "  estimatedTotal: number;",
                "  logo: string;",
                "  symbol: string;",
                "  subtitle: string;",
                "  maker: string;",
                "  accent: string;",
                "  accentSoft: string;",
                "  accentText: string;",
                "  emoji: string;",
                "}",
                "",
                "export const POKEMON_SETS: PokemonSetMeta[] = " + json.dumps(set_metas, indent=2) + ";",
                "",
                f"export const POKEMON_TOTAL_GM_CARDS = {total_gm_cards};",
                "",
            ]),
            encoding="utf-8",
        )
        print(f"Generated {len(set_metas)} English Pokémon TCG sets with {total_gm_cards:,} Grand Master cards!")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
