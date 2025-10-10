/**
 * Analytics Type Definitions
 * Shared types for analytics data across the application
 */

// ============================================================================
// Metric Types
// ============================================================================

export type MetricType = 'revenue' | 'opportunities' | 'offers' | 'successes' | 'conversion_rate'

export type CategoryType = 'upsell' | 'upsize' | 'addon'

export type ViewMode = 'stacked' | 'individual'

// ============================================================================
// Category Metrics
// ============================================================================

/**
 * Metrics for a single category (upsell, upsize, or addon)
 */
export interface CategoryMetrics {
  opportunities: number
  offers: number
  successes: number
  conversion_rate: number
  revenue: number
}

// ============================================================================
// Daily Metrics (Time Series Data)
// ============================================================================

/**
 * Complete analytics metrics for a single day
 * Matches the backend response from /analytics/location/<location_id>/over_time
 */
export interface DailyMetrics {
  date: string

  // Revenue metrics (existing - backward compatible)
  upsell_revenue: number
  upsize_revenue: number
  addon_revenue: number
  total_revenue: number

  // Overall aggregate metrics
  total_opportunities: number
  total_offers: number
  total_successes: number
  overall_conversion_rate: number

  // Upsell category metrics
  upsell_opportunities: number
  upsell_offers: number
  upsell_successes: number
  upsell_conversion_rate: number

  // Upsize category metrics
  upsize_opportunities: number
  upsize_offers: number
  upsize_successes: number
  upsize_conversion_rate: number

  // Addon category metrics
  addon_opportunities: number
  addon_offers: number
  addon_successes: number
  addon_conversion_rate: number
}

/**
 * Structured version of DailyMetrics for easier consumption
 * Used internally by components after transformation
 */
export interface StructuredDailyMetrics {
  date: string
  total: {
    revenue: number
    opportunities: number
    offers: number
    successes: number
    conversion_rate: number
  }
  upsell: CategoryMetrics
  upsize: CategoryMetrics
  addon: CategoryMetrics
}

// ============================================================================
// API Response Types
// ============================================================================

export interface AnalyticsOverTimeResponse {
  success: boolean
  data: DailyMetrics[]
  period: {
    start_date: string
    end_date: string
    days: number
  }
}

// ============================================================================
// Chart Configuration
// ============================================================================

/**
 * Configuration for chart data keys based on metric type and category
 */
export interface ChartDataKey {
  key: string
  label: string
  color: string
}

/**
 * Filter state for the analytics chart
 */
export interface ChartFilterState {
  metricType: MetricType
  selectedCategories: Set<CategoryType>
  viewMode: ViewMode
  timeRange: string
}

/**
 * Transformed chart data point (what Recharts consumes)
 */
export interface ChartDataPoint {
  date: string
  [key: string]: string | number // Dynamic keys based on selected categories
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Helper type to extract metric value from DailyMetrics based on category and metric type
 */
export type MetricExtractor = (
  data: DailyMetrics,
  category: CategoryType,
  metricType: MetricType
) => number

/**
 * URL search params for shareable chart state
 */
export interface ChartUrlParams {
  metric?: MetricType
  categories?: string
  view?: ViewMode
  range?: string
}
