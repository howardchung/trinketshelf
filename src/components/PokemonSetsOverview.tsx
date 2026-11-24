import { ChevronRight } from 'lucide-react';
import type { PokemonSetMeta } from '../data/pokemonSets';
import { formatUsdWhole } from '../data/prices';
import type { CollectionId, ItemTrackingState } from '../types';

interface PokemonSetsOverviewProps {
  sets: PokemonSetMeta[];
  tracking: Record<string, ItemTrackingState>;
  onSelectSet: (colId: CollectionId) => void;
}

export function PokemonSetsOverview({
  sets,
  tracking,
  onSelectSet,
}: PokemonSetsOverviewProps) {
  // Pre-aggregate owned count & wishlisted cost per setId from tracking keys (pkmn-<setId>-...)
  const ownedBySet = new Map<string, number>();
  const wishlistCostBySet = new Map<string, number>();
  for (const [itemId, tr] of Object.entries(tracking)) {
    if (!itemId.startsWith('pkmn-')) continue;
    const rest = itemId.slice(5);
    const dash = rest.indexOf('-');
    if (dash <= 0) continue;
    const sid = rest.slice(0, dash);
    if (tr.status === 'owned' || tr.status === 'duplicate') {
      ownedBySet.set(sid, (ownedBySet.get(sid) ?? 0) + 1);
    } else if (tr.status === 'wishlist') {
      const p = tr.customPrice ?? tr.cachedPrice ?? 1;
      wishlistCostBySet.set(sid, (wishlistCostBySet.get(sid) ?? 0) + p);
    }
  }

  return (
    <div className="overview-grid">
      {sets.map((s) => {
        const owned = ownedBySet.get(s.setId) ?? 0;
        const wishlistCost = wishlistCostBySet.get(s.setId) ?? 0;
        const pct =
          s.grandMasterCount > 0 ? Math.round((owned / s.grandMasterCount) * 100) : 0;

        return (
          <button
            key={s.id}
            type="button"
            className="collection-card"
            onClick={() => onSelectSet(s.id)}
          >
            <div className="collection-card-header">
              <div>
                <h2 className="collection-card-title">
                  {s.emoji} {s.shortName}
                </h2>
                <p className="collection-card-sub">
                  {s.era} · {s.releaseDate.slice(0, 4)} · {s.cardCount} base / {s.grandMasterCount} GM
                </p>
              </div>
              <span
                className="collection-badge"
                style={{ background: s.accentSoft, color: s.accentText }}
              >
                {owned}/{s.grandMasterCount}
              </span>
            </div>

            <div className="pkmn-logo-frame">
              {s.logo ? (
                <img src={s.logo} alt={s.shortName} loading="lazy" />
              ) : (
                <span style={{ fontSize: '1.8rem' }}>{s.emoji}</span>
              )}
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
                    : `Est. ${formatUsdWhole(s.estimatedTotal)} GM set`}
                  <ChevronRight size={14} />
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${pct}%`, background: s.accent }}
                />
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
