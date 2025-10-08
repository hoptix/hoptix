import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"

interface Location {
  id: string
  name: string
  org_id: string
  org_name: string
  timezone: string
  created_at: string
  display_name: string
}

interface LocationsResponse {
  locations: Location[]
  count: number
}

const fetchLocations = async (): Promise<LocationsResponse> => {
  return apiClient.get<LocationsResponse>('/locations')
}

export function useGetLocations() {
  return useQuery({
    queryKey: ['locations'],
    queryFn: fetchLocations,
    staleTime: 10 * 60 * 1000, // 10 minutes - locations don't change often
    refetchOnWindowFocus: false,
  })
}

export type { Location, LocationsResponse }
