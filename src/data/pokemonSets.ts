import type { CollectionId } from '../types';

export interface PokemonSetMeta {
  id: CollectionId;
  setId: string;
  name: string;
  shortName: string;
  era: string;
  releaseDate: string;
  cardCount: number;
  grandMasterCount: number;
  estimatedTotal: number;
  logo: string;
  symbol: string;
  subtitle: string;
  maker: string;
  accent: string;
  accentSoft: string;
  accentText: string;
  emoji: string;
}

export const POKEMON_SETS: PokemonSetMeta[] = [];

export let POKEMON_TOTAL_GM_CARDS = 0;

export function setPokemonSets(sets: PokemonSetMeta[]): void {
  POKEMON_SETS.length = 0;
  POKEMON_SETS.push(...sets);
  POKEMON_TOTAL_GM_CARDS = sets.reduce((sum, s) => sum + s.grandMasterCount, 0);
}
