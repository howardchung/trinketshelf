#!/usr/bin/env python3
"""Verify that every catalog item image referenced in src/data/*.ts exists on disk."""

from __future__ import annotations

import re
import sys

from common import DATA_DIR, PROJECT_ROOT


def main() -> None:
    ts_files = sorted(DATA_DIR.glob("*.ts"))
    all_imgs: list[str] = []
    for path in ts_files:
        txt = path.read_text(encoding="utf-8")
        found = re.findall(r'"?image"?:\s*[\'"](/images/[^\'"]+)[\'"]', txt)
        all_imgs.extend(found)
        print(f"  {path.name:20s}: {len(found):4d} items")

    missing = [
        img
        for img in all_imgs
        if not (PROJECT_ROOT / "public" / img.lstrip("/")).is_file()
        or (PROJECT_ROOT / "public" / img.lstrip("/")).stat().st_size == 0
    ]
    svgs = [img for img in all_imgs if img.endswith(".svg")]

    print(
        f"\nTotal catalog items: {len(all_imgs)} | "
        f"WebP photos: {len(all_imgs) - len(svgs)} | "
        f"SVG portraits: {len(svgs)} | "
        f"Missing: {len(missing)}"
    )
    if missing:
        print("Missing files:", missing[:20])
        sys.exit(1)


if __name__ == "__main__":
    main()
