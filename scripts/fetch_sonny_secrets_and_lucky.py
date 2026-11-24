#!/usr/bin/env python3
"""Match & download real Sonny Angel Secret, Robby Angel, Lucky, and Vintage photos.

Queries public Shopify product feeds (toysez.com, arttoyfamilia.com, blinkbox.com.au)
to replace any remaining `.svg` placeholder images in src/data/*.ts with normalized
512x512 `.webp` product photos in public/images/.
"""

from __future__ import annotations

import argparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import DATA_DIR, IMAGES_DIR, download_and_normalize_image, fetch_json

STOP_WORDS = {
    "sonny", "angel", "series", "blind", "box", "mini", "figure", "edition",
    "confirmed", "style", "limited", "the", "of", "in", "and", "with", "secret",
    "version", "ver", "regular", "gift", "collection", "vintage", "seasonal",
}

TS_FILES = [
    DATA_DIR / "catalog.ts",
    DATA_DIR / "sonnyHippers.ts",
    DATA_DIR / "sonnyLimited.ts",
    DATA_DIR / "sonnyVintage.ts",
]

ITEM_SVG_RE = re.compile(
    r'\{\s*"?id"?:\s*[\'"]([^\'"]+)[\'"],\s*"?collectionId"?:\s*[\'"]([^\'"]+)[\'"],\s*'
    r'"?name"?:\s*[\'"]([^\'"]+)[\'"],\s*"?series"?:\s*[\'"]([^\'"]+)[\'"],\s*'
    r'"?rarity"?:\s*[\'"]([^\'"]+)[\'"],\s*"?image"?:\s*[\'"](/images/[^\'"]+\.svg)[\'"]',
    re.S,
)


def tokens(text: str) -> set[str]:
    text = text.lower().replace("valentine's", "valentine").replace("valentines", "valentine")
    return set(re.findall(r"[a-z0-9]+", text)) - STOP_WORDS


def extract_years(text: str) -> set[str]:
    return set(re.findall(r"\b20\d\d\b", text))


def build_candidate_index() -> list[dict]:
    products: list[dict] = []
    for page in range(1, 10):
        url = f"https://toysez.com/collections/sonny-angel/products.json?limit=250&page={page}"
        try:
            batch = fetch_json(url).get("products", [])
            if not batch:
                break
            products.extend(batch)
        except Exception:
            break

    for url in [
        "https://arttoyfamilia.com/collections/sonny-angel/products.json?limit=250",
        "https://blinkbox.com.au/collections/sonny-angel/products.json?limit=250",
    ]:
        try:
            products.extend(fetch_json(url).get("products", []))
        except Exception:
            pass

    candidates: list[dict] = []
    for p in products:
        title = p.get("title", "")
        imgs = [im.get("src") for im in p.get("images", []) if im.get("src")]
        if imgs:
            tl = title.lower()
            candidates.append({
                "title": title,
                "toks": tokens(title),
                "years": extract_years(title),
                "is_robby": "robby" in tl,
                "is_secret": any(k in tl for k in ("secret", "1/144", "2/144", "2/96", "1/96")),
                "is_hipper": "hipper" in tl,
                "img": imgs[0],
            })
        for v in p.get("variants", []):
            vimg = (v.get("featured_image") or {}).get("src")
            vtitle = v.get("title", "")
            if vimg and vtitle and vtitle != "Default Title":
                vt = f"{title} {vtitle}"
                vtl = vt.lower()
                candidates.append({
                    "title": vt,
                    "toks": tokens(vt),
                    "years": extract_years(vt),
                    "is_robby": "robby" in vtl,
                    "is_secret": "secret" in vtl or "robby" in vtl,
                    "is_hipper": "hipper" in vtl,
                    "img": vimg,
                })
    return candidates


def find_best_match(candidates: list[dict], col_id: str, name: str, series: str, rarity: str):
    is_robby = "robby" in name.lower() or "-robby" in col_id
    is_secret = rarity == "Secret"
    is_hipper = col_id.startswith("sonny-hip-")
    item_years = extract_years(f"{series} {name}")
    series_toks = tokens(series)
    name_toks = tokens(name) - {"robby"}

    best_score = 0.0
    best = None
    for c in candidates:
        if is_robby != c["is_robby"] or is_hipper != c["is_hipper"]:
            continue
        if is_secret and not is_robby and not c["is_secret"]:
            continue
        if item_years and c["years"] and not (item_years & c["years"]):
            continue
        if not series_toks:
            continue
        if "animal" in series_toks:
            nums = {"1", "2", "3", "4"}
            if (series_toks & nums) and not ((series_toks & nums) <= c["toks"]):
                continue

        s_overlap = len(series_toks & c["toks"])
        if s_overlap == 0:
            continue
        s_ratio = s_overlap / len(series_toks)
        if len(series_toks) >= 2 and s_ratio < 0.5:
            continue

        n_overlap = len(name_toks & c["toks"])
        score = s_ratio * 10.0 + s_overlap * 2.0 + n_overlap * 4.0
        if item_years and (item_years & c["years"]):
            score += 6.0
        if is_secret and c["is_secret"]:
            score += 3.0
        if any(bad in c["title"].lower() for bad in ("complete set", "assorted", "full case")):
            score -= 8.0

        if score > best_score:
            best_score = score
            best = c

    return best if best_score >= 12.0 else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace Sonny Angel SVG placeholders with real photos")
    parser.add_argument("--apply", action="store_true", help="Download photos and update TypeScript files")
    args = parser.parse_args()

    candidates = build_candidate_index()
    print(f"Indexed {len(candidates)} Shopify product/variant entries")

    matches: dict[str, dict] = {}
    for fpath in TS_FILES:
        txt = fpath.read_text(encoding="utf-8")
        for m in ITEM_SVG_RE.finditer(txt):
            iid, col_id, name, series, rarity, old_img = m.groups()
            if not col_id.startswith("sonny-"):
                continue
            best = find_best_match(candidates, col_id, name, series, rarity)
            if best:
                matches[iid] = {
                    "fpath": fpath,
                    "old_img": old_img,
                    "new_img": f"/images/{iid}.webp",
                    "url": best["img"],
                    "title": best["title"],
                }

    print(f"Matched {len(matches)} SVG items to real photos.")
    if not args.apply or not matches:
        for iid, info in list(matches.items())[:20]:
            print(f"  {iid} <= {info['title']}")
        return

    ok_ids: set[str] = set()
    with ThreadPoolExecutor(max_workers=14) as pool:
        futs = {
            pool.submit(
                download_and_normalize_image,
                info["url"],
                IMAGES_DIR / f"{iid}.webp",
                overwrite=True,
            ): iid
            for iid, info in matches.items()
        }
        for fut in as_completed(futs):
            iid = futs[fut]
            try:
                fut.result()
                ok_ids.add(iid)
            except Exception as exc:
                print(f"  FAIL {iid}: {exc}")

    for fpath in [*TS_FILES, DATA_DIR / "sonnyArchive.ts"]:
        txt = fpath.read_text(encoding="utf-8")
        changed = 0
        for iid in ok_ids:
            info = matches[iid]
            if info["old_img"] in txt:
                txt = txt.replace(info["old_img"], info["new_img"])
                changed += 1
        if changed:
            fpath.write_text(txt, encoding="utf-8")
            print(f"Updated {changed} paths in {fpath.name}")


if __name__ == "__main__":
    main()
