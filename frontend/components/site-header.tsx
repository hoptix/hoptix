import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { LocationDropdown } from "@/components/location-dropdown"
import type { Location } from "@/hooks/getLocations"

interface SiteHeaderProps {
  title?: string
  showLocationDropdown?: boolean
  selectedLocationId?: string
  onLocationChange?: (locationId: string, location: Location) => void
}

export function SiteHeader({
  title = "Analytics Dashboard",
  showLocationDropdown = false,
  selectedLocationId,
  onLocationChange
}: SiteHeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-16 overflow-hidden">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6 min-w-0">
        <h1 className="text-base font-medium truncate">{title}</h1>

        {/* Location Dropdown */}
        {showLocationDropdown && onLocationChange && (
          <>
            <div className="flex-1 min-w-0" /> {/* Spacer */}
            <LocationDropdown
              selectedLocationId={selectedLocationId}
              onLocationChange={onLocationChange}
              className="ml-auto shrink-0"
            />
          </>
        )}
      </div>
    </header>
  )
}
