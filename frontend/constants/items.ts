// Keys and constants for item name lookups

export const ITEM_NAMES_QUERY_KEY = 'item-names-map'
export const ITEM_NAMES_ENDPOINT = '/api/analytics/item-names-map'

// Fallback used when a name is missing
export const UNKNOWN_ITEM_NAME = 'Unknown Item'

export type ItemNamesMap = Record<string, string>


