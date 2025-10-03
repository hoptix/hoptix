"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { RunsDataTable } from "@/components/runs-data-table"
import { SectionCards } from "@/components/section-cards"
import { TopTransactionsHighlight } from "@/components/top-transactions-highlight"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { useState } from "react"
import type { Location } from "@/hooks/getLocations"

import data from "./data.json"

export default function Page() {
  const [selectedLocationId, setSelectedLocationId] = useState<string>("")
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)

  const handleLocationChange = (locationId: string, location: Location) => {
    setSelectedLocationId(locationId)
    setSelectedLocation(locationId ? location : null)
  }

  return (
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
              <SectionCards data={data} />
              <div className="px-4 lg:px-6">
                <ChartAreaInteractive />
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
  )
}
