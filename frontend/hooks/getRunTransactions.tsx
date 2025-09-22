import { useQuery } from "@tanstack/react-query";

export interface Transaction {
  transaction_id: string;
  transcript: string;
  details: string;
  items_initial: string;
  num_items_initial: number;
  items_after: string;
  num_items_after: number;
  num_upsell_opportunities: number;
  items_upsellable: string;
  items_upselling_creators: string;
  num_upsell_offers: number;
  items_upsold: string;
  items_upsold_creators: string;
  num_upsell_success: number;
  num_largest_offers: number;
  num_upsize_opportunities: number;
  items_upsizeable: string;
  items_upsizing_creators: string;
  num_upsize_offers: number;
  num_upsize_success: number;
  items_upsize_success: string;
  items_upsize_creators: string;
  num_addon_opportunities: number;
  items_addonable: string;
  items_addon_creators: string;
  num_addon_offers: number;
  num_addon_success: number;
  items_addon_success: string;
  items_addon_final_creators: string;
  feedback: string;
  issues: string;
  complete_order: boolean;
  mobile_order: boolean;
  coupon_used: boolean;
  asked_more_time: boolean;
  out_of_stock_items: string;
  gpt_price: number;
  reasoning_summary: string;
  video_file_path: string;
  video_link: string;
  score: number;
  upsell_possible: boolean;
  upsell_offered: boolean;
  upsize_possible: boolean;
  upsize_offered: boolean;
  worker_id: string;
  begin_time: string;
  end_time: string;
  video_id: string;
  run_id: string;
  transaction_kind: string;
  transaction_meta: any;
  clip_s3_url: string;
  employee_id: string;
  employee_name: string;

}

interface TransactionsResponse {
  success: boolean;
  data: {
    transactions: Transaction[];
    total_count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  error?: string;
}

const fetchRunTransactions = async (
  runId: string, 
  limit: number = 50, 
  offset: number = 0
): Promise<TransactionsResponse> => {
  // Use environment variable or fallback to localhost for development
  const baseUrl = typeof window !== 'undefined' 
    ? (window.location.origin.includes('localhost') ? 'http://localhost:8000' : window.location.origin)
    : 'http://localhost:8000';
  
  const url = new URL(`/api/analytics/run/${runId}/transactions`, baseUrl);
  url.searchParams.append('limit', limit.toString());
  url.searchParams.append('offset', offset.toString());
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch run transactions: ${response.statusText}`);
  }
  
  return response.json();
};

export function useGetRunTransactions(
  runId: string, 
  options?: { 
    limit?: number; 
    offset?: number; 
    enabled?: boolean;
  }
) {
  const limit = options?.limit || 50;
  const offset = options?.offset || 0;
  const enabled = options?.enabled !== undefined ? options.enabled : true;

  return useQuery({
    queryKey: ['run-transactions', runId, limit, offset],
    queryFn: () => fetchRunTransactions(runId, limit, offset),
    enabled: !!runId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

export type { TransactionsResponse };
