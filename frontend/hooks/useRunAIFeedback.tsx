import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { useAuth } from "@/contexts/authContext"

export interface AIFeedbackIssue {
  issue: string;
  transaction_ids: string[];
}

export interface AIFeedbackStrength {
  strength: string;
  transaction_ids: string[];
}

export interface AIFeedback {
  top_issues: AIFeedbackIssue[];
  top_strengths: AIFeedbackStrength[];
  recommended_actions: string[];
  overall_rating: "Excellent" | "Good" | "Fair" | "Poor";
}

interface AIFeedbackResponse {
  success: boolean;
  data: {
    run_id: string;
    feedback: AIFeedback;
  } | null;
  message?: string;
  error?: string;
}

const fetchRunAIFeedback = async (
  runId: string
): Promise<AIFeedbackResponse> => {
  try {
    // Use apiClient which auto-attaches auth headers
    const response = await apiClient.get<AIFeedbackResponse>(`/runs/${runId}/ai-feedback`);
    return response;
  } catch (error: any) {
    // Handle case where no feedback is available
    if (error?.response?.status === 200 && error?.response?.data?.data === null) {
      return {
        success: true,
        data: null,
        message: "No feedback data available for this run"
      };
    }
    throw error;
  }
};

export function useRunAIFeedback(
  runId: string,
  options?: {
    enabled?: boolean;
  }
) {
  const { user } = useAuth()
  const enabled = options?.enabled !== undefined ? options.enabled : true;

  return useQuery({
    queryKey: ['run-ai-feedback', user?.id, runId],
    queryFn: () => fetchRunAIFeedback(runId),
    enabled: !!runId && !!user && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - AI feedback doesn't change often
    refetchOnWindowFocus: false,
  });
}

export type { AIFeedbackResponse };
