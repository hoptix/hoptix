"use client"

import React, { useState, useMemo } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { SectionCards } from "@/components/section-cards"
import { SiteHeader } from "@/components/site-header"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"

import data from "./data.json"

export default function Page() {
  const [selectedRestaurant, setSelectedRestaurant] = useState<string>("all")

  // Get unique restaurants for filter
  const uniqueRestaurants = useMemo(() => {
    const restaurants = data.map(item => `${item.restaurantName} - ${item.restaurantLocation}`)
    return Array.from(new Set(restaurants)).sort()
  }, [])

  // Filter data based on selected restaurant
  const filteredData = useMemo(() => {
    if (selectedRestaurant === "all") {
      return data
    }
    return data.filter(item => 
      `${item.restaurantName} - ${item.restaurantLocation}` === selectedRestaurant
    )
  }, [selectedRestaurant])

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              {/* Top-level Restaurant Filter */}
              <div className="px-4 lg:px-6">
                <div className="flex items-center gap-4 p-4 bg-muted/30 rounded-lg border">
                  <Label htmlFor="restaurant-filter" className="text-sm font-medium whitespace-nowrap">
                    Restaurant:
                  </Label>
                  <Select value={selectedRestaurant} onValueChange={setSelectedRestaurant}>
                    <SelectTrigger className="w-64" id="restaurant-filter">
                      <SelectValue placeholder="All restaurants" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Restaurants</SelectItem>
                      {uniqueRestaurants.map((restaurant) => (
                        <SelectItem key={restaurant} value={restaurant}>
                          {restaurant}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="text-sm text-muted-foreground">
                    Showing {filteredData.length} of {data.length} entries
                  </div>
                </div>
              </div>

              <SectionCards data={filteredData} />
              <div className="px-4 lg:px-6">
                <ChartAreaInteractive />
              </div>
              <DataTable data={filteredData} hideRestaurantFilter={true} />
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
