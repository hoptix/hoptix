"use client"

import * as React from "react"
import { MapPin, ChevronDown, Loader2 } from "lucide-react"
import { useGetLocations, type Location } from "@/hooks/getLocations"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"

interface LocationDropdownProps {
  selectedLocationId?: string
  onLocationChange: (locationId: string, location: Location) => void
  className?: string
}

export function LocationDropdown({ 
  selectedLocationId, 
  onLocationChange, 
  className = "" 
}: LocationDropdownProps) {
  const { data: locationsResponse, isLoading, isError } = useGetLocations()
  const locations = locationsResponse?.locations || []
  
  const selectedLocation = selectedLocationId 
    ? locations.find(loc => loc.id === selectedLocationId)
    : null

  const handleLocationSelect = (location: Location) => {
    onLocationChange(location.id, location)
  }

  if (isError) {
    return (
      <Button variant="outline" disabled className={className}>
        <MapPin className="mr-2 h-4 w-4" />
        Error loading locations
      </Button>
    )
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
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : selectedLocation ? (
              <span className="truncate">{selectedLocation.display_name}</span>
            ) : (
              "Select Location"
            )}
          </div>
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          Locations
          <Badge variant="secondary" className="ml-2">
            {locations.length}
          </Badge>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {locations.length === 0 ? (
          <DropdownMenuItem disabled>
            No locations found
          </DropdownMenuItem>
        ) : (
          locations.map((location) => (
            <DropdownMenuItem
              key={location.id}
              onClick={() => handleLocationSelect(location)}
              className="flex flex-col items-start space-y-1 p-3"
            >
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
            </DropdownMenuItem>
          ))
        )}
        
        {selectedLocationId && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onLocationChange("", {} as Location)}
              className="text-muted-foreground"
            >
              Clear selection
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

