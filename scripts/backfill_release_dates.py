#!/usr/bin/env python3
"""Backfill structured releaseDate (YYYY or YYYY-MM-DD) onto all CollectionMeta sets.

Sources:
  - Sonny Angel: explicit years in titles/subtitles + official Dreams Inc. release years
    + Toysez product created_at dates for recent 2024-2026 Limited editions.
  - Skullpanda, Zsiga, Tinytiny: Art Toy Familia product created_at dates (YYYY-MM-DD).
  - Sylvanian Families: official Epoch / Sylvanian Families Wiki release years for all 43 sets.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"

YEAR_RE = re.compile(r"\b((?:19|20)\d\d)\b")

SONNY_KNOWN_YEARS: dict[str, str] = {
    # Regular (Refined 2018+)
    "sonny-animal-1": "2018",
    "sonny-animal-2": "2018",
    "sonny-animal-3": "2018",
    "sonny-animal-4": "2018",
    "sonny-sweets": "2018",
    "sonny-fruit": "2018",
    "sonny-vegetable": "2018",
    "sonny-marine": "2018",
    "sonny-flower": "2018",
    "sonny-birthday-gift": "2018",
    "sonny-birthday-bear": "2021",
    "sonny-flower-gift": "2022",
    "sonny-gift-wrapped": "2020",
    # Hippers
    "sonny-hip-animal": "2021",
    "sonny-hip-harvest": "2022",
    "sonny-hip-dreaming": "2023",
    "sonny-hip-looking-back": "2024",
    "sonny-hip-cherry-blossom": "2025",
    # Recent Limited without year in title
    "sonny-lim-cat-christmas-series": "2026-11",
    "sonny-lim-summer-vacation-series-sun-kissed-style": "2026-06",
    "sonny-lim-strawberry-love-series": "2026-02",
    "sonny-lim-cherry-blossom-series-hanami-edition": "2025-03",
    "sonny-lim-cherry-blossom-series": "2019-03",
    "sonny-lim-santas-little-helper-series": "2025-11",
    "sonny-lim-pumpkin-patch-series": "2025-10",
    "sonny-lim-snack-series": "2025-07",
    "sonny-lim-rainy-day-series": "2025-05",
    "sonny-lim-kiss-kiss-series": "2025-01",
    "sonny-lim-dog-time-series": "2024-09",
    "sonny-lim-dinosaur-series": "2024-07",
    "sonny-lim-candy-store-series": "2023-11",
    "sonny-lim-cat-life-series": "2023-06",
    "sonny-lim-home-sweet-home-series": "2024-03",
    "sonny-lim-gol-series": "2024-01",
    "sonny-lim-gifts-of-love-series": "2024-01",
    "sonny-lim-winter-wonderland-series": "2023-11",
    "sonny-lim-bugs-world-series": "2022-05",
    "sonny-lim-creatures-series": "2022-09",
    "sonny-lim-enjoy-the-moment-series": "2022-07",
    "sonny-lim-space-adventure-series": "2020-07",
    "sonny-lim-wonderland-series": "2020-09",
    "sonny-lim-cactus-series": "2020-05",
    "sonny-lim-circus-series": "2019-10",
    "sonny-lim-seoul-series": "2021",
    "sonny-lim-new-york-series": "2019",
    "sonny-lim-jeju-series": "2020",
    "sonny-lim-okinawa-series": "2020",
    "sonny-lim-sky-color-series": "2017",
    # Additional Regular, Limited, Artist & Special sets
    "sonny-snack": "2025-07",
    "sonny-lim-santa-s-little-helper-series": "2025-11",
    "sonny-lim-i-love-rainy-day-series": "2025-05",
    "sonny-lim-15th-anniversary-cake": "2019",
    "sonny-lim-new-year-card": "2016",
    "sonny-lim-ladur-e-p-tisserie-collection": "2014",
    "sonny-lim-animal-series-ver-3-special-color": "2011",
    # Artist Collection
    "sonny-art-keme-life-everything-have-souls": "2021",
    "sonny-art-jimmy-liao-a-garden-in-my-heart": "2020",
    "sonny-art-angel-in-the-bird-garden": "2020",
    "sonny-art-collaboration-with-cai": "2019",
    "sonny-art-painted-by-robby": "2019",
    "sonny-art-my-sweet-honey": "2018",
    "sonny-art-joyful-garden": "2017",
    "sonny-art-halloween-pumpkin": "2017",
    "sonny-art-lucky-galo": "2017",
    "sonny-art-nippon-asagao": "2016",
    "sonny-art-my-happy-snack": "2015",
    "sonny-art-halloween-night": "2015",
    "sonny-art-tropical-marine": "2015",
    "sonny-art-happiness-snow": "2014",
    "sonny-art-marguerite": "2014",
    "sonny-art-birthday-ribbon": "2014",
    "sonny-art-heart-chocolate": "2014",
    "sonny-art-kiss-mark-leopard": "2013",
    # Special
    "sonny-spc-plush-collection-cuddly-rabbit": "2024",
    "sonny-spc-it-s-bananas": "2023",
    "sonny-spc-plush-collection-cuddly-bear": "2024",
    "sonny-spc-pet-treats": "2024",
    "sonny-spc-summer-island-holiday": "2021",
    "sonny-spc-bobbing-head": "2018",
    "sonny-spc-sky-color-series": "2017",
    "sonny-spc-snow-globe-ladur-e-p-tisserie-collection": "2014",
    "sonny-spc-bobbing-head-series-1": "2017",
    "sonny-spc-bobbing-head-butterfly": "2017",
}

SYLVANIAN_YEARS: dict[str, str] = {
    "sf-01-baby-band": "2018",
    "sf-02-baby-shopping": "2019",
    "sf-03-baby-outdoor": "2019",
    "sf-04-baby-party": "2019",
    "sf-05-baby-camping": "2020",
    "sf-06-baby-costume": "2020",
    "sf-07-magical-baby": "2021",
    "sf-08-baby-treats": "2021",
    "sf-09-baby-fun-hair": "2022",
    "sf-10-baby-fairytale": "2022",
    "sf-11-baby-seashore-friends": "2023",
    "sf-12-baby-forest-costume": "2023",
    "sf-13-baking-baby-party": "2024",
    "sf-14-blooming-baby-friends": "2024",
    "sf-15-baby-builder": "2025",
    "sf-16-baby-woodland-fairy": "2025",
    "sf-16b-baby-magical-wizard-friends": "2026",
    "sf-17-kuji-2021-shopping": "2021",
    "sf-18-kuji-2022-undersea": "2022",
    "sf-19-kuji-2023-forest": "2023",
    "sf-20-kuji-2024-delicious-parade": "2024",
    "sf-21-kuji-2025-happy-sweets": "2025",
    "sf-22-40th-anniversary-rabbits": "2025",
    "sf-23-pushchairs": "2025",
    "sf-24-flower-beds": "2025",
    "sf-25-flower-sofas": "2025",
    "sf-26-aqua-parade": "2022",
    "sf-27-fruits-1": "2023",
    "sf-28-fruits-2": "2023",
    "sf-29-ocean-babies": "2024",
    "sf-30-milky-way": "2025",
    "sf-31-tea-party": "2025",
    "sf-32-seaside-friends-children": "2024",
    "sf-33-milky-way-children": "2025",
    "sf-34-tea-party-children": "2025",
    "sf-35-mermaid-baby-furniture": "2023",
    "sf-36-fruits-3": "2025",
    "sf-37-fruits-4": "2025",
    "sf-38-very-berry-babies": "2023",
    "sf-39-bistro-babies": "2025",
    "sf-40-mini-party-babies": "2025",
    "sf-41-mini-fairytale-babies": "2025",
    "sf-42-6-figure-baby-shopping": "2023",
}


def fetch_products(url: str) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode()).get("products", [])
    except Exception:
        return []


def norm_toks(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {
        "skullpanda", "zsiga", "tinytiny", "sonny", "angel", "series", "blind", "box",
        "the", "of", "and", "in", "figures", "figurines", "edition", "plush", "pendant",
    }


def backfill_popmart(filename: str, slug: str) -> tuple[int, int]:
    path = DATA_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    prods = []
    for page in range(1, 5):
        batch = fetch_products(f"https://arttoyfamilia.com/collections/{slug}/products.json?limit=250&page={page}")
        if not batch:
            break
        prods.extend(batch)
        if len(batch) < 250:
            break

    p_index = [(norm_toks(p.get("title", "")), (p.get("created_at") or "")[:10]) for p in prods if p.get("created_at")]

    set_cnt = 0
    for c in data["collections"]:
        if c["id"].endswith(("mixed-sets", "standalone", "mixed")):
            continue
        if c.get("releaseDate"):
            set_cnt += 1
            continue
        ctoks = norm_toks(c.get("shortName") or c["name"])
        best_date = ""
        best_score = 0.0
        if ctoks:
            for ptoks, dt in p_index:
                if not ptoks:
                    continue
                score = len(ctoks & ptoks) / min(len(ctoks), len(ptoks))
                if score > best_score:
                    best_score = score
                    best_date = dt
        if best_date and best_score >= 0.65:
            c["releaseDate"] = best_date
            set_cnt += 1

    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return set_cnt, len(data["collections"])


def backfill_sonny() -> tuple[int, int]:
    total = 0
    done = 0
    for fn in ("sonny-regular.json", "sonny-hippers.json", "sonny-limited.json", "sonny-vintage.json", "sonny-archive.json"):
        path = DATA_DIR / fn
        data = json.loads(path.read_text(encoding="utf-8"))
        for k, v in data.items():
            if not (k.lower().endswith("collections") and isinstance(v, list)):
                continue
            for c in v:
                total += 1
                if c.get("releaseDate"):
                    done += 1
                    continue
                cid = c["id"]
                if cid in SONNY_KNOWN_YEARS:
                    c["releaseDate"] = SONNY_KNOWN_YEARS[cid]
                    done += 1
                    continue
                m = YEAR_RE.search(f"{c.get('name', '')} {c.get('subtitle', '')} {cid}")
                if m:
                    c["releaseDate"] = m.group(1)
                    done += 1
        path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return done, total


def backfill_sylvanian() -> tuple[int, int]:
    path = DATA_DIR / "sylvanian-families.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    done = 0
    for c in data["collections"]:
        if c["id"] in SYLVANIAN_YEARS:
            c["releaseDate"] = SYLVANIAN_YEARS[c["id"]]
            done += 1
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return done, len(data["collections"])


def main() -> None:
    sa_d, sa_t = backfill_sonny()
    sf_d, sf_t = backfill_sylvanian()
    sp_d, sp_t = backfill_popmart("skullpanda.json", "skullpanda")
    zs_d, zs_t = backfill_popmart("zsiga.json", "zsiga")
    tt_d, tt_t = backfill_popmart("tinytiny.json", "tinytiny")
    print(f"Sonny Angel : {sa_d:3d}/{sa_t:3d} sets with releaseDate")
    print(f"Sylvanian   : {sf_d:3d}/{sf_t:3d} sets with releaseDate")
    print(f"Skullpanda  : {sp_d:3d}/{sp_t:3d} sets with releaseDate")
    print(f"Zsiga       : {zs_d:3d}/{zs_t:3d} sets with releaseDate")
    print(f"Tinytiny    : {tt_d:3d}/{tt_t:3d} sets with releaseDate")


if __name__ == "__main__":
    main()
