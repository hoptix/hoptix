import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { DailyMetrics, AnalyticsOverTimeResponse } from '@/types/analytics'

interface UseLocationAnalyticsOverTimeParams {
  locationId?: string
  days?: number
  startDate?: string
  endDate?: string
  enabled?: boolean
}

export function useLocationAnalyticsOverTime({
  locationId,
  days = 30,
  startDate,
  endDate,
  enabled = true
}: UseLocationAnalyticsOverTimeParams) {
  return useQuery<DailyMetrics[]>({
    queryKey: ['locationAnalyticsOverTime', locationId, days, startDate, endDate],
    queryFn: async () => {
      if (!locationId) {
        throw new Error('Location ID is required')
      }

      const params = new URLSearchParams()
      if (days) params.append('days', days.toString())
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

      const queryString = params.toString()
      const url = `/api/analytics/location/${locationId}/over_time${queryString ? `?${queryString}` : ''}`

      const response = await apiClient.get<AnalyticsOverTimeResponse>(url)
      return response.data
    },
    enabled: enabled && !!locationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  })
}
