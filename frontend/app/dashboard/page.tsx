"use client"

import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { RunsDataTable } from "@/components/runs-data-table"
import { SectionCards } from "@/components/section-cards"
import { OperatorPerformanceSection } from "@/components/operator-performance-section"
import { SiteHeader } from "@/components/site-header"
import { RequireAuth } from "@/components/auth/RequireAuth"
import { DashboardFilterProvider, useDashboardFilters, useFormattedDashboardFilters } from "@/contexts/DashboardFilterContext"
import { useDashboardAnalytics } from "@/hooks/useDashboardAnalytics"

function DashboardContent() {
  const { filters } = useDashboardFilters()
  const { locationIds, startDate, endDate } = useFormattedDashboardFilters()

  // Fetch dashboard analytics for selected locations
  const { data: analyticsData, isLoading: isLoadingAnalytics } = useDashboardAnalytics({
    locationIds: locationIds,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
    comparePrevious: true,
    enabled: locationIds.length > 0
  })

  // Default metrics when no data
  const defaultMetrics = {
    operator_revenue: 0,
    offer_rate: 0,
    conversion_rate: 0,
    items_converted: 0
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="sticky top-0 z-10 bg-background">
        <SiteHeader
          title="Dashboard"
          showLocationDropdown={true}
          showDateRangePicker={true}
        />
      </div>
      <div className="flex-1 overflow-y-auto min-w-0">
        <div className="@container/main min-w-0">
          <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6 min-w-0 max-w-[1920px] mx-auto w-full">
            <SectionCards
              metrics={analyticsData?.metrics || defaultMetrics}
              trends={analyticsData?.trends}
              isLoading={isLoadingAnalytics}
            />
            <div className="px-4 lg:px-6 min-w-0 flex flex-col gap-4 md:gap-6">
              <ChartAreaInteractive />
              <OperatorPerformanceSection />
              <RunsDataTable />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Page() {
  return (
    <RequireAuth>
      <DashboardFilterProvider>
        <DashboardContent />
      </DashboardFilterProvider>
    </RequireAuth>
  )
}
