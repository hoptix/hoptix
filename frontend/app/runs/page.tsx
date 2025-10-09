"use client"

import { RequireAuth } from "@/components/auth/RequireAuth"
import { AppSidebar } from "@/components/app-sidebar"
import { RunsTable } from "@/components/runs-table"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { useState } from "react"
import type { Location } from "@/hooks/getLocations"

export default function RunsPage() {
  const [selectedLocationId, setSelectedLocationId] = useState<string>("")
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)

  const handleLocationChange = (locationId: string, location: Location) => {
    setSelectedLocationId(locationId)
    setSelectedLocation(locationId ? location : null)
  }

  return (
    <RequireAuth>
      <SidebarProvider>
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader 
          title="Runs Management"
          showLocationDropdown={true}
          selectedLocationId={selectedLocationId}
          onLocationChange={handleLocationChange}
        />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              
              {/* Info Banner */}
              {selectedLocation ? (
                <div className="px-4 lg:px-6">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="font-semibold text-green-900 mb-1">
                      Showing runs for: {selectedLocation.display_name}
                    </h3>
                    <p className="text-green-700 text-sm">
                      Location ID: <code className="bg-green-100 px-1 rounded text-xs">{selectedLocation.id}</code>
                      {selectedLocation.timezone && (
                        <span className="ml-3">Timezone: {selectedLocation.timezone}</span>
                      )}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="px-4 lg:px-6">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-semibold text-blue-900 mb-1">Select a Location</h3>
                    <p className="text-blue-700 text-sm">
                      Use the location dropdown in the header to select a location and view its runs.
                    </p>
                  </div>
                </div>
              )}

              {/* Runs Table */}
              <div className="px-4 lg:px-6">
                {selectedLocationId ? (
                  <RunsTable locationId={selectedLocationId} limit={100} />
                ) : (
                  <div className="flex flex-col items-center justify-center p-12 text-center border rounded-lg bg-muted/20">
                    <div className="text-muted-foreground mb-2">
                      <svg 
                        className="mx-auto h-12 w-12 mb-4" 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <path 
                          strokeLinecap="round" 
                          strokeLinejoin="round" 
                          strokeWidth={2} 
                          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" 
                        />
                        <path 
                          strokeLinecap="round" 
                          strokeLinejoin="round" 
                          strokeWidth={2} 
                          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" 
                        />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold mb-2">No Location Selected</h3>
                    <p className="text-muted-foreground max-w-md">
                      Select a location from the dropdown in the header to view runs data for that location.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
    </RequireAuth>
  )
}
