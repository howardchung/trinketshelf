#!/usr/bin/env python3
"""Fetch real TCGplayer market prices for all English Pokémon TCG sets via TCGCSV.

Updates:
  - public/data/pokemon/<setId>.json  (exact TCGplayer Market Price per card & variant)
  - src/data/pokemonSets.ts           (recalculated estimatedTotal per set from real TCGplayer prices)

Source: https://tcgcsv.com/tcgplayer/3/ (public daily mirror of TCGplayer Pokémon prices).
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT

POKEMON_DATA_DIR = PROJECT_ROOT / "public" / "data" / "pokemon"
BASE_URL = "https://tcgcsv.com/tcgplayer/3"
UA = "TrinketShelf/1.0 (https://github.com/howardc)"

# Explicit overrides where PokemonTCG set IDs map to non-obvious TCGplayer group names
EXACT_GROUP_OVERRIDES: dict[str, list[str]] = {
    "base1": ["Base Set"],
    "base2": ["Jungle"],
    "base3": ["Fossil"],
    "base4": ["Base Set 2"],
    "base5": ["Team Rocket"],
    "base6": ["Legendary Collection"],
    "basep": ["WoTC Promo"],
    "gym1": ["Gym Heroes"],
    "gym2": ["Gym Challenge"],
    "neo1": ["Neo Genesis"],
    "neo2": ["Neo Discovery"],
    "neo3": ["Neo Revelation"],
    "neo4": ["Neo Destiny"],
    "si1": ["Southern Islands"],
    "ecard1": ["Expedition"],
    "ecard2": ["Aquapolis"],
    "ecard3": ["Skyridge"],
    "ex1": ["Ruby and Sapphire", "EX Ruby & Sapphire"],
    "ex2": ["Sandstorm", "EX Sandstorm"],
    "ex3": ["EX Dragon", "Dragon"],
    "ex4": ["Team Magma vs Team Aqua", "EX Team Magma vs Team Aqua"],
    "ex5": ["Hidden Legends", "EX Hidden Legends"],
    "ex6": ["FireRed & LeafGreen", "EX FireRed & LeafGreen"],
    "ex7": ["Team Rocket Returns", "EX Team Rocket Returns"],
    "ex8": ["EX Deoxys", "Deoxys"],
    "ex9": ["EX Emerald", "Emerald"],
    "ex10": ["EX Unseen Forces", "Unseen Forces"],
    "ex11": ["EX Delta Species", "Delta Species"],
    "ex12": ["EX Legend Maker", "Legend Maker"],
    "ex13": ["EX Holon Phantoms", "Holon Phantoms"],
    "ex14": ["EX Crystal Guardians", "Crystal Guardians"],
    "ex15": ["EX Dragon Frontiers", "Dragon Frontiers"],
    "ex16": ["EX Power Keepers", "Power Keepers"],
    "tk1a": ["EX Trainer Kit 1: Latias & Latios"],
    "tk1b": ["EX Trainer Kit 1: Latias & Latios"],
    "tk2a": ["EX Trainer Kit 2: Plusle & Minun"],
    "tk2b": ["EX Trainer Kit 2: Plusle & Minun"],
    "ru1": ["Rumble"],
    "mcd21": ["McDonald's 25th Anniversary Promos"],
    "np": ["Nintendo Promos"],
    "dp1": ["Diamond and Pearl"],
    "dp2": ["Mysterious Treasures"],
    "dp3": ["Secret Wonders"],
    "dp4": ["Great Encounters"],
    "dp5": ["Majestic Dawn"],
    "dp6": ["Legends Awakened"],
    "dp7": ["Stormfront"],
    "dpp": ["Diamond and Pearl Promos"],
    "pl1": ["Platinum"],
    "pl2": ["Rising Rivals"],
    "pl3": ["Supreme Victors"],
    "pl4": ["Arceus"],
    "hgss1": ["HeartGold SoulSilver"],
    "hgss2": ["Unleashed"],
    "hgss3": ["Undaunted"],
    "hgss4": ["Triumphant"],
    "hsp": ["HGSS Promos"],
    "col1": ["Call of Legends"],
    "bw1": ["Black and White"],
    "bw2": ["Emerging Powers"],
    "bw3": ["Noble Victories"],
    "bw4": ["Next Destinies"],
    "bw5": ["Dark Explorers"],
    "bw6": ["Dragons Exalted"],
    "bw7": ["Boundaries Crossed"],
    "bw8": ["Plasma Storm"],
    "bw9": ["Plasma Freeze"],
    "bw10": ["Plasma Blast"],
    "bw11": ["Legendary Treasures"],
    "bwp": ["Black and White Promos"],
    "dv1": ["Dragon Vault"],
    "xy0": ["XY - Kalos Starter Set"],
    "xy1": ["XY Base Set"],
    "xy2": ["XY - Flashfire"],
    "xy3": ["XY - Furious Fists"],
    "xy4": ["XY - Phantom Forces"],
    "xy5": ["XY - Primal Clash"],
    "xy6": ["XY - Roaring Skies"],
    "xy7": ["XY - Ancient Origins"],
    "xy8": ["XY - BREAKthrough"],
    "xy9": ["XY - BREAKpoint"],
    "xy10": ["XY - Fates Collide"],
    "xy11": ["XY - Steam Siege"],
    "xy12": ["XY - Evolutions"],
    "xyp": ["XY Promos"],
    "dc1": ["Double Crisis"],
    "g1": ["Generations"],
    "sm1": ["SM Base Set"],
    "sm2": ["SM - Guardians Rising"],
    "sm3": ["SM - Burning Shadows"],
    "sm35": ["Shining Legends"],
    "sm4": ["SM - Crimson Invasion"],
    "sm5": ["SM - Ultra Prism"],
    "sm6": ["SM - Forbidden Light"],
    "sm7": ["SM - Celestial Storm"],
    "sm75": ["Dragon Majesty"],
    "sm8": ["SM - Lost Thunder"],
    "sm9": ["SM - Team Up"],
    "sm10": ["SM - Unbroken Bonds"],
    "sm11": ["SM - Unified Minds"],
    "sm115": ["Hidden Fates"],
    "sm12": ["SM - Cosmic Eclipse"],
    "smp": ["SM Promos"],
    "det1": ["Detective Pikachu"],
    "sma": ["Hidden Fates: Shiny Vault"],
    "swsh1": ["SWSH01: Sword & Shield Base Set"],
    "swsh2": ["SWSH02: Rebel Clash"],
    "swsh3": ["SWSH03: Darkness Ablaze"],
    "swsh35": ["Champion's Path"],
    "swsh4": ["SWSH04: Vivid Voltage"],
    "swsh45": ["Shining Fates"],
    "swsh45sv": ["Shining Fates: Shiny Vault"],
    "swsh5": ["SWSH05: Battle Styles"],
    "swsh6": ["SWSH06: Chilling Reign"],
    "swsh7": ["SWSH07: Evolving Skies"],
    "swsh8": ["SWSH08: Fusion Strike"],
    "swsh9": ["SWSH09: Brilliant Stars"],
    "swsh9tg": ["SWSH09: Brilliant Stars Trainer Gallery"],
    "swsh10": ["SWSH10: Astral Radiance"],
    "swsh10tg": ["SWSH10: Astral Radiance Trainer Gallery"],
    "swsh11": ["SWSH11: Lost Origin"],
    "swsh11tg": ["SWSH11: Lost Origin Trainer Gallery"],
    "swsh12": ["SWSH12: Silver Tempest"],
    "swsh12tg": ["SWSH12: Silver Tempest Trainer Gallery"],
    "swsh12pt5": ["Crown Zenith"],
    "swsh12pt5gg": ["Crown Zenith: Galarian Gallery"],
    "swshp": ["SWSH: Sword & Shield Promo Cards"],
    "cel25": ["Celebrations"],
    "cel25c": ["Celebrations: Classic Collection"],
    "pgo": ["Pokemon GO"],
    "sv1": ["SV01: Scarlet & Violet Base Set"],
    "sv2": ["SV02: Paldea Evolved"],
    "sv3": ["SV03: Obsidian Flames"],
    "sv3pt5": ["SV: Scarlet & Violet 151"],
    "sv4": ["SV04: Paradox Rift"],
    "sv4pt5": ["SV: Paldean Fates"],
    "sv5": ["SV05: Temporal Forces"],
    "sv6": ["SV06: Twilight Masquerade"],
    "sv6pt5": ["SV: Shrouded Fable"],
    "sv7": ["SV07: Stellar Crown"],
    "sv8": ["SV08: Surging Sparks"],
    "sv8pt5": ["SV: Prismatic Evolutions"],
    "sv9": ["SV09: Journey Together"],
    "sv10": ["SV10: Destined Rivals"],
    "svp": ["SV: Scarlet & Violet Promo Cards"],
    "zsv10pt5": ["SV: Black Bolt"],
    "rsv10pt5": ["SV: White Flare"],
    "me1": ["ME01: Mega Evolution"],
    "me2": ["ME02: Phantasmal Flames"],
    "me2pt5": ["ME: Ascended Heroes"],
    "me3": ["ME03: Perfect Order"],
    "me4": ["ME04: Chaos Rising"],
    "me5": ["ME05: Emerald Storm"],
    "me6": ["ME06: Delta Reign"],
    "mep": ["ME: Mega Evolution Promo"],
    "fut20": ["Pokemon Futsal Promos"],
}


def fetch_json(url: str, retries: int = 3) -> Any:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))
    return None


def norm_text(s: str) -> str:
    s = s.lower().replace("é", "e").replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def norm_card_num(raw: str) -> str:
    """Normalize card numbers like '001/102', '1/102', 'TG01/TG30', 'SWSH001' -> '1', 'tg1', 'swsh1'."""
    s = (raw or "").strip().split("/")[0].strip().lower()
    m = re.match(r"^([a-z]*)0*(\d+)([a-z]*)$", s)
    if m:
        return f"{m.group(1)}{int(m.group(2))}{m.group(3)}"
    return re.sub(r"[^a-z0-9]", "", s)


def best_price(pr: dict[str, Any]) -> float | None:
    for key in ("marketPrice", "midPrice", "lowPrice"):
        v = pr.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return round(float(v), 2)
    return None


def pick_group_for_set(
    set_meta: dict[str, Any],
    groups_by_norm: dict[str, dict[str, Any]],
    all_groups: list[dict[str, Any]],
) -> dict[str, Any] | None:
    sid = set_meta["setId"]
    # 1. Explicit override
    for candidate in EXACT_GROUP_OVERRIDES.get(sid, []):
        g = groups_by_norm.get(norm_text(candidate))
        if g:
            return g

    # 2. Exact normalized shortName match
    sn = norm_text(set_meta["shortName"])
    if sn in groups_by_norm:
        return groups_by_norm[sn]

    # 3. Strip prefix like "SV01: ", "SWSH02: ", "XY - ", "SM - ", "ME01: " from group names
    for g in all_groups:
        gname = g["name"]
        stripped = re.sub(r"^(?:SV\d*|SWSH\d*|ME\d*|XY|SM)\s*[:\-]\s*", "", gname, flags=re.I)
        if norm_text(stripped) == sn:
            return g

    # 4. McDonald's Collection matching by year
    if "mcdonald" in sn:
        year = set_meta["releaseDate"][:4]
        for g in all_groups:
            gn = norm_text(g["name"])
            if "mcdonald" in gn and year and year in gn:
                return g

    # 5. POP Series matching
    m_pop = re.match(r"pop series (\d+)", sn)
    if m_pop:
        num = m_pop.group(1)
        for g in all_groups:
            if norm_text(g["name"]) == f"pop series {num}":
                return g

    # 6. Token overlap fallback (strict)
    sn_tokens = set(sn.split())
    if len(sn_tokens) >= 2:
        best_g = None
        best_score = 0.0
        for g in all_groups:
            gt = set(norm_text(g["name"]).split())
            if not gt:
                continue
            inter = len(sn_tokens & gt)
            score = inter / max(len(sn_tokens), len(gt))
            if score > best_score and score >= 0.72:
                best_score = score
                best_g = g
        if best_g:
            return best_g

    return None


def fetch_group_bundle(group_id: int) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    prods = fetch_json(f"{BASE_URL}/{group_id}/products")["results"]
    prices = fetch_json(f"{BASE_URL}/{group_id}/prices")["results"]
    return group_id, prods, prices


def build_group_price_index(
    prods: list[dict[str, Any]], prices: list[dict[str, Any]]
) -> dict[str, dict[str, float]]:
    """Build lookup: key -> {subtype_bucket: market_price}.

    Keys include:
      - 'num:<norm_num>' for regular card products
      - 'mb:<norm_num>' for Master Ball Pattern products
      - 'name:<norm_name>' fallback for cards without standard numbers
    """
    prices_by_pid: dict[int, list[dict[str, Any]]] = {}
    for pr in prices:
        prices_by_pid.setdefault(pr["productId"], []).append(pr)

    index: dict[str, dict[str, float]] = {}

    for p in prods:
        pid = p["productId"]
        p_prices = prices_by_pid.get(pid)
        if not p_prices:
            continue

        ext = {ed.get("name"): ed.get("value") for ed in p.get("extendedData", [])}
        raw_num = ext.get("Number")
        if not raw_num:
            continue  # Skip sealed booster boxes, packs, ETBs, tins

        pname = p.get("name", "")
        pname_l = pname.lower()
        # Skip non-standard promo/stamped variants when indexing base cards
        is_master_ball = "master ball" in pname_l
        is_poke_ball = "poke ball" in pname_l or "pokeball" in pname_l
        is_special_stamp = any(
            k in pname_l
            for k in ("staff", "prerelease", "league", "cosmos", "cracked ice", "build & battle", "stamped", "prize pack", "world championship")
        )
        if is_poke_ball or is_special_stamp:
            continue

        n_num = norm_card_num(str(raw_num))
        n_name = norm_text(re.sub(r"\([^)]*\)", "", pname))

        subtype_map: dict[str, float] = {}
        for pr in p_prices:
            val = best_price(pr)
            if val is None:
                continue
            st = (pr.get("subTypeName") or "Normal").lower()
            if "1st edition" in st:
                # Prefer holofoil if both exist, otherwise keep higher/first
                if "holo" in st or "1st" not in subtype_map:
                    subtype_map["1st"] = val
            elif "reverse" in st:
                subtype_map["rev"] = val
            elif "holofoil" in st:
                # Unlimited Holofoil or Holofoil
                if "unlimited" in st or "holo" not in subtype_map:
                    subtype_map["holo"] = val
            else:
                if "unlimited" in st or "normal" not in subtype_map:
                    subtype_map["normal"] = val

        if not subtype_map:
            continue

        if is_master_ball:
            mb_val = subtype_map.get("holo") or subtype_map.get("rev") or subtype_map.get("normal")
            if mb_val is not None:
                index.setdefault(f"mb:{n_num}", {})["mb"] = mb_val
                index.setdefault(f"mbname:{n_name}", {})["mb"] = mb_val
        else:
            # Merge into regular card index (don't overwrite with weaker data)
            slot = index.setdefault(f"num:{n_num}", {})
            for k, v in subtype_map.items():
                slot.setdefault(k, v)
            nslot = index.setdefault(f"name:{n_name}", {})
            for k, v in subtype_map.items():
                nslot.setdefault(k, v)

    return index


def main() -> None:
    sets_json_path = PROJECT_ROOT / "public" / "data" / "pokemon-sets.json"
    set_metas: list[dict[str, Any]] = json.loads(sets_json_path.read_text(encoding="utf-8"))

    print("Fetching TCGplayer Pokémon groups from tcgcsv.com...")
    all_groups = fetch_json(f"{BASE_URL}/groups")["results"]
    groups_by_norm = {norm_text(g["name"]): g for g in all_groups}
    print(f"Found {len(all_groups)} TCGplayer Pokémon groups.")

    # Map our 177 sets -> TCGplayer groupId
    set_to_gid: dict[str, int] = {}
    unmatched_sets: list[str] = []
    for sm in set_metas:
        g = pick_group_for_set(sm, groups_by_norm, all_groups)
        if g:
            set_to_gid[sm["setId"]] = g["groupId"]
        else:
            unmatched_sets.append(f"{sm['setId']} ({sm['shortName']})")

    # Also fetch Base Set (Shadowless) groupId 1663 for Base Set 1st Edition prices
    shadowless_g = groups_by_norm.get(norm_text("Base Set (Shadowless)"))
    shadowless_gid = shadowless_g["groupId"] if shadowless_g else None

    unique_gids = set(set_to_gid.values())
    if shadowless_gid:
        unique_gids.add(shadowless_gid)

    print(
        f"Matched {len(set_to_gid)}/{len(set_metas)} sets to {len(unique_gids)} TCGplayer groups. "
        f"Unmatched: {len(unmatched_sets)}"
    )
    if unmatched_sets:
        print("  Unmatched sets:", ", ".join(unmatched_sets[:15]))

    # Concurrently fetch products + prices for all matched groups
    group_indices: dict[int, dict[str, dict[str, float]]] = {}
    failed_gids: list[int] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(fetch_group_bundle, gid): gid for gid in sorted(unique_gids)}
        done = 0
        for fut in as_completed(futs):
            gid = futs[fut]
            try:
                _, prods, prices = fut.result()
                group_indices[gid] = build_group_price_index(prods, prices)
            except Exception as exc:
                failed_gids.append(gid)
                print(f"  WARN: group {gid} failed: {exc}")
            done += 1
            if done % 30 == 0 or done == len(unique_gids):
                print(f"  Fetched {done}/{len(unique_gids)} groups...")

    shadowless_index = group_indices.get(shadowless_gid, {}) if shadowless_gid else {}

    total_cards = 0
    matched_cards = 0
    total_gm_cards = 0

    for sm in set_metas:
        sid = sm["setId"]
        json_path = POKEMON_DATA_DIR / f"{sid}.json"
        if not json_path.is_file():
            continue
        cards: list[dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
        gid = set_to_gid.get(sid)
        gidx = group_indices.get(gid, {}) if gid else {}

        set_total = 0.0
        for card in cards:
            total_cards += 1
            cid = card["id"]
            cname = card["name"]
            # Extract card number from "#001 Alakazam (1st Ed.)"
            m_num = re.match(r"^#([^\s]+)\s+(.*)$", cname)
            raw_num = m_num.group(1) if m_num else ""
            clean_name = re.sub(r"\s*\((?:1st Ed\.|Reverse Holo|Master Ball)\)\s*$", "", m_num.group(2) if m_num else cname)
            n_num = norm_card_num(raw_num)
            n_name = norm_text(clean_name)

            new_price: float | None = None

            if cid.endswith("-mb"):
                slot = gidx.get(f"mb:{n_num}") or gidx.get(f"mbname:{n_name}")
                if slot:
                    new_price = slot.get("mb")
            elif cid.endswith("-1ed"):
                # Base Set 1st Edition lives in Base Set (Shadowless) group
                src_idx = shadowless_index if sid == "base1" else gidx
                slot = src_idx.get(f"num:{n_num}") or src_idx.get(f"name:{n_name}")
                if slot:
                    new_price = slot.get("1st")
            elif cid.endswith("-rev"):
                slot = gidx.get(f"num:{n_num}") or gidx.get(f"name:{n_name}")
                if slot:
                    new_price = slot.get("rev")
            else:
                slot = gidx.get(f"num:{n_num}") or gidx.get(f"name:{n_name}")
                if slot:
                    # Prefer holo for Holo/EX/GX/V/Ultra/Secret cards, else normal -> holo
                    series_l = card.get("series", "").lower()
                    wants_holo = any(
                        k in series_l
                        for k in ("holo", "secret", "ultra", "illustration", "hyper", "double rare", "ace spec", "vmax", "vstar", "gx", "ex", "radiant", "shining", "shiny", "rainbow", "prime", "legend")
                    )
                    if wants_holo:
                        new_price = slot.get("holo") or slot.get("normal") or slot.get("rev")
                    else:
                        new_price = slot.get("normal") or slot.get("holo") or slot.get("rev")

            if new_price is not None and new_price > 0:
                card["price"] = round(new_price, 2)
                matched_cards += 1

            set_total += float(card.get("price") or 0)

        json_path.write_text(json.dumps(cards, separators=(",", ":")), encoding="utf-8")
        sm["estimatedTotal"] = round(set_total, 2)
        total_gm_cards += len(cards)

    # Write updated public/data/pokemon-sets.json
    sets_json_path.write_text(json.dumps(set_metas), encoding="utf-8")

    pct = (matched_cards / total_cards * 100) if total_cards else 0
    print(
        f"Done! Updated {matched_cards:,}/{total_cards:,} cards ({pct:.1f}%) with real TCGplayer market prices."
    )


if __name__ == "__main__":
    main()
