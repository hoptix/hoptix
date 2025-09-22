"use client"

import { useQuery } from "@tanstack/react-query"

export interface TopTransaction {
  transaction_id: string
  run_id: string
  employee_name: string
  start_time: string
  end_time: string
  duration_minutes: number | null
  composite_score: number
  base_score: number
  rank: number
  performance_metrics: {
    upselling: {
      offers: number
      successes: number
      success_rate: number
    }
    upsizing: {
      offers: number
      successes: number
      success_rate: number
    }
    addons: {
      offers: number
      successes: number
      success_rate: number
    }
  }
  items_initial: string
  items_after: string
  feedback: string
  transcript_preview: string
  special_flags: {
    mobile_order: boolean
    coupon_used: boolean
  }
}

export interface TopTransactionsResponse {
  success: boolean
  data: {
    date: string
    location_id: string
    top_transactions: TopTransaction[]
    total_transactions_analyzed: number
    complete_transactions_analyzed: number
    criteria_explanation: {
      algorithm: string
      weights: {
        base_score: string
        upselling_success: string
        upsizing_success: string
        addon_success: string
      }
      bonuses: string[]
    }
  }
}

export function useGetTopTransactions(
  locationId: string,
  date?: string,
  limit: number = 5,
  enabled: boolean = true
) {
  const baseUrl = typeof window !== 'undefined' 
    ? (window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin)
    : 'http://localhost:8000'

  return useQuery<TopTransactionsResponse>({
    queryKey: ['topTransactions', locationId, date, limit],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (date) params.append('date', date)
      if (limit !== 5) params.append('limit', limit.toString())
      
      const queryString = params.toString()
      const url = `${baseUrl}/api/analytics/location/${locationId}/top-transactions/daily${queryString ? `?${queryString}` : ''}`
      
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('Failed to fetch top transactions')
      }
      return response.json()
    },
    enabled: enabled && !!locationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  })
}
