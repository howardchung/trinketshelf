#!/usr/bin/env python3
"""Safely discover and append newly released sets & figures across TrinketShelf shelves.

Strictly additive and idempotent:
  - Uses token-set similarity against existing series & items so re-runs never duplicate
    already-curated series or size/punctuation variants.
  - Skips known non-figure accessories, multi-box bundles, and previously removed duplicates.
  - Always runs apply_catalog_overrides.py at the end so manual fixes remain enforced.
"""

from __future__ import annotations

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import apply_catalog_overrides
from common import IMAGES_DIR, download_and_normalize_image, slugify

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"
PRICES_PATH = DATA_DIR / "prices.json"

SKIP_VARIANT_WORDS = (
    "blind box",
    "blindbox",
    "whole set",
    "full set",
    "complete set",
    "sealed fullset",
    "sealed happiness",
    "sealed set",
    "sealed box",
    "assorted",
    "random",
    "display",
    "confirmed figures",
    "confirmed styles",
)

SKIP_POPMART_TITLE_WORDS = (
    "pop bean",
    "phone case",
    "phone charm",
    "magsafe",
    "lanyard",
    "cable",
    "earphone",
    "airpod",
    "fridge magnet",
    "magnet",
    "mini bag",
    "tote",
    "pouch",
    "mirror",
    "keycap",
    "pillow",
    "cushion",
    "blanket",
    "mug",
    "tumbler",
    "cup",
    "coaster",
    "notebook",
    "sticker",
    "badge",
    "brooch",
    "pin",
    "fragrance",
    "perfume",
    "sachet",
    "crystal ball",
    "pendant light",
    "squishy",
    "pop attach",
    "off mode",
    "life is a show",
    "i'm zsiga",
    "wishes come true",
    "perfect ordinary days",
    "dip for fun",
    "addams family",
    "wednesday",
)

SKIP_SONNY_SERIES = (
    "h family",
    "summer vacation",
    "valentine",
    "cherry blossom",
    "cat christmas",
    "strawberry love",
    "shu uemura",
)

JELLYCAT_SKIP = (
    "book",
    "board book",
    "if i were",
    "blanket",
    "soother",
    "comforter",
    "blankie",
    "rattle",
    "musical pull",
    "chime",
    "stroller",
    "bib",
    "booties",
    "socks",
    "tote",
    "bum bag",
    "crossbody",
    "backpack",
    "pouch",
    "gift bag",
    "notebook",
    "journal",
    "decoration",
    "ornament",
    "handbag",
    "shoulder bag",
    "gift box",
    "dust bag",
    "card",
    "sticker",
    "puzzle",
    "mug",
    "pacifier",
    "teether",
    "crib",
    "mobile",
    "robe",
    "slipper",
    "hat",
    "costume",
    "outfit",
    "playmat",
    "pillow",
    "cushion",
    "lamp",
    "gigantic",
    "plush toys",
    "soft toys",
    "bundle",
    "set of",
    "hc",
)


def fetch_products(url: str) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()).get("products", [])
    except Exception:
        return []


def series_tokens(name: str) -> set[str]:
    s = re.sub(r"[^a-z0-9]+", " ", name.lower())
    stop = {"sonny", "angel", "skullpanda", "zsiga", "tinytiny", "series", "edition", "style", "blind", "box", "the", "of", "and", "mini", "action", "figure", "figures", "version", "ver"}
    return {w for w in s.split() if len(w) > 1 and w not in stop and not re.fullmatch(r"20\d\d", w)}


def is_existing_series(candidate: str, existing_token_sets: list[set[str]]) -> bool:
    ct = series_tokens(candidate)
    if not ct:
        return True
    for et in existing_token_sets:
        if not et:
            continue
        overlap = len(ct & et) / min(len(ct), len(et))
        if overlap >= 0.75:
            return True
    return False


def extract_atf_variants(p: dict) -> list[tuple[str, str, float | None]]:
    img_by_id = {im["id"]: im["src"] for im in (p.get("images") or [])}
    fallback_img = (p.get("images") or [{}])[0].get("src")
    out: list[tuple[str, str, float | None]] = []
    for v in p.get("variants") or []:
        vt = (v.get("title") or "").strip()
        vtl = vt.lower()
        if any(bad in vtl for bad in SKIP_VARIANT_WORDS):
            continue
        img = (v.get("featured_image") or {}).get("src") or img_by_id.get(v.get("image_id")) or fallback_img
        if not img:
            continue
        price = None
        try:
            pv = float(v.get("price") or 0)
            if pv > 0:
                price = round(pv, 2)
        except Exception:
            pass
        out.append((vt, img, price))
    return out


def discover_sonny_angel(prices: dict[str, float], tasks: list[tuple[str, str]]) -> int:
    sl_path = DATA_DIR / "sonny-limited.json"
    sa = json.loads(sl_path.read_text(encoding="utf-8"))
    existing_token_sets: list[set[str]] = []
    for fn in ("sonny-regular.json", "sonny-hippers.json", "sonny-limited.json", "sonny-vintage.json"):
        d = json.loads((DATA_DIR / fn).read_text(encoding="utf-8"))
        for c in d["collections"]:
            existing_token_sets.append(series_tokens(c.get("shortName") or c["name"]))

    prods = fetch_products("https://toysez.com/collections/sonny-angel/products.json?limit=250&page=1")
    grouped: dict[str, list[dict]] = {}
    for p in prods:
        t = p.get("title", "")
        tl = t.lower()
        if "complete set" in tl or "confirmed style" not in tl:
            continue
        m = re.match(r"^Sonny Angel\s+(.+?):\s+(.+?)(?:\s*\(.*\))?$", t, flags=re.I)
        if not m:
            continue
        series_raw = re.sub(r"\s*Blind Box\s*", " ", m.group(1), flags=re.I).strip()
        series_raw = re.sub(r"\s+", " ", series_raw)
        if any(skip in series_raw.lower() for skip in SKIP_SONNY_SERIES):
            continue
        fig_name = m.group(2).strip()
        if not (p.get("images") or [{}])[0].get("src"):
            continue
        grouped.setdefault(series_raw, []).append({
            "name": fig_name,
            "img": p["images"][0]["src"],
            "price": p["variants"][0].get("price") if p.get("variants") else None,
            "secret": "secret" in tl or "robby" in fig_name.lower(),
        })

    added = 0
    used_ids = {it["id"] for it in sa["items"]}
    for series_name, figs in grouped.items():
        if len(figs) < 5 or is_existing_series(series_name, existing_token_sets):
            continue
        cid = f"sonny-lim-{slugify(series_name)}"
        sa["collections"].insert(0, {
            "id": cid,
            "name": f"Sonny Angel · {series_name}",
            "shortName": series_name,
            "parentShelf": "sonny-angel",
            "sonnyCategory": "limited",
            "subtitle": f"Limited Series ({len(figs)} figures)",
            "maker": "Dreams Inc.",
            "accent": "#E86A7D",
            "accentSoft": "#FDECEF",
            "accentText": "#A83247",
            "emoji": "✨",
        })
        for f in figs:
            iid = f"{cid}-{slugify(f['name'])}"
            if iid in used_ids:
                continue
            used_ids.add(iid)
            tasks.append((iid, f["img"]))
            if f["price"]:
                try:
                    prices[iid] = round(float(f["price"]), 2)
                except Exception:
                    pass
            sa["items"].append({
                "id": iid,
                "collectionId": cid,
                "name": f["name"],
                "series": series_name,
                "rarity": "Secret" if f["secret"] else "Regular",
                "image": f"/images/{iid}.webp",
                "imageSourceUrl": f["img"],
            })
            added += 1

    if added:
        sl_path.write_text(json.dumps(sa, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return added


def discover_popmart_shelf(
    shelf_slug: str,
    json_name: str,
    id_prefix: str,
    shelf_label: str,
    prices: dict[str, float],
    tasks: list[tuple[str, str]],
) -> int:
    path = DATA_DIR / json_name
    data = json.loads(path.read_text(encoding="utf-8"))
    existing_token_sets = [series_tokens(c.get("shortName") or c["name"]) for c in data["collections"]]
    used_ids = {it["id"] for it in data["items"]}

    prods = fetch_products(f"https://arttoyfamilia.com/collections/{shelf_slug}/products.json?limit=250&page=1")
    added = 0
    for p in prods:
        t = (p.get("title") or "").strip()
        tl = t.lower()
        if any(bad in tl for bad in SKIP_POPMART_TITLE_WORDS):
            continue
        if shelf_slug not in tl or ("series" not in tl and "blind box" not in tl):
            continue
        vars_ok = extract_atf_variants(p)
        if len(vars_ok) < 4:
            continue

        short = re.sub(rf"^{re.escape(shelf_label)}\s+", "", t, flags=re.I)
        short = re.sub(r"\s*Blind\s*Box\s*$", "", short, flags=re.I).strip()
        if is_existing_series(short, existing_token_sets):
            continue
        existing_token_sets.append(series_tokens(short))

        cid = f"{id_prefix}-{slugify(short)}"
        data["collections"].insert(0, {
            "id": cid,
            "name": f"{shelf_label} · {short}",
            "shortName": short,
            "subtitle": f"Blind Box Series ({len(vars_ok)} figures)",
            "maker": "POP MART",
            "accent": "#7C65B8",
            "accentSoft": "#F1EEFA",
            "accentText": "#4D3885",
            "emoji": "✨",
        })
        for vt, img, price in vars_ok:
            iid = f"{cid}-{slugify(vt)}"
            if iid in used_ids:
                continue
            used_ids.add(iid)
            tasks.append((iid, img))
            if price is not None:
                prices[iid] = price
            data["items"].append({
                "id": iid,
                "collectionId": cid,
                "name": vt,
                "series": short,
                "rarity": "Secret" if "secret" in vt.lower() else "Regular",
                "image": f"/images/{iid}.webp",
            })
            added += 1

    if added:
        path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return added


def upgrade_jellycat_svgs(prices: dict[str, float], tasks: list[tuple[str, str]]) -> int:
    """Only upgrade existing Jellycat .svg placeholders when an exact stockist photo appears."""
    jc_path = DATA_DIR / "jellycat.json"
    jc = json.loads(jc_path.read_text(encoding="utf-8"))

    def jc_key(name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r"^jellycat\s*[-–:|]?\s*", "", s)
        s = re.sub(r"\b(small|medium|large|huge|big|tiny|really|gigantic|original|plush|toy|soft|stuffed|animal|\d+\s*(?:in|inch|cm|\"))\b", " ", s)
        s = re.sub(r"^amuse?ables?\s+", "amuseables ", s)
        return slugify(s)

    svg_by_key = {jc_key(it["name"]): it for it in jc["items"] if it["image"].endswith(".svg")}
    if not svg_by_key:
        return 0

    stores = [
        ("https://www.babycubby.com/collections/jellycat/products.json?limit=250&page=1", 1.0),
        ("https://pacifierkids.com/collections/jellycat/products.json?limit=250&page=1", 1.0),
        ("https://faoschwarz.com/collections/jellycat/products.json?limit=250&page=1", 1.0),
        ("https://www.activebaby.ca/collections/jellycat/products.json?limit=250&page=1", 0.72),
        ("https://kolkid.ca/collections/jellycat/products.json?limit=250&page=1", 0.72),
    ]

    upgraded = 0
    for url, fx in stores:
        for p in fetch_products(url):
            title = (p.get("title") or "").strip()
            tl = title.lower()
            if any(bad in tl for bad in JELLYCAT_SKIP):
                continue
            imgs = p.get("images") or []
            if not imgs or not imgs[0].get("src"):
                continue
            k = jc_key(title)
            it = svg_by_key.pop(k, None)
            if not it:
                continue
            tasks.append((it["id"], imgs[0]["src"]))
            old_svg = IMAGES_DIR / f"{it['id']}.svg"
            if old_svg.exists():
                old_svg.unlink()
            it["image"] = f"/images/{it['id']}.webp"
            if p.get("variants") and p["variants"][0].get("price") and it["id"] not in prices:
                try:
                    pv = float(p["variants"][0]["price"])
                    if pv > 0:
                        prices[it["id"]] = round(pv * fx, 2)
                except Exception:
                    pass
            upgraded += 1

    if upgraded:
        jc_path.write_text(json.dumps(jc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return upgraded


def main() -> None:
    prices: dict[str, float] = json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    tasks: list[tuple[str, str]] = []

    sa_n = discover_sonny_angel(prices, tasks)
    sp_n = discover_popmart_shelf("skullpanda", "skullpanda.json", "sp-series", "Skullpanda", prices, tasks)
    zs_n = discover_popmart_shelf("zsiga", "zsiga.json", "zs-series", "Zsiga", prices, tasks)
    tt_n = discover_popmart_shelf("tinytiny", "tinytiny.json", "tinytiny-series", "Tinytiny", prices, tasks)
    jc_up = upgrade_jellycat_svgs(prices, tasks)

    if tasks:
        print(f"Downloading {len(tasks)} newly discovered photos...")
        with ThreadPoolExecutor(max_workers=12) as pool:
            futs = {
                pool.submit(download_and_normalize_image, url, IMAGES_DIR / f"{iid}.webp", overwrite=True): iid
                for iid, url in tasks
            }
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    print(f"  WARN {futs[fut]}: {exc}")
        PRICES_PATH.write_text(json.dumps(prices, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    # Always enforce curated manual overrides after discovery
    apply_catalog_overrides.main()

    print(
        f"Discovery complete: Sonny +{sa_n}, Skullpanda +{sp_n}, Zsiga +{zs_n}, "
        f"Tinytiny +{tt_n}, Jellycat SVGs upgraded: {jc_up}"
    )


if __name__ == "__main__":
    main()
