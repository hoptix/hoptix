"use client"

import * as React from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { MetricTypeSelectorProps } from "./types"
import type { MetricType } from "@/types/analytics"

const METRIC_OPTIONS: { value: MetricType; label: string; description: string }[] = [
  {
    value: "revenue",
    label: "Revenue",
    description: "Total revenue generated from upsells, upsizes, and add-ons",
  },
  {
    value: "opportunities",
    label: "Opportunities",
    description: "Number of upsell/upsize/add-on opportunities identified",
  },
  {
    value: "offers",
    label: "Offers",
    description: "Number of times operators offered upsells/upsizes/add-ons",
  },
  {
    value: "successes",
    label: "Successes",
    description: "Number of successful conversions (customer accepted)",
  },
  {
    value: "conversion_rate",
    label: "Conversion Rate",
    description: "Percentage of offers that resulted in success",
  },
]

export function MetricTypeSelector({
  value,
  onValueChange,
  disabled = false,
}: MetricTypeSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor="metric-type-select" className="text-sm font-medium whitespace-nowrap">
        Metric:
      </label>
      <Select
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
      >
        <SelectTrigger
          id="metric-type-select"
          className="w-[180px]"
          aria-label="Select metric type"
        >
          <SelectValue placeholder="Select metric" />
        </SelectTrigger>
        <SelectContent>
          {METRIC_OPTIONS.map((option) => (
            <SelectItem
              key={option.value}
              value={option.value}
              className="cursor-pointer"
            >
              <div className="flex flex-col">
                <span className="font-medium">{option.label}</span>
                <span className="text-xs text-muted-foreground hidden sm:block">
                  {option.description}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
