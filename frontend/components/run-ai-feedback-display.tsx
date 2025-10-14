"use client"

import * as React from "react"
import { AlertCircle, CheckCircle2, Lightbulb, Loader2, TrendingUp } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { AIFeedback } from "@/hooks/useRunAIFeedback"

interface RunAIFeedbackDisplayProps {
  feedback: AIFeedback | null | undefined
  runId?: string
  runDate?: string
  isLoading?: boolean
  className?: string
}

export function RunAIFeedbackDisplay({
  feedback,
  runId,
  runDate,
  isLoading = false,
  className
}: RunAIFeedbackDisplayProps) {
  // Loading state
  if (isLoading) {
    return (
      <Card className={cn("", className)}>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            AI Performance Insights
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Generating AI insights...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Handle null or missing feedback
  if (!feedback) {
    return (
      <Card className={cn("", className)}>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            AI Performance Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-muted/30 rounded-lg p-6 text-center">
            <p className="text-sm text-muted-foreground">
              No AI feedback available for this run yet
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const getRatingColor = (rating: string) => {
    const normalized = rating.toLowerCase()
    if (normalized === 'excellent') return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    if (normalized === 'good') return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    if (normalized === 'fair') return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    if (normalized === 'poor') return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
  }

  const hasTopIssues = feedback.top_issues && feedback.top_issues.length > 0
  const hasTopStrengths = feedback.top_strengths && feedback.top_strengths.length > 0
  const hasRecommendations = feedback.recommended_actions && feedback.recommended_actions.length > 0

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            AI Performance Insights
          </CardTitle>
          {feedback.overall_rating && (
            <Badge className={cn("text-sm font-semibold", getRatingColor(feedback.overall_rating))}>
              {feedback.overall_rating}
            </Badge>
          )}
        </div>
        {(runId || runDate) && (
          <div className="flex gap-2 text-xs text-muted-foreground">
            {runDate && <span>{new Date(runDate).toLocaleDateString()}</span>}
            {runId && <span className="font-mono">{runId.slice(0, 8)}...</span>}
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Top Issues */}
        {hasTopIssues && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-orange-600" />
              <h4 className="text-sm font-semibold">Areas for Improvement</h4>
            </div>
            <div className="space-y-2">
              {feedback.top_issues.map((item, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg border border-orange-200 dark:border-orange-900 bg-orange-50/50 dark:bg-orange-950/20"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <p className="text-sm flex-1">{item.issue}</p>
                    <Badge variant="secondary" className="text-xs shrink-0">
                      {item.transaction_ids?.length || 0} tx
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Strengths */}
        {hasTopStrengths && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <h4 className="text-sm font-semibold">Key Strengths</h4>
            </div>
            <div className="space-y-2">
              {feedback.top_strengths.map((item, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg border border-green-200 dark:border-green-900 bg-green-50/50 dark:bg-green-950/20"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <p className="text-sm flex-1">{item.strength}</p>
                    <Badge
                      variant="secondary"
                      className="text-xs shrink-0 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                    >
                      {item.transaction_ids?.length || 0} tx
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Actions */}
        {hasRecommendations && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-blue-600" />
              <h4 className="text-sm font-semibold">Recommended Actions</h4>
            </div>
            <div className="p-4 rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20">
              <ol className="space-y-2.5">
                {feedback.recommended_actions.map((action, index) => (
                  <li key={index} className="flex gap-2.5 text-sm">
                    <span className="font-semibold text-blue-600 dark:text-blue-400 shrink-0">
                      {index + 1}.
                    </span>
                    <span className="flex-1">{action}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}

        {/* Empty state when no data */}
        {!hasTopIssues && !hasTopStrengths && !hasRecommendations && (
          <div className="bg-muted/30 rounded-lg p-6 text-center">
            <p className="text-sm text-muted-foreground">
              No detailed feedback available
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
