import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/contexts/authContext"

interface Run {
  id: string
  runId: string  // Add this field for the data table
  run_date: string
  status: string
  created_at: string
  org_id: string
  location_id: string
  // Analytics data from your endpoint
  total_transcriptions?: number
  successful_upsells?: number
  successful_upsizes?: number
  total_revenue?: number
}

interface RunsResponse {
  runs: Run[]
  count: number
}

const fetchRuns = async (locationId?: string, limit?: number, includeAnalytics: boolean = true): Promise<RunsResponse> => {
  const data = await apiClient.get<{ runs: any[] }>('/runs')

  // Map the backend response to match the frontend interface
  const runs = (data.runs || []).map((run: any) => ({
    ...run,
    runId: run.id,  // Map id to runId for the data table
    run_date: run.run_date,  // Keep run_date as run_date
  }))
  
  return {
    runs,
    count: runs.length
  }
}

export function useGetRuns(locationId?: string, options?: { limit?: number }) {
  const { user } = useAuth()

  return useQuery({
    queryKey: ['runs', user?.id, locationId ?? 'all', options?.limit],
    queryFn: () => fetchRuns(locationId, options?.limit),
    // Enabled by default (fetch all runs) and refetch when a location is selected
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
    enabled: !!user,
  })
}
