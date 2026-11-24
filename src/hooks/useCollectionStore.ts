import { useCallback, useEffect, useMemo, useState } from 'react';
import { DEFAULT_ITEMS } from '../data/catalog';
import type { CatalogItem, ItemStatus, ItemTrackingState, PersistedStore } from '../types';

const STORAGE_KEY = 'trinketshelf_store_v1';

const EMPTY_TRACKING: ItemTrackingState = {
  status: 'unowned',
  quantity: 0,
  notes: '',
};

function loadStore(): PersistedStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { version: 1, tracking: {}, customItems: [] };
    const parsed = JSON.parse(raw) as Partial<PersistedStore>;
    return {
      version: 1,
      tracking: parsed.tracking ?? {},
      customItems: Array.isArray(parsed.customItems) ? parsed.customItems : [],
    };
  } catch {
    return { version: 1, tracking: {}, customItems: [] };
  }
}

export function useCollectionStore() {
  const [store, setStore] = useState<PersistedStore>(loadStore);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    } catch {
      // Quota exceeded or private browsing — ignore silently
    }
  }, [store]);

  const allItems = useMemo<CatalogItem[]>(
    () => [...DEFAULT_ITEMS, ...store.customItems],
    [store.customItems]
  );

  const getTracking = useCallback(
    (itemId: string): ItemTrackingState => store.tracking[itemId] ?? EMPTY_TRACKING,
    [store.tracking]
  );

  const updateTracking = useCallback(
    (itemId: string, patch: Partial<ItemTrackingState>) => {
      setStore((prev) => {
        const current = prev.tracking[itemId] ?? EMPTY_TRACKING;
        const next: ItemTrackingState = { ...current, ...patch };

        if (patch.status) {
          if (patch.status === 'owned' && next.quantity < 1) {
            next.quantity = 1;
            if (!next.acquiredDate) {
              next.acquiredDate = new Date().toISOString().slice(0, 10);
            }
          } else if (patch.status === 'duplicate' && next.quantity < 2) {
            next.quantity = 2;
            if (!next.acquiredDate) {
              next.acquiredDate = new Date().toISOString().slice(0, 10);
            }
          } else if (patch.status === 'unowned' || patch.status === 'wishlist') {
            next.quantity = 0;
          }
        }

        return {
          ...prev,
          tracking: {
            ...prev.tracking,
            [itemId]: next,
          },
        };
      });
    },
    []
  );

  const toggleStatusQuick = useCallback(
    (itemId: string, target: 'owned' | 'wishlist', cachedPrice?: number) => {
      const current = store.tracking[itemId] ?? EMPTY_TRACKING;
      const nextStatus: ItemStatus = current.status === target ? 'unowned' : target;
      updateTracking(itemId, {
        status: nextStatus,
        ...(typeof cachedPrice === 'number' ? { cachedPrice } : {}),
      });
    },
    [store.tracking, updateTracking]
  );

  const addCustomItem = useCallback((item: Omit<CatalogItem, 'id' | 'isCustom'>, initialStatus: ItemStatus) => {
    const id = `custom-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const newItem: CatalogItem = { ...item, id, isCustom: true };
    setStore((prev) => ({
      ...prev,
      customItems: [newItem, ...prev.customItems],
      tracking: {
        ...prev.tracking,
        [id]: {
          status: initialStatus,
          quantity: initialStatus === 'owned' ? 1 : initialStatus === 'duplicate' ? 2 : 0,
          notes: '',
          acquiredDate: initialStatus === 'owned' || initialStatus === 'duplicate'
            ? new Date().toISOString().slice(0, 10)
            : undefined,
        },
      },
    }));
  }, []);

  const deleteCustomItem = useCallback((itemId: string) => {
    setStore((prev) => {
      const nextTracking = { ...prev.tracking };
      delete nextTracking[itemId];
      return {
        ...prev,
        customItems: prev.customItems.filter((i) => i.id !== itemId),
        tracking: nextTracking,
      };
    });
  }, []);

  const exportJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(store, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trinketshelf-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [store]);

  const importJson = useCallback((rawText: string): boolean => {
    try {
      const parsed = JSON.parse(rawText) as Partial<PersistedStore>;
      if (!parsed || typeof parsed !== 'object') return false;
      setStore({
        version: 1,
        tracking: parsed.tracking ?? {},
        customItems: Array.isArray(parsed.customItems) ? parsed.customItems : [],
      });
      return true;
    } catch {
      return false;
    }
  }, []);

  return {
    allItems,
    trackingMap: store.tracking,
    getTracking,
    updateTracking,
    toggleStatusQuick,
    addCustomItem,
    deleteCustomItem,
    exportJson,
    importJson,
  };
}
