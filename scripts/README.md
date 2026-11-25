# Data Fetching & Verification Scripts

Python utilities used to fetch official product catalogs, download and normalize collectible photos (`512×512` centered `.webp` on white studio canvas), and verify asset integrity.

## Requirements

- Python 3.10+
- Pillow (`pip install pillow`)

## Scripts

- `common.py` — Shared HTTP fetching, FooGallery HTML parsing (`sonnyangel.com`), and Pillow image normalization helpers.
- `fetch_sonny_official.py` — Scrapes official Sonny Angel sections (Regular, Gift, Hippers, Limited, Unrefined `~2018`/`~2019`, Artist Collection, and Others/Special) from `sonnyangel.com`.
  ```bash
  python3 scripts/fetch_sonny_official.py                  # Dry-run summary
  python3 scripts/fetch_sonny_official.py --download       # Download missing WebP images
  ```
- `fetch_sonny_secrets_and_lucky.py` — Matches Sonny Angel Secrets, Robby Angels, Lucky Figures, and Vintage Seasonal figures against public collector Shopify feeds (`toysez.com`, `arttoyfamilia.com`, `blinkbox.com.au`) to replace any `.svg` placeholders with real photos.
  ```bash
  python3 scripts/fetch_sonny_secrets_and_lucky.py         # Preview matches
  python3 scripts/fetch_sonny_secrets_and_lucky.py --apply # Download & update public/data/*.json
  ```
- `apply_sonny_overrides.py` — Reproducible Sonny Angel Secret & Robby overrides (refined Regular Robbys with bases, base-less Unrefined Robbys & color-accurate SVGs, non-existent Unrefined Sweets Robby removal, Santa's Little Helper Secret/Robby, Dinosaur 2024 Secret/Robby).
  ```bash
  python3 scripts/apply_sonny_overrides.py          # Apply overrides using cached images
  python3 scripts/apply_sonny_overrides.py --force  # Re-download all pinned photos
  ```
- `fetch_tinytiny.py` — Fetches all POP MART TinyTiny series (*Prologue*, *Act I: Sugar Therapy Room*, *Mixed Series*, and *Standalone Figures*) with studio photos and regenerates `src/data/tinytiny.ts`.
  ```bash
  python3 scripts/fetch_tinytiny.py
  ```
- `fetch_skullpanda.py` — Fetches POP MART Skullpanda Blind Box series, Plush Pendant series, and Mixed-IP crossover sets with studio photos and regenerates `src/data/skullpanda.ts`.
  ```bash
  python3 scripts/fetch_skullpanda.py
  ```
- `fetch_jellycat.py` — Fetches official Jellycat plushies organized by series (*Amuseables*, *Bashful Bunnies*, *Blossom Bunnies*, *Bashful Animals*, *Bears & Bartholomew*, *Dragons*, *Smudge*, *Bag Charms*, *Animals & Friends*) and regenerates `src/data/jellycat.ts`.
  ```bash
  python3 scripts/fetch_jellycat.py
  ```
- `fetch_zsiga.py` — Fetches POP MART Zsiga Blind Box series, Mixed-IP sets, and Standalone figures with individual studio photos and regenerates `src/data/zsiga.ts`.
  ```bash
  python3 scripts/fetch_zsiga.py
  ```
- `fetch_sullivan_family.py` — Fetches Sylvanian Families Blind Bag series and Blind Box series (Doki Doki Collection, FamilyMart, Lottery) with individual studio photos and regenerates `src/data/sullivanFamily.ts`.
  ```bash
  python3 scripts/fetch_sullivan_family.py
  ```
- `build_calico_surprise_packs.py` — Maps North American Calico Critters Surprise Pack Series (Series 1–15 + Classic Surprise Packs) to the cached studio photos and generates `src/data/calicoCritters.ts`.
  ```bash
  python3 scripts/build_calico_surprise_packs.py
  ```
- `fetch_prices.py` — Unified pricing workflow: fetches live USD pricing from collector & retail Shopify feeds for all collectible shelves (`src/data/prices.ts`) **and** real TCGplayer Market Prices via `tcgcsv.com` for all English Pokémon TCG sets (`public/data/pokemon/*.json` + `src/data/pokemonSets.ts`).
  ```bash
  python3 scripts/fetch_prices.py                # All shelves + Pokémon TCGplayer prices
  python3 scripts/fetch_prices.py --pokemon-only # Pokémon TCGplayer prices only
  python3 scripts/fetch_prices.py --skip-pokemon # Non-Pokémon shelves only
  ```
- `fetch_pokemon_prices.py` — Standalone TCGplayer Market Price fetcher (invoked automatically by `fetch_prices.py`).
- `fetch_pokemon_tcg.py` — Clones `PokemonTCG/pokemon-tcg-data` (English sets only), expands Grand Master card variants (1st Edition / Reverse Holo / Master Ball), writes `src/data/pokemonSets.ts`, and outputs lazy-loaded per-set JSONs into `public/data/pokemon/`.
  ```bash
  python3 scripts/fetch_pokemon_tcg.py
  ```
- `verify_catalog.py` — Verifies that every image path referenced in `src/data/*.ts` exists in `public/images/` and is non-empty.
  ```bash
  python3 scripts/verify_catalog.py
  ```
