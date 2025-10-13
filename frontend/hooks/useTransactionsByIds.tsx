import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { TopTransaction } from './useTopTransactions'

interface UseTransactionsByIdsParams {
  transactionIds?: string[]
  locationIds?: string[]
  enabled?: boolean
}

export function useTransactionsByIds({
  transactionIds,
  locationIds,
  enabled = true
}: UseTransactionsByIdsParams) {
  return useQuery<TopTransaction[]>({
    queryKey: ['transactionsByIds', transactionIds, locationIds],
    queryFn: async () => {
      // Return empty array if no transaction IDs provided
      if (!transactionIds || transactionIds.length === 0) {
        return []
      }

      if (!locationIds || locationIds.length === 0) {
        return []
      }

      const params = new URLSearchParams()

      // Add all transaction IDs
      transactionIds.forEach(id => params.append('transaction_ids[]', id))

      // Add all location IDs
      locationIds.forEach(id => params.append('location_ids[]', id))

      const queryString = params.toString()
      const url = `/api/analytics/transactions-by-ids${queryString ? `?${queryString}` : ''}`

      const response = await apiClient.get<{ success: boolean; data: TopTransaction[] }>(url)
      return response.data
    },
    enabled: enabled &&
             !!transactionIds &&
             transactionIds.length > 0 &&
             !!locationIds &&
             locationIds.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
