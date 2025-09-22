"use client"

import { IconStar, IconTrophy, IconClock, IconUser, IconTrendingUp, IconInfoCircle, IconDownload } from "@tabler/icons-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useGetTopTransactions, type TopTransaction } from "@/hooks/getTopTransactions"
import { convertToCSV, downloadCSV, formatDateForCSV, type CSVColumn } from "@/lib/csv-export"
import { format } from "date-fns"

interface TopTransactionsHighlightProps {
  locationId: string
  date?: string
  className?: string
}

const getRankBadgeColor = (rank: number) => {
  switch (rank) {
    case 1: return "bg-yellow-100 text-yellow-800 border-yellow-300"
    case 2: return "bg-gray-100 text-gray-800 border-gray-300"
    case 3: return "bg-orange-100 text-orange-800 border-orange-300"
    default: return "bg-blue-100 text-blue-800 border-blue-300"
  }
}

const getRankIcon = (rank: number) => {
  switch (rank) {
    case 1: return <IconTrophy className="h-4 w-4 text-yellow-600" />
    case 2: case 3: return <IconStar className="h-4 w-4" />
    default: return <IconTrendingUp className="h-4 w-4" />
  }
}

const TransactionCard = ({ transaction }: { transaction: TopTransaction }) => {
  const startTime = new Date(transaction.start_time)
  const formattedTime = format(startTime, "HH:mm")
  
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200 bg-white">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Badge className={`${getRankBadgeColor(transaction.rank)} font-semibold`}>
            <div className="flex items-center space-x-1">
              {getRankIcon(transaction.rank)}
              <span>#{transaction.rank}</span>
            </div>
          </Badge>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <div className="text-sm font-medium text-gray-900 truncate max-w-32">
                  {transaction.employee_name}
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Employee: {transaction.employee_name}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-green-600">
            {(transaction.composite_score * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500">Composite Score</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
        <div className="text-center p-2 bg-green-50 rounded">
          <div className="font-semibold text-green-700">
            {transaction.performance_metrics.upselling.success_rate}%
          </div>
          <div className="text-gray-600">Upselling</div>
        </div>
        <div className="text-center p-2 bg-blue-50 rounded">
          <div className="font-semibold text-blue-700">
            {transaction.performance_metrics.upsizing.success_rate}%
          </div>
          <div className="text-gray-600">Upsizing</div>
        </div>
        <div className="text-center p-2 bg-purple-50 rounded">
          <div className="font-semibold text-purple-700">
            {transaction.performance_metrics.addons.success_rate}%
          </div>
          <div className="text-gray-600">Add-ons</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-1">
          <IconClock className="h-3 w-3" />
          <span>{formattedTime}</span>
          {transaction.duration_minutes && (
            <span>({transaction.duration_minutes}m)</span>
          )}
        </div>
        <div className="flex items-center space-x-1">
          {transaction.special_flags.mobile_order && (
            <Badge variant="outline" className="text-xs">Mobile</Badge>
          )}
          {transaction.special_flags.coupon_used && (
            <Badge variant="outline" className="text-xs">Coupon</Badge>
          )}
        </div>
      </div>

      {transaction.feedback && (
        <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
          <div className="truncate" title={transaction.feedback}>
            {transaction.feedback.length > 100 
              ? `${transaction.feedback.substring(0, 100)}...` 
              : transaction.feedback
            }
          </div>
        </div>
      )}
    </div>
  )
}

export function TopTransactionsHighlight({ locationId, date, className }: TopTransactionsHighlightProps) {
  const { data, isLoading, isError, error } = useGetTopTransactions(locationId, date, 5)

  // CSV column definitions for top transactions
  const csvColumns: CSVColumn[] = [
    { key: 'rank', label: 'Rank' },
    { key: 'transaction_id', label: 'Transaction ID' },
    { key: 'employee_name', label: 'Employee Name' },
    { key: 'start_time', label: 'Start Time', transform: formatDateForCSV },
    { key: 'end_time', label: 'End Time', transform: formatDateForCSV },
    { key: 'duration_minutes', label: 'Duration (Minutes)' },
    { key: 'composite_score', label: 'Composite Score' },
    { key: 'base_score', label: 'Base Score' },
    { 
      key: 'performance_metrics', 
      label: 'Upselling Success Rate', 
      transform: (value: any) => `${value.upselling.success_rate}%`
    },
    { 
      key: 'performance_metrics', 
      label: 'Upselling (Success/Offers)', 
      transform: (value: any) => `${value.upselling.successes}/${value.upselling.offers}`
    },
    { 
      key: 'performance_metrics', 
      label: 'Upsizing Success Rate', 
      transform: (value: any) => `${value.upsizing.success_rate}%`
    },
    { 
      key: 'performance_metrics', 
      label: 'Upsizing (Success/Offers)', 
      transform: (value: any) => `${value.upsizing.successes}/${value.upsizing.offers}`
    },
    { 
      key: 'performance_metrics', 
      label: 'Addons Success Rate', 
      transform: (value: any) => `${value.addons.success_rate}%`
    },
    { 
      key: 'performance_metrics', 
      label: 'Addons (Success/Offers)', 
      transform: (value: any) => `${value.addons.successes}/${value.addons.offers}`
    },
    { key: 'items_initial', label: 'Initial Items' },
    { key: 'items_after', label: 'Final Items' },
    { key: 'feedback', label: 'Feedback' },
    { key: 'transcript_preview', label: 'Transcript Preview' },
    { 
      key: 'special_flags', 
      label: 'Mobile Order', 
      transform: (value: any) => value.mobile_order ? 'Yes' : 'No'
    },
    { 
      key: 'special_flags', 
      label: 'Coupon Used', 
      transform: (value: any) => value.coupon_used ? 'Yes' : 'No'
    },
  ];

  const exportTopTransactions = () => {
    if (!data?.data.top_transactions.length) return;
    
    const csv = convertToCSV(data.data.top_transactions, csvColumns);
    const timestamp = new Date().toISOString().slice(0, 10);
    const filename = `top_transactions_${locationId}_${date || timestamp}_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.csv`;
    
    downloadCSV(csv, filename);
  };

  if (!locationId) {
    return null
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <IconTrophy className="h-5 w-5 text-yellow-600" />
            <span>Top Transactions Today</span>
          </CardTitle>
          <CardDescription>AI-powered performance highlights</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <div className="h-6 w-12 bg-gray-200 rounded"></div>
                      <div className="h-4 w-20 bg-gray-200 rounded"></div>
                    </div>
                    <div className="text-right">
                      <div className="h-6 w-12 bg-gray-200 rounded"></div>
                      <div className="h-3 w-16 bg-gray-200 rounded mt-1"></div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {[1, 2, 3].map((j) => (
                      <div key={j} className="h-12 bg-gray-100 rounded"></div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isError) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <IconTrophy className="h-5 w-5 text-yellow-600" />
            <span>Top Transactions Today</span>
          </CardTitle>
          <CardDescription>AI-powered performance highlights</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <IconInfoCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">Unable to load top transactions</p>
            <p className="text-sm text-gray-500">{error?.message || 'Please try again later'}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data?.success || !data.data.top_transactions.length) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <IconTrophy className="h-5 w-5 text-yellow-600" />
            <span>Top Transactions Today</span>
          </CardTitle>
          <CardDescription>AI-powered performance highlights</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <IconUser className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No transactions found</p>
            <p className="text-sm text-gray-500">
              {data?.data.criteria_explanation || 'No transactions available for the selected date'}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { top_transactions, total_transactions_analyzed, complete_transactions_analyzed, criteria_explanation } = data.data

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <IconTrophy className="h-5 w-5 text-yellow-600" />
              <span>Top Transactions Today</span>
            </CardTitle>
            <CardDescription>AI-powered performance highlights</CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportTopTransactions}
              disabled={!data?.data.top_transactions.length}
            >
              <IconDownload className="h-4 w-4 mr-2" />
              Export
            </Button>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <IconInfoCircle className="h-5 w-5 text-gray-400 hover:text-gray-600 cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-sm">
                  <div className="space-y-2">
                    <div className="font-semibold">AI Scoring Algorithm:</div>
                    <div className="text-xs space-y-1">
                      <div>• Base Score: 40%</div>
                      <div>• Upselling: 25%</div>
                      <div>• Upsizing: 20%</div>
                      <div>• Add-ons: 15%</div>
                    </div>
                    <div className="text-xs text-gray-500 pt-1">
                      Analyzed {complete_transactions_analyzed} of {total_transactions_analyzed} transactions
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {top_transactions.map((transaction) => (
            <TransactionCard key={transaction.transaction_id} transaction={transaction} />
          ))}
        </div>
        
        {top_transactions.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 text-center">
              Showing top {top_transactions.length} of {complete_transactions_analyzed} complete transactions
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
