"use client"

import * as React from "react"
import { format } from "date-fns"
import { IconChevronDown, IconChevronRight, IconCalendar, IconLoader, IconAlertCircle } from "@tabler/icons-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { RunAIFeedbackDisplay } from "./run-ai-feedback-display"
import { RangeRunAIFeedback } from "@/hooks/useRangeRunsAIFeedback"
import { cn } from "@/lib/utils"

interface RangeRunsAIFeedbackDisplayProps {
  rangeData: RangeRunAIFeedback[]
  isLoading?: boolean
  className?: string
}

export function RangeRunsAIFeedbackDisplay({
  rangeData,
  isLoading = false,
  className
}: RangeRunsAIFeedbackDisplayProps) {
  const [expandedRuns, setExpandedRuns] = React.useState<Set<string>>(new Set())

  const toggleRun = (runId: string) => {
    setExpandedRuns(prev => {
      const next = new Set(prev)
      if (next.has(runId)) {
        next.delete(runId)
      } else {
        next.add(runId)
      }
      return next
    })
  }

  // Loading state
  if (isLoading) {
    return (
      <Card className={cn("", className)}>
        <CardHeader>
          <CardTitle className="text-lg">AI Performance Insights by Run</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <IconLoader className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Generating AI insights for all runs in the range...
              </p>
              <p className="text-xs text-muted-foreground">
                This may take a moment for multiple runs
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // No data
  if (!rangeData || rangeData.length === 0) {
    return (
      <Card className={cn("", className)}>
        <CardHeader>
          <CardTitle className="text-lg">AI Performance Insights by Run</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-muted/30 rounded-lg p-6 text-center">
            <p className="text-sm text-muted-foreground">
              No runs found in the selected date range
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Filter runs that have feedback
  const runsWithFeedback = rangeData.filter(r => r.has_feedback && r.feedback)
  const runsWithoutFeedback = rangeData.filter(r => !r.has_feedback || !r.feedback)

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">AI Performance Insights by Run</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {runsWithFeedback.length} of {rangeData.length} runs have AI feedback
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Runs with feedback */}
        {runsWithFeedback.length > 0 && (
          <div className="space-y-2">
            {runsWithFeedback.map((runData) => {
              const isExpanded = expandedRuns.has(runData.run_id)
              const runDate = runData.run_date ? format(new Date(runData.run_date), 'MMM d, yyyy') : 'Unknown date'

              return (
                <div key={runData.run_id} className="border rounded-lg">
                  <Button
                    variant="ghost"
                    className="w-full justify-between p-4 h-auto hover:bg-muted/50"
                    onClick={() => toggleRun(runData.run_id)}
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <IconChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                      ) : (
                        <IconChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                      )}
                      <div className="flex items-center gap-2">
                        <IconCalendar className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{runDate}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {runData.feedback?.overall_rating && (
                        <span className="text-xs font-medium text-muted-foreground">
                          {runData.feedback.overall_rating}
                        </span>
                      )}
                    </div>
                  </Button>

                  {isExpanded && runData.feedback && (
                    <div className="px-4 pb-4">
                      <RunAIFeedbackDisplay
                        feedback={runData.feedback}
                        runId={runData.run_id}
                        runDate={runData.run_date}
                        isLoading={false}
                        className="shadow-none border-0"
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Info about runs without feedback */}
        {runsWithoutFeedback.length > 0 && (
          <div className="mt-4 p-3 bg-muted/30 rounded-lg">
            <div className="flex items-start gap-2">
              <IconAlertCircle className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="text-xs text-muted-foreground">
                <p className="font-medium mb-1">
                  {runsWithoutFeedback.length} run{runsWithoutFeedback.length !== 1 ? 's' : ''} without feedback
                </p>
                <p>
                  These runs may not have transaction-level feedback data available yet.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
