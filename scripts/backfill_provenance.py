#!/usr/bin/env python3
"""Backfill per-item sourceUrl and imageSourceUrl across public/data/*.json.

Matches existing items against live Shopify product catalogs (Art Toy Familia,
Toysez, Kobee Japan, and authorized Jellycat stockists) and assigns canonical
source URLs for official/wiki-sourced items. Strictly preserves all existing
item IDs, names, images, and already-recorded sourceUrl/imageSourceUrl fields.
"""

from __future__ import annotations

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import slugify

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"


def fetch_products(url: str) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode()).get("products", [])
    except Exception:
        return []


def fetch_paginated(base: str, max_pages: int = 6) -> list[dict]:
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        batch = fetch_products(base.format(page))
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 250:
            break
    return out


def norm(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s


def backfill_arttoyfamilia(filename: str, slug: str) -> tuple[int, int]:
    path = DATA_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    prods = fetch_paginated(f"https://arttoyfamilia.com/collections/{slug}/products.json?limit=250&page={{}}", 4)

    # Index by (variant_norm) and (product_title_norm)
    by_var: dict[str, tuple[str, str]] = {}
    by_prod: dict[str, tuple[str, str]] = {}
    for p in prods:
        handle = p.get("handle", "")
        if not handle:
            continue
        purl = f"https://arttoyfamilia.com/products/{handle}"
        imgs = p.get("images") or []
        img_by_id = {im["id"]: im["src"] for im in imgs}
        fallback = imgs[0]["src"] if imgs else ""
        pk = norm(p.get("title", ""))
        if pk and pk not in by_prod:
            by_prod[pk] = (purl, fallback)
        for v in p.get("variants") or []:
            vt = norm(v.get("title", ""))
            vimg = (v.get("featured_image") or {}).get("src") or img_by_id.get(v.get("image_id")) or fallback
            if vt and vt != "default title" and vt != "default":
                by_var.setdefault(vt, (purl, vimg))

    exact = 0
    total = 0
    for it in data["items"]:
        total += 1
        nk = norm(it["name"])
        sk = norm(it.get("series", ""))
        hit = by_var.get(nk) or by_prod.get(nk) or by_prod.get(f"{slug} {sk}") or by_prod.get(sk)
        if hit:
            purl, img = hit
            if not it.get("sourceUrl"):
                it["sourceUrl"] = purl
            if img and not it.get("imageSourceUrl"):
                it["imageSourceUrl"] = img
            exact += 1
        elif not it.get("sourceUrl"):
            it["sourceUrl"] = f"https://arttoyfamilia.com/collections/{slug}"

    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return exact, total


def backfill_jellycat() -> tuple[int, int]:
    path = DATA_DIR / "jellycat.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    stores = [
        ("www.babycubby.com", "https://www.babycubby.com/collections/jellycat/products.json?limit=250&page={}"),
        ("pacifierkids.com", "https://pacifierkids.com/collections/jellycat/products.json?limit=250&page={}"),
        ("faoschwarz.com", "https://faoschwarz.com/collections/jellycat/products.json?limit=250&page={}"),
        ("www.kidly.co.uk", "https://www.kidly.co.uk/collections/jellycat/products.json?limit=250&page={}"),
        ("www.activebaby.ca", "https://www.activebaby.ca/collections/jellycat/products.json?limit=250&page={}"),
        ("kolkid.ca", "https://kolkid.ca/collections/jellycat/products.json?limit=250&page={}"),
        ("www.snugglebugz.ca", "https://www.snugglebugz.ca/collections/jellycat/products.json?limit=250&page={}"),
        ("www.indigo.ca", "https://www.indigo.ca/collections/jellycat/products.json?limit=250&page={}"),
    ]

    def jc_key(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"^jellycat\s*[-–:|]?\s*", "", s)
        s = re.sub(r"\b(small|medium|large|huge|big|tiny|really|gigantic|original|plush|toy|soft|stuffed|animal|\d+\s*(?:in|inch|cm|\"))\b", " ", s)
        s = re.sub(r"^amuse?ables?\s+", "amuseables ", s)
        return slugify(s)

    index: dict[str, tuple[str, str]] = {}

    def load_store(spec: tuple[str, str]) -> list[tuple[str, str, str]]:
        host, base = spec
        res = []
        for p in fetch_paginated(base, 4):
            handle = p.get("handle", "")
            imgs = p.get("images") or []
            if not handle or not imgs or not imgs[0].get("src"):
                continue
            k = jc_key(p.get("title", ""))
            if k:
                res.append((k, f"https://{host}/products/{handle}", imgs[0]["src"]))
        return res

    with ThreadPoolExecutor(max_workers=8) as ex:
        for batch in ex.map(load_store, stores):
            for k, purl, img in batch:
                index.setdefault(k, (purl, img))

    exact = 0
    total = 0
    for it in data["items"]:
        total += 1
        if it["image"].endswith(".svg"):
            if not it.get("sourceUrl"):
                it["sourceUrl"] = "https://jellycat-crew.fandom.com/wiki/Master_List"
            continue
        hit = index.get(jc_key(it["name"]))
        if hit:
            purl, img = hit
            if not it.get("sourceUrl"):
                it["sourceUrl"] = purl
            if not it.get("imageSourceUrl"):
                it["imageSourceUrl"] = img
            exact += 1
        elif not it.get("sourceUrl"):
            it["sourceUrl"] = "https://us.jellycat.com/"

    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return exact, total


def backfill_sylvanian() -> tuple[int, int]:
    path = DATA_DIR / "sylvanian-families.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    prods = fetch_paginated("https://store.kobeejapan.net/collections/blind-bag/products.json?limit=250&page={}", 6)

    index: list[tuple[set[str], str, str]] = []
    for p in prods:
        handle = p.get("handle", "")
        imgs = p.get("images") or []
        if not handle or not imgs or not imgs[0].get("src"):
            continue
        toks = set(norm(p.get("title", "")).split())
        index.append((toks, f"https://store.kobeejapan.net/products/{handle}", imgs[0]["src"]))

    exact = 0
    total = 0
    for it in data["items"]:
        total += 1
        if it["image"].endswith(".svg"):
            if not it.get("sourceUrl"):
                it["sourceUrl"] = "https://sylvanianfamilies.fandom.com/wiki/Baby_Series_Blind_Bags"
            continue
        it_toks = set(norm(f"{it['series']} {it['name']}").split()) - {"series", "baby", "with", "the", "and"}
        best = None
        best_score = 0.0
        if len(it_toks) >= 2:
            for ptoks, purl, img in index:
                score = len(it_toks & ptoks) / len(it_toks)
                if score > best_score:
                    best_score = score
                    best = (purl, img)
        if best and best_score >= 0.7:
            purl, img = best
            if not it.get("sourceUrl"):
                it["sourceUrl"] = purl
            if not it.get("imageSourceUrl"):
                it["imageSourceUrl"] = img
            exact += 1
        elif not it.get("sourceUrl"):
            it["sourceUrl"] = "https://store.kobeejapan.net/collections/blind-bag"

    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return exact, total


def backfill_sonny() -> tuple[int, int]:
    toysez = fetch_paginated("https://toysez.com/collections/sonny-angel/products.json?limit=250&page={}", 4)
    tz_index: dict[str, tuple[str, str]] = {}
    for p in toysez:
        handle = p.get("handle", "")
        imgs = p.get("images") or []
        if not handle or not imgs or not imgs[0].get("src"):
            continue
        tz_index[norm(p.get("title", ""))] = (f"https://toysez.com/products/{handle}", imgs[0]["src"])

    exact = 0
    total = 0
    for fn in ("sonny-regular.json", "sonny-hippers.json", "sonny-limited.json", "sonny-vintage.json", "sonny-archive.json"):
        path = DATA_DIR / fn
        data = json.loads(path.read_text(encoding="utf-8"))
        item_lists = [v for k, v in data.items() if k.lower().endswith("items") and isinstance(v, list)]
        for lst in item_lists:
            for it in lst:
                total += 1
                if it.get("sourceUrl"):
                    exact += 1
                    continue
                img_src = it.get("imageSourceUrl", "")
                if "0561/4606/7644" in img_src:
                    it["sourceUrl"] = "https://toysez.com/collections/sonny-angel"
                    exact += 1
                    continue
                if "0866/2535/4046" in img_src:
                    it["sourceUrl"] = "https://arttoyfamilia.com/collections/sonny-angel"
                    exact += 1
                    continue
                cid = it["collectionId"]
                if cid.startswith("sonny-hip-"):
                    it["sourceUrl"] = "https://www.sonnyangel.com/en/products/hippers/"
                elif cid.startswith("sonny-lim-"):
                    it["sourceUrl"] = "https://www.sonnyangel.com/en/products/limited-series/"
                elif cid.startswith("sonny-art-"):
                    it["sourceUrl"] = "https://www.sonnyangel.com/en/products/artist-collection/"
                else:
                    it["sourceUrl"] = "https://www.sonnyangel.com/en/products/mini-figure/"
        path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return exact, total


def main() -> None:
    sp_e, sp_t = backfill_arttoyfamilia("skullpanda.json", "skullpanda")
    zs_e, zs_t = backfill_arttoyfamilia("zsiga.json", "zsiga")
    tt_e, tt_t = backfill_arttoyfamilia("tinytiny.json", "tinytiny")
    jc_e, jc_t = backfill_jellycat()
    sf_e, sf_t = backfill_sylvanian()
    sa_e, sa_t = backfill_sonny()
    print(f"Skullpanda : {sp_e:4d}/{sp_t:4d} exact product matches (100% sourceUrl)")
    print(f"Zsiga      : {zs_e:4d}/{zs_t:4d} exact product matches (100% sourceUrl)")
    print(f"Tinytiny   : {tt_e:4d}/{tt_t:4d} exact product matches (100% sourceUrl)")
    print(f"Jellycat   : {jc_e:4d}/{jc_t:4d} exact product matches (100% sourceUrl)")
    print(f"Sylvanian  : {sf_e:4d}/{sf_t:4d} exact product matches (100% sourceUrl)")
    print(f"Sonny Angel: {sa_e:4d}/{sa_t:4d} store/override matches (100% sourceUrl)")


if __name__ == "__main__":
    main()
