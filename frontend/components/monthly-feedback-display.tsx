"use client"

import * as React from "react"
import { AlertCircle, CheckCircle2, Lightbulb, TrendingDown, TrendingUp, MessageSquare } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { MonthlyFeedback } from "@/hooks/useTopOperators"
import { TopTransaction } from "@/hooks/useTopTransactions"

interface MonthlyFeedbackDisplayProps {
  feedback: MonthlyFeedback | null
  transactions: TopTransaction[] | undefined
  isLoadingTransactions?: boolean
  className?: string
}

export function MonthlyFeedbackDisplay({
  feedback,
  transactions,
  isLoadingTransactions = false,
  className
}: MonthlyFeedbackDisplayProps) {
  const [expandedIssues, setExpandedIssues] = React.useState<Set<number>>(new Set())
  const [expandedStrengths, setExpandedStrengths] = React.useState<Set<number>>(new Set())
  const [expandedTransactions, setExpandedTransactions] = React.useState<Set<string>>(new Set())

  // Handle null or missing feedback
  if (!feedback) {
    return (
      <div className={cn("bg-muted/30 rounded-lg p-4", className)}>
        <p className="text-sm text-muted-foreground text-center">
          No monthly feedback available yet
        </p>
      </div>
    )
  }

  const toggleIssue = (index: number) => {
    setExpandedIssues(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const toggleStrength = (index: number) => {
    setExpandedStrengths(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const toggleTransaction = (transactionId: string) => {
    setExpandedTransactions(prev => {
      const next = new Set(prev)
      if (next.has(transactionId)) {
        next.delete(transactionId)
      } else {
        next.add(transactionId)
      }
      return next
    })
  }

  // Helper to get transactions for specific IDs
  const getTransactionsForIds = (transactionIds: string[]): TopTransaction[] => {
    if (!transactions || !transactionIds) return []
    return transactions.filter(t => transactionIds.includes(t.id))
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
    <div className={cn("space-y-4", className)}>
      {/* Overall Rating */}
      {feedback.overall_rating && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Overall Rating:</span>
          <Badge className={cn("text-sm font-semibold", getRatingColor(feedback.overall_rating))}>
            {feedback.overall_rating}
          </Badge>
        </div>
      )}

      {/* Top Issues */}
      {hasTopIssues && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-4 w-4 text-orange-600" />
            <h4 className="text-sm font-semibold">Areas for Improvement</h4>
          </div>
          <div className="space-y-2">
            {feedback.top_issues.map((item, index) => {
              const issueTransactions = getTransactionsForIds(item.transaction_ids || [])

              return (
                <Collapsible
                  key={index}
                  open={expandedIssues.has(index)}
                  onOpenChange={() => toggleIssue(index)}
                >
                  <Card className="border-orange-200 dark:border-orange-900">
                    <CollapsibleTrigger className="w-full">
                      <CardHeader className="p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 text-left">
                            <p className="text-sm text-foreground">{item.issue}</p>
                          </div>
                          <Badge variant="secondary" className="text-xs">
                            {item.transaction_ids?.length || 0} {item.transaction_ids?.length === 1 ? 'transaction' : 'transactions'}
                          </Badge>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <CardContent className="p-3 pt-0">
                        <Separator className="mb-3" />

                        {/* Transaction Details */}
                        {isLoadingTransactions ? (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground mb-2">Loading transactions...</p>
                            {[1, 2].map((i) => (
                              <div key={i} className="h-20 bg-muted rounded animate-pulse"></div>
                            ))}
                          </div>
                        ) : issueTransactions.length > 0 ? (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground mb-2">
                              Affected Transactions:
                            </p>
                            {issueTransactions.map((transaction) => {
                              const totalOpportunities =
                                (transaction.grading?.upsell?.opportunities || 0) +
                                (transaction.grading?.upsize?.opportunities || 0) +
                                (transaction.grading?.addon?.opportunities || 0)
                              const totalSuccesses =
                                (transaction.grading?.upsell?.successes || 0) +
                                (transaction.grading?.upsize?.successes || 0) +
                                (transaction.grading?.addon?.successes || 0)

                              return (
                                <Collapsible
                                  key={transaction.id}
                                  open={expandedTransactions.has(transaction.id)}
                                  onOpenChange={() => toggleTransaction(transaction.id)}
                                >
                                  <Card className="border border-orange-100 dark:border-orange-950 bg-orange-50/50 dark:bg-orange-950/20">
                                    <CollapsibleTrigger className="w-full">
                                      <CardHeader className="p-2">
                                        <div className="flex items-start justify-between gap-2">
                                          <div className="flex-1 text-left">
                                            <div className="flex items-center gap-2 mb-1">
                                              <MessageSquare className="h-3 w-3 text-orange-600" />
                                              <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded">
                                                {transaction.id.slice(0, 8)}...
                                              </code>
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                              {totalOpportunities} opportunities, {totalSuccesses} conversions • {transaction.run_date ? new Date(transaction.run_date).toLocaleDateString() : 'N/A'}
                                            </p>
                                          </div>
                                        </div>
                                      </CardHeader>
                                    </CollapsibleTrigger>
                                    <CollapsibleContent>
                                      <CardContent className="p-2 pt-0">
                                        <Separator className="mb-3" />

                                        {/* Performance Metrics Breakdown */}
                                        <div className="mb-3">
                                          <p className="text-xs font-semibold mb-2">Performance Metrics:</p>

                                          {/* Overall Metrics */}
                                          <div className="bg-background/80 p-2 rounded border mb-2">
                                            <p className="text-xs font-medium text-muted-foreground mb-1">Overall</p>
                                            <div className="flex flex-wrap gap-1.5">
                                              <Badge variant="secondary" className="text-xs">
                                                {totalOpportunities} {totalOpportunities === 1 ? 'opportunity' : 'opportunities'}
                                              </Badge>
                                              <Badge variant="secondary" className="text-xs">
                                                {(transaction.grading?.upsell?.offers || 0) +
                                                 (transaction.grading?.upsize?.offers || 0) +
                                                 (transaction.grading?.addon?.offers || 0)} {((transaction.grading?.upsell?.offers || 0) +
                                                 (transaction.grading?.upsize?.offers || 0) +
                                                 (transaction.grading?.addon?.offers || 0)) === 1 ? 'offer' : 'offers'}
                                              </Badge>
                                              <Badge variant="secondary" className="text-xs">
                                                {totalSuccesses} {totalSuccesses === 1 ? 'conversion' : 'conversions'}
                                              </Badge>
                                            </div>
                                          </div>

                                          {/* Category Breakdown */}
                                          <div className="space-y-1.5">
                                            {/* Upsell */}
                                            <div className="flex items-center justify-between text-xs bg-blue-50/50 dark:bg-blue-950/20 p-1.5 rounded border border-blue-100 dark:border-blue-900">
                                              <span className="font-medium text-blue-700 dark:text-blue-300">Upsell</span>
                                              <div className="flex gap-1">
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-blue-200 dark:border-blue-800">
                                                  {transaction.grading?.upsell?.opportunities || 0} opp
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-blue-200 dark:border-blue-800">
                                                  {transaction.grading?.upsell?.offers || 0} off
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-blue-200 dark:border-blue-800">
                                                  {transaction.grading?.upsell?.successes || 0} conv
                                                </Badge>
                                              </div>
                                            </div>

                                            {/* Upsize */}
                                            <div className="flex items-center justify-between text-xs bg-purple-50/50 dark:bg-purple-950/20 p-1.5 rounded border border-purple-100 dark:border-purple-900">
                                              <span className="font-medium text-purple-700 dark:text-purple-300">Upsize</span>
                                              <div className="flex gap-1">
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-purple-200 dark:border-purple-800">
                                                  {transaction.grading?.upsize?.opportunities || 0} opp
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-purple-200 dark:border-purple-800">
                                                  {transaction.grading?.upsize?.offers || 0} off
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-purple-200 dark:border-purple-800">
                                                  {transaction.grading?.upsize?.successes || 0} conv
                                                </Badge>
                                              </div>
                                            </div>

                                            {/* Add-ons */}
                                            <div className="flex items-center justify-between text-xs bg-amber-50/50 dark:bg-amber-950/20 p-1.5 rounded border border-amber-100 dark:border-amber-900">
                                              <span className="font-medium text-amber-700 dark:text-amber-300">Add-ons</span>
                                              <div className="flex gap-1">
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-amber-200 dark:border-amber-800">
                                                  {transaction.grading?.addon?.opportunities || 0} opp
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-amber-200 dark:border-amber-800">
                                                  {transaction.grading?.addon?.offers || 0} off
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-amber-200 dark:border-amber-800">
                                                  {transaction.grading?.addon?.successes || 0} conv
                                                </Badge>
                                              </div>
                                            </div>
                                          </div>
                                        </div>

                                        <Separator className="mb-2" />
                                        {transaction.transaction_text && (
                                          <div className="mb-2">
                                            <p className="text-xs font-medium mb-1">Transcript:</p>
                                            <p className="text-xs text-muted-foreground italic bg-background/50 p-2 rounded border">
                                              {transaction.transaction_text}
                                            </p>
                                          </div>
                                        )}
                                        {transaction.ai_feedback && (
                                          <div>
                                            <p className="text-xs font-medium mb-1">Feedback:</p>
                                            <p className="text-xs text-muted-foreground italic bg-background/50 p-2 rounded border">
                                              {transaction.ai_feedback}
                                            </p>
                                          </div>
                                        )}
                                      </CardContent>
                                    </CollapsibleContent>
                                  </Card>
                                </Collapsible>
                              )
                            })}
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Transaction details not available
                          </p>
                        )}
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              )
            })}
          </div>
        </div>
      )}

      {/* Top Strengths */}
      {hasTopStrengths && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <h4 className="text-sm font-semibold">Key Strengths</h4>
          </div>
          <div className="space-y-2">
            {feedback.top_strengths.map((item, index) => {
              const strengthTransactions = getTransactionsForIds(item.transaction_ids || [])

              return (
                <Collapsible
                  key={index}
                  open={expandedStrengths.has(index)}
                  onOpenChange={() => toggleStrength(index)}
                >
                  <Card className="border-green-200 dark:border-green-900">
                    <CollapsibleTrigger className="w-full">
                      <CardHeader className="p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 text-left">
                            <p className="text-sm text-foreground">{item.strength}</p>
                          </div>
                          <Badge variant="secondary" className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            {item.transaction_ids?.length || 0} {item.transaction_ids?.length === 1 ? 'transaction' : 'transactions'}
                          </Badge>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <CardContent className="p-3 pt-0">
                        <Separator className="mb-3" />

                        {/* Transaction Details */}
                        {isLoadingTransactions ? (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground mb-2">Loading transactions...</p>
                            {[1, 2].map((i) => (
                              <div key={i} className="h-20 bg-muted rounded animate-pulse"></div>
                            ))}
                          </div>
                        ) : strengthTransactions.length > 0 ? (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground mb-2">
                              Example Transactions:
                            </p>
                            {strengthTransactions.map((transaction) => {
                              const totalOpportunities =
                                (transaction.grading?.upsell?.opportunities || 0) +
                                (transaction.grading?.upsize?.opportunities || 0) +
                                (transaction.grading?.addon?.opportunities || 0)
                              const totalSuccesses =
                                (transaction.grading?.upsell?.successes || 0) +
                                (transaction.grading?.upsize?.successes || 0) +
                                (transaction.grading?.addon?.successes || 0)

                              return (
                                <Collapsible
                                  key={transaction.id}
                                  open={expandedTransactions.has(transaction.id)}
                                  onOpenChange={() => toggleTransaction(transaction.id)}
                                >
                                  <Card className="border border-green-100 dark:border-green-950 bg-green-50/50 dark:bg-green-950/20">
                                    <CollapsibleTrigger className="w-full">
                                      <CardHeader className="p-2">
                                        <div className="flex items-start justify-between gap-2">
                                          <div className="flex-1 text-left">
                                            <div className="flex items-center gap-2 mb-1">
                                              <MessageSquare className="h-3 w-3 text-green-600" />
                                              <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded">
                                                {transaction.id.slice(0, 8)}...
                                              </code>
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                              {totalOpportunities} opportunities, {totalSuccesses} conversions • {transaction.run_date ? new Date(transaction.run_date).toLocaleDateString() : 'N/A'}
                                            </p>
                                          </div>
                                        </div>
                                      </CardHeader>
                                    </CollapsibleTrigger>
                                    <CollapsibleContent>
                                      <CardContent className="p-2 pt-0">
                                        <Separator className="mb-3" />

                                        {/* Performance Metrics Breakdown */}
                                        <div className="mb-3">
                                          <p className="text-xs font-semibold mb-2">Performance Metrics:</p>

                                          {/* Overall Metrics */}
                                          <div className="bg-background/80 p-2 rounded border mb-2">
                                            <p className="text-xs font-medium text-muted-foreground mb-1">Overall</p>
                                            <div className="flex flex-wrap gap-1.5">
                                              <Badge variant="secondary" className="text-xs">
                                                {totalOpportunities} {totalOpportunities === 1 ? 'opportunity' : 'opportunities'}
                                              </Badge>
                                              <Badge variant="secondary" className="text-xs">
                                                {(transaction.grading?.upsell?.offers || 0) +
                                                 (transaction.grading?.upsize?.offers || 0) +
                                                 (transaction.grading?.addon?.offers || 0)} {((transaction.grading?.upsell?.offers || 0) +
                                                 (transaction.grading?.upsize?.offers || 0) +
                                                 (transaction.grading?.addon?.offers || 0)) === 1 ? 'offer' : 'offers'}
                                              </Badge>
                                              <Badge variant="secondary" className="text-xs">
                                                {totalSuccesses} {totalSuccesses === 1 ? 'conversion' : 'conversions'}
                                              </Badge>
                                            </div>
                                          </div>

                                          {/* Category Breakdown */}
                                          <div className="space-y-1.5">
                                            {/* Upsell */}
                                            <div className="flex items-center justify-between text-xs bg-blue-50/50 dark:bg-blue-950/20 p-1.5 rounded border border-blue-100 dark:border-blue-900">
                                              <span className="font-medium text-blue-700 dark:text-blue-300">Upsell</span>
                                              <div className="flex gap-1">
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-blue-200 dark:border-blue-800">
                                                  {transaction.grading?.upsell?.opportunities || 0} opp
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-blue-200 dark:border-blue-800">
                                                  {transaction.grading?.upsell?.offers || 0} off
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-blue-200 dark:border-blue-800">
                                                  {transaction.grading?.upsell?.successes || 0} conv
                                                </Badge>
                                              </div>
                                            </div>

                                            {/* Upsize */}
                                            <div className="flex items-center justify-between text-xs bg-purple-50/50 dark:bg-purple-950/20 p-1.5 rounded border border-purple-100 dark:border-purple-900">
                                              <span className="font-medium text-purple-700 dark:text-purple-300">Upsize</span>
                                              <div className="flex gap-1">
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-purple-200 dark:border-purple-800">
                                                  {transaction.grading?.upsize?.opportunities || 0} opp
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-purple-200 dark:border-purple-800">
                                                  {transaction.grading?.upsize?.offers || 0} off
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-purple-200 dark:border-purple-800">
                                                  {transaction.grading?.upsize?.successes || 0} conv
                                                </Badge>
                                              </div>
                                            </div>

                                            {/* Add-ons */}
                                            <div className="flex items-center justify-between text-xs bg-amber-50/50 dark:bg-amber-950/20 p-1.5 rounded border border-amber-100 dark:border-amber-900">
                                              <span className="font-medium text-amber-700 dark:text-amber-300">Add-ons</span>
                                              <div className="flex gap-1">
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-amber-200 dark:border-amber-800">
                                                  {transaction.grading?.addon?.opportunities || 0} opp
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-amber-200 dark:border-amber-800">
                                                  {transaction.grading?.addon?.offers || 0} off
                                                </Badge>
                                                <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-amber-200 dark:border-amber-800">
                                                  {transaction.grading?.addon?.successes || 0} conv
                                                </Badge>
                                              </div>
                                            </div>
                                          </div>
                                        </div>

                                        <Separator className="mb-2" />
                                        {transaction.transaction_text && (
                                          <div className="mb-2">
                                            <p className="text-xs font-medium mb-1">Transcript:</p>
                                            <p className="text-xs text-muted-foreground italic bg-background/50 p-2 rounded border">
                                              {transaction.transaction_text}
                                            </p>
                                          </div>
                                        )}
                                        {transaction.ai_feedback && (
                                          <div>
                                            <p className="text-xs font-medium mb-1">Feedback:</p>
                                            <p className="text-xs text-muted-foreground italic bg-background/50 p-2 rounded border">
                                              {transaction.ai_feedback}
                                            </p>
                                          </div>
                                        )}
                                      </CardContent>
                                    </CollapsibleContent>
                                  </Card>
                                </Collapsible>
                              )
                            })}
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Transaction details not available
                          </p>
                        )}
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              )
            })}
          </div>
        </div>
      )}

      {/* Recommended Actions */}
      {hasRecommendations && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="h-4 w-4 text-blue-600" />
            <h4 className="text-sm font-semibold">Recommended Actions</h4>
          </div>
          <Card className="border-blue-200 dark:border-blue-900">
            <CardContent className="p-3">
              <ol className="space-y-2 text-sm">
                {feedback.recommended_actions.map((action, index) => (
                  <li key={index} className="flex gap-2">
                    <span className="font-semibold text-blue-600 dark:text-blue-400">{index + 1}.</span>
                    <span className="flex-1">{action}</span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty state when no data */}
      {!hasTopIssues && !hasTopStrengths && !hasRecommendations && (
        <div className="bg-muted/30 rounded-lg p-4">
          <p className="text-sm text-muted-foreground text-center">
            No detailed feedback available yet
          </p>
        </div>
      )}
    </div>
  )
}
