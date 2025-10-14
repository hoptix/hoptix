import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/contexts/authContext"
import { AIFeedback } from "./useRunAIFeedback"

export interface RangeRunAIFeedback {
  run_id: string;
  run_date: string;
  location_id: string;
  feedback: AIFeedback | null;
  has_feedback: boolean;
  error?: string;
}

interface RangeAIFeedbackResponse {
  success: boolean;
  data: RangeRunAIFeedback[];
  meta: {
    total_runs: number;
    runs_with_feedback: number;
    start_date: string;
    end_date: string;
  };
  error?: string;
}

const fetchRangeRunsAIFeedback = async (
  locationIds: string[],
  startDate: string | null,
  endDate: string | null
): Promise<RangeAIFeedbackResponse> => {
  // Build query parameters
  const params = new URLSearchParams()

  // Add location_ids[] as multiple params
  locationIds.forEach(id => {
    params.append('location_ids[]', id)
  })

  // Add date range
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)

  const response = await apiClient.get<RangeAIFeedbackResponse>(
    `/runs/range-ai-feedback?${params.toString()}`
  )

  return response
}

export function useRangeRunsAIFeedback(
  locationIds: string[],
  startDate: string | null,
  endDate: string | null,
  options?: {
    enabled?: boolean;
  }
) {
  const { user } = useAuth()
  const enabled = options?.enabled !== undefined ? options.enabled : true

  return useQuery({
    queryKey: ['range-runs-ai-feedback', user?.id, locationIds, startDate, endDate],
    queryFn: () => fetchRangeRunsAIFeedback(locationIds, startDate, endDate),
    enabled: !!user && enabled && locationIds.length > 0 && !!startDate && !!endDate,
    staleTime: 15 * 60 * 1000, // 15 minutes - AI feedback is expensive to generate
    refetchOnWindowFocus: false,
  })
}

export type { RangeAIFeedbackResponse }
