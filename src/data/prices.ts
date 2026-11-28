// Runtime-loaded USD retail / secondary-market prices (from /data/prices.json)
export const ITEM_PRICES: Record<string, number> = {};
// IDs whose price in prices.json fell back to baseline_price() estimates
export const ESTIMATED_PRICE_IDS = new Set<string>();

export function setItemPrices(prices: Record<string, number>): void {
  for (const key of Object.keys(ITEM_PRICES)) {
    delete ITEM_PRICES[key];
  }
  Object.assign(ITEM_PRICES, prices);
}

export function setEstimatedPriceIds(ids: string[]): void {
  ESTIMATED_PRICE_IDS.clear();
  for (const id of ids) {
    ESTIMATED_PRICE_IDS.add(id);
  }
}

export function isEstimatedPrice(
  itemId: string,
  customPrice?: number,
  fallbackPrice?: number
): boolean {
  if (typeof customPrice === 'number' && !Number.isNaN(customPrice) && customPrice >= 0) {
    return false;
  }
  if (ESTIMATED_PRICE_IDS.has(itemId)) {
    return true;
  }
  if (itemId in ITEM_PRICES) {
    return false;
  }
  if (typeof fallbackPrice === 'number' && !Number.isNaN(fallbackPrice) && fallbackPrice >= 0) {
    return false;
  }
  return true;
}

export function getItemPrice(
  itemId: string,
  customPrice?: number,
  fallbackPrice?: number
): number {
  if (typeof customPrice === 'number' && !Number.isNaN(customPrice) && customPrice >= 0) {
    return customPrice;
  }
  if (itemId in ITEM_PRICES) {
    return ITEM_PRICES[itemId];
  }
  if (typeof fallbackPrice === 'number' && !Number.isNaN(fallbackPrice) && fallbackPrice >= 0) {
    return fallbackPrice;
  }
  return 15;
}

export function formatUsd(amount: number): string {
  return amount.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

export function formatUsdWhole(amount: number): string {
  return Math.round(amount).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}
