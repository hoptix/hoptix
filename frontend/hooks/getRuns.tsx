import { useQuery } from "@tanstack/react-query";

interface Run {
  id: string;
  runId: string;  // Add this field for the data table
  date: string;
  status: string;
  created_at: string;
  org_id: string;
  location_id: string;
  // Analytics data from your endpoint
  total_transcriptions?: number;
  successful_upsells?: number;
  successful_upsizes?: number;
  total_revenue?: number;
}

interface RunsResponse {
  runs: Run[];
  count: number;
}

const fetchRuns = async (locationId?: string, limit?: number, includeAnalytics: boolean = true): Promise<RunsResponse> => {
  // Use environment variable or fallback to localhost for development
  const baseUrl = typeof window !== 'undefined' 
    ? (window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin)
    : 'http://localhost:8000';
  
  // Your endpoint only supports /runs, not location-specific runs
  const url = new URL(`/runs`, baseUrl);
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch runs: ${response.statusText}`);
  }
  
  const data = await response.json();
  console.log(data);
  
  // Map the backend response to match the frontend interface
  const runs = (data.runs || []).map((run: any) => ({
    ...run,
    runId: run.id,  // Map id to runId for the data table
    date: run.run_date || run.date,  // Map run_date to date if needed
  }));
  
  return {
    runs,
    count: runs.length
  };
};

export function useGetRuns(locationId?: string, options?: { limit?: number }) {
  return useQuery({
    queryKey: ['runs', locationId ?? 'all', options?.limit],
    queryFn: () => fetchRuns(locationId, options?.limit),
    // Enabled by default (fetch all runs) and refetch when a location is selected
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}
