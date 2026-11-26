export type CollectionId =
  | 'sonny-animal-1'
  | 'sonny-animal-2'
  | 'sonny-animal-3'
  | 'sonny-animal-4'
  | 'sonny-fruit'
  | 'sonny-vegetable'
  | 'sonny-marine'
  | 'sonny-flower'
  | 'sonny-sweets'
  | 'sonny-snack'
  | 'sonny-flower-gift'
  | 'sonny-birthday-bear'
  | 'sonny-birthday-gift'
  | `sonny-lim-${string}`
  | `sonny-hip-${string}`
  | `sonny-unr-${string}`
  | `sonny-art-${string}`
  | `sonny-spc-${string}`
  | `sonny-vin-${string}`
  | `sp-${string}`
  | 'tinytiny-prologue'
  | 'tinytiny-sugar-therapy'
  | 'tinytiny-mixed'
  | 'tinytiny-standalone'
  | `sf-${string}`
  | `zs-${string}`
  | `jc-${string}`
  | `pkmn-${string}`;

export type ItemStatus = 'unowned' | 'owned' | 'wishlist' | 'duplicate';

export type ItemRarity = 'Regular' | 'Special' | 'Lucky' | 'Secret';

export type TopLevelShelfId =
  | 'sonny-angel'
  | 'skullpanda'
  | 'tinytiny'
  | 'sylvanian-families'
  | 'zsiga'
  | 'jellycat'
  | 'pokemon-tcg';

export interface CollectionMeta {
  id: CollectionId;
  name: string;
  shortName?: string;
  parentShelf?: 'sonny-angel';
  sonnyCategory?: 'regular' | 'limited' | 'hippers' | 'unrefined' | 'artist' | 'special' | 'vintage';
  skullpandaCategory?: 'blind-box' | 'plush' | 'mixed';
  sylvanianCategory?: 'blind-bag' | 'blind-box';
  subtitle: string;
  maker: string;
  accent: string;
  accentSoft: string;
  accentText: string;
  emoji: string;
}

export interface CatalogItem {
  id: string;
  collectionId: CollectionId;
  name: string;
  series: string;
  rarity: ItemRarity;
  image: string;
  price?: number;
  sourceUrl?: string;
  imageSourceUrl?: string;
  isCustom?: boolean;
}

export interface ItemTrackingState {
  status: ItemStatus;
  quantity: number;
  notes: string;
  acquiredDate?: string;
  customPrice?: number;
  cachedPrice?: number;
}

export interface PersistedStore {
  version: number;
  tracking: Record<string, ItemTrackingState>;
  customItems: CatalogItem[];
}
