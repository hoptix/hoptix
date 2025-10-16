import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { ITEM_NAMES_ENDPOINT, ITEM_NAMES_QUERY_KEY, type ItemNamesMap } from "@/constants/items"

interface ItemNamesResponse {
  success: boolean
  data: ItemNamesMap
}

export function useItemNames(enabled: boolean = true) {
  return useQuery({
    queryKey: [ITEM_NAMES_QUERY_KEY],
    queryFn: async (): Promise<ItemNamesMap> => {
      const resp = await apiClient.get<ItemNamesResponse>(ITEM_NAMES_ENDPOINT)
      return resp.data || {}
    },
    enabled,
    staleTime: 60 * 60 * 1000, // 1 hour
    refetchOnWindowFocus: false,
  })
}


