import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

interface DashboardMetrics {
  operator_revenue: number
  offer_rate: number
  conversion_rate: number
  items_converted: number
}

interface DashboardTrends {
  operator_revenue_change: number
  offer_rate_change: number
  conversion_rate_change: number
  items_converted_change: number
}

interface DashboardPeriod {
  start_date: string
  end_date: string
  days: number
}

interface DashboardAnalyticsResponse {
  period: DashboardPeriod
  metrics: DashboardMetrics
  trends?: DashboardTrends
  previous_period?: {
    start_date: string
    end_date: string
    metrics: DashboardMetrics
  }
  raw_data: {
    total_opportunities: number
    total_offers: number
    total_successes: number
  }
}

interface UseDashboardAnalyticsParams {
  locationId?: string
  startDate?: string
  endDate?: string
  comparePrevious?: boolean
  enabled?: boolean
}

export function useDashboardAnalytics({
  locationId,
  startDate,
  endDate,
  comparePrevious = true,
  enabled = true
}: UseDashboardAnalyticsParams) {
  return useQuery<DashboardAnalyticsResponse>({
    queryKey: ['dashboardAnalytics', locationId, startDate, endDate, comparePrevious],
    queryFn: async () => {
      if (!locationId) {
        throw new Error('Location ID is required')
      }

      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      params.append('compare_previous', comparePrevious.toString())

      const queryString = params.toString()
      const url = `/api/analytics/location/${locationId}/dashboard${queryString ? `?${queryString}` : ''}`

      const response = await apiClient.get<{ success: boolean; data: DashboardAnalyticsResponse }>(url)
      return response.data
    },
    enabled: enabled && !!locationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  })
}
