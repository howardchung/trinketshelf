import type { CatalogItem } from '../types';

export interface ItemImageProvenance {
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
  'pricecharting.com': 'PriceCharting',
  'github.com': 'Pokémon TCG Data',
};

function labelForUrl(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return HOST_LABELS[host] ?? host;
  } catch {
    return 'Image Source';
  }
}

function cleanQuery(text: string): string {
  return text
    .replace(/^#\S+\s+/, '')
    .replace(/\((?:1st Ed\.|Reverse Holo|Master Ball|Poké Ball|Secret|Unrefined)\)/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function getItemImageProvenance(item: CatalogItem): ItemImageProvenance | null {
  if (item.image.endsWith('.svg')) {
    return null;
  }

  if (item.sourceUrl) {
    return {
      label: labelForUrl(item.sourceUrl),
      url: item.sourceUrl,
    };
  }

  const cid = item.collectionId;
  const qName = cleanQuery(item.name);
  const enc = encodeURIComponent;

  if (cid === 'pkmn-csv4c') {
    const numMatch = item.name.match(/^#0*(\d+)/);
    const q = numMatch ? `csv4c ${qName} #${numMatch[1]}` : `csv4c ${qName}`;
    return {
      label: 'PriceCharting',
      url: `https://www.pricecharting.com/search-products?q=${enc(q)}&type=prices`,
    };
  }

  if (cid.startsWith('pkmn-')) {
    const setId = cid.replace(/^pkmn-/, '');
    return {
      label: 'Pokémon TCG Data',
      url: `https://github.com/PokemonTCG/pokemon-tcg-data/blob/master/cards/en/${enc(setId)}.json`,
    };
  }

  if (cid.startsWith('sonny-')) {
    if (item.imageSourceUrl?.includes('0561/4606/7644') || item.rarity === 'Secret' || item.rarity === 'Lucky') {
      return {
        label: 'Toysez',
        url: `https://toysez.com/search?q=${enc(`Sonny Angel ${qName}`)}`,
      };
    }
    if (item.imageSourceUrl?.includes('0866/2535/4046')) {
      return {
        label: 'Art Toy Familia',
        url: `https://arttoyfamilia.com/search?q=${enc(`Sonny Angel ${qName}`)}`,
      };
    }
    const officialUrl = cid.startsWith('sonny-hip-')
      ? 'https://www.sonnyangel.com/en/products/hippers/'
      : cid.startsWith('sonny-lim-')
      ? 'https://www.sonnyangel.com/en/products/limited-series/'
      : cid.startsWith('sonny-art-')
      ? 'https://www.sonnyangel.com/en/products/artist-collection/'
      : 'https://www.sonnyangel.com/en/products/mini-figure/';
    return { label: 'Sonny Angel Official', url: officialUrl };
  }

  if (cid.startsWith('sp-')) {
    return {
      label: 'Art Toy Familia',
      url: `https://arttoyfamilia.com/search?q=${enc(`Skullpanda ${qName}`)}`,
    };
  }

  if (cid.startsWith('tinytiny-')) {
    return {
      label: 'Art Toy Familia',
      url: `https://arttoyfamilia.com/search?q=${enc(`Tinytiny ${qName}`)}`,
    };
  }

  if (cid.startsWith('zs-')) {
    return {
      label: 'Art Toy Familia',
      url: `https://arttoyfamilia.com/search?q=${enc(`Zsiga ${qName}`)}`,
    };
  }

  if (cid.startsWith('sf-')) {
    return {
      label: 'Kobee Japan',
      url: `https://store.kobeejapan.net/search?q=${enc(qName)}`,
    };
  }

  if (cid.startsWith('jc-')) {
    return {
      label: 'Baby Cubby',
      url: `https://www.babycubby.com/search?q=${enc(`Jellycat ${qName}`)}`,
    };
  }

  return null;
}
