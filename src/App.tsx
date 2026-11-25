import { type ChangeEvent, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  Download,
  LayoutGrid,
  Plus,
  Search,
  Sparkles,
  Upload,
  WifiOff,
  Smartphone,
} from 'lucide-react';
import {
  CALICO_SERIES_IDS,
  COLLECTIONS,
  JELLYCAT_SERIES_IDS,
  SKULLPANDA_SERIES_IDS,
  SONNY_ARTIST_IDS,
  SONNY_HIPPERS_IDS,
  SONNY_LIMITED_IDS,
  SONNY_REGULAR_IDS,
  SONNY_SERIES_IDS,
  SONNY_SPECIAL_IDS,
  SONNY_UNREFINED_IDS,
  SONNY_VINTAGE_IDS,
  SULLIVAN_SERIES_IDS,
  TINYTINY_SERIES_IDS,
  TOP_LEVEL_SHELVES,
  ZSIGA_SERIES_IDS,
} from './data/catalog';
import { POKEMON_SETS, POKEMON_TOTAL_GM_CARDS, type PokemonSetMeta } from './data/pokemonSets';
import { formatUsdWhole, getItemPrice } from './data/prices';
import { useCollectionStore } from './hooks/useCollectionStore';
import { usePokemonSetLoader } from './hooks/usePokemonSetLoader';
import { usePwaInstall } from './hooks/usePwaInstall';
import type { CatalogItem, CollectionId, ItemStatus, TopLevelShelfId } from './types';
import { CollectionOverview, type OverviewCardGroup } from './components/CollectionOverview';
import { PokemonSetsOverview } from './components/PokemonSetsOverview';
import { ItemCard } from './components/ItemCard';
import { ItemDetailModal } from './components/ItemDetailModal';
import { AddItemModal } from './components/AddItemModal';

type ActiveShelf = 'overview' | TopLevelShelfId;
type ActiveSubSeries = 'all' | CollectionId;
type SonnySeriesTab = 'all' | 'regular' | 'hippers' | 'limited' | 'vintage' | 'unrefined' | 'artist' | 'special';
type SkullpandaTab = 'all' | 'blind-box' | 'plush' | 'mixed';
type SullivanTab = 'all' | 'blind-bag' | 'blind-box';
type PokemonEraTab =
  | 'all'
  | 'Simplified Chinese'
  | 'Mega Evolution'
  | 'Scarlet & Violet'
  | 'Sword & Shield'
  | 'Sun & Moon'
  | 'XY'
  | 'Black & White'
  | 'dp-hgss'
  | 'ex-ecard'
  | 'classic'
  | 'other';
type StatusFilter = 'all' | ItemStatus;

function matchesPokemonEra(s: PokemonSetMeta, tab: PokemonEraTab): boolean {
  if (tab === 'all') return true;
  if (tab === 'dp-hgss') {
    return s.era === 'Diamond & Pearl' || s.era === 'Platinum' || s.era === 'HeartGold & SoulSilver';
  }
  if (tab === 'ex-ecard') {
    return s.era === 'EX' || s.era === 'E-Card';
  }
  if (tab === 'classic') {
    return s.era === 'Base' || s.era === 'Gym' || s.era === 'Neo';
  }
  if (tab === 'other') {
    return s.era === 'POP' || s.era === 'NP' || s.era === 'Other';
  }
  return s.era === tab;
}

const SONNY_ID_SET = new Set<CollectionId>(SONNY_SERIES_IDS);
const SONNY_REGULAR_SET = new Set<CollectionId>(SONNY_REGULAR_IDS);
const SONNY_HIPPERS_SET = new Set<CollectionId>(SONNY_HIPPERS_IDS);
const SONNY_LIMITED_SET = new Set<CollectionId>(SONNY_LIMITED_IDS);
const SONNY_VINTAGE_SET = new Set<CollectionId>(SONNY_VINTAGE_IDS);
const SONNY_UNREFINED_SET = new Set<CollectionId>(SONNY_UNREFINED_IDS);
const SONNY_ARTIST_SET = new Set<CollectionId>(SONNY_ARTIST_IDS);
const SONNY_SPECIAL_SET = new Set<CollectionId>(SONNY_SPECIAL_IDS);
const SKULLPANDA_ID_SET = new Set<CollectionId>(SKULLPANDA_SERIES_IDS);
const TINYTINY_ID_SET = new Set<CollectionId>(TINYTINY_SERIES_IDS);
const JELLYCAT_ID_SET = new Set<CollectionId>(JELLYCAT_SERIES_IDS);
const ZSIGA_ID_SET = new Set<CollectionId>(ZSIGA_SERIES_IDS);
const SULLIVAN_ID_SET = new Set<CollectionId>(SULLIVAN_SERIES_IDS);
const CALICO_ID_SET = new Set<CollectionId>(CALICO_SERIES_IDS);

export default function App() {
  const {
    allItems,
    trackingMap,
    getTracking,
    updateTracking,
    toggleStatusQuick,
    addCustomItem,
    deleteCustomItem,
    exportJson,
    importJson,
  } = useCollectionStore();

  const { canInstall, isOnline, promptInstall } = usePwaInstall();

  const [activeShelf, setActiveShelf] = useState<ActiveShelf>('overview');
  const [activeSubSeries, setActiveSubSeries] = useState<ActiveSubSeries>('all');
  const [sonnySeriesTab, setSonnySeriesTab] = useState<SonnySeriesTab>('all');
  const [skullpandaTab, setSkullpandaTab] = useState<SkullpandaTab>('all');
  const [sullivanTab, setSullivanTab] = useState<SullivanTab>('all');
  const [pokemonEraTab, setPokemonEraTab] = useState<PokemonEraTab>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [secretOnly, setSecretOnly] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activePokemonSetId =
    activeShelf === 'pokemon-tcg' && activeSubSeries !== 'all'
      ? activeSubSeries.replace(/^pkmn-/, '')
      : null;

  const { cards: pokemonCards, loading: pokemonLoading } =
    usePokemonSetLoader(activePokemonSetId);

  const pokemonOwnedTotal = useMemo(() => {
    let count = 0;
    for (const [itemId, tr] of Object.entries(trackingMap)) {
      if (itemId.startsWith('pkmn-') && (tr.status === 'owned' || tr.status === 'duplicate')) {
        count++;
      }
    }
    return count;
  }, [trackingMap]);

  const pokemonSetsInEra = useMemo(
    () => POKEMON_SETS.filter((s) => matchesPokemonEra(s, pokemonEraTab)),
    [pokemonEraTab]
  );

  const filteredPokemonSets = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return pokemonSetsInEra;
    return pokemonSetsInEra.filter((s) =>
      `${s.shortName} ${s.era} ${s.setId} ${s.releaseDate}`.toLowerCase().includes(q)
    );
  }, [pokemonSetsInEra, searchQuery]);

  const showToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2600);
  };

  const activeTopShelf = useMemo(
    () =>
      activeShelf === 'overview'
        ? null
        : TOP_LEVEL_SHELVES.find((s) => s.id === activeShelf) ?? null,
    [activeShelf]
  );

  const isGroupedShelf = activeShelf !== 'overview';

  const activeSubCollection = useMemo(
    () =>
      isGroupedShelf && activeSubSeries !== 'all'
        ? COLLECTIONS.find((c) => c.id === activeSubSeries) ?? null
        : null,
    [isGroupedShelf, activeSubSeries]
  );

  const subSeriesGroups = useMemo<OverviewCardGroup<CollectionId>[]>(() => {
    if (activeShelf === 'skullpanda') {
      return COLLECTIONS.filter((c) => {
        if (!SKULLPANDA_ID_SET.has(c.id)) return false;
        if (skullpandaTab === 'all') return true;
        return c.skullpandaCategory === skullpandaTab;
      }).map((c) => ({
        id: c.id,
        name: c.shortName ?? c.name.replace(/^Skullpanda · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    if (activeShelf === 'calico-critters') {
      return COLLECTIONS.filter((c) => CALICO_ID_SET.has(c.id)).map((c) => ({
        id: c.id,
        name: c.shortName ?? c.name.replace(/^Calico Critters · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    if (activeShelf === 'sullivan-family') {
      return COLLECTIONS.filter((c) => {
        if (!SULLIVAN_ID_SET.has(c.id)) return false;
        if (sullivanTab === 'all') return true;
        return c.sullivanCategory === sullivanTab;
      }).map((c) => ({
        id: c.id,
        name: c.shortName ?? c.name.replace(/^Sylvanian Families · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    if (activeShelf === 'zsiga') {
      return COLLECTIONS.filter((c) => ZSIGA_ID_SET.has(c.id)).map((c) => ({
        id: c.id,
        name: c.shortName ?? c.name.replace(/^Zsiga · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    if (activeShelf === 'jellycat') {
      return COLLECTIONS.filter((c) => JELLYCAT_ID_SET.has(c.id)).map((c) => ({
        id: c.id,
        name: c.shortName ?? c.name.replace(/^Jellycat · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    if (activeShelf === 'tinytiny') {
      return COLLECTIONS.filter((c) => TINYTINY_ID_SET.has(c.id)).map((c) => ({
        id: c.id,
        name: c.shortName ?? c.name.replace(/^Tinytiny · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    if (activeShelf === 'sonny-angel') {
      return COLLECTIONS.filter((c) => {
        if (!SONNY_ID_SET.has(c.id)) return false;
        if (sonnySeriesTab === 'regular') return SONNY_REGULAR_SET.has(c.id);
        if (sonnySeriesTab === 'hippers') return SONNY_HIPPERS_SET.has(c.id);
        if (sonnySeriesTab === 'limited') return SONNY_LIMITED_SET.has(c.id);
        if (sonnySeriesTab === 'vintage') return SONNY_VINTAGE_SET.has(c.id);
        if (sonnySeriesTab === 'unrefined') return SONNY_UNREFINED_SET.has(c.id);
        if (sonnySeriesTab === 'artist') return SONNY_ARTIST_SET.has(c.id);
        if (sonnySeriesTab === 'special') return SONNY_SPECIAL_SET.has(c.id);
        return true;
      }).map((c) => ({
        id: c.id,
        name: c.name.replace(/^(?:Sonny Angel|Artist Collection) · /, ''),
        subtitle: c.subtitle,
        maker: c.maker,
        accent: c.accent,
        accentSoft: c.accentSoft,
        accentText: c.accentText,
        emoji: c.emoji,
        collectionIds: [c.id],
      }));
    }
    return [];
  }, [activeShelf, sonnySeriesTab, skullpandaTab, sullivanTab]);

  const scopedCollectionIds = useMemo<Set<CollectionId> | null>(() => {
    if (activeShelf === 'overview') return null;
    if (activeShelf === 'calico-critters') {
      return activeSubSeries !== 'all'
        ? new Set<CollectionId>([activeSubSeries])
        : CALICO_ID_SET;
    }
    if (activeShelf === 'sullivan-family') {
      if (activeSubSeries !== 'all') return new Set<CollectionId>([activeSubSeries]);
      if (sullivanTab === 'all') return SULLIVAN_ID_SET;
      return new Set<CollectionId>(
        COLLECTIONS.filter((c) => SULLIVAN_ID_SET.has(c.id) && c.sullivanCategory === sullivanTab).map(
          (c) => c.id
        )
      );
    }
    if (activeShelf === 'skullpanda') {
      if (activeSubSeries !== 'all') return new Set<CollectionId>([activeSubSeries]);
      if (skullpandaTab === 'all') return SKULLPANDA_ID_SET;
      return new Set<CollectionId>(
        COLLECTIONS.filter((c) => SKULLPANDA_ID_SET.has(c.id) && c.skullpandaCategory === skullpandaTab).map(
          (c) => c.id
        )
      );
    }
    if (activeShelf === 'zsiga') {
      return activeSubSeries !== 'all'
        ? new Set<CollectionId>([activeSubSeries])
        : ZSIGA_ID_SET;
    }
    if (activeShelf === 'jellycat') {
      return activeSubSeries !== 'all'
        ? new Set<CollectionId>([activeSubSeries])
        : JELLYCAT_ID_SET;
    }
    if (activeShelf === 'tinytiny') {
      return activeSubSeries !== 'all'
        ? new Set<CollectionId>([activeSubSeries])
        : TINYTINY_ID_SET;
    }
    if (activeShelf === 'sonny-angel') {
      if (activeSubSeries !== 'all') {
        return new Set<CollectionId>([activeSubSeries]);
      }
      if (sonnySeriesTab === 'regular') return SONNY_REGULAR_SET;
      if (sonnySeriesTab === 'hippers') return SONNY_HIPPERS_SET;
      if (sonnySeriesTab === 'limited') return SONNY_LIMITED_SET;
      if (sonnySeriesTab === 'vintage') return SONNY_VINTAGE_SET;
      if (sonnySeriesTab === 'unrefined') return SONNY_UNREFINED_SET;
      if (sonnySeriesTab === 'artist') return SONNY_ARTIST_SET;
      if (sonnySeriesTab === 'special') return SONNY_SPECIAL_SET;
      return SONNY_ID_SET;
    }
    return new Set<CollectionId>([activeShelf as CollectionId]);
  }, [activeShelf, activeSubSeries, sonnySeriesTab, skullpandaTab, sullivanTab]);

  const stats = useMemo(() => {
    if (activeShelf === 'pokemon-tcg' && activeSubSeries === 'all') {
      const setIdSet = new Set(pokemonSetsInEra.map((s) => s.setId));
      const total = pokemonSetsInEra.reduce((sum, s) => sum + s.grandMasterCount, 0);
      let owned = 0;
      let wishlist = 0;
      let duplicate = 0;
      let dupExtraCopies = 0;
      let ownedValue = 0;
      let dupValue = 0;
      let wishlistValue = 0;

      for (const [itemId, tr] of Object.entries(trackingMap)) {
        if (!itemId.startsWith('pkmn-')) continue;
        const rest = itemId.slice(5);
        const dash = rest.indexOf('-');
        const sid = dash > 0 ? rest.slice(0, dash) : '';
        if (!setIdSet.has(sid)) continue;
        const price = tr.customPrice ?? tr.cachedPrice ?? 1;
        if (tr.status === 'owned') {
          owned++;
          const qty = Math.max(1, tr.quantity || 1);
          ownedValue += price * qty;
          if (qty > 1) {
            dupExtraCopies += qty - 1;
            dupValue += price * (qty - 1);
          }
        } else if (tr.status === 'duplicate') {
          owned++;
          duplicate++;
          const qty = Math.max(2, tr.quantity || 2);
          ownedValue += price * qty;
          dupExtraCopies += qty - 1;
          dupValue += price * (qty - 1);
        } else if (tr.status === 'wishlist') {
          wishlist++;
          wishlistValue += price;
        }
      }
      const remainingCount = wishlist;
      const costToComplete = wishlistValue;
      const pct = total > 0 ? Math.round((owned / total) * 100) : 0;
      return {
        total,
        owned,
        wishlist,
        duplicate,
        dupExtraCopies,
        pct,
        ownedValue,
        dupValue,
        wishlistValue,
        costToComplete,
        remainingCount,
      };
    }

    const scope =
      activeShelf === 'pokemon-tcg' && activeSubSeries !== 'all'
        ? [
            ...pokemonCards,
            ...allItems.filter((i) => i.collectionId === activeSubSeries),
          ]
        : scopedCollectionIds
        ? allItems.filter((i) => scopedCollectionIds.has(i.collectionId))
        : allItems;
    let owned = 0;
    let wishlist = 0;
    let duplicate = 0;
    let dupExtraCopies = 0;
    let ownedValue = 0;
    let dupValue = 0;
    let wishlistValue = 0;
    let costToComplete = 0;
    let remainingCount = 0;
    for (const item of scope) {
      const tr = getTracking(item.id);
      const st = tr.status;
      const price = getItemPrice(item.id, tr.customPrice, item.price);
      if (st === 'owned') {
        owned++;
        const qty = Math.max(1, tr.quantity || 1);
        ownedValue += price * qty;
        if (qty > 1) {
          dupExtraCopies += qty - 1;
          dupValue += price * (qty - 1);
        }
      } else if (st === 'duplicate') {
        owned++;
        duplicate++;
        const qty = Math.max(2, tr.quantity || 2);
        const extras = qty - 1;
        ownedValue += price * qty;
        dupExtraCopies += extras;
        dupValue += price * extras;
      } else if (st === 'wishlist') {
        wishlist++;
        wishlistValue += price;
        remainingCount++;
        costToComplete += price;
      }
    }
    let total = scope.length;
    if (activeShelf === 'overview') {
      for (const [itemId, tr] of Object.entries(trackingMap)) {
        if (!itemId.startsWith('pkmn-')) continue;
        const price = tr.customPrice ?? tr.cachedPrice ?? 1;
        if (tr.status === 'owned') {
          owned++;
          const qty = Math.max(1, tr.quantity || 1);
          ownedValue += price * qty;
          if (qty > 1) {
            dupExtraCopies += qty - 1;
            dupValue += price * (qty - 1);
          }
        } else if (tr.status === 'duplicate') {
          owned++;
          duplicate++;
          const qty = Math.max(2, tr.quantity || 2);
          ownedValue += price * qty;
          dupExtraCopies += qty - 1;
          dupValue += price * (qty - 1);
        } else if (tr.status === 'wishlist') {
          wishlist++;
          wishlistValue += price;
          remainingCount++;
          costToComplete += price;
        }
      }
      total += POKEMON_TOTAL_GM_CARDS;
    }
    const pct = total > 0 ? Math.round((owned / total) * 100) : 0;
    return {
      total,
      owned,
      wishlist,
      duplicate,
      dupExtraCopies,
      pct,
      ownedValue,
      dupValue,
      wishlistValue,
      costToComplete,
      remainingCount,
    };
  }, [
    activeShelf,
    activeSubSeries,
    pokemonSetsInEra,
    pokemonCards,
    trackingMap,
    scopedCollectionIds,
    allItems,
    getTracking,
  ]);

  const hasActiveFilters =
    searchQuery.trim().length > 0 || statusFilter !== 'all' || secretOnly;

  const showTopOverview = activeShelf === 'overview' && !hasActiveFilters;
  const showPokemonSetsOverview =
    activeShelf === 'pokemon-tcg' && activeSubSeries === 'all';
  const showSubOverview =
    isGroupedShelf &&
    activeShelf !== 'pokemon-tcg' &&
    activeSubSeries === 'all' &&
    !hasActiveFilters;

  const filteredItems = useMemo(() => {
    if (showTopOverview || showSubOverview || showPokemonSetsOverview) return [];
    const sourceItems =
      activeShelf === 'pokemon-tcg' && activeSubSeries !== 'all'
        ? [
            ...pokemonCards,
            ...allItems.filter((i) => i.collectionId === activeSubSeries),
          ]
        : allItems;
    const q = searchQuery.trim().toLowerCase();
    return sourceItems.filter((item) => {
      if (
        activeShelf !== 'pokemon-tcg' &&
        scopedCollectionIds &&
        !scopedCollectionIds.has(item.collectionId)
      ) {
        return false;
      }
      const tr = getTracking(item.id);
      if (statusFilter !== 'all') {
        if (statusFilter === 'owned') {
          if (tr.status !== 'owned' && tr.status !== 'duplicate') return false;
        } else if (tr.status !== statusFilter) {
          return false;
        }
      }
      if (secretOnly && item.rarity !== 'Secret') return false;
      if (q) {
        const hay = `${item.name} ${item.series} ${tr.notes}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [
    showTopOverview,
    showSubOverview,
    showPokemonSetsOverview,
    activeShelf,
    activeSubSeries,
    pokemonCards,
    scopedCollectionIds,
    allItems,
    getTracking,
    searchQuery,
    secretOnly,
    statusFilter,
  ]);

  const selectedItem: CatalogItem | null = useMemo(
    () =>
      allItems.find((i) => i.id === selectedItemId) ??
      pokemonCards.find((i) => i.id === selectedItemId) ??
      null,
    [allItems, pokemonCards, selectedItemId]
  );

  const handleImportFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const ok = importJson(String(reader.result ?? ''));
      showToast(ok ? 'Collection backup restored!' : 'Invalid backup file.');
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const selectTopShelf = (shelf: ActiveShelf) => {
    setActiveShelf(shelf);
    setActiveSubSeries('all');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const defaultAddCollectionId: CollectionId =
    activeSubCollection?.id ??
    (activeShelf === 'skullpanda'
      ? SKULLPANDA_SERIES_IDS[0] ?? 'sonny-animal-1'
      : activeShelf === 'tinytiny'
      ? 'tinytiny-prologue'
      : activeShelf === 'calico-critters'
      ? CALICO_SERIES_IDS[0] ?? 'cc-sp-01-baby-band'
      : activeShelf === 'sullivan-family'
      ? SULLIVAN_SERIES_IDS[0] ?? 'sonny-animal-1'
      : activeShelf === 'zsiga'
      ? ZSIGA_SERIES_IDS[0] ?? 'sonny-animal-1'
      : activeShelf === 'jellycat'
      ? JELLYCAT_SERIES_IDS[0] ?? 'jc-amuseables'
      : activeShelf === 'pokemon-tcg'
      ? POKEMON_SETS[0]?.id ?? 'pkmn-base1'
      : 'sonny-animal-1');

  const heroAccent = activeSubCollection?.accent ?? activeTopShelf?.accent ?? '#2A2421';

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="header-inner">
          <button
            type="button"
            className="brand"
            onClick={() => {
              setActiveShelf('overview');
              setActiveSubSeries('all');
              setSearchQuery('');
              setStatusFilter('all');
              setSecretOnly(false);
            }}
          >
            <img src="/icons/icon-192.png" alt="TrinketShelf" className="brand-icon" />
            <div>
              <h1 className="brand-title">TrinketShelf</h1>
              <p className="brand-sub">{TOP_LEVEL_SHELVES.length} Collectible Shelves · Offline PWA</p>
            </div>
          </button>

          <div className="header-actions">
            {!isOnline && (
              <span className="offline-pill">
                <WifiOff size={13} /> Offline
              </span>
            )}
            {canInstall && (
              <button type="button" className="btn" onClick={promptInstall}>
                <Smartphone size={15} />
                <span className="hide-mobile">Install App</span>
              </button>
            )}
            <button
              type="button"
              className="btn btn-icon-only"
              onClick={() => {
                exportJson();
                showToast('Backup exported as JSON');
              }}
              title="Export collection backup"
              aria-label="Export collection backup"
            >
              <Download size={16} />
            </button>
            <button
              type="button"
              className="btn btn-icon-only"
              onClick={() => fileInputRef.current?.click()}
              title="Import collection backup"
              aria-label="Import collection backup"
            >
              <Upload size={16} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              onChange={handleImportFile}
              hidden
            />
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowAddModal(true)}
            >
              <Plus size={16} />
              <span className="hide-mobile">Add Item</span>
            </button>
          </div>
        </div>

        <nav className="tabs-bar" aria-label="Collections">
          <button
            type="button"
            className={`tab-pill ${activeShelf === 'overview' ? 'active' : ''}`}
            onClick={() => selectTopShelf('overview')}
          >
            <LayoutGrid size={14} />
            <span>All Shelves</span>
            <span className="tab-count">{TOP_LEVEL_SHELVES.length}</span>
          </button>
          {TOP_LEVEL_SHELVES.map((shelf) => {
            if (shelf.id === 'pokemon-tcg') {
              return (
                <button
                  key={shelf.id}
                  type="button"
                  className={`tab-pill ${activeShelf === shelf.id ? 'active' : ''}`}
                  onClick={() => selectTopShelf(shelf.id)}
                >
                  <span>{shelf.emoji}</span>
                  <span>{shelf.name}</span>
                  <span className="tab-count">
                    {pokemonOwnedTotal}/{POKEMON_TOTAL_GM_CARDS.toLocaleString()}
                  </span>
                </button>
              );
            }
            const idSet = new Set(shelf.collectionIds);
            const shelfItems = allItems.filter((i) => idSet.has(i.collectionId));
            const shelfOwned = shelfItems.filter((i) => {
              const st = getTracking(i.id).status;
              return st === 'owned' || st === 'duplicate';
            }).length;
            return (
              <button
                key={shelf.id}
                type="button"
                className={`tab-pill ${activeShelf === shelf.id ? 'active' : ''}`}
                onClick={() => selectTopShelf(shelf.id)}
              >
                <span>{shelf.emoji}</span>
                <span>{shelf.name}</span>
                <span className="tab-count">
                  {shelfOwned}/{shelfItems.length}
                </span>
              </button>
            );
          })}
        </nav>
      </header>

      <main className="main-content">
        <section className="stats-strip" aria-label="Collection Progress">
          <div className="stat-card">
            <div className="stat-label">Collected</div>
            <div className="stat-value-row">
              <span className="stat-value">{stats.owned.toLocaleString()}</span>
              <span className="stat-sub">/ {stats.total.toLocaleString()}</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${stats.pct}%`,
                  background: heroAccent,
                }}
              />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Est. Value</div>
            <div className="stat-value-row">
              <span className="stat-value" style={{ color: 'var(--owned-text)' }}>
                {formatUsdWhole(stats.ownedValue)}
              </span>
              <span className="stat-sub">owned</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Wishlist / ISO</div>
            <div className="stat-value-row">
              <span className="stat-value" style={{ color: 'var(--wishlist-text)' }}>
                {stats.wishlist.toLocaleString()}
              </span>
              <span className="stat-sub">
                {stats.wishlistValue > 0 ? formatUsdWhole(stats.wishlistValue) : 'wanted'}
              </span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Cost to Complete</div>
            <div className="stat-value-row">
              <span className="stat-value">
                {formatUsdWhole(stats.costToComplete)}
              </span>
              <span className="stat-sub">
                {stats.remainingCount === 0
                  ? 'no wishlist'
                  : `${stats.remainingCount.toLocaleString()} wishlisted`}
              </span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">For Trade</div>
            <div className="stat-value-row">
              <span className="stat-value" style={{ color: 'var(--dup-text)' }}>
                {stats.duplicate}
              </span>
              <span className="stat-sub">dups</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Dups Value</div>
            <div className="stat-value-row">
              <span className="stat-value" style={{ color: 'var(--dup-text)' }}>
                {formatUsdWhole(stats.dupValue)}
              </span>
              <span className="stat-sub">
                {stats.dupExtraCopies === 1 ? '1 extra' : `${stats.dupExtraCopies} extras`}
              </span>
            </div>
          </div>
        </section>

        {activeTopShelf && (
          <section className="collection-hero">
            <div className="collection-hero-left">
              <div
                className="collection-emoji-badge"
                style={{
                  background: activeSubCollection?.accentSoft ?? activeTopShelf.accentSoft,
                }}
              >
                {activeSubCollection?.emoji ?? activeTopShelf.emoji}
              </div>
              <div>
                {activeSubCollection && (
                  <button
                    type="button"
                    className="back-link"
                    onClick={() => setActiveSubSeries('all')}
                  >
                    <ArrowLeft size={14} />
                    <span>All {activeTopShelf.name} Series</span>
                  </button>
                )}
                <h2 style={{ margin: 0, fontSize: '1.45rem' }}>
                  {activeSubCollection?.name ?? activeTopShelf.name}
                </h2>
                <p style={{ margin: '2px 0 0', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  {activeSubCollection?.subtitle ?? activeTopShelf.subtitle} ·{' '}
                  {activeSubCollection?.maker ?? activeTopShelf.maker}
                </p>
              </div>
            </div>
            <button
              type="button"
              className="btn"
              onClick={() => setShowAddModal(true)}
              style={{
                background: activeSubCollection?.accentSoft ?? activeTopShelf.accentSoft,
                color: activeSubCollection?.accentText ?? activeTopShelf.accentText,
                borderColor: 'transparent',
              }}
            >
              <Plus size={15} />
              <span>
                Add to{' '}
                {activeSubCollection
                  ? activeSubCollection.name.replace(/^(?:Sonny Angel|Artist Collection|Skullpanda|Tinytiny|Calico Critters|Sylvanian Families|Zsiga|Jellycat|Pokémon TCG) · /, '')
                  : activeTopShelf.name}
              </span>
            </button>
          </section>
        )}

        {isGroupedShelf && (
          <>
            {activeShelf === 'sonny-angel' && (
              <div className="sonny-mode-bar" role="tablist" aria-label="Sonny Angel Series Type">
                {(
                  [
                    ['all', `All (${SONNY_SERIES_IDS.length})`],
                    ['regular', `Regular (${SONNY_REGULAR_IDS.length})`],
                    ['hippers', `Hippers (${SONNY_HIPPERS_IDS.length})`],
                    ['limited', `Limited (${SONNY_LIMITED_IDS.length})`],
                    ['vintage', `Vintage (${SONNY_VINTAGE_IDS.length})`],
                    ['unrefined', `Unrefined (${SONNY_UNREFINED_IDS.length})`],
                    ['artist', `Artist (${SONNY_ARTIST_IDS.length})`],
                    ['special', `Special (${SONNY_SPECIAL_IDS.length})`],
                  ] as [SonnySeriesTab, string][]
                ).map(([mode, label]) => (
                  <button
                    key={mode}
                    type="button"
                    role="tab"
                    aria-selected={sonnySeriesTab === mode}
                    className={`sonny-mode-btn ${sonnySeriesTab === mode ? 'active' : ''}`}
                    onClick={() => {
                      setSonnySeriesTab(mode);
                      setActiveSubSeries('all');
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {activeShelf === 'skullpanda' && (
              <div className="sonny-mode-bar" role="tablist" aria-label="Skullpanda Series Type">
                {(
                  [
                    ['all', `All (${SKULLPANDA_SERIES_IDS.length})`],
                    [
                      'blind-box',
                      `Blind Box (${COLLECTIONS.filter((c) => c.skullpandaCategory === 'blind-box').length})`,
                    ],
                    [
                      'plush',
                      `Plush Pendants (${COLLECTIONS.filter((c) => c.skullpandaCategory === 'plush').length})`,
                    ],
                    ['mixed', 'Mixed Sets'],
                  ] as [SkullpandaTab, string][]
                ).map(([mode, label]) => (
                  <button
                    key={mode}
                    type="button"
                    role="tab"
                    aria-selected={skullpandaTab === mode}
                    className={`sonny-mode-btn ${skullpandaTab === mode ? 'active' : ''}`}
                    onClick={() => {
                      setSkullpandaTab(mode);
                      setActiveSubSeries('all');
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {activeShelf === 'sullivan-family' && (
              <div className="sonny-mode-bar" role="tablist" aria-label="Sylvanian Families Series Type">
                {(
                  [
                    ['all', `All (${SULLIVAN_SERIES_IDS.length})`],
                    [
                      'blind-bag',
                      `Blind Bags (${COLLECTIONS.filter((c) => c.sullivanCategory === 'blind-bag').length})`,
                    ],
                    [
                      'blind-box',
                      `Blind Boxes (${COLLECTIONS.filter((c) => c.sullivanCategory === 'blind-box').length})`,
                    ],
                  ] as [SullivanTab, string][]
                ).map(([mode, label]) => (
                  <button
                    key={mode}
                    type="button"
                    role="tab"
                    aria-selected={sullivanTab === mode}
                    className={`sonny-mode-btn ${sullivanTab === mode ? 'active' : ''}`}
                    onClick={() => {
                      setSullivanTab(mode);
                      setActiveSubSeries('all');
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {activeShelf === 'pokemon-tcg' && (
              <div className="sonny-mode-bar" role="tablist" aria-label="Pokémon TCG Era">
                {(
                  [
                    ['all', `All (${POKEMON_SETS.length})`],
                    ['Simplified Chinese', `Chinese (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'Simplified Chinese')).length})`],
                    ['Mega Evolution', `Mega Evolution (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'Mega Evolution')).length})`],
                    ['Scarlet & Violet', `Scarlet & Violet (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'Scarlet & Violet')).length})`],
                    ['Sword & Shield', `Sword & Shield (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'Sword & Shield')).length})`],
                    ['Sun & Moon', `Sun & Moon (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'Sun & Moon')).length})`],
                    ['XY', `XY (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'XY')).length})`],
                    ['Black & White', `Black & White (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'Black & White')).length})`],
                    ['dp-hgss', `DP / Plat / HGSS (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'dp-hgss')).length})`],
                    ['ex-ecard', `EX / E-Card (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'ex-ecard')).length})`],
                    ['classic', `Base / Gym / Neo (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'classic')).length})`],
                    ['other', `POP & Promos (${POKEMON_SETS.filter((s) => matchesPokemonEra(s, 'other')).length})`],
                  ] as [PokemonEraTab, string][]
                ).map(([mode, label]) => (
                  <button
                    key={mode}
                    type="button"
                    role="tab"
                    aria-selected={pokemonEraTab === mode}
                    className={`sonny-mode-btn ${pokemonEraTab === mode ? 'active' : ''}`}
                    onClick={() => {
                      setPokemonEraTab(mode);
                      setActiveSubSeries('all');
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            <nav className="subtabs-bar" aria-label="Sub-series">
              <button
                type="button"
                className={`subtab-pill ${activeSubSeries === 'all' ? 'active' : ''}`}
                onClick={() => setActiveSubSeries('all')}
              >
                <LayoutGrid size={13} />
                <span>
                  All ({activeShelf === 'pokemon-tcg' ? pokemonSetsInEra.length : subSeriesGroups.length})
                </span>
              </button>
              {activeShelf === 'pokemon-tcg'
                ? pokemonSetsInEra.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`subtab-pill ${activeSubSeries === s.id ? 'active' : ''}`}
                      onClick={() => setActiveSubSeries(s.id)}
                    >
                      <span>{s.emoji}</span>
                      <span>{s.shortName}</span>
                      <span className="tab-count">{s.grandMasterCount}</span>
                    </button>
                  ))
                : subSeriesGroups.map((series) => {
                    const sItems = allItems.filter((i) => i.collectionId === series.id);
                    const sOwned = sItems.filter((i) => {
                      const st = getTracking(i.id).status;
                      return st === 'owned' || st === 'duplicate';
                    }).length;
                    return (
                      <button
                        key={series.id}
                        type="button"
                        className={`subtab-pill ${activeSubSeries === series.id ? 'active' : ''}`}
                        onClick={() => setActiveSubSeries(series.id)}
                      >
                        <span>{series.emoji}</span>
                        <span>{series.name}</span>
                        <span className="tab-count">
                          {sOwned}/{sItems.length}
                        </span>
                      </button>
                    );
                  })}
            </nav>
          </>
        )}

        <section className="toolbar" aria-label="Search and filter">
          <div className="search-box">
            <Search size={16} />
            <input
              type="search"
              className="search-input"
              placeholder={
                activeSubCollection
                  ? `Search ${activeSubCollection.name}...`
                  : activeShelf === 'pokemon-tcg'
                  ? `Search ${pokemonSetsInEra.length} Pokémon TCG sets (e.g., Base Set, 151, Prismatic, Evolving Skies)...`
                  : isGroupedShelf && activeTopShelf
                  ? `Search all ${subSeriesGroups.length} ${activeTopShelf.name} series...`
                  : activeTopShelf
                  ? `Search ${activeTopShelf.name}...`
                  : `Search all ${TOP_LEVEL_SHELVES.length} collections...`
              }
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {(
              [
                ['all', 'All'],
                ['owned', 'Owned'],
                ['wishlist', 'Wishlist'],
                ['duplicate', 'For Trade'],
                ['unowned', 'Missing'],
              ] as [StatusFilter, string][]
            ).map(([val, label]) => (
              <button
                key={val}
                type="button"
                className={`filter-pill ${statusFilter === val ? 'active' : ''}`}
                onClick={() => setStatusFilter(val)}
              >
                {label}
              </button>
            ))}
            <button
              type="button"
              className={`filter-pill ${secretOnly ? 'active' : ''}`}
              onClick={() => setSecretOnly((v) => !v)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              <Sparkles size={13} />
              <span>Secrets</span>
            </button>
          </div>
        </section>

        {showTopOverview ? (
          <CollectionOverview
            groups={TOP_LEVEL_SHELVES}
            allItems={allItems}
            getTracking={getTracking}
            trackingMap={trackingMap}
            onSelect={(id) => selectTopShelf(id)}
          />
        ) : showPokemonSetsOverview ? (
          filteredPokemonSets.length === 0 ? (
            <div className="empty-state">
              <p style={{ margin: 0, fontWeight: 600, fontSize: '1rem', color: 'var(--text)' }}>
                No matching Pokémon TCG sets found
              </p>
              <p style={{ margin: '6px 0 16px', fontSize: '0.88rem' }}>
                Try clearing your search or switching to the All era tab.
              </p>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setSearchQuery('');
                  setPokemonEraTab('all');
                }}
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <PokemonSetsOverview
              sets={filteredPokemonSets}
              tracking={trackingMap}
              onSelectSet={(colId) => {
                setActiveSubSeries(colId);
                setSearchQuery('');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />
          )
        ) : showSubOverview ? (
          <CollectionOverview
            groups={subSeriesGroups}
            allItems={allItems}
            getTracking={getTracking}
            onSelect={(id) => {
              setActiveSubSeries(id);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          />
        ) : pokemonLoading ? (
          <div className="empty-state">
            <p style={{ margin: 0, fontWeight: 600, fontSize: '1rem', color: 'var(--text)' }}>
              Loading Grand Master card list...
            </p>
            <p style={{ margin: '6px 0 0', fontSize: '0.88rem' }}>
              Fetching set cards & variants for {activeSubCollection?.shortName ?? 'this set'}.
            </p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">
            <p style={{ margin: 0, fontWeight: 600, fontSize: '1rem', color: 'var(--text)' }}>
              No matching collectibles found
            </p>
            <p style={{ margin: '6px 0 16px', fontSize: '0.88rem' }}>
              Try clearing your search or status filters, or add a custom item to your shelf.
            </p>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
                setSecretOnly(false);
              }}
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="items-grid">
            {filteredItems.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                tracking={getTracking(item.id)}
                onOpenDetail={() => setSelectedItemId(item.id)}
                onToggleOwned={() => toggleStatusQuick(item.id, 'owned', item.price)}
                onToggleWishlist={() => toggleStatusQuick(item.id, 'wishlist', item.price)}
              />
            ))}
          </div>
        )}
      </main>

      {selectedItem && (
        <ItemDetailModal
          item={selectedItem}
          collection={
            COLLECTIONS.find((c) => c.id === selectedItem.collectionId) ?? COLLECTIONS[0]
          }
          tracking={getTracking(selectedItem.id)}
          onUpdate={(patch) =>
            updateTracking(selectedItem.id, {
              ...patch,
              ...(typeof selectedItem.price === 'number'
                ? { cachedPrice: selectedItem.price }
                : {}),
            })
          }
          onDeleteCustom={
            selectedItem.isCustom
              ? () => {
                  deleteCustomItem(selectedItem.id);
                  setSelectedItemId(null);
                  showToast('Custom item deleted');
                }
              : undefined
          }
          onClose={() => setSelectedItemId(null)}
        />
      )}

      {showAddModal && (
        <AddItemModal
          defaultCollectionId={defaultAddCollectionId}
          onAdd={(item, initialStatus) => {
            addCustomItem(item, initialStatus);
            showToast(`Added "${item.name}" to your shelf`);
          }}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
