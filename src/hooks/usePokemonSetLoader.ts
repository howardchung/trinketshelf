import { useEffect, useState } from 'react';
import type { CatalogItem } from '../types';

const setCache = new Map<string, CatalogItem[]>();

export function usePokemonSetLoader(setId: string | null) {
  const [cards, setCards] = useState<CatalogItem[]>(() =>
    setId ? setCache.get(setId) ?? [] : []
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!setId) {
      setCards([]);
      setLoading(false);
      return;
    }

    const cached = setCache.get(setId);
    if (cached) {
      setCards(cached);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    fetch(`/data/pokemon/${setId}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${setId}`);
        return res.json() as Promise<CatalogItem[]>;
      })
      .then((data) => {
        setCache.set(setId, data);
        if (!cancelled) {
          setCards(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCards([]);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [setId]);

  return { cards, loading };
}
