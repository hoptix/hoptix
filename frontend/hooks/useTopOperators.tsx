import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface OperatorMetrics {
  total_transactions: number
  total_revenue: number
  offer_rate: number
  conversion_rate: number
  total_opportunities: number
  total_offers: number
  total_successes: number
  run_count: number
}

export interface OperatorBreakdown {
  upsell: {
    opportunities: number
    offers: number
    successes: number
    revenue: number
  }
  upsize: {
    opportunities: number
    offers: number
    successes: number
    revenue: number
  }
  addon: {
    opportunities: number
    offers: number
    successes: number
    revenue: number
  }
}

export interface MonthlyFeedbackIssue {
  issue: string
  transaction_ids: string[]
}

export interface MonthlyFeedbackStrength {
  strength: string
  transaction_ids: string[]
}

export interface MonthlyFeedback {
  top_issues: MonthlyFeedbackIssue[]
  top_strengths: MonthlyFeedbackStrength[]
  recommended_actions: string[]
  overall_rating: 'Excellent' | 'Good' | 'Fair' | 'Poor' | string
}

export interface TopOperator {
  rank: number
  worker_id: string
  name: string
  monthly_feedback: string | null  // Raw JSON string from API
  monthly_feedback_parsed?: MonthlyFeedback | null  // Parsed version for UI
  metrics: OperatorMetrics
  breakdown: OperatorBreakdown
}

interface TopOperatorsResponse {
  data: TopOperator[]
  period: {
    start_date: string
    end_date: string
    location_count: number
  }
}

interface UseTopOperatorsParams {
  locationIds?: string[]
  startDate?: string
  endDate?: string
  limit?: number
  enabled?: boolean
}

export function useTopOperators({
  locationIds,
  startDate,
  endDate,
  limit = 5,
  enabled = true
}: UseTopOperatorsParams) {
  return useQuery<TopOperator[]>({
    queryKey: ['topOperators', locationIds, startDate, endDate, limit],
    queryFn: async () => {
      const params = new URLSearchParams()

      if (locationIds && locationIds.length > 0) {
        locationIds.forEach(id => params.append('location_ids[]', id))
      }

      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      params.append('limit', limit.toString())

      const queryString = params.toString()
      const url = `/api/analytics/top-operators${queryString ? `?${queryString}` : ''}`

      const response = await apiClient.get<{ success: boolean; data: TopOperator[] }>(url)
      return response.data
    },
    enabled: enabled && (!locationIds || locationIds.length > 0),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}