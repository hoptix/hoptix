import { useQuery } from "@tanstack/react-query";

interface Run {
  id: string;
  runId: string;
  date: string;
  status: string;
  created_at: string;
  org_id: string;
  location_id: string;
  // Analytics data
  totalTransactions?: number;
  successfulUpsells?: number;
  successfulUpsizes?: number;
  totalRevenue?: number;
}

interface RunsResponse {
  runs: Run[];
  count: number;
}

const fetchRuns = async (locationId: string, limit?: number, includeAnalytics: boolean = true): Promise<RunsResponse> => {
  // Use environment variable or fallback to localhost for development
  const baseUrl = typeof window !== 'undefined' 
    ? (window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin)
    : 'http://localhost:8000';
  
  const url = new URL(`/locations/${locationId}/runs`, baseUrl);
  
  if (limit) {
    url.searchParams.append('limit', limit.toString());
  }
  
  if (includeAnalytics) {
    url.searchParams.append('include_analytics', 'true');
  }
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch runs: ${response.statusText}`);
  }
  
  return response.json();
};

export function useGetRuns(locationId: string, options?: { limit?: number }) {
  return useQuery({
    queryKey: ['runs', locationId, options?.limit],
    queryFn: () => fetchRuns(locationId, options?.limit),
    enabled: !!locationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}
