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
  location_count?: number
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
  locationIds?: string[]
  startDate?: string
  endDate?: string
  comparePrevious?: boolean
  enabled?: boolean
}

export function useDashboardAnalytics({
  locationId,
  locationIds,
  startDate,
  endDate,
  comparePrevious = true,
  enabled = true
}: UseDashboardAnalyticsParams) {
  // Determine if we should use multi-location endpoint
  const useMultiLocation = locationIds && locationIds.length > 0
  const useSingleLocation = locationId && !useMultiLocation

  return useQuery<DashboardAnalyticsResponse>({
    queryKey: ['dashboardAnalytics', locationId, locationIds, startDate, endDate, comparePrevious],
    queryFn: async () => {
      if (!useSingleLocation && !useMultiLocation) {
        // Return empty data when no locations selected
        return {
          period: { start_date: '', end_date: '', days: 0, location_count: 0 },
          metrics: {
            operator_revenue: 0,
            offer_rate: 0,
            conversion_rate: 0,
            items_converted: 0
          },
          raw_data: {
            total_opportunities: 0,
            total_offers: 0,
            total_successes: 0
          }
        }
      }

      const params = new URLSearchParams()

      if (useMultiLocation) {
        // Use multi-location endpoint
        locationIds!.forEach(id => params.append('location_ids[]', id))
      }

      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      params.append('compare_previous', comparePrevious.toString())

      const queryString = params.toString()

      let url: string
      if (useMultiLocation) {
        // Use new multi-location endpoint
        url = `/api/analytics/dashboard${queryString ? `?${queryString}` : ''}`
      } else {
        // Use single location endpoint for backward compatibility
        url = `/api/analytics/location/${locationId}/dashboard${queryString ? `?${queryString}` : ''}`
      }

      const response = await apiClient.get<{ success: boolean; data: DashboardAnalyticsResponse }>(url)
      return response.data
    },
    enabled: enabled && (!!useSingleLocation || !!useMultiLocation),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  })
}
