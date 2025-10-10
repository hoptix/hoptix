import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/contexts/authContext"

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
  const { user } = useAuth()

  return useQuery({
    queryKey: ['locations', user?.id], // Include user ID in cache key
    queryFn: fetchLocations,
    staleTime: 5 * 60 * 1000, // Reduced to 5 minutes for more responsive updates
    refetchOnWindowFocus: false,
    enabled: !!user, // Only fetch when user is authenticated
  })
}

export type { Location, LocationsResponse }
