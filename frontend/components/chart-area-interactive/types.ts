/**
 * Component-specific types for ChartAreaInteractive
 */

import type { MetricType, CategoryType, ViewMode } from '@/types/analytics'

export interface ChartFilterProps {
  metricType: MetricType
  selectedCategories: Set<CategoryType>
  viewMode: ViewMode
  timeRange: string
  onMetricTypeChange: (value: MetricType) => void
  onCategoriesChange: (value: Set<CategoryType>) => void
  onViewModeChange: (value: ViewMode) => void
  onTimeRangeChange: (value: string) => void
  isMobile?: boolean
}

export interface MetricTypeSelectorProps {
  value: MetricType
  onValueChange: (value: MetricType) => void
  disabled?: boolean
}

export interface CategoryFilterProps {
  selectedCategories: Set<CategoryType>
  onCategoriesChange: (value: Set<CategoryType>) => void
  disabled?: boolean
}

export interface ViewModeToggleProps {
  value: ViewMode
  onValueChange: (value: ViewMode) => void
  disabled?: boolean
}
