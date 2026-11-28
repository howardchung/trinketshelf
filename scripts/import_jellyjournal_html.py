#!/usr/bin/env python3
"""Import Jellycats from locally saved Jelly Journal HTML pages (jellycat/page_*.html).

- Upgrades matching existing .svg placeholders in public/data/jellycat.json to real
  Jelly Journal WebP photos (https://jellyjournal.com/assets/images/jellycats/...)
  and removes the replaced local .svg files.
- Appends all missing unique Jellycat plushies & bag charms (deduplicating size
  variants and skipping non-plush accessories like books, blankets, stickers, etc.).
- Records exact sourceUrl, imageSourceUrl, and priceSourceUrl on every item.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "jellycat"
JC_JSON = ROOT / "public" / "data" / "jellycat.json"
IMAGES_DIR = ROOT / "public" / "images"

CARD_RE = re.compile(
    r'<a\s+href="(/jellycat\.php\?sku=[^"]+)"\s+class="jellycat-link">.*?'
    r'<img\s+src="(/assets/images/jellycats/[^"]+)"\s+alt="([^"]+)"',
    re.S | re.I,
)

SIZE_RE = re.compile(
    r"\s*(?:[-–]\s*)?(?:Small|Medium|Large|Huge|Big|Little|Tiny|Really\s+Big|Gigantic|"
    r"Original|Mini|One\s+Size|Very\s+Big|Super|Extra\s+Large|XL|Baby)\s*$",
    re.I,
)

SKIP_NON_PLUSH = (
    "if i were",
    "book",
    "board book",
    "cloth book",
    "sticker",
    "blanket",
    "soother",
    "comforter",
    "blankie",
    "rattle",
    "ring rattle",
    "musical pull",
    "chime",
    "stroller",
    "bib",
    "booties",
    "socks",
    "decoration",
    "ornament",
    "bauble",
    "notebook",
    "journal",
    "puzzle",
    "gift bag",
    "tote",
    "pouch",
    "backpack",
    "handbag",
    "shoulder bag",
    "crossbody",
    "bum bag",
    "purse",
    "wallet",
    "pencil case",
    "cosmetic",
    "pin badge",
    "enamel pin",
    "mug",
    "cushion",
    "pillow",
    "playmat",
    "activity toy",
    "jiggle",
    "jitter",
    "grabber",
    "lovey",
    "robe",
    "slipper",
)


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def clean_name(raw: str) -> str:
    s = re.sub(r"[\U0001F1E6-\U0001F1FF]+", "", raw).strip()
    for _ in range(2):
        s = SIZE_RE.sub("", s).strip(" -–")
    s = re.sub(r"^Amuseable\s+", "Amuseables ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_key(s: str) -> str:
    s = s.lower()
    s = re.sub(r"^amuseables?\s+", "amuseables ", s)
    return slugify(s)


def classify_series(name: str) -> str:
    tl = name.lower()
    if "bag charm" in tl or "keychain" in tl or "key chain" in tl or "keyring" in tl:
        return "jc-bag-charms"
    if "amuseable" in tl or "amuseabean" in tl:
        return "jc-amuseables"
    if "blossom" in tl and "bunny" in tl:
        return "jc-blossom-bunnies"
    if "smudge" in tl:
        return "jc-smudge"
    if "dragon" in tl:
        return "jc-dragons"
    if "bashful" in tl and "bunny" in tl:
        return "jc-bashful-bunnies"
    if "bashful" in tl:
        return "jc-bashful-animals"
    if "bartholomew" in tl or " bear" in tl or tl.endswith("bear"):
        return "jc-bears"
    return "jc-animals"


def main() -> None:
    pages = sorted(HTML_DIR.glob("page_*.html"))
    if not pages:
        raise SystemExit(f"No HTML pages found in {HTML_DIR}")

    unique: dict[str, tuple[str, str, str]] = {}
    raw_count = 0
    for p in pages:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for m in CARD_RE.finditer(txt):
            raw_count += 1
            sku_href = m.group(1)
            img_src = m.group(2)
            alt = html.unescape(m.group(3)).strip()
            cname = clean_name(alt)
            if not cname or len(cname) < 3:
                continue
            k = norm_key(cname)
            if k not in unique:
                unique[k] = (cname, sku_href, img_src)

    jc = json.loads(JC_JSON.read_text(encoding="utf-8"))
    if not any(c["id"] == "jc-accessories" for c in jc["collections"]):
        jc["collections"].append({
            "id": "jc-accessories",
            "name": "Jellycat · Accessories, Bags & Books",
            "shortName": "Accessories, Bags & Books",
            "subtitle": "Bags, Books, Pins, Stickers & Baby Gear (0)",
            "maker": "Jellycat London",
            "accent": "#9B6BB8",
            "accentSoft": "#F4EEFA",
            "accentText": "#5E3478",
            "emoji": "🎒",
        })
    col_label = {c["id"]: c["shortName"] for c in jc["collections"]}
    used_ids = {it["id"] for it in jc["items"]}
    existing_by_key = {norm_key(it["name"]): it for it in jc["items"]}

    upgraded_svgs = 0
    added = 0
    added_acc = 0

    for k, (cname, sku_href, img_src) in unique.items():
        # URL-encode any spaces or quotes in the image path while keeping slashes
        encoded_img_path = urllib.parse.quote(html.unescape(img_src), safe="/:@")
        full_img_url = f"https://jellyjournal.com{encoded_img_path}"
        full_src_url = f"https://jellyjournal.com{sku_href}"

        # 1. Upgrade existing SVG placeholder if matched
        if k in existing_by_key:
            it = existing_by_key[k]
            if it["image"].endswith(".svg"):
                old_svg = IMAGES_DIR / Path(it["image"]).name
                if old_svg.exists():
                    old_svg.unlink()
                it["image"] = full_img_url
                it["imageSourceUrl"] = full_img_url
                it["sourceUrl"] = full_src_url
                upgraded_svgs += 1
            continue

        # 2. Route non-plush accessories into jc-accessories instead of skipping
        tl = cname.lower()
        is_acc = any(bad in tl for bad in SKIP_NON_PLUSH) or tl.endswith(" bag")
        cid = "jc-accessories" if is_acc else classify_series(cname)
        base_id = f"{cid}-{k}"
        iid = base_id
        n = 2
        while iid in used_ids:
            iid = f"{base_id}-{n}"
            n += 1
        used_ids.add(iid)

        rarity = (
            "Special"
            if any(w in tl for w in ("luxe", "limited", "christmas", "valentine", "halloween", "john lewis", "exclusive", "selfridges"))
            else "Regular"
        )
        jc["items"].append({
            "id": iid,
            "collectionId": cid,
            "name": cname,
            "series": col_label[cid],
            "rarity": rarity,
            "image": full_img_url,
            "sourceUrl": full_src_url,
            "imageSourceUrl": full_img_url,
            "priceSourceUrl": f"https://us.jellycat.com/search?q={urllib.parse.quote(cname)}",
        })
        added += 1
        if is_acc:
            added_acc += 1

    # Update collection subtitles with new counts
    for c in jc["collections"]:
        cnt = sum(1 for it in jc["items"] if it["collectionId"] == c["id"])
        c["subtitle"] = re.sub(r"\(\d+\)$", f"({cnt})", c["subtitle"])

    JC_JSON.write_text(json.dumps(jc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    rem_svg = sum(1 for it in jc["items"] if it["image"].endswith(".svg"))
    print(
        f"Parsed {len(pages)} pages ({raw_count} raw cards -> {len(unique)} unique). "
        f"Upgraded {upgraded_svgs} SVGs, added {added} items ({added_acc} accessories). "
        f"Jellycat total: {len(jc['items'])} ({rem_svg} SVGs remaining)."
    )
    for c in jc["collections"]:
        cnt = sum(1 for it in jc["items"] if it["collectionId"] == c["id"])
        print(f"  {c['shortName']:24s}: {cnt}")


if __name__ == "__main__":
    main()
