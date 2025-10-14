"use client"

import * as React from "react"
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Users, Target, DollarSign } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { useFormattedDashboardFilters } from "@/contexts/DashboardFilterContext"
import { useTopOperators, MonthlyFeedback } from "@/hooks/useTopOperators"
import { useTopTransactions } from "@/hooks/useTopTransactions"
import { useTransactionsByIds } from "@/hooks/useTransactionsByIds"
import { MonthlyFeedbackDisplay } from "@/components/monthly-feedback-display"
import { cn } from "@/lib/utils"

interface OperatorPerformanceSectionProps {
  className?: string
}

// Helper function to convert Python dict string to valid JSON
function pythonDictToJson(pythonStr: string): string {
  let jsonStr = pythonStr.trim()

  // If the string is wrapped in outer quotes, unwrap it
  if ((jsonStr.startsWith('"') && jsonStr.endsWith('"')) ||
      (jsonStr.startsWith("'") && jsonStr.endsWith("'"))) {
    jsonStr = jsonStr.slice(1, -1)
  }

  // Replace Python constants first
  jsonStr = jsonStr
    .replace(/\bNone\b/g, 'null')
    .replace(/\bTrue\b/g, 'true')
    .replace(/\bFalse\b/g, 'false')

  // More sophisticated single quote to double quote conversion
  // This handles the complex case where we need to replace single quotes used as dict delimiters
  // but preserve single quotes used as apostrophes

  // State machine approach: track if we're inside a string
  let result = ''
  let inString = false
  let stringChar = ''

  for (let i = 0; i < jsonStr.length; i++) {
    const char = jsonStr[i]
    const prevChar = i > 0 ? jsonStr[i - 1] : ''
    const nextChar = i < jsonStr.length - 1 ? jsonStr[i + 1] : ''

    // Handle escape sequences
    if (char === '\\' && (nextChar === "'" || nextChar === '"')) {
      result += char + nextChar
      i++ // skip next character
      continue
    }

    if (char === "'" && prevChar !== '\\') {
      if (!inString) {
        // Starting a string with single quote
        result += '"'
        inString = true
        stringChar = "'"
      } else if (stringChar === "'") {
        // Ending a string with single quote
        result += '"'
        inString = false
        stringChar = ''
      } else {
        // Single quote inside a double-quoted string - keep as apostrophe
        result += "'"
      }
    } else if (char === '"' && prevChar !== '\\') {
      if (!inString) {
        // Starting a string with double quote
        result += '"'
        inString = true
        stringChar = '"'
      } else if (stringChar === '"') {
        // Ending a string with double quote
        result += '"'
        inString = false
        stringChar = ''
      } else {
        // Double quote inside a single-quoted string - escape it
        result += '\\"'
      }
    } else {
      result += char
    }
  }

  return result
}

// Helper function to safely parse monthly feedback JSON
function parseMonthlyFeedback(feedbackString: string | null): MonthlyFeedback | null {
  if (!feedbackString) return null

  try {
    let parsed
    try {
      // First, try parsing as-is (valid JSON)
      parsed = JSON.parse(feedbackString)
      console.log('✅ Parsed monthly feedback as valid JSON')
    } catch (firstError) {
      // If that fails, try converting Python dict format to JSON
      try {
        console.log('⚠️ Not valid JSON, attempting Python dict conversion...')
        const jsonString = pythonDictToJson(feedbackString)
        console.log('Converted string (first 200 chars):', jsonString.substring(0, 200))
        parsed = JSON.parse(jsonString)
        console.log('✅ Successfully parsed Python dict format')
      } catch (secondError) {
        console.warn('⚠️ Python dict conversion failed, trying simple replacement')
        console.error('Second error:', secondError)
        // Last resort: very simple replacement (will break on apostrophes)
        const jsonString = feedbackString
          .trim()
          .replace(/^["']|["']$/g, '') // Remove outer quotes
          .replace(/'/g, '"')
          .replace(/\bNone\b/g, 'null')
          .replace(/\bTrue\b/g, 'true')
          .replace(/\bFalse\b/g, 'false')

        console.log('Simple replacement result (first 200 chars):', jsonString.substring(0, 200))
        parsed = JSON.parse(jsonString)
        console.log('✅ Parsed with simple replacement (may have issues with apostrophes)')
      }
    }

    // Ensure required fields have defaults
    return {
      top_issues: parsed.top_issues || [],
      top_strengths: parsed.top_strengths || [],
      recommended_actions: parsed.recommended_actions || [],
      overall_rating: parsed.overall_rating || 'N/A'
    }
  } catch (error) {
    console.error('❌ Failed to parse monthly feedback:', error)
    console.error('Original feedback string:', feedbackString?.substring(0, 200))
    return null
  }
}

// Helper function to extract all transaction IDs from monthly feedback
function extractTransactionIds(feedback: MonthlyFeedback | null): string[] {
  if (!feedback) return []

  const issueIds = feedback.top_issues?.flatMap(issue => issue.transaction_ids || []) || []
  const strengthIds = feedback.top_strengths?.flatMap(strength => strength.transaction_ids || []) || []

  // Remove duplicates using Set
  return Array.from(new Set([...issueIds, ...strengthIds]))
}

export function OperatorPerformanceSection({ className }: OperatorPerformanceSectionProps) {
  const [operatorCount, setOperatorCount] = React.useState(5)
  const [inputValue, setInputValue] = React.useState("5")
  const [pendingValue, setPendingValue] = React.useState<number | null>(null)
  const [expandedOperators, setExpandedOperators] = React.useState<Set<string>>(new Set())
  const { locationIds, startDate, endDate } = useFormattedDashboardFilters()

  // Debounce the operator count update (500ms delay)
  React.useEffect(() => {
    if (pendingValue === null) return

    const timeoutId = setTimeout(() => {
      setOperatorCount(pendingValue)
      setPendingValue(null)
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [pendingValue])

  // Handle input change with validation
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value

    // Allow empty string for better UX while typing
    if (value === '') {
      setInputValue('')
      return
    }

    // Only allow numbers
    if (!/^\d+$/.test(value)) {
      return
    }

    const numValue = parseInt(value, 10)

    // Update input value immediately for responsive UI
    setInputValue(value)

    // Clamp value between 1 and 10 and set pending for debounced update
    if (numValue >= 1 && numValue <= 10) {
      setPendingValue(numValue)
    }
  }

  // Handle blur to ensure valid value and immediately apply changes
  const handleInputBlur = () => {
    // Clear any pending debounced update
    setPendingValue(null)

    if (inputValue === '' || parseInt(inputValue, 10) < 1) {
      setInputValue('1')
      setOperatorCount(1)
    } else if (parseInt(inputValue, 10) > 10) {
      setInputValue('10')
      setOperatorCount(10)
    } else {
      // If there's a valid pending value, apply it immediately on blur
      const numValue = parseInt(inputValue, 10)
      if (numValue !== operatorCount) {
        setOperatorCount(numValue)
      }
    }
  }

  // Fetch top operators data
  const { data: operators, isLoading: operatorsLoading } = useTopOperators({
    locationIds,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
    limit: operatorCount,
    enabled: locationIds.length > 0,
  })

  const toggleOperator = (operatorId: string) => {
    setExpandedOperators(prev => {
      const next = new Set(prev)
      if (next.has(operatorId)) {
        next.delete(operatorId)
      } else {
        next.add(operatorId)
      }
      return next
    })
  }

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null || isNaN(value)) {
      return '$0.00'
    }
    return value.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null || isNaN(value)) {
      return '0.0%'
    }
    return `${value.toFixed(1)}%`
  }

  const getMetricColor = (value: number | undefined, threshold: number = 50) => {
    if (value === undefined || value === null || isNaN(value)) return "text-muted-foreground"
    if (value >= threshold) return "text-green-600"
    if (value >= threshold * 0.7) return "text-yellow-600"
    return "text-red-600"
  }

  if (operatorsLoading) {
    return (
      <Card className={cn("@container/card", className)}>
        <CardHeader>
          <div className="h-6 bg-muted rounded w-48 mb-2 animate-pulse"></div>
          <div className="h-4 bg-muted rounded w-64 animate-pulse"></div>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-muted rounded animate-pulse"></div>
          ))}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn("@container/card", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-semibold">Top Operator Performance</CardTitle>
            <CardDescription>
              Ranked operators by revenue generation and conversion rates
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="operator-count" className="text-sm text-muted-foreground whitespace-nowrap">
              Show top
            </Label>
            <Input
              id="operator-count"
              type="text"
              inputMode="numeric"
              value={inputValue}
              onChange={handleInputChange}
              onBlur={handleInputBlur}
              className="h-9 w-16 text-center font-medium text-sm"
              placeholder="5"
              aria-label="Number of operators to show (1-10)"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!operators || operators.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No operator data available for the selected period
          </div>
        ) : (
          <div
            className="max-h-[600px] overflow-y-auto space-y-4 pr-2 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/40"
            style={{ scrollbarWidth: 'thin', scrollbarColor: 'hsl(var(--muted-foreground) / 0.2) transparent' }}
          >
            {operators.map((operator) => {
            const isExpanded = expandedOperators.has(operator.worker_id)
            const offerRateColor = getMetricColor(operator.metrics.offer_rate, 70)
            const conversionRateColor = getMetricColor(operator.metrics.conversion_rate, 50)

            return (
              <Collapsible
                key={operator.worker_id}
                open={isExpanded}
                onOpenChange={() => toggleOperator(operator.worker_id)}
              >
                <div className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                  <CollapsibleTrigger className="w-full">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 text-primary font-bold">
                          {operator.rank}
                        </div>
                        <div className="text-left">
                          <p className="font-semibold text-base">{operator.name}</p>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                            <span>{operator.metrics.total_transactions} transactions</span>
                            <span>•</span>
                            <span>{formatCurrency(operator.metrics.total_revenue)} revenue</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className="flex items-center gap-2">
                            <Target className="h-4 w-4 text-muted-foreground" />
                            <span className={cn("font-medium", offerRateColor)}>
                              {formatPercent(operator.metrics.offer_rate)}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground">Offer Rate</p>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-muted-foreground" />
                            <span className={cn("font-medium", conversionRateColor)}>
                              {formatPercent(operator.metrics.conversion_rate)}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground">Conversion</p>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    </div>
                  </CollapsibleTrigger>

                  <CollapsibleContent>
                    <div className="mt-4 space-y-4">
                      {/* Monthly Feedback with Transactions */}
                      <OperatorMonthlyFeedbackSection
                        operator={operator}
                      />

                      {/* Performance Breakdown */}
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Upselling</p>
                          <div className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span>Opportunities</span>
                              <span className="font-medium">{operator.breakdown.upsell.opportunities}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Offers</span>
                              <span className="font-medium">{operator.breakdown.upsell.offers}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Successes</span>
                              <span className="font-medium text-green-600">{operator.breakdown.upsell.successes}</span>
                            </div>
                            <div className="flex justify-between text-sm font-medium">
                              <span>Revenue</span>
                              <span>{formatCurrency(operator.breakdown.upsell.revenue)}</span>
                            </div>
                          </div>
                        </div>

                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Upsizing</p>
                          <div className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span>Opportunities</span>
                              <span className="font-medium">{operator.breakdown.upsize.opportunities}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Offers</span>
                              <span className="font-medium">{operator.breakdown.upsize.offers}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Successes</span>
                              <span className="font-medium text-green-600">{operator.breakdown.upsize.successes}</span>
                            </div>
                            <div className="flex justify-between text-sm font-medium">
                              <span>Revenue</span>
                              <span>{formatCurrency(operator.breakdown.upsize.revenue)}</span>
                            </div>
                          </div>
                        </div>

                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Add-ons</p>
                          <div className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span>Opportunities</span>
                              <span className="font-medium">{operator.breakdown.addon.opportunities}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Offers</span>
                              <span className="font-medium">{operator.breakdown.addon.offers}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Successes</span>
                              <span className="font-medium text-green-600">{operator.breakdown.addon.successes}</span>
                            </div>
                            <div className="flex justify-between text-sm font-medium">
                              <span>Revenue</span>
                              <span>{formatCurrency(operator.breakdown.addon.revenue)}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                    </div>
                  </CollapsibleContent>
                </div>
              </Collapsible>
            )
          })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function OperatorMonthlyFeedbackSection({
  operator
}: {
  operator: any
}) {
  const { locationIds } = useFormattedDashboardFilters()

  // Parse monthly feedback
  const monthlyFeedback = React.useMemo(() => {
    return parseMonthlyFeedback(operator.monthly_feedback)
  }, [operator.monthly_feedback])

  // Extract ALL transaction IDs from monthly feedback (no limit)
  const transactionIds = React.useMemo(() => {
    return extractTransactionIds(monthlyFeedback)
  }, [monthlyFeedback])

  // Fetch all mentioned transactions
  const { data: transactions, isLoading } = useTransactionsByIds({
    transactionIds: transactionIds,
    locationIds,
    enabled: transactionIds.length > 0 && locationIds.length > 0,
  })

  // If no monthly feedback, show nothing
  if (!monthlyFeedback) {
    return null
  }

  return (
    <div>
      <p className="text-sm font-medium mb-2">Monthly Feedback</p>
      <MonthlyFeedbackDisplay
        feedback={monthlyFeedback}
        transactions={transactions}
        isLoadingTransactions={isLoading}
      />
    </div>
  )
}

function formatPercent(value: number | undefined) {
  if (value === undefined || value === null || isNaN(value)) {
    return '0.0%'
  }
  return `${value.toFixed(1)}%`
}