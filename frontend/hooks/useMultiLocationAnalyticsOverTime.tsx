import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { DailyMetrics, AnalyticsOverTimeResponse } from '@/types/analytics'

interface UseMultiLocationAnalyticsOverTimeParams {
  locationIds?: string[]
  days?: number
  startDate?: string
  endDate?: string
  enabled?: boolean
}

export function useMultiLocationAnalyticsOverTime({
  locationIds,
  days = 30,
  startDate,
  endDate,
  enabled = true
}: UseMultiLocationAnalyticsOverTimeParams) {
  return useQuery<DailyMetrics[]>({
    queryKey: ['multiLocationAnalyticsOverTime', locationIds, days, startDate, endDate],
    queryFn: async () => {
      if (!locationIds || locationIds.length === 0) {
        return []
      }

      // If only one location, use the existing single location endpoint
      if (locationIds.length === 1) {
        const params = new URLSearchParams()
        if (days) params.append('days', days.toString())
        if (startDate) params.append('start_date', startDate)
        if (endDate) params.append('end_date', endDate)

        const queryString = params.toString()
        const url = `/api/analytics/location/${locationIds[0]}/over_time${queryString ? `?${queryString}` : ''}`

        const response = await apiClient.get<AnalyticsOverTimeResponse>(url)
        return response.data
      }

      // For multiple locations, we need to fetch each and aggregate
      // This could be optimized with a backend endpoint that handles multiple locations
      const allData: DailyMetrics[][] = await Promise.all(
        locationIds.map(async (locationId) => {
          const params = new URLSearchParams()
          if (days) params.append('days', days.toString())
          if (startDate) params.append('start_date', startDate)
          if (endDate) params.append('end_date', endDate)

          const queryString = params.toString()
          const url = `/api/analytics/location/${locationId}/over_time${queryString ? `?${queryString}` : ''}`

          const response = await apiClient.get<AnalyticsOverTimeResponse>(url)
          return response.data || []
        })
      )

      // Aggregate data by date
      const aggregatedData: { [date: string]: DailyMetrics } = {}

      allData.forEach(locationData => {
        locationData.forEach(dailyMetric => {
          const date = dailyMetric.date
          if (!aggregatedData[date]) {
            aggregatedData[date] = {
              date,
              upsell_revenue: 0,
              upsize_revenue: 0,
              addon_revenue: 0,
              total_revenue: 0,
              total_opportunities: 0,
              total_offers: 0,
              total_successes: 0,
              upsell_opportunities: 0,
              upsell_offers: 0,
              upsell_successes: 0,
              upsize_opportunities: 0,
              upsize_offers: 0,
              upsize_successes: 0,
              addon_opportunities: 0,
              addon_offers: 0,
              addon_successes: 0,
              overall_conversion_rate: 0,
              upsell_conversion_rate: 0,
              upsize_conversion_rate: 0,
              addon_conversion_rate: 0
            }
          }

          // Aggregate numeric values
          aggregatedData[date].upsell_revenue += dailyMetric.upsell_revenue || 0
          aggregatedData[date].upsize_revenue += dailyMetric.upsize_revenue || 0
          aggregatedData[date].addon_revenue += dailyMetric.addon_revenue || 0
          aggregatedData[date].total_revenue += dailyMetric.total_revenue || 0
          aggregatedData[date].total_opportunities += dailyMetric.total_opportunities || 0
          aggregatedData[date].total_offers += dailyMetric.total_offers || 0
          aggregatedData[date].total_successes += dailyMetric.total_successes || 0
          aggregatedData[date].upsell_opportunities += dailyMetric.upsell_opportunities || 0
          aggregatedData[date].upsell_offers += dailyMetric.upsell_offers || 0
          aggregatedData[date].upsell_successes += dailyMetric.upsell_successes || 0
          aggregatedData[date].upsize_opportunities += dailyMetric.upsize_opportunities || 0
          aggregatedData[date].upsize_offers += dailyMetric.upsize_offers || 0
          aggregatedData[date].upsize_successes += dailyMetric.upsize_successes || 0
          aggregatedData[date].addon_opportunities += dailyMetric.addon_opportunities || 0
          aggregatedData[date].addon_offers += dailyMetric.addon_offers || 0
          aggregatedData[date].addon_successes += dailyMetric.addon_successes || 0
        })
      })

      // Recalculate conversion rates based on aggregated data
      Object.values(aggregatedData).forEach(metrics => {
        metrics.overall_conversion_rate = metrics.total_offers > 0
          ? (metrics.total_successes / metrics.total_offers) * 100
          : 0
        metrics.upsell_conversion_rate = metrics.upsell_offers > 0
          ? (metrics.upsell_successes / metrics.upsell_offers) * 100
          : 0
        metrics.upsize_conversion_rate = metrics.upsize_offers > 0
          ? (metrics.upsize_successes / metrics.upsize_offers) * 100
          : 0
        metrics.addon_conversion_rate = metrics.addon_offers > 0
          ? (metrics.addon_successes / metrics.addon_offers) * 100
          : 0
      })

      // Convert to array and sort by date
      return Object.values(aggregatedData).sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )
    },
    enabled: enabled && (!locationIds || locationIds.length > 0),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  })
}