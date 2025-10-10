/**
 * API functions for analytics page
 * TODO: Implement actual API calls
 */

import { apiClient } from './api-client'

// Types
export interface Location {
  id: string
  name: string
  org_id: string
  created_at: string
}

export interface Run {
  id: string
  runId: string
  name?: string
  date: string
  location_id: string
  created_at: string
  status: string
  org_id: string
}

export interface StoreAnalytics {
  location_name: string
  summary: {
    total_transactions: number
    complete_transactions: number
    completion_rate: number
    avg_items_initial: number
    avg_items_final: number
    avg_item_increase: number
  }
  upselling: CategoryAnalytics
  upsizing: CategoryAnalytics
  addons: CategoryAnalytics
  operators: Record<string, OperatorAnalytics>
}

interface CategoryAnalytics {
  summary: {
    total_revenue: number
    conversion_rate: number
    total_successes: number
  }
  item_breakdown: Record<string, ItemStats>
}

interface OperatorAnalytics {
  upselling: CategoryAnalytics
  upsizing: CategoryAnalytics
  addons: CategoryAnalytics
}

interface ItemStats {
  opportunities: number
  offers: number
  successes: number
  revenue: number
  success_rate: number
  offer_rate: number
}

// API Functions
export async function fetchLocations(): Promise<Location[]> {
  try {
    return await apiClient.get<Location[]>('/api/locations')
  } catch (error) {
    console.error('Error fetching locations:', error)
    throw error
  }
}

export async function fetchRunsByLocation(locationId: string): Promise<Run[]> {
  try {
    return await apiClient.get<Run[]>(`/api/runs?location_id=${locationId}`)
  } catch (error) {
    console.error('Error fetching runs:', error)
    throw error
  }
}

export async function generateAnalytics(runId: string): Promise<StoreAnalytics> {
  try {
    return await apiClient.post<StoreAnalytics>(`/api/analytics/generate/${runId}`)
  } catch (error) {
    console.error('Error generating analytics:', error)
    throw error
  }
}

export async function fetchExistingAnalytics(runId: string): Promise<StoreAnalytics | null> {
  try {
    return await apiClient.get<StoreAnalytics>(`/api/analytics/${runId}`)
  } catch (error) {
    // Return null if analytics don't exist yet
    return null
  }
}

// Utility Functions
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}

export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}
