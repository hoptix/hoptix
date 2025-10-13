import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/contexts/authContext"

interface SizeMetrics {
  upsell_base: number;
  upsell_candidates: number;
  upsell_offered: number;
  upsell_success: number;
  upsell_base_sold: number;
  upsell_base_offers: number;
  upsize_base: number;
  upsize_candidates: number;
  upsize_offered: number;
  upsize_success: number;
  upsize_base_sold: number;
  upsize_base_offers: number;
  addon_base: number;
  addon_candidates: number;
  addon_offered: number;
  addon_success: number;
  addon_base_sold: number;
  addon_base_offers: number;
}

interface ItemAnalytics {
  name: string
  sizes: Record<string, SizeMetrics>
  transitions: {
    "1_to_2": number
    "1_to_3": number
    "2_to_3": number
  }
}

interface DetailedAnalytics {
  [itemId: string]: ItemAnalytics
}

interface OperatorMetrics {
  total_opportunities?: number
  total_offers?: number
  total_successes?: number
  total_revenue?: number
  offer_rate?: number
  success_rate?: number
  conversion_rate?: number
  avg_revenue_per_success?: number
}

interface RunAnalytics {
  run_id: string
  run_date: string
  location_id: string
  location_name: string
  org_name: string
  total_transactions: number
  complete_transactions: number
  completion_rate: number
  avg_items_initial: number
  avg_items_final: number
  avg_item_increase: number

  // Upselling metrics
  upsell_opportunities: number
  upsell_offers: number
  upsell_successes: number
  upsell_conversion_rate: number
  upsell_revenue: number

  // Upsizing metrics
  upsize_opportunities: number
  upsize_offers: number
  upsize_successes: number
  upsize_conversion_rate: number
  upsize_revenue: number

  // Add-on metrics
  addon_opportunities: number
  addon_offers: number
  addon_successes: number
  addon_conversion_rate: number
  addon_revenue: number

  // Overall metrics
  total_opportunities: number
  total_offers: number
  total_successes: number
  overall_conversion_rate: number
  total_revenue: number

  // Detailed analytics with per-item breakdown
  detailed_analytics?: string // JSON string containing item analytics
}

const fetchRunAnalytics = async (runId: string): Promise<{ success: boolean; data: RunAnalytics }> => {
  return apiClient.get<{ success: boolean; data: RunAnalytics }>(`/api/analytics/run/${runId}`)
}

export function useGetRunAnalytics(runId: string, enabled: boolean = true) {
  const { user } = useAuth()

  return useQuery({
    queryKey: ['run-analytics', user?.id, runId],
    queryFn: () => fetchRunAnalytics(runId),
    enabled: !!runId && !!user && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - analytics don't change often
    refetchOnWindowFocus: false,
  })
}

// Worker Analytics type (same structure as RunAnalytics but with worker_id)
interface WorkerAnalytics extends RunAnalytics {
  worker_id: string
}

// Hook to fetch worker analytics for a run
export function useGetWorkerAnalytics(runId: string, workerId?: string) {
  const { user } = useAuth()

  return useQuery({
    queryKey: ['workerAnalytics', user?.id, runId, workerId],
    queryFn: async (): Promise<{ success: boolean; data: WorkerAnalytics[] }> => {
      const params = workerId ? `?worker_id=${workerId}` : ''
      return apiClient.get<{ success: boolean; data: WorkerAnalytics[] }>(`/api/analytics/run/${runId}/workers${params}`)
    },
    enabled: !!runId && !!user,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  })
}

// Hook to fetch all worker analytics for the data table
export function useGetAllWorkerAnalytics() {
  const { user } = useAuth()

  return useQuery({
    queryKey: ['allWorkerAnalytics', user?.id],
    queryFn: async (): Promise<{ success: boolean; data: WorkerAnalytics[] }> => {
      return apiClient.get<{ success: boolean; data: WorkerAnalytics[] }>('/api/analytics/workers')
    },
    enabled: !!user,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  })
}

// Range Analytics Response (same structure as RunAnalytics but for a date range)
interface RangeAnalyticsResponse {
  success: boolean
  data: {
    analytics: RunAnalytics
    worker_analytics: WorkerAnalytics[]
  }
}

// Hook to fetch analytics for a custom date range across multiple locations
export function useGetRangeAnalytics(
  locationIds: string[],
  startDate: string | null,
  endDate: string | null,
  enabled: boolean = true
) {
  const { user } = useAuth()

  return useQuery({
    queryKey: ['range-analytics', user?.id, locationIds, startDate, endDate],
    queryFn: async (): Promise<RangeAnalyticsResponse> => {
      // Build query parameters
      const params = new URLSearchParams()

      // Add location_ids[] as multiple params
      locationIds.forEach(id => {
        params.append('location_ids[]', id)
      })

      // Add date range if provided
      if (startDate) {
        params.append('start_date', startDate)
      }
      if (endDate) {
        params.append('end_date', endDate)
      }

      return apiClient.get<RangeAnalyticsResponse>(`/api/analytics/range-report?${params.toString()}`)
    },
    enabled: !!user && enabled && locationIds.length > 0 && !!startDate && !!endDate,
    staleTime: 5 * 60 * 1000, // 5 minutes - range analytics may change more frequently
    refetchOnWindowFocus: false,
  })
}

export type { RunAnalytics, OperatorMetrics, ItemAnalytics, SizeMetrics, DetailedAnalytics, WorkerAnalytics, RangeAnalyticsResponse }
