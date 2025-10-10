import { useMemo } from 'react'
import type { DailyMetrics, MetricType, CategoryType, ChartDataPoint } from '@/types/analytics'

interface UseChartDataTransformParams {
  data: DailyMetrics[] | undefined
  metricType: MetricType
  selectedCategories: Set<CategoryType>
}

interface ChartConfig {
  [key: string]: {
    label: string
    color: string
  }
}

const CATEGORY_COLORS = {
  upsell: 'hsl(var(--chart-1))',
  upsize: 'hsl(var(--chart-2))',
  addon: 'hsl(var(--chart-3))',
} as const

const CATEGORY_LABELS = {
  upsell: 'Upsell',
  upsize: 'Upsize',
  addon: 'Add-ons',
} as const

/**
 * Custom hook to transform analytics data for chart rendering
 * Handles data transformation based on selected metric type and categories
 */
export function useChartDataTransform({
  data,
  metricType,
  selectedCategories,
}: UseChartDataTransformParams) {
  // Transform data based on metric type and selected categories
  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!data || data.length === 0) {
      return []
    }

    return data.map((day) => {
      const transformed: ChartDataPoint = { date: day.date }

      // Add data for each selected category
      selectedCategories.forEach((category) => {
        const value = extractMetricValue(day, category, metricType)
        transformed[category] = value
      })

      return transformed
    })
  }, [data, metricType, selectedCategories])

  // Generate chart config dynamically based on selected categories
  const chartConfig = useMemo<ChartConfig>(() => {
    const config: ChartConfig = {
      upsell: {
        label: CATEGORY_LABELS.upsell,
        color: CATEGORY_COLORS.upsell,
      },
      upsize: {
        label: CATEGORY_LABELS.upsize,
        color: CATEGORY_COLORS.upsize,
      },
      addon: {
        label: CATEGORY_LABELS.addon,
        color: CATEGORY_COLORS.addon,
      },
    }

    return config
  }, [])

  // Get formatted label for the metric type
  const metricLabel = useMemo(() => {
    switch (metricType) {
      case 'revenue':
        return 'Revenue'
      case 'opportunities':
        return 'Opportunities'
      case 'offers':
        return 'Offers'
      case 'successes':
        return 'Successes'
      case 'conversion_rate':
        return 'Conversion Rate'
      default:
        return 'Revenue'
    }
  }, [metricType])

  // Get tooltip formatter based on metric type
  const tooltipFormatter = useMemo(() => {
    switch (metricType) {
      case 'revenue':
        return (value: number) => `$${value.toFixed(2)}`
      case 'conversion_rate':
        return (value: number) => `${value.toFixed(1)}%`
      case 'opportunities':
      case 'offers':
      case 'successes':
        return (value: number) => `${Math.round(value)} items`
      default:
        return (value: number) => `${value}`
    }
  }, [metricType])

  return {
    chartData,
    chartConfig,
    metricLabel,
    tooltipFormatter,
  }
}

/**
 * Extract the appropriate metric value from daily data
 */
function extractMetricValue(
  day: DailyMetrics,
  category: CategoryType,
  metricType: MetricType
): number {
  switch (metricType) {
    case 'revenue':
      return day[`${category}_revenue`]
    case 'opportunities':
      return day[`${category}_opportunities`]
    case 'offers':
      return day[`${category}_offers`]
    case 'successes':
      return day[`${category}_successes`]
    case 'conversion_rate':
      return day[`${category}_conversion_rate`]
    default:
      return 0
  }
}
