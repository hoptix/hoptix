import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"

interface SizeMetrics {
  upsell_base: number
  upsell_candidates: number
  upsell_offered: number
  upsell_success: number
  upsize_base: number
  upsize_candidates: number
  upsize_offered: number
  upsize_success: number
  addon_base: number
  addon_candidates: number
  addon_offered: number
  addon_success: number
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
  return useQuery({
    queryKey: ['run-analytics', runId],
    queryFn: () => fetchRunAnalytics(runId),
    enabled: !!runId && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - analytics don't change often
    refetchOnWindowFocus: false,
  })
}

// Worker Analytics type (same structure as RunAnalytics but with worker_id)
interface WorkerAnalytics extends RunAnalytics {
  worker_id: string
}

// Hook to fetch worker analytics for a run
export function useGetWorkerAnalytics(runId: string) {
  return useQuery({
    queryKey: ['workerAnalytics', runId],
    queryFn: async (): Promise<{ success: boolean; data: WorkerAnalytics[] }> => {
      return apiClient.get<{ success: boolean; data: WorkerAnalytics[] }>(`/api/analytics/run/${runId}/workers`)
    },
    enabled: !!runId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  })
}

// Hook to fetch all worker analytics for the data table
export function useGetAllWorkerAnalytics() {
  return useQuery({
    queryKey: ['allWorkerAnalytics'],
    queryFn: async (): Promise<{ success: boolean; data: WorkerAnalytics[] }> => {
      return apiClient.get<{ success: boolean; data: WorkerAnalytics[] }>('/api/analytics/workers')
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  })
}

export type { RunAnalytics, OperatorMetrics, ItemAnalytics, SizeMetrics, DetailedAnalytics, WorkerAnalytics }
