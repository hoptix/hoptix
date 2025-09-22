import { useQuery } from "@tanstack/react-query";

interface Location {
  id: string;
  name: string;
  org_id: string;
  org_name: string;
  timezone: string;
  created_at: string;
  display_name: string;
}

interface LocationsResponse {
  locations: Location[];
  count: number;
}

const fetchLocations = async (): Promise<LocationsResponse> => {
  // Use environment variable or fallback to localhost for development
  const baseUrl = typeof window !== 'undefined' 
    ? (window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin)
    : 'http://localhost:8000';
  
  const url = new URL('/locations', baseUrl);
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch locations: ${response.statusText}`);
  }
  
  return response.json();
};

export function useGetLocations() {
  return useQuery({
    queryKey: ['locations'],
    queryFn: fetchLocations,
    staleTime: 10 * 60 * 1000, // 10 minutes - locations don't change often
    refetchOnWindowFocus: false,
  });
}

export type { Location, LocationsResponse };
