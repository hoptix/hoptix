"use client"

import * as React from "react"
import { Calendar as CalendarIcon } from "lucide-react"
import { DateRange } from "react-day-picker"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useDashboardFilters } from "@/contexts/DashboardFilterContext"
import { startOfMonth, endOfMonth, startOfWeek, endOfWeek, subDays, subMonths } from "date-fns"

export function DateRangePicker({ className }: { className?: string }) {
  const { filters, updateDateRange } = useDashboardFilters()
  const [date, setDate] = React.useState<DateRange | undefined>({
    from: filters.dateRange.startDate || undefined,
    to: filters.dateRange.endDate || undefined,
  })

  React.useEffect(() => {
    setDate({
      from: filters.dateRange.startDate || undefined,
      to: filters.dateRange.endDate || undefined,
    })
  }, [filters.dateRange])

  const handleDateSelect = (selectedDate: DateRange | undefined) => {
    setDate(selectedDate)
    if (selectedDate?.from && selectedDate?.to) {
      updateDateRange({
        startDate: selectedDate.from,
        endDate: selectedDate.to
      })
    }
  }

  const handlePresetChange = (value: string) => {
    const today = new Date()
    let from: Date
    let to: Date

    switch (value) {
      case "today":
        from = today
        to = today
        break
      case "yesterday":
        from = subDays(today, 1)
        to = subDays(today, 1)
        break
      case "last7days":
        from = subDays(today, 6)
        to = today
        break
      case "last30days":
        from = subDays(today, 29)
        to = today
        break
      case "thisWeek":
        from = startOfWeek(today)
        to = endOfWeek(today)
        break
      case "thisMonth":
        from = startOfMonth(today)
        to = endOfMonth(today)
        break
      case "lastMonth":
        from = startOfMonth(subMonths(today, 1))
        to = endOfMonth(subMonths(today, 1))
        break
      default:
        return
    }

    const newRange = { from, to }
    setDate(newRange)
    updateDateRange({
      startDate: from,
      endDate: to
    })
  }

  return (
    <div className={cn("flex gap-2", className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={"outline"}
            className={cn(
              "w-[260px] justify-start text-left font-normal",
              !date && "text-muted-foreground"
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {date?.from ? (
              date.to ? (
                <>
                  {format(date.from, "LLL dd, y")} -{" "}
                  {format(date.to, "LLL dd, y")}
                </>
              ) : (
                format(date.from, "LLL dd, y")
              )
            ) : (
              <span>Pick a date range</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            initialFocus
            mode="range"
            defaultMonth={date?.from}
            selected={date}
            onSelect={handleDateSelect}
            numberOfMonths={2}
          />
        </PopoverContent>
      </Popover>

      <Select onValueChange={handlePresetChange}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="Quick select" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="today">Today</SelectItem>
          <SelectItem value="yesterday">Yesterday</SelectItem>
          <SelectItem value="last7days">Last 7 days</SelectItem>
          <SelectItem value="last30days">Last 30 days</SelectItem>
          <SelectItem value="thisWeek">This week</SelectItem>
          <SelectItem value="thisMonth">This month</SelectItem>
          <SelectItem value="lastMonth">Last month</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}