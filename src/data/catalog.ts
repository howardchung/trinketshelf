import type { CatalogItem, CollectionId, CollectionMeta, TopLevelShelfId } from '../types';
import {
  POKEMON_SETS,
  POKEMON_TOTAL_GM_CARDS,
  setPokemonSets,
  type PokemonSetMeta,
} from './pokemonSets';
import { setItemPrices } from './prices';

export interface TopLevelShelfMeta {
  id: TopLevelShelfId;
  name: string;
  subtitle: string;
  maker: string;
  accent: string;
  accentSoft: string;
  accentText: string;
  emoji: string;
  collectionIds: CollectionId[];
}

interface ShelfJson {
  collections: CollectionMeta[];
  items: CatalogItem[];
}

interface SonnyArchiveJson {
  unrefinedCollections: CollectionMeta[];
  unrefinedItems: CatalogItem[];
  artistCollections: CollectionMeta[];
  artistItems: CatalogItem[];
  specialCollections: CollectionMeta[];
  specialItems: CatalogItem[];
}

export const SONNY_REGULAR_IDS: CollectionId[] = [];
export const SONNY_LIMITED_IDS: CollectionId[] = [];
export const SONNY_HIPPERS_IDS: CollectionId[] = [];
export const SONNY_UNREFINED_IDS: CollectionId[] = [];
export const SONNY_ARTIST_IDS: CollectionId[] = [];
export const SONNY_SPECIAL_IDS: CollectionId[] = [];
export const SONNY_VINTAGE_IDS: CollectionId[] = [];
export const SONNY_SERIES_IDS: CollectionId[] = [];

export const SKULLPANDA_SERIES_IDS: CollectionId[] = [];
export const TINYTINY_SERIES_IDS: CollectionId[] = [];
export const JELLYCAT_SERIES_IDS: CollectionId[] = [];
export const ZSIGA_SERIES_IDS: CollectionId[] = [];
export const SULLIVAN_SERIES_IDS: CollectionId[] = [];
export const CALICO_SERIES_IDS: CollectionId[] = [];
export const POKEMON_SERIES_IDS: CollectionId[] = [];

export const TOP_LEVEL_SHELVES: TopLevelShelfMeta[] = [];
export const COLLECTIONS: CollectionMeta[] = [];
export const DEFAULT_ITEMS: CatalogItem[] = [];

function replaceArray<T>(target: T[], next: T[]): void {
  target.length = 0;
  target.push(...next);
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to load ${url} (${res.status})`);
  }
  return (await res.json()) as T;
}

let loadedPromise: Promise<void> | null = null;

export function loadAllCatalogData(): Promise<void> {
  if (loadedPromise) return loadedPromise;

  loadedPromise = (async () => {
    const [
      sonnyReg,
      sonnyHippers,
      sonnyLimited,
      sonnyVintage,
      sonnyArchive,
      skullpanda,
      tinytiny,
      calico,
      sylvanian,
      zsiga,
      jellycat,
      pokemonSets,
      prices,
    ] = await Promise.all([
      fetchJson<ShelfJson>('/data/sonny-regular.json'),
      fetchJson<ShelfJson>('/data/sonny-hippers.json'),
      fetchJson<ShelfJson>('/data/sonny-limited.json'),
      fetchJson<ShelfJson>('/data/sonny-vintage.json'),
      fetchJson<SonnyArchiveJson>('/data/sonny-archive.json'),
      fetchJson<ShelfJson>('/data/skullpanda.json'),
      fetchJson<ShelfJson>('/data/tinytiny.json'),
      fetchJson<ShelfJson>('/data/calico-critters.json'),
      fetchJson<ShelfJson>('/data/sylvanian-families.json'),
      fetchJson<ShelfJson>('/data/zsiga.json'),
      fetchJson<ShelfJson>('/data/jellycat.json'),
      fetchJson<PokemonSetMeta[]>('/data/pokemon-sets.json'),
      fetchJson<Record<string, number>>('/data/prices.json'),
    ]);

    setPokemonSets(pokemonSets);
    setItemPrices(prices);

    replaceArray(SONNY_REGULAR_IDS, sonnyReg.collections.map((c) => c.id));
    replaceArray(SONNY_HIPPERS_IDS, sonnyHippers.collections.map((c) => c.id));
    replaceArray(SONNY_LIMITED_IDS, sonnyLimited.collections.map((c) => c.id));
    replaceArray(SONNY_VINTAGE_IDS, sonnyVintage.collections.map((c) => c.id));
    replaceArray(SONNY_UNREFINED_IDS, sonnyArchive.unrefinedCollections.map((c) => c.id));
    replaceArray(SONNY_ARTIST_IDS, sonnyArchive.artistCollections.map((c) => c.id));
    replaceArray(SONNY_SPECIAL_IDS, sonnyArchive.specialCollections.map((c) => c.id));
    replaceArray(SONNY_SERIES_IDS, [
      ...SONNY_REGULAR_IDS,
      ...SONNY_HIPPERS_IDS,
      ...SONNY_LIMITED_IDS,
      ...SONNY_VINTAGE_IDS,
      ...SONNY_UNREFINED_IDS,
      ...SONNY_ARTIST_IDS,
      ...SONNY_SPECIAL_IDS,
    ]);

    replaceArray(SKULLPANDA_SERIES_IDS, skullpanda.collections.map((c) => c.id));
    replaceArray(TINYTINY_SERIES_IDS, tinytiny.collections.map((c) => c.id));
    replaceArray(CALICO_SERIES_IDS, calico.collections.map((c) => c.id));
    replaceArray(SULLIVAN_SERIES_IDS, sylvanian.collections.map((c) => c.id));
    replaceArray(ZSIGA_SERIES_IDS, zsiga.collections.map((c) => c.id));
    replaceArray(JELLYCAT_SERIES_IDS, jellycat.collections.map((c) => c.id));
    replaceArray(POKEMON_SERIES_IDS, POKEMON_SETS.map((s) => s.id));

    replaceArray(TOP_LEVEL_SHELVES, [
      {
        id: 'sonny-angel',
        name: 'Sonny Angel',
        subtitle: `${SONNY_SERIES_IDS.length} Official Series · Regular, Hippers, Limited, Unrefined & Artist`,
        maker: 'Dreams Inc.',
        accent: '#E86A7D',
        accentSoft: '#FDECEF',
        accentText: '#A83247',
        emoji: '🍓',
        collectionIds: SONNY_SERIES_IDS,
      },
      {
        id: 'skullpanda',
        name: 'Skullpanda',
        subtitle: `${SKULLPANDA_SERIES_IDS.length} Series · Blind Boxes, Plush Pendants & Mixed Sets`,
        maker: 'POP MART',
        accent: '#7C65B8',
        accentSoft: '#F1EEFA',
        accentText: '#4D3885',
        emoji: '🌙',
        collectionIds: SKULLPANDA_SERIES_IDS,
      },
      {
        id: 'tinytiny',
        name: 'Tinytiny',
        subtitle: '2 Blind Box Series · Mixed Series · Standalone Figures',
        maker: 'POP MART',
        accent: '#4F94A8',
        accentSoft: '#EAF5F8',
        accentText: '#2A6070',
        emoji: '🔑',
        collectionIds: TINYTINY_SERIES_IDS,
      },
      {
        id: 'calico-critters',
        name: 'Calico Critters',
        subtitle: `${CALICO_SERIES_IDS.length} Surprise Pack Series · Baby Collectibles`,
        maker: 'Epoch',
        accent: '#D98A4E',
        accentSoft: '#FDF2E8',
        accentText: '#915221',
        emoji: '🎻',
        collectionIds: CALICO_SERIES_IDS,
      },
      {
        id: 'sullivan-family',
        name: 'Sylvanian Families',
        subtitle: `${SULLIVAN_SERIES_IDS.length} Series · Blind Bags & Blind Boxes`,
        maker: 'Epoch',
        accent: '#639A67',
        accentSoft: '#EDF6EE',
        accentText: '#356338',
        emoji: '🌼',
        collectionIds: SULLIVAN_SERIES_IDS,
      },
      {
        id: 'zsiga',
        name: 'Zsiga',
        subtitle: `${ZSIGA_SERIES_IDS.length} Series · Blind Boxes, Mixed Sets & Standalone Figures`,
        maker: 'POP MART',
        accent: '#C97B63',
        accentSoft: '#FAF0EC',
        accentText: '#874532',
        emoji: '🦊',
        collectionIds: ZSIGA_SERIES_IDS,
      },
      {
        id: 'jellycat',
        name: 'Jellycat',
        subtitle: `${JELLYCAT_SERIES_IDS.length} Series · Amuseables, Bashful, Bears, Dragons & More`,
        maker: 'Jellycat London',
        accent: '#5C85B8',
        accentSoft: '#ECF2FA',
        accentText: '#315482',
        emoji: '🥐',
        collectionIds: JELLYCAT_SERIES_IDS,
      },
      {
        id: 'pokemon-tcg',
        name: 'Pokémon TCG',
        subtitle: `${POKEMON_SETS.length} Sets · ${POKEMON_TOTAL_GM_CARDS.toLocaleString()} Grand Master Cards`,
        maker: 'The Pokémon Company',
        accent: '#D94862',
        accentSoft: '#FDECEF',
        accentText: '#8F2237',
        emoji: '⚡',
        collectionIds: POKEMON_SERIES_IDS,
      },
    ]);

    replaceArray(COLLECTIONS, [
      ...sonnyReg.collections,
      ...sonnyHippers.collections,
      ...sonnyLimited.collections,
      ...sonnyVintage.collections,
      ...sonnyArchive.unrefinedCollections,
      ...sonnyArchive.artistCollections,
      ...sonnyArchive.specialCollections,
      ...skullpanda.collections,
      ...tinytiny.collections,
      ...calico.collections,
      ...sylvanian.collections,
      ...zsiga.collections,
      ...jellycat.collections,
      ...POKEMON_SETS,
    ]);

    replaceArray(DEFAULT_ITEMS, [
      ...sonnyReg.items,
      ...sonnyHippers.items,
      ...sonnyLimited.items,
      ...sonnyVintage.items,
      ...sonnyArchive.unrefinedItems,
      ...sonnyArchive.artistItems,
      ...sonnyArchive.specialItems,
      ...skullpanda.items,
      ...tinytiny.items,
      ...calico.items,
      ...sylvanian.items,
      ...zsiga.items,
      ...jellycat.items,
    ]);
  })();

  return loadedPromise;
}
