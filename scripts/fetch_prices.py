#!/usr/bin/env python3
"""Fetch accurate USD pricing data for all TrinketShelf catalog items and Pokémon TCG cards.

1. Non-Pokémon shelves: reads per-variant prices from public Shopify product feeds
   (toysez.com, arttoyfamilia.com, babycubby.com, pacifierkids.com, faoschwarz.com,
   store.kobeejapan.net), strictly separating Secret, Robby Angel, Lucky, and Regular
   variants, and writes src/data/prices.ts.
2. Pokémon TCG shelf: fetches real TCGplayer Market Prices (via tcgcsv.com) for all
   English sets & Grand Master variants, updating public/data/pokemon/*.json and
   src/data/pokemonSets.ts.

Usage:
  python3 scripts/fetch_prices.py                # Refresh all shelves + Pokémon TCG
  python3 scripts/fetch_prices.py --pokemon-only # Refresh Pokémon TCGplayer prices only
  python3 scripts/fetch_prices.py --skip-pokemon # Refresh non-Pokémon shelves only
"""


from __future__ import annotations

import argparse
import json
import re
import urllib.parse

from common import DATA_DIR, fetch_json
import fetch_pokemon_csv4c
import fetch_pokemon_prices

CATALOG_FILES = [
    DATA_DIR / "catalog.ts",
    DATA_DIR / "sonnyHippers.ts",
    DATA_DIR / "sonnyLimited.ts",
    DATA_DIR / "sonnyArchive.ts",
    DATA_DIR / "sonnyVintage.ts",
    DATA_DIR / "tinytiny.ts",
    DATA_DIR / "skullpanda.ts",
    DATA_DIR / "zsiga.ts",
    DATA_DIR / "sullivanFamily.ts",
    DATA_DIR / "calicoCritters.ts",
    DATA_DIR / "jellycat.ts",
]

ITEM_RE = re.compile(
    r'\{\s*"?id"?:\s*[\'"]([^\'"]+)[\'"],\s*"?collectionId"?:\s*[\'"]([^\'"]+)[\'"],\s*'
    r'"?name"?:\s*[\'"]([^\'"]+)[\'"],\s*"?series"?:\s*[\'"]([^\'"]+)[\'"],\s*'
    r'"?rarity"?:\s*[\'"]([^\'"]+)[\'"]',
    re.S,
)

STOP = {
    "sonny", "angel", "series", "blind", "box", "bag", "mini", "figure", "edition",
    "confirmed", "style", "limited", "the", "of", "in", "and", "with", "plush",
    "toy", "by", "jellycat", "pop", "mart", "sylvanian", "families", "calico", "critters",
    "secret", "hidden", "super",
}

CITY_EXCLUSIVE_PRICES = {
    "jc-city-briggs-beaver": 48.0,
    "jc-city-maple-leaf": 42.0,
    "jc-city-fran-pancakes": 55.0,
    "jc-city-rene-waffle": 55.0,
    "jc-city-strutton-pigeon": 58.0,
    "jc-city-bubbeca-milkshake": 55.0,
    "jc-city-rustic-fries": 45.0,
    "jc-city-mckenna-burger": 50.0,
    "jc-city-crember-cheesecake": 55.0,
    "jc-city-paris-brest": 58.0,
    "jc-city-chouquettes": 55.0,
    "jc-city-raspberry-souffle": 55.0,
    "jc-city-lily-fish": 55.0,
    "jc-city-mushy-peas": 48.0,
    "jc-city-leicester-pigeon": 58.0,
    "jc-city-melbie-peach-cake": 65.0,
    "jc-city-vividdy-teapot": 68.0,
    "jc-city-berrity-latte": 60.0,
    "jc-city-leola-strawberry-cake": 72.0,
}


def toks(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP


def make_entry(label: str, price: float) -> dict:
    ll = label.lower()
    is_robby = "robby" in ll
    is_secret = is_robby or any(
        k in ll for k in ("secret", "hidden", "1/144", "2/144", "1/72", "2/96", "1/96", "1/24")
    )
    is_lucky = "lucky" in ll and "lucky cat" not in ll and "good luck" not in ll
    return {
        "label": label,
        "toks": toks(label),
        "price": round(price, 2),
        "is_secret": is_secret,
        "is_robby": is_robby,
        "is_lucky": is_lucky,
    }


def extract_product_entries(products: list[dict]) -> list[dict]:
    entries: list[dict] = []
    for p in products:
        title = p.get("title", "")
        tl = title.lower()
        if any(skip in tl for skip in ("complete set", "full set", "whole set", "full case", "16 bags", "assorted")):
            continue
        variants = p.get("variants") or []
        if len(variants) == 1:
            try:
                price = float(variants[0].get("price", 0))
                if 2.0 <= price <= 5000.0:
                    entries.append(make_entry(title, price))
            except Exception:
                pass
        else:
            for v in variants:
                vt = v.get("title", "")
                vtl = vt.lower()
                if vtl == "default title" or any(
                    skip in vtl for skip in ("full set", "fullset", "whole set", "confirmed figures", "sealed", "blind box", "single box")
                ):
                    continue
                try:
                    price = float(v.get("price", 0))
                    if 2.0 <= price <= 5000.0:
                        entries.append(make_entry(f"{title} {vt}", price))
                except Exception:
                    pass
    return entries


def fetch_store_prices(base_url: str, max_pages: int = 5) -> list[dict]:
    products: list[dict] = []
    for page in range(1, max_pages + 1):
        try:
            batch = fetch_json(base_url.format(page)).get("products", [])
            if not batch:
                break
            products.extend(batch)
        except Exception:
            break
    return extract_product_entries(products)


def fetch_atf_tinytiny_prices() -> list[dict]:
    products: list[dict] = []
    try:
        sugg = fetch_json(
            "https://arttoyfamilia.com/search/suggest.json?q=tinytiny&resources[type]=product&resources[limit]=25"
        )
        for p in sugg.get("resources", {}).get("results", {}).get("products", []):
            if "tinytiny" not in p.get("title", "").lower():
                continue
            handle = urllib.parse.quote(p["handle"])
            pj = fetch_json(f"https://arttoyfamilia.com/products/{handle}.json")["product"]
            products.append(pj)
    except Exception:
        pass
    return extract_product_entries(products)


def baseline_price(col_id: str, name: str, series: str, rarity: str) -> float:
    nl = name.lower()
    sl = series.lower()

    if col_id.startswith("sonny-"):
        if "robby" in nl:
            return 135.0
        if rarity == "Secret":
            return 115.0
        if rarity == "Lucky":
            return 48.0
        if col_id.startswith("sonny-art-"):
            return 34.0
        if col_id.startswith("sonny-spc-"):
            return 28.0
        if col_id.startswith("sonny-vin-"):
            return 24.0
        if col_id.startswith("sonny-unr-"):
            return 18.0
        if col_id.startswith("sonny-hip-"):
            return 14.5
        if col_id.startswith("sonny-lim-"):
            return 16.0
        return 13.75

    if col_id.startswith("sp-"):
        if rarity == "Secret":
            return 145.0
        if col_id.startswith("sp-plush-"):
            return 27.99
        return 16.99

    if col_id.startswith("tinytiny-"):
        if rarity == "Secret":
            return 135.0
        if col_id == "tinytiny-standalone":
            return 38.0
        return 16.99

    if col_id.startswith("zs-"):
        if rarity == "Secret":
            return 130.0
        if "plush" in sl:
            return 24.99
        if col_id == "zs-standalone":
            return 38.0
        return 16.99

    if col_id.startswith("jc-"):
        if col_id == "jc-bag-charms":
            return 25.0
        if col_id == "jc-dragons":
            return 65.0
        if col_id == "jc-bears":
            return 38.0
        if col_id == "jc-smudge":
            return 35.0
        if col_id in ("jc-bashful-bunnies", "jc-blossom-bunnies"):
            return 30.0
        if col_id == "jc-amuseables":
            return 32.0
        return 34.0

    if col_id.startswith(("cc-", "sf-")):
        if rarity == "Secret":
            return 28.0
        if col_id.startswith("sf-box-") or "friends" in sl:
            return 9.99
        return 6.99

    return 15.0


def match_live_price(pool: list[dict], name: str, series: str, rarity: str) -> float | None:
    is_robby = "robby" in name.lower()
    is_secret = rarity == "Secret"
    is_lucky = rarity == "Lucky"

    nt = toks(name)
    st = toks(series)
    if not nt and not st:
        return None

    best_score = 0.0
    best_price: float | None = None

    for entry in pool:
        # Strict rarity/robby separation so Secrets NEVER match regular-figure prices
        if is_robby != entry["is_robby"]:
            continue
        if is_secret != entry["is_secret"]:
            continue
        if is_lucky != entry["is_lucky"]:
            continue

        ptoks = entry["toks"]
        n_hit = len(nt & ptoks)
        s_hit = len(st & ptoks)
        n_ratio = (n_hit / len(nt)) if nt else 0.0
        s_ratio = (s_hit / len(st)) if st else 0.0

        if is_secret:
            # For secrets/robbys, strong series match is primary (names vary slightly across stores)
            if s_hit == 0 or s_ratio < 0.5:
                continue
            score = s_ratio * 12.0 + s_hit * 2.5 + n_ratio * 8.0 + n_hit * 2.0
            min_thresh = 13.0
        else:
            if n_hit == 0 or n_ratio < 0.6:
                continue
            score = n_ratio * 10.0 + n_hit * 2.0 + s_ratio * 6.0 + s_hit
            min_thresh = 13.5

        if score > best_score:
            best_score = score
            best_price = entry["price"]

    return best_price if best_score >= (13.0 if is_secret else 13.5) else None


def main() -> None:
    print("Fetching live per-variant USD prices from public collector & retail feeds...")
    pools = {
        "sonny": fetch_store_prices("https://toysez.com/collections/sonny-angel/products.json?limit=250&page={}", 5),
        "skullpanda": (
            fetch_store_prices("https://arttoyfamilia.com/collections/skullpanda/products.json?limit=250&page={}", 3)
            + fetch_store_prices("https://toysez.com/collections/skullpanda/products.json?limit=250&page={}", 4)
        ),
        "tinytiny": (
            fetch_atf_tinytiny_prices()
            + fetch_store_prices("https://toysez.com/collections/tinytiny/products.json?limit=250&page={}", 3)
        ),
        "zsiga": (
            fetch_store_prices("https://arttoyfamilia.com/collections/zsiga/products.json?limit=250&page={}", 2)
            + fetch_store_prices("https://toysez.com/collections/zsiga/products.json?limit=250&page={}", 3)
        ),
        "jellycat": (
            fetch_store_prices("https://www.babycubby.com/collections/jellycat/products.json?limit=250&page={}", 3)
            + fetch_store_prices("https://pacifierkids.com/collections/jellycat/products.json?limit=250&page={}", 3)
            + fetch_store_prices("https://faoschwarz.com/collections/jellycat/products.json?limit=250&page={}", 2)
        ),
        "sylvanian": fetch_store_prices("https://store.kobeejapan.net/collections/blind-bag/products.json?limit=250&page={}", 3),
    }
    for k, v in pools.items():
        sec_n = sum(1 for e in v if e["is_secret"])
        print(f"  {k:12s}: {len(v)} variant prices ({sec_n} secret/robby)")

    prices: dict[str, float] = {}
    live_matched = 0
    secret_live = 0
    secret_total = 0
    total = 0

    for path in CATALOG_FILES:
        txt = path.read_text(encoding="utf-8")
        for m in ITEM_RE.finditer(txt):
            iid, col_id, name, series, rarity = m.groups()
            total += 1
            if rarity == "Secret":
                secret_total += 1
            if iid in CITY_EXCLUSIVE_PRICES:
                prices[iid] = CITY_EXCLUSIVE_PRICES[iid]
                continue

            if col_id.startswith("sonny-"):
                pool = pools["sonny"]
            elif col_id.startswith("sp-"):
                pool = pools["skullpanda"]
            elif col_id.startswith("tinytiny-"):
                pool = pools["tinytiny"]
            elif col_id.startswith("zs-"):
                pool = pools["zsiga"]
            elif col_id.startswith("jc-"):
                pool = pools["jellycat"]
            else:
                pool = pools["sylvanian"]

            matched = match_live_price(pool, name, series, rarity)
            if matched is not None:
                prices[iid] = matched
                live_matched += 1
                if rarity == "Secret":
                    secret_live += 1
            else:
                prices[iid] = baseline_price(col_id, name, series, rarity)

    out_ts = DATA_DIR / "prices.ts"
    out_ts.write_text(
        "\n".join([
            "// Estimated USD retail / secondary-market prices per item (generated by scripts/fetch_prices.py)",
            "export const ITEM_PRICES: Record<string, number> = " + json.dumps(prices, indent=2) + ";",
            "",
            "export function getItemPrice(itemId: string, customPrice?: number, fallbackPrice?: number): number {",
            "  if (typeof customPrice === 'number' && !Number.isNaN(customPrice) && customPrice >= 0) {",
            "    return customPrice;",
            "  }",
            "  if (itemId in ITEM_PRICES) {",
            "    return ITEM_PRICES[itemId];",
            "  }",
            "  if (typeof fallbackPrice === 'number' && !Number.isNaN(fallbackPrice) && fallbackPrice >= 0) {",
            "    return fallbackPrice;",
            "  }",
            "  return 15;",
            "}",
            "",
            "export function formatUsd(amount: number): string {",
            "  return amount.toLocaleString('en-US', {",
            "    style: 'currency',",
            "    currency: 'USD',",
            "    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,",
            "    maximumFractionDigits: 2,",
            "  });",
            "}",
            "",
            "export function formatUsdWhole(amount: number): string {",
            "  return Math.round(amount).toLocaleString('en-US', {",
            "    style: 'currency',",
            "    currency: 'USD',",
            "    minimumFractionDigits: 0,",
            "    maximumFractionDigits: 0,",
            "  });",
            "}",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_ts}: {len(prices)} priced items ({live_matched}/{total} live; Secrets live: {secret_live}/{secret_total})")
    # Spot-check a few famous secrets
    for sid in [
        "tinytiny-prologue-perfect-gift",
        "tinytiny-sugar-therapy-sweetness-generator",
        "sp-series-sound-series-the-equilibrium",
        "sonny-fruit-sprout",
        "sonny-snack-robby",
    ]:
        if sid in prices:
            print(f"  sample secret {sid}: ${prices[sid]}")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Fetch USD prices for TrinketShelf catalog and Pokémon TCG.")
    parser.add_argument("--pokemon-only", action="store_true", help="Only refresh Pokémon TCGplayer prices.")
    parser.add_argument("--skip-pokemon", action="store_true", help="Skip Pokémon TCGplayer prices.")
    args = parser.parse_args()

    if not args.pokemon_only:
        main()
    if not args.skip_pokemon:
        print("\n--- Refreshing Pokémon TCGplayer Market Prices ---")
        fetch_pokemon_prices.main()
        print("\n--- Refreshing Simplified Chinese Reward Round (CSV4C) Prices ---")
        fetch_pokemon_csv4c.main()


if __name__ == "__main__":
    cli()
