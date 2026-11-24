import { ChevronRight } from 'lucide-react';
import { POKEMON_SETS, POKEMON_TOTAL_GM_CARDS } from '../data/pokemonSets';
import { formatUsdWhole, getItemPrice } from '../data/prices';
import type { CatalogItem, CollectionId, ItemTrackingState } from '../types';

export interface OverviewCardGroup<T extends string = string> {
  id: T;
  name: string;
  subtitle: string;
  maker: string;
  accent: string;
  accentSoft: string;
  accentText: string;
  emoji: string;
  collectionIds: CollectionId[];
}

interface CollectionOverviewProps<T extends string> {
  groups: OverviewCardGroup<T>[];
  allItems: CatalogItem[];
  getTracking: (itemId: string) => ItemTrackingState;
  trackingMap?: Record<string, ItemTrackingState>;
  onSelect: (id: T) => void;
}

const POKEMON_PREVIEW_SET_IDS = ['base1', 'sv8pt5', 'sv3pt5', 'swsh12pt5'];

export function CollectionOverview<T extends string>({
  groups,
  allItems,
  getTracking,
  trackingMap,
  onSelect,
}: CollectionOverviewProps<T>) {
  return (
    <div className="overview-grid">
      {groups.map((group) => {
        const isPokemonShelf = group.id === 'pokemon-tcg';

        if (isPokemonShelf) {
          let ownedCount = 0;
          let wishlistCost = 0;
          if (trackingMap) {
            for (const [itemId, tr] of Object.entries(trackingMap)) {
              if (!itemId.startsWith('pkmn-')) continue;
              if (tr.status === 'owned' || tr.status === 'duplicate') {
                ownedCount++;
              } else if (tr.status === 'wishlist') {
                wishlistCost += tr.customPrice ?? tr.cachedPrice ?? 1;
              }
            }
          }
          const totalCount = POKEMON_TOTAL_GM_CARDS;
          const pct = totalCount > 0 ? Math.round((ownedCount / totalCount) * 100) : 0;
          const previewSets = POKEMON_PREVIEW_SET_IDS
            .map((sid) => POKEMON_SETS.find((s) => s.setId === sid))
            .filter((s): s is NonNullable<typeof s> => Boolean(s));

          return (
            <button
              key={group.id}
              type="button"
              className="collection-card"
              onClick={() => onSelect(group.id)}
            >
              <div className="collection-card-header">
                <div>
                  <h2 className="collection-card-title">
                    {group.emoji} {group.name}
                  </h2>
                  <p className="collection-card-sub">{group.subtitle}</p>
                </div>
                <span
                  className="collection-badge"
                  style={{ background: group.accentSoft, color: group.accentText }}
                >
                  {ownedCount}/{totalCount.toLocaleString()}
                </span>
              </div>

              <div className="collection-mosaic">
                {previewSets.map((s) => (
                  <div key={s.id} className="mosaic-thumb" style={{ padding: 6 }}>
                    <img
                      src={s.logo}
                      alt={s.shortName}
                      loading="lazy"
                      style={{ objectFit: 'contain' }}
                    />
                  </div>
                ))}
              </div>

              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '0.78rem',
                    color: 'var(--text-secondary)',
                    fontWeight: 600,
                  }}
                >
                  <span>{pct}% collected</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    {wishlistCost > 0
                      ? `${formatUsdWhole(wishlistCost)} to complete`
                      : 'No wishlist'}
                    <ChevronRight size={14} />
                  </span>
                </div>
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{ width: `${pct}%`, background: group.accent }}
                  />
                </div>
              </div>
            </button>
          );
        }

        const idSet = new Set(group.collectionIds);
        const items = allItems.filter((i) => idSet.has(i.collectionId));
        const ownedCount = items.filter((i) => {
          const st = getTracking(i.id).status;
          return st === 'owned' || st === 'duplicate';
        }).length;
        const costToComplete = items.reduce((sum, i) => {
          const tr = getTracking(i.id);
          if (tr.status !== 'wishlist') return sum;
          return sum + getItemPrice(i.id, tr.customPrice, i.price);
        }, 0);
        const pct = items.length > 0 ? Math.round((ownedCount / items.length) * 100) : 0;

        // Pick 4 representative preview thumbnails (spread across sub-series if grouped)
        const previews: CatalogItem[] = [];
        if (group.collectionIds.length > 1) {
          const previewSeries = ['sonny-fruit', 'sonny-animal-1', 'sonny-sweets', 'sonny-snack'];
          for (const sid of previewSeries) {
            const first = items.find((i) => i.collectionId === sid);
            if (first) previews.push(first);
          }
        }
        while (previews.length < 4 && previews.length < items.length) {
          const next = items.find((i) => !previews.includes(i));
          if (!next) break;
          previews.push(next);
        }

        return (
          <button
            key={group.id}
            type="button"
            className="collection-card"
            onClick={() => onSelect(group.id)}
          >
            <div className="collection-card-header">
              <div>
                <h2 className="collection-card-title">
                  {group.emoji} {group.name}
                </h2>
                <p className="collection-card-sub">{group.subtitle}</p>
              </div>
              <span
                className="collection-badge"
                style={{ background: group.accentSoft, color: group.accentText }}
              >
                {ownedCount}/{items.length}
              </span>
            </div>

            <div className="collection-mosaic">
              {previews.map((item) => {
                const st = getTracking(item.id).status;
                const isOwned = st === 'owned' || st === 'duplicate';
                return (
                  <div
                    key={item.id}
                    className={`mosaic-thumb ${isOwned ? 'is-owned' : ''}`}
                  >
                    <img src={item.image} alt={item.name} loading="lazy" />
                  </div>
                );
              })}
            </div>

            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.78rem',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                }}
              >
                <span>{pct}% collected</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  {costToComplete > 0 ? `${formatUsdWhole(costToComplete)} to complete` : 'No wishlist'}
                  <ChevronRight size={14} />
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${pct}%`, background: group.accent }}
                />
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
