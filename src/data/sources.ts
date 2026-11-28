import type { CatalogItem } from '../types';

export interface ProvenanceLink {
  kind: 'source' | 'image' | 'price';
  label: string;
  url: string;
}

const HOST_LABELS: Record<string, string> = {
  'arttoyfamilia.com': 'Art Toy Familia',
  'toysez.com': 'Toysez',
  'sonnyangel.com': 'Sonny Angel Official',
  'store.kobeejapan.net': 'Kobee Japan',
  'babycubby.com': 'Baby Cubby',
  'pacifierkids.com': 'Pacifier Kids',
  'faoschwarz.com': 'FAO Schwarz',
  'kidly.co.uk': 'Kidly',
  'activebaby.ca': 'Active Baby',
  'kolkid.ca': 'Kolkid',
  'snugglebugz.ca': 'Snuggle Bugz',
  'indigo.ca': 'Indigo',
  'us.jellycat.com': 'Jellycat',
  'jellyjournal.com': 'Jelly Journal',
  'jellycat-crew.fandom.com': 'Jellycat Crew Wiki',
  'sylvanianfamilies.fandom.com': 'Sylvanian Wiki',
  'pricecharting.com': 'PriceCharting',
  'tcgplayer.com': 'TCGplayer',
  'github.com': 'Pokémon TCG Data',
  'images.pokemontcg.io': 'Pokémon TCG Images',
  'cdn.shopify.com': 'Shopify CDN',
};

function labelForUrl(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return HOST_LABELS[host] ?? host;
  } catch {
    return url;
  }
}

export function getItemProvenanceLinks(item: CatalogItem): ProvenanceLink[] {
  const links: ProvenanceLink[] = [];
  const cid = item.collectionId;

  const sourceUrl =
    item.sourceUrl ??
    (cid.startsWith('pkmn-') && cid !== 'pkmn-csv4c'
      ? `https://github.com/PokemonTCG/pokemon-tcg-data/blob/master/cards/en/${encodeURIComponent(cid.replace(/^pkmn-/, ''))}.json`
      : undefined);

  const imageUrl =
    item.imageSourceUrl ??
    (item.image.startsWith('http://') || item.image.startsWith('https://') ? item.image : undefined);

  const priceUrl =
    item.priceSourceUrl ??
    (cid.startsWith('pkmn-') && cid !== 'pkmn-csv4c'
      ? `https://www.tcgplayer.com/search/pokemon/product?productLineName=pokemon&q=${encodeURIComponent(item.name.replace(/^#\S+\s+/, ''))}&view=grid`
      : undefined);

  if (sourceUrl) {
    links.push({ kind: 'source', label: `Source: ${labelForUrl(sourceUrl)}`, url: sourceUrl });
  }
  if (imageUrl) {
    links.push({ kind: 'image', label: `Image: ${labelForUrl(imageUrl)}`, url: imageUrl });
  }
  if (priceUrl) {
    links.push({ kind: 'price', label: `Price: ${labelForUrl(priceUrl)}`, url: priceUrl });
  }

  return links;
}
