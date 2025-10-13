"use client"

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'
import { useAuth } from '@/contexts/authContext'
import { useGetLocations, type Location } from '@/hooks/getLocations'
import { startOfMonth, endOfMonth } from 'date-fns'

interface DateRange {
  startDate: Date | null
  endDate: Date | null
}

interface DashboardFilters {
  locationIds: string[]
  locations: Location[]
  dateRange: DateRange
  isAllLocations: boolean
}

interface DashboardFilterContextValue {
  filters: DashboardFilters
  updateLocationIds: (locationIds: string[]) => void
  updateDateRange: (dateRange: DateRange) => void
  toggleLocation: (locationId: string) => void
  selectAllLocations: () => void
  clearLocationSelection: () => void
  isLoading: boolean
  availableLocations: Location[]
}

const DashboardFilterContext = createContext<DashboardFilterContextValue | undefined>(undefined)

interface DashboardFilterProviderProps {
  children: ReactNode
}

export function DashboardFilterProvider({ children }: DashboardFilterProviderProps) {
  const { user } = useAuth()
  const { data: locationsData, isLoading } = useGetLocations()

  // Initialize with current month date range
  const [filters, setFilters] = useState<DashboardFilters>({
    locationIds: [],
    locations: [],
    dateRange: {
      startDate: startOfMonth(new Date()),
      endDate: endOfMonth(new Date())
    },
    isAllLocations: true
  })

  const availableLocations = locationsData?.locations || []

  // Set all locations by default when locations are loaded
  useEffect(() => {
    if (availableLocations.length > 0 && filters.locationIds.length === 0 && filters.isAllLocations) {
      setFilters(prev => ({
        ...prev,
        locationIds: availableLocations.map((loc: Location) => loc.id),
        locations: availableLocations,
        isAllLocations: true
      }))
    }
  }, [availableLocations, filters.locationIds.length, filters.isAllLocations])

  const updateLocationIds = useCallback((locationIds: string[]) => {
    const selectedLocations = availableLocations.filter((loc: Location) => locationIds.includes(loc.id))
    setFilters(prev => ({
      ...prev,
      locationIds,
      locations: selectedLocations,
      isAllLocations: locationIds.length === availableLocations.length
    }))
  }, [availableLocations])

  const updateDateRange = useCallback((dateRange: DateRange) => {
    setFilters(prev => ({
      ...prev,
      dateRange
    }))
  }, [])

  const toggleLocation = useCallback((locationId: string) => {
    setFilters(prev => {
      const isCurrentlySelected = prev.locationIds.includes(locationId)
      let newLocationIds: string[]

      if (isCurrentlySelected) {
        newLocationIds = prev.locationIds.filter(id => id !== locationId)
      } else {
        newLocationIds = [...prev.locationIds, locationId]
      }

      const selectedLocations = availableLocations.filter((loc: Location) => newLocationIds.includes(loc.id))

      return {
        ...prev,
        locationIds: newLocationIds,
        locations: selectedLocations,
        isAllLocations: newLocationIds.length === availableLocations.length
      }
    })
  }, [availableLocations])

  const selectAllLocations = useCallback(() => {
    setFilters(prev => ({
      ...prev,
      locationIds: availableLocations.map((loc: Location) => loc.id),
      locations: availableLocations,
      isAllLocations: true
    }))
  }, [availableLocations])

  const clearLocationSelection = useCallback(() => {
    setFilters(prev => ({
      ...prev,
      locationIds: [],
      locations: [],
      isAllLocations: false
    }))
  }, [])

  const value: DashboardFilterContextValue = {
    filters,
    updateLocationIds,
    updateDateRange,
    toggleLocation,
    selectAllLocations,
    clearLocationSelection,
    isLoading,
    availableLocations
  }

  return (
    <DashboardFilterContext.Provider value={value}>
      {children}
    </DashboardFilterContext.Provider>
  )
}

export function useDashboardFilters() {
  const context = useContext(DashboardFilterContext)
  if (context === undefined) {
    throw new Error('useDashboardFilters must be used within a DashboardFilterProvider')
  }
  return context
}

// Helper hook to get formatted date strings for API calls
export function useFormattedDashboardFilters() {
  const { filters } = useDashboardFilters()

  return {
    locationIds: filters.locationIds,
    startDate: filters.dateRange.startDate?.toISOString().split('T')[0] || null,
    endDate: filters.dateRange.endDate?.toISOString().split('T')[0] || null,
    isAllLocations: filters.isAllLocations
  }
}