#!/usr/bin/env python3
"""Build the definitive 42-set Sylvanian Families catalog (public/data/sylvanian-families.json).

Combines:
  - Existing real Kobee Japan WebP photos & prices from sylvanian-families.json and calico-critters.json
  - Live Kobee Japan lookups for Pushchairs, Flower Beds, Aqua Parade, and Mermaid Baby Furniture
  - Authoritative Sylvanian Families Fandom Wiki rosters for all 16 Main Series, Mini Babies,
    Cutie Collectibles, Very Berry Babies, Bistro Babies, and 40th Anniversary Rabbits
  - Clean, XML-valid SVG portraits for figures without a store photo
"""

from __future__ import annotations

import html
import json
import re
import shutil
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import IMAGES_DIR, download_and_normalize_image, slugify

ROOT = Path(__file__).resolve().parent.parent
SF_JSON = ROOT / "public" / "data" / "sylvanian-families.json"
CC_JSON = ROOT / "public" / "data" / "calico-critters.json"
PRICES_JSON = ROOT / "public" / "data" / "prices.json"
WIKI_CACHE = Path("/tmp/sf_wiki_pages.json")

PALETTE = [
    ("#7A9E7E", "#EEF6EF", "#3E6342"),
    ("#D98A4E", "#FDF2E8", "#915221"),
    ("#C97B63", "#FAF0EC", "#874532"),
    ("#5C85B8", "#ECF2FA", "#315482"),
    ("#9B6BB8", "#F4EEFA", "#5E3478"),
    ("#D46C8C", "#FCEEF3", "#8E2F4C"),
    ("#4F94A8", "#EAF5F8", "#2A6070"),
    ("#B88B4A", "#FAF4EA", "#7A5724"),
]

# Definitive 42 sets in exact user-specified order:
# (id, shortName, group_label, emoji)
SETS_42 = [
    # Main Series (1-16)
    ("sf-01-baby-band", "Baby Band Series", "Main Series", "🎺"),
    ("sf-02-baby-shopping", "Baby Shopping Series", "Main Series", "🛒"),
    ("sf-03-baby-outdoor", "Baby Outdoor Series", "Main Series", "🏕️"),
    ("sf-04-baby-party", "Baby Party Series", "Main Series", "🎉"),
    ("sf-05-baby-camping", "Baby Camping Series", "Main Series", "⛺"),
    ("sf-06-baby-costume", "Baby Costume Series", "Main Series", "🎭"),
    ("sf-07-magical-baby", "Magical Baby Series", "Main Series", "🪄"),
    ("sf-08-baby-treats", "Baby Treats Series", "Main Series", "🧁"),
    ("sf-09-baby-fun-hair", "Baby Fun Hair Series", "Main Series", "🎀"),
    ("sf-10-baby-fairytale", "Baby Fairytale Series", "Main Series", "🧚"),
    ("sf-11-baby-seashore-friends", "Baby Seashore Friends Series", "Main Series", "🐚"),
    ("sf-12-baby-forest-costume", "Baby Forest Costume Series", "Main Series", "🍄"),
    ("sf-13-baking-baby-party", "Baking Baby Party Series", "Main Series", "🥐"),
    ("sf-14-blooming-baby-friends", "Blooming Baby Friends Series", "Main Series", "🌸"),
    ("sf-15-baby-builder", "Baby Builder Series", "Main Series", "🔨"),
    ("sf-16-baby-woodland-fairy", "Baby Woodland Fairy Costume", "Main Series", "🌿"),
    # Kuji Lottery (Japan Only) (17-21)
    ("sf-17-kuji-2021-shopping", "Kuji 2021 · Shopping", "Kuji Lottery (Japan Only)", "🎟️"),
    ("sf-18-kuji-2022-undersea", "Kuji 2022 · Undersea", "Kuji Lottery (Japan Only)", "🐠"),
    ("sf-19-kuji-2023-forest", "Kuji 2023 · Forest", "Kuji Lottery (Japan Only)", "🌲"),
    ("sf-20-kuji-2024-delicious-parade", "Kuji 2024 · Delicious Parade", "Kuji Lottery (Japan Only)", "🍨"),
    ("sf-21-kuji-2025-happy-sweets", "Kuji 2025 · Happy Sweets", "Kuji Lottery (Japan Only)", "🍰"),
    # JP Store Lotteries (22-25)
    ("sf-22-40th-anniversary-rabbits", "40th Anniversary Rabbits", "JP Store Lotteries", "🐰"),
    ("sf-23-pushchairs", "Pushchairs", "JP Store Lotteries", "🍼"),
    ("sf-24-flower-beds", "Flower Beds (Newborns)", "JP Store Lotteries", "🌼"),
    ("sf-25-flower-sofas", "Flower Sofas", "JP Store Lotteries", "🛋️"),
    # Official Store 6-Figure Bags (どきどきコレクション) (26-31)
    ("sf-26-aqua-parade", "Aqua Parade", "Official Store 6-Figure Bags", "🐬"),
    ("sf-27-fruits-1", "Fruits 1", "Official Store 6-Figure Bags", "🍓"),
    ("sf-28-fruits-2", "Fruits 2", "Official Store 6-Figure Bags", "🍑"),
    ("sf-29-ocean-babies", "Ocean Babies", "Official Store 6-Figure Bags", "🐙"),
    ("sf-30-milky-way", "Milky Way", "Official Store 6-Figure Bags", "🌌"),
    ("sf-31-tea-party", "Tea Party", "Official Store 6-Figure Bags", "🫖"),
    # Boxes (32-35)
    ("sf-32-seaside-friends-children", "Seaside Friends (Children)", "Boxes", "🦀"),
    ("sf-33-milky-way-children", "Milky Way (Children)", "Boxes", "⭐"),
    ("sf-34-tea-party-children", "Tea Party (Children)", "Boxes", "☕"),
    ("sf-35-mermaid-baby-furniture", "Mermaid Baby Furniture", "Boxes", "🧜"),
    # Calico Critters (36-39)
    ("sf-36-fruits-3", "Fruits 3", "Calico Critters", "🍇"),
    ("sf-37-fruits-4", "Fruits 4", "Calico Critters", "🍉"),
    ("sf-38-very-berry-babies", "Very Berry Babies", "Calico Critters", "🍓"),
    ("sf-39-bistro-babies", "Bistro Babies", "Calico Critters", "🍔"),
    # Others (40-42)
    ("sf-40-mini-party-babies", "Mini Party Babies Series", "Others · Newborns", "🎈"),
    ("sf-41-mini-fairytale-babies", "Mini Fairy Tale Babies Series", "Others · Newborns", "👑"),
    ("sf-42-6-figure-baby-shopping", "6-Figure Baby Shopping Series", "Others", "🛍️"),
]


def wrap_lines(text: str, max_chars: int = 19) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:4]


def make_svg(name: str, short_name: str, accent: str, accent_soft: str, accent_text: str, emoji: str) -> str:
    lines = wrap_lines(name, 19)
    start_y = 248 - (len(lines) - 1) * 14
    tspans = "".join(
        f'<text x="200" y="{start_y + i * 30}" text-anchor="middle" '
        f'font-family="system-ui,-apple-system,sans-serif" font-size="22" font-weight="700" '
        f'fill="{accent_text}">{html.escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    series_upper = html.escape(short_name.upper())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">'
        f'<rect width="400" height="400" rx="28" fill="{accent_soft}"/>'
        f'<circle cx="200" cy="135" r="62" fill="#FFFFFF" fill-opacity="0.88" stroke="{accent}" stroke-width="3"/>'
        f'<text x="200" y="154" text-anchor="middle" font-size="56">{emoji}</text>'
        f"{tspans}"
        f'<text x="200" y="355" text-anchor="middle" font-family="system-ui,-apple-system,sans-serif" '
        f'font-size="13" font-weight="600" fill="{accent}" letter-spacing="0.8">{series_upper}</text>'
        f"</svg>"
    )


def clean_wiki_line(s: str) -> str:
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s)
    s = re.sub(r"<ref[^/>]*/>", "", s)
    s = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"\s+", " ", s).strip(" -–:.")
    return s


def parse_wiki_section_numbered(wikitext: str, section_name: str) -> list[str]:
    secs = re.split(r"^==+\s*(.+?)\s*==+$", wikitext, flags=re.M)
    for i in range(1, len(secs), 2):
        if secs[i].strip().lower() == section_name.lower():
            body = secs[i + 1]
            lines = re.findall(r"^#\s*(.+)$", body, flags=re.M)
            return [clean_wiki_line(l) for l in lines if clean_wiki_line(l)]
    return []


def parse_wiki_bullets(wikitext: str, section_name: str = "Figures") -> list[str]:
    secs = re.split(r"^==+\s*(.+?)\s*==+$", wikitext, flags=re.M)
    for i in range(1, len(secs), 2):
        if secs[i].strip().lower() == section_name.lower():
            body = secs[i + 1]
            lines = re.findall(r"^\*\s*(.+)$", body, flags=re.M)
            return [clean_wiki_line(l) for l in lines if clean_wiki_line(l)]
    return []


def search_kobee(query: str, must_contain: str) -> list[dict]:
    u = (
        "https://store.kobeejapan.net/search/suggest.json?q="
        + urllib.parse.quote(query)
        + "&resources[type]=product&resources[limit]=10"
    )
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
        prods = d.get("resources", {}).get("results", {}).get("products", [])
    except Exception:
        return []
    out = []
    for p in prods:
        t = p.get("title", "")
        tl = t.lower()
        if "[used]" in tl or "blind bag" in tl or "complete set" in tl or "pair set" in tl:
            continue
        if must_contain.lower() not in tl:
            continue
        img = p.get("image") or (p.get("featured_image") or {}).get("url")
        if not img:
            continue
        if img.startswith("//"):
            img = "https:" + img
        price = None
        try:
            pv = float(p.get("price") or 0)
            if pv > 0:
                price = round(pv, 2)
        except Exception:
            pass
        # Clean title
        name = re.sub(r"\b20\d\d\b.*", "", t).strip()
        name = re.sub(r"\s*Sylvanian Families.*$", "", name, flags=re.I).strip()
        name = re.sub(r"^" + re.escape(must_contain) + r"\s*[-–:]?\s*", "", name, flags=re.I).strip()
        name = re.sub(r"\s+", " ", name).strip(" -–:")
        if name:
            prod_url = p.get("url") or ""
            if prod_url.startswith("/"):
                prod_url = "https://store.kobeejapan.net" + prod_url.split("?")[0]
            out.append({"name": name, "img": img, "price": price, "source_url": prod_url})
    return out


def main() -> None:
    sf_old = json.loads(SF_JSON.read_text(encoding="utf-8"))
    cc_old = json.loads(CC_JSON.read_text(encoding="utf-8"))
    prices = json.loads(PRICES_JSON.read_text(encoding="utf-8"))
    wiki = json.loads(WIKI_CACHE.read_text(encoding="utf-8"))

    # Group existing items by collectionId
    old_by_cid: dict[str, list[dict]] = {}
    for src in (sf_old, cc_old):
        for it in src["items"]:
            old_by_cid.setdefault(it["collectionId"], []).append(it)

    # Map our 42 set IDs to existing collection IDs with real Kobee Japan WebP photos
    EXISTING_SOURCE_MAP: dict[str, list[str]] = {
        "sf-01-baby-band": ["cc-sp-01-baby-band"],
        "sf-02-baby-shopping": ["sf-bag-baby-shopping-series", "cc-sp-02-baby-shopping"],
        "sf-04-baby-party": ["sf-bag-baby-party-series", "cc-sp-03-baby-party"],
        "sf-05-baby-camping": ["sf-bag-baby-camping-series", "cc-sp-06-baby-camping"],
        "sf-06-baby-costume": ["cc-sp-04-baby-costume"],
        "sf-07-magical-baby": ["sf-bag-baby-magical-series", "cc-sp-07-magical-baby"],
        "sf-08-baby-treats": ["cc-sp-05-baby-treats"],
        "sf-09-baby-fun-hair": ["cc-sp-08-baby-fun-hair"],
        "sf-10-baby-fairytale": ["cc-sp-10-baby-fairytale"],
        "sf-11-baby-seashore-friends": ["cc-sp-09-baby-seashore"],
        "sf-12-baby-forest-costume": ["sf-bag-baby-forest-costume", "cc-sp-11-baby-forest"],
        "sf-13-baking-baby-party": ["cc-sp-12-baking-party"],
        "sf-14-blooming-baby-friends": ["sf-bag-blooming-baby-friends", "cc-sp-13-blooming-friends"],
        "sf-15-baby-builder": ["sf-bag-baby-craft-lovers"],
        "sf-16-baby-woodland-fairy": ["sf-bag-fairy-forest-friends", "cc-sp-14-fairy-forest"],
        "sf-20-kuji-2024-delicious-parade": ["sf-box-delicious-parade-blind-box"],
        "sf-21-kuji-2025-happy-sweets": ["sf-box-happy-sweets-lottery-box"],
        "sf-27-fruits-1": ["sf-bag-baby-fruit-party"],
        "sf-28-fruits-2": ["sf-bag-baby-fruit-party-2"],
        "sf-30-milky-way": ["sf-box-doki-doki-milky-way"],
        "sf-31-tea-party": ["sf-box-doki-doki-baby-tea-time"],
        "sf-38-very-berry-babies": ["sf-box-very-berry-babies"],
    }

    # Fetch live Kobee Japan products for Pushchairs, Flower Beds, Aqua Parade, Mermaid Baby Furniture
    kobee_live: dict[str, list[dict]] = {}
    kobee_queries = {
        "sf-23-pushchairs": ("Baby and Stroller Series", "Baby and Stroller Series"),
        "sf-24-flower-beds": ("Baby and Flower Bed Set", "Baby and Flower Bed Set"),
        "sf-26-aqua-parade": ("Baby Aqua Parade Series", "Baby Aqua Parade Series"),
        "sf-35-mermaid-baby-furniture": ("Baby Furniture Collection Dreamy Mermaid", "Baby Furniture Collection Dreamy Mermaid"),
    }
    for sid, (q, must) in kobee_queries.items():
        hits = search_kobee(q, must)
        if hits:
            kobee_live[sid] = hits
            print(f"Kobee live [{sid}]: {len(hits)} items")

    # Authoritative fallback rosters for sets without full Kobee listings
    bb_txt = wiki["Baby Series Blind Bags"]
    mini_txt = wiki["Baby Series Blind Bags/Mini Babies"]

    ROSTERS: dict[str, list[tuple[str, str]]] = {
        "sf-03-baby-outdoor": [
            (n, "Secret" if i == 8 else "Regular")
            for i, n in enumerate(parse_wiki_section_numbered(bb_txt, "Baby Outdoor Series"))
        ],
        "sf-17-kuji-2021-shopping": [
            ("Chocolate Rabbit Baby (Shopping Kuji)", "Regular"),
            ("Walnut Squirrel Baby (Shopping Kuji)", "Regular"),
            ("Persian Cat Baby (Shopping Kuji)", "Regular"),
            ("Toy Poodle Baby (Shopping Kuji)", "Regular"),
            ("Maple Cat Baby (Shopping Kuji)", "Regular"),
            ("Milk Rabbit Baby (Shopping Kuji)", "Regular"),
            ("Bear Baby (Shopping Kuji)", "Regular"),
            ("Marshmallow Mouse Baby (Shopping Kuji)", "Regular"),
        ],
        "sf-18-kuji-2022-undersea": [
            ("Chocolate Rabbit Baby (Undersea Kuji)", "Regular"),
            ("Husky Baby (Undersea Kuji)", "Regular"),
            ("Silk Cat Baby (Undersea Kuji)", "Regular"),
            ("Marshmallow Mouse Baby (Undersea Kuji)", "Regular"),
            ("Splashy Otter Baby (Undersea Kuji)", "Regular"),
            ("Persian Cat Baby (Undersea Kuji)", "Regular"),
            ("Fennec Fox Baby (Undersea Kuji)", "Regular"),
            ("Bear Baby (Undersea Kuji)", "Regular"),
        ],
        "sf-19-kuji-2023-forest": [
            ("Walnut Squirrel Baby (Forest Kuji)", "Regular"),
            ("Marshmallow Mouse Baby (Forest Kuji)", "Regular"),
            ("Koala Baby (Forest Kuji)", "Regular"),
            ("Deer Baby (Forest Kuji)", "Regular"),
            ("Husky Baby (Forest Kuji)", "Regular"),
            ("Chocolate Rabbit Baby (Forest Kuji)", "Regular"),
            ("Latte Cat Baby (Forest Kuji)", "Regular"),
            ("Bear Baby (Forest Kuji)", "Regular"),
        ],
        "sf-22-40th-anniversary-rabbits": [
            ("Chocolate Rabbit Baby (Pink Bunny Costume)", "Special"),
            ("Flora Rabbit Baby (Yellow Bunny Costume)", "Special"),
            ("Milk Rabbit Baby (Blue Bunny Costume)", "Special"),
            ("Marguerite Rabbit Baby (Purple Bunny Costume)", "Special"),
            ("Cottontail Rabbit Baby (Green Bunny Costume)", "Special"),
        ],
        "sf-25-flower-sofas": [
            ("Chocolate Rabbit Baby with Flower Sofa", "Regular"),
            ("Persian Cat Baby with Flower Sofa", "Regular"),
            ("Fennec Fox Baby with Flower Sofa", "Regular"),
            ("Latte Cat Baby with Flower Sofa", "Regular"),
            ("Husky Baby with Flower Sofa", "Regular"),
            ("Deer Baby with Flower Sofa", "Regular"),
        ],
        "sf-29-ocean-babies": [
            (f"{n} (Ocean Babies)", "Regular")
            for n in parse_wiki_bullets(wiki["Cutie Collectibles – Ocean Babies"])
        ],
        "sf-32-seaside-friends-children": [
            (f"{n} (Seaside Friends)", "Regular")
            for n in parse_wiki_bullets(wiki["Cutie Collectibles – Seaside Friends"])
        ],
        "sf-33-milky-way-children": [
            (f"{n} (Milky Way Friends)", "Regular")
            for n in parse_wiki_bullets(wiki["Cutie Collectibles – Milky Way Friends"])
        ],
        "sf-34-tea-party-children": [
            ("Chocolate Rabbit Girl (Tea Party)", "Regular"),
            ("Fennec Fox Girl (Tea Party)", "Regular"),
            ("Deer Girl (Tea Party)", "Regular"),
            ("Giraffe Girl (Tea Party)", "Regular"),
        ],
        "sf-36-fruits-3": [
            ("Sheep Baby · Sean (Fruits 3)", "Regular"),
            ("Koala Baby · Adelaide (Fruits 3)", "Regular"),
            ("Chocolate Rabbit Baby (Fruits 3)", "Regular"),
            ("Persian Cat Baby (Fruits 3)", "Regular"),
            ("Husky Baby (Fruits 3)", "Regular"),
            ("Latte Cat Baby (Fruits 3)", "Regular"),
        ],
        "sf-37-fruits-4": [
            ("Fennec Fox Baby · Yulie (Fruits 4)", "Regular"),
            ("Deer Baby (Fruits 4)", "Regular"),
            ("Walnut Squirrel Baby (Fruits 4)", "Regular"),
            ("Bear Baby (Fruits 4)", "Regular"),
            ("Striped Cat Baby (Fruits 4)", "Regular"),
            ("Marshmallow Mouse Baby (Fruits 4)", "Regular"),
        ],
        "sf-39-bistro-babies": [
            ("Chocolate Rabbit Baby (Bistro Babies)", "Regular"),
            ("Walnut Squirrel Baby (Bistro Babies)", "Regular"),
            ("Persian Cat Baby (Bistro Babies)", "Regular"),
            ("Husky Baby (Bistro Babies)", "Regular"),
            ("Fennec Fox Baby (Bistro Babies)", "Regular"),
            ("Koala Baby (Bistro Babies)", "Regular"),
        ],
        "sf-40-mini-party-babies": [
            (n, "Regular")
            for n in parse_wiki_section_numbered(mini_txt, "Mini Party Babies Series")
        ],
        "sf-41-mini-fairytale-babies": [
            (n, "Regular")
            for n in parse_wiki_section_numbered(mini_txt, "Mini Fairytale Babies Series")
        ],
        "sf-42-6-figure-baby-shopping": [
            ("Chocolate Rabbit Baby with Bread", "Regular"),
            ("Walnut Squirrel Baby with Shopping Cart", "Regular"),
            ("Silk Cat Baby with Cash Register", "Regular"),
            ("Toy Poodle Baby with Popcorn Cart", "Regular"),
            ("Bear Baby with Toast", "Regular"),
            ("Marshmallow Mouse Baby with Grocery Basket", "Regular"),
        ],
    }

    collections: list[dict] = []
    items: list[dict] = []
    used_ids: set[str] = set()
    download_tasks: list[tuple[str, str]] = []
    referenced_images: set[str] = set()

    for idx, (sid, short_name, group_label, emoji) in enumerate(SETS_42):
        accent, accent_soft, accent_text = PALETTE[idx % len(PALETTE)]
        set_items: list[dict] = []

        # 1. Existing real Kobee WebP items (take first matching source collection that has items)
        if sid in EXISTING_SOURCE_MAP:
            chosen_src = []
            for old_cid in EXISTING_SOURCE_MAP[sid]:
                if old_by_cid.get(old_cid):
                    chosen_src = old_by_cid[old_cid]
                    break
            seen_names: set[str] = set()
            for old_it in chosen_src:
                nk = slugify(old_it["name"])
                if nk in seen_names:
                    continue
                seen_names.add(nk)
                old_id = old_it["id"]
                new_id = f"{sid}-{nk}"
                n = 2
                while new_id in used_ids:
                    new_id = f"{sid}-{nk}-{n}"
                    n += 1
                used_ids.add(new_id)

                # Copy existing WebP under new sf-* ID so cc-* files can be safely deleted
                old_img_path = ROOT / "public" / old_it["image"].lstrip("/")
                ext = old_img_path.suffix or ".webp"
                new_img_rel = f"/images/{new_id}{ext}"
                new_img_path = IMAGES_DIR / f"{new_id}{ext}"
                if old_img_path.is_file() and old_img_path != new_img_path:
                    shutil.copy2(old_img_path, new_img_path)
                referenced_images.add(new_img_path.name)

                # Copy price if present
                if old_id in prices and new_id not in prices:
                    prices[new_id] = prices[old_id]

                set_items.append({
                    "id": new_id,
                    "collectionId": sid,
                    "name": old_it["name"],
                    "series": short_name,
                    "rarity": old_it.get("rarity", "Regular"),
                    "image": new_img_rel,
                })

            # Special case: Very Berry Babies has 5 figures (add 5th Bear Baby Jason if missing)
            if sid == "sf-38-very-berry-babies" and len(set_items) < 5:
                if not any("bear" in x["name"].lower() or "jason" in x["name"].lower() for x in set_items):
                    iid = f"{sid}-bear-baby-jason-osborne"
                    used_ids.add(iid)
                    svg_p = IMAGES_DIR / f"{iid}.svg"
                    svg_p.write_text(make_svg("Bear Baby · Jason Osborne", short_name, accent, accent_soft, accent_text, emoji), encoding="utf-8")
                    referenced_images.add(svg_p.name)
                    set_items.append({
                        "id": iid,
                        "collectionId": sid,
                        "name": "Bear Baby · Jason Osborne",
                        "series": short_name,
                        "rarity": "Regular",
                        "image": f"/images/{iid}.svg",
                    })

        # 2. Live Kobee Japan items (download real WebP photos!)
        elif sid in kobee_live:
            seen_names = set()
            for hit in kobee_live[sid]:
                nk = slugify(hit["name"])
                if nk in seen_names:
                    continue
                seen_names.add(nk)
                iid = f"{sid}-{nk}"
                n = 2
                while iid in used_ids:
                    iid = f"{sid}-{nk}-{n}"
                    n += 1
                used_ids.add(iid)
                download_tasks.append((iid, hit["img"]))
                referenced_images.add(f"{iid}.webp")
                if hit["price"] is not None:
                    prices[iid] = hit["price"]
                set_items.append({
                    "id": iid,
                    "collectionId": sid,
                    "name": hit["name"],
                    "series": short_name,
                    "rarity": "Regular",
                    "image": f"/images/{iid}.webp",
                    **({"sourceUrl": hit["source_url"]} if hit.get("source_url") else {}),
                    "imageSourceUrl": hit["img"],
                })

        # 3. Authoritative Wiki / curated roster with clean themed SVG portraits
        elif sid in ROSTERS:
            for name, rarity in ROSTERS[sid]:
                nk = slugify(name)
                iid = f"{sid}-{nk}"
                n = 2
                while iid in used_ids:
                    iid = f"{sid}-{nk}-{n}"
                    n += 1
                used_ids.add(iid)
                svg_p = IMAGES_DIR / f"{iid}.svg"
                svg_p.write_text(make_svg(name, short_name, accent, accent_soft, accent_text, emoji), encoding="utf-8")
                referenced_images.add(svg_p.name)
                set_items.append({
                    "id": iid,
                    "collectionId": sid,
                    "name": name,
                    "series": short_name,
                    "rarity": rarity,
                    "image": f"/images/{iid}.svg",
                })

        collections.append({
            "id": sid,
            "name": f"Sylvanian Families · {short_name}",
            "shortName": short_name,
            "subtitle": f"{group_label} ({len(set_items)} figures)",
            "maker": "Epoch",
            "accent": accent,
            "accentSoft": accent_soft,
            "accentText": accent_text,
            "emoji": emoji,
        })
        items.extend(set_items)

    # Download live Kobee images
    if download_tasks:
        print(f"Downloading {len(download_tasks)} live Kobee photos...")
        with ThreadPoolExecutor(max_workers=12) as pool:
            futs = {
                pool.submit(download_and_normalize_image, url, IMAGES_DIR / f"{iid}.webp", overwrite=False): iid
                for iid, url in download_tasks
            }
            for fut in as_completed(futs):
                iid = futs[fut]
                try:
                    fut.result()
                except Exception as exc:
                    print(f"  WARN {iid} failed ({exc}), falling back to SVG")
                    # Fallback to SVG
                    for it in items:
                        if it["id"] == iid:
                            col = next(c for c in collections if c["id"] == it["collectionId"])
                            svg_p = IMAGES_DIR / f"{iid}.svg"
                            svg_p.write_text(make_svg(it["name"], col["shortName"], col["accent"], col["accentSoft"], col["accentText"], col["emoji"]), encoding="utf-8")
                            it["image"] = f"/images/{iid}.svg"
                            referenced_images.add(svg_p.name)

    # Clean up old cc-* and unreferenced old sf-* images & prices
    new_sf_ids = {it["id"] for it in items}
    removed_imgs = 0
    for p in list(IMAGES_DIR.glob("cc-*")) + list(IMAGES_DIR.glob("sf-*")):
        if p.name not in referenced_images:
            p.unlink()
            removed_imgs += 1

    removed_prices = 0
    for k in list(prices.keys()):
        if k.startswith("cc-") or (k.startswith("sf-") and k not in new_sf_ids):
            del prices[k]
            removed_prices += 1

    SF_JSON.write_text(
        json.dumps({"collections": collections, "items": items}, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    PRICES_JSON.write_text(
        json.dumps(prices, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    if CC_JSON.exists():
        CC_JSON.unlink()

    webp_cnt = sum(1 for it in items if it["image"].endswith(".webp"))
    svg_cnt = sum(1 for it in items if it["image"].endswith(".svg"))
    print(f"Wrote {SF_JSON}: {len(collections)} sets, {len(items)} items ({webp_cnt} WebP, {svg_cnt} SVG)")
    print(f"Cleaned up {removed_imgs} old cc-/sf- images, {removed_prices} old prices, deleted calico-critters.json")


if __name__ == "__main__":
    main()
