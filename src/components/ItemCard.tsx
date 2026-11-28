import { Check, Heart, Repeat } from 'lucide-react';
import { formatUsd, getItemPrice, isEstimatedPrice } from '../data/prices';
import type { CatalogItem, ItemTrackingState } from '../types';

interface ItemCardProps {
  item: CatalogItem;
  tracking: ItemTrackingState;
  onOpenDetail: () => void;
  onToggleOwned: () => void;
  onToggleWishlist: () => void;
}

export function ItemCard({
  item,
  tracking,
  onOpenDetail,
  onToggleOwned,
  onToggleWishlist,
}: ItemCardProps) {
  const isOwned = tracking.status === 'owned';
  const isDup = tracking.status === 'duplicate';
  const isWishlist = tracking.status === 'wishlist';
  const unitPrice = getItemPrice(item.id, tracking.customPrice, item.price);
  const isEst = isEstimatedPrice(item.id, tracking.customPrice, item.price);

  return (
    <article className={`item-card status-${tracking.status}`}>
      <div className="item-image-wrap" onClick={onOpenDetail}>
        <img
          src={item.image}
          alt={`${item.name} — ${item.series}`}
          className="item-image"
          loading="lazy"
        />
        <div className="item-top-badges">
          <div>
            {item.rarity !== 'Regular' && (
              <span className={`rarity-badge rarity-${item.rarity}`}>
                {item.rarity === 'Secret'
                  ? '★ Secret'
                  : item.rarity === 'Lucky'
                  ? '🍀 Lucky'
                  : item.rarity}
              </span>
            )}
          </div>
          {tracking.quantity > 1 && (
            <span className="qty-badge">×{tracking.quantity}</span>
          )}
        </div>
      </div>

      <div className="item-body">
        <div className="item-meta" onClick={onOpenDetail}>
          <div className="item-title-row">
            <h3 className="item-name">{item.name}</h3>
            <span className="item-price">{isEst ? 'est. ' : ''}{formatUsd(unitPrice)}</span>
          </div>
          <p className="item-series">{item.series}</p>
        </div>

        <div className="item-actions">
          <button
            type="button"
            className={`quick-btn ${isOwned ? 'active-owned' : ''} ${isDup ? 'active-dup' : ''}`}
            onClick={onToggleOwned}
            title={isOwned ? 'Mark as not owned' : 'Mark as owned'}
          >
            {isDup ? <Repeat size={14} /> : <Check size={14} />}
            <span>{isDup ? 'For Trade' : isOwned ? 'Owned' : 'Collect'}</span>
          </button>

          <button
            type="button"
            className={`quick-btn quick-btn-icon ${isWishlist ? 'active-wishlist' : ''}`}
            onClick={onToggleWishlist}
            title={isWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
            aria-label={isWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
          >
            <Heart size={15} fill={isWishlist ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>
    </article>
  );
}
