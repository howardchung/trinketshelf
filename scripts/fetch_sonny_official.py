#!/usr/bin/env python3
"""Fetch official Sonny Angel catalogs & studio photos from sonnyangel.com.

Sources:
  - Regular & Unrefined (~2018/~2019): https://www.sonnyangel.com/en/products/
  - Gift Regular Series:               https://www.sonnyangel.com/en/products/mini-figure-gift/
  - Hippers Series:                    https://www.sonnyangel.com/en/products/mini-figure-hippers/
  - Limited Series:                    https://www.sonnyangel.com/en/products/mini-figure-limited/
  - Artist Collection:                 https://www.sonnyangel.com/en/products/artist-collection/
  - Special / Others:                  https://www.sonnyangel.com/en/products/others/

Run with `--download` to download/refresh normalized 512x512 WebP photos into public/images/.
Without flags, prints a summary of all series and figure counts found on sonnyangel.com.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import IMAGES_DIR, download_and_normalize_image, scrape_sonnyangel_tabs, slugify

SOURCES = {
    "regular": "https://www.sonnyangel.com/en/products/",
    "gift": "https://www.sonnyangel.com/en/products/mini-figure-gift/",
    "hippers": "https://www.sonnyangel.com/en/products/mini-figure-hippers/",
    "limited": "https://www.sonnyangel.com/en/products/mini-figure-limited/",
    "artist": "https://www.sonnyangel.com/en/products/artist-collection/",
    "others": "https://www.sonnyangel.com/en/products/others/",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official Sonny Angel catalogs from sonnyangel.com")
    parser.add_argument(
        "--section",
        choices=[*SOURCES.keys(), "all"],
        default="all",
        help="Which official sonnyangel.com section to inspect/fetch (default: all)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download and normalize studio images into public/images/",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing images when --download is set",
    )
    args = parser.parse_args()

    sections = list(SOURCES.keys()) if args.section == "all" else [args.section]
    tasks: list[tuple[str, str]] = []

    for sec in sections:
        tabs = scrape_sonnyangel_tabs(SOURCES[sec])
        total = sum(len(v) for v in tabs.values())
        print(f"[{sec}] {len(tabs)} series, {total} figures")
        for series_title, figs in tabs.items():
            prefix = f"sonny-{sec[:3]}-{slugify(series_title)}"
            for idx, (name, img_url) in enumerate(figs, 1):
                fig_slug = slugify(name) if name else f"figure-{idx}"
                tasks.append((f"{prefix}-{fig_slug}", img_url))

    if not args.download:
        print(f"\nFound {len(tasks)} total official figure images. Re-run with --download to save WebP files.")
        return

    ok = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=14) as pool:
        futs = {
            pool.submit(
                download_and_normalize_image,
                url,
                IMAGES_DIR / f"{iid}.webp",
                overwrite=args.overwrite,
            ): iid
            for iid, url in tasks
        }
        for fut in as_completed(futs):
            try:
                fut.result()
                ok += 1
            except Exception as exc:
                failed += 1
                print(f"  FAIL {futs[fut]}: {exc}")

    print(f"Downloaded {ok}/{len(tasks)} images (failed: {failed})")


if __name__ == "__main__":
    main()
