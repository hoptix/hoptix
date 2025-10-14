import { MultiLocationDropdown } from "@/components/multi-location-dropdown"
import { DateRangePicker } from "@/components/date-range-picker"
import { Separator } from "@/components/ui/separator"

interface SiteHeaderProps {
  title?: string
  showLocationDropdown?: boolean
  showDateRangePicker?: boolean
}

export function SiteHeader({
  title = "Analytics Dashboard",
  showLocationDropdown = false,
  showDateRangePicker = false
}: SiteHeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-16 overflow-hidden">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6 min-w-0">
        <h1 className="text-base font-medium truncate">{title}</h1>

        {/* Filters */}
        {(showLocationDropdown || showDateRangePicker) && (
          <>
            <div className="flex-1 min-w-0" /> {/* Spacer */}
            <div className="flex items-center gap-2 shrink-0">
              {showLocationDropdown && (
                <MultiLocationDropdown className="shrink-0" />
              )}
              {showLocationDropdown && showDateRangePicker && (
                <Separator orientation="vertical" className="h-8" />
              )}
              {showDateRangePicker && (
                <DateRangePicker className="shrink-0" />
              )}
            </div>
          </>
        )}
      </div>
    </header>
  )
}
