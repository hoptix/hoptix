"use client"

import * as React from "react"
import { MetricTypeSelector } from "./MetricTypeSelector"
import { CategoryFilter } from "./CategoryFilter"
import { ViewModeToggle } from "./ViewModeToggle"
import { Separator } from "@/components/ui/separator"
import type { ChartFilterProps } from "./types"

export function ChartFilters({
  metricType,
  selectedCategories,
  viewMode,
  onMetricTypeChange,
  onCategoriesChange,
  onViewModeChange,
  isMobile = false,
}: Omit<ChartFilterProps, "timeRange" | "onTimeRangeChange">) {
  return (
    <div className="flex flex-col gap-3 p-4 bg-muted/30 rounded-lg border">
      {/* First row: Metric Type */}
      <div className="flex flex-wrap items-center gap-4">
        <MetricTypeSelector
          value={metricType}
          onValueChange={onMetricTypeChange}
        />
      </div>

      <Separator className="my-1" />

      {/* Second row: Category Filter and View Mode */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <CategoryFilter
          selectedCategories={selectedCategories}
          onCategoriesChange={onCategoriesChange}
        />
        <ViewModeToggle value={viewMode} onValueChange={onViewModeChange} />
      </div>
    </div>
  )
}
