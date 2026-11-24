import { type ChangeEvent, type FormEvent, useState } from 'react';
import { ImagePlus, X } from 'lucide-react';
import { COLLECTIONS } from '../data/catalog';
import type { CollectionId, ItemRarity, ItemStatus } from '../types';

interface AddItemModalProps {
  defaultCollectionId: CollectionId;
  onAdd: (
    item: {
      collectionId: CollectionId;
      name: string;
      series: string;
      rarity: ItemRarity;
      image: string;
    },
    initialStatus: ItemStatus
  ) => void;
  onClose: () => void;
}

function makePlaceholderSvg(label: string, accent: string, emoji: string): string {
  const safe = label.replace(/[<>&"]/g, '');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
    <rect width="400" height="400" fill="#FFFFFF"/>
    <circle cx="200" cy="180" r="110" fill="${accent}" opacity="0.16"/>
    <text x="200" y="205" text-anchor="middle" font-size="96">${emoji}</text>
    <text x="200" y="330" text-anchor="middle" font-family="sans-serif" font-size="22" font-weight="600" fill="#554B44">${safe.slice(0, 22)}</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

async function compressImageFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const size = 512;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        if (!ctx) return reject(new Error('Canvas unavailable'));
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, size, size);
        const scale = Math.min(size / img.width, size / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
        resolve(canvas.toDataURL('image/webp', 0.85));
      };
      img.onerror = reject;
      img.src = String(reader.result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function AddItemModal({ defaultCollectionId, onAdd, onClose }: AddItemModalProps) {
  const [collectionId, setCollectionId] = useState<CollectionId>(defaultCollectionId);
  const [name, setName] = useState('');
  const [series, setSeries] = useState('');
  const [rarity, setRarity] = useState<ItemRarity>('Regular');
  const [status, setStatus] = useState<ItemStatus>('owned');
  const [photoDataUrl, setPhotoDataUrl] = useState<string>('');

  const handlePhotoChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const compressed = await compressImageFile(file);
      setPhotoDataUrl(compressed);
    } catch {
      // Ignore failed decode
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const col = COLLECTIONS.find((c) => c.id === collectionId) ?? COLLECTIONS[0];
    const image = photoDataUrl || makePlaceholderSvg(name.trim(), col.accent, col.emoji);
    onAdd(
      {
        collectionId,
        name: name.trim(),
        series: series.trim() || 'Custom Addition',
        rarity,
        image,
      },
      status
    );
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Add Collectible</h3>
          <button type="button" className="btn btn-icon-only" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          <div className="field-group">
            <label className="field-label" htmlFor="add-col">Collection</label>
            <select
              id="add-col"
              className="field-select"
              value={collectionId}
              onChange={(e) => setCollectionId(e.target.value as CollectionId)}
            >
              {COLLECTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.emoji} {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="add-name">Item Name *</label>
            <input
              id="add-name"
              type="text"
              required
              className="field-input"
              placeholder="e.g., Hippers Cherry, Smudge Elephant..."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="field-group">
            <label className="field-label" htmlFor="add-series">Series / Line</label>
            <input
              id="add-series"
              type="text"
              className="field-input"
              placeholder="e.g., Animal Series 2, Amuseables..."
              value={series}
              onChange={(e) => setSeries(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="field-group">
              <label className="field-label" htmlFor="add-rarity">Rarity</label>
              <select
                id="add-rarity"
                className="field-select"
                value={rarity}
                onChange={(e) => setRarity(e.target.value as ItemRarity)}
              >
                <option value="Regular">Regular</option>
                <option value="Special">Special</option>
                <option value="Lucky">Lucky</option>
                <option value="Secret">Secret</option>
              </select>
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="add-status">Initial Status</label>
              <select
                id="add-status"
                className="field-select"
                value={status}
                onChange={(e) => setStatus(e.target.value as ItemStatus)}
              >
                <option value="owned">Owned</option>
                <option value="wishlist">Wishlist / ISO</option>
                <option value="duplicate">For Trade</option>
                <option value="unowned">Not Owned</option>
              </select>
            </div>
          </div>

          <div className="field-group">
            <label className="field-label">Photo (optional, stored offline)</label>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                padding: photoDataUrl ? 10 : 18,
                borderRadius: 14,
                border: '1.5px dashed var(--border-strong)',
                background: 'var(--bg)',
                cursor: 'pointer',
              }}
            >
              {photoDataUrl ? (
                <img
                  src={photoDataUrl}
                  alt="Preview"
                  style={{ width: 96, height: 96, objectFit: 'contain', borderRadius: 10 }}
                />
              ) : (
                <>
                  <ImagePlus size={18} />
                  <span style={{ fontSize: '0.86rem', fontWeight: 600 }}>Upload Photo</span>
                </>
              )}
              <input type="file" accept="image/*" onChange={handlePhotoChange} hidden />
            </label>
          </div>

          <button type="submit" className="btn btn-primary" style={{ padding: '12px 18px' }}>
            Add to Shelf
          </button>
        </form>
      </div>
    </div>
  );
}
