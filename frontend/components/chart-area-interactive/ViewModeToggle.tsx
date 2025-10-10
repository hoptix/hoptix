"use client"

import * as React from "react"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { BarChart3, LineChart } from "lucide-react"
import type { ViewModeToggleProps } from "./types"

export function ViewModeToggle({
  value,
  onValueChange,
  disabled = false,
}: ViewModeToggleProps) {
  const handleValueChange = (newValue: string) => {
    // Prevent deselection - always keep one selected
    if (newValue) {
      onValueChange(newValue as "stacked" | "individual")
    }
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium whitespace-nowrap hidden md:inline">View:</span>
      <ToggleGroup
        type="single"
        value={value}
        onValueChange={handleValueChange}
        disabled={disabled}
        className="gap-1"
      >
        <ToggleGroupItem
          value="stacked"
          aria-label="Stacked view"
          className="gap-2"
        >
          <BarChart3 className="h-4 w-4" />
          <span className="hidden sm:inline">Stacked</span>
        </ToggleGroupItem>
        <ToggleGroupItem
          value="individual"
          aria-label="Individual view"
          className="gap-2"
        >
          <LineChart className="h-4 w-4" />
          <span className="hidden sm:inline">Individual</span>
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}
