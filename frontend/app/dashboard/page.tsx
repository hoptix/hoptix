"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { RunsDataTable } from "@/components/runs-data-table"
import { SectionCards } from "@/components/section-cards"
import { TopTransactionsHighlight } from "@/components/top-transactions-highlight"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { RequireAuth } from "@/components/auth/RequireAuth"
import { useState } from "react"
import type { Location } from "@/hooks/getLocations"
import { useDashboardAnalytics } from "@/hooks/useDashboardAnalytics"

export default function Page() {
  const [selectedLocationId, setSelectedLocationId] = useState<string>("")
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)

  const handleLocationChange = (locationId: string, location: Location) => {
    setSelectedLocationId(locationId)
    setSelectedLocation(locationId ? location : null)
  }

  // Fetch dashboard analytics for selected location
  const { data: analyticsData, isLoading: isLoadingAnalytics } = useDashboardAnalytics({
    locationId: selectedLocationId,
    comparePrevious: true,
    enabled: !!selectedLocationId
  })

  // Default metrics when no location is selected
  const defaultMetrics = {
    operator_revenue: 0,
    offer_rate: 0,
    conversion_rate: 0,
    items_converted: 0
  }

  return (
    <RequireAuth>
      <SidebarProvider>
        <AppSidebar variant="inset" />
        <SidebarInset>
          <SiteHeader
            title="Dashboard"
            showLocationDropdown={true}
            selectedLocationId={selectedLocationId}
            onLocationChange={handleLocationChange}
          />
          <div className="flex flex-1 flex-col">
            <div className="@container/main flex flex-1 flex-col gap-2">
              <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
                {selectedLocationId ? (
                  <SectionCards
                    metrics={analyticsData?.metrics || defaultMetrics}
                    trends={analyticsData?.trends}
                    isLoading={isLoadingAnalytics}
                  />
                ) : (
                  <div className="px-4 lg:px-6 text-center py-8 text-muted-foreground">
                    Please select a location to view dashboard analytics
                  </div>
                )}
                <div className="px-4 lg:px-6">
                  <ChartAreaInteractive locationId={selectedLocationId} />
                </div>
                {selectedLocationId && (
                  <div className="px-4 lg:px-6">
                    <TopTransactionsHighlight
                      locationId={selectedLocationId}
                      className="mb-6"
                    />
                  </div>
                )}
                <RunsDataTable locationId={selectedLocationId || undefined} />
              </div>
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </RequireAuth>
  )
}
