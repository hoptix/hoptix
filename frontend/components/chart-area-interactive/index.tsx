"use client"

import * as React from "react"
import { useSearchParams, useRouter, usePathname } from "next/navigation"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { useIsMobile } from "@/hooks/use-mobile"
import { useMultiLocationAnalyticsOverTime } from "@/hooks/useMultiLocationAnalyticsOverTime"
import { useFormattedDashboardFilters } from "@/contexts/DashboardFilterContext"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { ChartFilters } from "./ChartFilters"
import { useChartDataTransform } from "./useChartDataTransform"
import type { MetricType, CategoryType, ViewMode } from "@/types/analytics"

const STORAGE_KEY = "chart-area-interactive-prefs"

export function ChartAreaInteractive() {
  const isMobile = useIsMobile()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { locationIds, startDate, endDate } = useFormattedDashboardFilters()

  // Initialize state from URL params or localStorage
  const [timeRange, setTimeRange] = React.useState(() => {
    const urlRange = searchParams.get("range")
    if (urlRange && ["7d", "30d", "90d"].includes(urlRange)) {
      return urlRange
    }
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          const prefs = JSON.parse(saved)
          return prefs.timeRange || (isMobile ? "7d" : "30d")
        } catch {
          // Fall through to default
        }
      }
    }
    return isMobile ? "7d" : "30d"
  })

  const [metricType, setMetricType] = React.useState<MetricType>(() => {
    const urlMetric = searchParams.get("metric")
    if (urlMetric && ["revenue", "opportunities", "offers", "successes", "conversion_rate"].includes(urlMetric)) {
      return urlMetric as MetricType
    }
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          const prefs = JSON.parse(saved)
          return prefs.metricType || "revenue"
        } catch {
          // Fall through to default
        }
      }
    }
    return "revenue"
  })

  const [selectedCategories, setSelectedCategories] = React.useState<Set<CategoryType>>(() => {
    const urlCategories = searchParams.get("categories")
    if (urlCategories) {
      const categories = urlCategories.split(",").filter((c): c is CategoryType =>
        ["upsell", "upsize", "addon"].includes(c)
      )
      if (categories.length > 0) {
        return new Set(categories)
      }
    }
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          const prefs = JSON.parse(saved)
          if (prefs.selectedCategories && Array.isArray(prefs.selectedCategories)) {
            return new Set(prefs.selectedCategories)
          }
        } catch {
          // Fall through to default
        }
      }
    }
    return new Set<CategoryType>(["upsell", "upsize", "addon"])
  })

  const [viewMode, setViewMode] = React.useState<ViewMode>(() => {
    const urlView = searchParams.get("view")
    if (urlView && ["stacked", "individual"].includes(urlView)) {
      return urlView as ViewMode
    }
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          const prefs = JSON.parse(saved)
          return prefs.viewMode || "individual"
        } catch {
          // Fall through to default
        }
      }
    }
    return "individual"
  })

  // Auto-adjust time range on mobile
  React.useEffect(() => {
    if (isMobile && timeRange !== "7d") {
      setTimeRange("7d")
    }
  }, [isMobile, timeRange])

  // Persist preferences to localStorage and URL
  React.useEffect(() => {
    const prefs = {
      timeRange,
      metricType,
      selectedCategories: Array.from(selectedCategories),
      viewMode,
    }

    // Always save to localStorage for user convenience
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
    }

    // Only update URL params when locations are selected
    // This prevents polluting the URL before the user has made a meaningful selection
    if (locationIds.length > 0) {
      const params = new URLSearchParams(searchParams.toString())
      params.set("metric", metricType)
      params.set("categories", Array.from(selectedCategories).join(","))
      params.set("view", viewMode)
      params.set("range", timeRange)

      const newUrl = `${pathname}?${params.toString()}`
      router.replace(newUrl, { scroll: false })
    } else {
      // Clear URL params when no location is selected
      if (searchParams.toString()) {
        router.replace(pathname, { scroll: false })
      }
    }
  }, [timeRange, metricType, selectedCategories, viewMode, pathname, router, searchParams, locationIds])

  // Convert time range to days (only used if date range from context is not available)
  const getDaysFromTimeRange = (range: string) => {
    if (range === "7d") return 7
    if (range === "30d") return 30
    if (range === "90d") return 90
    return 30
  }

  // Fetch real data using filters from context
  const { data: chartData, isLoading } = useMultiLocationAnalyticsOverTime({
    locationIds,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
    days: (!startDate && !endDate) ? getDaysFromTimeRange(timeRange) : undefined,
    enabled: locationIds.length > 0,
  })

  // Transform data for chart
  const { chartData: transformedData, chartConfig, metricLabel, tooltipFormatter } = useChartDataTransform({
    data: chartData,
    metricType,
    selectedCategories,
  })

  // Calculate dynamic Y-axis domain to prevent clipping
  const yAxisDomain = React.useMemo<[number | 'auto', number | 'auto']>(() => {
    if (!transformedData || transformedData.length === 0) {
      return [0, 100]
    }

    let maxValue = 0
    let minValue = Infinity

    // Find the maximum and minimum values across all data points and categories
    transformedData.forEach((point) => {
      let pointTotal = 0
      selectedCategories.forEach((category) => {
        const value = point[category] as number

        // IMPORTANT: Never stack conversion rates - they should be compared, not summed
        if (viewMode === "stacked" && metricType !== "conversion_rate") {
          // For stacked mode (except conversion rates), sum all values
          pointTotal += value || 0
        } else {
          // For individual mode OR conversion rates, track max individual value
          maxValue = Math.max(maxValue, value || 0)
          minValue = Math.min(minValue, value || 0)
        }
      })
      if (viewMode === "stacked" && metricType !== "conversion_rate") {
        maxValue = Math.max(maxValue, pointTotal)
        minValue = 0 // Stacked charts always start from 0
      }
    })

    // Reset minValue if no valid data
    if (minValue === Infinity) {
      minValue = 0
    }

    // Add 20% padding to the top to prevent clipping peaks
    const paddedMax = maxValue * 1.2

    // Add small padding to bottom (5% or min 0)
    const paddedMin = Math.max(0, minValue - (maxValue * 0.05))

    // For conversion rates, cap at 100% and ensure we start at 0
    if (metricType === "conversion_rate") {
      return [0, Math.min(Math.max(paddedMax, 10), 100)]
    }

    // Ensure minimum range for better visibility
    const range = paddedMax - paddedMin
    if (range < 10) {
      return [0, Math.max(10, paddedMax)]
    }

    return [paddedMin, paddedMax]
  }, [transformedData, selectedCategories, viewMode, metricType])

  // Format Y-axis ticks based on metric type
  const formatYAxis = React.useCallback((value: number) => {
    if (metricType === "revenue") {
      return `$${value >= 1000 ? (value / 1000).toFixed(1) + "k" : value.toFixed(0)}`
    } else if (metricType === "conversion_rate") {
      return `${value.toFixed(0)}%`
    } else {
      return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toFixed(0)
    }
  }, [metricType])

  // Memoized X-axis tick formatter
  const xAxisTickFormatter = React.useCallback((value: string | number) => {
    const date = new Date(value)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    })
  }, [])

  // Memoized tooltip label formatter to prevent re-renders
  const tooltipLabelFormatter = React.useCallback((value: string | number) => {
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }, [])

  // Memoized tooltip value formatter with colored dots
  // Returns JSX with colored dot indicator, label, and formatted value
  const tooltipValueFormatter = React.useCallback((value: any, name: any, item: any) => {
    const category = String(name) as CategoryType
    const categoryConfig = chartConfig[category]

    if (!categoryConfig) {
      return tooltipFormatter(Number(value))
    }

    return (
      <div className="flex w-full items-center gap-2">
        {/* Colored dot indicator using CSS variables */}
        <div
          className="h-2.5 w-2.5 shrink-0 rounded-[2px] bg-[--color-bg]"
          style={{
            '--color-bg': `var(--color-${category})`,
          } as React.CSSProperties}
        />
        {/* Category label and value */}
        <div className="flex flex-1 justify-between items-center leading-none">
          <span className="text-muted-foreground">
            {categoryConfig.label}
          </span>
          <span className="font-mono font-medium tabular-nums text-foreground ml-2">
            {tooltipFormatter(Number(value))}
          </span>
        </div>
      </div>
    )
  }, [tooltipFormatter, chartConfig])

  // Memoize gradient definitions to prevent re-renders
  const gradientDefs = React.useMemo(() => {
    return Array.from(selectedCategories).map((category) => (
      <linearGradient key={category} id={`fill${category}`} x1="0" y1="0" x2="0" y2="1">
        <stop
          offset="5%"
          stopColor={`var(--color-${category})`}
          stopOpacity={category === "upsell" ? 1.0 : category === "upsize" ? 0.8 : 0.6}
        />
        <stop
          offset="95%"
          stopColor={`var(--color-${category})`}
          stopOpacity={0.1}
        />
      </linearGradient>
    ))
  }, [selectedCategories])

  // Memoize Area components to prevent re-renders
  const areaComponents = React.useMemo(() => {
    return Array.from(selectedCategories)
      .reverse()
      .map((category) => {
        const shouldStack = viewMode === "stacked" && metricType !== "conversion_rate"
        return (
          <Area
            key={category}
            dataKey={category}
            type="natural"
            fill={`url(#fill${category})`}
            stroke={`var(--color-${category})`}
            strokeWidth={2}
            stackId={shouldStack ? "a" : undefined}
            fillOpacity={shouldStack ? 1 : 0.4}
            isAnimationActive={false}
            animationDuration={0}
          />
        )
      })
  }, [selectedCategories, viewMode, metricType])

  // Memoize cursor style to prevent re-creation
  const cursorStyle = React.useMemo(() => ({
    stroke: "hsl(var(--muted-foreground))",
    strokeWidth: 1,
    strokeDasharray: "4 4"
  }), [])

  // Memoize tooltip wrapper style to prevent re-creation
  const tooltipWrapperStyle = React.useMemo(() => ({
    pointerEvents: 'none' as const
  }), [])

  // Memoize tooltip position to prevent re-creation
  const tooltipPosition = React.useMemo(() => ({
    y: 0
  }), [])

  // Memoize tooltip content to prevent re-renders on vertical mouse movement
  const tooltipContent = React.useMemo(() => {
    return (
      <ChartTooltipContent
        labelFormatter={tooltipLabelFormatter}
        formatter={tooltipValueFormatter}
        indicator="dot"
        hideLabel={false}
        hideIndicator={false}
        className="min-w-[150px]"
      />
    )
  }, [tooltipLabelFormatter, tooltipValueFormatter])

  // Loading state
  if (isLoading) {
    return (
      <Card className="@container/card">
        <CardHeader className="relative">
          <div className="h-6 bg-muted rounded w-48 mb-2 animate-pulse"></div>
          <div className="h-4 bg-muted rounded w-64 animate-pulse"></div>
        </CardHeader>
        <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6 space-y-4">
          <div className="h-24 bg-muted rounded animate-pulse"></div>
          <div className="h-[320px] bg-muted rounded animate-pulse"></div>
        </CardContent>
      </Card>
    )
  }

  // Empty state (no locations selected)
  if (locationIds.length === 0) {
    return (
      <Card className="@container/card">
        <CardHeader>
          <CardTitle>Analytics Over Time</CardTitle>
          <CardDescription>
            Track performance metrics across different time periods
          </CardDescription>
        </CardHeader>
        <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
          <div className="h-[320px] flex items-center justify-center text-muted-foreground">
            Select locations to view analytics
          </div>
        </CardContent>
      </Card>
    )
  }

  // No data state
  if (!chartData || chartData.length === 0) {
    return (
      <Card className="@container/card">
        <CardHeader>
          <CardTitle>Analytics Over Time</CardTitle>
          <CardDescription>
            Track performance metrics across different time periods
          </CardDescription>
        </CardHeader>
        <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
          <div className="h-[320px] flex items-center justify-center text-muted-foreground">
            No analytics data available for the selected period
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="@container/card overflow-hidden">
      <CardHeader className="relative overflow-hidden">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>{metricLabel} Over Time</CardTitle>
            <CardDescription>
              <span className="@[540px]/card:block hidden">
                Daily {metricLabel.toLowerCase()} from upsells, upsizes, and add-ons
              </span>
              <span className="@[540px]/card:hidden">Daily breakdown</span>
            </CardDescription>
          </div>

          {/* Time Range Selector */}
          <div className="shrink-0">
            <ToggleGroup
              type="single"
              value={timeRange}
              onValueChange={(value) => value && setTimeRange(value)}
              variant="outline"
              className="@[767px]/card:flex hidden"
            >
              <ToggleGroupItem value="90d" className="h-8 px-2.5" aria-label="Last 3 months">
                Last 3 months
              </ToggleGroupItem>
              <ToggleGroupItem value="30d" className="h-8 px-2.5" aria-label="Last 30 days">
                Last 30 days
              </ToggleGroupItem>
              <ToggleGroupItem value="7d" className="h-8 px-2.5" aria-label="Last 7 days">
                Last 7 days
              </ToggleGroupItem>
            </ToggleGroup>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger
                className="@[767px]/card:hidden flex w-40"
                aria-label="Select time range"
              >
                <SelectValue placeholder="Last 3 months" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="90d" className="rounded-lg">
                  Last 3 months
                </SelectItem>
                <SelectItem value="30d" className="rounded-lg">
                  Last 30 days
                </SelectItem>
                <SelectItem value="7d" className="rounded-lg">
                  Last 7 days
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6 space-y-4">
        {/* Filter Controls */}
        <div className="space-y-2">
          <ChartFilters
            metricType={metricType}
            selectedCategories={selectedCategories}
            viewMode={viewMode}
            onMetricTypeChange={setMetricType}
            onCategoriesChange={setSelectedCategories}
            onViewModeChange={setViewMode}
            isMobile={isMobile}
          />
          {metricType === "conversion_rate" && viewMode === "stacked" && (
            <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20 p-2.5 rounded border border-amber-200 dark:border-amber-800 flex items-start gap-2">
              <span className="text-sm">💡</span>
              <span>
                <strong>Note:</strong> Conversion rates are displayed individually for comparison.
                Percentages cannot be mathematically stacked (e.g., 50% + 60% ≠ 110%).
              </span>
            </div>
          )}
        </div>

        {/* Chart */}
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-[320px] w-full"
        >
          <AreaChart
            data={transformedData}
            accessibilityLayer
            margin={{ top: 12, right: 12, left: 0, bottom: 5 }}
            syncId="analytics-chart"
          >
            {/* Only show tooltip based on X-axis position, not proximity to data points */}
            <defs>{gradientDefs}</defs>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={xAxisTickFormatter}
              height={40}
              interval="preserveStartEnd"
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={formatYAxis}
              domain={yAxisDomain}
              width={metricType === "conversion_rate" ? 50 : 60}
              allowDataOverflow={false}
              scale="linear"
            />
            <ChartTooltip
              content={tooltipContent}
              cursor={cursorStyle}
              animationDuration={0}
              isAnimationActive={false}
              shared={true}
              allowEscapeViewBox={{ x: false, y: true }}
              wrapperStyle={tooltipWrapperStyle}
              position={tooltipPosition}
            />
            {areaComponents}
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
