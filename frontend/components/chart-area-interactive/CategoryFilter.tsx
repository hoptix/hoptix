"use client"

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Checkbox } from "@/components/ui/checkbox"
import { Filter } from "lucide-react"
import type { CategoryFilterProps } from "./types"
import type { CategoryType } from "@/types/analytics"

const CATEGORY_OPTIONS: { value: CategoryType; label: string; color: string }[] = [
  { value: "upsell", label: "Upsell", color: "hsl(var(--chart-1))" },
  { value: "upsize", label: "Upsize", color: "hsl(var(--chart-2))" },
  { value: "addon", label: "Add-ons", color: "hsl(var(--chart-3))" },
]

export function CategoryFilter({
  selectedCategories,
  onCategoriesChange,
  disabled = false,
}: CategoryFilterProps) {
  const toggleCategory = (category: CategoryType) => {
    const newCategories = new Set(selectedCategories)
    if (newCategories.has(category)) {
      // Don't allow deselecting if it's the only one selected
      if (newCategories.size > 1) {
        newCategories.delete(category)
      }
    } else {
      newCategories.add(category)
    }
    onCategoriesChange(newCategories)
  }

  const selectAll = () => {
    onCategoriesChange(new Set<CategoryType>(["upsell", "upsize", "addon"]))
  }

  const allSelected = selectedCategories.size === 3

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium whitespace-nowrap">Categories:</span>

      {/* Desktop: Show as toggleable badges */}
      <div className="hidden sm:flex items-center gap-2">
        {CATEGORY_OPTIONS.map((option) => {
          const isSelected = selectedCategories.has(option.value)
          return (
            <Badge
              key={option.value}
              variant={isSelected ? "default" : "outline"}
              className="cursor-pointer select-none"
              style={{
                backgroundColor: isSelected ? option.color : "transparent",
                borderColor: option.color,
                color: isSelected ? "white" : "inherit",
              }}
              onClick={() => !disabled && toggleCategory(option.value)}
            >
              {option.label}
            </Badge>
          )
        })}
      </div>

      {/* Mobile: Show as popover */}
      <Popover>
        <PopoverTrigger asChild className="sm:hidden">
          <Button variant="outline" size="sm" disabled={disabled}>
            <Filter className="h-4 w-4 mr-2" />
            {selectedCategories.size} selected
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-56" align="start">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">Categories</h4>
              {!allSelected && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 text-xs"
                  onClick={selectAll}
                >
                  Select All
                </Button>
              )}
            </div>
            <div className="space-y-2">
              {CATEGORY_OPTIONS.map((option) => {
                const isSelected = selectedCategories.has(option.value)
                const isOnlySelected = isSelected && selectedCategories.size === 1
                return (
                  <div key={option.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`category-${option.value}`}
                      checked={isSelected}
                      onCheckedChange={() => toggleCategory(option.value)}
                      disabled={disabled || isOnlySelected}
                    />
                    <label
                      htmlFor={`category-${option.value}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2 cursor-pointer"
                    >
                      <div
                        className="w-3 h-3 rounded-sm"
                        style={{ backgroundColor: option.color }}
                      />
                      {option.label}
                    </label>
                  </div>
                )
              })}
            </div>
            {selectedCategories.size === 1 && (
              <p className="text-xs text-muted-foreground">
                At least one category must be selected
              </p>
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
