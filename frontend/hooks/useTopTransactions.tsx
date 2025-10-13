import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface TransactionGrading {
  upsell: {
    opportunities: number
    offers: number
    successes: number
  }
  upsize: {
    opportunities: number
    offers: number
    successes: number
  }
  addon: {
    opportunities: number
    offers: number
    successes: number
  }
}

export interface TopTransaction {
  id: string
  run_id: string
  worker_id: string
  run_date: string
  transaction_text: string
  ai_feedback: string
  grading: TransactionGrading
  begin_time: string
}

interface TopTransactionsResponse {
  data: TopTransaction[]
  period: {
    start_date: string
    end_date: string
    location_count: number
  }
}

interface UseTopTransactionsParams {
  locationIds?: string[]
  startDate?: string
  endDate?: string
  workerId?: string
  limit?: number
  enabled?: boolean
}

export function useTopTransactions({
  locationIds,
  startDate,
  endDate,
  workerId,
  limit = 10,
  enabled = true
}: UseTopTransactionsParams) {
  return useQuery<TopTransaction[]>({
    queryKey: ['topTransactions', locationIds, startDate, endDate, workerId, limit],
    queryFn: async () => {
      const params = new URLSearchParams()

      if (locationIds && locationIds.length > 0) {
        locationIds.forEach(id => params.append('location_ids[]', id))
      }

      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      if (workerId) params.append('worker_id', workerId)
      params.append('limit', limit.toString())

      const queryString = params.toString()
      const url = `/api/analytics/top-transactions${queryString ? `?${queryString}` : ''}`

      const response = await apiClient.get<{ success: boolean; data: TopTransaction[] }>(url)
      return response.data
    },
    enabled: enabled && (!locationIds || locationIds.length > 0),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}