import type { PersistedStore } from '../types';

const OPFS_FILENAME = 'trinketshelf_store_v1.json';

let writeQueue: Promise<void> = Promise.resolve();

/**
 * Ask the browser to mark origin storage as persistent (protects localStorage,
 * Cache Storage, and OPFS against automatic eviction under storage pressure).
 */
export async function requestPersistentStorage(): Promise<boolean> {
  try {
    if (!navigator.storage || typeof navigator.storage.persist !== 'function') {
      return false;
    }
    if (typeof navigator.storage.persisted === 'function') {
      const already = await navigator.storage.persisted();
      if (already) return true;
    }
    return await navigator.storage.persist();
  } catch {
    return false;
  }
}

export async function readStoreFromOpfs(): Promise<PersistedStore | null> {
  try {
    if (!navigator.storage || typeof navigator.storage.getDirectory !== 'function') {
      return null;
    }
    const root = await navigator.storage.getDirectory();
    const handle = await root.getFileHandle(OPFS_FILENAME);
    const file = await handle.getFile();
    const text = await file.text();
    if (!text) return null;
    const parsed = JSON.parse(text) as Partial<PersistedStore>;
    return {
      version: 1,
      tracking: parsed.tracking ?? {},
      customItems: Array.isArray(parsed.customItems) ? parsed.customItems : [],
    };
  } catch {
    return null;
  }
}

/**
 * Serialize writes through a promise queue so rapid state updates never race
 * on the OPFS file handle.
 */
export function writeStoreToOpfs(store: PersistedStore): Promise<void> {
  const payload = JSON.stringify(store);
  writeQueue = writeQueue
    .then(async () => {
      if (!navigator.storage || typeof navigator.storage.getDirectory !== 'function') {
        return;
      }
      const root = await navigator.storage.getDirectory();
      const handle = await root.getFileHandle(OPFS_FILENAME, { create: true });
      if (typeof handle.createWritable !== 'function') {
        return;
      }
      const writable = await handle.createWritable();
      try {
        await writable.write(payload);
        await writable.close();
      } catch {
        try {
          await writable.abort();
        } catch {
          // ignore
        }
      }
    })
    .catch(() => {
      // OPFS unavailable or quota exceeded — localStorage remains primary
    });
  return writeQueue;
}
