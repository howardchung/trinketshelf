#!/usr/bin/env python3
"""Bundle public/data/pokemon/*.json into a single public/data/pokemon-cards.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"


def main() -> None:
    sets = json.loads((DATA_DIR / "pokemon-sets.json").read_text(encoding="utf-8"))
    all_cards: list[dict] = []
    for s in sets:
        sid = s["id"].replace("pkmn-", "")
        p = DATA_DIR / "pokemon" / f"{sid}.json"
        if p.is_file():
            all_cards.extend(json.loads(p.read_text(encoding="utf-8")))

    out = DATA_DIR / "pokemon-cards.json"
    out.write_text(json.dumps(all_cards, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Bundled {len(all_cards)} Pokémon cards into {out.name} ({out.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
