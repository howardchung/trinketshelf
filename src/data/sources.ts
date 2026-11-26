import type { CatalogItem, CollectionMeta } from '../types';

export interface ItemSourceLink {
  label: string;
  url: string;
  kind: 'source' | 'image';
}

function cleanQuery(text: string): string {
  return text
    .replace(/^#\S+\s+/, '')
    .replace(/\((?:1st Ed\.|Reverse Holo|Master Ball|Poké Ball|Secret|Unrefined)\)/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function getItemSourceLinks(
  item: CatalogItem,
  collection: CollectionMeta
): ItemSourceLink[] {
  const links: ItemSourceLink[] = [];
  const cid = item.collectionId;
  const qName = cleanQuery(item.name);
  const enc = encodeURIComponent;

  if (item.sourceUrl) {
    links.push({ label: 'Source', url: item.sourceUrl, kind: 'source' });
    return links;
  }

  if (cid === 'pkmn-csv4c') {
    const numMatch = item.name.match(/^#0*(\d+)/);
    const q = numMatch ? `csv4c ${qName} #${numMatch[1]}` : `csv4c ${qName}`;
    links.push({
      label: 'PriceCharting (CSV4C)',
      url: `https://www.pricecharting.com/search-products?q=${enc(q)}&type=prices`,
      kind: 'source',
    });
  } else if (cid.startsWith('pkmn-')) {
    const setId = cid.replace(/^pkmn-/, '');
    const setShort = collection.shortName ?? collection.name.replace(/^Pokémon TCG · /, '');
    links.push({
      label: 'TCGplayer',
      url: `https://www.tcgplayer.com/search/pokemon/product?productLineName=pokemon&q=${enc(`${qName} ${setShort}`)}&view=grid`,
      kind: 'source',
    });
    links.push({
      label: 'Pokémon TCG Data',
      url: `https://github.com/PokemonTCG/pokemon-tcg-data/blob/master/cards/en/${enc(setId)}.json`,
      kind: 'image',
    });
  } else if (cid.startsWith('sonny-')) {
    const officialUrl = cid.startsWith('sonny-hip-')
      ? 'https://www.sonnyangel.com/en/products/hippers/'
      : cid.startsWith('sonny-lim-')
      ? 'https://www.sonnyangel.com/en/products/limited-series/'
      : cid.startsWith('sonny-art-')
      ? 'https://www.sonnyangel.com/en/products/artist-collection/'
      : 'https://www.sonnyangel.com/en/products/mini-figure/';
    links.push({ label: 'Sonny Angel Official', url: officialUrl, kind: 'source' });

    if (item.imageSourceUrl?.includes('0561/4606/7644') || item.rarity === 'Secret' || item.rarity === 'Lucky') {
      links.push({
        label: 'Toysez',
        url: `https://toysez.com/search?q=${enc(`Sonny Angel ${qName}`)}`,
        kind: 'image',
      });
    } else if (item.imageSourceUrl?.includes('0866/2535/4046')) {
      links.push({
        label: 'Art Toy Familia',
        url: `https://arttoyfamilia.com/search?q=${enc(`Sonny Angel ${qName}`)}`,
        kind: 'image',
      });
    }
  } else if (cid.startsWith('sp-')) {
    links.push({
      label: 'Art Toy Familia',
      url: `https://arttoyfamilia.com/search?q=${enc(`Skullpanda ${qName}`)}`,
      kind: 'source',
    });
  } else if (cid.startsWith('tinytiny-')) {
    links.push({
      label: 'Art Toy Familia',
      url: `https://arttoyfamilia.com/search?q=${enc(`Tinytiny ${qName}`)}`,
      kind: 'source',
    });
  } else if (cid.startsWith('zs-')) {
    links.push({
      label: 'Art Toy Familia',
      url: `https://arttoyfamilia.com/search?q=${enc(`Zsiga ${qName}`)}`,
      kind: 'source',
    });
  } else if (cid.startsWith('sf-') || cid.startsWith('cc-')) {
    links.push({
      label: 'Kobee Japan',
      url: `https://store.kobeejapan.net/search?q=${enc(qName)}`,
      kind: 'source',
    });
  } else if (cid.startsWith('jc-')) {
    links.push({
      label: 'Jellycat',
      url: `https://us.jellycat.com/search?q=${enc(qName)}`,
      kind: 'source',
    });
    links.push({
      label: 'Baby Cubby',
      url: `https://www.babycubby.com/search?q=${enc(`Jellycat ${qName}`)}`,
      kind: 'image',
    });
  }

  return links;
}
