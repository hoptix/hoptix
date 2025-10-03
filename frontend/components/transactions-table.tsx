"use client"

import * as React from "react"
import { format } from "date-fns"
import {
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
  IconLoader,
  IconAlertCircle,
  IconEye,
  IconExternalLink,
  IconDownload,
} from "@tabler/icons-react"

import { useGetRunTransactions, type Transaction } from "@/hooks/getRunTransactions"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { convertToCSV, downloadCSV, formatDateForCSV, formatDurationForCSV, cleanJSONForCSV, type CSVColumn } from "@/lib/csv-export"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface TransactionsTableProps {
  runId: string
  pageSize?: number
}

// Helper function to parse and format item lists
const formatItems = (itemsString: string): string => {
  if (!itemsString || itemsString === '[]') return 'None';
  try {
    // Remove brackets and quotes, split by comma
    const items = itemsString.replace(/[\[\]"]/g, '').split(',').map(item => item.trim()).filter(Boolean);
    return items.join(', ');
  } catch {
    return itemsString;
  }
};

// Helper function to format time duration
const formatDuration = (startTime: string, endTime: string): string => {
  try {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end.getTime() - start.getTime();
    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  } catch {
    return 'N/A';
  }
};

// Helper function to get success rate color
const getSuccessRateColor = (opportunities: number, successes: number): string => {
  if (opportunities === 0) return 'text-gray-500';
  const rate = (successes / opportunities) * 100;
  if (rate >= 50) return 'text-green-600';
  if (rate >= 25) return 'text-yellow-600';
  return 'text-red-600';
};

export function TransactionsTable({ runId, pageSize = 25 }: TransactionsTableProps) {
  const [currentPage, setCurrentPage] = React.useState(0);
  const [expandedTranscripts, setExpandedTranscripts] = React.useState<Set<string>>(new Set());
  const [isExporting, setIsExporting] = React.useState(false);
  const offset = currentPage * pageSize;

  const { data, isLoading, isError, error, refetch } = useGetRunTransactions(runId, {
    limit: pageSize,
    offset: offset,
  });

  const transactions = data?.data?.transactions || [];
  const totalCount = data?.data?.total_count || 0;
  const hasMore = data?.data?.has_more || false;
  const totalPages = Math.ceil(totalCount / pageSize);

  const handlePreviousPage = () => {
    setCurrentPage(prev => Math.max(0, prev - 1));
  };

  const handleNextPage = () => {
    if (hasMore) {
      setCurrentPage(prev => prev + 1);
    }
  };

  const handleFirstPage = () => {
    setCurrentPage(0);
  };

  const handleLastPage = () => {
    setCurrentPage(totalPages - 1);
  };

  const toggleTranscript = (transactionId: string) => {
    setExpandedTranscripts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(transactionId)) {
        newSet.delete(transactionId);
      } else {
        newSet.add(transactionId);
      }
      return newSet;
    });
  };

  // CSV column definitions
  const csvColumns: CSVColumn[] = [
    { key: 'transaction_id', label: 'Transaction ID' },
    { key: 'employee_name', label: 'Employee Name' },
    { key: 'employee_id', label: 'Employee ID' },
    { key: 'begin_time', label: 'Start Time', transform: formatDateForCSV },
    { key: 'end_time', label: 'End Time', transform: formatDateForCSV },
    { 
      key: 'begin_time', 
      label: 'Duration', 
      transform: (value: string, row: Transaction) => formatDurationForCSV(row.begin_time, row.end_time)
    },
    { key: 'transcript', label: 'Transcript', transform: cleanJSONForCSV },
    { key: 'num_items_initial', label: 'Initial Items Count' },
    { key: 'items_initial', label: 'Initial Items', transform: cleanJSONForCSV },
    { key: 'num_items_after', label: 'Final Items Count' },
    { key: 'items_after', label: 'Final Items', transform: cleanJSONForCSV },
    { key: 'num_upsell_opportunities', label: 'Upsell Opportunities' },
    { key: 'num_upsell_offers', label: 'Upsell Offers' },
    { key: 'num_upsell_success', label: 'Upsell Successes' },
    { key: 'upsell_candidate_items', label: 'Items Upsellable', transform: cleanJSONForCSV },
    { key: 'upsell_success_items', label: 'Items Upsold', transform: cleanJSONForCSV },
    { key: 'num_upsize_opportunities', label: 'Upsize Opportunities' },
    { key: 'num_upsize_offers', label: 'Upsize Offers' },
    { key: 'num_upsize_success', label: 'Upsize Successes' },
    { key: 'upsize_candidate_items', label: 'Items Upsizeable', transform: cleanJSONForCSV },
    { key: 'upsize_success_items', label: 'Items Upsized', transform: cleanJSONForCSV },
    { key: 'num_addon_opportunities', label: 'Addon Opportunities' },
    { key: 'num_addon_offers', label: 'Addon Offers' },
    { key: 'num_addon_success', label: 'Addon Successes' },
    { key: 'addon_candidate_items', label: 'Items Addonable', transform: cleanJSONForCSV },
    { key: 'addon_success_items', label: 'Items Added', transform: cleanJSONForCSV },
    { key: 'score', label: 'Score' },
    { key: 'complete_order', label: 'Complete Order', transform: (value: number) => value ? 'Yes' : 'No' },
    { key: 'mobile_order', label: 'Mobile Order', transform: (value: number) => value ? 'Yes' : 'No' },
    { key: 'coupon_used', label: 'Coupon Used', transform: (value: number) => value ? 'Yes' : 'No' },
    { key: 'asked_more_time', label: 'Asked More Time', transform: (value: number) => value ? 'Yes' : 'No' },
    { key: 'details', label: 'Details', transform: cleanJSONForCSV },
    { key: 'out_of_stock_items', label: 'Out of Stock Items', transform: cleanJSONForCSV },
    { key: 'reasoning_summary', label: 'Reasoning Summary', transform: cleanJSONForCSV },
    { key: 'feedback', label: 'Feedback', transform: cleanJSONForCSV },
    { key: 'issues', label: 'Issues', transform: cleanJSONForCSV },
    { key: 'video_link', label: 'Video Link' },
    { key: 'clip_s3_url', label: 'Clip URL' },
  ];

  // Export current page to CSV
  const exportCurrentPageToCSV = () => {
    if (!transactions.length) return;
    
    const csv = convertToCSV(transactions, csvColumns);
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const filename = `transactions_${runId}_page${currentPage + 1}_${timestamp}.csv`;
    
    downloadCSV(csv, filename);
  };

  // Export all transactions to CSV
  const exportAllToCSV = async () => {
    setIsExporting(true);
    try {
      // Fetch all transactions by making multiple requests
      const allTransactions: Transaction[] = [];
      const batchSize = 200; // Larger batch size for export
      let currentOffset = 0;
      let hasMoreData = true;

      while (hasMoreData) {
        const response = await fetch(
          `http://localhost:8000/api/analytics/run/${runId}/transactions?limit=${batchSize}&offset=${currentOffset}`
        );
        
        if (!response.ok) {
          throw new Error('Failed to fetch transactions');
        }
        
        const data = await response.json();
        if (data.success && data.data.transactions) {
          allTransactions.push(...data.data.transactions);
          hasMoreData = data.data.has_more;
          currentOffset += batchSize;
        } else {
          hasMoreData = false;
        }
      }

      if (allTransactions.length > 0) {
        const csv = convertToCSV(allTransactions, csvColumns);
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
        const filename = `transactions_${runId}_complete_${timestamp}.csv`;
        
        downloadCSV(csv, filename);
      }
    } catch (error) {
      console.error('Error exporting transactions:', error);
      alert('Failed to export transactions. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Transaction Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <IconLoader className="h-6 w-6 animate-spin mr-2" />
            <span>Loading transactions...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Transaction Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-red-600">
            <IconAlertCircle className="h-6 w-6 mr-2" />
            <span>Error loading transactions: {error?.message}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Transaction Details</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {totalCount} total transactions
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={exportCurrentPageToCSV}
              disabled={!transactions.length}
            >
              <IconDownload className="h-4 w-4 mr-2" />
              Export Page
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={exportAllToCSV}
              disabled={isExporting || !totalCount}
            >
              {isExporting ? (
                <IconLoader className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <IconDownload className="h-4 w-4 mr-2" />
              )}
              Export All
            </Button>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {transactions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No transactions found for this run.
          </div>
        ) : (
          <>
            <div className="rounded-md border overflow-x-auto">
              <Table className="min-w-max">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-32">Employee</TableHead>
                    <TableHead className="w-28">Time</TableHead>
                    <TableHead className="w-20">Duration</TableHead>
                    <TableHead className="w-32">Transcript</TableHead>
                    <TableHead className="w-48">Items Initial</TableHead>
                    <TableHead className="w-48">Items After</TableHead>
                    <TableHead className="w-32">Upselling</TableHead>
                    <TableHead className="w-48">Items Upsellable</TableHead>
                    <TableHead className="w-48">Items Upsold</TableHead>
                    <TableHead className="w-32">Upsizing</TableHead>
                    <TableHead className="w-48">Items Upsizeable</TableHead>
                    <TableHead className="w-48">Items Upsized</TableHead>
                    <TableHead className="w-32">Add-ons</TableHead>
                    <TableHead className="w-48">Items Addonable</TableHead>
                    <TableHead className="w-48">Items Added</TableHead>
                    <TableHead className="w-20">Score</TableHead>
                    <TableHead className="w-24">Complete</TableHead>
                    <TableHead className="w-24">Mobile</TableHead>
                    <TableHead className="w-24">Coupon</TableHead>
                    <TableHead className="w-24">More Time</TableHead>
                    <TableHead className="w-64">Details</TableHead>
                    <TableHead className="w-48">Out of Stock</TableHead>
                    <TableHead className="w-64">Reasoning</TableHead>
                    <TableHead className="w-64">Feedback</TableHead>
                    <TableHead className="w-64">Issues</TableHead>
                    <TableHead className="w-32">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((transaction) => (
                    <TableRow key={transaction.transaction_id}>
                      {/* Employee */}
                      <TableCell className="w-32">
                        <div>
                          <div className="font-medium">{transaction.employee_name || 'Unknown'}</div>
                          <div className="text-xs text-muted-foreground">
                            ID: {transaction.employee_id?.substring(0, 8) || 'N/A'}
                          </div>
                        </div>
                      </TableCell>
                      
                      {/* Time */}
                      <TableCell className="w-28">
                        <div className="text-sm">
                          {transaction.begin_time ? format(new Date(transaction.begin_time), 'HH:mm:ss') : 'N/A'}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {transaction.begin_time ? format(new Date(transaction.begin_time), 'MMM dd') : ''}
                        </div>
                      </TableCell>
                      
                      {/* Duration */}
                      <TableCell className="w-20">
                        <Badge variant="outline">
                          {formatDuration(transaction.begin_time, transaction.end_time)}
                        </Badge>
                      </TableCell>
                      
                      {/* Transcript */}
                      <TableCell className="w-32">
                        <div 
                          className="text-xs text-muted-foreground cursor-pointer hover:text-blue-600 transition-colors"
                          onClick={() => toggleTranscript(transaction.transaction_id)}
                          title="Click to expand/collapse transcript"
                        >
                          {expandedTranscripts.has(transaction.transaction_id) ? (
                            <div className="whitespace-pre-wrap max-h-32 overflow-y-auto p-2 bg-gray-50 rounded border">
                              {transaction.transcript || 'None'}
                            </div>
                          ) : (
                            <div className="truncate">
                              {transaction.transcript ? 
                                (transaction.transcript.length > 50 ? 
                                  `${transaction.transcript.substring(0, 50)}...` : 
                                  transaction.transcript
                                ) : 
                                'None'
                              }
                            </div>
                          )}
                        </div>
                      </TableCell>
                      
                      {/* Items Initial */}
                      <TableCell className="w-48">
                        <div className="text-sm">
                          <span className="font-medium">{transaction.num_items_initial}</span> items
                        </div>
                        <div className="text-xs text-muted-foreground truncate" title={transaction.items_initial}>
                          {transaction.items_initial || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Items After */}
                      <TableCell className="w-48">
                        <div className="text-sm">
                          <span className="font-medium">{transaction.num_items_after}</span> items
                        </div>
                        <div className="text-xs text-muted-foreground truncate" title={transaction.items_after}>
                          {transaction.items_after || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Upselling Stats */}
                      <TableCell className="w-32">
                        <div className="text-center">
                          <div className={`text-sm font-medium ${getSuccessRateColor(transaction.num_upsell_opportunities, transaction.num_upsell_success)}`}>
                            {transaction.num_upsell_success}/{transaction.num_upsell_opportunities}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {transaction.num_upsell_offers} offers
                          </div>
                        </div>
                      </TableCell>
                      
                      {/* Items Upsellable */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={String(transaction.upsell_candidate_items || 'None')}>
                          {transaction.upsell_candidate_items || 'None'}
                        </div>
                      </TableCell>

                      {/* Items Upsold */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={String(transaction.upsell_success_items || 'None')}>
                          {transaction.upsell_success_items || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Upsizing Stats */}
                      <TableCell className="w-32">
                        <div className="text-center">
                          <div className={`text-sm font-medium ${getSuccessRateColor(transaction.num_upsize_opportunities, transaction.num_upsize_success)}`}>
                            {transaction.num_upsize_success}/{transaction.num_upsize_opportunities}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {transaction.num_upsize_offers} offers
                          </div>
                        </div>
                      </TableCell>
                      
                      {/* Items Upsizeable */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={String(transaction.upsize_candidate_items || 'None')}>
                          {transaction.upsize_candidate_items || 'None'}
                        </div>
                      </TableCell>

                      {/* Items Upsized */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={String(transaction.upsize_success_items || 'None')}>
                          {transaction.upsize_success_items || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Add-ons Stats */}
                      <TableCell className="w-32">
                        <div className="text-center">
                          <div className={`text-sm font-medium ${getSuccessRateColor(transaction.num_addon_opportunities, transaction.num_addon_success)}`}>
                            {transaction.num_addon_success}/{transaction.num_addon_opportunities}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {transaction.num_addon_offers} offers
                          </div>
                        </div>
                      </TableCell>
                      
                      {/* Items Addonable */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={String(transaction.addon_candidate_items || 'None')}>
                          {transaction.addon_candidate_items || 'None'}
                        </div>
                      </TableCell>

                      {/* Items Added */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={String(transaction.addon_success_items || 'None')}>
                          {transaction.addon_success_items || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Score */}
                      <TableCell className="w-20">
                        <Badge 
                          variant={transaction.score >= 80 ? "default" : transaction.score >= 60 ? "secondary" : "destructive"}
                        >
                          {transaction.score}
                        </Badge>
                      </TableCell>
                      
                      {/* Complete Order */}
                      <TableCell className="w-24">
                        <Badge variant={transaction.complete_order ? "default" : "destructive"}>
                          {transaction.complete_order ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                      
                      {/* Mobile Order */}
                      <TableCell className="w-24">
                        <Badge variant={transaction.mobile_order ? "secondary" : "outline"}>
                          {transaction.mobile_order ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                      
                      {/* Coupon Used */}
                      <TableCell className="w-24">
                        <Badge variant={transaction.coupon_used ? "secondary" : "outline"}>
                          {transaction.coupon_used ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                      
                      {/* Asked More Time */}
                      <TableCell className="w-24">
                        <Badge variant={transaction.asked_more_time ? "secondary" : "outline"}>
                          {transaction.asked_more_time ? "Yes" : "No"}
                        </Badge>
                      </TableCell>
                      
                      
                      {/* Details */}
                      <TableCell className="w-64">
                        <div className="text-xs text-muted-foreground truncate" title={typeof transaction.details === 'object' ? JSON.stringify(transaction.details) : transaction.details}>
                          {typeof transaction.details === 'object' 
                            ? 'JSON Object'
                            : (transaction.details || 'None')
                          }
                        </div>
                      </TableCell>
                      
                      {/* Out of Stock Items */}
                      <TableCell className="w-48">
                        <div className="text-xs text-muted-foreground truncate" title={transaction.out_of_stock_items}>
                          {transaction.out_of_stock_items || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Reasoning Summary */}
                      <TableCell className="w-64">
                        <div className="text-xs text-muted-foreground truncate" title={transaction.reasoning_summary}>
                          {transaction.reasoning_summary || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Feedback */}
                      <TableCell className="w-64">
                        <div className="text-xs text-muted-foreground truncate" title={transaction.feedback}>
                          {transaction.feedback || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Issues */}
                      <TableCell className="w-64">
                        <div className="text-xs text-muted-foreground truncate" title={transaction.issues}>
                          {transaction.issues || 'None'}
                        </div>
                      </TableCell>
                      
                      {/* Actions */}
                      <TableCell className="w-32">
                        <div className="flex items-center gap-2">
                          {transaction.video_link && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => transaction.video_link && window.open(transaction.video_link, '_blank')}
                            >
                              <IconEye className="h-4 w-4" />
                            </Button>
                          )}
                          {transaction.clip_s3_url && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => transaction.clip_s3_url && window.open(transaction.clip_s3_url, '_blank')}
                            >
                              <IconExternalLink className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-2 py-4">
                <div className="text-sm text-muted-foreground">
                  Showing {offset + 1} to {Math.min(offset + pageSize, totalCount)} of {totalCount} transactions
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleFirstPage}
                    disabled={currentPage === 0}
                  >
                    <IconChevronsLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePreviousPage}
                    disabled={currentPage === 0}
                  >
                    <IconChevronLeft className="h-4 w-4" />
                  </Button>
                  <div className="text-sm">
                    Page {currentPage + 1} of {totalPages}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleNextPage}
                    disabled={!hasMore}
                  >
                    <IconChevronRight className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLastPage}
                    disabled={currentPage >= totalPages - 1}
                  >
                    <IconChevronsRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
