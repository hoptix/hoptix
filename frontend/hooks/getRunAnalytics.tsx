import { useQuery } from "@tanstack/react-query";

interface OperatorMetrics {
  upselling?: {
    summary?: {
      total_opportunities: number;
      total_offers: number;
      total_successes: number;
      total_revenue: number;
      offer_rate: number;
      success_rate: number;
      conversion_rate: number;
    };
    // Direct properties (based on actual API response)
    total_opportunities?: number;
    total_offers?: number;
    total_successes?: number;
    total_revenue?: number;
    offer_rate?: number;
    success_rate?: number;
    conversion_rate?: number;
    item_breakdown?: Record<string, {
      opportunities: number;
      offers: number;
      successes: number;
      revenue: number;
      offer_rate: number;
      success_rate: number;
    }>;
  };
  upsizing?: {
    summary?: {
      total_opportunities: number;
      total_offers: number;
      total_successes: number;
      total_revenue: number;
      offer_rate: number;
      success_rate: number;
      conversion_rate: number;
    };
    // Direct properties (based on actual API response)
    total_opportunities?: number;
    total_offers?: number;
    total_successes?: number;
    total_revenue?: number;
    offer_rate?: number;
    success_rate?: number;
    conversion_rate?: number;
    item_breakdown?: Record<string, {
      opportunities: number;
      offers: number;
      successes: number;
      revenue: number;
      offer_rate: number;
      success_rate: number;
    }>;
  };
  addons?: {
    summary?: {
      total_opportunities: number;
      total_offers: number;
      total_successes: number;
      total_revenue: number;
      offer_rate: number;
      success_rate: number;
      conversion_rate: number;
    };
    // Direct properties (based on actual API response)
    total_opportunities?: number;
    total_offers?: number;
    total_successes?: number;
    total_revenue?: number;
    offer_rate?: number;
    success_rate?: number;
    conversion_rate?: number;
    item_breakdown?: Record<string, {
      opportunities: number;
      offers: number;
      successes: number;
      revenue: number;
      offer_rate: number;
      success_rate: number;
    }>;
  };
}

interface RunAnalytics {
  success: boolean;
  data?: {
    run_id: string;
    run_date: string;
    location_id: string;
    location_name: string;
    org_name: string;
    total_transactions: number;
    complete_transactions: number;
    completion_rate: number;
    avg_items_initial: number;
    avg_items_final: number;
    avg_item_increase: number;
    
    // Upselling metrics
    upsell_opportunities: number;
    upsell_offers: number;
    upsell_successes: number;
    upsell_conversion_rate: number;
    upsell_revenue: number;
    
    // Upsizing metrics
    upsize_opportunities: number;
    upsize_offers: number;
    upsize_successes: number;
    upsize_conversion_rate: number;
    upsize_revenue: number;
    
    // Add-on metrics
    addon_opportunities: number;
    addon_offers: number;
    addon_successes: number;
    addon_conversion_rate: number;
    addon_revenue: number;
    
    // Overall metrics
    total_opportunities: number;
    total_offers: number;
    total_successes: number;
    overall_conversion_rate: number;
    total_revenue: number;
    
    // Detailed analytics with operator breakdown
    detailed_analytics?: {
      operator_analytics?: Record<string, OperatorMetrics>;
      recommendations?: string[];
    };
  };
  error?: string;
}

const fetchRunAnalytics = async (runId: string): Promise<RunAnalytics> => {
  // Use environment variable or fallback to localhost for development
  const baseUrl = typeof window !== 'undefined' 
    ? (window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin)
    : 'http://localhost:8000';
  
  const url = new URL(`/api/analytics/run/${runId}`, baseUrl);
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch run analytics: ${response.statusText}`);
  }
  
  return response.json();
};

export function useGetRunAnalytics(runId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['run-analytics', runId],
    queryFn: () => fetchRunAnalytics(runId),
    enabled: !!runId && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - analytics don't change often
    refetchOnWindowFocus: false,
  });
}

export type { RunAnalytics, OperatorMetrics };
