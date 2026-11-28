import { Check, Circle, ExternalLink, Heart, Image as ImageIcon, Repeat, Trash2, X } from 'lucide-react';
import { formatUsd, getItemPrice } from '../data/prices';
import { getItemProvenanceLinks } from '../data/sources';
import type { CatalogItem, CollectionMeta, ItemStatus, ItemTrackingState } from '../types';

interface ItemDetailModalProps {
  item: CatalogItem;
  collection: CollectionMeta;
  tracking: ItemTrackingState;
  onUpdate: (patch: Partial<ItemTrackingState>) => void;
  onDeleteCustom?: () => void;
  onClose: () => void;
}

const STATUS_OPTIONS: { value: ItemStatus; label: string; icon: typeof Check }[] = [
  { value: 'unowned', label: 'Not Owned', icon: Circle },
  { value: 'owned', label: 'Owned', icon: Check },
  { value: 'wishlist', label: 'Wishlist / ISO', icon: Heart },
  { value: 'duplicate', label: 'For Trade / Dup', icon: Repeat },
];

export function ItemDetailModal({
  item,
  collection,
  tracking,
  onUpdate,
  onDeleteCustom,
  onClose,
}: ItemDetailModalProps) {
  const showQty = tracking.status === 'owned' || tracking.status === 'duplicate';
  const defaultPrice = getItemPrice(item.id, undefined, item.price);
  const effectivePrice = getItemPrice(item.id, tracking.customPrice, item.price);
  const provenanceLinks = getItemProvenanceLinks(item);
  const sourceLink = provenanceLinks.find((l) => l.kind === 'source');
  const imageLink = provenanceLinks.find((l) => l.kind === 'image');
  const priceLink = provenanceLinks.find((l) => l.kind === 'price');

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{item.name}</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {collection.name} · {item.series}
            </span>
          </div>
          <button
            type="button"
            className="btn btn-icon-only"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div className="detail-photo-frame" style={{ position: 'relative' }}>
            {imageLink ? (
              <a
                href={imageLink.url}
                target="_blank"
                rel="noopener noreferrer"
                title={`${imageLink.label} (${imageLink.url})`}
                style={{ display: 'flex', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center' }}
              >
                <img src={item.image} alt={item.name} />
                <span
                  style={{
                    position: 'absolute',
                    right: 8,
                    bottom: 8,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    padding: '3px 7px',
                    borderRadius: 999,
                    background: 'rgba(255,255,255,0.88)',
                    color: 'var(--text-secondary)',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                  }}
                >
                  <ImageIcon size={11} />
                  <span>{imageLink.label.replace(/^Image:\s*/, '')}</span>
                </span>
              </a>
            ) : (
              <img src={item.image} alt={item.name} />
            )}
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {sourceLink ? (
              <a
                href={sourceLink.url}
                target="_blank"
                rel="noopener noreferrer"
                title={`${sourceLink.label} (${sourceLink.url})`}
                className="collection-badge"
                style={{
                  background: collection.accentSoft,
                  color: collection.accentText,
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                <span>
                  {collection.emoji} {collection.name}
                </span>
                <ExternalLink size={11} style={{ opacity: 0.75 }} />
              </a>
            ) : (
              <span
                className="collection-badge"
                style={{ background: collection.accentSoft, color: collection.accentText }}
              >
                {collection.emoji} {collection.name}
              </span>
            )}
            <span
              className={`rarity-badge ${
                item.rarity === 'Secret'
                  ? 'rarity-Secret'
                  : item.rarity === 'Lucky'
                  ? 'rarity-Lucky'
                  : item.rarity === 'Special'
                  ? 'rarity-Special'
                  : ''
              }`}
              style={
                item.rarity === 'Regular'
                  ? { background: 'var(--surface-muted)', color: 'var(--text-secondary)' }
                  : undefined
              }
            >
              {item.rarity}
            </span>
            {priceLink ? (
              <a
                href={priceLink.url}
                target="_blank"
                rel="noopener noreferrer"
                title={`${priceLink.label} (${priceLink.url})`}
                className="collection-badge"
                style={{
                  background: 'var(--surface-muted)',
                  color: 'var(--text)',
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                <span>Est. {formatUsd(effectivePrice)}</span>
                <ExternalLink size={11} style={{ opacity: 0.65 }} />
              </a>
            ) : (
              <span
                className="collection-badge"
                style={{ background: 'var(--surface-muted)', color: 'var(--text)' }}
              >
                Est. {formatUsd(effectivePrice)}
              </span>
            )}
          </div>

          <div className="field-group">
            <label className="field-label">Collection Status</label>
            <div className="status-grid">
              {STATUS_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const isSelected = tracking.status === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    className={`status-option ${isSelected ? `selected-${opt.value}` : ''}`}
                    onClick={() => onUpdate({ status: opt.value })}
                  >
                    <Icon size={16} />
                    <span>{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {showQty && (
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <div className="field-group">
                <label className="field-label">Quantity</label>
                <div className="stepper">
                  <button
                    type="button"
                    onClick={() =>
                      onUpdate({ quantity: Math.max(1, (tracking.quantity || 1) - 1) })
                    }
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <span>{tracking.quantity || 1}</span>
                  <button
                    type="button"
                    onClick={() => onUpdate({ quantity: (tracking.quantity || 1) + 1 })}
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>
              </div>

              <div className="field-group" style={{ flex: 1, minWidth: 150 }}>
                <label className="field-label" htmlFor="acquired-date">
                  Acquired Date
                </label>
                <input
                  id="acquired-date"
                  type="date"
                  className="field-input"
                  value={tracking.acquiredDate ?? ''}
                  onChange={(e) => onUpdate({ acquiredDate: e.target.value })}
                />
              </div>
            </div>
          )}

          <div className="field-group">
            <label className="field-label" htmlFor="custom-price">
              Price / Value (USD) — est. {formatUsd(defaultPrice)}
            </label>
            <input
              id="custom-price"
              type="number"
              min="0"
              step="0.01"
              className="field-input"
              placeholder={String(defaultPrice)}
              value={tracking.customPrice ?? ''}
              onChange={(e) => {
                const raw = e.target.value;
                onUpdate({ customPrice: raw === '' ? undefined : Math.max(0, Number(raw)) });
              }}
            />
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="item-notes">
              Collector Notes
            </label>
            <textarea
              id="item-notes"
              rows={3}
              className="field-textarea"
              placeholder="Where you pulled it, box condition, trade notes..."
              value={tracking.notes}
              onChange={(e) => onUpdate({ notes: e.target.value })}
            />
          </div>

          {item.isCustom && onDeleteCustom && (
            <button
              type="button"
              className="btn"
              style={{
                color: '#B9314F',
                borderColor: '#F7C2CE',
                background: '#FDECEF',
                marginTop: 4,
              }}
              onClick={onDeleteCustom}
            >
              <Trash2 size={15} />
              <span>Delete Custom Item</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
