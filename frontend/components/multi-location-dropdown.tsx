"use client"

import * as React from "react"
import { MapPin, ChevronDown, Loader2, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { useDashboardFilters } from "@/contexts/DashboardFilterContext"

export function MultiLocationDropdown({ className = "" }: { className?: string }) {
  const {
    filters,
    toggleLocation,
    selectAllLocations,
    clearLocationSelection,
    isLoading,
    availableLocations
  } = useDashboardFilters()

  const handleSelectAll = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    selectAllLocations()
  }

  const handleClearAll = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    clearLocationSelection()
  }

  const handleToggle = (locationId: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    toggleLocation(locationId)
  }

  const getButtonLabel = () => {
    if (isLoading) return "Loading..."
    if (filters.locationIds.length === 0) return "Select Locations"
    if (filters.isAllLocations) return "All Locations"
    if (filters.locationIds.length === 1) {
      const location = filters.locations[0]
      return location?.display_name || "1 Location"
    }
    return `${filters.locationIds.length} Locations`
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={`justify-between min-w-[180px] max-w-[300px] ${className}`}
          disabled={isLoading}
        >
          <div className="flex items-center">
            <MapPin className="mr-2 h-4 w-4" />
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <span className="truncate">{getButtonLabel()}</span>
          </div>
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          Locations
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              {filters.locationIds.length}/{availableLocations.length}
            </Badge>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Select All / Clear All buttons */}
        <div className="flex items-center justify-between px-2 py-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSelectAll}
            className="h-auto p-1 text-xs"
          >
            Select All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            className="h-auto p-1 text-xs"
          >
            Clear All
          </Button>
        </div>
        <DropdownMenuSeparator />

        {availableLocations.length === 0 ? (
          <DropdownMenuItem disabled>
            No locations found
          </DropdownMenuItem>
        ) : (
          <div className="max-h-[300px] overflow-y-auto">
            {availableLocations.map((location) => {
              const isSelected = filters.locationIds.includes(location.id)
              return (
                <DropdownMenuItem
                  key={location.id}
                  onClick={handleToggle(location.id)}
                  className="flex items-start space-x-3 p-3"
                  onSelect={(e) => e.preventDefault()}
                >
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => toggleLocation(location.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <div className="flex-1 space-y-1">
                    <div className="font-medium">{location.display_name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <span>ID: {location.id.slice(0, 8)}...</span>
                      {location.timezone && (
                        <>
                          <span>•</span>
                          <span>{location.timezone}</span>
                        </>
                      )}
                    </div>
                  </div>
                  {isSelected && <Check className="h-4 w-4 text-primary" />}
                </DropdownMenuItem>
              )
            })}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}