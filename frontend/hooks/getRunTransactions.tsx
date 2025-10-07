import { useQuery } from "@tanstack/react-query";

export interface Transaction {
  transaction_id: string;
  transcript: string;
  details: any;
  items_initial: string;
  num_items_initial: number;
  items_after: string;
  num_items_after: number;
  num_upsell_opportunities: number;
  upsell_base_items: any[];
  upsell_candidate_items: string;
  upsell_offered_items: string;
  upsell_success_items: string;
  num_upsell_offers: number;
  num_upsell_success: number;
  num_largest_offers: number;
  num_upsize_opportunities: number;
  upsize_base_items: any[];
  upsize_candidate_items: string;
  upsize_offered_items: string;
  upsize_success_items: string;
  num_upsize_offers: number;
  num_upsize_success: number;
  num_addon_opportunities: number;
  addon_base_items: string;
  addon_candidate_items: string;
  addon_offered_items: string;
  addon_success_items: string;
  num_addon_offers: number;
  num_addon_success: number;
  items_addonable: string; // Added this field
  items_upsizeable: string; // Added this field
  feedback: string;
  issues: string;
  complete_order: number;
  mobile_order: number;
  coupon_used: number;
  asked_more_time: number;
  out_of_stock_items: string;
  reasoning_summary: string;
  video_file_path: string | null;
  video_link: string | null;
  score: number;
  worker_id: string;
  begin_time: string;
  end_time: string;
  video_id: string;
  run_id: string;
  transaction_kind: string;
  transaction_meta: any;
  clip_s3_url: string | null;
  employee_id: string;
  employee_legal_name: string;
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
  
  // Backend route lives under /runs/<run_id>/transactions
  const url = new URL(`/runs/${runId}/transactions`, baseUrl);
  url.searchParams.append('limit', limit.toString());
  url.searchParams.append('offset', offset.toString());
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch run transactions: ${response.statusText}`);
  }
  
  const raw = await response.json();
  const rows: any[] = raw?.data?.transactions ?? raw?.transactions ?? [];

  // Normalize backend fields to Transaction interface
  const transactions: Transaction[] = rows.map((t: any) => {
    const initialItems = t.initial_items ?? t.items_initial ?? [];
    const finalItems = t.final_items ?? t.items_after ?? [];

    // Coerce arrays/strings defensively
    const ensureArray = (v: any) => Array.isArray(v) ? v : (v ? [v] : []);

    const upsellBase = t.upsell_base_item ?? t.upsell_base_items ?? [];
    const upsizeBase = t.upsize_base_item ?? t.upsize_base_items ?? [];

    const tx: Transaction = {
      // ID fallbacks
      transaction_id: t.transaction_id ?? t.id ?? t.uuid ?? '',
      transcript: t.transcript ?? '',
      details: t.details ?? null,
      items_initial: Array.isArray(initialItems) ? initialItems.join(', ') : String(initialItems ?? ''),
      num_items_initial: Array.isArray(initialItems) ? initialItems.length : (t.num_items_initial ?? 0),
      items_after: Array.isArray(finalItems) ? finalItems.join(', ') : String(finalItems ?? ''),
      num_items_after: Array.isArray(finalItems) ? finalItems.length : (t.num_items_after ?? 0),
      num_upsell_opportunities: t.num_upsell_opportunities ?? 0,
      upsell_base_items: ensureArray(upsellBase),
      upsell_candidate_items: t.upsell_candidate_items ?? '',
      upsell_offered_items: t.upsell_offered_items ?? '',
      upsell_success_items: t.upsell_success_items ?? '',
      num_upsell_offers: t.num_upsell_offers ?? 0,
      num_upsell_success: t.num_upsell_success ?? 0,
      num_largest_offers: t.num_largest_offers ?? 0,
      num_upsize_opportunities: t.num_upsize_opportunities ?? 0,
      upsize_base_items: ensureArray(upsizeBase),
      upsize_candidate_items: t.upsize_candidate_items ?? '',
      upsize_offered_items: t.upsize_offered_items ?? '',
      upsize_success_items: t.upsize_success_items ?? '',
      num_upsize_offers: t.num_upsize_offers ?? 0,
      num_upsize_success: t.num_upsize_success ?? 0,
      num_addon_opportunities: t.num_addon_opportunities ?? 0,
      addon_base_items: t.addon_base_item ?? t.addon_base_items ?? '',
      addon_candidate_items: t.addon_candidate_items ?? '',
      addon_offered_items: t.addon_offered_items ?? '',
      addon_success_items: t.addon_success_items ?? '',
      num_addon_offers: t.num_addon_offers ?? 0,
      num_addon_success: t.num_addon_success ?? 0,
      items_addonable: t.items_addonable ?? '',
      items_upsizeable: t.items_upsizeable ?? '',
      feedback: t.feedback ?? '',
      issues: t.issues ?? '',
      complete_order: t.complete_order ?? 0,
      mobile_order: t.mobile_order ?? 0,
      coupon_used: t.coupon_used ?? 0,
      asked_more_time: t.asked_more_time ?? 0,
      out_of_stock_items: t.out_of_stock_items ?? '',
      reasoning_summary: t.reasoning_summary ?? '',
      video_file_path: t.video_file_path ?? null,
      video_link: t.video_link ?? null,
      score: t.score ?? 0,
      worker_id: t.worker_id ?? '',
      begin_time: t.begin_time ?? t.start_time ?? '',
      end_time: t.end_time ?? t.finish_time ?? '',
      video_id: t.video_id ?? '',
      run_id: t.run_id ?? '',
      transaction_kind: t.transaction_kind ?? '',
      transaction_meta: t.transaction_meta ?? null,
      clip_s3_url: t.clip_s3_url ?? null,
      employee_id: t.employee_id ?? '',
      employee_legal_name: t.employee_legal_name ?? '',
      employee_name: t.employee_name ?? '',
    };
    return tx;
  });

  const total_count = raw?.data?.total_count ?? transactions.length;
  const has_more = raw?.data?.has_more ?? total_count > limit + offset;

  return {
    success: true,
    data: {
      transactions,
      total_count,
      limit,
      offset,
      has_more,
    },
  } as TransactionsResponse;
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
